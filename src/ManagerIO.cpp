/*
 * Copyright (c) 2015, 2016, 2017, 2018, Intel Corporation
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions
 * are met:
 *
 *     * Redistributions of source code must retain the above copyright
 *       notice, this list of conditions and the following disclaimer.
 *
 *     * Redistributions in binary form must reproduce the above copyright
 *       notice, this list of conditions and the following disclaimer in
 *       the documentation and/or other materials provided with the
 *       distribution.
 *
 *     * Neither the name of Intel Corporation nor the names of its
 *       contributors may be used to endorse or promote products derived
 *       from this software without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
 * "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
 * LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
 * A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
 * OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
 * SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
 * LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
 * DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
 * THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY LOG OF THE USE
 * OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */

#include <fstream>
#include <sstream>
#include <algorithm>
#include <iostream>
#include <string>
#include <cmath>
#include <string.h>

#include "contrib/json11/json11.hpp"

#include "ManagerIO.hpp"
#include "PlatformTopo.hpp"
#include "SharedMemory.hpp"
#include "Exception.hpp"
#include "Helper.hpp"
#include "config.h"

using json11::Json;

namespace geopm
{

    ManagerIO::ManagerIO(const std::string &json_path, std::unique_ptr<ISharedMemory> json_shmem)
        : m_path(json_path)
        , m_json_shmem(std::move(json_shmem))
        , m_data(nullptr)
        , m_signal_value_map({})
        , m_is_shm_data((m_path[0] == '/' && m_path.find_last_of('/') == 0) ? true : false)
    {
        if (m_json_shmem == nullptr) {
            size_t shmem_size = sizeof(struct geopm_manager_shmem_s);
            m_json_shmem = geopm::make_unique<SharedMemory>(m_path, shmem_size);
        }

        if (m_is_shm_data == true) {
            m_data = (struct geopm_manager_shmem_s *) m_json_shmem->pointer();
            *m_data = {};
            setup_mutex(m_data->lock);
        }
    }

    ManagerIO::ManagerIO(const std::string &json_path)
        : ManagerIO(json_path, nullptr)
    {
    }

    void ManagerIO::setup_mutex(pthread_mutex_t &lock)
    {
        pthread_mutexattr_t lock_attr;
        int err = pthread_mutexattr_init(&lock_attr);
        if (err) {
            throw Exception("ProfileTable: pthread mutex initialization", GEOPM_ERROR_RUNTIME, __FILE__, __LINE__);
        }
        err = pthread_mutexattr_settype(&lock_attr, PTHREAD_MUTEX_ERRORCHECK);
        if (err) {
            throw Exception("ProfileTable: pthread mutex initialization", GEOPM_ERROR_RUNTIME, __FILE__, __LINE__);
        }
        err = pthread_mutexattr_setpshared(&lock_attr, PTHREAD_PROCESS_SHARED);
        if (err) {
            throw Exception("ProfileTable: pthread mutex initialization", GEOPM_ERROR_RUNTIME, __FILE__, __LINE__);
        }
        err = pthread_mutex_init(&lock, &lock_attr);
        if (err) {
            throw Exception("ProfileTable: pthread mutex initialization", GEOPM_ERROR_RUNTIME, __FILE__, __LINE__);
        }
    }

    void ManagerIO::adjust(const std::string &signal_name, double setting)
    {
        m_signal_value_map.emplace(signal_name, setting);
    }

    void ManagerIO::write_batch(void)
    {
        if (m_is_shm_data == true) {
            write_shmem();
        }
        else {
            write_file();
        }
    }

    void ManagerIO::write_file(void)
    {
        std::ofstream json_file_out(m_path, std::ifstream::out);

        if (!json_file_out.is_open()) {
            throw Exception("ManagerIOSampler::" + std::string(__func__)  + "(): output file \"" + m_path +
                            "\" could not be opened", GEOPM_ERROR_INVALID, __FILE__, __LINE__);
        }

        Json root (m_signal_value_map);
        json_file_out << root.dump();
        json_file_out.close();
    }

    void ManagerIO::write_shmem(void)
    {
        std::string json_str = Json(m_signal_value_map).dump();

        if (m_data->is_updated == true) {
            throw Exception("ManagerIOSampler::" + std::string(__func__)  + "(): write requested before previous " +
                            "update has been processed.", GEOPM_ERROR_INVALID, __FILE__, __LINE__);
        }

        int err = pthread_mutex_lock(&m_data->lock); // Default mutex will block until this completes.
        if (err) {
            throw Exception("ManagerIOSampler::pthread_mutex_lock()", err, __FILE__, __LINE__);
        }

        m_data->is_updated = true;
        m_data->json_size = json_str.size();
        strncpy(m_data->json_str, json_str.c_str(), json_str.size());
        pthread_mutex_unlock(&m_data->lock);
    }

    /*********************************************************************************************************/

    ManagerIOSampler::ManagerIOSampler(const std::string &json_path, std::unique_ptr<ISharedMemoryUser> json_shmem)
        : m_path(json_path)
        , m_json_shmem(std::move(json_shmem))
        , m_data(nullptr)
        , m_json_data("")
        , m_signal_value_map(parse_json())
    {
    }

    ManagerIOSampler::ManagerIOSampler(const std::string &json_path)
        : ManagerIOSampler(json_path, nullptr)
    {
    }

    std::map<std::string, double> ManagerIOSampler::parse_json(void)
    {
        std::map<std::string, double> signal_value_map;
        std::string json_str;

        if (m_path[0] == '/' && m_path.find_last_of('/') == 0) {
            json_str = read_shmem();
            m_is_shm_data = true;
        }
        else {
            json_str = read_file();
            m_is_shm_data = false;
        }

        // Begin JSON parse
        std::string err;
        Json root = Json::parse(json_str, err);
        if (!err.empty() || !root.is_object()) {
            throw Exception("ManagerIOSampler::" + std::string(__func__) + "(): detected a malformed json config file: " + err,
                            GEOPM_ERROR_FILE_PARSE, __FILE__, __LINE__);
        }

        m_json_data = root.dump();

        for (const auto &obj : root.object_items()) {
            switch (obj.second.type()) {
                case Json::NUMBER:
                    signal_value_map.emplace(obj.first, obj.second.number_value());
                    break;
                default:
                    throw Exception("Json::" + std::string(__func__)  + ": unsupported type or malformed json config file",
                                    GEOPM_ERROR_FILE_PARSE, __FILE__, __LINE__);
                    break;
            }
        }

        return signal_value_map;
    }

    const std::string ManagerIOSampler::read_file(void)
    {
        std::string json_str;
        std::ifstream json_file_in(m_path, std::ifstream::in);

        if (!json_file_in.is_open()) {
            throw Exception("ManagerIOSampler::" + std::string(__func__)  + "(): input configuration file \"" + m_path +
                            "\" could not be opened", GEOPM_ERROR_INVALID, __FILE__, __LINE__);
        }

        json_file_in.seekg(0, std::ios::end);
        size_t file_size = json_file_in.tellg();
        if (file_size <= 0) {
            throw Exception("ManagerIOSampler::" + std::string(__func__)  + "(): input configuration file invalid",
                            GEOPM_ERROR_INVALID, __FILE__, __LINE__);
        }
        json_str.resize(file_size); // DO NOT modify json_str beyond this point.
        json_file_in.seekg(0, std::ios::beg);
        json_file_in.read(&json_str[0], file_size);
        json_file_in.close();

        return json_str;
    }

    const std::string ManagerIOSampler::read_shmem(void)
    {
        std::string json_data;

        if (m_json_shmem == nullptr) {
            m_json_shmem = geopm::make_unique<SharedMemoryUser>(m_path, 5);
        }

        m_data = (struct geopm_manager_shmem_s *) m_json_shmem->pointer(); // Managed by shmem subsystem.

        int err = pthread_mutex_lock(&m_data->lock); // Default mutex will block until this completes.
        if (err) {
            throw Exception("ManagerIOSampler::pthread_mutex_lock()", err, __FILE__, __LINE__);
        }

        if(m_data->is_updated == true) {
            json_data = std::string(m_data->json_str, m_data->json_size);
            m_data->is_updated = false;
            (void) pthread_mutex_unlock(&m_data->lock);
        }
        else {
            (void) pthread_mutex_unlock(&m_data->lock);
            throw Exception("ManagerIOSampler::" + std::string(__func__)  + "(): reread of shm region requested before update.",
                            GEOPM_ERROR_INVALID, __FILE__, __LINE__);
        }

        return json_data;
    }

    bool ManagerIOSampler::is_valid_signal(const std::string &signal_name)
    {
        return m_signal_value_map.find(signal_name) != m_signal_value_map.end();
    }

    void ManagerIOSampler::read_batch(void)
    {
        //Re-parse the shmem region
        if (m_is_shm_data == true) {
            m_signal_value_map = parse_json();
        }
        else {
            throw Exception("ManagerIOSampler::" + std::string(__func__)  + "(): reread of file data requested. " +
                            "This is only valid for shmem regions.",
                            GEOPM_ERROR_INVALID, __FILE__, __LINE__);
        }
    }

    // Do the map lookup, return the value.  Should take a std::string for the signal name.
    double ManagerIOSampler::sample(const std::string &signal_name)
    {
        if (!is_valid_signal(signal_name)) {
            throw Exception("ManagerIOGroup::" + std::string(__func__) + "(): " + signal_name + " not valid for ManagerIOGroup.",
                            GEOPM_ERROR_INVALID, __FILE__, __LINE__);
        }

        return m_signal_value_map.find(signal_name)->second;
    }

    // Change the int to a std::string for the signal name. The idea is that this would be called a few times to
    // update the map before it is written to shared memory.
    // MOVE THIS TO THE WRITER
    // void ManagerIOSampler::adjust(int batch_idx, double setting)
    // {
    //     std::ostringstream ex_str;
    //     ex_str << "ManagerIOSampler::" << __func__ << "(): there are no controls supported by the ManagerIOSampler";
    //     throw Exception(ex_str.str(), GEOPM_ERROR_INVALID, __FILE__, __LINE__);
    // }

    std::string ManagerIOSampler::json_str(void)
    {
        return m_json_data;
    }

    bool ManagerIOSampler::is_update_available(void)
    {
        if(m_data == nullptr) {
            std::ostringstream ex_str;
            ex_str << "ManagerIOSampler::" << __func__ << "(): m_data is null";
            throw Exception(ex_str.str(), GEOPM_ERROR_INVALID, __FILE__, __LINE__);
        }
        return m_data->is_updated != 0;
    }

}

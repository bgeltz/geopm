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
#ifndef GLOBALPOLICYIOGROUP_HPP_INCLUDE
#define GLOBALPOLICYIOGROUP_HPP_INCLUDE

#include <map>
#include <pthread.h>

namespace geopm
{
    class ISharedMemory;
    class ISharedMemoryUser;

    // TODO Think about putting the padding in this struct.  align_as...
    struct geopm_manager_shmem_s {
        /// @brief Lock to ensure r/w consistency between GEOPM and the resource manager.
        pthread_mutex_t lock;
        /// @brief Enables notification of updates to GEOPM.
        uint8_t is_updated;
        /// @brief Specifies the size of the json_str.
        size_t json_size;
        /// @brief Holds arbitrary JSON data.
        char json_str[1 * 1024 * 1024]; // 1 MB = 1 * (1024 B / 1 KB) * (1024 KB / 1 MB)
        // double new_thing[ 512 - sizeof(above_stuff) ];
    };

    class ManagerIO
    {
        public:
            ManagerIO() = delete;
            ManagerIO(const ManagerIO &other) = delete;
            ManagerIO(const std::string &json_data_path);
            ManagerIO(const std::string &json_data_path, std::unique_ptr<ISharedMemory> json_shmem);
            ~ManagerIO() = default;
            void adjust(const std::string &signal_name, double setting);
            void write_batch(void);
            std::string json_str(void);
            static void setup_mutex(pthread_mutex_t &lock);

        private:
            void write_file();
            void write_shmem();
            std::string m_path;
            std::unique_ptr<ISharedMemory> m_json_shmem;
            struct geopm_manager_shmem_s *m_data;
            std::map<std::string, double> m_signal_value_map;
            bool m_is_shm_data;
    };

    class ManagerIOSampler
    {
        public:
            ManagerIOSampler() = delete;
            ManagerIOSampler(const ManagerIOSampler &other) = delete;
            ManagerIOSampler(const std::string &json_data_path);
            ManagerIOSampler(const std::string &json_data_path, std::unique_ptr<ISharedMemoryUser> json_shmem);
            ~ManagerIOSampler() = default;
            bool is_valid_signal(const std::string &signal_name);
            void read_batch(void);
            double sample(const std::string &signal_name);
            std::string json_str(void);
            bool is_update_available(void);

        private:
            std::map<std::string, double> parse_json(void);
            const std::string read_file(void);
            const std::string read_shmem(void);

            std::string m_path;
            std::unique_ptr<ISharedMemoryUser> m_json_shmem;
            struct geopm_manager_shmem_s *m_data;
            std::string m_json_data;
            std::map<std::string, double> m_signal_value_map;
            bool m_is_shm_data;
    };
}

#endif

/* Opens:
 *   1. How the resource manager will create and setup the shmem region.  New cmdline binary for interaction?
 *   2. How the signals contained within the JSON data will be vetted?  The old GlobalPolicy had explicit checks
 *      for every possible data element.
 *   3. How data in the signal_value_map will get updated for platform IO?  Need a map updated method and a write method.
 *   4. Do we need the ability to write JSON files (not into shmem)?  If so why?
 *   5. Should ManagerIOSamplerTest::setup_mutex be here somewhere?  Standardizing the setup process seems important.
 *      Perhaps this should be a static method?
 *   6. Any other mandatory strings that belong here?  geopm_version?  profile_name?  Perhaps this is the controller's
 *      responsibility.
 */


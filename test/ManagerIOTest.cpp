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

#include <string.h>
#include <stdlib.h>
#include <pthread.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <iostream>
#include <fstream>
#include <map>
#include <vector>

#include "contrib/json11/json11.hpp"

#include "gtest/gtest.h"
#include "gmock/gmock.h"
#include "geopm_test.hpp"

#include "MockSharedMemory.hpp"
#include "MockSharedMemoryUser.hpp"

#include "Helper.hpp"
#include "Exception.hpp"
#include "ManagerIO.hpp"
#include "PlatformTopo.hpp"
#include "SharedMemory.hpp"

using geopm::IPlatformTopo;
using geopm::ManagerIO;
using geopm::ManagerIOSampler;
using geopm::SharedMemory;
using geopm::geopm_manager_shmem_s;
using geopm::Exception;

using json11::Json;

class ManagerIOTest: public :: testing :: Test
{
    public:
        ManagerIOTest();
        ~ManagerIOTest() = default;

    protected:
        const std::string m_json_file_path = "ManagerIOTest_data";
        const std::string m_json_shm_path = "/ManagerIOTest_data_" + std::to_string(geteuid());
        std::string m_valid_json;
};

ManagerIOTest::ManagerIOTest()
{
    std::string tab = std::string(4, ' ');
    std::ostringstream valid_json;
    valid_json << "{" << std::endl
                 << tab << "\"POWER_CONSUMED\" : 777," << std::endl
                 << tab << "\"RUNTIME\" : 12.3456," << std::endl
                 << tab << "\"GHZ\" : 2.3e9" << std::endl
                 << "}" << std::endl;
    m_valid_json = valid_json.str();
}

TEST_F(ManagerIOTest, write_json_file)
{
    ManagerIO jio(m_json_file_path);

    jio.adjust("POWER_CONSUMED", 777);
    jio.adjust("RUNTIME", 12.3456);
    jio.adjust("GHZ", 2.3e9);
    jio.write_batch();

    ManagerIOSampler jios(m_json_file_path);

    EXPECT_EQ(777, jios.sample("POWER_CONSUMED"));
    EXPECT_EQ(12.3456, jios.sample("RUNTIME"));
    EXPECT_EQ(2.3e9, jios.sample("GHZ"));

    std::remove(m_json_file_path.c_str());
}

TEST_F(ManagerIOTest, write_json_shm)
{
    size_t shmem_size = sizeof(struct geopm_manager_shmem_s);
    std::unique_ptr<MockSharedMemory> json_shmem(new MockSharedMemory(shmem_size));
    struct geopm_manager_shmem_s *data = (struct geopm_manager_shmem_s *) json_shmem->pointer();
    ManagerIO jio(m_json_shm_path, std::move(json_shmem));

    jio.adjust("POWER_CONSUMED", 777);
    jio.adjust("RUNTIME", 12.3456);
    jio.adjust("GHZ", 2.3e9);
    jio.write_batch();

    std::string json_str(data->json_str, data->json_size);
    Json root (json_str);

    // ManagerIOSampler jios("/BULLSHIT", );

    // EXPECT_EQ(777, jios.sample("POWER_CONSUMED"));
    // EXPECT_EQ(12.3456, jios.sample("RUNTIME"));
    // EXPECT_EQ(2.3e9, jios.sample("GHZ"));
}

TEST_F(ManagerIOTest, negative_write_json_shm_int)
{
    ManagerIO jio(m_json_shm_path);

    jio.adjust("POWER_CONSUMED", 777);
    jio.adjust("RUNTIME", 12.3456);
    jio.adjust("GHZ", 2.3e9);
    jio.write_batch();

    GEOPM_EXPECT_THROW_MESSAGE(jio.write_batch(),
                               GEOPM_ERROR_INVALID, "write requested before previous update has been processed.");

    std::remove(m_json_file_path.c_str());
}

TEST_F(ManagerIOTest, negative_write_json_file)
{
    std::string path ("ManagerIOTest_empty");
    std::ofstream empty_file(path, std::ofstream::out);
    empty_file.close();
    chmod(path.c_str(), 0);

    ManagerIO jio (path);

    GEOPM_EXPECT_THROW_MESSAGE(jio.write_batch(),
                               GEOPM_ERROR_INVALID, "output file \"" + path + "\" could not be opened");
    std::remove(path.c_str());
}

/*************************************************************************************************/

class ManagerIOSamplerTest: public :: testing :: Test
{
    public:
        ManagerIOSamplerTest();

    protected:
        void SetUp();
        void TearDown();
        const std::string m_json_file_path = "ManagerIOSamplerTest_data";
        const std::string m_json_file_path_bad = "ManagerIOSamplerTest_data_bad";
        const std::string m_json_shm_path = "/ManagerIOSamplerTest_data_" + std::to_string(geteuid());
        std::string m_valid_json;
        std::string m_valid_json_bad_type;
};

ManagerIOSamplerTest::ManagerIOSamplerTest()
{
    std::string tab = std::string(4, ' ');
    std::ostringstream valid_json;
    valid_json << "{" << std::endl
                 << tab << "\"POWER_MAX\" : 400," << std::endl
                 << tab << "\"FREQUENCY_MAX\" : 2300000000," << std::endl
                 << tab << "\"FREQUENCY_MIN\" : 1200000000," << std::endl
                 << tab << "\"PI\" : 3.14159265," << std::endl
                 << tab << "\"GHZ\" : 2.3e9" << std::endl
                 << "}" << std::endl;
    m_valid_json = valid_json.str();

    std::ostringstream bad_json;
    bad_json << "{" << std::endl
               << tab << "\"POWER_MAX\" : 400," << std::endl
               << tab << "\"FREQUENCY_MAX\" : 2300000000," << std::endl
               << tab << "\"FREQUENCY_MIN\" : 1200000000," << std::endl
               << tab << "\"ARBITRARY_SIGNAL\" : \"WUBBA LUBBA DUB DUB\"," << std::endl // Strings are not handled.
               << tab << "\"PI\" : 3.14159265," << std::endl
               << tab << "\"GHZ\" : 2.3e9" << std::endl
               << "}" << std::endl;
    m_valid_json_bad_type = bad_json.str();
}

void ManagerIOSamplerTest::SetUp()
{
    std::ofstream json_stream(m_json_file_path);
    std::ofstream json_stream_bad(m_json_file_path_bad);

    json_stream << m_valid_json;
    json_stream.close();

    json_stream_bad << m_valid_json_bad_type;
    json_stream_bad.close();
}

void ManagerIOSamplerTest::TearDown()
{
    std::remove(m_json_file_path.c_str());
    std::remove(m_json_file_path_bad.c_str());
}

TEST_F(ManagerIOSamplerTest, parse_json_file)
{
    ManagerIOSampler gp(m_json_file_path);

    EXPECT_EQ(400, gp.sample("POWER_MAX"));
    EXPECT_EQ(2.3e9, gp.sample("FREQUENCY_MAX"));
    EXPECT_EQ(1.2e9, gp.sample("FREQUENCY_MIN"));
    EXPECT_EQ(3.14159265, gp.sample("PI"));
}

TEST_F(ManagerIOSamplerTest, negative_parse_json_file)
{
    GEOPM_EXPECT_THROW_MESSAGE(new ManagerIOSampler(m_json_file_path_bad),
                               GEOPM_ERROR_FILE_PARSE, "unsupported type or malformed json config file");

    ManagerIOSampler gp(m_json_file_path);
    GEOPM_EXPECT_THROW_MESSAGE(gp.read_batch(), GEOPM_ERROR_INVALID, "reread of file data requested.");
}

TEST_F(ManagerIOSamplerTest, parse_json_shm)
{
    size_t shmem_size = sizeof(struct geopm_manager_shmem_s);
    std::unique_ptr<MockSharedMemoryUser> json_shmem(new MockSharedMemoryUser(shmem_size));
    struct geopm_manager_shmem_s *data = (struct geopm_manager_shmem_s *) json_shmem->pointer();

    // Build the data
    data->is_updated = true;
    ManagerIO::setup_mutex(data->lock);
    data->json_size = m_valid_json.size();
    strncpy(data->json_str, m_valid_json.c_str(), m_valid_json.size());

    ManagerIOSampler gp("/BULLSHIT", std::move(json_shmem));

    EXPECT_FALSE(gp.is_update_available());
    EXPECT_EQ(400, gp.sample("POWER_MAX"));
    EXPECT_EQ(2.3e9, gp.sample("FREQUENCY_MAX"));
    EXPECT_EQ(1.2e9, gp.sample("FREQUENCY_MIN"));
    EXPECT_EQ(3.14159265, gp.sample("PI"));
}

TEST_F(ManagerIOSamplerTest, parse_json_shm_int)
{
    // TODO Move to TestIntegration variant of ManagerIOSamplerTest
    std::string full_path("/dev/shm" + m_json_shm_path);
    std::remove(full_path.c_str());

    size_t shmem_size = sizeof(struct geopm_manager_shmem_s);
    SharedMemory sm(m_json_shm_path, shmem_size);
    struct geopm_manager_shmem_s *data = (struct geopm_manager_shmem_s *) sm.pointer();

    // Build the data
    data->is_updated = true;
    ManagerIO::setup_mutex(data->lock);
    data->json_size = m_valid_json.size();
    strncpy(data->json_str, m_valid_json.c_str(), m_valid_json.size());

    ManagerIOSampler gp(m_json_shm_path);

    EXPECT_FALSE(gp.is_update_available());
    EXPECT_EQ(400, gp.sample("POWER_MAX"));
    EXPECT_EQ(2.3e9, gp.sample("FREQUENCY_MAX"));
    EXPECT_EQ(1.2e9, gp.sample("FREQUENCY_MIN"));
    EXPECT_EQ(3.14159265, gp.sample("PI"));

    std::string updated_json = m_valid_json;
    updated_json.replace(m_valid_json.find("400"), 3, "350");

    pthread_mutex_lock(&data->lock);
    data->is_updated = true;
    data->json_size = updated_json.size();
    strncpy(data->json_str, updated_json.c_str(), updated_json.size());
    pthread_mutex_unlock(&data->lock);

    gp.read_batch();

    EXPECT_EQ(350, gp.sample("POWER_MAX"));
    EXPECT_EQ(2.3e9, gp.sample("FREQUENCY_MAX"));
    EXPECT_EQ(1.2e9, gp.sample("FREQUENCY_MIN"));
    EXPECT_EQ(3.14159265, gp.sample("PI"));
}

TEST_F(ManagerIOSamplerTest, negative_parse_json_shm)
{
    size_t shmem_size = sizeof(struct geopm_manager_shmem_s);
    std::unique_ptr<MockSharedMemoryUser> json_shmem(new MockSharedMemoryUser(shmem_size));
    struct geopm_manager_shmem_s *data = (struct geopm_manager_shmem_s *) json_shmem->pointer();

    // Build the data
    data->is_updated = true;
    ManagerIO::setup_mutex(data->lock);
    data->json_size = m_valid_json_bad_type.size();
    strncpy(data->json_str, m_valid_json_bad_type.c_str(), m_valid_json_bad_type.size());

    GEOPM_EXPECT_THROW_MESSAGE(new ManagerIOSampler("/BULLSHIT", std::move(json_shmem)),
                               GEOPM_ERROR_FILE_PARSE, "unsupported type or malformed json config file");

    // Reset the structures for the next test
    json_shmem = geopm::make_unique<MockSharedMemoryUser>(shmem_size);
    data = (struct geopm_manager_shmem_s *) json_shmem->pointer();

    data->is_updated = false; // This will force the parsing logic to throw since the structure is "not updated".
    ManagerIO::setup_mutex(data->lock);
    data->json_size = m_valid_json_bad_type.size();
    strncpy(data->json_str, m_valid_json_bad_type.c_str(), m_valid_json_bad_type.size());

    GEOPM_EXPECT_THROW_MESSAGE(new ManagerIOSampler("/BULLSHIT", std::move(json_shmem)),
                               GEOPM_ERROR_INVALID, "reread of shm region requested before update");
}

TEST_F(ManagerIOSamplerTest, negative_shm_setup_mutex)
{
    // This test requires PTHREAD_MUTEX_ERRORCHECK
    size_t shmem_size = sizeof(struct geopm_manager_shmem_s);
    std::unique_ptr<MockSharedMemoryUser> json_shmem(new MockSharedMemoryUser(shmem_size));
    struct geopm_manager_shmem_s *data = (struct geopm_manager_shmem_s *) json_shmem->pointer();
    *data = {};

    // Build the data
    data->is_updated = true;
    ManagerIO::setup_mutex(data->lock);
    (void) pthread_mutex_lock(&data->lock); // Force pthread_mutex_lock to puke by trying to lock a locked mutex.
    data->json_size = m_valid_json_bad_type.size();
    strncpy(data->json_str, m_valid_json_bad_type.c_str(), m_valid_json_bad_type.size());

    GEOPM_EXPECT_THROW_MESSAGE(new ManagerIOSampler("/BULLSHIT", std::move(json_shmem)),
                               EDEADLK, "Resource deadlock avoided");
}

TEST_F(ManagerIOSamplerTest, negative_parse_bad_json_shm)
{
    size_t shmem_size = sizeof(struct geopm_manager_shmem_s);
    std::unique_ptr<MockSharedMemoryUser> json_shmem(new MockSharedMemoryUser(shmem_size));
    struct geopm_manager_shmem_s *data = (struct geopm_manager_shmem_s *) json_shmem->pointer();

    // Build the data
    data->is_updated = true;
    ManagerIO::setup_mutex(data->lock);
    data->json_size = 1; // Make the size incorrect to force the Json parser to puke.
    strncpy(data->json_str, m_valid_json_bad_type.c_str(), m_valid_json_bad_type.size());

    GEOPM_EXPECT_THROW_MESSAGE(new ManagerIOSampler("/BULLSHIT", std::move(json_shmem)),
                               GEOPM_ERROR_FILE_PARSE, "detected a malformed json config file: unexpected end of input");
}

TEST_F(ManagerIOSamplerTest, get_json_str)
{
    std::string err;
    ManagerIOSampler gp(m_json_file_path);
    Json root = Json::parse(m_valid_json, err);
    EXPECT_EQ(root.dump(), gp.json_str());
}

TEST_F(ManagerIOSamplerTest, negative_bad_files)
{
    std::string path ("ManagerIOSamplerTest_empty");
    std::ofstream empty_file(path, std::ofstream::out);
    empty_file.close();
    GEOPM_EXPECT_THROW_MESSAGE(new ManagerIOSampler(path), GEOPM_ERROR_INVALID, "input configuration file invalid");
    chmod(path.c_str(), 0);
    GEOPM_EXPECT_THROW_MESSAGE(new ManagerIOSampler(path),
                               GEOPM_ERROR_INVALID, "input configuration file \"" + path + "\" could not be opened");
    std::remove(path.c_str());
}


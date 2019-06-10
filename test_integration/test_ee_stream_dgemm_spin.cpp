/*
 * Copyright (c) 2015, 2016, 2017, 2018, 2019, Intel Corporation
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
#include <limits.h>
#include <mpi.h>
#include <string>
#include <vector>
#include <memory>

#include "geopm.h"
#include "Exception.hpp"
#include "ModelRegion.hpp"

static bool get_env(const std::string &name, std::string &env_string)
{
    bool result = false;
    char *check_string = getenv(name.c_str());
    if (check_string != NULL) {
        if (strlen(check_string) > NAME_MAX) {
            throw geopm::Exception("Environment variable too long",
                            GEOPM_ERROR_INVALID, __FILE__, __LINE__);
        }
        env_string = check_string;
        result = true;
    }
    return result;
}

int main(int argc, char **argv)
{
    int err = 0;
    int comm_rank;
    int comm_size;
    MPI_Init(&argc, &argv);
    MPI_Comm_size(MPI_COMM_WORLD, &comm_size);
    MPI_Comm_rank(MPI_COMM_WORLD, &comm_rank);
    bool is_verbose = false;
    if (comm_rank == 0) {
        for (int arg_idx = 1; arg_idx < argc; ++arg_idx) {
            if (strncmp(argv[arg_idx], "--verbose", strlen("--verbose")) == 0 ||
                strncmp(argv[arg_idx], "-v", strlen("-v")) == 0) {
                is_verbose = true;
            }
        }
    }

    uint64_t stream_region_id = 0;
    std::unique_ptr<geopm::ModelRegionBase> stream_model(geopm::model_region_factory("stream", 1.35, is_verbose));
    err = geopm_prof_region("stream", GEOPM_REGION_HINT_UNKNOWN, &stream_region_id);
    if (err) {
        throw geopm::Exception("test_ee_stream_dgemm_spin", err, __FILE__, __LINE__);
    }

    uint64_t dgemm_region_id = 0;
    std::unique_ptr<geopm::ModelRegionBase> dgemm_model(geopm::model_region_factory("dgemm", 20.0, is_verbose));
    err = geopm_prof_region("dgemm", GEOPM_REGION_HINT_UNKNOWN, &dgemm_region_id);
    if (err) {
        throw geopm::Exception("test_ee_stream_dgemm_spin", err, __FILE__, __LINE__);
    }

    std::unique_ptr<geopm::ModelRegionBase> spin_model(geopm::model_region_factory("spin", 0.50, is_verbose));
    uint64_t spin_region_id = 0;
    err = geopm_prof_region("spin", GEOPM_REGION_HINT_UNKNOWN, &spin_region_id);
    if (err) {
        throw geopm::Exception("test_ee_stream_dgemm_spin", err, __FILE__, __LINE__);
    }

    int repeat;
    std::string iterations;
    if (get_env("TEST_ITERATIONS", iterations)) {
        repeat = std::stoi(iterations);
    }
    else {
        repeat = 10;
    }

    for (int rep_idx = 0; rep_idx != repeat; ++rep_idx) {
        err = geopm_prof_enter(stream_region_id);
        if (err) {
            throw geopm::Exception("test_ee_stream_dgemm_spin", err, __FILE__, __LINE__);
        }
        stream_model->run();
        err = geopm_prof_exit(stream_region_id);
        if (err) {
            throw geopm::Exception("test_ee_stream_dgemm_spin", err, __FILE__, __LINE__);
        }

        err = geopm_prof_enter(dgemm_region_id);
        if (err) {
            throw geopm::Exception("test_ee_stream_dgemm_spin", err, __FILE__, __LINE__);
        }
        dgemm_model->run();
        err = geopm_prof_exit(dgemm_region_id);
        if (err) {
            throw geopm::Exception("test_ee_stream_dgemm_spin", err, __FILE__, __LINE__);
        }

        err = geopm_prof_enter(spin_region_id);
        if (err) {
            throw geopm::Exception("test_ee_stream_dgemm_spin", err, __FILE__, __LINE__);
        }
        spin_model->run();
        err = geopm_prof_exit(spin_region_id);
        if (err) {
            throw geopm::Exception("test_ee_stream_dgemm_spin", err, __FILE__, __LINE__);
        }

        MPI_Barrier(MPI_COMM_WORLD);
    }

    MPI_Finalize();
    return err;
}

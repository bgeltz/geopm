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

int main(int argc, char **argv)
{
    int err = 0;
    int comm_rank;
    int comm_size;
    MPI_Init(&argc, &argv);
    MPI_Comm_size(MPI_COMM_WORLD, &comm_size);
    MPI_Comm_rank(MPI_COMM_WORLD, &comm_rank);

    uint64_t stream_region_id = 0;
    uint64_t dgemm_region_id = 0;
    uint64_t spin_region_id = 0;

    geopm_prof_region("stream", GEOPM_REGION_HINT_UNKNOWN, &stream_region_id);
    geopm_prof_region("dgemm", GEOPM_REGION_HINT_UNKNOWN, &dgemm_region_id);
    geopm_prof_region("spin", GEOPM_REGION_HINT_UNKNOWN, &spin_region_id);

    // Add artifical imbalance to one node; assumes 4 app ranks per node
    double imbalance = 0.0;
    if (argc > 1 && strcmp(argv[1], "--imbalance") == 0) {
        if (comm_rank < 4) {
            imbalance = 0.3;
        }
    }

    std::unique_ptr<geopm::ModelRegionBase> stream_model(geopm::model_region_factory("stream", 1.35 + imbalance, true));
    std::unique_ptr<geopm::ModelRegionBase> dgemm_model(geopm::model_region_factory("dgemm", 20.0 + 20*imbalance, true));
    std::unique_ptr<geopm::ModelRegionBase> spin_model(geopm::model_region_factory("spin", 0.50 + imbalance, true));

    int repeat = 200;

    for (int rep_idx = 0; rep_idx != repeat; ++rep_idx) {
        geopm_prof_epoch();

        geopm_prof_enter(stream_region_id);
        stream_model->run();
        geopm_prof_exit(stream_region_id);

        geopm_prof_enter(dgemm_region_id);
        dgemm_model->run();
        geopm_prof_exit(dgemm_region_id);

        geopm_prof_enter(spin_region_id);
        spin_model->run();
        geopm_prof_exit(spin_region_id);

        MPI_Barrier(MPI_COMM_WORLD);
    }

    MPI_Finalize();
    return err;
}

/*
 * Copyright (c) 2015, 2016, 2017, Intel Corporation
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

#include <stdlib.h>
#include <iostream>
#include <map>

#include "gtest/gtest.h"
#include "geopm_error.h"
#include "Exception.hpp"
#include "DeciderFactory.hpp"
#include "GoverningDecider.hpp"
#include "Decider.hpp"
#include "SimpleFreqDecider.hpp"
#include "Region.hpp"
#include "Policy.hpp"
#include "geopm.h"


class SimpleFreqDeciderTest: public :: testing :: Test
{
    protected:
    void SetUp();
    void TearDown();
    void run_param_case(double min_freq, double max_freq, double curr_freq, int num_sockets, uint64_t hint);
    geopm::IDecider *m_decider;
    geopm::DeciderFactory *m_fact;
};

void SimpleFreqDeciderTest::SetUp()
{
    setenv("GEOPM_PLUGIN_PATH", ".libs/", 1);
    m_fact = new geopm::DeciderFactory();
    m_decider = NULL;
    m_decider = m_fact->decider("simple_freq");
}

void SimpleFreqDeciderTest::TearDown()
{
    if (m_decider) {
        delete m_decider;
    }
    if (m_fact) {
        delete m_fact;
    }
}

/// @todo: Add test where domains have imbalanced power consumption.

TEST_F(SimpleFreqDeciderTest, decider_is_supported)
{
    EXPECT_TRUE(m_decider->decider_supported("simple_freq"));
    EXPECT_FALSE(m_decider->decider_supported("bad_string"));
}

TEST_F(SimpleFreqDeciderTest, name)
{
    EXPECT_TRUE(std::string("simple_freq") == m_decider->name());
}

TEST_F(SimpleFreqDeciderTest, clone)
{
    geopm::IDecider *cloned = m_decider->clone();
    EXPECT_TRUE(std::string("simple_freq") == cloned->name());
    delete cloned;
}

TEST_F(SimpleFreqDeciderTest, 1_socket_under_budget)
{
    run_param_case(1 ,1300000, 800000 , 1, GEOPM_REGION_HINT_UNKNOWN );
}

void SimpleFreqDeciderTest::run_param_case(double min_freq, double max_freq, double curr_freq, int num_sockets, uint64_t hint)
{

    //GoverningDeciderTest Should still hold.
    //TODO add SimpleFreqDeciderTest!
}

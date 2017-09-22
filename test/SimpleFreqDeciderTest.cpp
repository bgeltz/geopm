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
#include "gmock/gmock.h"
#include "geopm_error.h"
#include "Exception.hpp"
#include "DeciderFactory.hpp"

#include "Decider.hpp"
#include "GoverningDecider.hpp"
#include "SimpleFreqDecider.hpp"

#include "Region.hpp"
#include "MockRegion.hpp"
#include "Policy.hpp"
#include "MockPolicy.hpp"
#include "geopm.h"

using  ::testing::_;
using  ::testing::AtLeast;
using  ::testing::Matcher;
using  ::testing::Each;
using  ::testing::SizeIs;
using  ::testing::Pointwise;
using  ::testing::ContainerEq;

class SimpleFreqDeciderTest: public :: testing :: Test
{
    protected:
        void SetUp();
        void TearDown();
        void run_param_case(double min_freq, double max_freq, double curr_freq, int num_sockets, uint64_t hint);
        geopm::IDecider *m_decider;
        geopm::DeciderFactory *m_fact;
        geopm::MockIRegion *m_mockregion;
        geopm::MockIPolicy *m_mockpolicy;
    private:
        void setup_MockRegion(uint64_t hint);
        void setup_MockPolicy(int num_domain, double target_freq);
};

void SimpleFreqDeciderTest::SetUp()
{
    setenv("GEOPM_PLUGIN_PATH", ".libs/", 1);
    m_fact = new geopm::DeciderFactory();
    m_decider = NULL;
    m_decider = m_fact->decider("simple_freq");
    m_mockregion = new geopm::MockIRegion();
    m_mockpolicy = new geopm::MockIPolicy();
}

void SimpleFreqDeciderTest::TearDown()
{
    if (m_decider) {
        delete m_decider;
    }
    if (m_fact) {
        delete m_fact;
    }
    if (m_mockregion) {
        delete m_mockregion;
    }
    if (m_mockpolicy) {
        delete m_mockpolicy;
    }
}

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


TEST_F(SimpleFreqDeciderTest, hint_mock)
{
    run_param_case(1 ,1300000, 800000 , 1, 1&0xfffffff00000000ULL);
}


TEST_F(SimpleFreqDeciderTest, hint_compute)
{
    run_param_case(1 ,1300000, 800000 , 1, GEOPM_REGION_HINT_COMPUTE );
}

TEST_F(SimpleFreqDeciderTest, 8_domains)
{
    run_param_case(1 ,1300000, 800000 , 8, GEOPM_REGION_HINT_COMPUTE );
}

TEST_F(SimpleFreqDeciderTest, hint_serial)
{
    run_param_case(1 ,1300000, 800000 , 1, GEOPM_REGION_HINT_SERIAL);
}

TEST_F(SimpleFreqDeciderTest, hint_parallel)
{
    run_param_case(1 ,1300000, 800000 , 1, GEOPM_REGION_HINT_PARALLEL);
}


TEST_F(SimpleFreqDeciderTest, hint_memory)
{
    run_param_case(1 ,1300000, 800000 , 1, GEOPM_REGION_HINT_MEMORY);
}


TEST_F(SimpleFreqDeciderTest, hint_network)
{
    run_param_case(1 ,1300000, 800000 , 1, GEOPM_REGION_HINT_NETWORK);
}

TEST_F(SimpleFreqDeciderTest, hint_io)
{
    run_param_case(1 ,1300000, 800000 , 1, GEOPM_REGION_HINT_IO);
}

TEST_F(SimpleFreqDeciderTest, hint_unknown)
{
    run_param_case(1 ,1300000, 800000 , 1, GEOPM_REGION_HINT_UNKNOWN);
}

TEST_F(SimpleFreqDeciderTest, hint_ignore)
{
    run_param_case(1 ,1300000, 800000 , 1, GEOPM_REGION_HINT_IGNORE);
}

void SimpleFreqDeciderTest::setup_MockRegion(uint64_t hint){
    EXPECT_CALL(*m_mockregion,hint())
        .Times(AtLeast(1))
        .WillRepeatedly(testing::Return(hint));
}
void SimpleFreqDeciderTest::setup_MockPolicy(int num_domain, double target_freq){
    //Write EXPECT_CALL that tests if ctl_cpu_freq was called with the right frequency (target_freq)
    std::vector<double> freq_vector(num_domain,target_freq);
    EXPECT_CALL(*m_mockpolicy,ctl_cpu_freq(
        _)) //Works but can't verify what should be tested.
//        Matcher<std::vector<double>>(Each(target_freq))))    
//        Matcher<std::vector<double>>(ContainerEq(freq_vector)))) //This should work... ask Brandon ;)
//        Matcher<std::vector<double>>(Pointwise(num_domain,freq_vector))))
        .Times(AtLeast(1))
        ;
}

void SimpleFreqDeciderTest::run_param_case(double min_freq, double max_freq, double curr_freq, int num_domain, uint64_t hint)
{
    // SimpleFreqDecider is expected to
    // 1: call update_policy of the inheritted GoverningDecider (Not testible?)
    // 2: get the hint region
    // 3: set the freqeuncy according to the hint.

    // Thus setup m_mockregion so that the hint passed will be returned for the decider.
    setup_MockRegion(hint);

    // ,choose the right frequency according to the hint.
    double target_freq;
    switch( hint )
    {
        case GEOPM_REGION_HINT_COMPUTE:
        case GEOPM_REGION_HINT_SERIAL:
        case GEOPM_REGION_HINT_PARALLEL:
            target_freq=max_freq;
            break; 
        case GEOPM_REGION_HINT_MEMORY:
        case GEOPM_REGION_HINT_NETWORK:
        case GEOPM_REGION_HINT_IO:
            target_freq=min_freq;
            break; 
        case GEOPM_REGION_HINT_UNKNOWN:
        case GEOPM_REGION_HINT_IGNORE:
            target_freq=curr_freq;
        default:
            break; 
    }
    // And setup m_mockpolicy so that the function ctl_cpu_freq is called with frequency selected  
    setup_MockPolicy(num_domain, target_freq);

    // Finally call update policy for the decider and see if everything was done alright.
    m_decider->update_policy(*m_mockregion,*m_mockpolicy);
    // No ExPECT_'s follow since only side effects are visible.

}

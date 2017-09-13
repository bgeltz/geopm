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
#include "geopm.h"


class SimpleFreqDeciderTest: public :: testing :: Test
{
    protected:
    void SetUp();
    void TearDown();
    void run_param_case(double min_freq, double max_freq, double curr_freq, int num_sockets, uint64_t hint);
    geopm::IDecider *m_decider;
    geopm::DeciderFactory *m_fact;
    MockRegion *mockregion;
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

//TEST_F(SimpleFreqDeciderTest, 1_socket_under_budget)
//{
//    run_param_case(1 ,1300000, 800000 , 1, GEOPM_REGION_HINT_UNKNOWN );
//}

TEST_F(SimpleFreqDeciderTest, hint_mock)
{
    run_param_case(1 ,1300000, 800000 , 1, 1&0xfffffff00000000ULL);
}


TEST_F(SimpleFreqDeciderTest, hint_compute)
{
    run_param_case(1 ,1300000, 800000 , 1, GEOPM_REGION_HINT_COMPUTE );
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


void SimpleFreqDeciderTest::run_param_case(double min_freq, double max_freq, double curr_freq, int num_domain, uint64_t hint)
{
    const int region_id = 1;
    
    geopm::Region region(region_id, num_domain, 0,NULL); 
    geopm::Policy policy(num_domain);


    struct geopm_policy_message_s policy_msg = {GEOPM_POLICY_MODE_DYNAMIC, 0, 1, 165.0};
    m_decider->update_policy(policy_msg,policy);

    //This tests all the switch case functionality! but not if frequency is set correctly! This should be moved to Region test.
    EXPECT_EQ (region.hint() , hint);

    std::vector<double> freq_vec_comparison(num_domain, -1.0 );

    switch( region.hint())
    {
    case GEOPM_REGION_HINT_COMPUTE:
    case GEOPM_REGION_HINT_SERIAL:
    case GEOPM_REGION_HINT_PARALLEL:
        std::fill(freq_vec_comparison.begin(),freq_vec_comparison.end(),max_freq);
//         for 
//        EXPECT_DOUBLE_EQ(freq, max_freq);// member not accessible from outside!
//        EXPECT_DOUBLE_EQ(m_decider->m_max_freq,max_freq);
        break; 
    case GEOPM_REGION_HINT_MEMORY:
    case GEOPM_REGION_HINT_NETWORK:
    case GEOPM_REGION_HINT_IO:
        std::fill(freq_vec_comparison.begin(),freq_vec_comparison.end(),min_freq);
//        EXPECT_DOUBLE_EQ(4.5,min_freq);
//        EXPECT_DOUBLE_EQ(m_min_freq,min_freq);
        break; 
    case GEOPM_REGION_HINT_UNKNOWN:
    case GEOPM_REGION_HINT_IGNORE:
    default:
        break; 
    }

    for( unsigned int i=0;i<freq_vec_comparison.size();i++)
    {
//        EXCPECT_DOUBLE_EQ(freq_vec_comparison[i],freq_vec[i]);
        ;;
    }
    
    MockRegion mockregion(); // currently not used. //region_id, num_domain, 0,NULL); 
//    EXPECT_CALL(mockregion,hint());

    
//    mockregion = new MockRegion();// mockregion();//    region.hint
//    MockRegion trueregion(region_id,num_domain,0,NULL);
    
    //EXPECT_EQ (mockregion.hint() , hint);
    //EXPECT_CALL(*mockregion,hint());
            
//            EQ (mockregion.hint() , hint);
    
//    m_decider->
//    EXPECT_EQ (m_decider->name(),"power_governing");
//    std::cout << m_decider->IDecider->m_max_freq << '\n';
//
//
//
//        EXPECT_EQ(1,2);
//        EXPECT_NE();
//        EXPECT_NEAR();
//        EXPECT_TRUE();
//        EXPECT_FALSE();
//        EXPECT_DOUBLE_EQ();
//        EXPECT_THROW();
//        EXPECT_DOUBLE_NE();


    //GoverningDeciderTest Should still hold.
    //TODO add SimpleFreqDeciderTest!
}

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

#ifndef SIMPLE_FREQ_HPP_INCLUDE
#define SIMPLE_FREQ_HPP_INCLUDE

#include "Decider.hpp"
#include "geopm_plugin.h"

namespace geopm
{

    /// @brief Simple implementation of a binary frequency decider.
    /// 
    /// This frequency decider uses the geopm_hint interface to determine 
    /// wether we are in a compute or memory bound region and choose 
    /// the maximum frequency and a fraction of the minimal possible frequency 
    /// repsectively. 
    /// 
    /// This is a leaf decider.
    class SimpleFreq : public Decider
    {
        public:
            /// @ brief SimpleFreq default constructor.
            SimpleFreq();
            SimpleFreq(const SimpleFreq &other);
            /// @brief BalancinDecider destructor, virtual.
            virtual ~SimpleFreq();
            virtual IDecider *clone(void) const;
            virtual void bound(double upper_bound, double lower_bound);
            virtual bool update_policy(const struct geopm_policy_message_s &policy_msg, IPolicy &curr_policy);
            virtual bool update_policy(IRegion &curr_region, IPolicy &curr_policy);
            virtual bool decider_supported(const std::string &descripton);
            virtual const std::string& name(void) const;
        private:
            const std::string m_name;
            double m_last_freq;
            double m_min_freq;
            double m_max_freq;
            unsigned int m_num_cores;

    };
}

#endif

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

#include <hwloc.h>
#include <algorithm>
#include <thread>

#include "geopm.h"
#include "geopm_message.h"
#include "geopm_plugin.h"

#include "SimpleFreqDecider.hpp"
#include "GoverningDecider.hpp"
#include "Exception.hpp"
#include <fstream>
#include <string>
#include <cmath>

#include "Region.hpp"

#include <iostream>
#include <stdlib.h>

int geopm_plugin_register(int plugin_type, struct geopm_factory_c *factory, void *dl_ptr)
{
    int err = 0;

    try {
        if (plugin_type == GEOPM_PLUGIN_TYPE_DECIDER) {
            geopm::IDecider *decider = new geopm::SimpleFreqDecider;
            geopm_factory_register(factory, decider, dl_ptr);
        }
    }
    catch (...) {
        err = geopm::exception_handler(std::current_exception());
    }

    return err;
}

double max_freq()  //This should be read from MSR/CSR not cpuinfo!
{
    const char* env_cpu_freq_max_hz = getenv("GEOPM_SIMPLE_FREQ_MAX");
    if (env_cpu_freq_max_hz){
        return std::stod(env_cpu_freq_max_hz);
    }

    std::string s1;
    double out;
    std::ifstream cpuinfoFile("/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq");
    if (cpuinfoFile.is_open()) {
        getline(cpuinfoFile,s1); // in KHz
        out = std::stod(s1) * 1e3; // in Hz
    }
    cpuinfoFile.close();
    return out;
}

double min_freq()
{
    const char* env_cpu_freq_min_hz = getenv("GEOPM_SIMPLE_FREQ_MIN");
    if(env_cpu_freq_min_hz){
        return std::stod(env_cpu_freq_min_hz);
    }

    std::string s1;
    double out;
    std::ifstream cpuinfoFile("/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_min_freq");
    if (cpuinfoFile.is_open()) {
        getline(cpuinfoFile,s1); // in KHz
        out = std::stod(s1) * 1e3; // in Hz
    }
    cpuinfoFile.close();
    return out; // These are absolute min values possible
    // This is not the desireable for efficiency.
}

double current_freq()
{
    // Use as soon as msr_read is working and return: return (max_freq() * aperf / mperf);
    // double aperf = 40000;//msr_read(GEOPM_DOMAIN_CPU,0,IA32_APERF;//msr
    // double mperf = 30000;//msr_read(GEOPM_DOMAIN_CPU,0,IA32_MPERF;//msr
    // return (max_freq() * aperf / mperf);
    return max_freq();
}

namespace geopm
{
    void ctl_cpu_freq(std::vector<double> freq);

    SimpleFreqDecider::SimpleFreqDecider()
        : GoverningDecider()
        , m_last_freq(NAN)
        , m_min_freq(min_freq())
        , m_max_freq(max_freq())
        , m_num_cores(std::thread::hardware_concurrency()) // Logical cores! //check if ok or physical cores needed.
    {
        m_name = "simple_freq";
    }

    SimpleFreqDecider::SimpleFreqDecider(const SimpleFreqDecider &other)
        : GoverningDecider(other)
        , m_last_freq(other.m_last_freq)
        , m_min_freq(other.m_min_freq)
        , m_max_freq(other.m_max_freq)
        , m_num_cores(other.m_num_cores)
    {

    }

    SimpleFreqDecider::~SimpleFreqDecider()
    {

    }

    IDecider *SimpleFreqDecider::clone(void) const
    {
        return (IDecider*)(new SimpleFreqDecider(*this));
    }

    bool SimpleFreqDecider::update_policy(IRegion &curr_region, IPolicy &curr_policy)
    {
        // Never receiving a new policy power budget via geopm_policy_message_s, since we set according to frequencies, not policy.
        bool is_updated = false;
        is_updated = GoverningDecider::update_policy(curr_region, curr_policy);

        double freq=m_last_freq;
        switch(curr_region.hint()) {

            // Hints for low CPU frequency
            case GEOPM_REGION_HINT_MEMORY:
            case GEOPM_REGION_HINT_NETWORK:
            case GEOPM_REGION_HINT_IO:
                freq=m_min_freq;
                break;

            // Hints for maximum CPU frequency
            case GEOPM_REGION_HINT_COMPUTE:
            case GEOPM_REGION_HINT_SERIAL:
            case GEOPM_REGION_HINT_PARALLEL:
                freq=m_max_freq;
                break;
            // Hint Inconclusive
            //case GEOPM_REGION_HINT_UNKNOWN:
            //case GEOPM_REGION_HINT_IGNORE:
            default:
                freq=m_min_freq;
                break;
        }

        if (freq != m_last_freq) {
            std::cout << "Hint = " << curr_region.hint() << "\n";
            std::cout << "Freq = " << freq << "\n";
            std::vector<double> freq_vec(m_num_cores, freq);

            curr_policy.ctl_cpu_freq(freq_vec);
            m_last_freq = freq;
        }

        // Don't do anything since we never get a new policy.
        return is_updated;
    }
}

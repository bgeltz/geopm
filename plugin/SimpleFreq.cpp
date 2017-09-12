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
//#include "geopm_ctl.h"

#include "SimpleFreq.hpp"
#include "Exception.hpp"
#include <fstream>
#include <string>

#include "Region.hpp"

//#include <iostream>
//#include "MSRIO.hpp"
//#include "Platform.hpp"
//#include "PlatformTopology.hpp"

int geopm_plugin_register(int plugin_type, struct geopm_factory_c *factory, void *dl_ptr)
{
    int err = 0;

    try {
        if (plugin_type == GEOPM_PLUGIN_TYPE_DECIDER) {
            geopm::IDecider *decider = new geopm::SimpleFreq;
            geopm_factory_register(factory, decider, dl_ptr);
        }
    }
    catch(...) {
        err = geopm::exception_handler(std::current_exception());
    }

    return err;
}

double max_freq(){ //This should be read from MSR/CSR not cpuinfo!
  std::string s1;
  std::string s2="model name";
  double out;
  std::ifstream cpuinfoFile("/proc/cpuinfo");
  if (cpuinfoFile.is_open()){
    while(!cpuinfoFile.eof()){
      getline(cpuinfoFile,s1);
      if(s1.find(s2) != std::string::npos ){
        s2=s1.substr(s1.find("@")+1);
        s1=s2.substr(0,s2.find("GHz"));
        out = std::stod(s1)*1000000;
        break;
      }
    }
  }
  cpuinfoFile.close();
  return out;
}

double min_freq(){
  return(800000);//check
}
double current_freq(){
  double aperf=40000;//msr_read(GEOPM_DOMAIN_CPU,0,IA32_APERF;//msr
  double mperf=30000;//msr_read(GEOPM_DOMAIN_CPU,0,IA32_MPERF;//msr
  return (max_freq()*aperf/mperf);
}

namespace geopm
{
    void ctl_cpu_freq(std::vector<double> freq);

    SimpleFreq::SimpleFreq()
        : m_name("simple_freq")
        , m_last_freq(current_freq())
        , m_min_freq(min_freq())
        , m_max_freq(max_freq())
        , m_num_cores(std::thread::hardware_concurrency()) // Logical cores! //check if ok or physical cores needed.
    {

    }

    SimpleFreq::SimpleFreq(const SimpleFreq &other)
        : Decider(other)
        , m_name(other.m_name)
        , m_last_freq(other.m_last_freq)
        , m_min_freq(other.m_min_freq)
        , m_max_freq(other.m_max_freq)
        , m_num_cores(other.m_num_cores)
    {

    }

    SimpleFreq::~SimpleFreq()
    {

    }

    IDecider *SimpleFreq::clone(void) const
    {
        return (IDecider*)(new SimpleFreq(*this));
    }

    bool SimpleFreq::decider_supported(const std::string &description)
    {
        return (description == m_name);
    }

    const std::string& SimpleFreq::name(void) const
    {
        return m_name;
    }

    //For Frequency this is p-state bound accroding to Reference. Should this be actual frequencies? (max/min?)
    void SimpleFreq::bound(double upper_bound, double lower_bound)
    {
        m_upper_bound = upper_bound ;
        //m_max_freq=upper_bound;
        m_lower_bound = lower_bound ;
        //m_min_freq=lower_bound;
    }

    bool SimpleFreq::update_policy(const struct geopm_policy_message_s &policy_msg, IPolicy &curr_policy)
    {
      // Never receiving a new power budget via geopm_policy_message_s, since we set according to frequencies.
        bool result = false;
        return result;
    }

    bool SimpleFreq::update_policy(IRegion &curr_region, IPolicy &curr_policy)
    {
        // Never receiving a new policy power budget via geopm_policy_message_s, since we set according to frequencies, not policy.
        bool is_updated = false;
        double freq=m_last_freq;
        switch(curr_region.hint())
        {
          case GEOPM_REGION_HINT_UNKNOWN:
            break;
          case GEOPM_REGION_HINT_COMPUTE:
            freq=m_max_freq;
            break;
          case GEOPM_REGION_HINT_MEMORY:
            freq=m_min_freq;
            break;
          case GEOPM_REGION_HINT_NETWORK:
            freq=m_min_freq;
            break;
          case GEOPM_REGION_HINT_IO:
            freq=m_min_freq;
            break;
          case GEOPM_REGION_HINT_SERIAL:
            freq=m_max_freq;
            break;
          case GEOPM_REGION_HINT_PARALLEL:
            freq=m_max_freq;
            break;
          case GEOPM_REGION_HINT_IGNORE:
            break;
          default: break;
        }

        if ( freq != m_last_freq){
          std::vector<double> freq_vec(m_num_cores, freq);
          geopm::ctl_cpu_freq(freq_vec);
          is_updated = true; //This is irrelevant since only power is traversed up or down the tree.
        }


        // Don't do anything since we never get a new policy.
        return is_updated;
    }
}

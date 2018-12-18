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

#ifndef STATICPOLICYDECIDER_HPP_INCLUDE
#define STATICPOLICYDECIDER_HPP_INCLUDE

#include "Decider.hpp"

namespace geopm
{
    /// @brief Decider which does not update the policy.
    ///
    /// Useful for running geopm as a profile only tool.  When using
    /// this decider at the leaf or tree level, policy will never be
    /// updated and therefore never enforced.
    class StaticPolicyDecider : public Decider
    {
        public:
            /// @brief StaticPolicyDecider default constructor.
            StaticPolicyDecider();
            StaticPolicyDecider(const StaticPolicyDecider &other) = delete;
            StaticPolicyDecider &operator=(const StaticPolicyDecider &other) = delete;
            /// @brief StaticPolicyDecider destructor, virtual.
            virtual ~StaticPolicyDecider() = default;
            virtual bool update_policy(IRegion &curr_region, IPolicy &curr_policy) override;
            virtual bool decider_supported(const std::string &descripton) override;
            virtual const std::string& name(void) const override;
            static std::string plugin_name(void);
            static std::unique_ptr<IDecider> make_plugin(void);
        private:
            const std::string m_name;
    };
}

#endif
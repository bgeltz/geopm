/*
 * Copyright (c) 2015 - 2023, Intel Corporation
 * SPDX-License-Identifier: BSD-3-Clause
 */

#ifndef MOCKIOGROUP_HPP_INCLUDE
#define MOCKIOGROUP_HPP_INCLUDE

#include "gmock/gmock.h"

#include "geopm/IOGroup.hpp"

class MockIOGroup : public geopm::IOGroup
{
    public:
        MOCK_METHOD(std::set<std::string>, signal_names, (), (const, override));
        MOCK_METHOD(std::set<std::string>, control_names, (), (const, override));
        MOCK_METHOD(bool, is_valid_signal, (const std::string &signal_name),
                    (const, override));
        MOCK_METHOD(bool, is_valid_control, (const std::string &control_name),
                    (const, override));
        MOCK_METHOD(int, signal_domain_type, (const std::string &signal_name),
                    (const, override));
        MOCK_METHOD(int, control_domain_type, (const std::string &control_name),
                    (const, override));
        MOCK_METHOD(int, push_signal,
                    (const std::string &signal_name, int domain_type, int domain_idx),
                    (override));
        MOCK_METHOD(int, push_control,
                    (const std::string &control_name, int domain_type, int domain_idx),
                    (override));
        MOCK_METHOD(void, read_batch, (), (override));
        MOCK_METHOD(void, write_batch, (), (override));
        MOCK_METHOD(double, sample, (int sample_idx), (override));
        MOCK_METHOD(void, adjust, (int control_idx, double setting), (override));
        MOCK_METHOD(double, read_signal,
                    (const std::string &signal_name, int domain_type, int domain_idx),
                    (override));
        MOCK_METHOD(void, write_control,
                    (const std::string &control_name, int domain_type,
                     int domain_idx, double setting),
                    (override));
        MOCK_METHOD(void, save_control, (), (override));
        MOCK_METHOD(void, restore_control, (), (override));
        MOCK_METHOD(void, save_control, (const std::string &save_dir), (override));
        MOCK_METHOD(void, restore_control, (const std::string &save_dir), (override));
        MOCK_METHOD(std::function<double(const std::vector<double> &)>, agg_function,
                    (const std::string &signal_name), (const, override));
        MOCK_METHOD(std::function<std::string(double)>, format_function,
                    (const std::string &signal_name), (const, override));
        MOCK_METHOD(std::string, signal_description,
                    (const std::string &signal_name), (const, override));
        MOCK_METHOD(std::string, control_description,
                    (const std::string &control_name), (const, override));
        MOCK_METHOD(int, signal_behavior, (const std::string &signal_name),
                    (const, override));
        MOCK_METHOD(std::string, name, (),
                    (const, override));
};

#endif

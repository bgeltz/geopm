#!/usr/bin/env python3

#  Copyright (c) 2015 - 2023, Intel Corporation
#  SPDX-License-Identifier: BSD-3-Clause
#

import os
import sys
import unittest
import subprocess

import geopmdpy
import geopmpy.io

import static_agent

class TestStaticAgentStressng(unittest.TestCase):
    def setUp(self):
        self._cpu_power_limit = 150.0
        initial_controls = {'CPU_POWER_LIMIT_CONTROL': self._cpu_power_limit}
        agent = static_agent.StaticAgent(period_seconds=1,
                                         initial_controls=initial_controls)

        controller = geopmdpy.runtime.Controller(agent)

        self._expected_runtime = 10
        # TODO Use integration.experiment import machine to query for the number of CPUs
        app_args = f'stress-ng --cpu 44 --taskset 0-43 --timeout {self._expected_runtime}'.split(' ')
        report = controller.run(app_args, None)

        self._report_name = 'static_agent_stressng.report'
        with open(self._report_name, 'w') as f:
            print(report, file=f)

    def test_report(self):
        report = geopmpy.io.RawReport(self._report_name)
        for host in report.host_names():
            totals = report.raw_totals(host)

            self.assertAlmostEqual(self._expected_runtime, totals['runtime (s)'], delta=0.5)
            self.assertAlmostEqual(self._cpu_power_limit, totals['power (W)'],
                                   delta=self._cpu_power_limit * 0.1)


if __name__ == '__main__':
    unittest.main()

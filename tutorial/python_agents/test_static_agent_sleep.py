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

class TestStaticAgentSleep(unittest.TestCase):
    def setUp(self):
        agent = static_agent.StaticAgent(period_seconds=1)

        controller = geopmdpy.runtime.Controller(agent)

        self._expected_runtime = 10
        app_args = f'sleep {self._expected_runtime}'.split(' ')
        report = controller.run(app_args, None)

        self._report_name = 'static_agent_sleep.report'
        with open(self._report_name, 'w') as f:
            print(report, file=f)

    def test_report(self):
        report = geopmpy.io.RawReport(self._report_name)
        for host in report.host_names():
            totals = report.raw_totals(host)
            self.assertAlmostEqual(self._expected_runtime, totals['runtime (s)'], delta=0.5)


if __name__ == '__main__':
    unittest.main()

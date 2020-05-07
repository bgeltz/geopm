#!/usr/bin/env python
#
#  Copyright (c) 2015, 2016, 2017, 2018, 2019, 2020, Intel Corporation
#
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions
#  are met:
#
#      * Redistributions of source code must retain the above copyright
#        notice, this list of conditions and the following disclaimer.
#
#      * Redistributions in binary form must reproduce the above copyright
#        notice, this list of conditions and the following disclaimer in
#        the documentation and/or other materials provided with the
#        distribution.
#
#      * Neither the name of Intel Corporation nor the names of its
#        contributors may be used to endorse or promote products derived
#        from this software without specific prior written permission.
#
#  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
#  "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
#  LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
#  A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
#  OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
#  SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
#  LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
#  DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
#  THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#  (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY LOG OF THE USE
#  OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#

"""GADGET

"""

import sys
import unittest
import os
import glob
import shutil

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from test_integration import geopm_context
import geopmpy.io
import geopmpy.error

from test_integration import util
if util.do_launch():
    # Note: this import may be moved outside of do_launch if needed to run
    # commands on compute nodes such as geopm_test_launcher.geopmread
    from test_integration import geopm_test_launcher
    geopmpy.error.exc_clear()

class AppConf(object):
    """Class that is used by the test launcher in place of a
    geopmpy.io.BenchConf when running the gadget benchmark.

    """
    def __init__(self):
        # TODO Test that there's something there
        self.default_src_dir = os.path.join(os.getenv('HOME'), 'apps', 'gadget')
        self.gadget_src_dir = os.getenv('GADGET_SRC_DIR', self.default_src_dir)
        input_data = os.getenv('GADGET_INPUT_PATH', '16cubed')
        self.input_data_dir = os.path.join(self.gadget_src_dir, 'ipcc-test-problem', input_data, 'from-snapshot')

        #  bin_path = os.getenv('GADGET_BIN_PATH', None)
        #  if bin_path is None:
        #      raise RuntimeError("Please set GADGET_BIN_PATH to point to the compiled binary.")

        #  return bin_path

    def write(self):
        """Called by the test launcher prior to executing the test application
        to write any files required by the application.

        """
        # Setup execution dir
        self.outdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'gadget')
        try:
            os.mkdir(self.outdir)
        except OSError: # dir already exists
            shutil.rmtree(self.outdir)
            os.mkdir(self.outdir)

        # Symlink all input data
        for ii in os.listdir(self.input_data_dir):
            if ii in ['outdir', 'P-Gadget3']: # Remove work dirs
                continue
            full_path = os.path.join(self.input_data_dir, ii)
            link_path = os.path.join(self.outdir, ii)
            os.symlink(full_path, link_path)

        os.mkdir(os.path.join(self.outdir, 'outdir')) # Runtime output goes here
        os.mkdir(os.path.join(self.outdir, 'P-Gadget3')) # Executable goes here

        # Copy executable binary to execution directory
        binary_path = os.path.join(self.gadget_src_dir, 'P-Gadget3')
        shutil.copy2(binary_path, os.path.join(self.outdir, 'P-Gadget3'))

        # TODO
        #  os.rmdir(self.outdir) # Cleanup belongs somewhere?

        pass

    def get_exec_path(self):
        """Path to benchmark.
           Assumption for GADGET is that CWD is root of outdir
        """
        return os.path.join('.', 'P-Gadget3', 'P-Gadget3')

    def get_exec_args(self):
        """Returns a list of strings representing the command line arguments
        to pass to the test-application for the next run.  This is
        especially useful for tests that execute the test-application
        multiple times.

        """
        return ['./ipcc-test.par', '2']


class TestIntegration_gadget(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Create launcher, execute benchmark and set up class variables.

        """
        sys.stdout.write('(' + os.path.basename(__file__).split('.')[0] +
                         '.' + cls.__name__ + ') ...')
        test_name = 'gadget'
        cls._report_path = 'test_{}.report'.format(test_name)
        cls._trace_path = 'test_{}.trace'.format(test_name)
        cls._image_path = 'test_{}.png'.format(test_name)
        cls._skip_launch = not util.do_launch()
        cls._keep_files = (cls._skip_launch or
                           os.getenv('GEOPM_KEEP_FILES') is not None)
        cls._agent_conf_path = test_name + '-agent-config.json'
        # Clear out exception record for python 2 support
        geopmpy.error.exc_clear()
        if not cls._skip_launch:
            # Set the job size parameters
            num_node = 1
            num_rank = 4
            # TODO threads? 10 per node?
            time_limit = 600
            # Configure the test application
            app_conf = AppConf()
            # Configure the agent
            # Query for the min and sticker frequency and run the
            # energy efficient agent over this range.
            freq_min = geopm_test_launcher.geopmread("CPUINFO::FREQ_MIN board 0")
            freq_sticker = geopm_test_launcher.geopmread("CPUINFO::FREQ_STICKER board 0")
            agent_conf_dict = {'FREQ_MIN':freq_min,
                               'FREQ_MAX':freq_sticker}
            agent_conf = geopmpy.io.AgentConf(cls._agent_conf_path,
                                              'energy_efficient',
                                              agent_conf_dict)
            # Create the test launcher with the above configuration
            launcher = geopm_test_launcher.TestLauncher(app_conf,
                                                        agent_conf,
                                                        cls._report_path,
                                                        cls._trace_path,
                                                        time_limit=time_limit)
            launcher.set_num_node(num_node)
            launcher.set_num_rank(num_rank)
            launcher.write_log(test_name, 'SRC dir = {}'.format(app_conf.gadget_src_dir))
            launcher.write_log(test_name, 'Input dataset = {}'.format(app_conf.input_data_dir))

            # Run the test application
            launcher.run(test_name)

    @classmethod
    def tearDownClass(cls):
        """Clean up any files that may have been created during the test if we
        are not handling an exception and the GEOPM_KEEP_FILES
        environment variable is unset.

        """

        if not cls._keep_files:
            os.unlink(cls._agent_conf_path)
            os.unlink(cls._report_path)
            os.unlink(cls._image_path)
            for tf in glob.glob(cls._trace_path + '.*'):
                os.unlink(tf)

    def tearDown(self):
        if sys.exc_info() != (None, None, None):
            TestIntegration_gadget._keep_files = True

    def test_load_report(self):
        """Test that the report can be loaded

        """
        #  report = geopmpy.io.RawReport(self._report_path)
        self.fail("Make proper failure criteria.")

if __name__ == '__main__':
    # Call do_launch to clear non-pyunit command line option
    util.do_launch()
    unittest.main()

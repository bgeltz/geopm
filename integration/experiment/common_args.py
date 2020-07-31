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

'''
Common command line arguments for experiments.
'''

# TODO:
# - might need argv as an input for testing.  For now, uses sys.argv automatically
# - use of handle_help is a little weird for caller. might back this out if
#   scripts only require one set.  e.g. launch script can provide output_dir to
#   analysis step.  if show_details is desired, have to use other script
# - might want named members instead of forcing caller to use self.args

import sys
import os
import argparse


def shared_args(parser):
    # output should be shared so that launch and analysis use the same location
    parser.add_argument('-o', '--output-dir', dest='output_dir',
                        action='store', default='.',
                        help='location for reports and other output files')
    parser.add_argument('--machine-config', dest='machine_config',
                        action='store', required=True,
                        help='path to the file containing machine hardware limits for launch')


def handle_help(parser):
    ''' Workaround so that multiple parsers can be used in combination. '''
    result = False
    if '-h' in sys.argv or '--help' in sys.argv:
        parser.print_help()
        result = True
    return result


class ExperimentLaunchArgs:
    def __init__(self):
        parser = argparse.ArgumentParser()
        shared_args(parser)
        parser.add_argument('--skip-launch', dest='skip_launch',
                            action='store_true', default=False,
                            help='reuse existing data files; do not launch any jobs')
        parser.add_argument('--nodes', default=1, type=int,
                            help='number of nodes to use for launch')

        do_help = handle_help(parser)
        self.do_help = do_help
        if not do_help:
            self.args, _ = parser.parse_known_args()


class ExperimentAnalysisArgs:
    def __init__(self):
        parser = argparse.ArgumentParser()
        shared_args(parser)
        parser.add_argument('--show-details', dest='show_details',
                            action='store_true', default=False,
                            help='print additional data analysis details')

        do_help = handle_help(parser)
        self.do_help = do_help
        if not do_help:
            self.args, _ = parser.parse_known_args()

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

import sys
import json
import util


class Machine:
    def __init__(self, path):
        self.signals = {}
        self.path = path
        try:
            self.load(path)
        except RuntimeError:
           self.query()
           self.save(path)

    def load(self, config_path):
        try:
            with open(config_path) as fid:
                self.signals = json.load(fid)
        except:
            raise RuntimeError("<geopm> Unable to open machine config {}.".format(config_path))

    def save(self, config_path):
        with open(config_path, 'w') as info_file:
            json.dump(self.signals, info_file)

    def query(self):
        self.signals = {}
        signal_names = ['FREQUENCY_MIN',
                        'FREQUENCY_MAX',
                        'FREQUENCY_STICKER',
                        'FREQUENCY_STEP',
                        'POWER_PACKAGE_MIN',
                        'POWER_PACKAGE_TDP',
                        'POWER_PACKAGE_MAX']
        for sn in signal_names:
            self.signals[sn] = util.geopmread('{} board 0'.format(sn))

    def signals(self):
        return dict(self.signals)

    def frequency_min(self):
        return self.signals['FREQUENCY_MIN']

    def frequency_max(self):
        return self.signals['FREQUENCY_MAX']

    def frequency_sticker(self):
        return self.signals['FREQUENCY_STICKER']

    def frequency_step(self):
        return self.signals['FREQUENCY_STEP']

    def power_package_min(self):
        return self.signals['POWER_PACKAGE_MIN']

    def power_package_tdp(self):
        return self.signals['POWER_PACKAGE_TDP']

    def power_package_max(self):
        return self.signals['POWER_PACKAGE_MAX']


if __name__ == '__main__':
    usage = """\
Usage: {} machine_file
    machine_file: Output JSON file with machine specification

""".format(sys.argv[0])

    if len(sys.argv) != 2 or sys.argv[1] in ('-h', '--help'):
        sys.stderr.write(usage)
    else:
        outfile = sys.argv[1]
        Machine(outfile)

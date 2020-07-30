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

'''
Shows balancer chosen power limits on each socket over time.
'''

import pandas
import matplotlib.pyplot as plt
import sys

if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.stderr.write('Provide name of trace file')
        sys.exit(1)

    for path in sys.argv[1:]:
        node_num = int(path.split('mcfly')[1])
        df = pandas.read_csv(path, delimiter='|', comment='#')
        time = df['TIME']
        pl0 = df['MSR::PKG_POWER_LIMIT:PL1_POWER_LIMIT-package-0']
        pl1 = df['MSR::PKG_POWER_LIMIT:PL1_POWER_LIMIT-package-1']
        rt0 = df['EPOCH_RUNTIME-package-0'] - df['EPOCH_RUNTIME_NETWORK-package-0']
        rt1 = df['EPOCH_RUNTIME-package-1'] - df['EPOCH_RUNTIME_NETWORK-package-1']
        tgt = df['POLICY_MAX_EPOCH_RUNTIME']
        plt.subplot(2, 1, 1)
        ply.xlim((50, 100))
        plt.plot(time, pl0, label='limit-0-mf{}'.format(node_num))
        plt.plot(time, pl1, label='limit-1-mf{}'.format(node_num))
        plt.title('Per socket power limits')
        plt.ylabel('Power (w)')
        plt.legend()
        plt.subplot(2, 1, 2)
        plt.plot(time, rt0, label='time-0-mf{}'.format(node_num))
        plt.plot(time, rt1, label='time-1-mf{}'.format(node_num))
        if node_num == 10:
            plt.plot(time, tgt, label='target')
        plt.xlabel('Time (s)')
        plt.ylabel('Epoch duration (s)')
    plt.title('Per socket runtimes and target')
    plt.legend()
    # plt.show()
    plt.savefig('fig.png')

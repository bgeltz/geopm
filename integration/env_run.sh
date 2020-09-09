#!/bin/bash
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

set -e

# Default GEOPM setup
GEOPM_SRC=${GEOPM_SRC:?Please set GEOPM_SRC in your environment.}
GEOPM_BUILD=${GEOPM_BUILD:?Please set GEOPM_BUILD in your environment.}
GEOPM_APPS_SRCDIR=${GEOPM_APPS_SRCDIR:?Please set GEOPM_APPS_SRCDIR in your environment.}
GEOPM_WORKDIR=${GEOPM_WORKDIR:?Please set GEOPM_WORKDIR in your environment.}

export PATH=\
"${GEOPM_BUILD}/bin:"\
"${PATH}"

export LD_LIBRARY_PATH=\
"${GEOPM_BUILD}/lib:"\
"${LD_LIBRARY_PATH}"

export PYTHONPATH=\
"${GEOPM_SRC}/integration:"\
"${GEOPM_BUILD}/lib/python2.7/site-packages:"\
"${GEOPM_BUILD}/lib/python3.6/site-packages:"\
"${PYTHONPATH}"

export MANPATH=\
"${GEOPM_BUILD}/share/man:"\
"${MANPATH}"

# Env checks
if [ ! -d ${GEOPM_WORKDIR} ]; then
    echo "ERROR: Job output is expected to go in ${GEOPM_WORKDIR} which doesn't exist."
    return 1
fi

if [ ! -x "$(command -v geopmread)" ]; then
    echo "ERROR: 'geopmread' is not available.  Please build and install GEOPM into ${HOME}/build/geopm."
    return 1
elif [ ! -z ${GEOPM_SRC+x} ]; then
    # Check installed version of GEOPM against source version
    pushd ${GEOPM_SRC} > /dev/null
    GEOPM_SRC_VERSION=$(cat VERSION)
    popd > /dev/null
    GEOPMREAD_VERSION=$(geopmread --version | head -n1)

    if [ "${GEOPMREAD_VERSION}" != "${GEOPM_SRC_VERSION}" ]; then
        echo "WARNING: Version mismatch between installed version of GEOPM and the source tree!"
        echo"   Installed version = ${GEOPMREAD_VERSION} | Source version = ${GEOPM_SRC_VERSION}"
    fi
fi

if ! ldd $(which geopmbench) | grep --quiet libimf; then
    echo "ERROR: Please build geopm with the Intel Toolchain"
    echo "       to ensure the best performance."
    return 1
fi


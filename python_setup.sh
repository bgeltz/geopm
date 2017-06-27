#!/bin/bash

set -e
set -x

# Non-root install

wget https://bootstrap.pypa.io/get-pip.py
python get-pip.py --prefix=${HOME}/build/python

# Set PATH to:
export PATH=${HOME}/build/python/bin:${PATH}

# Set PYTHONPATH to:
export PYTHONPATH=${HOME}/build/python/lib/python2.7/site-packages:${PYTHONPATH}

pip install --user pandas matplotlib natsort numexpr bottleneck

# https://pip.pypa.io/en/stable/reference/pip_install/
#   Look at --root <dir> or --prefix <dir> for installng to an alternate path.

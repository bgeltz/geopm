#!/bin/bash

set -e
# set -x

usage() {
cat << EOF
Usage: ${0} [-h] [-c] [-d] [-i] [-t]
    Build the code
Options:
    -c : Start with make clean
    -d : Force default environment reinit (module load, autogen, configure)
    -i : Force Intel environment reinint
    -t : Run all the unit tests after compiling 
    -h : Print this page
EOF
}

TIMESTAMP=$(date +\%F_\%H\%M.\%S)
export BIN_PATH=$HOME/build

while getopts "hcdit" opt; do
    case $opt in
        h)
            usage
            exit
            ;;
        c)
            export MAKE_CLEAN=1
            ;;
        d)
            export FORCE_DEFAULTS=1
            ;;
        i)
            export FORCE_INTEL=1
            ;;
        t)
            export RUN_TESTS=1
            ;;
        \?)
            usage
            exit
            ;;
    esac
done

if [ ! -d "${BIN_PATH}" ]; then
    mkdir -p ${BIN_PATH}/build_logs
fi

ln -sf ${BIN_PATH}/build_logs/build.${TIMESTAMP}.log ${BIN_PATH}/build_latest.log

# Not sure what's going on below, but everything but the $() approach will insta-return instead of actually executing go1 through script.  The $() approach does spew minor garbage with saying libtool: command not found
# . script -ec go1 ${BIN_PATH}/build_logs/build.${TIMESTAMP}.log
# . go1 > >(tee -a ${BIN_PATH}/build_logs/build.${TIMESTAMP}.log) 2>&1
echo $(script -ec go1 ${BIN_PATH}/build_logs/build.${TIMESTAMP}.log)
# script -ec go1 ${BIN_PATH}/build_logs/build.${TIMESTAMP}.log


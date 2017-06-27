#!/bin/sh
#
# Copyright  (C) 1985-2017 Intel Corporation. All rights reserved.
#
# The information and source code contained herein is the exclusive property
# of Intel Corporation and may not be disclosed, examined, or reproduced in
# whole or in part without explicit written authorization from the Company.
#

PROD_DIR="/soft/compilers/intel/compilers_and_libraries_2017.2.174/linux"

INTEL_TARGET_ARCH=
INTEL_TARGET_PLATFORM=linux

if [ -e "$PROD_DIR/bin/intel64/icl_fbsd.cfg" ]; then
    INTEL_TARGET_ARCH=intel64
    INTEL_TARGET_PLATFORM=freebsd
fi

COMPILERVARS_ARGV=$#
if [ $# -eq 0 ]; then
  if [ "$COMPILERVARS_ARCHITECTURE" != '' ]; then
    INTEL_TARGET_ARCH=$COMPILERVARS_ARCHITECTURE
  fi
  if [ "$COMPILERVARS_PLATFORM" != '' ]; then
    INTEL_TARGET_PLATFORM=$COMPILERVARS_PLATFORM
  fi
fi

while [ $# -gt 0 ]
do
opt="$1"
case $opt in
  -arch)
  shift
  INTEL_TARGET_ARCH="$1"
  shift
  ;;
  -platform)
  shift
  INTEL_TARGET_PLATFORM="$1"
  shift
  ;;
  *)
  INTEL_TARGET_ARCH="$1"
  shift
  ;;
esac
done

if [ ! -e "$PROD_DIR/bin/intel64/icl_fbsd.cfg" ] && \
   [ "$INTEL_TARGET_ARCH" != "ia32" -a "$INTEL_TARGET_ARCH" != "intel64" -o \
     "$INTEL_TARGET_PLATFORM" != "android" -a "$INTEL_TARGET_PLATFORM" != "linux" -a "$INTEL_TARGET_PLATFORM" != "mac" ]; then

  echo "compilervars.sh [-arch] <arch> [-platform <platform>]"
  echo ""
  echo "  <arch> must be one of the following:"
  echo "      ia32           : Set up for IA-32 target."
  echo "      intel64        : Set up for Intel(R)64 target."
  echo "  <platform> must be of the following:"
  if [ "`uname`" = "Darwin" ]; then
    echo "      linux          : Set to Linux* target."
    echo "      mac            : Set to macOS* target.(default)"
  else
    echo "      android        : Set to Android* target."
    echo "      linux          : Set to Linux* target.(default)"
  fi
  echo ""
  echo "If the arguments to the sourced script are ignored (consult docs"
  echo "for your shell) the alternative way to specify target is environment"
  echo "variables COMPILERVARS_ARCHITECTURE to pass <arch> to the script"
  echo "and COMPILERVARS_PLATFORM to pass <platform>"

  return 1
elif [ -e "$PROD_DIR/bin/intel64/icl_fbsd.cfg" ] && \
     [ "$INTEL_TARGET_ARCH" != "intel64" -o \
       "$INTEL_TARGET_PLATFORM" != "freebsd" ]; then

  echo "compilervars.sh [-arch <arch>] [-platform <platform>]"
  echo ""
  echo "  <arch> must be one of the following:"
  echo "      intel64        : Set up for Intel(R)64 target."
  echo "  <platform> must be of the following:"
  echo "      freebsd        : Set to FreeBSD* target."
  echo ""
  echo "If the arguments to the sourced script are ignored (consult docs"
  echo "for your shell) the alternative way to specify target is environment"
  echo "variables COMPILERVARS_ARCHITECTURE to pass <arch> to the script"
  echo "and COMPILERVARS_PLATFORM to pass <platform>"

  return 1
fi

if [ "$INTEL_TARGET_PLATFORM" = "mac" ]; then
  INTEL_TARGET_PLATFORM="linux"
fi

if [ $COMPILERVARS_ARGV -eq 0 ] ; then
  #pass default values via COMPILERVARS_*
  if [ "$COMPILERVARS_ARCHITECTURE" = '' ]; then
    COMPILERVARS_ARCHITECTURE=$INTEL_TARGET_ARCH
  fi
  if [ "$COMPILERVARS_PLATFORM" = '' ]; then
    COMPILERVARS_PLATFORM=$INTEL_TARGET_PLATFORM
  fi
  INTEL_TARGET_ARCH=
  INTEL_TARGET_PLATFORM=
fi

if [ -e "$PROD_DIR/daal/bin/daalvars.sh" ]; then
   . "$PROD_DIR/daal/bin/daalvars.sh" $INTEL_TARGET_ARCH
fi
if [ -e "$PROD_DIR/../../debugger_2017/bin/debuggervars.sh" ]; then
  . "$PROD_DIR/../../debugger_2017/bin/debuggervars.sh" $INTEL_TARGET_ARCH
fi
if [ -e "$PROD_DIR/tbb/bin/tbbvars.sh" ]; then
   . "$PROD_DIR/tbb/bin/tbbvars.sh" $INTEL_TARGET_ARCH $INTEL_TARGET_PLATFORM
fi
if [ -e "$PROD_DIR/mkl/bin/mklvars.sh" ]; then
  . "$PROD_DIR/mkl/bin/mklvars.sh" $INTEL_TARGET_ARCH
fi
if [ -e "$PROD_DIR/ipp/bin/ippvars.sh" ]; then
  . "$PROD_DIR/ipp/bin/ippvars.sh" $INTEL_TARGET_ARCH $INTEL_TARGET_PLATFORM
fi
#if [ -e "$PROD_DIR/mpi/intel64/bin/mpivars.sh" ] && \
#   [ "$INTEL_TARGET_ARCH" = "intel64" -o "$COMPILERVARS_ARCHITECTURE" = "intel64" ]; then
#  . "$PROD_DIR/mpi/intel64/bin/mpivars.sh"
#fi

# BRG ENV
#export PATH=$HOME/build/mvapich2-2.3a/bin:$PATH
#export LD_LIBRARY_PATH=${HOME}/build/mvapich2-2.3a/lib:$LD_LIBRARY_PATH

#Steve ENV
export PATH=$HOME/build/mvapich2-2.2rc2/bin:$PATH
export LD_LIBRARY_PATH=${HOME}/build/mvapich2-2.2rc2/lib:$LD_LIBRARY_PATH

if [ -e "$PROD_DIR/pkg_bin/compilervars_arch.sh" ]; then
    . "$PROD_DIR/pkg_bin/compilervars_arch.sh" $INTEL_TARGET_ARCH $INTEL_TARGET_PLATFORM
fi

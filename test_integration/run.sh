#!/bin/bash
#SBATCH -N 1
#SBATCH -J test_ee_short_region_slop
#SBATCH -t 36:00:00
#SBATCH -o %j.out

source $HOME/geopm-env.sh
DATE=$(date +%F_%H%M)
set -ex

export OMP_NUM_THREADS=20
hostname
out_dir_0=$HOME/slop_data/${DATE}/ucore-1.0-2.4
out_dir_1=$HOME/slop_data/${DATE}/ucore-2.4-2.4
out_dir_2=$HOME/slop_data/${DATE}/freq-1.6-2.0
mkdir -p $out_dir_0/data
mkdir -p $out_dir_1/data
mkdir -p $out_dir_2/data

#Clear CORE PERFMON MSRs
# geopmwrite MSR::IA32_PMC0:PERFCTR board 0 0x0
# geopmwrite MSR::IA32_PMC1:PERFCTR board 0 0x0
# geopmwrite MSR::IA32_PMC2:PERFCTR board 0 0x0
# geopmwrite MSR::IA32_PMC3:PERFCTR board 0 0x0

#Enable CORE PERFMON MSRs
# geopmwrite MSR::PERF_GLOBAL_CTRL:EN_PMC0 board 0 0x1
# geopmwrite MSR::PERF_GLOBAL_CTRL:EN_PMC1 board 0 0x1
# geopmwrite MSR::PERF_GLOBAL_CTRL:EN_PMC2 board 0 0x1
# geopmwrite MSR::PERF_GLOBAL_CTRL:EN_PMC3 board 0 0x1

#############################################
# Perfmon set 14 - Cross Core Snoops and L2 #
#############################################
# geopmwrite MSR::IA32_PERFEVTSEL0:EVENT_SELECT board 0 0xD1 #MEM_LOAD_RETIRED
# geopmwrite MSR::IA32_PERFEVTSEL0:UMASK board 0 0x08 #L1 MISS
# geopmwrite MSR::IA32_PERFEVTSEL1:EVENT_SELECT board 0 0xF2 #L2_LINES_OUT
# geopmwrite MSR::IA32_PERFEVTSEL1:UMASK board 0 0x01 #SILENT
# geopmwrite MSR::IA32_PERFEVTSEL2:EVENT_SELECT board 0 0xD2 #MEM_LOAD_L3_HIT_RETIRED
# geopmwrite MSR::IA32_PERFEVTSEL2:UMASK board 0 0x04 #XSNP_HITM
# geopmwrite MSR::IA32_PERFEVTSEL3:EVENT_SELECT board 0 0xF1 #L2_LINES_IN
# geopmwrite MSR::IA32_PERFEVTSEL3:UMASK board 0 0x1  #ALL

#Enable Perfmon (yes there are two enables)
# geopmwrite MSR::IA32_PERFEVTSEL0:USR board 0 0x1
# geopmwrite MSR::IA32_PERFEVTSEL1:USR board 0 0x1
# geopmwrite MSR::IA32_PERFEVTSEL2:USR board 0 0x1
# geopmwrite MSR::IA32_PERFEVTSEL3:USR board 0 0x1
# geopmwrite MSR::IA32_PERFEVTSEL0:OS board 0 0x1
# geopmwrite MSR::IA32_PERFEVTSEL1:OS board 0 0x1
# geopmwrite MSR::IA32_PERFEVTSEL2:OS board 0 0x1
# geopmwrite MSR::IA32_PERFEVTSEL3:OS board 0 0x1
# geopmwrite MSR::IA32_PERFEVTSEL0:EN board 0 0x1
# geopmwrite MSR::IA32_PERFEVTSEL1:EN board 0 0x1
# geopmwrite MSR::IA32_PERFEVTSEL2:EN board 0 0x1
# geopmwrite MSR::IA32_PERFEVTSEL3:EN board 0 0x1

# Run full range for CPU and uncore
GEOPM_KEEP_FILES=true \
GEOPM_LAUNCHER=impi \
python ./test_ee_short_region_slop.py -v
mv *.png $out_dir_0
mv *.report* *.log *.json *trace* $out_dir_0/data

# Fix uncore at max
max_uncore_freq=$(geopmread MSR::UNCORE_RATIO_LIMIT:MAX_RATIO board 0)
geopmwrite MSR::UNCORE_RATIO_LIMIT:MIN_RATIO board 0 $max_uncore_freq

# Run full range for CPU and fixed uncore
GEOPM_KEEP_FILES=true \
GEOPM_LAUNCHER=impi \
python ./test_ee_short_region_slop.py
mv *.png $out_dir_1
mv *.report* *.log *.json *trace* $out_dir_1/data

# Run limited range for CPU and fixed uncore
GEOPM_KEEP_FILES=true \
GEOPM_LAUNCHER=impi \
GEOPM_SLOP_FREQ_MIN=1.6e9 \
GEOPM_SLOP_FREQ_MAX=2.0e9 \
python ./test_ee_short_region_slop.py
mv *.png $out_dir_2
mv *.report* *.log *.json *trace* $out_dir_2/data
# mv *.out $HOME/slop_data

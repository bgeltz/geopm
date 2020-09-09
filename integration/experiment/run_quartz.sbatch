#!/bin/bash
#SBATCH -J nekbone
#SBATCH -o %j.nekbone.out
#SBATCH --account ecp_pm
#SBATCH -N 1
#SBATCH -t 0:30:00
#SBATCH -p pdebug

##SBATCH -N 128
##SBATCH -t 3:00:00
##SBATCH -p pbatch

./run.sbatch


#!/bin/bash
#SBATCH -J nekbone
#SBATCH -o %j.nekbone.out
#SBATCH --constraint="noscratch"
#SBATCH --account h1906
#SBATCH --ear off
#SBATCH -N 1
#SBATCH -t 0:30:00
#SBATCH -p test

##SBATCH -N 128
##SBATCH -t 3:00:00
##SBATCH -p general

./run.sbatch


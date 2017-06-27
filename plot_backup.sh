#!/bin/bash

BACKUP_DIR=/mnt/ssd/backup/plots
BACKUP_FILE=${1%/}.$(date +%F_%H%M_%S).tgz

compress.sh ${1}
mv ${1%/}.tgz ${BACKUP_DIR}/${BACKUP_FILE}
echo "Created ${BACKUP_DIR}/${BACKUP_FILE}"

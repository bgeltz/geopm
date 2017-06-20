#!/bin/bash

for i in $(seq 135 5 225); do
    echo "${i} - $(awk '{print $9}' ${i}*unbalanced*trace* | grep "0\.5.*"| wc -l)"
done


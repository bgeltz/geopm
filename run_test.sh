#!/bin/bash
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'
#in geopm Repo
make checkprogs
if [ $? != 0 ]; then
   exit 
fi
if [ -n "$1" ]; then
  for TEST in $(ls test/gtest_links/$1* | grep -v log | grep -v xml); do
      $TEST
      if [ $? == 0 ]; then
        echo -e "${GREEN}PASS${NC}   $TEST"
      else
        echo -e "${RED}FAILED${NC} $TEST"
      fi
  done
else
  echo "Provide Test name as second Arguement e.g.! \"$0 ExceptionTest\""
fi

#!/bin/bash
D=$1
cd $D && python -m pytest verification/rule-tests -q -p no:cacheprovider --tb=no -rA 2>&1 | grep -E "^(PASSED|FAILED|ERROR)" | sed -E 's/ - .*//' | sort

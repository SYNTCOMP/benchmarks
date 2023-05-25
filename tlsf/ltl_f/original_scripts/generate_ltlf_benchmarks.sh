#!/bin/bash

set -e

N=10
if [ -n "$1" ]; then
  N=$1
fi

python3 benchmark_generate.py workstation_resupply "$N"
python3 benchmark_generate.py finding_nemo "$N"

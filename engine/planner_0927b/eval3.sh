#!/bin/bash
# usage: eval3.sh cand opp tag seeds...
cand=$1; opp=$2; tag=$3; shift 3
mkdir -p /root/kg/ev
for s in "$@"; do
  (timeout 900 python /root/kg/pdump.py $cand $opp $s 0 > /root/kg/ev/${tag}_${s}_s0.txt 2>&1; timeout 900 python /root/kg/pdump.py $cand $opp $s 1 > /root/kg/ev/${tag}_${s}_s1.txt 2>&1) &
done
wait
for s in "$@"; do for st in 0 1; do echo "$tag seed $s seat $st: $(grep FINAL /root/kg/ev/${tag}_${s}_s${st}.txt)"; done; done

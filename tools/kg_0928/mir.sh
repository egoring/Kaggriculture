#!/bin/bash
cd /root/kg
( for s in 21 22 23; do python h2.py submission_v886b_h3.py submission_step1009.py $s; python h2.py submission_step1009.py submission_v886b_h3.py $s; done 2>&1 | grep FINAL > ev/mir886_1009.txt ) &
( for s in 21 22 23; do python h2.py submission_v886b_h3.py submission_v879_mpx9.py $s; python h2.py submission_v879_mpx9.py submission_v886b_h3.py $s; done 2>&1 | grep FINAL > ev/mir886_879.txt ) &
wait

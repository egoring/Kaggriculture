#!/bin/bash
cd /root/kg
( for s in 21 22 23; do python h2.py submission_v887_fixord.py submission_v886_s1009wash.py $s; python h2.py submission_v886_s1009wash.py submission_v887_fixord.py $s; done 2>&1 | grep FINAL > ev/mir887_886.txt ) &
( for s in 21 22 23; do python h2.py submission_v887_fixord.py submission_step1009.py $s; python h2.py submission_step1009.py submission_v887_fixord.py $s; done 2>&1 | grep FINAL > ev/mir887_1009.txt ) &
wait
python h2.py submission_v887_fixord.py submission_v887_fixord.py 31 2>&1 | grep FINAL > ev/mir887_self.txt

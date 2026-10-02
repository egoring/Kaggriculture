import os,signal,subprocess
out=subprocess.run(['ps','-eo','pid,args'],capture_output=True,text=True).stdout
me=os.getpid()
for line in out.splitlines()[1:]:
    pid,args=line.strip().split(None,1)
    if int(pid)==me or 'shell-snapshots' in args or 'killtests' in args: continue
    if any(k in args for k in ('mir'+'ror.py','mir'+'ror1.py','nb'+'t.sh')):
        try: os.kill(int(pid),signal.SIGKILL); print('killed',pid,args[:60])
        except Exception as e: print('fail',pid,e)

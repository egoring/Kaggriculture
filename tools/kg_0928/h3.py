import sys,importlib.util,time
from kaggle_environments import make
def load(p):
    s=importlib.util.spec_from_file_location('C'+str(abs(hash(p))),p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
A=load(sys.argv[1]); B=load(sys.argv[2]); seed=int(sys.argv[3])
ag=[getattr(A,'kaggle_submission_agent',None) or A.agent, getattr(B,'kaggle_submission_agent',None) or B.agent]
env=make("kaggriculture",configuration={"seed":seed}); env.reset()
t0=time.time(); tmax=[0,0]
for t in range(720):
    obs=[env._Environment__get_shared_state(i).observation for i in (0,1)]
    acts=[]
    for i in (0,1):
        a=time.time(); acts.append(ag[i](obs[i],env.configuration)); tmax[i]=max(tmax[i],time.time()-a)
    env.step(acts)
    if env.done: break
rw=[s.reward for s in env.state]; print(sys.argv[1],'vs',sys.argv[2],'seed',seed,'FINAL',rw,'margin %+.0f'%(rw[0]-rw[1]),'wall %.0fs maxstep %.2f/%.2f'%(time.time()-t0,*tmax))
for m in (A,B):
    for k in ('_ORC_REPORT','_WASH_REPORT','_ASAP_REPORT','_V7_MPX_REPORT','_FIXORD_REPORT','REPORT','TELEMETRY','_F5_QTY'):
        v=getattr(m,k,None)
        if v is not None and k!='_F5_QTY': print('  ',k,v)

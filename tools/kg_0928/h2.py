import sys,importlib.util
from kaggle_environments import make
def load(p):
    s=importlib.util.spec_from_file_location('C'+str(abs(hash(p))),p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
A=load(sys.argv[1]); B=load(sys.argv[2]); seed=int(sys.argv[3])
ag=[getattr(A,'kaggle_submission_agent',None) or A.agent, getattr(B,'kaggle_submission_agent',None) or B.agent]
env=make("kaggriculture",configuration={"seed":seed}); env.reset()
for t in range(720):
    obs=[env._Environment__get_shared_state(i).observation for i in (0,1)]
    env.step([ag[i](obs[i],env.configuration) for i in (0,1)])
    if env.done: break
rw=[s.reward for s in env.state]; print(sys.argv[1],'vs',sys.argv[2],'seed',seed,'FINAL',rw,'margin %+.0f'%(rw[0]-rw[1]))

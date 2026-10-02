import sys,importlib.util
from kaggle_environments import make
def load(p):
    s=importlib.util.spec_from_file_location('C'+str(abs(hash(p))),p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
A=load(sys.argv[1]); B=load(sys.argv[2]); seed=int(sys.argv[3]); D=int(sys.argv[4]); U=int(sys.argv[5])
a=A.kaggle_submission_agent; b=getattr(B,'kaggle_submission_agent',None) or B.agent
env=make("kaggriculture",configuration={"seed":seed}); env.reset()
for t in range(720):
    obs=[env._Environment__get_shared_state(i).observation for i in (0,1)]
    acts=[a(obs[0],env.configuration), b(obs[1],env.configuration)]
    st=(A._STATE if hasattr(A,"_STATE") else A.V2._STATE)[0]
    if t//24==D:
        if t%24==2: print('script', st.scripts[U] if U < len(st.scripts) else None)
        units=st.units; inv=st.invs
        u=([acts[0]['farmer']]+acts[0]['hands'])[U] if U < len(units) else None
        print(f"h{t%24:2d} pos {units[U] if U<len(units) else None} act {u} inv {inv[U] if U<len(inv) else None} spos {st.script_pos[U] if U<len(st.script_pos) else None}")
    env.step(acts)
    if env.done: break

import pickle,sys,json,multiprocessing as mp,importlib.util
from kaggle_environments import make
from tapeagent import make_tape_agent
OPPNAME=sys.argv[1]; CANDS=sys.argv[2].split(",")
recs=pickle.load(open("recs.pkl","rb")); cands=pickle.load(open("cands.pkl","rb"))
s=importlib.util.spec_from_file_location("v","submission_v89.py"); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); cands["tape7"]=m._TAPES[7]
def load(p,n):
    s=importlib.util.spec_from_file_location(n,p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m.agent
games=[r for r in recs if r["name"]==OPPNAME and r["opp"]=="Whyme Labs"]
def run(args):
    cn,g=args
    opp=make_tape_agent(g["acts"])
    me=load("submission_v810.py","me") if cn=="v810" else make_tape_agent(cands[cn])
    agents=[opp,me] if g["seat"]==0 else [me,opp]
    env=make("kaggriculture",configuration={"seed":g["seed"]}); env.run(agents)
    r=[s.reward for s in env.steps[-1]]; mine=r[1-g["seat"]]; his=r[g["seat"]]
    return cn,g["ep"],mine,his,g["opp_reward"],g["reward"]
if __name__=="__main__":
    jobs=[(cn,g) for cn in CANDS for g in games]
    out={}
    with mp.Pool(2) as pool:
        for cn,ep,mine,his,rec_me,rec_his in pool.imap_unordered(run,jobs):
            out.setdefault(cn,[]).append((ep,mine,his,rec_me,rec_his))
    print(f"recorded Whyme vs {OPPNAME}: {sum(a>b for _,_,_,a,b in out[CANDS[0]])}/{len(games)}")
    for cn,res in out.items():
        res.sort(); w=sum(a>b for _,a,b,_,_ in res)
        print(f"{cn:12s} vs {OPPNAME} recorded actions: {w}/{len(res)} mean diff {sum(a-b for _,a,b,_,_ in res)/len(res):+.0f} diffs {[round(a-b) for _,a,b,_,_ in res]}")

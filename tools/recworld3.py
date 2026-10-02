import pickle,sys,glob,importlib.util,multiprocessing as mp
from kaggle_environments import make
from tapeagent import make_tape_agent
# usage: recworld3.py <folder> fileA,fileB [loss|all]  — recs_cache 에서 해당 폴더의 우리 에피소드만 로드해 기록 세계 재현
FOLDER=sys.argv[1]; FILES=sys.argv[2].split(","); ONLY=sys.argv[3] if len(sys.argv)>3 else "loss"
games=[]
for cp in glob.glob(f"recs_cache/logs__{FOLDER}__*.pkl"):
    rs=pickle.load(open(cp,"rb")); me=[r for r in rs if r["name"]=="weense"]
    if not me: continue
    me=me[0]; opp=[r for r in rs if r is not me][0]
    if ONLY=="loss" and me["win"]: continue
    games.append((me["ep"],me["seed"],me["seat"],me["reward"],me["opp_reward"],opp["name"],opp["acts"]))
def load(p,n):
    s=importlib.util.spec_from_file_location(n,p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m.agent
def run(args):
    f,(ep,seed,seat,ra,rb,on,oacts)=args
    A=load(f,"A"); B=make_tape_agent(oacts); agents=[A,B] if seat==0 else [B,A]
    env=make("kaggriculture",configuration={"seed":seed}); env.run(agents); rw=[s.reward for s in env.steps[-1]]
    return f,ep,rw[seat],rw[1-seat],ra,rb,on
if __name__=="__main__":
    out={}
    with mp.Pool(2) as pool:
        for f,ep,a,b,ra,rb,on in pool.imap_unordered(run,[(f,g) for f in FILES for g in games]):
            out.setdefault(f,[]).append((ep,a-b,ra-rb,on))
    import statistics
    for f,rs in out.items():
        print(f"{f}: {FOLDER} {ONLY} {len(rs)}판 재현 → 승 {sum(d>0 for _,d,_,_ in rs)}/{len(rs)} (기록 {sum(r>0 for _,_,r,_ in rs)}), 평균 마진 {statistics.mean(r for _,_,r,_ in rs):+.0f} → {statistics.mean(d for _,d,_,_ in rs):+.0f}")

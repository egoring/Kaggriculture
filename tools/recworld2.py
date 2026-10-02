import pickle,sys,importlib.util,multiprocessing as mp
from kaggle_environments import make
from tapeagent import make_tape_agent
recs=pickle.load(open("recs.pkl","rb"))
EPS=[int(x) for x in sys.argv[1].split(",")]; FILES=sys.argv[2].split(",")
me={r["ep"]:r for r in recs if r["name"]=="weense"}
def load(p,n):
    s=importlib.util.spec_from_file_location(n,p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m.agent
def run(args):
    f,ep=args; r=me[ep]; opp=[x for x in recs if x["ep"]==ep and x["seat"]!=r["seat"]][0]
    A=load(f,"A"); B=make_tape_agent(opp["acts"]); agents=[A,B] if r["seat"]==0 else [B,A]
    env=make("kaggriculture",configuration={"seed":r["seed"]}); env.run(agents)
    rw=[s.reward for s in env.steps[-1]]; return f,ep,rw[r["seat"]],rw[1-r["seat"]],r["reward"],r["opp_reward"],opp["name"]
if __name__=="__main__":
    with mp.Pool(2) as pool:
        for f,ep,a,b,ra,rb,on in pool.imap(run,[(f,ep) for f in FILES for ep in EPS]):
            print(f"{f:20s} ep{ep} vs {on:16s}: replay me {a:8.0f} opp {b:8.0f} ({a-b:+8.0f}) | recorded me {ra:8.0f} opp {rb:8.0f} ({ra-rb:+8.0f})",flush=True)

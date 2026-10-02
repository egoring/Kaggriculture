import sys,importlib.util,collections
from kaggle_environments import make
def load(p):
    s=importlib.util.spec_from_file_location('C'+str(abs(hash(p))),p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
A=load(sys.argv[1]); B=load(sys.argv[2]); seed=int(sys.argv[3]); crop=sys.argv[4]; who=int(sys.argv[5]) if len(sys.argv)>5 else 0
ag=[A.kaggle_submission_agent, getattr(B,'kaggle_submission_agent',None) or B.agent]
env=make("kaggriculture",configuration={"seed":seed}); env.reset()
life={}  # (pos,planted) -> dict
hist=collections.Counter()
prev=None
for t in range(720):
    obs=[env._Environment__get_shared_state(i).observation for i in (0,1)]
    acts=[ag[i](obs[i],env.configuration) for i in (0,1)]
    if t%24==23:
        day=t//24; f=obs[0]['farms'][who]; cur={}
        for y,row in enumerate(f['tiles']):
            for x,tl in enumerate(row):
                if isinstance(tl,dict) and tl.get('kind')=='PLANT' and tl['crop']==crop:
                    key=((x,y),tl['planted_day']); cur[key]=tl
                    L=life.setdefault(key,{'w':[],'f':[],'y':[]})
                    if tl['watered_today']: L['w'].append(day-tl['planted_day'])
                    if tl.get('fertilized_until_day',-1)>=day: L['f'].append(day-tl['planted_day'])
                    L['y'].append(tl['yield_units'])
        if prev is not None:
            for key,tl in prev.items():
                if key not in cur:
                    L=life[key]; L['end']=day; L['age_end']=day-key[1]; L['weed']= isinstance(f['tiles'][key[0][1]][key[0][0]],dict) and f['tiles'][key[0][1]][key[0][0]].get('kind')=='WEED'
        prev=cur
    env.step(acts)
    if env.done: break
n=0
for key,L in sorted(life.items(), key=lambda kv: kv[0][1]):
    if 'end' not in L: continue
    n+=1
    if n<=25: print(f"pos {key[0]} planted d{key[1]} ended age {L['age_end']} weed={L['weed']} watered ages {L['w']} fert {L['f']} yields {L['y']}")
    hist[(L['age_end'], L['weed'], L['y'][-1] if L['y'] else None)]+=1
print('total ended', n, 'summary (age_end, weed, last_yield): count')
for k,v in sorted(hist.items(), key=lambda kv:-kv[1])[:12]: print('  ',k,v)

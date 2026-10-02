import pickle,sys,collections
sys.path.insert(0,'/root/kg')
from kaggle_environments import make
from tapeagent import make_tape_agent
POOL,EP=sys.argv[1],int(sys.argv[2])
recs=pickle.load(open(f'recs_cache/logs__{POOL}__all.pkl','rb'))
pair={r['seat']:r for r in recs if r['ep']==EP}
seed=pair[0]['seed']
env=make("kaggriculture",configuration={"seed":seed}); G=env.interpreter.__globals__
orig=G['_commit_unit']; LOG=[]; CUR={'s':0,'f':None}
def hook(op,item,price,farm,private,market,shed_capacity=100,_o=orig):
    ok=_o(op,item,price,farm,private,market,shed_capacity)
    if ok: LOG.append((CUR['s'],CUR['f'].index(farm) if farm in CUR['f'] else -1,op,item,price))
    return ok
G['_commit_unit']=hook
oh=G['_do_hire']
def hh(farm,private,board_size,mult=G['FARM_HAND_COST_MULT'],_o=oh):
    m0=farm['money']; r=_o(farm,private,board_size,mult); LOG.append((CUR['s'],CUR['f'].index(farm),'HIRE','',m0-farm['money'])); return r
G['_do_hire']=hh
oa=G['_apply_unit_action']; HL=[]
def ha(farm, private, idx, action, board_size, day, turns_per_day, shed_capacity=100, _o=oa):
    if isinstance(action,list) and action and action[0] not in ('NORTH','SOUTH','EAST','WEST','PASS'):
        pos=G['_farmer_position'](farm,idx); t=farm['tiles'][pos[1]][pos[0]]
        HL.append((CUR['s'],CUR['f'].index(farm),action[0],(t.get('crop') or t.get('animal')) if isinstance(t,dict) else None,t.get('yield_units',0) if isinstance(t,dict) else 0))
    return _o(farm, private, idx, action, board_size, day, turns_per_day, shed_capacity)
G['_apply_unit_action']=ha
oi=env.interpreter
def interp(state, env_):
    CUR['s']=int(state[0].observation.step); CUR['f']=list(state[0].observation.farms); return oi(state, env_)
env.interpreter=interp
env.run([make_tape_agent(pair[0]['acts']),make_tape_agent(pair[1]['acts'])])
rw=[s.reward for s in env.steps[-1]]; print('replay rewards',rw,'recorded',pair[0]['reward'],pair[1]['reward'],'names',pair[0]['name'],pair[1]['name'])
for seat in (0,1):
    money=[env.steps[min(t,719)][seat]['observation']['farms'][seat]['money'] for t in range(0,720,72)]
    print('seat',seat,pair[seat]['name'][:15],'money every 3 days',[round(m) for m in money])
    units=collections.Counter(); rev=collections.Counter(); hv=collections.Counter(); ops=collections.Counter()
    for s,f,op,item,price in LOG:
        if f!=seat: continue
        if op=='SELL': units[item]+=1; rev[item]+=price
        elif op=='HIRE': rev['HIRE']-=price
        else: rev['BUY_'+item]-=price
    for s,f,op,c,y in HL:
        if f!=seat: continue
        ops[op]+=1
        if op=='HARVEST': hv[c]+=y
    print('  sold',dict(sorted(units.items())))
    print('  rev ',{k:round(v) for k,v in sorted(rev.items())})
    print('  harvested',dict(sorted(hv.items(),key=lambda x:str(x[0]))))
    print('  ops',dict(sorted(ops.items())))

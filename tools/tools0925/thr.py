import json,pickle,collections,ast,sys
from kaggle_environments.envs.kaggriculture.kaggriculture import market_price, MARKET_PARAMS
rs=pickle.load(open('recs_cache/logs__p868__all.pkl','rb'))
byep=collections.defaultdict(list)
for r in rs: byep[r['ep']].append(r)
names=sys.argv[1:]
IT=("MILK","WOOL","EGG","STRAWBERRY","MELON","CARROT","TOMATO")
rows=collections.defaultdict(list)
for ep,p in byep.items():
    me=[r for r in p if r['name']=='weense'][0]; op=[r for r in p if r is not me][0]
    if not any(op['name'].startswith(n) for n in names): continue
    e=json.load(open(f'/tmp/s868/s56546862/{ep}.json'))
    for t in range(1,len(e['steps'])-1):
        mk=e['steps'][t][0]['observation']['market']
        if isinstance(mk,str): mk=ast.literal_eval(mk)
        inv=mk['inventory']
        a=e['steps'][t+1][op['seat']]['action'] or {}
        pr=e['steps'][t+1][op['seat']]['observation'].get('private') or e['steps'][t+1][0]['observation'].get('private')
        for o in (a.get('market') or []):
            if o and o[0]=='SELL' and o[1] in IT and int(o[2])>0:
                it=o[1]; q=int(o[2]); base=MARKET_PARAMS[it]['base']
                last=market_price(it,inv[it]+q-1); nxt=market_price(it,inv[it]+q)
                rows[it].append((t,q,inv[it]-10000,last/base,nxt/base))
for it in IT:
    r=rows[it]
    if not r: continue
    print(it,'n',len(r),' last-unit price/base: median %.2f min %.2f | next-unit price/base: median %.2f max %.2f'%(sorted(x[3] for x in r)[len(r)//2],min(x[3] for x in r),sorted(x[4] for x in r)[len(r)//2],max(x[4] for x in r)))
    print('   sample',r[:12])

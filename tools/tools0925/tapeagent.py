import copy
def make_tape_agent(acts):
    def agent(obs, cfg=None):
        step=int(obs["step"]); a=copy.deepcopy(acts[min(step,718)] or {"farmer":["PASS"],"hands":[],"market":[]})
        farms=obs["farms"]; seat=int(obs["player"]); exp=len(farms[seat]["hands"])
        h=list(a.get("hands") or []); h+= [["PASS"]]*(exp-len(h)); a["hands"]=h[:exp]
        a.setdefault("farmer",["PASS"]); a.setdefault("market",[])
        return a
    return agent

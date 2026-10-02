# Kaggle Notebook용: georgymamarin/kaggriculture-episodes 에서 상위 N팀의 최근 사다리 에피소드를
# (v2: 레이팅 기준) 우리 recs.pkl 형식(logs/<folder>.recs.pkl 과 동일)으로 압축 추출한다.
# 사용: Kaggle에서 새 Notebook 생성 → Add Input: "Kaggriculture Episodes" (georgymamarin) → 이 코드 한 셀 붙여넣고 실행
#       → 출력 /kaggle/working/top_rated.recs.pkl (수 MB) 다운로드 → C:\kaggle\logs\top_rated.recs.pkl 로 저장
import pandas as pd, json, glob, hashlib, collections, pickle, time
import pyarrow.dataset as pads

import os
# 데이터셋 경로 자동 탐색 (입력이 추가되지 않았으면 안내 후 중단)
_hits = glob.glob("/kaggle/input/**/teams.csv", recursive=True)
if not _hits:
    print("입력 목록:", os.listdir("/kaggle/input") if os.path.exists("/kaggle/input") else "(없음)")
    raise SystemExit("teams.csv를 찾지 못했습니다. 노트북 오른쪽 Input 패널에서 'Kaggriculture Episodes' (georgymamarin) 데이터셋을 Add Input 해 주세요.")
BASE = os.path.dirname(_hits[0]); print("BASE =", BASE, "files:", sorted(os.listdir(BASE))[:20])
MIN_RATING = 2650   # 이 레이팅 이상인 좌석이 있는 사다리 판만
MAX_EPISODES = 400  # 최근 순으로 최대 몇 판
OUT = "/kaggle/working/top_rated.recs.pkl"

teams = pd.read_csv(f"{BASE}/teams.csv")
name_of = dict(zip(teams.team_id, teams.team_name))
top_ids = set(teams.sort_values("ladder_score", ascending=False).head(10).team_id)

ep = pd.read_csv(f"{BASE}/episodes.csv")
ep = ep[ep["type"] == "EPISODE_TYPE_PUBLIC"].copy()
ep["maxr"] = ep[["rating_0", "rating_1"]].max(axis=1)
sel = ep[ep.maxr >= MIN_RATING].sort_values("end_time", ascending=False).head(MAX_EPISODES)
print("episodes with a seat >=", MIN_RATING, ":", (ep.maxr >= MIN_RATING).sum(), "-> taking", len(sel))
wanted = {}
for _, row in sel.iterrows():
    hi = [int(row.team_0) if row.rating_0 >= MIN_RATING else None, int(row.team_1) if row.rating_1 >= MIN_RATING else None]
    wanted[int(row.episode_id)] = {t for t in hi if t is not None}
print("episodes to pull:", len(wanted))

ds = pads.dataset(sorted(glob.glob(f"{BASE}/replays_*.parquet")))
ids = list(wanted.keys())
out = []
t0 = time.time()
for i in range(0, len(ids), 25):
    chunk = ids[i:i + 25]
    tbl = ds.scanner(filter=pads.field("episode_id").isin(chunk)).to_table()
    for eid, rj in zip(tbl.column("episode_id").to_pylist(), tbl.column("replay_json").to_pylist()):
        d = json.loads(rj)
        info = d.get("info", {}) or {}
        steps = d["steps"]
        if len(steps) < 720:
            continue
        names = info.get("TeamNames") or [None, None]
        row = ep[ep.episode_id == eid].iloc[0]
        tids = [int(row.team_0), int(row.team_1)]
        names = [names[s] or name_of.get(tids[s], str(tids[s])) for s in (0, 1)]
        ratings = [row.get("rating_0"), row.get("rating_1")]
        shops = list((steps[-1][0]["observation"].get("town", {}) or {}).get("unlocked_shops", []))
        for seat in (0, 1):
            acts = [steps[k + 1][seat]["action"] for k in range(719)]
            h = hashlib.sha256(json.dumps(acts, sort_keys=True).encode()).hexdigest()[:16]
            buys = collections.Counter(); sells = collections.Counter()
            for a in acts:
                for o in (a or {}).get("market") or []:
                    if not o or len(o) < 2: continue
                    if o[0] == "BUY_ANIMAL": buys[o[1]] += int(o[2]) if len(o) > 2 else 1
                    elif o[0] == "SELL": sells[o[1]] += int(o[2])
            prof = f"C{buys['COW']}S{buys['SHEEP']}G{buys['GOOSE']}"
            out.append(dict(file=f"kaggle/{eid}", folder="top10", ep=int(eid), seed=info.get("seed"), seat=seat,
                            name=names[seat], opp=names[1 - seat], team_id=tids[seat], is_top=(tids[seat] in wanted[eid]), is_top10=(tids[seat] in top_ids),
                            rating=ratings[seat], opp_rating=ratings[1 - seat], engine=d.get("module_version"),
                            reward=d["rewards"][seat], opp_reward=d["rewards"][1 - seat],
                            win=d["rewards"][seat] > d["rewards"][1 - seat], shops=shops, hash=h, prof=prof,
                            sells={k: sells[k] for k in ("MILK", "WOOL", "EGG", "STRAWBERRY", "MELON", "WHEAT", "CARROT", "TOMATO")},
                            acts=acts, status=(d.get("statuses") or ["?", "?"])[seat], step0=acts[0].get("market")))
    print(f"{min(i + 25, len(ids))}/{len(ids)} episodes, {len(out)} records, {time.time() - t0:.0f}s", flush=True)

pickle.dump(out, open(OUT, "wb"), protocol=4)
import os; print("saved", OUT, os.path.getsize(OUT) // 1024, "KB, records", len(out))

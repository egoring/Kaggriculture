"""tools/tape_gates.py — generic gate-suite runner for a candidate submission.

Generalizes analysis/t_79fa4f47/{run_g2_v3,g2_check_v2,g2b_margin_v3,make_g1/g3/g4/g5_jobs,
g5_runner,g5_coverage,g6_timing*}.py into one script driven by --cand/--base/--team/--src.
Those originals are left unmodified as the v888-verified reference implementation; the gate
LOGIC here (thresholds are NOT judged here — only numbers are produced, per spec) mirrors them.

Gates:
  G0 file size / py_compile / forbidden external-access strings in --cand.
  G1 official 5 seeds x both seats, cand vs base, must finish DONE/DONE, 720 steps, 0 errors.
  G2 replay purity: every episode in --src pool containing --team, cand agent in team's seat,
     opponent replayed from the recorded tape -> per-episode match_frac (pure function replay,
     g2_check_v2.py method) + final reward_diff via real env.run (g2b_margin_v3.py method).
  G3 cand vs base, seed set = official 5 + random.Random(887).sample(range(1000,100000),20)
     (== make_g3_jobs.py), both seats = 50 games. Seed list can be overridden via --g3-seeds.
  G4 cand vs the AGENTS §1 regression opponent set (make_g4_jobs.py's OPPS, unchanged),
     official 5 seeds, both seats = 80 games. Base is NOT used here (matches original).
  G5 our real-play pool(s) replay: cand and base each dropped into our seat, opponent replayed
     from the recorded tape, real env.run (g5_runner.py method), per-episode margin for both.
  G6 max per-step call time of --cand, official 5 seeds x both seats, real env.run
     (g6_timing_engine_v2.py method).

G2's margin jobs and G5's jobs are dispatched into ONE shared multiprocessing Pool
(--workers) so they run in parallel; G0/G1/G3/G4/G6 are short and run around them.

Usage:
    python tools/tape_gates.py --cand submissions/submission_v888_jatape.py \
        --base submissions/submission_v887_fixord.py --team "Joseph Adamski" \
        --src logs/ja_56557382:56557382 --src logs/ja_56524217:56524217 \
        --outdir analysis/tape_ja_selfcheck/ --workers 8
"""
import argparse
import ast
import copy
import glob
import json
import os
import py_compile
import random
import sys
import time
from multiprocessing import Pool

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
from logio import load_log

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

OFFICIAL_SEEDS = [7, 17, 27, 37, 47]

# AGENTS.md §1의 4번 항목(archive 프록시 6종) + 이전 기준선 2종 = G4 회귀 세트.
# make_g4_jobs.py의 OPPS 그대로 (경로만 상대경로 유지).
G4_OPPS = {
    'v850': 'submissions/submission_v850.py',
    'v830': 'submissions/submission_v830.py',
    'arc_v89': 'submissions/archive/submission_v89.py',
    'arc_v89r': 'submissions/archive/submission_v89r.py',
    'arc_v87': 'submissions/archive/submission_v87.py',
    'arc_8.3': 'submissions/archive/submission8.3.py',
    'arc_8.2': 'submissions/archive/submission8.2.py',
    'arc_v85': 'submissions/archive/submission_v85.py',
}

FORBIDDEN_SNIPPETS = ['open(', 'import os', 'requests', 'urllib', 'socket']


# ---------------------------------------------------------------------------
# candidate wrapper: __raw_path__ injection + oracle telemetry (AGENTS §9 checklist #4)
# ---------------------------------------------------------------------------
# 후보를 함수로 env.run에 넘기면 build_agent가 configuration["__raw_path__"]를 채워주지 않는다
# (문자열 경로일 때만 채워줌). 자기 파일을 다시 읽는 오라클 레이어가 조용히 꺼지므로,
# 호출마다 cfg *사본*에 __raw_path__=<후보 절대경로>를 넣는다(관측·env.configuration은 수정 안 함).
# 표준 구현: tools/t0925/run_h2h.py:44-50. 테스트에서만 False로 바꾼다(검증 (b)).
INJECT_RAW_PATH = True


def make_cand_agent(cand_path, ns):
    """ns(exec된 후보 네임스페이스)의 에이전트를 cfg 사본 주입 래퍼로 감싼다. 반환: (agent_fn, read_orc)."""
    final = ns.get('kaggle_submission_agent') or ns.get('agent')

    def cand_agent(obs, cfg=None):
        if INJECT_RAW_PATH:
            cfg2 = {'__raw_path__': cand_path} if cfg is None else dict(cfg)
            cfg2['__raw_path__'] = cand_path
        else:
            cfg2 = cfg
        return final(obs, cfg2)

    def read_orc():
        # run_h2h.py:83-107 방식: 감싸는 레이어가 agent.telemetry를 덮어쓸 수 있어 ns의 _ORC_REPORT를 먼저 읽는다.
        tel = ns.get('_ORC_REPORT')
        if tel is None:
            t2 = getattr(final, 'telemetry', None)
            tel = t2 if isinstance(t2, dict) and 'orc_on' in t2 else None
        if not isinstance(tel, dict):
            return dict(orc_on=None, orc_off_reason=None, orc_fires=None, has_oracle=False)
        return dict(orc_on=int(tel.get('orc_on', 0)), orc_off_reason=tel.get('orc_off_reason'),
                    orc_fires=tel.get('orc_fires'), has_oracle=True)

    return cand_agent, read_orc


def orc_invalid_report(rows, label_fn):
    """오라클이 있는 후보인데 orc_on==0인 실행이 1건이라도 있으면 그 그룹은 INVALID.
    label_fn(row) -> 그룹 이름(cand/base). orc_on is None(오라클 레이어 없음)은 해당 없음으로 유효."""
    out = {}
    for r in rows:
        g = out.setdefault(label_fn(r), {'n': 0, 'n_orc_on': 0, 'n_orc_off': 0, 'n_no_oracle': 0, 'reasons': []})
        g['n'] += 1
        if r.get('orc_on') is None:
            g['n_no_oracle'] += 1
        elif r['orc_on'] == 1:
            g['n_orc_on'] += 1
        else:
            g['n_orc_off'] += 1
            g['reasons'].append('%s: orc_off_reason=%r' % (r.get('ep_id', (r.get('seed'), r.get('seat'))), r.get('orc_off_reason')))
    for g in out.values():
        g['valid'] = g['n_orc_off'] == 0
    return out


def canon(a):
    return json.dumps(a, sort_keys=True, separators=(',', ':'))


def pad_hands(a, n):
    a = dict(a or {})
    h = list(a.get('hands') or [])
    h += [['PASS']] * max(0, n - len(h))
    a['hands'] = h[:n]
    a.setdefault('farmer', ['PASS'])
    a.setdefault('market', [])
    return a


# ---------------------------------------------------------------------------
# G0
# ---------------------------------------------------------------------------
def gate0(cand_path, outdir):
    result = {'gate': 'G0', 'cand': cand_path}
    size = os.path.getsize(cand_path)
    result['file_size_bytes'] = size
    src = open(cand_path).read()
    try:
        ast.parse(src)
        py_compile.compile(cand_path, doraise=True)
        result['py_compile_ok'] = True
        result['py_compile_error'] = None
    except Exception as e:
        result['py_compile_ok'] = False
        result['py_compile_error'] = str(e)
    hits = []
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in src:
            hits.append(snippet)
    result['forbidden_strings_found'] = hits
    result['forbidden_clean'] = len(hits) == 0
    write_jsonl(os.path.join(outdir, 'g0.jsonl'), [result])
    return result


# ---------------------------------------------------------------------------
# generic head-to-head job (G1/G3/G4)
# ---------------------------------------------------------------------------
def h2h_job(j):
    from kaggle_environments import make
    cand = os.path.join(ROOT, j['cand'])
    opp = os.path.join(ROOT, j['opp'])
    seat = j['seat']
    seed = j['seed']
    agents = [None, None]
    agents[seat] = cand
    agents[1 - seat] = opp
    t0 = time.time()
    env = make('kaggriculture', configuration={'seed': seed, 'actTimeout': 1})
    env.run(agents)
    dt = time.time() - t0
    last = env.steps[-1]
    rw = [s.reward for s in last]
    statuses = [s.status for s in last]
    r = dict(j)
    r.update(status=statuses, nsteps=len(env.steps), me=rw[seat], them=rw[1 - seat],
             margin=rw[seat] - rw[1 - seat], wall_s=round(dt, 2))
    return r


def run_h2h_pool(jobs, workers, out_path):
    with Pool(min(workers, max(1, len(jobs))), maxtasksperchild=1) as pool:
        rows = list(pool.imap_unordered(h2h_job, jobs))
    write_jsonl(out_path, rows)
    return rows


# ---------------------------------------------------------------------------
# G1 / G3 / G4 job builders
# ---------------------------------------------------------------------------
def build_g1_jobs(cand, base):
    return [{'key': f'g1_{seed}_{seat}', 'cand': cand, 'opp': base, 'seed': seed, 'seat': seat, 'kind': 'g1'}
            for seed in OFFICIAL_SEEDS for seat in (0, 1)]


def build_g3_jobs(cand, base, extra_seeds=None):
    extra = extra_seeds if extra_seeds is not None else random.Random(887).sample(range(1000, 100000), 20)
    seeds = list(extra) + list(OFFICIAL_SEEDS)
    return [{'key': f'g3_{seed}_{seat}', 'cand': cand, 'opp': base, 'seed': seed, 'seat': seat, 'kind': 'g3'}
            for seed in seeds for seat in (0, 1)], seeds


def build_g4_jobs(cand):
    jobs = []
    for name, path in G4_OPPS.items():
        for seed in OFFICIAL_SEEDS:
            for seat in (0, 1):
                jobs.append({'key': f'g4_{name}_{seed}_{seat}', 'cand': cand, 'opp': path,
                              'seed': seed, 'seat': seat, 'kind': 'g4', 'opp_name': name})
    return jobs


# ---------------------------------------------------------------------------
# G2: pool episode scan (team detection) + pure-function purity + env margin
# ---------------------------------------------------------------------------
def scan_team_episodes(folders, team):
    """folders: [(folder, source), ...]. Returns list of {path, source, ep_id}."""
    out = []
    for folder, source in folders:
        files = sorted(glob.glob(os.path.join(folder, '*.json.gz')))
        if not files:
            files = sorted(glob.glob(os.path.join(folder, '*.json')))
        for path in files:
            try:
                d = load_log(path)
            except Exception:
                continue
            info = d.get('info', {})
            teams = info.get('TeamNames')
            if not teams or len(teams) != 2:
                continue
            if teams[0] == team and teams[1] == team:
                continue
            if team not in teams:
                continue
            steps = d.get('steps')
            if not steps or len(steps) < 720:
                continue
            out.append({'path': path, 'source': source, 'ep_id': d.get('id') or os.path.basename(path),
                         'seat': teams.index(team)})
    return out


def load_agent_ns(path, name='cand'):
    ns = {'__name__': name}
    exec(compile(open(path).read(), path, 'exec'), ns)
    return ns


def g2_purity_eval(ns, ep, team):
    """pure-function replay, g2_check_v2.py method."""
    agent_fn = ns['kaggle_submission_agent']
    d = load_log(ep['path'])
    ja = ep['seat']
    steps = d['steps']
    n_steps = 0
    n_match = 0
    for t in range(719):
        obs = steps[t][ja]['observation']
        recorded = steps[t + 1][ja].get('action') or {}
        n_hands = len(obs.get('farms', [{}] * (ja + 1))[ja].get('hands', []))
        try:
            got = agent_fn(obs, None)
        except Exception:
            got = {'farmer': ['PASS'], 'hands': [['PASS']] * n_hands, 'market': []}
        got_p = pad_hands(got, n_hands)
        rec_p = pad_hands(recorded, n_hands)
        n_steps += 1
        if canon(got_p) == canon(rec_p):
            n_match += 1
    return {'ep_id': ep['ep_id'], 'source': ep['source'], 'seat': ja,
            'n_steps': n_steps, 'n_match': n_match,
            'match_frac': n_match / n_steps if n_steps else 0}


def g2margin_job(j):
    """real env.run, cand in team's seat, opponent replayed from recorded tape.
    g2b_margin_v3.py method."""
    from kaggle_environments import make
    t_job0 = time.time()

    def tape(acts):
        def agent(obs, cfg=None):
            step = int(obs['step'])
            a = copy.deepcopy(acts[min(step, len(acts) - 1)] or {})
            exp = len(obs['farms'][int(obs['player'])]['hands'])
            h = list(a.get('hands') or [])
            h += [['PASS']] * (exp - len(h))
            a['hands'] = h[:exp]
            a.setdefault('farmer', ['PASS'])
            a.setdefault('market', [])
            return a
        return agent

    d = load_log(j['path'])
    st = d['steps']
    seat = j['seat']
    op = 1 - seat
    opp_acts = [st[t + 1][op].get('action') or {} for t in range(len(st) - 1)]
    opp = tape(opp_acts)
    seed = d['info']['seed']
    ns = {'__name__': 'g2margin_cand'}
    exec(compile(open(os.path.join(ROOT, j['cand_path'])).read(), j['cand_path'], 'exec'), ns)
    cand_fn, read_orc = make_cand_agent(os.path.join(ROOT, j['cand_path']), ns)
    ags = [None, None]
    ags[seat] = cand_fn
    ags[1 - seat] = opp
    env = make('kaggriculture', configuration={'seed': seed, 'actTimeout': 1})
    env.run(ags)
    last = env.steps[-1]
    rw = [s.reward for s in last]
    recorded_final = st[-1][seat].get('reward')
    r = dict(source=j['source'], ep_id=j['ep_id'], seat=seat, match_frac=j['match_frac'], kind='g2margin')
    r.update(status=[s.status for s in last], nsteps=len(env.steps),
             our_reward=rw[seat], opp_reward=rw[1 - seat], our_margin=rw[seat] - rw[1 - seat],
             recorded_reward=recorded_final,
             reward_diff=(rw[seat] - recorded_final) if recorded_final is not None else None,
             wall_s=round(time.time() - t_job0, 3), **read_orc())
    return r


# ---------------------------------------------------------------------------
# G5: our real-play pool(s), cand+base each replayed into our seat
# ---------------------------------------------------------------------------
def scan_g5_folders_once(folders):
    """G5 폴더들을 한 번만 읽어 팀명 판별과 에피소드 목록 구성에 함께 쓴다
    (기존 detect_our_name + scan_our_episodes 이중 load_log 중복 제거, review A).
    반환: [{path, teams, ep_id, n_steps}, ...] (모든 판단은 나중에 별도로 한다)."""
    out = []
    for folder in folders:
        files = sorted(glob.glob(os.path.join(folder, '*.json.gz')))
        if not files:
            files = sorted(glob.glob(os.path.join(folder, '*.json')))
        for path in files:
            try:
                d = load_log(path)
            except Exception:
                continue
            info = d.get('info', {})
            teams = info.get('TeamNames')
            steps = d.get('steps')
            out.append({'path': path, 'teams': teams, 'ep_id': d.get('id') or os.path.basename(path),
                        'n_steps': len(steps) if steps else 0})
    return out


def determine_our_name(raw, override=None, fallback=None):
    """등장 팀명 중 가장 흔한 것을 우리 팀명으로 자동 판별한다(--our-name으로 강제 지정 가능)."""
    if override:
        return override
    counts = {}
    for r in raw:
        teams = r['teams']
        if not teams or len(teams) != 2:
            continue
        for t in set(teams):
            counts[t] = counts.get(t, 0) + 1
    if not counts:
        return fallback
    return max(counts, key=counts.get)


def build_g5_episodes(raw, our_name):
    out = []
    for r in raw:
        teams = r['teams']
        if not teams or len(teams) != 2:
            continue
        if our_name not in teams:
            continue
        if teams[0] == teams[1]:
            continue
        if r['n_steps'] < 720:
            continue
        us = teams.index(our_name)
        out.append({'path': r['path'], 'ep_id': r['ep_id'], 'our_seat': us, 'opp_team': teams[1 - us]})
    return out


def g5_job(j):
    """real env.run, cand_key ('cand' or 'base') in our seat, opponent replayed. g5_runner.py method."""
    from kaggle_environments import make
    t_job0 = time.time()

    def tape(acts):
        def agent(obs, cfg=None):
            step = int(obs['step'])
            a = copy.deepcopy(acts[min(step, len(acts) - 1)] or {})
            exp = len(obs['farms'][int(obs['player'])]['hands'])
            h = list(a.get('hands') or [])
            h += [['PASS']] * (exp - len(h))
            a['hands'] = h[:exp]
            a.setdefault('farmer', ['PASS'])
            a.setdefault('market', [])
            return a
        return agent

    d = load_log(j['path'])
    st = d['steps']
    us = j['our_seat']
    op = 1 - us
    opp_acts = [st[t + 1][op].get('action') or {} for t in range(len(st) - 1)]
    opp = tape(opp_acts)
    seed = d['info']['seed']
    cand_path = os.path.join(ROOT, j['cand_path'])
    ns = {'__name__': 'g5_' + j['cand_key'] + '_' + str(j['ep_id'])}
    exec(compile(open(cand_path).read(), cand_path, 'exec'), ns)
    cand_fn, read_orc = make_cand_agent(cand_path, ns)
    ags = [None, None]
    ags[us] = cand_fn
    ags[1 - us] = opp
    env = make('kaggriculture', configuration={'seed': seed, 'actTimeout': 1})
    env.run(ags)
    last = env.steps[-1]
    rw = [s.reward for s in last]
    r = dict(cand_key=j['cand_key'], ep_id=j['ep_id'], our_seat=us, opp_team=j['opp_team'],
              folder=j['folder'], kind='g5')
    r.update(status=[s.status for s in last], nsteps=len(env.steps),
             our_reward=rw[us], opp_reward=rw[1 - us], margin=rw[us] - rw[1 - us],
             wall_s=round(time.time() - t_job0, 3), **read_orc())
    return r


# ---------------------------------------------------------------------------
# G6
# ---------------------------------------------------------------------------
def heavy_dispatch(j):
    if j['kind'] == 'g2margin':
        return g2margin_job(j)
    return g5_job(j)


def g6_job(args):
    from kaggle_environments import make
    seed, seat, cand_path, base_path = args
    ns = {'__name__': 'cand_g6'}
    exec(compile(open(cand_path).read(), cand_path, 'exec'), ns)
    cand_fn, read_orc = make_cand_agent(cand_path, ns)
    timings = []

    def wrapped(obs, cfg=None):
        t0 = time.perf_counter()
        r = cand_fn(obs, cfg)
        timings.append(time.perf_counter() - t0)
        return r

    ags = [None, None]
    ags[seat] = wrapped
    ags[1 - seat] = os.path.join(ROOT, base_path)
    env = make('kaggriculture', configuration={'seed': seed, 'actTimeout': 1})
    env.run(ags)
    last = env.steps[-1]
    status = [s.status for s in last]
    return {'seed': seed, 'seat': seat, 'status': status, 'nsteps': len(env.steps),
            'n_calls': len(timings), 'max_dt': max(timings) if timings else None,
            'first_dt': timings[0] if timings else None, **read_orc()}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def write_jsonl(path, rows):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, 'w') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cand', required=True)
    ap.add_argument('--base', default='submissions/submission_v888_jatape.py',
                     help='비교 대상(기본: submissions/submission_v888_jatape.py = 현행 배포본)')
    ap.add_argument('--team', required=True)
    ap.add_argument('--src', action='append', required=True, help='<폴더>:<제출번호>, 여러 개 가능')
    ap.add_argument('--outdir', required=True)
    ap.add_argument('--workers', type=int, default=8)
    ap.add_argument('--our-name', default=None, help='G5용 우리 팀명(기본: --team과 동일 자동 판별)')
    ap.add_argument('--g5-folder', action='append', default=None,
                     help='G5 실전 풀 폴더(상대경로), 여러 개 가능. 기본: logs/weense_g5,logs/s56642280,logs/s56657622')
    ap.add_argument('--g3-seeds', type=int, nargs='*', default=None,
                     help='G3 추가 시드 목록(생략 시 random.Random(887).sample(range(1000,100000),20))')
    args = ap.parse_args()

    outdir = args.outdir
    os.makedirs(outdir, exist_ok=True)
    cand_abs = args.cand if os.path.isabs(args.cand) else os.path.join(ROOT, args.cand)
    base_abs = args.base if os.path.isabs(args.base) else os.path.join(ROOT, args.base)
    g5_folders_rel = args.g5_folder or ['logs/weense_g5', 'logs/s56642280', 'logs/s56657622']
    g5_folders = [f if os.path.isabs(f) else os.path.join(ROOT, f) for f in g5_folders_rel]

    src_folders = []
    for s in args.src:
        folder, source = s.rsplit(':', 1)
        src_folders.append((folder if os.path.isabs(folder) else os.path.join(ROOT, folder), source))

    timing = {}
    loadavg = {}
    t_all0 = time.time()
    loadavg['start'] = os.getloadavg()

    # ---- G0 ----
    t0 = time.time()
    g0 = gate0(cand_abs, outdir)
    timing['G0'] = round(time.time() - t0, 2)
    print('G0', g0)

    # ---- review A: G5 폴더는 한 번만 읽는다(팀명 판별 + 에피소드 목록을 같은 raw 데이터에서 뽑는다) ----
    t0 = time.time()
    g5_raw = scan_g5_folders_once(g5_folders)
    our_name = determine_our_name(g5_raw, override=args.our_name, fallback=args.team)
    g5_episodes = build_g5_episodes(g5_raw, our_name)
    print('G5 our_name detected/used:', our_name, '| G5 pool size', len(g5_episodes))
    timing['scan_g5'] = round(time.time() - t0, 2)

    # ---- review B: G5 작업을 heavy pool에 먼저 넣는다(G2 순도 계산을 기다리지 않는다) ----
    g5_jobs = []
    for cand_key, cand_path in (('cand', args.cand), ('base', args.base)):
        for ep in g5_episodes:
            g5_jobs.append({'cand_key': cand_key, 'cand_path': cand_path, 'ep_id': ep['ep_id'],
                             'our_seat': ep['our_seat'], 'opp_team': ep['opp_team'], 'path': ep['path'],
                             'folder': os.path.basename(os.path.dirname(ep['path'])), 'kind': 'g5'})
    print('heavy pool: submitting G5 jobs first:', len(g5_jobs))
    t_heavy0 = time.time()
    heavy_pool = Pool(args.workers, maxtasksperchild=1)
    heavy_async = [heavy_pool.apply_async(heavy_dispatch, (j,)) for j in g5_jobs]

    # ---- G2 팀 에피소드 스캔 + 순도 계산 (heavy pool이 G5를 처리하는 동안 메인 프로세스에서 진행) ----
    t0 = time.time()
    g2_episodes = scan_team_episodes(src_folders, args.team)
    print('G2 pool size', len(g2_episodes))
    timing['scan_g2'] = round(time.time() - t0, 2)

    t0 = time.time()
    ns_cand = load_agent_ns(cand_abs, 'g2_purity_cand')
    g2_rows = [g2_purity_eval(ns_cand, ep, args.team) for ep in g2_episodes]
    write_jsonl(os.path.join(outdir, 'g2_purity.jsonl'), g2_rows)
    match_by_key = {(r['source'], r['ep_id']): r['match_frac'] for r in g2_rows}
    n_cond1 = sum(1 for r in g2_rows if r['match_frac'] >= 0.98)
    timing['G2_purity'] = round(time.time() - t0, 2)
    print('G2 purity match_frac>=0.98:', n_cond1, '/', len(g2_rows))

    # ---- G2 margin 작업을 같은 heavy pool에 추가 제출 ----
    g2margin_jobs = []
    for ep in g2_episodes:
        g2margin_jobs.append({'source': ep['source'], 'ep_id': ep['ep_id'], 'seat': ep['seat'],
                               'path': ep['path'], 'match_frac': match_by_key.get((ep['source'], ep['ep_id']), 0),
                               'cand_path': args.cand, 'kind': 'g2margin'})
    print('heavy pool: submitting G2 margin jobs:', len(g2margin_jobs))
    heavy_async += [heavy_pool.apply_async(heavy_dispatch, (j,)) for j in g2margin_jobs]
    heavy_pool.close()
    loadavg['heavy_pool_all_submitted'] = os.getloadavg()

    # ---- G1 (10 games), G3 (50 games), G4 (80 games), G6 (10 games) run while heavy pool churns ----
    small_workers = max(1, min(2, args.workers))

    t0 = time.time()
    g1_jobs = build_g1_jobs(args.cand, args.base)
    g1_rows = run_h2h_pool(g1_jobs, small_workers, os.path.join(outdir, 'g1.jsonl'))
    timing['G1'] = round(time.time() - t0, 2)
    print('G1 done', len(g1_rows), 'games')

    t0 = time.time()
    g3_jobs, g3_seed_list = build_g3_jobs(args.cand, args.base, args.g3_seeds)
    g3_rows = run_h2h_pool(g3_jobs, small_workers, os.path.join(outdir, 'g3.jsonl'))
    timing['G3'] = round(time.time() - t0, 2)
    print('G3 done', len(g3_rows), 'games, seeds=', g3_seed_list)

    t0 = time.time()
    g4_jobs = build_g4_jobs(args.cand)
    g4_rows = run_h2h_pool(g4_jobs, small_workers, os.path.join(outdir, 'g4.jsonl'))
    timing['G4'] = round(time.time() - t0, 2)
    print('G4 done', len(g4_rows), 'games')

    t0 = time.time()
    g6_args = [(s, seat, cand_abs, args.base) for s in OFFICIAL_SEEDS for seat in (0, 1)]
    with Pool(small_workers, maxtasksperchild=1) as p:
        g6_rows = list(p.imap_unordered(g6_job, g6_args))
    write_jsonl(os.path.join(outdir, 'g6.jsonl'), g6_rows)
    timing['G6'] = round(time.time() - t0, 2)
    print('G6 done', len(g6_rows), 'games')

    # ---- collect heavy pool (review C: 결과에서 wall_s 최대·중앙값 기록) ----
    loadavg['before_heavy_get'] = os.getloadavg()
    heavy_rows = [ar.get() for ar in heavy_async]
    heavy_pool.join()
    loadavg['after_heavy_join'] = os.getloadavg()
    timing['G2margin_G5_parallel'] = round(time.time() - t_heavy0, 2)
    g2margin_rows = [r for r in heavy_rows if r['kind'] == 'g2margin']
    g5_rows = [r for r in heavy_rows if r['kind'] == 'g5']
    write_jsonl(os.path.join(outdir, 'g2_margin.jsonl'), g2margin_rows)
    write_jsonl(os.path.join(outdir, 'g5.jsonl'), g5_rows)
    n_cond2 = sum(1 for r in g2margin_rows if r['reward_diff'] is not None and abs(r['reward_diff']) <= 50)
    print('G2 margin |diff|<=50:', n_cond2, '/', len(g2margin_rows))
    g5_cand = [r for r in g5_rows if r['cand_key'] == 'cand']
    g5_base = [r for r in g5_rows if r['cand_key'] == 'base']
    g5_cand_wins = sum(1 for r in g5_cand if r['margin'] > 0)
    g5_base_wins = sum(1 for r in g5_base if r['margin'] > 0)
    print('G5 wins: cand', g5_cand_wins, '/', len(g5_cand), 'base', g5_base_wins, '/', len(g5_base))

    # ---- 오라클 off 배치 무효화 (AGENTS §9 #4): 오라클 후보인데 orc_on==0 실행이 1건이라도 있으면 INVALID ----
    orc_report = {
        'G2': orc_invalid_report(g2margin_rows, lambda r: 'cand'),
        'G5': orc_invalid_report(g5_rows, lambda r: r['cand_key']),
        'G6': orc_invalid_report(g6_rows, lambda r: 'cand'),
    }
    for gate, rep in orc_report.items():
        for grp, g in rep.items():
            if not g['valid']:
                print('!! %s INVALID (%s): 오라클 후보인데 orc_on==0 실행 %d/%d건 -> 이 게이트 결과 무효.\n   %s'
                      % (gate, grp, g['n_orc_off'], g['n'], '; '.join(g['reasons'][:10])))

    heavy_wall = sorted(r['wall_s'] for r in heavy_rows if r.get('wall_s') is not None)

    def _median(xs):
        n = len(xs)
        if not n:
            return None
        mid = n // 2
        return xs[mid] if n % 2 else (xs[mid - 1] + xs[mid]) / 2

    timing['TOTAL'] = round(time.time() - t_all0, 2)

    # ---- summary ----
    g1_errors = sum(1 for r in g1_rows if r['status'] != ['DONE', 'DONE'] or r['nsteps'] != 720)
    g3_cand_wins = sum(1 for r in g3_rows if r['margin'] > 0)
    g4_by_opp = {}
    for name in G4_OPPS:
        rs = [r for r in g4_rows if r['opp_name'] == name]
        g4_by_opp[name] = {'n': len(rs), 'wins': sum(1 for r in rs if r['margin'] > 0),
                            'margin_avg': (sum(r['margin'] for r in rs) / len(rs)) if rs else None}
    g6_max_dt = max((r['max_dt'] for r in g6_rows if r['max_dt'] is not None), default=None)

    summary = {
        'oracle_check': orc_report,
        'INVALID_GATES': sorted('%s(%s)' % (gate, grp) for gate, rep in orc_report.items()
                                for grp, g in rep.items() if not g['valid']),
        'cand': args.cand, 'base': args.base, 'team': args.team, 'our_name': our_name,
        'src': args.src, 'g5_folders': g5_folders_rel, 'workers': args.workers,
        'timing_sec': timing,
        'loadavg': loadavg,
        'heavy_wall_s': {'n': len(heavy_wall), 'median': _median(heavy_wall),
                          'max': heavy_wall[-1] if heavy_wall else None},
        'G0': g0,
        'G1': {'n': len(g1_rows), 'errors_or_incomplete': g1_errors},
        'G2': {'n_pool': len(g2_rows), 'purity_ge_0.98': n_cond1, 'purity_ge_0.98_frac': n_cond1 / len(g2_rows) if g2_rows else None,
               'margin_le_50': n_cond2, 'margin_le_50_frac': n_cond2 / len(g2margin_rows) if g2margin_rows else None},
        'G3': {'n': len(g3_rows), 'seeds': g3_seed_list, 'cand_wins': g3_cand_wins,
               'cand_winrate': g3_cand_wins / len(g3_rows) if g3_rows else None},
        'G4': {'opponents': g4_by_opp, 'n_total': len(g4_rows),
               'cand_wins_total': sum(v['wins'] for v in g4_by_opp.values())},
        'G5': {'n_pool': len(g5_episodes), 'cand_wins': g5_cand_wins, 'cand_n': len(g5_cand),
               'base_wins': g5_base_wins, 'base_n': len(g5_base)},
        'G6': {'n': len(g6_rows), 'max_step_dt_sec': g6_max_dt},
    }
    with open(os.path.join(outdir, 'summary.json'), 'w') as f:
        json.dump(summary, f, ensure_ascii=False, indent=1)
    print('wrote', os.path.join(outdir, 'summary.json'))
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()

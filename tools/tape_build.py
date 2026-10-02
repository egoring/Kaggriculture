"""tools/tape_build.py — generic offline builder for a scripted-team tenacious-replay tape
(오프라인 전용, 제출 파일에 포함 안 함).

Generalization of tools/build_ja_tape.py (kept unmodified as the v888/JA reference
implementation): takes --team/--src instead of hardcoding 'Joseph Adamski' and the
FOLDERS list, but keeps build_ja_tape.py's v3 rules verbatim (접두 일치 대표 선택,
a/b/c/d 단계, 빌드 자체 검사 + 불일치 리프 제거).

Rules (unchanged from build_ja_tape.py v3):
  대표 선택을 순수 "접두 일치" 원칙으로 강제한다. 이어붙인 열이 실제로 존재하지 않는 판이
  되는 것을 원천 차단하기 위해, 각 구간의 대표는 반드시 "그 구간 시작 전까지의 행동이
  이미 정해진 부모 대표(같은 좌석)와 정확히 같은 실제 판"의 연속 구간에서만 뽑는다.

  각 (구간, 키, 좌석)에 대해:
    a. 후보 = 같은 키·같은 좌석의 판 중, 앞부분 행동 [0:구간시작] 이 이미 정한
       부모 대표 접두(이 좌석 기준)와 정확히 같은 판.
    b. a가 0개면: 같은 키·반대 좌석의 판 중, 앞부분 행동이 이 좌석 부모 대표 접두와
       정확히 같은 판.
    c. b도 0개면: 이 (키,좌석) 항목을 표에서 뺀다. 접두가 다른 판으로 채우지 않는다.
    d. 후보가 있으면: --src 인자 중 먼저 쓴 것(=최신, NEWEST_SOURCE) 후보가 있으면
       그것만, 없으면 다음 소스 후보로, 그 안에서 가장 많이 나온 [구간시작:구간끝]
       행동 열을 대표로 쓴다. (--src 는 여러 개 줄 수 있고, 먼저 쓴 것이 최신/대표
       선택 우선순위 1순위 — build_ja_tape.py의 FOLDERS 순서와 동일 의미)

구간 경계 72/144/216은 게임 규칙(townShopUnlockInterval=3일=72스텝)이라 공통이며
바꾸지 않는다.

Usage:
    python tools/tape_build.py --team "Joseph Adamski" \
        --src logs/ja_56557382:56557382 --src logs/ja_56524217:56524217 \
        --out-build analysis/tape_generic/ja_build.json \
        --report analysis/tape_generic/ja_report.json
"""
import argparse
import base64
import collections
import glob
import json
import os
import sys
import zlib

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
from logio import load_log

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

B_COMMON_END = 72   # t=0..71 공통
B_S1_END = 144       # t=72..143 s1
B_S2_END = 216       # t=144..215 s2
B_S3_END = 719       # t=216..718 s3


def canon(seq):
    """액션 열을 정렬키 비교 가능한 캐노니컬 JSON 문자열로."""
    return json.dumps(seq, sort_keys=True, separators=(',', ':'))


def load_episode(path, source, team):
    try:
        d = load_log(path)
    except Exception as e:
        return None, f'load_error:{e}'
    info = d.get('info', {})
    teams = info.get('TeamNames')
    if not teams or len(teams) != 2:
        return None, 'bad_teams'
    if teams[0] == team and teams[1] == team:
        return None, 'mirror'
    if team not in teams:
        return None, 'no_team'
    ja = teams.index(team)
    steps = d['steps']
    if len(steps) < 720:
        return None, 'short'
    try:
        shops72 = steps[B_COMMON_END][0]['observation']['town']['unlocked_shops']
        shops144 = steps[B_S1_END][0]['observation']['town']['unlocked_shops']
        shops216 = steps[B_S2_END][0]['observation']['town']['unlocked_shops']
    except Exception as e:
        return None, f'shop_err:{e}'
    s1 = tuple(shops72[:1])
    s2 = tuple(shops144[:2])
    s3 = tuple(shops216[:3])
    actions = []
    for t in range(719):
        a = steps[t + 1][ja].get('action') or {}
        actions.append(a)
    ep_id = d.get('id') or os.path.basename(path)
    seed = info.get('seed')
    return {
        'seat': ja, 's1': s1, 's2': s2, 's3': s3, 'actions': actions,
        'source': source, 'id': ep_id, 'seed': seed,
    }, None


def load_all_episodes(folders, team):
    episodes = []
    skip_reasons = collections.Counter()
    per_folder = {}
    for folder, source in folders:
        files = sorted(glob.glob(os.path.join(folder, '*.json.gz')))
        if not files:
            files = sorted(glob.glob(os.path.join(folder, '*.json')))
        per_folder[source] = {'total_files': len(files)}
        ok = 0
        for f in files:
            ep, reason = load_episode(f, source, team)
            if ep is None:
                skip_reasons[reason] += 1
                continue
            episodes.append(ep)
            ok += 1
        per_folder[source]['used'] = ok
    return episodes, skip_reasons, per_folder


def pick_rep(cands, lo, hi, newest_source):
    """cands: candidate episodes already filtered to match the exact parent prefix
    (same seat, or opposite seat as fallback). Prefer newest_source subset, else all."""
    if not cands:
        return None, None
    newest = [e for e in cands if e['source'] == newest_source]
    older = [e for e in cands if e['source'] != newest_source]
    pool = newest if newest else older
    cnt = collections.Counter(canon(e['actions'][lo:hi]) for e in pool)
    rep_canon = cnt.most_common(1)[0][0]
    mismatch = None
    if newest and older:
        cnt_o = collections.Counter(canon(e['actions'][lo:hi]) for e in older)
        rep_o_canon = cnt_o.most_common(1)[0][0]
        mismatch = (rep_o_canon != rep_canon)
    return json.loads(rep_canon), mismatch


def get_candidates(seatmap, seat, lo, parent_prefix):
    """rule a/b: parent_prefix is the canon() of this seat's already-chosen parent
    action prefix (or canon([]) at the common level, i.e. trivially true).
    Returns the candidate episode list, or None if rule c fires (drop)."""
    same = seatmap.get(seat, [])
    if lo == 0:
        cand = same
    else:
        cand = [e for e in same if canon(e['actions'][:lo]) == parent_prefix]
    if cand:
        return cand
    opp = seatmap.get(1 - seat, [])
    if lo == 0:
        cand2 = opp
    else:
        cand2 = [e for e in opp if canon(e['actions'][:lo]) == parent_prefix]
    if cand2:
        return cand2
    return None


def build_level(groups, lo, hi, parent_prefix_fn, stats, level_name, newest_source):
    """groups: {key: {seat: [episodes]}}. parent_prefix_fn(key, seat) -> list|None
    (the seat's chosen parent action prefix; None means the parent itself is missing
    for this seat, so this key/seat cannot be built).
    A key is kept only if BOTH seats resolve to a rep (rule a/b/c per seat, but if
    either seat ends up with no valid candidate the whole key is dropped -- this
    avoids asymmetric single-seat entries that the runtime's own-seat/opposite-seat
    fallback could later re-splice inconsistently)."""
    table = {}
    dropped_keys = []
    for key, seatmap in groups.items():
        reps = {}
        ok = True
        for seat in (0, 1):
            parent_prefix_list = parent_prefix_fn(key, seat)
            if parent_prefix_list is None:
                ok = False
                break
            parent_prefix = canon(parent_prefix_list)
            cand = get_candidates(seatmap, seat, lo, parent_prefix)
            if cand is None:
                ok = False
                break
            rep, mismatch = pick_rep(cand, lo, hi, newest_source)
            reps[seat] = rep
            if mismatch:
                stats['version_mismatch_keys'][level_name] += 1
        if ok:
            table[key] = reps
        else:
            dropped_keys.append(key)
    stats['dropped'][level_name] = len(dropped_keys)
    return table, dropped_keys


def build(folders, team, out_build_path):
    newest_source = folders[0][1]  # 먼저 쓴 --src 가 최신/대표 우선순위 1순위
    episodes, skip_reasons, per_folder = load_all_episodes(folders, team)
    print('coverage_per_folder', json.dumps(per_folder, ensure_ascii=False))
    print('skip_reasons', json.dumps(skip_reasons, ensure_ascii=False))
    n_total = len(episodes)
    print('total_usable_episodes', n_total)

    stats = {
        'version_mismatch_keys': {'common': 0, 's1': 0, 's2': 0, 's3': 0},
        'dropped': {'common': 0, 's1': 0, 's2': 0, 's3': 0},
    }

    # ---- common (t 0..71), single group, no parent prefix (trivially matches) ----
    common_groups = {'_': collections.defaultdict(list)}
    for e in episodes:
        common_groups['_'][e['seat']].append(e)
    common_table, common_dropped = build_level(
        common_groups, 0, B_COMMON_END, lambda k, s: [], stats, 'common', newest_source)
    common_rep = common_table.get('_', {})

    # ---- s1 (t 72..143), grouped by s1, per seat; parent prefix = common_rep[seat] ----
    s1_groups = collections.defaultdict(lambda: collections.defaultdict(list))
    for e in episodes:
        s1_groups[e['s1']][e['seat']].append(e)
    s1_cov = {s1: {'n0': len(sm.get(0, [])), 'n1': len(sm.get(1, []))} for s1, sm in s1_groups.items()}

    def s1_parent(key, seat):
        return common_rep.get(seat)

    s1_table, s1_dropped = build_level(s1_groups, B_COMMON_END, B_S1_END, s1_parent, stats, 's1', newest_source)

    # ---- s2 (t 144..215), grouped by (s1,s2), per seat; parent prefix = common+s1 ----
    s2_groups = collections.defaultdict(lambda: collections.defaultdict(list))
    for e in episodes:
        s2_groups[(e['s1'], e['s2'])][e['seat']].append(e)
    s2_cov = {k: {'n0': len(sm.get(0, [])), 'n1': len(sm.get(1, []))} for k, sm in s2_groups.items()}

    def s2_parent(key, seat):
        s1, s2 = key
        if s1 not in s1_table or seat not in s1_table[s1]:
            return None
        c = common_rep.get(seat)
        if c is None:
            return None
        return c + s1_table[s1][seat]

    s2_table_flat, s2_dropped = build_level(s2_groups, B_S1_END, B_S2_END, s2_parent, stats, 's2', newest_source)
    s2_table = collections.defaultdict(dict)
    for (s1, s2), reps in s2_table_flat.items():
        s2_table[s1][s2] = reps

    # ---- s3 (t 216..718), grouped by (s1,s2,s3), per seat; parent prefix = common+s1+s2 ----
    s3_groups = collections.defaultdict(lambda: collections.defaultdict(list))
    for e in episodes:
        s3_groups[(e['s1'], e['s2'], e['s3'])][e['seat']].append(e)
    s3_cov = {k: {'n0': len(sm.get(0, [])), 'n1': len(sm.get(1, []))} for k, sm in s3_groups.items()}

    def s3_parent(key, seat):
        s1, s2, s3 = key
        if s1 not in s1_table or seat not in s1_table[s1]:
            return None
        if s2 not in s2_table.get(s1, {}) or seat not in s2_table[s1][s2]:
            return None
        c = common_rep.get(seat)
        if c is None:
            return None
        return c + s1_table[s1][seat] + s2_table[s1][s2][seat]

    s3_table_flat, s3_dropped = build_level(s3_groups, B_S2_END, B_S3_END, s3_parent, stats, 's3', newest_source)
    s3_table = collections.defaultdict(lambda: collections.defaultdict(dict))
    for (s1, s2, s3), reps in s3_table_flat.items():
        s3_table[s1][s2][s3] = reps

    print('n_s1_keys', len(s1_table))
    print('n_s2_keys', sum(len(v) for v in s2_table.values()))
    print('n_s3_keys', len(s3_table_flat))
    print('stats(before self-check pruning)', json.dumps(stats, ensure_ascii=False))

    # ---- self-check: reconstruct the full 719-step splice for every kept leaf
    # (s1,s2,s3,seat) exactly the way the runtime agent would, and verify it matches
    # a real recorded episode (any seat) byte-for-byte. Prune any leaf that doesn't. ----
    full_set = set(canon(e['actions']) for e in episodes)

    def seat_seq(rep, seat):
        if seat in rep:
            return rep[seat]
        return rep.get(1 - seat)

    checked = 0
    pruned = []
    for s1, s2d in list(s3_table.items()):
        for s2, s3d in list(s2d.items()):
            for s3, reps in list(s3d.items()):
                for seat in (0, 1):
                    c = common_rep.get(seat)
                    s1seg = s1_table.get(s1, {}).get(seat) if s1 in s1_table else None
                    s2seg = s2_table.get(s1, {}).get(s2, {}).get(seat) if s2 in s2_table.get(s1, {}) else None
                    s3seg = seat_seq(reps, seat)
                    if c is None or s1seg is None or s2seg is None or s3seg is None:
                        continue
                    checked += 1
                    splice = c + s1seg + s2seg + s3seg
                    if canon(splice) not in full_set:
                        pruned.append((s1, s2, s3, seat))
    for (s1, s2, s3, seat) in pruned:
        reps = s3_table[s1][s2][s3]
        reps.pop(seat, None)
        if not reps:
            del s3_table[s1][s2][s3]
            if not s3_table[s1][s2]:
                del s3_table[s1][s2]
            if not s3_table[s1]:
                del s3_table[s1]

    stats['self_check'] = {
        'checked_leaf_seat_pairs': checked,
        'pruned_leaf_seat_pairs': len(pruned),
        'pruned_list': [[list(s1), list(s2), list(s3), seat] for (s1, s2, s3, seat) in pruned],
    }
    print('self_check', json.dumps(stats['self_check'], ensure_ascii=False))

    os.makedirs(os.path.dirname(os.path.abspath(out_build_path)), exist_ok=True)

    return {
        'common': common_rep,
        's1': s1_table,
        's2': dict(s2_table),
        's3': {s1: {s2: dict(s3d) for s2, s3d in s2d.items()} for s1, s2d in s3_table.items()},
    }, {
        'n_total_episodes': n_total,
        's1_cov': {json.dumps(list(k)): v for k, v in s1_cov.items()},
        's2_cov': {json.dumps([list(a) for a in k]): v for k, v in s2_cov.items()},
        's3_cov': {json.dumps([list(a) for a in k]): v for k, v in s3_cov.items()},
        'per_folder': per_folder,
        'skip_reasons': dict(skip_reasons),
        'rep_selection_stats': stats,
    }, episodes


def compress_str(obj):
    raw = json.dumps(obj, separators=(',', ':')).encode('utf-8')
    comp = zlib.compress(raw, 9)
    b85 = base64.b85encode(comp).decode('ascii')
    return b85, len(raw), len(comp), len(b85)


def compute_purity_report(episodes, table, cov):
    """순도 보고(--report): 원본 판마다 표에서 조립한 열과 그 판 실제 행동이 719스텝 중
    몇 스텝 같은지(match_frac)의 분포(평균/중앙값/>=0.98 비율)."""
    common_rep = table['common']
    s1_table = table['s1']
    s2_table = table['s2']
    s3_table = table['s3']

    def seat_seq(rep, seat):
        if rep is None:
            return None
        if seat in rep:
            return rep[seat]
        return rep.get(1 - seat)

    match_fracs = []
    key_hits = 0
    for e in episodes:
        seat = e['seat']
        c = common_rep.get(seat)
        s1seg = seat_seq(s1_table.get(e['s1']), seat) if e['s1'] in s1_table else None
        s2seg = None
        s3seg = None
        s1_ok = e['s1'] in s1_table
        s2_ok = s1_ok and e['s2'] in s2_table.get(e['s1'], {})
        s3_ok = s2_ok and e['s3'] in s3_table.get(e['s1'], {}).get(e['s2'], {})
        if s2_ok:
            s2seg = seat_seq(s2_table[e['s1']][e['s2']], seat)
        if s3_ok:
            s3seg = seat_seq(s3_table[e['s1']][e['s2']][e['s3']], seat)
        built = list(c or [])
        built += list(s1seg or [])
        built += list(s2seg or [])
        built += list(s3seg or [])
        actual = e['actions']
        n = min(len(built), len(actual))
        matches = sum(1 for i in range(n) if canon(built[i]) == canon(actual[i]))
        match_frac = matches / len(actual) if actual else 0.0
        match_fracs.append(match_frac)
        if s1_ok and s2_ok and s3_ok:
            key_hits += 1

    n = len(match_fracs)
    mean = sum(match_fracs) / n if n else 0.0
    sorted_fracs = sorted(match_fracs)
    median = sorted_fracs[n // 2] if n else 0.0
    ge98 = sum(1 for f in match_fracs if f >= 0.98)
    return {
        'n_episodes_used': n,
        'n_keys_removed_by_prune': cov['rep_selection_stats']['self_check']['pruned_leaf_seat_pairs'],
        'skip_reasons': cov['skip_reasons'],
        'per_folder': cov['per_folder'],
        'n_s1_keys': len(s1_table),
        'n_s2_keys': sum(len(v) for v in s2_table.values()),
        'n_s3_keys': sum(len(v2) for v in s3_table.values() for v2 in v.values()),
        'key_hit_rate': key_hits / n if n else 0.0,
        'purity_match_frac': {
            'mean': mean,
            'median': median,
            'ge_0.98_count': ge98,
            'ge_0.98_frac': ge98 / n if n else 0.0,
            'n': n,
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--team', required=True, help='TeamNames 기준 팀명')
    ap.add_argument('--src', action='append', required=True,
                     help='<폴더>:<제출번호> 형식, 여러 개 가능. 먼저 쓴 것이 최신/대표 우선')
    ap.add_argument('--out-build', required=True)
    ap.add_argument('--report', required=True)
    args = ap.parse_args()

    folders = []
    for s in args.src:
        folder, source = s.rsplit(':', 1)
        if not os.path.isabs(folder):
            folder = os.path.join(ROOT, folder)
        folders.append((folder, source))

    table, cov, episodes = build(folders, args.team, args.out_build)

    common_json = {str(seat): seg for seat, seg in table['common'].items()}
    s1_json = {json.dumps(list(k)): {str(seat): seg for seat, seg in reps.items()}
               for k, reps in table['s1'].items()}

    def cov_n(covdict, key):
        c = covdict.get(key, {})
        return c.get('n0', 0) + c.get('n1', 0)

    s2_blocks = {}
    for s1, s2d in table['s2'].items():
        block = {json.dumps(list(s2)): {str(seat): seg for seat, seg in reps.items()} for s2, reps in s2d.items()}
        best_key, best_n = None, -1
        for s2 in s2d:
            n = cov_n(cov['s2_cov'], json.dumps([list(s1), list(s2)]))
            if n > best_n:
                best_n = n; best_key = json.dumps(list(s2))
        if best_key is not None:
            block['__default__'] = best_key
        s2_blocks[json.dumps(list(s1))] = block

    s3_blocks = {}
    for s1, s2d in table['s3'].items():
        for s2, s3d in s2d.items():
            blockkey = json.dumps([list(s1), list(s2)])
            block = {json.dumps(list(s3)): {str(seat): seg for seat, seg in reps.items()} for s3, reps in s3d.items()}
            best_key, best_n = None, -1
            for s3 in s3d:
                n = cov_n(cov['s3_cov'], json.dumps([list(s1), list(s2), list(s3)]))
                if n > best_n:
                    best_n = n; best_key = json.dumps(list(s3))
            if best_key is not None:
                block['__default__'] = best_key
            s3_blocks[blockkey] = block

    best_s1_key, best_s1_n = None, -1
    for s1 in table['s1']:
        n = cov_n(cov['s1_cov'], json.dumps(list(s1)))
        if n > best_s1_n:
            best_s1_n = n; best_s1_key = json.dumps(list(s1))
    if best_s1_key is not None:
        s1_json['__default__'] = best_s1_key

    b_common, raw_c, comp_c, b85_c = compress_str(common_json)
    print('common bytes: raw=%d comp=%d b85=%d' % (raw_c, comp_c, b85_c))

    b_s1, raw_1, comp_1, b85_1 = compress_str(s1_json)
    print('s1 bytes: raw=%d comp=%d b85=%d' % (raw_1, comp_1, b85_1))

    s2_compressed = {}
    tot_raw2 = tot_comp2 = tot_b85_2 = 0
    for k, v in s2_blocks.items():
        b, r, c, b85 = compress_str(v)
        s2_compressed[k] = b
        tot_raw2 += r; tot_comp2 += c; tot_b85_2 += b85
    print('s2 blocks=%d bytes: raw=%d comp=%d b85=%d' % (len(s2_blocks), tot_raw2, tot_comp2, tot_b85_2))

    s3_compressed = {}
    tot_raw3 = tot_comp3 = tot_b85_3 = 0
    for k, v in s3_blocks.items():
        b, r, c, b85 = compress_str(v)
        s3_compressed[k] = b
        tot_raw3 += r; tot_comp3 += c; tot_b85_3 += b85
    print('s3 blocks=%d bytes: raw=%d comp=%d b85=%d' % (len(s3_blocks), tot_raw3, tot_comp3, tot_b85_3))

    out = {
        'common': b_common,
        's1': b_s1,
        's2_blocks': s2_compressed,
        's3_blocks': s3_compressed,
    }
    with open(args.out_build, 'w') as f:
        json.dump({'blobs': out, 'coverage': cov}, f)
    print('wrote', args.out_build, 'total_bytes', os.path.getsize(args.out_build))
    total_b85 = b85_c + b85_1 + tot_b85_2 + tot_b85_3
    print('TOTAL_B85_BYTES', total_b85, '(~%.2f MB)' % (total_b85 / 1e6))

    report = compute_purity_report(episodes, table, cov)
    os.makedirs(os.path.dirname(os.path.abspath(args.report)), exist_ok=True)
    with open(args.report, 'w') as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    print('wrote report', args.report)
    print('purity_match_frac', json.dumps(report['purity_match_frac'], ensure_ascii=False))


if __name__ == '__main__':
    main()

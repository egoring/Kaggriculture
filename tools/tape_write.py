"""tools/tape_write.py — generic writer: <team>_tape_build.json -> single-file submission.py

Generalization of write_v888.py (see tools/build_ja_tape.py / write_v888.py for the v888
JA-specific originals, kept unmodified). The generated code (everything except the two
header comment lines) is byte-identical to write_v888.py's output — see build_source().

Usage:
    python tools/tape_write.py --build <build.json> --out <submission.py> \
        [--header "line1"] [--header "line2"] ...
    (헤더를 생략하면 write_v888.py의 두 헤더 줄 그대로 사용)
"""
import argparse
import json
import os

DEFAULT_HEADERS = [
    '# v888 = Joseph Adamski(JA) tenacious-replay reproduction (JA-TAPE).',
    '# Single-file, no external file/network access. Offline builder: tools/build_ja_tape.py (not included here).',
]

# Everything below is copied verbatim from write_v888.py's main()/code body so the
# generated runtime logic is byte-identical for the JA case (R1).
_CODE_BODY = r'''
PASS_ACTION = {"farmer": ["PASS"], "hands": [], "market": []}


def _get(obs, key, default=None):
    if isinstance(obs, dict):
        return obs.get(key, default)
    getter = getattr(obs, "get", None)
    if callable(getter):
        return getter(key, default)
    return getattr(obs, key, default)


def _step_of(observation):
    raw = _get(observation, "step")
    if raw is not None:
        try:
            return int(raw)
        except (TypeError, ValueError):
            pass
    try:
        return int(_get(observation, "day", 0)) * 24 + int(_get(observation, "hour", 0))
    except (TypeError, ValueError):
        return 0


_STATE = {}


def _fresh_state():
    return {
        "last_step": -1,
        "s1": None, "s2": None, "s3": None,
        "s1_key": None, "s2_key": None, "s3_key": None,
        "s2_fallback": False, "s3_fallback": False,
        "common_seq": None, "s1_seq": None, "s2_seq": None, "s3_seq": None,
    }


def _pad_hands(a, n_hands):
    a = dict(a or {})
    h = list(a.get("hands") or [])
    if len(h) < n_hands:
        h = h + [["PASS"]] * (n_hands - len(h))
    a["hands"] = h[:n_hands]
    a.setdefault("farmer", ["PASS"])
    a.setdefault("market", [])
    return a


def _telemetry_init():
    return {"s1_fallback": 0, "s2_fallback": 0, "s3_fallback": 0, "errors": 0, "steps": 0}


TELEMETRY = _telemetry_init()


def _seat_seq(rep, seat):
    """rep: {"0": seq, "1": seq}. seat is int 0/1."""
    key = str(seat)
    if key in rep:
        return rep[key]
    other = str(1 - seat)
    return rep.get(other)


def kaggle_submission_agent(observation, configuration=None):
    try:
        step = _step_of(observation)
        seat = int(_get(observation, "player", 0))
        farms = _get(observation, "farms", []) or []
        n_hands = 0
        if seat < len(farms):
            n_hands = len(_get(farms[seat], "hands", []) or [])

        st = _STATE.get(seat)
        if st is None or step == 0 or step <= st["last_step"]:
            st = _fresh_state()
            _STATE[seat] = st
        st["last_step"] = step
        TELEMETRY["steps"] += 1

        town = _get(observation, "town", {}) or {}
        shops = list(_get(town, "unlocked_shops", []) or [])

        # ---- common block t=0..71 ----
        if step < 72:
            seq = st["common_seq"]
            if seq is None:
                seq = _seat_seq(_COMMON, seat) or []
                st["common_seq"] = seq
            a = seq[step] if step < len(seq) else None
            return _pad_hands(a or PASS_ACTION, n_hands)

        # ---- s1 key latch at step>=72 ----
        if st["s1"] is None:
            s1 = tuple(shops[:1])
            st["s1"] = s1
            s1_key = json.dumps(list(s1))
            if s1_key not in _S1:
                s1_key = _S1.get("__default__")
                st["s1_fallback"] = True
                TELEMETRY["s1_fallback"] += 1
            st["s1_key"] = s1_key
            rep = _S1.get(s1_key, {}) if s1_key else {}
            st["s1_seq"] = _seat_seq(rep, seat) or []

        # ---- s1 block t=72..143 ----
        if step < 144:
            seq = st["s1_seq"] or []
            idx = step - 72
            a = seq[idx] if 0 <= idx < len(seq) else None
            return _pad_hands(a or PASS_ACTION, n_hands)

        # ---- s2 key latch at step>=144 ----
        if st["s2"] is None:
            s2 = tuple(shops[:2])
            st["s2"] = s2
            s2_key = json.dumps(list(s2))
            block = _get_s2_block(st["s1_key"]) if st["s1_key"] else {}
            if s2_key not in block:
                s2_key = block.get("__default__")
                st["s2_fallback"] = True
                TELEMETRY["s2_fallback"] += 1
            st["s2_key"] = s2_key
            rep = block.get(s2_key, {}) if s2_key else {}
            st["s2_seq"] = _seat_seq(rep, seat) or []

        # ---- s2 block t=144..215 ----
        if step < 216:
            seq = st["s2_seq"] or []
            idx = step - 144
            a = seq[idx] if 0 <= idx < len(seq) else None
            return _pad_hands(a or PASS_ACTION, n_hands)

        # ---- s3 key latch at step>=216 ----
        if st["s3"] is None:
            s3 = tuple(shops[:3])
            st["s3"] = s3
            s12_key = json.dumps([list(st["s1"]), list(st["s2"])])
            block = _get_s3_block(s12_key)
            s3_key = json.dumps(list(s3))
            if s3_key not in block:
                s3_key = block.get("__default__")
                st["s3_fallback"] = True
                TELEMETRY["s3_fallback"] += 1
            st["s3_key"] = s3_key
            rep = block.get(s3_key, {}) if s3_key else {}
            st["s3_seq"] = _seat_seq(rep, seat) or []

        # ---- s3 block t=216..718 ----
        seq = st["s3_seq"] or []
        idx = step - 216
        a = seq[idx] if 0 <= idx < len(seq) else None
        return _pad_hands(a or PASS_ACTION, n_hands)
    except Exception:
        TELEMETRY["errors"] += 1
        try:
            farms = _get(observation, "farms", []) or []
            seat = int(_get(observation, "player", 0))
            hands = _get(farms[seat], "hands", []) or [] if seat < len(farms) else []
            return {"farmer": ["PASS"], "hands": [["PASS"] for _ in hands], "market": []}
        except Exception:
            return copy.deepcopy(PASS_ACTION)


agent = kaggle_submission_agent
'''


# --s3-fallback-fix (default OFF): replaces ONLY the s3 key-latch block of _CODE_BODY.
# Bug: when s2 is absent from the tape, s2_key becomes the __default__ representative but
# s12_key was built from the *actual* shops -> _get_s3_block() returns {} -> steps 216+ all PASS.
_S3_LATCH_OLD = '''            s12_key = json.dumps([list(st["s1"]), list(st["s2"])])
            block = _get_s3_block(s12_key)
            s3_key = json.dumps(list(s3))
            if s3_key not in block:
                s3_key = block.get("__default__")
                st["s3_fallback"] = True
                TELEMETRY["s3_fallback"] += 1
            st["s3_key"] = s3_key
            rep = block.get(s3_key, {}) if s3_key else {}
            st["s3_seq"] = _seat_seq(rep, seat) or []
'''
_S3_LATCH_NEW = '''            # s12 key = keys actually used for s1/s2 (incl. __default__ fallbacks)
            if st["s1_key"] and st["s2_key"]:
                s12_key = json.dumps([json.loads(st["s1_key"]), json.loads(st["s2_key"])])
            else:
                s12_key = json.dumps([list(st["s1"]), list(st["s2"])])
            block = _get_s3_block(s12_key)
            s3_key = json.dumps(list(s3))
            if s3_key not in block:
                s3_key = block.get("__default__")
                st["s3_fallback"] = True
                TELEMETRY["s3_fallback"] += 1
            rep = block.get(s3_key, {}) if s3_key else {}
            seq = _seat_seq(rep, seat) or []
            if not seq:
                # still empty: any S3 block under the same s1 -> its __default__ representative
                s1_lst = json.loads(st["s1_key"]) if st["s1_key"] else list(st["s1"])
                for bk in _S3_BLOCKS_B85:
                    try:
                        if json.loads(bk)[0] != s1_lst:
                            continue
                        blk = _get_s3_block(bk)
                        dk = blk.get("__default__")
                        sq = _seat_seq(blk.get(dk, {}), seat) if dk else None
                        if sq:
                            s3_key, seq = dk, sq
                            st["s3_fallback"] = True
                            TELEMETRY["s3_fallback"] += 1
                            break
                    except Exception:
                        continue
            st["s3_key"] = s3_key
            st["s3_seq"] = seq
'''


def build_source(build_json, headers=None, s3_fallback_fix=False):
    """build_json: dict with key 'blobs' -> {'common','s1','s2_blocks','s3_blocks'} (b85 strings).
    headers: list of header comment lines (default: write_v888.py's two lines).
    s3_fallback_fix: default False -> output byte-identical to before."""
    blobs = build_json['blobs']
    code_body = _CODE_BODY
    if s3_fallback_fix:
        assert code_body.count(_S3_LATCH_OLD) == 1
        code_body = code_body.replace(_S3_LATCH_OLD, _S3_LATCH_NEW)
    headers = headers if headers else DEFAULT_HEADERS
    out = []
    for h in headers:
        out.append(h)
    out.append('from __future__ import annotations')
    out.append('import zlib, base64, json, copy')
    out.append('')
    out.append("_COMMON_B85 = '%s'" % blobs['common'])
    out.append("_S1_B85 = '%s'" % blobs['s1'])
    out.append('_S2_BLOCKS_B85 = %s' % json.dumps(blobs['s2_blocks']))
    out.append('_S3_BLOCKS_B85 = %s' % json.dumps(blobs['s3_blocks']))
    out.append('')
    out.append('_S2_CACHE = {}')
    out.append('_S3_CACHE = {}')
    out.append('')
    out.append('def _decode(b85):')
    out.append('    return json.loads(zlib.decompress(base64.b85decode(b85)).decode("utf-8"))')
    out.append('')
    out.append('_COMMON = _decode(_COMMON_B85)  # {"0": [...actions t=0..71...], "1": [...]}')
    out.append('_S1 = _decode(_S1_B85)          # {json([s1]): {"0": [...], "1": [...]}, "__default__": key}')
    out.append('')
    out.append('def _get_s2_block(s1_key):')
    out.append('    if s1_key in _S2_CACHE:')
    out.append('        return _S2_CACHE[s1_key]')
    out.append('    b85 = _S2_BLOCKS_B85.get(s1_key)')
    out.append('    block = _decode(b85) if b85 is not None else {}')
    out.append('    _S2_CACHE[s1_key] = block')
    out.append('    return block')
    out.append('')
    out.append('def _get_s3_block(s12_key):')
    out.append('    if s12_key in _S3_CACHE:')
    out.append('        return _S3_CACHE[s12_key]')
    out.append('    b85 = _S3_BLOCKS_B85.get(s12_key)')
    out.append('    block = _decode(b85) if b85 is not None else {}')
    out.append('    _S3_CACHE[s12_key] = block')
    out.append('    return block')
    out.append('')
    out.append(code_body)
    return '\n'.join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--build', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--header', action='append', default=None)
    ap.add_argument('--s3-fallback-fix', action='store_true',
                    help='fix s3 key latch when s2 was replaced by __default__ (default off)')
    args = ap.parse_args()

    build_json = json.load(open(args.build))
    src = build_source(build_json, headers=args.header, s3_fallback_fix=args.s3_fallback_fix)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, 'w') as f:
        f.write(src)
    print('wrote', args.out, len(src), 'bytes')


if __name__ == '__main__':
    main()

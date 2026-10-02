"""
bulk_replay_fetch.py — kaggriculture 리플레이(에피소드)를 EpisodeService 내부
API로 일괄 다운로드.

엔드포인트/payload는 실제 브라우저 curl로 검증됨 (2026-09-04):
  POST https://www.kaggle.com/api/i/competitions.EpisodeService/GetEpisode
  body: {"episodeId": <int>}
  → 인증은 세션 쿠키 + XSRF-TOKEN 쿠키 값을 x-xsrf-token 헤더에 그대로 실어야 통과.

⚠️ 아직 미검증인 부분: "제출 ID → 그 제출의 에피소드 ID 목록"을 가져오는 API
(list_episodes_for_submission / ListEpisodes 엔드포인트)는 확인된 curl이 없어서
추측입니다. 지금은 test-one으로 GetEpisode부터 검증하고, list가 필요하면
submissions 페이지에서 에피소드 목록이 로드/스크롤될 때 뜨는 네트워크 요청을
캡처해서 알려주세요 (test-one과 같은 방식).

사전 준비 (매번 쿠키가 만료되면 다시, 브라우저에서):
  1. kaggle.com 로그인 상태에서 리플레이 페이지 하나를 연다.
  2. DevTools(F12) > Network 탭 > "GetEpisode" 요청 찾기 > 우클릭 > Copy as cURL.
  3. 그 curl에서:
     -b/Cookie 값 전체            → COOKIE_STRING
     x-kaggle-build-version 헤더값 → BUILD_VERSION
     (x-xsrf-token은 COOKIE_STRING 안의 XSRF-TOKEN 값에서 스크립트가 자동으로 뽑아 씀)

사용법:
  단일 ID 스모크 테스트 (먼저 이것부터):
       python bulk_replay_fetch.py test-one --episode-id 105362250

  1) 내 제출들의 에피소드 ID 모으기 (엔드포인트 미검증 — 실패하면 알려주세요)
       python bulk_replay_fetch.py list --submission-ids 56003067 --out episode_ids.txt
  2) 모은 ID로 리플레이 JSON 일괄 다운로드 (중단됐다 재실행해도 이미 받은 건 건너뜀)
       python bulk_replay_fetch.py fetch --ids-file episode_ids.txt --out-dir replays/
"""
import argparse
import json
import re
import time
from pathlib import Path

import requests

BASE = "https://www.kaggle.com/api/i/competitions.EpisodeService"

# ↓↓↓ 브라우저 DevTools에서 복사한 값들을 여기 붙여넣기 ↓↓↓
import os
COOKIE_STRING = os.environ.get("KAGGLE_COOKIE_STRING", "")  # 브라우저 세션 쿠키 전체를 환경변수로 주입 (저장소에 넣지 말 것)
BUILD_VERSION = "ab8b2a36d6fed5aa25c79168f86df9ba10dd1673"  # 예: ab8b2a36d6fed5aa25c79168f86df9ba10dd1673
REFERER = "https://www.kaggle.com/competitions/kaggriculture/submissions"


def _xsrf_token_from_cookie(cookie_string: str) -> str:
    m = re.search(r"(?:^|;\s*)XSRF-TOKEN=([^;]+)", cookie_string)
    if not m:
        raise RuntimeError(
            "COOKIE_STRING 안에서 XSRF-TOKEN을 못 찾았습니다. "
            "브라우저에서 쿠키를 다시 복사해서 COOKIE_STRING에 넣어주세요."
        )
    return m.group(1)


def build_headers() -> dict:
    return {
        "accept": "application/json",
        "content-type": "application/json",
        "origin": "https://www.kaggle.com",
        "referer": REFERER,
        "user-agent": "Mozilla/5.0",
        "x-kaggle-build-version": BUILD_VERSION,
        "x-xsrf-token": _xsrf_token_from_cookie(COOKIE_STRING),
        "Cookie": COOKIE_STRING,
    }


def list_episodes_for_submission(session: requests.Session, submission_id: int) -> list:
    """제출 ID 하나에 딸린 에피소드 ID들을 모은다.
    ⚠️ 엔드포인트/필드명 미검증 — 실패하면 submissions 페이지에서 실제로
    캡처한 네트워크 요청을 기준으로 고쳐야 함."""
    payload = {"submissionId": submission_id}
    r = session.post(f"{BASE}/ListEpisodes", json=payload, headers=build_headers(), timeout=30)
    r.raise_for_status()
    data = r.json()
    eps = data.get("episodes") or data.get("result", {}).get("episodes", [])
    return [e["id"] for e in eps]


def fetch_replay(session: requests.Session, episode_id: int) -> dict:
    r = session.post(
        f"{BASE}/GetEpisode",
        json={"episodeId": episode_id},
        headers=build_headers(),
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def cmd_test_one(args):
    session = requests.Session()
    r = session.post(
        f"{BASE}/GetEpisode",
        json={"episodeId": args.episode_id},
        headers=build_headers(),
        timeout=30,
    )
    print(f"HTTP {r.status_code}")
    try:
        data = r.json()
        print(json.dumps(data, indent=2, ensure_ascii=False)[:2000])
    except ValueError:
        print("(JSON 파싱 실패, 원문 앞부분)")
        print(r.text[:1000])
    print("\n--- 위 응답에 리플레이 데이터(steps 등)가 보이면 OK. "
          "에러/HTML/빈 값이면 쿠키·BUILD_VERSION을 다시 확인하거나 이 출력을 붙여넣어 주세요. ---")


def cmd_list(args):
    session = requests.Session()
    all_ids = set()
    for sid in args.submission_ids:
        ids = list_episodes_for_submission(session, sid)
        print(f"submission {sid}: {len(ids)}개 에피소드")
        all_ids.update(ids)
        time.sleep(args.delay)
    out = Path(args.out)
    out.write_text("\n".join(str(i) for i in sorted(all_ids)))
    print(f"총 {len(all_ids)}개 에피소드 ID → {out}")


def cmd_fetch(args):
    ids = [int(x) for x in Path(args.ids_file).read_text().split() if x.strip()]
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    done = {p.stem for p in out_dir.glob("*.json")}  # 이미 받은 건 건너뜀 (재시작 가능)
    for i, eid in enumerate(ids, 1):
        if str(eid) in done:
            continue
        for attempt in range(5):
            try:
                data = fetch_replay(session, eid)
                break
            except requests.HTTPError as e:
                status = e.response.status_code if e.response is not None else None
                if status == 429:
                    wait = args.delay * (2 ** attempt) + 1
                    print(f"  [{eid}] 429 rate-limit, {wait:.0f}s 대기 후 재시도")
                    time.sleep(wait)
                    continue
                raise
        else:
            print(f"  [{eid}] 5회 실패, 스킵")
            continue
        (out_dir / f"{eid}.json").write_text(json.dumps(data))
        if i % 20 == 0:
            print(f"  {i}/{len(ids)} 완료")
        time.sleep(args.delay)
    print("done.")


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    p_test = sub.add_parser("test-one", help="에피소드 ID 1개로 스모크 테스트")
    p_test.add_argument("--episode-id", type=int, required=True)
    p_test.set_defaults(func=cmd_test_one)

    p_list = sub.add_parser("list", help="제출 ID들 → 에피소드 ID 목록 파일")
    p_list.add_argument("--submission-ids", type=int, nargs="+", required=True)
    p_list.add_argument("--out", default="episode_ids.txt")
    p_list.add_argument("--delay", type=float, default=1.0)
    p_list.set_defaults(func=cmd_list)

    p_fetch = sub.add_parser("fetch", help="에피소드 ID 목록 → 리플레이 JSON 일괄 다운로드")
    p_fetch.add_argument("--ids-file", default="episode_ids.txt")
    p_fetch.add_argument("--out-dir", default="replays")
    p_fetch.add_argument("--delay", type=float, default=1.5)
    p_fetch.set_defaults(func=cmd_fetch)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

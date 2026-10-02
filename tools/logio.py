"""로그 입출력 공용 헬퍼.

`logs/` 아래 리플레이 로그는 디스크 절약을 위해 gzip 압축되어 있다
(.json 4,728개 = 141GB -> .json.gz = 3.8GB, 약 138GB 회수).

새 코드는 `open()` + `json.load()` 대신 여기 함수를 쓴다.
`.json` 과 `.json.gz` 를 모두 투명하게 처리하므로, 나중에 일부만
압축을 풀어두더라도 호출부를 고칠 필요가 없다.

    from logio import load_log, iter_logs, log_paths

    d = load_log("logs/8.43v/107540971.json")      # .gz 가 있으면 자동으로 그쪽을 읽음
    for path, d in iter_logs("logs/*/*.json"):     # 패턴도 .gz 자동 확장
        ...
"""

from __future__ import annotations

import glob as _glob
import gzip
import json
import lzma
import os
from typing import Any, Iterator

__all__ = ["open_log", "load_log", "log_paths", "iter_logs"]


def _resolve(path: str) -> str:
    """실제 존재하는 경로를 돌려준다 (.json <-> .json.gz <-> .json.xz 자동 대응).

    압축 여부를 호출부가 몰라도 되게 하는 것이 목적. .json 경로 요청 시
    .json -> .json.gz -> .json.xz 순으로 찾는다. 아무것도 없으면
    원래 경로를 그대로 반환해 FileNotFoundError 가 정상적으로 나게 둔다.
    """
    if os.path.exists(path):
        return path
    if path.endswith(".gz"):
        if os.path.exists(path[:-3]):
            return path[:-3]
        return path
    if path.endswith(".xz"):
        if os.path.exists(path[:-3]):
            return path[:-3]
        return path
    # bare .json (or other) path: try .gz then .xz
    if os.path.exists(path + ".gz"):
        return path + ".gz"
    if os.path.exists(path + ".xz"):
        return path + ".xz"
    return path


def open_log(path: str, mode: str = "rt", **kwargs):
    """로그 파일 핸들. .gz 면 gzip, .xz 면 lzma, 아니면 평문으로 연다."""
    real = _resolve(path)
    if real.endswith(".gz"):
        return gzip.open(real, mode, **kwargs)
    if real.endswith(".xz"):
        return lzma.open(real, mode, **kwargs)
    return open(real, mode, **kwargs)


def load_log(path: str) -> Any:
    """로그 JSON 하나를 dict 로 읽는다 (압축 여부 무관)."""
    with open_log(path, "rt") as fh:
        return json.load(fh)


def log_paths(pattern: str) -> list[str]:
    """glob 패턴에 매칭되는 로그 경로 목록 (정렬됨).

    `logs/*/*.json` 처럼 비압축 패턴을 줘도 `.json.gz`/`.json.xz` 까지
    함께 찾는다. 같은 로그의 평문/gz/xz 본이 여럿 있으면 하나만 남긴다
    (우선순위: 평문 > gz > xz).
    """
    found = set(_glob.glob(pattern))
    if pattern.endswith(".json"):
        found |= set(_glob.glob(pattern + ".gz"))
        found |= set(_glob.glob(pattern + ".xz"))
    elif pattern.endswith(".json.gz"):
        found |= set(_glob.glob(pattern[:-3]))
        found |= set(_glob.glob(pattern[:-3] + ".xz"))
    elif pattern.endswith(".json.xz"):
        found |= set(_glob.glob(pattern[:-3]))
        found |= set(_glob.glob(pattern[:-3] + ".gz"))

    # 중복 제거 우선순위: 평문 > gz > xz
    plain = {p for p in found if not p.endswith(".gz") and not p.endswith(".xz")}
    gz = {p for p in found if p.endswith(".gz") and p[:-3] not in plain}
    xz = {
        p
        for p in found
        if p.endswith(".xz") and p[:-3] not in plain and (p[:-3] + ".gz") not in gz
    }
    result = plain | gz | xz
    return sorted(result)


def iter_logs(pattern: str) -> Iterator[tuple[str, Any]]:
    """패턴에 맞는 로그를 (경로, 내용) 으로 하나씩 내보낸다.

    수천 개 로그를 도는 용도라 제너레이터로 둔다 (전부 메모리에 올리지 않음).
    """
    for path in log_paths(pattern):
        yield path, load_log(path)

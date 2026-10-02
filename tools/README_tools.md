# kaggriculture 로컬 검증 도구 (세션 2, 2026-09-02)

전제: `pip install kaggle-environments==1.32.7` (엔진 버전은 실전과 동일해야 함). CPU 2코어 기준 1판 ≈ 7초.
모든 스크립트는 이 폴더에서 실행하며, 제출본 파일은 `../submissions/`에 있으므로 경로를 맞춰 복사하거나 심볼릭 링크로 가져온다.

| 파일 | 용도 | 사용 예 |
|---|---|---|
| `h2h.py` | 두 제출 파일의 양좌석 h2h. `file:idx`로 pool 대본 인덱스 고정 가능 | `python h2h.py submission_v811.py submission_v810.py 7 17 27` |
| `nonreg.py` | 한 파일 vs 여러 상대, 2프로세스 병렬 (하위 밴드 비회귀용) | `python nonreg.py submission_v811.py submission_v89.py,submission_v87.py 7,17,27,37` |
| `sweep.py` | pool 안의 모든 대본을 tape0 상대로 총당 | `python sweep.py` |
| `probe.py` | 한 판 실행 후 종료 시점 창고·시장·타일·자금 궤적 출력 | `python probe.py 7` |
| `tapeagent.py` | 719수 액션 리스트를 에이전트로 감싸는 헬퍼 (다른 스크립트가 import) | – |
| `extract.py` | `logs/<이름>/*.json` 에피소드 → `recs.pkl` (좌석별 719수, 오프닝 프로필, 승패, seed) | `python extract.py` |
| `stageA.py` | recs.pkl의 대본을 이름 필터로 골라 v810 상대 소배치 필터 | `python stageA.py 7,17 stageA.json "MtN,Whyme Labs"` |
| `stageB.py` | `cands.pkl`(이름→대본) 후보를 신선 시드로 재검증 | `python stageB.py 101,103,105 submission_v810.py stageB.json` |
| `recworld.py` | **기록된 세계 재현**: 에피소드 `info.seed`로 같은 월드를 만들고 후보 대본 vs 상대의 기록 액션 | `python recworld.py MtN v810,consensus,tape7` |

핵심 사실
- 에피소드 JSON의 `info.seed`를 `make("kaggriculture", configuration={"seed": ...})`에 넣으면 세계(상점 순서·잡초)가 정확히 재현된다. 같은 대본을 재생하면 기록 금액과 일치.
- 스텝 i의 액션은 `steps[i+1][seat]["action"]`.
- 같은 대본 미러는 금액까지 완전 동점. 좌석을 바꿔도 결과가 같으므로 h2h는 한 좌석만 돌려도 된다(양좌석은 확인용).
- 방법론: 소배치(Stage A) 신호는 자주 증발한다 → 신선 시드(Stage B) → 홀드아웃(7,17,…,97) → 하위 밴드 계열(v89·v87·8.3·8.2·v85) 비회귀 → ast/엔진 완주/리플레이 719/타이밍 검증 후 제출.

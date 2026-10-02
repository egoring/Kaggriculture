# kg_0928 — 마지막 주(9/26~9/29) 클라우드 작업 도구

전제: `kaggle_environments` 1.32.7, 같은 폴더의 `tapeagent.py`, 풀 pkl은 `recs_cache/logs__<풀>__all.pkl`.

| 파일 | 용도 |
|---|---|
| `extract_cloud.py <풀이름> <에피소드 json 폴더>` | 실전 로그(json)에서 좌석별 행동열·결과를 뽑아 풀 pkl 생성 |
| `tapefrun3.py <풀> <후보.py> lo hi` | 풀의 [lo,hi) 판을 상대는 기록 대본으로, 우리 자리에 후보를 넣어 재생. `rec`=기록 마진, `rep`=재생 마진 (후보가 제출본이면 두 값이 같아야 함) |
| `tapefrun4.py <풀> <후보.py> ep,ep` | 특정 에피소드만 + 레이어 텔레메트리 출력 |
| `cmphyb.py 태그…` / `cmpl.py 기준패턴 후보패턴…` | 풀 재생 결과 파일(ev/*.txt)을 같은 판끼리 비교(승수·평균·중앙값·우세 판·뒤집힘) |
| `h2.py A B seed` / `h3.py A B seed` | 인프로세스 대결(h3는 스텝 시간·텔레메트리 포함). `mir.sh`, `mir2.sh`는 양좌석 미러 묶음 |
| `revtape.py <풀> <후보> ep,…` | `_commit_unit` 훅으로 체결 매출을 품목별로 분해, 판매 시각 평균 |
| `itemtrace.py <풀> <후보> ep 품목` / `wheattrace.py <풀> <후보> ep lo hi` | 한 판의 품목별 체결·창고 추적 / 밀·현금·주문 추적 |
| `trigchk.py 풀…` | v889 JA 트리거(1스텝 돈 동일) 오발동 검사 |
| `build_hyb.py` | Step1009 + 레이어(WASH/FEED5/ORACLE/ASAP/MPX/WASH2) 혼합 변형 생성기 |
| `sellhour.py`, `kpi.py` | 판매 시각·작업 KPI 비교 |

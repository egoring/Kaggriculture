# 9/25 분석 도구 (kaggriculture, /root/kg 기준)

공통: 로그 풀은 `python3 extract_cloud.py <태그> <json폴더>` → `recs_cache/logs__<태그>__all.pkl`. 후보 파일은 마지막 callable(`kaggle_submission_agent`) 사용.

| 파일 | 용도 |
|---|---|
| extract_cloud.py / quickstat.py | 로그 추출, 풀 승률·계열별 마진 요약 |
| tapefrun.py 풀 후보 [이름들] | 기록 상대 테이프 vs 후보 파일 재생(`ORC_DEBUG=1`이면 오라클 off 스텝/fires 출력) |
| frun.py A B 시드 | 파일경로 러너(오라클은 `__raw_path__` 필요) |
| orctape.py 풀 후보 이름들 | 테이프 상대로 2일 단위 fires/hits 텔레메트리 |
| orcrep.py / orcrep2.py 후보 상대 시드들 | 인프로세스 파일 상대 텔레메트리(orcrep2는 2일 단위) |
| orcfid.py / orcfid2.py 후보 상대 시드 | 모델의 상대 행동 재구성(r_t) vs 실제 행동 비교(2는 raw 주문 동일성) |
| orcfid3.py | 추적 창고 vs 실제 창고 편차, 재고 초과 매도 주문 수 |
| orcscore.py | 적중률 채점 미스의 원인 덤프(흐름·창고·draw·우리매도) |
| orcdev.py 후보 file:경로:시드 또는 tape:풀:이름 | 그림자 money/inv 편차 분포 |
| orcdiff.py / orcdiff2.py 후보 풀 이름 [N] | 모델 vs 변종의 시장 주문 차이(2는 추적 창고 포함) |
| thr.py 이름들 | 변종 매도의 마지막/다음 단위 가격 비율(임계 추정) |
| revcmp.py A B 시드 | 품목별 체결 매출 비교(_commit_unit 훅; 좌석 식별은 보완 필요) |
| late3.py / late4.py | 후반 돈 곡선·일별 매도 / 스텝별 추적 |
| pairdiag.py 풀 ep | 기록 한 판 양쪽 테이프 재현, 품목별 매출·수확·작업 |
| asaplayer.py / pulllayer.py | 즉시매도·앞당기기 레이어(미채택, 결과는 6-43절) |
| oraclelayer_v869.py, submission_v869/870/871 | 보관용 |

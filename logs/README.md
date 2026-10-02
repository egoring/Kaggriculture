# logs/ (git 제외, 로컬 110GB)

- `s<제출번호>/` : 활성 제출의 실전 에피소드(json.gz) + index.csv (episode, seat, opponent, result, margin, shops, 파종 수)
- `8.xxv*/`, `*.recs.pkl` : 9월 초 버전별 실전 로그와 추출 캐시(`tools/extract_local.py`)
- `0909_top*.pkl`, `0910_*`, `0912_*` : 캐글 데이터셋(georgymamarin/kaggriculture-episodes)에서 2650+ 좌석 추출
- `1_*.zip`, `2_*.zip`, `3_*.zip` : 9/2 시점 상위 팀 에피소드
- `tt/` : mhw 125판·Timbs 90판·v879 151판 압축 표
- 클라우드 재생 풀(`recs_cache/logs__r2five__all.pkl` 199판, `l886` 113판, `l887` 117판)은 `tools/kg_0928/extract_cloud.py`로 만든다.

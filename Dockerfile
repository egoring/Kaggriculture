# Kaggriculture 로컬 재현 환경
# - kaggle-environments 1.32.7 (대회 실전 엔진과 같은 버전)
# - tools/ (재생·대결·녹화 빌더·게이트), engine/ (실험 코드), docs/
# 제출 파일과 실전 로그는 포함하지 않는다. 로그는 -v 로 마운트해서 쓴다.
#
#   docker run --rm -it -v "$PWD/logs:/kaggriculture/logs" ghcr.io/egoring/kaggriculture:latest
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN pip install "kaggle-environments==1.32.7"

WORKDIR /kaggriculture
COPY README.md ./
COPY docs/ ./docs/
COPY tools/ ./tools/
COPY engine/ ./engine/

# 빌드 시 엔진 로드 확인: kaggriculture 환경이 만들어지고 1판이 끝까지 도는지
RUN python -c "from kaggle_environments import make; e=make('kaggriculture'); e.run(['random','random']); print('kaggriculture', len(e.steps), 'steps', [s['status'] for s in e.steps[-1]])"

CMD ["bash"]

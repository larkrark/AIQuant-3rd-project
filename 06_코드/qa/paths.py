# -*- coding: utf-8 -*-
"""qa 트랙 경로 상수 — 단일 정의.

2026-07-24 팀 리팩터(7b084ae)로 06_코드 구조가 트랙별로 분리되면서
`engine/input_data`·`engine/pilot_run` 이 `data/` 아래로 이동했다.
경로를 각 스크립트에 흩어 두면 다음 이동 때 또 깨지므로 여기 한 곳에서만 정의한다.

기본값은 전부 **git에 등록된 실데이터**를 가리킨다(합성 표본 미사용 — 룰북 R12).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))          # 06_코드/qa
CODE = os.path.abspath(os.path.join(HERE, ".."))           # 06_코드
ROOT = os.path.abspath(os.path.join(CODE, ".."))           # 저장소 루트

ENGINE = os.path.join(CODE, "engine")                      # 팀 엔진 (qa는 import하지 않음)
DATA = os.path.join(CODE, "data")

# --- git 등록 실데이터 ---
INPUT_DATA = os.path.join(DATA, "input_data")              # 수집 원본(팀 인계본 포함)
PILOT = os.path.join(DATA, "pilot_run")
PILOT_INPUT = os.path.join(PILOT, "input_krxbm")           # 파일럿 본실행 입력 (KR9+US9)
PILOT_OUTPUT = os.path.join(PILOT, "output_krxbm")         # 파일럿 본실행 산출 (대조 기준)
PILOT_INPUT_ALT = os.path.join(PILOT, "input")             # 예비 BM 입력
PILOT_OUTPUT_ALT = os.path.join(PILOT, "output")           # 예비 BM 산출

SEED_BASKET = os.path.join(INPUT_DATA, "seed_basket.csv")  # 유니버스 정본

# --- qa 로컬 작업물 (git 미추적) ---
FIGURES = os.path.join(HERE, "figures")                    # 대시보드 PNG·지표 JSON
COLLECTED = os.path.join(HERE, "collected")                # data_loader 독립 수집본
MINE_OUTPUT = os.path.join(ENGINE, "output_real")          # 독립 수집본을 통과시킨 재산출


def env_path() -> str:
    """.env 위치 — 팀 리팩터로 ingest/ 가 표준. 이전 위치(engine/)도 허용."""
    for p in (os.path.join(CODE, "ingest", ".env"), os.path.join(ENGINE, ".env")):
        if os.path.exists(p):
            return p
    return ""


def force_utf8_stdout() -> None:
    """Windows cp949 콘솔에서 — · → 등 출력 깨짐 방지 (engine/run_pilot.py 와 동일 처리)."""
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass


def require(path: str, what: str) -> str:
    """없는 경로를 조용히 넘기지 않는다 — 무엇이 왜 필요한지 밝히고 중단."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"{what} 없음: {path}")
    return path

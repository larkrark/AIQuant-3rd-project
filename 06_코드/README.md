# 06_코드 — 코드 구조

트랙별로 폴더를 분리한다. **숫자·정책은 `engine/config.py`에만**(룰북 R1), **결정의 단일 원본은 `01_운영문서/결정로그.md`**.

| 폴더 | 역할 | 비고 |
|---|---|---|
| `engine/` | 본체 파이프라인 (상태코드→인디케이터→구성→가중→지수·BM) | `config·market_state·indicators·composition·index_calc·run_pilot` + `tests/` |
| `ingest/` | 데이터 수집·인계 (실데이터, 로컬·네트워크 필요) | `collect_pilot_inputs·build_pilot_inputs·check_data_paths` + `.env`(gitignore) |
| `report/` | 발표·리포팅 산출 | `gen_visual_page`(위키 standalone HTML) |
| `qa/` | **독립 재산출·검산 (김민호)** — 독립성 규칙상 `engine`을 import하지 않는다 | 규칙 문서만 보고 별도 구현 |
| `analysis/` | 비교시험(#15·#19)·분포·당좌비율·달력 적용시험 등 일회성 산출 러너 | 확정 절차, 코드 예정 |
| `data/` | 입력·산출 데이터 (`input_data`, `pilot_run`) — 코드와 분리 | 대용량 CSV |

## 실행 (파일럿)

> **Windows 주의:** `python`에 pandas가 없으면 `py` 런처를 쓴다(`py run_pilot.py ...`). 콘솔 한글/기호(—·→) 깨짐은 각 스크립트가 표준출력을 UTF-8로 강제해 해결돼 있다.

```bash
pip install -r requirements.txt
# 엔진: 반드시 engine/ 에서 실행 (평면 임포트).  Windows는 python 대신 py 사용 가능
cd engine
py run_pilot.py ../data/pilot_run/input_krxbm ../data/pilot_run/output_krxbm
# 불변식 스모크 테스트 (합성 표본 → 파이프라인 관통 → 상태코드·가중합·정합 검사)
py tests/test_invariants.py
```

리포팅·수집은 각 폴더에서:

```bash
python ingest/build_pilot_inputs.py     # data/input_data → data/pilot_run/input 병합
python report/gen_visual_page.py        # data/pilot_run/output_krxbm → 루트 pilot-visual.html
```

## 원칙

- `qa/`는 `engine/`을 import하지 않는다(독립 재산출의 독립성 — 역할배정 QA 방식 정의).
- 성과 결과를 본 뒤 `config.py`·규칙을 바꾸지 않는다(룰북 R3). 값 변경은 결정로그 기록 후.
- 합성 데이터(`engine/tests/make_sample.py`) 산출물은 어떤 문서에도 인용 금지(룰북 R12).

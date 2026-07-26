# ingest — 데이터 수집·인계

실데이터 수집 스크립트. **로컬·네트워크 환경에서 실행**(클라우드 세션은 외부 시세망 차단).

| 파일 | 역할 |
|---|---|
| `check_data_paths.py` | pykrx·yfinance·^RUA·KRX300·ECOS 경로 실체 확인 (5/5 통과해야 수집 착수) |
| `collect_pilot_inputs.py` | 미국 시계열·상장일·calendar·KOSPI200/^RUA·ECOS 환율 수집 → `../data/input_data` |
| `build_pilot_inputs.py` | KR9+US9 인계본을 run_pilot 입력계약(18종목)으로 병합 → `../data/pilot_run/input` |

- `.env`(ECOS/KRX 자격증명)는 이 폴더에 두고 **커밋 금지**(.gitignore, 룰북 R16). `collect`가 같은 폴더의 `.env`를 읽는다.
- 산출 경로는 `__file__` 기준으로 `../data/`를 참조한다(cwd 무관).

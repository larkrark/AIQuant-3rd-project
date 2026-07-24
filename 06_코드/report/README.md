# report — 발표·리포팅 산출

| 파일 | 역할 |
|---|---|
| `gen_visual_page.py` | `../data/pilot_run/output_krxbm`의 지수·BM을 읽어 발표용 standalone HTML(`<루트>/pilot-visual.html`) 생성. 외부 라이브러리 없이 내장 SVG |

- 입력 경로·출력 경로는 `__file__` 기준으로 계산(cwd 무관).
- 파일럿(v0.9-pilot) 수치는 파이프라인 검증용 잠정치이며 성과판정이 아니다(룰북 R12).

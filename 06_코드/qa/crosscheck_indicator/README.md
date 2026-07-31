# qa/crosscheck_indicator — 인디케이터 교차구현 검증 도구

| 구분 | 내용 |
|---|---|
| 목적 | 규칙 문서(데이터사전 5장·D-06·D-07 기본안·D-10 ③)만으로 엔진 ADTV90 원장이 재현되는지 교차검증 |
| 원본 | 추주원 indicator_prototype v4 → 권보성 리뷰 수정본 v5 (2026-07-31) |
| 상태 | method_status=APPROVAL_PENDING · **엔진 병합 금지**(독립 교차구현 가치 보존, D-7 게이트 대상 아님 — QA 보조 도구) |
| 수용 확인 | **완료** — 추주원 동의(2026-07-31 DM). 리뷰 문서 `01_운영문서/260731_인디케이터_v4리뷰_및_v5안내.txt` |

## 파일

- `indicator_prototype_v5.py` — 교차구현 본체 (시계열 ADTV90·축별 게이트·D-10 ③ 재배분)
- `crosscheck_vs_engine.py` — 엔진 원장 대조 스크립트
- `crosscheck_result.json` — 최근 실행 결과 (as-run 기록)

## 실행

```
python crosscheck_vs_engine.py ../../data/pilot_run/output_f1
```

## 최근 결과 (2026-07-31, output_f1 기준)

두 회차(컷 2026-03-24·2026-06-23) 18종목 전부 adtv90_status·seasoning_status 일치,
official_adtv90 최대 상대오차 1.3e-16 / 1.9e-16 (QA 허용오차 1e-12 통과).

## 경계

- 이 도구의 산출은 진단·검증 전용이며 공식 산출물이 아니다(엔진 산출물이 정본).
- 재무 임계값·판정 코드 매핑·허용오차 일원화는 미의결 — 차기 회의 의안 연동.

# -*- coding: utf-8 -*-
"""팩터 귀속 분석 — 초과수익이 테마 때문인가, 시장 노출 때문인가.

묻는 것
  우리 지수가 BM 을 앞선 것이 "테마 선택" 때문인가,
  아니면 그냥 시장보다 크게 움직이는 바스켓(고베타)이라서인가.

방법
  1단계  자체 BM 단일팩터 회귀 — 통화·구성이 정확히 맞는 유일한 회귀다
           r_index = α + β·r_BM + ε
         β > 1 이고 α ≈ 0 이면 "고베타 바스켓"이지 테마 효과가 아니다.
  2단계  Fama-French 3팩터 + 모멘텀 추가 (강건성 확인)
         ★ 주의 — FF 팩터는 달러 기준 미국 시장이고 우리 수익률은 원화·한미 혼합이다.
           정확한 정합이 아니므로 참고값으로만 읽는다. 이 한계를 산출물에 기록한다.
  3단계  구간 분할 — 앞뒤 절반에서 결과가 유지되는가

성과 인용 제한
  Seed18 은 2026년 시점 선택이므로 α 가 유의해도 "수익성 입증"이 아니다.
  본 분석의 용도는 초과수익의 원천을 가르는 것이다.
"""
import io
import json
import os
import sys
import urllib.request
import zipfile

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
FF_URL = ("https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
          "F-F_Research_Data_Factors_daily_CSV.zip")
MOM_URL = ("https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
           "F-F_Momentum_Factor_daily_CSV.zip")


def ols(y, X, names):
    """최소제곱 + Newey-West 보정 없는 기본 t값. 표본이 크므로 충분하다."""
    X = np.column_stack([np.ones(len(y)), X])
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ b
    n, k = X.shape
    s2 = resid @ resid / (n - k)
    se = np.sqrt(np.diag(s2 * np.linalg.inv(X.T @ X)))
    t = b / se
    r2 = 1 - (resid @ resid) / ((y - y.mean()) @ (y - y.mean()))
    return pd.DataFrame({"계수": b, "표준오차": se, "t값": t},
                        index=["α(절편)"] + names), r2, n


def fetch_ff(url, names):
    """Ken French 일별 CSV — 헤더 위치·열 수가 파일마다 달라 데이터 행에서 직접 잡는다."""
    with urllib.request.urlopen(url, timeout=60) as r:
        z = zipfile.ZipFile(io.BytesIO(r.read()))
    raw = z.read(z.namelist()[0]).decode("utf-8", errors="ignore").splitlines()
    rows = []
    for l in raw:
        p = [x.strip() for x in l.split(",")]
        if len(p) < 2 or len(p[0]) != 8 or not p[0].isdigit():
            if rows:            # 데이터 블록이 끝나면 (연간 요약부 시작) 중단
                break
            continue
        rows.append(p[:1 + len(names)])
    df = pd.DataFrame(rows, columns=["date"] + names)
    df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
    for c in names:
        df[c] = pd.to_numeric(df[c], errors="coerce") / 100.0
    return df.dropna()


def main():
    idx = pd.read_csv(os.path.join(OUT, "index_vs_benchmark.csv"),
                      parse_dates=["market_date"]).sort_values("market_date")
    idx["r_i"] = idx.index_level.pct_change()
    idx["r_b"] = idx.benchmark_level.pct_change()
    d = idx.dropna(subset=["r_i", "r_b"]).copy()

    print("=" * 70)
    print("팩터 귀속 분석 — 초과수익의 원천")
    print("=" * 70)
    print(f"  표본 {len(d):,}일  {d.market_date.min().date()} ~ {d.market_date.max().date()}\n")

    res = {"sample_days": len(d),
           "window": [str(d.market_date.min().date()), str(d.market_date.max().date())]}

    # ── 1단계 ────────────────────────────────────────────────
    print("[1] 자체 BM 단일팩터 — 통화·구성이 정확히 맞는 유일한 회귀")
    tab, r2, n = ols(d.r_i.values, d[["r_b"]].values, ["β(BM)"])
    a_ann = (1 + tab.loc["α(절편)", "계수"]) ** 252 - 1
    print(tab.round(5).to_string())
    print(f"    R² {r2:.4f}   연율 α {a_ann*100:+.2f}%   "
          f"α t값 {tab.loc['α(절편)','t값']:.2f}")
    beta = tab.loc["β(BM)", "계수"]
    print(f"\n    해석: β={beta:.3f} → BM 이 1% 움직일 때 지수는 {beta:.2f}% 움직인다")
    if beta > 1.15:
        print(f"           BM 보다 크게 움직이는 고베타 바스켓이다.")
        print(f"           초과수익 중 상당 부분이 '더 많이 실은 것'의 결과일 수 있다.")
    res["capm"] = {"beta": beta, "alpha_daily": tab.loc["α(절편)", "계수"],
                   "alpha_annual_pct": a_ann * 100,
                   "alpha_t": tab.loc["α(절편)", "t값"], "r2": r2}

    # ── 2단계 ────────────────────────────────────────────────
    print("\n[2] Fama-French 3팩터 + 모멘텀 (참고 — 통화·시장 불일치)")
    try:
        ff = fetch_ff(FF_URL, ["Mkt_RF", "SMB", "HML", "RF"])
        mom = fetch_ff(MOM_URL, ["MOM"])
        f = ff.merge(mom, on="date", how="inner")
        m = d.merge(f, left_on="market_date", right_on="date", how="inner")
        print(f"    FF 팩터 매칭 {len(m):,}일")
        y = (m.r_i - m.RF).values
        X = m[["Mkt_RF", "SMB", "HML", "MOM"]].values
        tab2, r22, _ = ols(y, X, ["시장", "규모(SMB)", "가치(HML)", "모멘텀(MOM)"])
        a2 = (1 + tab2.loc["α(절편)", "계수"]) ** 252 - 1
        print(tab2.round(5).to_string())
        print(f"    R² {r22:.4f}   연율 α {a2*100:+.2f}%   t값 {tab2.loc['α(절편)','t값']:.2f}")
        res["ff4"] = {"alpha_annual_pct": a2 * 100,
                      "alpha_t": tab2.loc["α(절편)", "t값"], "r2": r22,
                      "betas": {k: float(v) for k, v in
                                zip(["Mkt_RF", "SMB", "HML", "MOM"],
                                    tab2["계수"].values[1:])},
                      "caveat": "FF 팩터는 USD·미국시장 기준, 지수는 KRW·한미혼합 — 참고값"}
        print("    ★ FF 는 달러·미국 기준이고 우리 지수는 원화·한미 혼합이라 정합하지 않는다.")
    except Exception as e:
        print(f"    건너뜀 — {type(e).__name__}: {str(e)[:60]}")
        res["ff4"] = None

    # ── 3단계 ────────────────────────────────────────────────
    print("\n[3] 구간 분할 — 결과가 유지되는가")
    half = len(d) // 2
    for lab, seg in [("전반", d.iloc[:half]), ("후반", d.iloc[half:])]:
        t3, r23, n3 = ols(seg.r_i.values, seg[["r_b"]].values, ["β(BM)"])
        aa = (1 + t3.loc["α(절편)", "계수"]) ** 252 - 1
        print(f"    {lab} {seg.market_date.min().date()}~{seg.market_date.max().date()} "
              f"({n3:,}일)  β {t3.loc['β(BM)','계수']:.3f}  "
              f"연율α {aa*100:+.2f}%  t {t3.loc['α(절편)','t값']:.2f}")
        res[f"split_{lab}"] = {"beta": t3.loc["β(BM)", "계수"],
                               "alpha_annual_pct": aa * 100,
                               "alpha_t": t3.loc["α(절편)", "t값"]}

    res["citation_rule"] = ("Seed18 은 2026년 시점 선택이므로 α 가 유의해도 수익성 입증이 아니다. "
                            "본 분석의 용도는 초과수익 원천의 분해다.")
    with open(os.path.join(OUT, "factor_attribution.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2, default=float)
    print(f"\n  {os.path.join(OUT, 'factor_attribution.json')}")


if __name__ == "__main__":
    main()

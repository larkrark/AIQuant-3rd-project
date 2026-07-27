# -*- coding: utf-8 -*-
"""단계별 대조 — 독립 재산출(4~6단계) vs engine 산출물.

qa/README.md: "비교 대상은 engine 산출물이며, 불일치는 사유·규칙경로와 함께 기록한다."
지수값 하나가 아니라 **단계마다** 대조해야 불일치의 발생 지점을 특정할 수 있다.

사용:
  python crosscheck.py                       # out/ vs data/pilot_run/output_krxbm
  python crosscheck.py --mine <내 산출> --team <engine 산출>
"""
import os
import sys
import json
import argparse
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import paths as P
import rules as R

P.force_utf8_stdout()
TOL = 1e-6          # 허용오차 — 비중·비율 (부동소수 왕복 오차 흡수)
TOL_REL = 1e-9      # 허용오차 — 금액 상대오차


def _rd(d, n, **kw):
    p = os.path.join(d, n)
    return pd.read_csv(p, dtype={"security_id": str}, **kw) if os.path.exists(p) else None


def cmp_states(mine_dir, team_dir) -> dict:
    """4단계 — 종목×일자 상태코드 일치율."""
    a, b = _rd(mine_dir, "daily_market_state.csv"), _rd(team_dir, "daily_market_state.csv")
    if a is None or b is None:
        return {"stage": "4 상태코드", "status": "SKIP", "note": "산출물 없음"}
    key = ["security_id", "market_date"]
    m = a[key + ["daily_market_state"]].merge(
        b[key + ["daily_market_state"]], on=key, suffixes=("_mine", "_team"), how="outer")
    hit = (m["daily_market_state_mine"] == m["daily_market_state_team"])
    bad = m[~hit]
    note = "" if bad.empty else \
        "; ".join(f"{r.daily_market_state_mine}→{r.daily_market_state_team}"
                  for r in bad.head(3).itertuples())
    return {"stage": "4 상태코드", "n": len(m), "mismatch": int((~hit).sum()),
            "status": "MATCH" if bad.empty else "DIFF", "note": note}


def cmp_ledger(mine_dir, team_dir) -> list:
    """5단계 — ADTV90 원장(시즈닝일수·관측일수·공식 ADTV90)."""
    a, b = _rd(mine_dir, "adtv90_ledger.csv"), _rd(team_dir, "adtv90_ledger.csv")
    if a is None or b is None:
        return [{"stage": "5 ADTV90 원장", "status": "SKIP", "note": "산출물 없음"}]
    key = ["security_id", "review_cycle_id"]
    m = a.merge(b, on=key, suffixes=("_mine", "_team"))
    out = []
    for col, rel in (("observed_open_days", False), ("seasoning_days", False),
                     ("official_adtv90", True)):
        x, y = m[f"{col}_mine"], m[f"{col}_team"]
        both_na = x.isna() & y.isna()
        d = (x - y).abs()
        hit = both_na | (d / y.abs().replace(0, np.nan) < TOL_REL if rel else d < TOL)
        hit = hit.fillna(False)
        worst = float(d.max()) if d.notna().any() else 0.0
        out.append({"stage": f"5 {col}", "n": len(m), "mismatch": int((~hit).sum()),
                    "status": "MATCH" if hit.all() else "DIFF",
                    "note": "" if hit.all() else f"최대 절대차 {worst:,.4g}"})
    return out


def cmp_thresholds(mine_dir, team_dir) -> list:
    """5단계 — 시장별 P10 잠정 하한."""
    out = []
    for sel in R.SELECTION_DATES:
        pa, pb = (os.path.join(d, f"thresholds_{sel}.json") for d in (mine_dir, team_dir))
        if not (os.path.exists(pa) and os.path.exists(pb)):
            out.append({"stage": f"5 P10 {sel}", "status": "SKIP", "note": "산출물 없음"})
            continue
        A = json.load(open(pa, encoding="utf-8"))["provisional_P10"]
        B = json.load(open(pb, encoding="utf-8"))["provisional_P10"]
        diffs = []
        for k in sorted(set(A) | set(B)):
            va, vb = A.get(k), B.get(k)
            if va is None or vb is None or vb == 0 or abs(va - vb) / abs(vb) >= TOL_REL:
                diffs.append(f"{k} 내 {va:,.4g} vs 팀 {vb:,.4g}")
        out.append({"stage": f"5 P10 {sel}", "n": len(set(A) | set(B)), "mismatch": len(diffs),
                    "status": "MATCH" if not diffs else "DIFF", "note": "; ".join(diffs)})
    return out


def cmp_selection(mine_dir, team_dir) -> list:
    """6단계 — 편입 판정과 최종 목표비중."""
    out = []
    for sel in R.SELECTION_DATES:
        a, b = (_rd(d, f"constituents_{sel}.csv") for d in (mine_dir, team_dir))
        if a is None or b is None:
            out.append({"stage": f"6 편입판정 {sel}", "status": "SKIP", "note": "산출물 없음"})
        else:
            m = a[["security_id", "selected_flag"]].merge(
                b[["security_id", "selected_flag"]], on="security_id",
                suffixes=("_mine", "_team"), how="outer")
            hit = m["selected_flag_mine"] == m["selected_flag_team"]
            bad = m[~hit]["security_id"].tolist()
            out.append({"stage": f"6 편입판정 {sel}", "n": len(m), "mismatch": int((~hit).sum()),
                        "status": "MATCH" if not bad else "DIFF",
                        "note": "" if not bad else f"불일치 {', '.join(bad[:6])}"})

        a, b = (_rd(d, f"weights_{sel}.csv") for d in (mine_dir, team_dir))
        if a is None or b is None:
            out.append({"stage": f"6 가중 {sel}", "status": "SKIP", "note": "산출물 없음"})
            continue
        m = a[["security_id", "final_target_weight"]].merge(
            b[["security_id", "final_target_weight"]], on="security_id",
            suffixes=("_mine", "_team"), how="outer").fillna(0.0)
        d = (m["final_target_weight_mine"] - m["final_target_weight_team"]).abs()
        out.append({"stage": f"6 가중 {sel}", "n": len(m), "mismatch": int((d >= TOL).sum()),
                    "status": "MATCH" if (d < TOL).all() else "DIFF",
                    "note": "" if (d < TOL).all() else f"최대 비중차 {d.max():.6f}"})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mine", default=os.path.join(P.HERE, "independent", "out"))
    ap.add_argument("--team", default=P.PILOT_OUTPUT)
    ap.add_argument("--md", default=None, help="대조표 마크다운 저장 경로")
    args = ap.parse_args()

    P.require(os.path.join(args.mine, "adtv90_ledger.csv"), "독립 재산출 (recompute.py 선행)")
    P.require(os.path.join(args.team, "adtv90_ledger.csv"), "engine 산출물")

    rows = [cmp_states(args.mine, args.team)] + cmp_ledger(args.mine, args.team) \
        + cmp_thresholds(args.mine, args.team) + cmp_selection(args.mine, args.team)
    df = pd.DataFrame(rows)[["stage", "n", "mismatch", "status", "note"]]

    print(f"독립 재산출 대조  내={os.path.relpath(args.mine, P.ROOT)}  "
          f"팀={os.path.relpath(args.team, P.ROOT)}\n")
    print(df.fillna("").to_string(index=False))
    n_diff = int((df["status"] == "DIFF").sum())
    print(f"\n일치 {int((df['status']=='MATCH').sum())} · 불일치 {n_diff} · "
          f"생략 {int((df['status']=='SKIP').sum())}")

    out_csv = os.path.join(args.mine, "crosscheck.csv")
    df.to_csv(out_csv, index=False)
    print(f"→ {os.path.relpath(out_csv, P.ROOT)}")
    if args.md:
        with open(args.md, "w", encoding="utf-8") as f:
            f.write(f"# 독립 재산출 대조표\n\n내={args.mine} · 팀={args.team}\n\n")
            f.write(df.fillna("").to_markdown(index=False))
            f.write("\n")
        print(f"→ {args.md}")
    return n_diff


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""파일럿 산출물 -> 발표용 시각화 페이지(위키 standalone HTML). 외부 라이브러리 없이 내장 SVG."""
import pandas as pd, json, os
import sys as _sys
for _s in (_sys.stdout, _sys.stderr):
    try: _s.reconfigure(encoding="utf-8")   # Windows cp949 콘솔에서 —·→ 등 출력 깨짐 방지
    except Exception: pass
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))          # 프로젝트 루트
O = os.path.join(_HERE, "..", "data", "pilot_run", "output_krxbm")
iv = pd.read_csv(f"{O}/index_vs_benchmark.csv")
dates = list(iv.market_date); idx = list(iv.index_level); bm = list(iv.benchmark_level); alpha = list(iv.alpha)
n = len(dates)

def path_pts(vals, x, yfn):
    return " ".join(f"{x(i):.1f},{yfn(v):.1f}" for i, v in enumerate(vals))

# ---- 메인 차트 (지수 vs BM) ----
W, Hm = 900, 300
pL, pR, pT, pB = 58, 16, 14, 26
pw, ph = W - pL - pR, Hm - pT - pB
ymin, ymax = 940, 1500
X = lambda i: pL + pw * i / (n - 1)
Ym = lambda v: pT + ph * (ymax - v) / (ymax - ymin)
# 월 경계
month_ticks = []
seen = set()
for i, d in enumerate(dates):
    mo = d[:7]
    if mo not in seen:
        seen.add(mo); month_ticks.append((i, {"2026-04": "4월", "2026-05": "5월", "2026-06": "6월"}.get(mo, mo)))
ygrid = [1000, 1100, 1200, 1300, 1400, 1500]

svg = [f'<svg viewBox="0 0 {W} {Hm}" width="100%" role="img" aria-label="지수 vs 합성 BM 추이">']
svg.append(f'<rect x="{pL}" y="{pT}" width="{pw}" height="{ph}" fill="#fbfcfe" stroke="#e6eaf1"/>')
for gy in ygrid:
    y = Ym(gy)
    dash = ' stroke-dasharray="4 4"' if gy == 1000 else ''
    col = '#c9ccd6' if gy == 1000 else '#eef1f6'
    svg.append(f'<line x1="{pL}" y1="{y:.1f}" x2="{pL+pw}" y2="{y:.1f}" stroke="{col}"{dash}/>')
    svg.append(f'<text x="{pL-8}" y="{y+3:.1f}" text-anchor="end" font-size="10" fill="#8b93a3">{gy:,}</text>')
for i, lab in month_ticks:
    x = X(i)
    svg.append(f'<line x1="{x:.1f}" y1="{pT}" x2="{x:.1f}" y2="{pT+ph}" stroke="#eef1f6"/>')
    svg.append(f'<text x="{x+3:.1f}" y="{pT+ph+16}" font-size="10" fill="#8b93a3">{lab}</text>')
svg.append(f'<text x="{pL-8}" y="{Ym(1000)-6:.1f}" text-anchor="end" font-size="9" fill="#c9ccd6">기준 1,000</text>')
svg.append(f'<polyline fill="none" stroke="#b07a1e" stroke-width="2" points="{path_pts(bm, X, Ym)}"/>')
svg.append(f'<polyline fill="none" stroke="#1e2761" stroke-width="2.4" points="{path_pts(idx, X, Ym)}"/>')
# 끝점 마커+라벨
svg.append(f'<circle cx="{X(n-1):.1f}" cy="{Ym(idx[-1]):.1f}" r="3.2" fill="#1e2761"/>')
svg.append(f'<circle cx="{X(n-1):.1f}" cy="{Ym(bm[-1]):.1f}" r="3.2" fill="#b07a1e"/>')
svg.append(f'<text x="{X(n-1)-4:.1f}" y="{Ym(idx[-1])+14:.1f}" text-anchor="end" font-size="10.5" font-weight="700" fill="#1e2761">지수 {idx[-1]:,.0f}</text>')
svg.append(f'<text x="{X(n-1)-4:.1f}" y="{Ym(bm[-1])-6:.1f}" text-anchor="end" font-size="10.5" font-weight="700" fill="#b07a1e">BM {bm[-1]:,.0f}</text>')
svg.append('</svg>')
svg_main = "\n".join(svg)

# ---- alpha 서브차트 ----
Ha = 120
paT, paB = 10, 24
pah = Ha - paT - paB
amin, amax = -260, 60
Ya = lambda v: paT + pah * (amax - v) / (amax - amin)
a = [f'<svg viewBox="0 0 {W} {Ha}" width="100%" role="img" aria-label="누적 alpha">']
zero = Ya(0)
area = f"{X(0):.1f},{zero:.1f} " + path_pts(alpha, X, Ya) + f" {X(n-1):.1f},{zero:.1f}"
a.append(f'<polygon points="{area}" fill="#9b2c2c" fill-opacity="0.10"/>')
a.append(f'<line x1="{pL}" y1="{zero:.1f}" x2="{pL+pw}" y2="{zero:.1f}" stroke="#c9ccd6" stroke-dasharray="4 4"/>')
a.append(f'<text x="{pL-8}" y="{zero+3:.1f}" text-anchor="end" font-size="10" fill="#8b93a3">0</text>')
for gv in (-200, -100):
    a.append(f'<line x1="{pL}" y1="{Ya(gv):.1f}" x2="{pL+pw}" y2="{Ya(gv):.1f}" stroke="#f1eaea"/>')
    a.append(f'<text x="{pL-8}" y="{Ya(gv)+3:.1f}" text-anchor="end" font-size="10" fill="#b98a8a">{gv}</text>')
a.append(f'<polyline fill="none" stroke="#9b2c2c" stroke-width="2" points="{path_pts(alpha, X, Ya)}"/>')
for i, lab in month_ticks:
    a.append(f'<text x="{X(i)+3:.1f}" y="{paT+pah+16}" font-size="10" fill="#8b93a3">{lab}</text>')
a.append(f'<text x="{X(n-1)-4:.1f}" y="{Ya(alpha[-1])+15:.1f}" text-anchor="end" font-size="10.5" font-weight="700" fill="#9b2c2c">alpha {alpha[-1]:,.0f}</text>')
a.append('</svg>')
svg_alpha = "\n".join(a)

# ---- 구성/제외/하한 데이터 ----
CELLS = [("KR","AI로보틱스","AI_ROBOTICS",2,"8.33%","018260 탈락"),
         ("KR","에너지·전력","ENERGY_POWER",3,"5.56%","—"),
         ("KR","우주방산","SPACE_DEFENSE",3,"5.56%","—"),
         ("US","AI로보틱스","AI_ROBOTICS",3,"5.56%","—"),
         ("US","에너지·전력","ENERGY_POWER",3,"5.56%","—"),
         ("US","우주방산","SPACE_DEFENSE",1,"16.67%","1종목 집중")]
EXC = {"2026-03-31":[("018260","KR","ADTV90 P10 미달"),("SPCX","US","시즈닝 미충족(상장 6/12)"),("ATI","US","ADTV90 P10 미달")],
       "2026-06-30":[("018260","KR","ADTV90 P10 미달"),("SPCX","US","시즈닝 미충족(관측 12일)"),("KTOS","US","ADTV90 P10 미달")]}
THR = {"2026-03-31":("73,914,096,486","308,975,201"),"2026-06-30":("126,878,040,848","325,377,655")}

def mk(m):
    return f'<span class="mk {"kr" if m=="KR" else "us"}">{m}</span>'

def _cellrow(m,tk,nn,per,note):
    cls = ' class="warn-row"' if note not in ("—","018260 탈락") else ""
    return f'<tr{cls}><td>{mk(m)} · {tk}</td><td class="num">{nn}</td><td class="num">16.67%</td><td class="num">{per}</td><td class="note">{note}</td></tr>'
cell_rows = "\n".join(_cellrow(m,tk,nn,per,note) for (m,tk,_,nn,per,note) in CELLS)

def exc_block(d):
    rows = "\n".join(f'<tr><td>{s}</td><td>{mk(m)}</td><td class="note">{r}</td></tr>' for s,m,r in EXC[d])
    return f'<div class="excbox"><div class="exch"><b>{d}</b> · 선정 <b>15</b>/18</div><table><tr><th>제외</th><th>시장</th><th>사유</th></tr>{rows}</table></div>'

thr_rows = "\n".join(f'<tr><td>{d}</td><td class="num">{kr}</td><td class="num">{us}</td></tr>' for d,(kr,us) in THR.items())

CSS = """
:root{--ink:#222;--muted:#5b6472;--line:#dfe4ec;--blue:#1e2761;--gold:#b07a1e;--green:#e6f4ea;--green-ink:#1a7f37;--red:#fdeaea;--red-ink:#9b2c2c;--gray:#f2f4f7}
*{box-sizing:border-box}
body{font-family:"Segoe UI","Malgun Gothic",Arial,sans-serif;margin:24px;background:#fff;color:var(--ink);max-width:1000px;line-height:1.45}
a{color:var(--blue)}
.wikinav{display:flex;gap:6px;flex-wrap:wrap;align-items:center;font-size:.8rem;margin-bottom:14px;padding-bottom:12px;border-bottom:1px solid var(--line)}
.wikinav a{text-decoration:none;border:1px solid var(--line);border-radius:999px;padding:3px 10px;color:var(--muted);background:#fafbfc}
.wikinav a.home{border-color:var(--blue);color:var(--blue);font-weight:700}
.wikinav a:hover{background:#eef1f8}
.wikinav .sep{color:#c9ccd6}
h1{font-size:1.35rem;margin:0 0 4px}
h2{font-size:1rem;margin:0}
.sub,.meta,.foot{color:var(--muted);font-size:.82rem}
.meta{margin:8px 0 16px}
code{background:#f2f4f7;border-radius:4px;padding:1px 5px;font-size:.8rem}
.top{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:16px 0}
.metric{border:1px solid var(--line);border-radius:8px;padding:12px;background:#fafbfc}
.metric b{display:block;font-size:1.4rem;color:var(--blue)}
.metric .d{font-size:.75rem;margin-top:2px}.up{color:var(--green-ink)}.down{color:var(--red-ink)}
.metric span{font-size:.76rem;color:var(--muted)}
.panel{border:1px solid var(--line);border-radius:8px;margin:14px 0;overflow:hidden}
.panel>header{display:flex;justify-content:space-between;gap:12px;align-items:center;background:var(--blue);color:#fff;padding:10px 14px}
.panel>.body{padding:14px}
.legend{display:flex;gap:16px;flex-wrap:wrap;margin:2px 2px 10px;font-size:.8rem;color:var(--muted)}
.legend i{display:inline-block;width:20px;height:3px;vertical-align:middle;margin-right:5px;border-radius:2px}
table{width:100%;border-collapse:collapse;font-size:.86rem}
th{background:#f7f8fa;color:var(--muted);font-weight:700;text-align:left;padding:8px 12px;border-bottom:1px solid var(--line);font-size:.76rem}
td{padding:8px 12px;border-bottom:1px solid #eef0f4;vertical-align:top}
tr:last-child td{border-bottom:none}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
.note{color:var(--muted);font-size:.8rem}
tr.warn-row{background:#fff7f7}
.mk{font-weight:700;font-size:.72rem;padding:0 5px;border-radius:4px}
.mk.kr{color:#1e3a8a;background:#e7edfb}.mk.us{color:#8a4b1e;background:#f7ece1}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.excbox{border:1px solid var(--line);border-radius:8px;overflow:hidden}
.exch{background:#f7f8fa;padding:8px 12px;font-size:.82rem;color:var(--muted);border-bottom:1px solid var(--line)}
.bridge{border:1px solid var(--line);border-radius:8px;padding:12px 14px;background:#fafbfc;margin:14px 0;font-size:.84rem}
.bridge b{color:var(--red-ink)}
.foot{margin-top:10px}
@media(max-width:760px){body{margin:14px}.top{grid-template-columns:1fr 1fr}.grid2{grid-template-columns:1fr}}
"""

html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>파일럿 지수 시각화 (발표용) — v0.9-pilot</title>
<style>{CSS}</style>
</head>
<body>

<nav class="wikinav">
  <a class="home" href="index.html">📚 문서 위키 홈</a>
  <span class="sep">│</span>
  <span style="color:var(--muted)">연동 페이지:</span>
  <a href="role-flow.html">역할 순서도</a>
  <a href="pilot-status.html">진행 상태판</a>
  <span style="border:1px solid var(--blue);border-radius:999px;padding:3px 10px;color:#fff;background:var(--blue);font-weight:700">지수 시각화 (현재)</span>
</nav>

<h1>파일럿 지수 시각화 <span style="font-size:.9rem;color:var(--muted)">(발표용)</span></h1>
<div class="sub"><a href="pilot-status.html">진행 상태판</a>의 5단계(발표·제출) 산출물 시각화입니다. 엔진 v0 드라이런 결과를 발표 화면용으로 정리했습니다.</div>
<div class="meta">기준: 2026-07-24 · rule_version <code>v0.9-pilot</code>(잠정) · 대표 검토일 2026-03-31 / 2026-06-30 · 기준값 1,000 · PR·원화·무헤지 · 합성 BM <b>KRX 공식 KOSPI200</b> 50% + Russell3000 50%</div>

<div class="top">
  <div class="metric"><b>1,271</b><div class="d up">+27.11%</div><span>지수 종가</span></div>
  <div class="metric"><b>1,418</b><div class="d up">+41.78%</div><span>합성 BM 종가</span></div>
  <div class="metric"><b style="color:var(--red-ink)">−146.6</b><div class="d down">BM 대비 언더퍼폼</div><span>누적 alpha</span></div>
  <div class="metric"><b>15<span style="font-size:.9rem;color:var(--muted)"> / 18</span></b><div class="d">6셀 모두 충족</div><span>선정 종목</span></div>
</div>

<div class="panel">
<header><h2>1 · 지수 vs 합성 BM 추이</h2><span style="font-size:.76rem">2026-04-01 ~ 06-30 · 59 개장일</span></header>
<div class="body">
  <div class="legend"><span><i style="background:#1e2761"></i>본 지수</span><span><i style="background:#b07a1e"></i>합성 BM(KRX 공식)</span><span><i style="background:#c9ccd6"></i>기준 1,000</span></div>
  {svg_main}
  <div style="font-size:.8rem;color:var(--muted);margin:10px 2px 2px">누적 alpha (지수 − BM, 원화 지수포인트)</div>
  {svg_alpha}
  <div class="foot foot-note" style="font-size:.78rem;color:var(--muted)">두 계열 모두 2026-04-01 = 1,000 리베이스. 구간 내 지수가 한때 BM을 앞섰으나(alpha 최고 +46) 이후 벌어져 종료 시 −147.</div>
</div>
</div>

<div class="panel">
<header><h2>2 · 셀 구성·가중</h2><span style="font-size:.76rem">6셀 각 1/6 · 셀 내 동일가중(잠정)</span></header>
<div class="body">
<table>
<tr><th>셀</th><th class="num">종목수</th><th class="num">셀 가중</th><th class="num">종목당</th><th>비고</th></tr>
{cell_rows}
</table>
<div class="foot" style="font-size:.78rem;color:var(--muted)">가중 총합 = 1.000000(검산 통과) · 셀 부족·재배분 0건 · WEIGHTING_STATUS=TEMPORARY(가중 H 확정 전)</div>
</div>
</div>

<div class="panel">
<header><h2>3 · 제외 종목·사유 (회차별)</h2><span style="font-size:.76rem">정량 게이트</span></header>
<div class="body">
<div class="grid2">{exc_block("2026-03-31")}{exc_block("2026-06-30")}</div>
<div class="foot" style="font-size:.78rem;color:var(--muted)">SPCX는 양 회차 시즈닝(유효관측 90일) 미충족. US 우주방산 P10 탈락은 회차별 교대(3-31 ATI · 6-30 KTOS).</div>
</div>
</div>

<div class="panel">
<header><h2>4 · ADTV90 잠정 하한 (시장별 P10)</h2><span style="font-size:.76rem">official method = ZERO</span></header>
<div class="body">
<table><tr><th>회차</th><th class="num">KR P10 (원)</th><th class="num">US P10 (USD)</th></tr>{thr_rows}</table>
</div>
</div>

<div class="bridge">
<b>발표 시 주의(전원 확인/이월):</b>
이 수치는 <b>파이프라인 검증·비교시험 입력 확보용 잠정치</b>이며 성과판정이 아닙니다(간이투자설명서 [백테스트 후 채움] 칸에 넣지 않음).
<b>A-2 "종일 거래정지일 0 반영"</b>은 전원 확인 대기 안건이고, <b>US 우주방산 셀 16.67% 1종목 집중</b>은 상한(NO_CAP) 미적용 파일럿 한계입니다.
P10 하한은 9종목 소규모 유니버스의 기계적 절단으로, 절대금액 승인은 정식 이월(#16)입니다.
</div>

<div class="foot">
근거 산출물: <code>06_코드/data/pilot_run/output_krxbm/</code> · 병합 <code>06_코드/ingest/build_pilot_inputs.py</code> · BM <code>06_코드/data/input_data/bm_kr_krx_official.csv</code>(KRX 공식, 야후 예비값과 180일 0.00% 일치).
전체 문서는 <a href="index.html">문서 위키 홈</a> 및 <a href="pilot-status.html">진행 상태판</a>에서 확인하세요.
</div>

</body>
</html>
"""
with open(os.path.join(_ROOT, "pilot-visual.html"), "w", encoding="utf-8") as f:
    f.write(html)
print("생성 완료: pilot-visual.html", len(html), "bytes / 차트점", n)

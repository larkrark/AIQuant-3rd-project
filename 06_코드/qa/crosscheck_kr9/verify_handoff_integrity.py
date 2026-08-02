# -*- coding: utf-8 -*-
"""KR9 인계패키지 무결성 — git 원본 blob 으로 검증.

파일시스템 추출은 Windows 경로길이 제한으로 파일을 흘리고, 체크아웃 필터가
개행을 바꾼다. blob 을 직접 읽으면 둘 다 우회한다.
"""
import csv
import io
import os
import subprocess
import sys
import hashlib

sys.stdout.reconfigure(encoding="utf-8")
REPO = r"c:\Users\zzxxc\Documents\deep_lerning\venv\AIQuant-3rd-project"
BR = "origin/인계/KR9-정기보고서-1차완결-20260801"
PKG = "handoff/260801_KR9_정기보고서_3방향_1차완결_인계패키지_v1.0"


def git(*args):
    # core.quotepath=false — 비ASCII 경로를 \NNN 로 이스케이프하지 않게 한다
    return subprocess.run(["git", "-C", REPO, "-c", "core.quotepath=false", *args],
                          capture_output=True)


# 경로 -> blob sha 색인
out = git("ls-tree", "-r", BR, "--format=%(objectname) %(path)").stdout.decode("utf-8")
index = {}
for line in out.splitlines():
    sha, _, path = line.partition(" ")
    index[path.strip('"')] = sha

# SHA256SUMS 자체를 blob 에서 읽는다
sums_path = f"{PKG}/05_무결성/SHA256SUMS.csv"
raw = git("cat-file", "blob", index[sums_path]).stdout
rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))

print("=" * 68)
print("KR9 인계패키지 무결성 — git 원본 blob 대조")
print("=" * 68)
print(f"  SHA256SUMS.csv  {len(rows)}행\n")

ok = bad = miss = 0
bads, misses = [], []
for r in rows:
    rel = r["상대경로"].replace("\\", "/")
    full = f"{PKG}/{rel}"
    sha = index.get(full)
    if sha is None:
        miss += 1
        misses.append(rel)
        continue
    blob = git("cat-file", "blob", sha).stdout
    h = hashlib.sha256(blob).hexdigest().upper()
    if h == r["SHA256"].upper():
        ok += 1
    else:
        bad += 1
        crlf = hashlib.sha256(blob.replace(b"\n", b"\r\n")).hexdigest().upper()
        lf = hashlib.sha256(blob.replace(b"\r\n", b"\n")).hexdigest().upper()
        why = ("LF→CRLF 로 일치" if crlf == r["SHA256"].upper()
               else "CRLF→LF 로 일치" if lf == r["SHA256"].upper()
               else "개행 무관 — 내용 상이")
        bads.append((rel, why))

print(f"[결과] 일치 {ok} · 불일치 {bad} · git 에 없음 {miss}   (전체 {len(rows)})")

if bads:
    print("\n[불일치]")
    for rel, why in bads:
        print(f"  ★ {why:<18} {rel}")

if misses:
    print("\n[git 에 없음]")
    for m in misses:
        print(f"  ★ {m}")

# 반대 방향 — 패키지에 있는데 SHA256SUMS 에 없는 파일
listed = {r["상대경로"].replace("\\", "/") for r in rows}
actual = {p[len(PKG) + 1:] for p in index if p.startswith(PKG + "/")}
extra = sorted(actual - listed)
print(f"\n[매니페스트 미기재] 패키지 {len(actual)}개 중 {len(extra)}개")
for e in extra:
    print(f"  · {e}")

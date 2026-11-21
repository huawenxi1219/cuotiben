# -*- coding: utf-8 -*-
"""排版审计：找可能溢出屏幕的 Row（多按钮不换行）、写死宽度的弹窗内容。"""
import io, re

SRC = r"C:\myapp\main.py"
lines = io.open(SRC, encoding="utf-8").read().split("\n")

# ---- 1) 括号配平，抓出每个 ft.Row( ... ) 的完整范围 ----
rows = []
for i, ln in enumerate(lines):
    if "ft.Row(" not in ln:
        continue
    depth = 0
    started = False
    j = i
    body = []
    while j < len(lines):
        seg = lines[j]
        for ch in seg:
            if ch in "([{":
                depth += 1
                started = True
            elif ch in ")]}":
                depth -= 1
        body.append(seg)
        if started and depth <= 0:
            break
        j += 1
    text = "\n".join(body)
    n_btn = len(re.findall(r"ft\.(?:ElevatedButton|TextButton|OutlinedButton|IconButton)\(", text))
    has_wrap = "wrap=True" in text
    has_expand = "expand=True" in text
    rows.append((i + 1, j + 1, n_btn, has_wrap, has_expand, body[0].strip()[:60]))

print("=== A. 一行里挤了 ≥3 个按钮且没 wrap（窄屏会溢出） ===")
for s, e, n, wrap, exp, head in rows:
    if n >= 3 and not wrap:
        print(f"  L{s}-{e}  按钮 {n} 个  {head}")

# ---- 2) 写死宽度的控件（>320 在 360 宽手机上容易顶边） ----
print("\n=== B. 写死宽度 ≥ 330 的控件（弹窗/卡片） ===")
for i, ln in enumerate(lines, 1):
    m = re.search(r"width=(\d{3,4})", ln)
    if m:
        w = int(m.group(1))
        if 330 <= w <= 900:
            print(f"  L{i}  width={w}  {ln.strip()[:70]}")

# ---- 3) AlertDialog 的 content 用了固定宽度 Column/Container ----
print("\n=== C. AlertDialog 内容里的固定宽度 ===")
for i, ln in enumerate(lines, 1):
    if re.search(r"(Column|Container|TextField)\([^)]*width=3[0-9]{2}", ln):
        print(f"  L{i}  {ln.strip()[:80]}")

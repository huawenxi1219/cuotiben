# -*- coding: utf-8 -*-
"""改完代码先跑这个：语法 → Flet API → 函数参数。任一失败就返回非 0。
（界面巡检另外跑：DSH_SMOKE=1 python main.py）
"""
import subprocess, sys

MAIN = r"C:\myapp\main.py"
STEPS = [
    ("语法编译", [sys.executable, "-m", "py_compile", MAIN]),
    ("Flet API", [sys.executable, r"C:\myapp\_check_flet_api.py", MAIN]),
    ("函数参数", [sys.executable, r"C:\myapp\_check_arity.py", MAIN]),
]

failed = 0
for name, cmd in STEPS:
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (r.stdout or "").strip()
    if r.returncode != 0:
        failed += 1
        print(f"[FAIL] {name}")
        print(out[-800:])
    else:
        tail = out.splitlines()[-1] if out else "ok"
        print(f"[OK]   {name}  {tail if '问题' in tail or '发现' in tail else ''}")

print("\n全部通过" if failed == 0 else f"\n{failed} 项失败")
sys.exit(1 if failed else 0)

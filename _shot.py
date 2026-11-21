# -*- coding: utf-8 -*-
"""启动 App（手机比例）→ 等界面出来 → 截屏 → 退出。
用法：python _shot.py <输出png> [等待秒数]
"""
import os, subprocess, sys, time
from PIL import ImageGrab

out = sys.argv[1] if len(sys.argv) > 1 else r"C:\myapp\_shot.png"
wait = float(sys.argv[2]) if len(sys.argv) > 2 else 9.0

env = dict(os.environ)
env["DSH_PHONE_SIM"] = "1"
env["PYTHONIOENCODING"] = "utf-8"

p = subprocess.Popen([sys.executable, "-u", "main.py"],
                     cwd=r"C:\myapp", env=env,
                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)
try:
    time.sleep(wait)
    img = ImageGrab.grab()
    img.save(out)
    print("saved", out, img.size)
finally:
    p.terminate()
    try:
        p.wait(timeout=5)
    except Exception:
        p.kill()
    out_txt = p.stdout.read().decode("utf-8", "replace") if p.stdout else ""
    print("--- app stdout ---")
    print(out_txt[-800:])

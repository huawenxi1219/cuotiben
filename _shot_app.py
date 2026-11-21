# -*- coding: utf-8 -*-
"""启动 App → 前台显示窗口 → 按窗口坐标截图 → 退出。"""
import ctypes, os, subprocess, sys, time
from ctypes import wintypes
from PIL import ImageGrab

out = sys.argv[1] if len(sys.argv) > 1 else r"C:\myapp\_app.png"
wait = float(sys.argv[2]) if len(sys.argv) > 2 else 8.0
title = "池鱼Study"

user32 = ctypes.windll.user32
user32.SetProcessDPIAware()

env = dict(os.environ)
env["DSH_PHONE_SIM"] = "1"
env["PYTHONIOENCODING"] = "utf-8"

p = subprocess.Popen([sys.executable, "-u", "main.py"], cwd=r"C:\myapp",
                     env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
try:
    hwnd = None
    for _ in range(40):
        time.sleep(0.5)
        hwnd = user32.FindWindowW(None, title)
        if hwnd:
            break
    if not hwnd:
        print("!! 找不到窗口", title)
    else:
        time.sleep(max(0.0, wait - 2))
        user32.ShowWindow(hwnd, 9)          # SW_RESTORE
        user32.SetForegroundWindow(hwnd)
        time.sleep(0.6)
        r = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(r))
        print("window rect:", r.left, r.top, r.right, r.bottom)
        img = ImageGrab.grab(bbox=(r.left, r.top, r.right, r.bottom))
        img.save(out)
        print("saved", out, img.size)
finally:
    p.terminate()
    try:
        p.wait(timeout=5)
    except Exception:
        p.kill()
    if p.stdout:
        txt = p.stdout.read().decode("utf-8", "replace")
        print("--- app stdout ---")
        print(txt[-600:])

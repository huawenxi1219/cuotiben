# -*- coding: utf-8 -*-
"""用 PrintWindow 直接抓指定窗口的内容（即使被遮挡也能抓到）。"""
import ctypes, os, subprocess, sys, time
from ctypes import wintypes
from PIL import Image

out = sys.argv[1] if len(sys.argv) > 1 else r"C:\myapp\_app.png"
wait = float(sys.argv[2]) if len(sys.argv) > 2 else 10.0
title = "池鱼Study"

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
user32.SetProcessDPIAware()

env = dict(os.environ)
env["DSH_PHONE_SIM"] = os.environ.get("SHOT_SIM", "1")
if os.environ.get("SHOT_SIM", "1") == "1":
    env["DSH_FORCE_MOBILE"] = "1"
env["PYTHONIOENCODING"] = "utf-8"

def capture(hwnd, path):
    r = wintypes.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(r))
    w, h = r.right - r.left, r.bottom - r.top
    if w <= 0 or h <= 0:
        print("!! 窗口尺寸异常", w, h)
        return False
    hdc = user32.GetWindowDC(hwnd)
    mfc = gdi32.CreateCompatibleDC(hdc)
    bmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
    gdi32.SelectObject(mfc, bmp)
    # 2 = PW_RENDERFULLCONTENT
    ok = user32.PrintWindow(hwnd, mfc, 2)
    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG),
                    ("biHeight", wintypes.LONG), ("biPlanes", wintypes.WORD),
                    ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                    ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
                    ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD),
                    ("biClrImportant", wintypes.DWORD)]
    bi = BITMAPINFOHEADER()
    bi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bi.biWidth = w
    bi.biHeight = -h
    bi.biPlanes = 1
    bi.biBitCount = 32
    bi.biCompression = 0
    buf = ctypes.create_string_buffer(w * h * 4)
    gdi32.GetDIBits(mfc, bmp, 0, h, buf, ctypes.byref(bi), 0)
    img = Image.frombuffer("RGBA", (w, h), buf, "raw", "BGRA", 0, 1).convert("RGB")
    img.save(path)
    gdi32.DeleteObject(bmp)
    gdi32.DeleteDC(mfc)
    user32.ReleaseDC(hwnd, hdc)
    print("printwindow_ok:", ok, "size:", (w, h), "->", path)
    return True

p = subprocess.Popen([sys.executable, "-u", "main.py"], cwd=r"C:\myapp",
                     env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
try:
    hwnd = None
    for _ in range(30):
        time.sleep(0.5)
        hwnd = user32.FindWindowW(None, title)
        if hwnd:
            break
    if not hwnd:
        print("!! 窗口未出现")
    else:
        time.sleep(wait)
        capture(hwnd, out)
finally:
    p.terminate()
    try:
        p.wait(timeout=5)
    except Exception:
        p.kill()
    # Flet 的窗口是独立的 flet.exe 客户端进程，必须一并关掉，否则会留一堆窗口
    subprocess.run(['taskkill', '/F', '/IM', 'flet.exe'],
                   capture_output=True)
    if p.stdout:
        print((p.stdout.read().decode("utf-8", "replace") or "")[-500:])

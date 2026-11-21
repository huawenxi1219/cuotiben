# -*- coding: utf-8 -*-
"""解压 apkstart 运行时里被压缩的系统镜像（ApkStart 原本会自动做这步）。"""
import lzma, gzip, os, shutil, time

IMG = r"C:\Users\黄\AppData\Roaming\apkstart\runtime\system-images\android-34\google_apis_playstore\x86_64"


def unxz(name):
    src = os.path.join(IMG, name + ".xz")
    dst = os.path.join(IMG, name)
    if not os.path.exists(src) or os.path.exists(dst):
        print("skip", name)
        return
    t0 = time.time()
    with lzma.open(src, "rb") as fin, open(dst, "wb") as fout:
        shutil.copyfileobj(fin, fout, 1 << 20)
    print(f"{name}: {os.path.getsize(dst)/1e9:.2f} GB, {time.time()-t0:.0f}s")


def ungz(name, out):
    src = os.path.join(IMG, name)
    dst = os.path.join(IMG, out)
    if not os.path.exists(src) or os.path.exists(dst):
        print("skip", out)
        return
    with gzip.open(src, "rb") as fin, open(dst, "wb") as fout:
        shutil.copyfileobj(fin, fout, 1 << 20)
    print(f"{out}: {os.path.getsize(dst)/1e6:.1f} MB")


unxz("system.img")
unxz("vendor.img")
ungz("userdata.img.gz", "userdata.img")
print("done")

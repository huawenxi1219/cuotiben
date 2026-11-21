# -*- coding: utf-8 -*-
"""统一 FLET_CACHE_DIR，让预置的 CPython 包被 serious_python 命中。"""
import io

P = r"C:\myapp\.github\workflows\build.yml"
t = io.open(P, encoding="utf-8").read()

JOB_ENV = """    env:
      FLET_CACHE_DIR: ${{ github.workspace }}/.fletcache
"""

if "FLET_CACHE_DIR" not in t:
    t = t.replace("""    permissions:
      contents: write
""", """    permissions:
      contents: write
""" + JOB_ENV, 1)

t = t.replace('DIR="$HOME/.flet/cache/python-build-standalone/20250205"',
              'DIR="$FLET_CACHE_DIR/python-build-standalone/20250205"')

io.open(P, "w", encoding="utf-8", newline="\n").write(t)
print("done")

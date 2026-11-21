# -*- coding: utf-8 -*-
"""CI 试验：把 Android Python 运行时指向现存 release（20261027 / 3.12.16），
   绕过 flet 0.28.3 默认的 20250205（上游已删除）。"""
import io

P = r"C:\myapp\.github\workflows\build.yml"
t = io.open(P, encoding="utf-8").read()

if "SERIOUS_PYTHON_FULL_VERSION" not in t:
    t = t.replace("      GRADLE_OPTS: >-",
                  "      SERIOUS_PYTHON_VERSION: \"3.12\"\n"
                  "      SERIOUS_PYTHON_FULL_VERSION: \"3.12.16\"\n"
                  "      SERIOUS_PYTHON_BUILD_DATE: \"20261027\"\n"
                  "      GRADLE_OPTS: >-", 1)

io.open(P, "w", encoding="utf-8", newline="\n").write(t)
print("env 覆盖已加入")

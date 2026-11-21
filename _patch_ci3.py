# -*- coding: utf-8 -*-
"""CI：改用 GitHub API 资产接口下载 CPython 包（release CDN 504），并保留多级回退。"""
import io

P = r"C:\myapp\.github\workflows\build.yml"
t = io.open(P, encoding="utf-8").read()

start = t.index("      - name: 预置 CPython 运行时")
end = t.index("      - name: 打包 APK", start)

NEW = '''      - name: 预置 CPython 运行时（绕过 release CDN 504）
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          set -euo pipefail
          DIR="$HOME/.flet/cache/python-build-standalone/20250205"
          FILE="cpython-3.12.9+20250205-x86_64-unknown-linux-gnu-install_only_stripped.tar.gz"
          ASSET_ID=226610613
          mkdir -p "$DIR"
          ok=0
          for i in 1 2 3 4 5; do
            echo "===== 第 $i 次尝试下载 CPython ====="

            # 方式一：API 资产接口（带 token，绕过 releases/download 的 504）
            if curl -fL --retry 3 --retry-all-errors --connect-timeout 20 --max-time 600 \\
                 -H "Authorization: Bearer $GH_TOKEN" \\
                 -H "Accept: application/octet-stream" \\
                 -o "$DIR/$FILE.part" \\
                 "https://api.github.com/repos/astral-sh/python-build-standalone/releases/assets/$ASSET_ID" \\
               && tar tzf "$DIR/$FILE.part" > /dev/null 2>&1; then
              mv "$DIR/$FILE.part" "$DIR/$FILE"
              echo "✅ 通过 API 资产接口获取成功：$(stat -c%s "$DIR/$FILE") bytes"
              ok=1; break
            fi
            rm -f "$DIR/$FILE.part"

            # 方式二：官方 release 直链（CDN 恢复时可用）
            if curl -fL --retry 3 --retry-all-errors --connect-timeout 20 --max-time 600 \\
                 -o "$DIR/$FILE.part" \\
                 "https://github.com/astral-sh/python-build-standalone/releases/download/20250205/$FILE" \\
               && tar tzf "$DIR/$FILE.part" > /dev/null 2>&1; then
              mv "$DIR/$FILE.part" "$DIR/$FILE"
              echo "✅ 通过 release 直链获取成功：$(stat -c%s "$DIR/$FILE") bytes"
              ok=1; break
            fi
            rm -f "$DIR/$FILE.part"
            sleep 10
          done
          if [ "$ok" != "1" ]; then echo "❌ 无法获取完整 CPython 包"; exit 1; fi
          ls -la "$DIR"

'''

t = t[:start] + NEW + t[end:]
io.open(P, "w", encoding="utf-8", newline="\n").write(t)
print("下载逻辑已改为 API 资产优先")

# -*- coding: utf-8 -*-
"""CI 修复：
1) 打包前预置并校验 CPython 运行时（serious_python 下载不校验完整性，截断即静默失败）
2) 打包后强制校验 APK 产物，避免假成功
"""
import io

P = r"C:\myapp\.github\workflows\build.yml"
t = io.open(P, encoding="utf-8").read()

# 找到现有的打包步骤整段（从 "- name: 打包" 到下一个 "- name:" 之前）
start = t.index("      - name: 打包 APK")
end = t.index("      - name: 检查 APK 签名指纹", start)

NEW = '''      - name: 预置 CPython 运行时（serious_python 下载不校验完整性）
        run: |
          set -euo pipefail
          DIR="$HOME/.flet/cache/python-build-standalone/20250205"
          FILE="cpython-3.12.9+20250205-x86_64-unknown-linux-gnu-install_only_stripped.tar.gz"
          URL="https://github.com/astral-sh/python-build-standalone/releases/download/20250205/$FILE"
          mkdir -p "$DIR"
          ok=0
          for i in 1 2 3 4 5; do
            echo "===== 下载 CPython 第 $i 次 ====="
            if curl -fL --retry 5 --retry-all-errors --retry-delay 5 \\
                 --connect-timeout 20 --max-time 600 \\
                 -o "$DIR/$FILE.part" "$URL" && tar tzf "$DIR/$FILE.part" > /dev/null 2>&1; then
              mv "$DIR/$FILE.part" "$DIR/$FILE"
              echo "✅ CPython 包校验通过：$(stat -c%s "$DIR/$FILE") bytes"
              ok=1
              break
            fi
            rm -f "$DIR/$FILE.part"
            sleep 10
          done
          if [ "$ok" != "1" ]; then echo "❌ 无法获取完整 CPython 包"; exit 1; fi

      - name: 打包 APK（用命令行参数传签名）
        run: |
          set -euo pipefail
          df -h /home/runner
          flet build apk \\
            --build-number ${{ github.run_number }} \\
            --build-version 1.0.${{ github.run_number }} \\
            --android-signing-key-store "${{ github.workspace }}/my-release-key.keystore" \\
            --android-signing-key-alias "${{ secrets.ALIAS }}" \\
            --android-signing-key-password "${{ secrets.ALIAS_PASSWORD }}" \\
            --android-signing-key-store-password "${{ secrets.KEYSTORE_PASSWORD }}"
          echo "=== 产物检查 ==="
          ls -la build/apk/ || true
          APK=$(find build -name '*.apk' -type f | head -1)
          if [ -z "$APK" ]; then echo "❌ 没有生成任何 APK"; exit 1; fi
          echo "✅ 生成: $APK ($(stat -c%s "$APK") bytes)"
          mkdir -p build/apk
          cp "$APK" build/apk/ || true
          ls -la build/apk/

'''

t = t[:start] + NEW + t[end:]
io.open(P, "w", encoding="utf-8", newline="\n").write(t)
print("workflow 已重写打包段")

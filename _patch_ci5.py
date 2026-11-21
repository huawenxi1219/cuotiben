# -*- coding: utf-8 -*-
"""CI：加长 Gradle 网络超时 + 整段打包重试（Gradle 下载偶发 Read timed out）。"""
import io

P = r"C:\myapp\.github\workflows\build.yml"
t = io.open(P, encoding="utf-8").read()

# 1) job env 增加 Gradle 超时参数
if "GRADLE_OPTS" not in t:
    t = t.replace("      FLET_CACHE_DIR: ${{ github.workspace }}/.fletcache",
                  "      FLET_CACHE_DIR: ${{ github.workspace }}/.fletcache\n"
                  "      GRADLE_OPTS: >-\n"
                  "        -Dorg.gradle.internal.http.socketTimeout=180000\n"
                  "        -Dorg.gradle.internal.http.connectionTimeout=180000\n"
                  "        -Dorg.gradle.daemon=false", 1)

# 2) 打包改成可重试
start = t.index("      - name: 打包 APK")
end = t.index("      - name: 检查 APK 签名指纹", start)

NEW = '''      - name: 打包 APK（用命令行参数传签名）
        run: |
          set -uo pipefail
          df -h /home/runner
          ok=0
          for attempt in 1 2 3; do
            echo "===== 第 $attempt 次打包 ====="
            rm -rf build
            if flet build apk \\
              --build-number ${{ github.run_number }} \\
              --build-version 1.0.${{ github.run_number }} \\
              --android-signing-key-store "${{ github.workspace }}/my-release-key.keystore" \\
              --android-signing-key-alias "${{ secrets.ALIAS }}" \\
              --android-signing-key-password "${{ secrets.ALIAS_PASSWORD }}" \\
              --android-signing-key-store-password "${{ secrets.KEYSTORE_PASSWORD }}"; then
              ok=1
              echo "✅ 第 $attempt 次打包成功"
              break
            fi
            echo "⚠️ 第 $attempt 次失败，30s 后重试"
            sleep 30
          done
          echo "=== 产物检查 ==="
          APK=$(find build -name '*.apk' -type f | head -1 || true)
          if [ -z "$APK" ]; then echo "❌ 没有生成任何 APK（ok=$ok）"; exit 1; fi
          echo "✅ 生成: $APK ($(stat -c%s "$APK") bytes)"
          mkdir -p build/apk
          cp "$APK" build/apk/
          ls -la build/apk/

'''

t = t[:start] + NEW + t[end:]
io.open(P, "w", encoding="utf-8", newline="\n").write(t)
print("done")

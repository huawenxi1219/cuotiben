# -*- coding: utf-8 -*-
"""给打包步骤加重试：flet 下载的独立 Python 偶发解压失败（No such file or directory）。"""
import io

P = r"C:\myapp\.github\workflows\build.yml"
t = io.open(P, encoding="utf-8").read()

OLD = '''      - name: 打包 APK（用命令行参数传签名）
        run: |
          flet build apk --verbose \\
            --build-number ${{ github.run_number }} \\
            --build-version 1.0.${{ github.run_number }} \\
            --android-signing-key-store "${{ github.workspace }}/my-release-key.keystore" \\
            --android-signing-key-alias "${{ secrets.ALIAS }}" \\
            --android-signing-key-password "${{ secrets.ALIAS_PASSWORD }}" \\
            --android-signing-key-store-password "${{ secrets.KEYSTORE_PASSWORD }}"'''

NEW = '''      - name: 打包 APK（用命令行参数传签名）
        run: |
          df -h /home/runner
          flet --version || true
          for attempt in 1 2 3; do
            echo "===== 第 $attempt 次打包尝试 ====="
            rm -rf build
            if flet build apk \\
              --build-number ${{ github.run_number }} \\
              --build-version 1.0.${{ github.run_number }} \\
              --android-signing-key-store "${{ github.workspace }}/my-release-key.keystore" \\
              --android-signing-key-alias "${{ secrets.ALIAS }}" \\
              --android-signing-key-password "${{ secrets.ALIAS_PASSWORD }}" \\
              --android-signing-key-store-password "${{ secrets.KEYSTORE_PASSWORD }}"; then
              echo "打包成功（第 $attempt 次）"
              break
            fi
            echo "第 $attempt 次失败，清理后重试"
            sleep 15
          done
          ls -la build/flutter/app/app.zip build/apk 2>/dev/null || true'''

assert OLD in t, "打包步骤未匹配"
t = t.replace(OLD, NEW, 1)
io.open(P, "w", encoding="utf-8", newline="\n").write(t)
print("已加入 3 次重试")

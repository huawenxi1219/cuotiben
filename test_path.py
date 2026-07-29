import os
import json

# 测试路径
test_dir = r"C:\Users\黄\Desktop\错题笔记助手"

# 检查文件夹里有哪些文件
print("📁 文件夹内容：")
for f in os.listdir(test_dir):
    print(f"  - {f}")

# 尝试读取 errors.jsonl（如果有的话）
errors_file = os.path.join(test_dir, "errors.jsonl")
if os.path.exists(errors_file):
    try:
        with open(errors_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            print(f"\n✅ errors.jsonl 读取成功，共 {len(lines)} 行")
    except Exception as e:
        print(f"\n❌ errors.jsonl 读取失败: {e}")
else:
    print("\n⚠️ errors.jsonl 不存在")
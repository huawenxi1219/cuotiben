# -*- coding: utf-8 -*-
"""错题永久编号（按学科分别编号）：数学 #001、化学 #001 互不干扰。

- 录题时分配 no = 该学科已有最大号 + 1
- 启动时给老数据补号（按录入时间先后）
- 导出/查询都用这个号，纸上和软件永远对得上
"""
import io
import re

MAIN = r"C:\myapp\main.py"
t = io.open(MAIN, encoding="utf-8").read()

# ---------- 1) 模块级：补号函数 ----------
ANCHOR = "def save_error(subject, original=\"\", original_media=None,"
HELPER = '''def ensure_error_numbers():
    """给没有 no 的老错题按学科补编号（按时间先后）。"""
    try:
        data = load_jsonl(ERRORS_FILE)
        changed = False
        by_subj = {}
        for e in data:
            s = e.get("subject") or "未分类"
            by_subj.setdefault(s, []).append(e)
        for s, arr in by_subj.items():
            used = [int(x.get("no")) for x in arr if str(x.get("no") or "").isdigit()]
            nxt = (max(used) + 1) if used else 1
            for e in sorted(arr, key=lambda x: x.get("timestamp") or 0):
                if not str(e.get("no") or "").isdigit():
                    e["no"] = nxt
                    nxt += 1
                    changed = True
        if changed:
            save_jsonl(ERRORS_FILE, data)
    except BaseException as _be:
        _diag_log(_be, "ensure_no")


def next_error_no(subject):
    """该学科下一个可用编号。"""
    try:
        data = load_jsonl(ERRORS_FILE)
        used = [int(e.get("no")) for e in data
                if e.get("subject") == subject and str(e.get("no") or "").isdigit()]
        return (max(used) + 1) if used else 1
    except BaseException:
        return 1


'''
assert ANCHOR in t
if "def ensure_error_numbers" not in t:
    t = t.replace(ANCHOR, HELPER + ANCHOR, 1)

# ---------- 2) save_error 带上 no ----------
OLD = '''    entry = {
        "type": "error", "subject": subject, "original": original, "original_media": original_media,'''
NEW = '''    entry = {
        "type": "error", "subject": subject, "no": next_error_no(subject),
        "original": original, "original_media": original_media,'''
assert OLD in t
t = t.replace(OLD, NEW, 1)

# ---------- 3) 启动时补号 ----------
OLD_INIT = '''    ensure_data_dirs()'''
if OLD_INIT in t and "ensure_error_numbers()" not in t.split("def main(")[-1][:2000]:
    t = t.replace(OLD_INIT, '''    ensure_data_dirs()
    ensure_error_numbers()''', 1)

# ---------- 4) 导出时用永久编号 ----------
OLD_RENDER = '''            no = first_no + i
            d.text((inner_x, cur_y), f"{no:03d}", font=f_no, fill=(180, 60, 60))'''
t = t.replace(OLD_RENDER, OLD_RENDER, 1)   # 在 a4_render 里改，这里不动

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(t)
print("永久编号已写入主程序")

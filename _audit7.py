# -*- coding: utf-8 -*-
"""第34轮 AST 静态审计：验证新增代码的 定义→引用 时序与作用域，防止闭包陷阱。"""
import ast
import sys

SRC = r"C:\myapp\main.py"
with open(SRC, encoding="utf-8") as f:
    src = f.read()
tree = ast.parse(src)

fails = []


def find_def(func_name):
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func_name:
            return node
    return None


def def_order_in_fn(fn_node, names):
    """返回 fn_node 内各 name 的‘首次定义行’（赋值/def/参数），未定义为 -1"""
    order = {}
    for n in ast.walk(fn_node):
        if isinstance(n, ast.FunctionDef):
            if n.name in names:
                order.setdefault(n.name, n.lineno)
        elif isinstance(n, (ast.Assign, ast.AnnAssign)):
            for t in n.targets if isinstance(n, ast.Assign) else [n.target]:
                if isinstance(t, ast.Name) and t.id in names:
                    order.setdefault(t.id, n.lineno)
    return order


# 1) build_chat_window 内：抽屉函数必须先于 make_user_bubble / make_ai_bubble 定义
bcw = find_def("build_chat_window")
if bcw is None:
    fails.append("找不到 build_chat_window")
else:
    needed = ["_drawer_add_item", "_drawer_remove_item", "_drawer_open", "_drawer_close",
              "_ask_collect_menu", "_ai_fill_fields", "_drawer_done", "drawer_container"]
    order = def_order_in_fn(bcw, needed)
    for name in needed:
        if name not in order:
            fails.append(f"build_chat_window 内未定义 {name}")
    for m in ["make_user_bubble", "make_ai_bubble"]:
        mb = find_def(m)
        if mb is None:
            fails.append(f"找不到 {m}")
            continue
        mb_lineno = mb.lineno
        for name in needed:
            if order.get(name, 0) > mb_lineno:
                fails.append(f"{name}(L{order[name]}) 定义晚于 {m}(L{mb_lineno}) —— 气泡引用时可能未定义")

# 2) cam_btn 定义先于输入行 Row 使用
cam_def = None
input_row_use = None
for n in ast.walk(bcw if bcw else tree):
    if isinstance(n, ast.Assign):
        for t in n.targets:
            if isinstance(t, ast.Name) and t.id == "cam_btn":
                cam_def = n.lineno
    if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "Row":
        ids = [x.id for x in ast.walk(n) if isinstance(x, ast.Name) and x.id == "cam_btn"]
        if ids and input_row_use is None:
            input_row_use = n.lineno
if cam_def is None:
    fails.append("找不到 cam_btn 定义")
elif input_row_use is not None and cam_def > input_row_use:
    fails.append(f"cam_btn 定义(L{cam_def})晚于输入行使用(L{input_row_use})")

# 3) 模块级：_match_existing_kp / _ai_extract_chat 已定义
for fn in ["_match_existing_kp", "_ai_extract_chat"]:
    if find_def(fn) is None:
        fails.append(f"缺少模块级函数 {fn}")

# 4) save_note 签名含 tags
sn = find_def("save_note")
if sn is None:
    fails.append("缺少 save_note")
else:
    argnames = [a.arg for a in sn.args.args]
    if "tags" not in argnames:
        fails.append(f"save_note 参数缺 tags：{argnames}")

# 5) DeepSeek 推理档位：call_ai_stream 内四档校验存在
cas = find_def("call_ai_stream")
if cas is None:
    fails.append("找不到 call_ai_stream")
else:
    cas_src = ast.get_source_segment(src, cas)
    if "reasoning_effort" not in cas_src:
        fails.append("call_ai_stream 无 reasoning_effort 注入")
    for lv in ("low", "medium", "high", "max"):
        if lv not in cas_src:
            fails.append(f"call_ai_stream 缺档位 {lv}")

# 6) 设置页含 deepseek_reasoning_dropdown 与 save_keys 保存
tree_src = src
if "deepseek_reasoning_dropdown" not in tree_src:
    fails.append("设置页缺 deepseek_reasoning_dropdown")
if '"deepseek_reasoning"' not in tree_src:
    fails.append("save_keys 未保存 deepseek_reasoning")

# 7) 抽屉完成键调用 save_error/save_note 的路径存在
if "def _drawer_done" not in src:
    fails.append("缺少 _drawer_done")
else:
    dd = find_def("_drawer_done")
    dd_src = ast.get_source_segment(src, dd)
    if "save_error(" not in dd_src or "save_note(" not in dd_src:
        fails.append("_drawer_done 未同时调 save_error/save_note")

# 8) 长按事件 on_long_press 已挂
if "on_long_press=lambda e: _ask_collect_menu" not in src:
    fails.append("气泡未挂长按收录")

if fails:
    print("FAIL 项：")
    for f in fails:
        print(" -", f)
    sys.exit(1)
print(f"AST 审计全部通过（build_chat_window 定义顺序 / cam_btn 时序 / 模块函数 / 档位 / 抽屉闭环）")

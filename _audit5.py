# -*- coding: utf-8 -*-
"""正确版：AST 递归嵌套树 + nonlocal 声明核查 + 关键函数链"""
import io, sys, ast
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
out = []
src = open(r'C:\myapp\main.py', encoding='utf-8', errors='replace').read()
tree = ast.parse(src)

# ---------- 1. 正确嵌套树：递归进入 FunctionDef body 才进新作用域 ----------
records = []
def visit(node, scope_stack, def_chain):
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            records.append({'name': child.name, 'scope': ' > '.join(def_chain) if def_chain else '<MODULE>',
                            'line': child.lineno, 'end': child.end_lineno})
            visit(child, scope_stack, def_chain + [child.name])
        else:
            visit(child, scope_stack, def_chain)
visit(tree, [], [])

# 关键函数与其真实父链
out.append('==== 关键函数真实嵌套链 ====')
watch = ['load_ui', 'build_chat_window', 'make_user_bubble', 'make_ai_bubble',
         'add_to_errorbook', 'ask_similar_q', 'regenerate_last', 'handle_send',
         '_send_internal', 'stop_generation', '_continue_generation', 'clear_history',
         'build_error_list_page', 'open_mm_view', 'open_ask_teacher', 'open_edit',
         'build_note_list_page', 'open_mm_from_note', 'build_mindmap_page',
         'mastery_for', 'rebuild_mindmap_view', '_node_box', '_apply_highlight',
         '_start_grow', '_toggle_node', 'open_function_page', 'go_back',
         'build_subject_page', 'on_subject_selected', 'switch_page', 'show_toast']
for r in records:
    if r['name'] in watch:
        out.append('  %-26s L%-5d 链: %s' % (r['name'], r['line'], r['scope']))

# ---------- 2. 所有 nonlocal 声明 vs 最外层可用变量 ----------
out.append('\n==== nonlocal 声明核查 ====')
for r in records:
    # 找该函数体内的 Nonlocal 节点
    pass
for node in ast.walk(tree):
    if isinstance(node, ast.Nonlocal):
        out.append('  L%-5d nonlocal %s' % (node.lineno, ', '.join(node.names)))

# 统计非 local 声明函数上下文
out.append('\n==== 各 nonlocal 所在函数 ====')
fn_of = {}
for node in ast.walk(tree):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        fn_of[node.lineno] = node.name
for node in ast.walk(tree):
    if isinstance(node, ast.Nonlocal):
        # 向上找最近的 FunctionDef
        out.append('  nonlocal L%d -> 所在函数: %s (%s)' % (node.lineno, fn_of.get(node.lineno, '?'), ', '.join(node.names)))

# ---------- 3. 页面构建函数是否被 open_function_page 一次性全建（状态残留风险） ----------
out.append('\n==== open_function_page 每次构建的全部页面 ====')
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and node.name == 'open_function_page':
        for sub in ast.walk(node):
            if isinstance(sub, ast.Assign) and isinstance(sub.value, ast.Dict):
                for k in sub.value.keys:
                    if isinstance(k, ast.Constant):
                        out.append('  dict key: %s' % k.value)

# ---------- 4. main_subject_page / subject_page_content 双重赋值（残留风险） ----------
out.append('\n==== subject_page_content / main_subject_page / selected_subject_for_page 引用点 ====')
for node in ast.walk(tree):
    if isinstance(node, (ast.Name,)):
        if node.id in ('subject_page_content', 'main_subject_page', 'selected_subject_for_page'):
            ctx = '读' if isinstance(node.ctx, ast.Load) else ('写' if isinstance(node.ctx, ast.Store) else '删')
            if node.lineno and node.lineno < 8000:
                pass  # 太密，下面聚合
# 简化：直接统计出现行
import collections
for v in ['subject_page_content', 'main_subject_page', 'selected_subject_for_page']:
    lines = [node.lineno for node in ast.walk(tree) if isinstance(node, ast.Name) and node.id == v]
    out.append('  %s 出现 %d 次: %s' % (v, len(lines), lines[:40]))

open(r'C:\myapp\_audit5.txt', 'w', encoding='utf-8').write('\n'.join(out))
print('\n'.join(out))

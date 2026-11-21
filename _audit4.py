# -*- coding: utf-8 -*-
"""全软件系统级检查：函数嵌套树 + 关键状态变量定义/引用图谱 + 页面切换链路"""
import io, sys, ast, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
out = []
src = open(r'C:\myapp\main.py', encoding='utf-8', errors='replace').read()
tree = ast.parse(src)

# ---------- 1. 函数嵌套树（真实缩进层级） ----------
def fn_tree():
    result = []
    stack = []  # (indent, name, lineno)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            indent = node.col_offset
            while stack and stack[-1][0] >= indent:
                stack.pop()
            parent = stack[-1][1] if stack else '<MODULE>'
            result.append({'name': node.name, 'parent': parent, 'indent': indent,
                           'line': node.lineno, 'end': node.end_lineno})
            stack.append((indent, node.name))
    return result

tree_fns = fn_tree()
out.append('==== 全部函数与嵌套父级（共 %d 个） ====' % len(tree_fns))
for f in sorted(tree_fns, key=lambda x: x['line']):
    out.append('  L%-5d %-34s [父:%s]' % (f['line'], f['name'], f['parent']))

# ---------- 2. load_ui 内的关键状态变量（赋值位置） ----------
out.append('\n==== load_ui 作用域关键状态变量赋值位置 ====')
# 先找 load_ui 函数体的行范围
load_ui_range = None
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and node.name == 'load_ui':
        load_ui_range = (node.lineno, node.end_lineno)
        break
key_vars = ['subject_page_content', 'selected_subject_for_page', 'current_chat_subject',
            '_MM_HIGHLIGHT', 'current_page', 'chat_dialog', 'ball_container',
            'contact_panel', 'main_subject_page', 'stop_flag', 'generation_active']
if load_ui_range:
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)) and node.lineno > load_ui_range[0] and node.lineno < load_ui_range[1]:
            for t in (node.targets if isinstance(node, ast.Assign) else [node.target]):
                if isinstance(t, ast.Name) and t.id in key_vars:
                    out.append('  L%-5d %s = ...' % (node.lineno, t.id))

# ---------- 3. 关键函数互相调用关系（函数体内是否引用其他函数名） ----------
out.append('\n==== 关键函数调用关系（谁调用了谁） ====')
call_targets = ['switch_page', 'open_function_page', 'build_subject_page',
                'build_error_list_page', 'build_note_list_page', 'build_mindmap_page',
                'build_chat_window', 'build_vocab_page', 'build_sentence_page',
                'go_back', 'on_subject_selected', 'open_chat', 'close_contact_panel',
                'rebuild_mindmap_view', 'show_toast', 'load_mindmap', 'build_mindmap']
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and node.name in ['switch_page', 'open_function_page',
                                                           'build_subject_page', 'on_subject_selected',
                                                           'open_chat', 'build_mindmap_page', 'build_chat_window']:
        calls = []
        for sub in ast.walk(node):
            if isinstance(sub, ast.Call):
                f = sub.func
                if isinstance(f, ast.Name) and f.id in call_targets:
                    calls.append((sub.lineno, f.id))
        if calls:
            out.append('  %s: %s' % (node.name, ', '.join('L%d→%s' % c for c in calls)))

# ---------- 4. page.open / page.close 配对（弹窗层级风险） ----------
out.append('\n==== page.open 弹窗调用 ====')
opens = []
for node in ast.walk(tree):
    if isinstance(node, ast.Call):
        f = node.func
        if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id == 'page' and f.attr == 'open':
            opens.append(node.lineno)
out.append('  共 %d 处 page.open（AlertDialog/FilePicker 均在此列，正常）' % len(opens))

open(r'C:\myapp\_audit4.txt', 'w', encoding='utf-8').write('\n'.join(out))
print('\n'.join(out))

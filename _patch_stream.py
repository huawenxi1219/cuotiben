# -*- coding: utf-8 -*-
"""修复：1) 流式回答只读 content，忽略 reasoning_content（思考模式导致"没反应"）
   2) 测试连接 max_tokens 太小被思考吃掉 → 返回为空
   3) 批量录题点了没反应 → 异常要能看见
"""
import io

MAIN = r"C:\myapp\main.py"
t = io.open(MAIN, encoding="utf-8").read()

# ---------- 1) 流式解析同时支持 reasoning_content ----------
OLD = '''                    accumulated = ""
                    for line in resp.iter_lines(decode_unicode=True):
                        if stop_flag:
                            break
                        if line and line.startswith('data: ') and line[6:].strip() != '[DONE]':
                            try:
                                data = json.loads(line[6:])
                                delta = data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                if delta:
                                    accumulated += delta
                                    on_chunk(accumulated)
                            except BaseException as _be:
                                _diag_log(_be, "L3695")

                                continue
                    return accumulated'''
NEW = '''                    accumulated = ""
                    _reasoning_len = 0
                    for line in resp.iter_lines(decode_unicode=True):
                        if stop_flag:
                            break
                        if line and line.startswith('data: ') and line[6:].strip() != '[DONE]':
                            try:
                                data = json.loads(line[6:])
                                _d = data.get("choices", [{}])[0].get("delta", {}) or {}
                                delta = _d.get("content") or ""
                                # DeepSeek 思考模式会先吐 reasoning_content，之前被完全忽略 → 看着像没反应
                                _rs = _d.get("reasoning_content") or _d.get("reasoning") or ""
                                if _rs:
                                    _reasoning_len += len(_rs)
                                    if not accumulated:
                                        on_chunk(f"⏳ 正在思考…（已推理 {_reasoning_len} 字）")
                                if delta:
                                    accumulated += delta
                                    on_chunk(accumulated)
                            except BaseException as _be:
                                _diag_log(_be, "L3695")

                                continue
                    return accumulated'''
assert OLD in t, "流式解析未匹配"
t = t.replace(OLD, NEW, 1)

# ---------- 2) 测试连接：关掉思考 + 留够 token ----------
OLD2 = '''                        payload = {"model": api_model,
                                   "messages": [{"role": "user", "content": "仅回复OK"}],
                                   "max_tokens": 5, "temperature": 0}'''
NEW2 = '''                        payload = {"model": api_model,
                                   "messages": [{"role": "user", "content": "仅回复OK"}],
                                   "max_tokens": 64, "temperature": 0}
                        if str(api_model).startswith("deepseek"):
                            # 不关思考的话，64 个 token 可能全被推理吃掉，content 就是空的
                            payload["reasoning_effort"] = "none"'''
assert OLD2 in t, "测试连接 payload 未匹配"
t = t.replace(OLD2, NEW2, 1)

# 非 200 时把响应体贴出来，方便定位
OLD3 = '''                        else:
                            test_conn_result.value = f"❌ 连接失败 (HTTP {resp.status_code})"'''
NEW3 = '''                        else:
                            _body = (resp.text or "")[:80].replace("\\n", " ")
                            test_conn_result.value = f"❌ 连接失败 (HTTP {resp.status_code}) {_body}"'''
assert OLD3 in t
t = t.replace(OLD3, NEW3, 1)

# ---------- 3) 批量录题：异常可见 ----------
OLD4 = '''                _use_picker(page, _on_files).pick_files(
                    file_type=ft.FilePickerFileType.IMAGE, allow_multiple=True)'''
NEW4 = '''                try:
                    _use_picker(page, _on_files).pick_files(
                        file_type=ft.FilePickerFileType.IMAGE, allow_multiple=True)
                except Exception as _ex:
                    show_toast(f"打开相册失败：{str(_ex)[:60]}", "red")'''
assert OLD4 in t, "批量录题按钮未匹配"
t = t.replace(OLD4, NEW4, 1)

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(t)
print("三处修复已写入")

# -*- coding: utf-8 -*-
"""修复 DeepSeek 对话不回复：_cfg_thinking_off 未定义（NameError 导致请求没发出）。
同时：提高 max_tokens；流式无正文时自动关思考重试；仍为空则明确报错。"""
import io

MAIN = r"C:\myapp\main.py"
t = io.open(MAIN, encoding="utf-8").read()

# 1) 补上缺失的函数（模块级，放在 endpoint_for 之前）
ANCHOR = "def endpoint_for(task=\"smart\"):"
HELPER = '''def _cfg_thinking_off():
    """是否关闭 DeepSeek 的思考模式：默认关闭（保证对话框能看到正文）。"""
    try:
        return not bool(load_ai_config().get("deepseek_thinking", False))
    except BaseException:
        return True


'''
assert ANCHOR in t
if "def _cfg_thinking_off()" not in t:
    t = t.replace(ANCHOR, HELPER + ANCHOR, 1)

# 2) max_tokens 提到 8192，并给思考模式留足空间
OLD = '''                payload = {"model": api_model, "messages": messages,
                           "temperature": 0.7, "max_tokens": 4096, "stream": True}'''
NEW = '''                payload = {"model": api_model, "messages": messages,
                           "temperature": 0.7, "max_tokens": 8192, "stream": True}'''
assert OLD in t
t = t.replace(OLD, NEW, 1)

# 3) 流式结束若无正文：自动关思考重试一次；仍空则把原因显示出来
OLD2 = '''                    return accumulated
                except Exception as e:
                    on_chunk(f"❌ 异常: {str(e)}")
                    return None'''
NEW2 = '''                    if not accumulated.strip():
                        # 正文为空：多半是思考把 token 用光了。关掉思考重试一次（非流式）
                        _retry = dict(payload)
                        _retry["stream"] = False
                        _retry["max_tokens"] = 2048
                        if str(_retry.get("model", "")).startswith("deepseek"):
                            _retry["reasoning_effort"] = "none"
                        try:
                            r2 = requests.post(api_url, headers=headers, json=_retry, timeout=90)
                            if r2.status_code == 200:
                                _j = r2.json()
                                _c = (_j.get("choices") or [{}])[0].get("message", {}).get("content", "")
                                if _c and _c.strip():
                                    on_chunk(_c)
                                    return _c
                                _fin = (_j.get("choices") or [{}])[0].get("finish_reason", "")
                                on_chunk(f"❌ 模型没有返回正文（finish_reason={_fin}），"
                                         f"请到「我的 → AI 设置」把模型换成 deepseek-flash 再试")
                            else:
                                on_chunk(f"❌ 重试失败 {r2.status_code} {(r2.text or '')[:120]}")
                        except Exception as _e2:
                            on_chunk(f"❌ 重试异常：{str(_e2)[:120]}")
                        return accumulated
                    return accumulated
                except Exception as e:
                    on_chunk(f"❌ 异常: {str(e)}")
                    return None'''
assert OLD2 in t
t = t.replace(OLD2, NEW2, 1)

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(t)
print("DeepSeek 对话修复已应用")

# -*- coding: utf-8 -*-
"""等待反馈：请求发出后每秒更新"已等待 N 秒"，首字到达时打印耗时。"""
import io

MAIN = r"C:\myapp\main.py"
t = io.open(MAIN, encoding="utf-8").read()

OLD = '''                    def ai_thread():
                        nonlocal generation_active, stop_flag
                        generation_active = True
                        stop_flag = False
                        was_stopped = {"v": False}
                        try:
                            final_accum = call_ai_stream(current_messages, "auto", on_chunk, need_vision=_need_vision)'''
NEW = '''                    def ai_thread():
                        nonlocal generation_active, stop_flag
                        generation_active = True
                        stop_flag = False
                        was_stopped = {"v": False}
                        _wait = {"stop": False, "t0": time.time(), "first": False}

                        def _tick():
                            while not _wait["stop"]:
                                time.sleep(1.0)
                                if _wait["stop"]:
                                    return
                                try:
                                    if not ai_response["text"] and content_ref.get("stream"):
                                        content_ref["stream"].value = (
                                            f"⏳ 思考中… 已等待 {int(time.time() - _wait['t0'])}s")
                                        page.update()
                                except BaseException:
                                    pass

                        threading.Thread(target=_tick, daemon=True).start()
                        print(f"[CHAT] 请求已发出 model={_model_name} 消息数={len(current_messages)}")
                        try:
                            final_accum = call_ai_stream(current_messages, "auto", on_chunk, need_vision=_need_vision)
                            print(f"[CHAT] 响应结束 用时 {time.time() - _wait['t0']:.1f}s")'''
assert OLD in t, "ai_thread 未匹配"
t = t.replace(OLD, NEW, 1)

OLD2 = '''                        finally:
                            if gen_token["id"] == my_gen:'''
NEW2 = '''                        finally:
                            _wait["stop"] = True
                            if gen_token["id"] == my_gen:'''
assert OLD2 in t, "finally 未匹配"
t = t.replace(OLD2, NEW2, 1)

# 首字到达时记录
OLD3 = '''                        ai_response["text"] = text
                        now = time.time()'''
NEW3 = '''                        if not ai_response["text"] and text:
                            try:
                                print(f"[CHAT] 首字到达 {time.time() - _send_t0['t']:.1f}s")
                            except BaseException:
                                pass
                        ai_response["text"] = text
                        now = time.time()'''
assert OLD3 in t, "on_chunk 未匹配"
t = t.replace(OLD3, NEW3, 1)

# 计时起点：放在 _send_internal 开头
OLD4 = '''                def _send_internal(content, insert_user_bubble=True):
                    nonlocal generation_active, stop_flag'''
NEW4 = '''                def _send_internal(content, insert_user_bubble=True):
                    nonlocal generation_active, stop_flag
                    _send_t0 = {"t": time.time()}'''
assert OLD4 in t, "_send_internal 未匹配"
t = t.replace(OLD4, NEW4, 1)

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(t)
print("等待反馈已加入")

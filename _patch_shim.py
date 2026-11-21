# -*- coding: utf-8 -*-
"""全局兜底：所有 DeepSeek 非流式请求自动关思考并放宽 max_tokens；
   所有文件选择去掉类型过滤，规避 Android 静默失败。"""
import io

MAIN = r"C:\myapp\main.py"
t = io.open(MAIN, encoding="utf-8").read()

# ---------- 1) requests.post 补丁 ----------
SHIM = '''
def _install_deepseek_post_shim():
    """DeepSeek 默认开启思考，会把小 max_tokens 全吃掉导致 content 为空。
    这里统一兜底：非流式请求自动 reasoning_effort=none 且 max_tokens 至少 1200。
    覆盖识图、打标签、分析、计划等所有调用点，避免逐个漏改。"""
    if getattr(requests, "_chiyu_shim", False):
        return
    _orig_post = requests.post

    def _post(url, *args, **kwargs):
        payload = kwargs.get("json")
        if isinstance(payload, dict):
            model = str(payload.get("model") or "")
            if model.startswith("deepseek"):
                if "reasoning_effort" not in payload:
                    payload["reasoning_effort"] = "none"
                if not payload.get("stream"):
                    try:
                        payload["max_tokens"] = max(int(payload.get("max_tokens") or 0), 1200)
                    except BaseException:
                        payload["max_tokens"] = 1200
        return _orig_post(url, *args, **kwargs)

    requests.post = _post
    requests._chiyu_shim = True


'''
anchor = "def resolve_deepseek_model(cfg):"
assert anchor in t
if "_install_deepseek_post_shim" not in t:
    t = t.replace(anchor, SHIM.lstrip("\n") + anchor, 1)

# 启动时安装（main 函数开头）
OLD_MAIN = "def main(page: ft.Page):"
if "_install_deepseek_post_shim()" not in t:
    t = t.replace(OLD_MAIN, OLD_MAIN + "\n    _install_deepseek_post_shim()", 1)

# ---------- 2) 文件选择：去掉类型过滤 ----------
t = t.replace("""                _use_picker(page, on_chat_img_picked).pick_files(
                    file_type=ft.FilePickerFileType.IMAGE""",
              """                _use_picker(page, on_chat_img_picked).pick_files(""", 1)

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(t)
print("补丁已安装")

# -*- coding: utf-8 -*-
"""1) DeepSeek 模型名归一化为官方名 deepseek-chat / deepseek-reasoner
   2) 去掉官方 API 不认的 thinking / reasoning_effort 参数
   3) 文字任务全部走 DeepSeek；识图任务固定走智谱 GLM-4V
"""
import io

MAIN = r"C:\myapp\main.py"
t = io.open(MAIN, encoding="utf-8").read()

# ---------- 1) 模型名归一化 ----------
OLD = '''    _m = (cfg.get("deepseek_model") or "deepseek-flash").strip() or "deepseek-flash"
    if _m in ("", "deepseek-chat", "deepseek-reasoner", "deepseek-v4-flash", "deepseek-v4-flash-vision-exp"):
        return "deepseek-flash"
    return _m'''
NEW = '''    _m = (cfg.get("deepseek_model") or "deepseek-chat").strip()
    if _m in ("", "deepseek-flash", "deepseek-v4-flash", "deepseek-chat"):
        return "deepseek-chat"
    if _m in ("deepseek-v4-pro", "deepseek-pro", "deepseek-reasoner"):
        return "deepseek-reasoner"
    return _m'''
assert OLD in t, "模型归一化未匹配"
t = t.replace(OLD, NEW, 1)

# ---------- 2) 去掉不支持的参数 ----------
OLD2 = '''                if api_model.startswith("deepseek"):
                    _cfg = load_ai_config()
                    if _cfg.get("deepseek_thinking", True):
                        payload["thinking"] = {"type": "enabled"}
                        _eff = str(_cfg.get("deepseek_reasoning", "medium") or "medium").strip().lower()
                        if _eff not in ("low", "medium", "high", "max"):
                            _eff = "medium"
                        payload["reasoning_effort"] = _eff'''
NEW2 = '''                if api_model.startswith("deepseek"):
                    # 官方 API 只认 deepseek-chat / deepseek-reasoner，
                    # 不支持 thinking / reasoning_effort 这类私有参数，别再发。
                    payload.pop("thinking", None)
                    payload.pop("reasoning_effort", None)'''
assert OLD2 in t, "参数块未匹配"
t = t.replace(OLD2, NEW2, 1)

# ---------- 3) 识图固定走智谱 ----------
OLD3 = '''    key_enh = cfg.get("api_key_enhanced", "").strip()
    if key_enh:
        zi = PROVIDERS["zhipu"]
        return key_enh, zi["url"], "glm-4-air", zi.get("vision_model", "")'''
if OLD3 not in t:
    OLD3 = '''    key_enh = cfg.get("api_key_enhanced", "").strip()
    if key_enh:
        zi = PROVIDERS["zhipu"]
        return key_enh, zi["url"], "glm-4-air", zi.get("vision_model", "")'''

# 在 cheap 分支前加 vision 分支
OLD4 = '''    if task == "cheap":
        key = cfg.get(info["key_field"], "").strip()
        return key, info["url"], info["model"], info.get("vision_model", "")'''
NEW4 = '''    if task == "vision":
        # 图像识别只有智谱 GLM-4V 能做，DeepSeek 官方 API 不支持图片
        zi = PROVIDERS["zhipu"]
        for kf in ("api_key_free", "api_key_enhanced"):
            k = cfg.get(kf, "").strip()
            if k:
                return k, zi["url"], zi.get("vision_model", "glm-4v"), zi.get("vision_model", "")
        return "", zi["url"], "", ""
    if task == "cheap":
        _ds = cfg.get("api_key_deepseek", "").strip()
        if _ds:
            dk = PROVIDERS["deepseek"]
            return _ds, dk["url"], resolve_deepseek_model(cfg), ""
        key = cfg.get(info["key_field"], "").strip()
        return key, info["url"], info["model"], info.get("vision_model", "")'''
assert OLD4 in t, "cheap 分支未匹配"
t = t.replace(OLD4, NEW4, 1)

# 两处识图调用改用 vision 任务
t = t.replace('''                api_key, api_url, _m, vision_model = endpoint_for("cheap")
                if not api_key:
                    return None''',
              '''                api_key, api_url, _m, vision_model = endpoint_for("vision")
                if not api_key:
                    show_toast("识图需要智谱的免费 Key，请在设置里填上", "red")
                    return None''', 1)

t = t.replace('''                    api_key, api_url, _m, vision_model = endpoint_for("cheap")''',
              '''                    api_key, api_url, _m, vision_model = endpoint_for("vision")''', 1)

# ---------- 4) 识图能力判断：只要有智谱 key 就允许 ----------
OLD5 = '''    cfg = load_ai_config()
    provider = cfg.get("provider", "zhipu")
    return PROVIDERS.get(provider, PROVIDERS["zhipu"]).get("supports_vision", False)'''
NEW5 = '''    cfg = load_ai_config()
    provider = cfg.get("provider", "zhipu")
    p = PROVIDERS.get(provider, PROVIDERS["zhipu"])
    if p.get("supports_vision") and cfg.get(p.get("key_field", ""), "").strip() \\
            and provider != "deepseek":
        return True
    # DeepSeek 没有视觉能力，但只要智谱有 key，识图就能用
    return bool(cfg.get("api_key_free", "").strip() or cfg.get("api_key_enhanced", "").strip())'''
assert OLD5 in t, "vision 判断未匹配"
t = t.replace(OLD5, NEW5, 1)

# ---------- 5) DeepSeek 不再声称支持图片 ----------
t = t.replace('''        "vision_model": "deepseek-flash",
        "key_field": "api_key_deepseek",
        "supports_vision": True,''',
              '''        "vision_model": "",
        "key_field": "api_key_deepseek",
        "supports_vision": False,''', 1)

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(t)
print("模型名/参数/识图路由 已修正")

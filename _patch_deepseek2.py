# -*- coding: utf-8 -*-
"""回滚错误改动：恢复 deepseek-flash / deepseek-v4-pro（官方最新），
   reasoning_effort 合法（low/high/max），deepseek-flash 支持图片输入。"""
import io

MAIN = r"C:\myapp\main.py"
t = io.open(MAIN, encoding="utf-8").read()

# 1) 模型名恢复官方最新
OLD = '''    _m = (cfg.get("deepseek_model") or "deepseek-chat").strip()
    if _m in ("", "deepseek-flash", "deepseek-v4-flash", "deepseek-chat"):
        return "deepseek-chat"
    if _m in ("deepseek-v4-pro", "deepseek-pro", "deepseek-reasoner"):
        return "deepseek-reasoner"
    return _m'''
NEW = '''    _m = (cfg.get("deepseek_model") or "deepseek-flash").strip()
    # 官方 /models 只列 deepseek-flash 与 deepseek-v4-pro
    if _m in ("", "deepseek-flash", "deepseek-v4-flash", "deepseek-chat", "deepseek-reasoner"):
        return "deepseek-flash"
    if _m in ("deepseek-v4-pro", "deepseek-pro"):
        return "deepseek-v4-pro"
    return _m'''
assert OLD in t, "模型名块未匹配"
t = t.replace(OLD, NEW, 1)

# 2) reasoning_effort 恢复（官方支持 low/high/max，默认 high）
OLD2 = '''                if api_model.startswith("deepseek"):
                    # 官方 API 只认 deepseek-chat / deepseek-reasoner，
                    # 不支持 thinking / reasoning_effort 这类私有参数，别再发。
                    payload.pop("thinking", None)
                    payload.pop("reasoning_effort", None)'''
NEW2 = '''                if api_model.startswith("deepseek"):
                    # 官方支持 reasoning_effort: low / high / max（默认 high），
                    # 传 none 即关闭思考。不要发 thinking 字段（那是智谱的）。
                    payload.pop("thinking", None)
                    if _cfg_thinking_off():
                        payload["reasoning_effort"] = "none"
                    else:
                        _eff = str(load_ai_config().get("deepseek_reasoning", "high") or "high").lower()
                        payload["reasoning_effort"] = _eff if _eff in ("low", "high", "max") else "high"'''
assert OLD2 in t, "参数块未匹配"
t = t.replace(OLD2, NEW2, 1)

# 3) 辅助函数：思考开关
HELPER = '''def _cfg_thinking_off():
    try:
        return not bool(load_ai_config().get("deepseek_thinking", True))
    except BaseException:
        return False


'''
anchor = "def resolve_deepseek_model(cfg):"
if "_cfg_thinking_off" not in t:
    t = t.replace(anchor, HELPER + anchor, 1)

# 4) deepseek-flash 支持图片
t = t.replace('''        "vision_model": "",
        "key_field": "api_key_deepseek",
        "supports_vision": False,''',
              '''        "vision_model": "deepseek-flash",
        "key_field": "api_key_deepseek",
        "supports_vision": True,''', 1)

# 5) 识图：优先用所选 provider（DeepSeek 也能看图），没有再用智谱
OLD5 = '''    if task == "vision":
        # 图像识别只有智谱 GLM-4V 能做，DeepSeek 官方 API 不支持图片
        zi = PROVIDERS["zhipu"]
        for kf in ("api_key_free", "api_key_enhanced"):
            k = cfg.get(kf, "").strip()
            if k:
                return k, zi["url"], zi.get("vision_model", "glm-4v"), zi.get("vision_model", "")
        return "", zi["url"], "", ""'''
NEW5 = '''    if task == "vision":
        # 所选 provider 支持图片就优先用它（deepseek-flash 支持 image 输入）
        if info.get("supports_vision"):
            k = cfg.get(info["key_field"], "").strip()
            if k:
                vm = info.get("vision_model") or info["model"]
                if provider == "deepseek":
                    vm = resolve_deepseek_model(cfg)
                return k, info["url"], vm, vm
        zi = PROVIDERS["zhipu"]
        for kf in ("api_key_free", "api_key_enhanced"):
            k = cfg.get(kf, "").strip()
            if k:
                return k, zi["url"], zi.get("vision_model", "glm-4v"), zi.get("vision_model", "")
        return "", zi["url"], "", ""'''
assert OLD5 in t, "vision 分支未匹配"
t = t.replace(OLD5, NEW5, 1)

# 6) 识图能力判断恢复
OLD6 = '''    cfg = load_ai_config()
    provider = cfg.get("provider", "zhipu")
    p = PROVIDERS.get(provider, PROVIDERS["zhipu"])
    if p.get("supports_vision") and cfg.get(p.get("key_field", ""), "").strip() \\
            and provider != "deepseek":
        return True
    # DeepSeek 没有视觉能力，但只要智谱有 key，识图就能用
    return bool(cfg.get("api_key_free", "").strip() or cfg.get("api_key_enhanced", "").strip())'''
NEW6 = '''    cfg = load_ai_config()
    provider = cfg.get("provider", "zhipu")
    p = PROVIDERS.get(provider, PROVIDERS["zhipu"])
    if p.get("supports_vision") and cfg.get(p.get("key_field", ""), "").strip():
        return True
    # 回退：智谱有 key 也能识图
    return bool(cfg.get("api_key_free", "").strip() or cfg.get("api_key_enhanced", "").strip())'''
assert OLD6 in t, "vision 判断未匹配"
t = t.replace(OLD6, NEW6, 1)

# 7) 推理程度选项：官方只支持 low / high / max
t = t.replace('ft.dropdown.Option("low", "低（最快）"),\n                        ft.dropdown.Option("medium", "中（平衡）"),',
              'ft.dropdown.Option("low", "低（最快）"),')
t = t.replace('ft.dropdown.Option("high", "高（默认）"),\n                        ft.dropdown.Option("max", "最高（最慢最强）"),',
              'ft.dropdown.Option("high", "高（默认）"),\n                        ft.dropdown.Option("max", "最高（最慢最强）"),')

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(t)
print("已回滚到官方最新模型名并修正参数")

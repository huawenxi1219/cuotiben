# -*- coding: utf-8 -*-
"""1) 修复隐藏回退：选了 DeepSeek 就必须真用 DeepSeek
   2) 设置页简化：去掉"省心/深度"整行，只留 Provider + 模型 + 推理程度
"""
import io

MAIN = r"C:\myapp\main.py"
t = io.open(MAIN, encoding="utf-8").read()

# ---------- 1) endpoint_for 尊重选择 ----------
OLD = '''            key_enh = cfg.get("api_key_enhanced", "").strip()
            if key_enh:
                zi = PROVIDERS["zhipu"]
                return key_enh, zi["url"], "glm-4-air", zi.get("vision_model", "")'''
NEW = '''            # 先尊重用户在下拉里选的 provider；只有它没填 key 时才回退
            key_sel = cfg.get(info["key_field"], "").strip()
            if key_sel:
                if provider == "deepseek":
                    return key_sel, info["url"], resolve_deepseek_model(cfg), info.get("vision_model", "")
                return key_sel, info["url"], info["model"], info.get("vision_model", "")
            key_enh = cfg.get("api_key_enhanced", "").strip()
            if key_enh:
                zi = PROVIDERS["zhipu"]
                return key_enh, zi["url"], "glm-4-air", zi.get("vision_model", "")'''
assert OLD in t, "endpoint_for 回退段未匹配"
t = t.replace(OLD, NEW, 1)

# ---------- 2) 设置页简化 ----------
OLD2 = '''                mode_switch_row,
                provider_dropdown,'''
NEW2 = '''                provider_dropdown,'''
assert OLD2 in t
t = t.replace(OLD2, NEW2, 1)

OLD3 = '''                deepseek_thinking_switch,
                fast_mode_switch,'''
NEW3 = '''                fast_mode_switch,'''
assert OLD3 in t
t = t.replace(OLD3, NEW3, 1)

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(t)
print("endpoint 回退已修复；设置页已精简")

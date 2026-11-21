# -*- coding: utf-8 -*-
"""1) 省心/深度 一键切换  2) AI 消息加「换个讲法」"""
import io, re

MAIN = r"C:\myapp\main.py"
src = io.open(MAIN, encoding="utf-8").read()

# ---------- 1) 模式切换 ----------
m = re.search(r"^(\s*)provider_dropdown,\s*$", src, re.M)
assert m, "找不到 provider_dropdown 在设置列里的位置"
ind = m.group(1)

MODE_ROW = (
    f'{ind}# 一键切换：省心模式（智谱免费额度） ↔ 深度模式（DeepSeek V4.1 Pro + High）\n'
    f'{ind}def _set_ai_mode(mode):\n'
    f'{ind}    cfg = load_ai_config()\n'
    f'{ind}    if mode == "light":\n'
    f'{ind}        cfg["provider"] = "zhipu"\n'
    f'{ind}        cfg["deepseek_thinking"] = False\n'
    f'{ind}        show_toast("已切到省心模式：智谱免费模型（够用、不花钱）", "green")\n'
    f'{ind}    else:\n'
    f'{ind}        cfg["provider"] = "deepseek"\n'
    f'{ind}        cfg["deepseek_model"] = "deepseek-v4-pro"\n'
    f'{ind}        cfg["deepseek_reasoning"] = "high"\n'
    f'{ind}        cfg["deepseek_thinking"] = True\n'
    f'{ind}        show_toast("已切到深度模式：V4.1 Pro + High 推理", "green")\n'
    f'{ind}    save_ai_config(cfg)\n'
    f'{ind}    try:\n'
    f'{ind}        provider_dropdown.value = cfg.get("provider", "zhipu")\n'
    f'{ind}        deepseek_model_input.value = cfg.get("deepseek_model", "deepseek-flash")\n'
    f'{ind}        deepseek_reasoning_dropdown.value = cfg.get("deepseek_reasoning", "medium")\n'
    f'{ind}        deepseek_thinking_switch.value = bool(cfg.get("deepseek_thinking", True))\n'
    f'{ind}        page.update()\n'
    f'{ind}    except BaseException:\n'
    f'{ind}        pass\n'
    f'{ind}\n'
    f'{ind}mode_switch_row = ft.Row([\n'
    f'{ind}    ft.ElevatedButton("🪶 省心模式", icon=ft.Icons.ECO,\n'
    f'{ind}                      on_click=lambda e: _set_ai_mode("light")),\n'
    f'{ind}    ft.ElevatedButton("🚀 深度模式", icon=ft.Icons.ROCKET_LAUNCH,\n'
    f'{ind}                      on_click=lambda e: _set_ai_mode("deep")),\n'
    f'{ind}], spacing=8, wrap=True)\n'
)
src = src[:m.start()] + MODE_ROW + src[m.start():]

# 把 mode_switch_row 放进页面列（在 provider_dropdown 前面）
src = src.replace(f"{ind}provider_dropdown,\n", f"{ind}mode_switch_row,\n{ind}provider_dropdown,\n", 1)

# ---------- 2) 换个讲法 ----------
OLD = """                    collect_btn = ft.IconButton("""
NEW = """                    retry_btn = ft.IconButton(
                        icon=ft.Icons.SWAP_HORIZ, icon_size=16,
                        tooltip="换个讲法：让它用另一种方式重讲",
                        icon_color="#A9B1D6",
                        on_click=lambda e: handle_send(
                            "换个讲法：请用另一种思路把刚才那个问题重新讲一遍，"
                            "换一个更直观的切入角度（能举例就举例、能画图就画图），"
                            "不要重复上一条回答里的说法。"))

                    collect_btn = ft.IconButton("""
assert OLD in src
src = src.replace(OLD, NEW, 1)

src = src.replace("action_row = ft.Row([copy_btn, regen_btn, del_btn, add_btn, collect_btn],",
                  "action_row = ft.Row([copy_btn, retry_btn, regen_btn, del_btn, add_btn, collect_btn],", 1)

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(src)
print("模式切换 + 换个讲法 已加入")

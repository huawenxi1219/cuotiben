# -*- coding: utf-8 -*-
"""v2：省心/深度一键切换（放在 mine_page 之前）+ 换个讲法按钮。"""
import io, re

MAIN = r"C:\myapp\main.py"
src = io.open(MAIN, encoding="utf-8").read()

# ---------- 1) 定义切换函数 + 按钮行（放在 mine_page 之前） ----------
m = re.search(r"^(\s*)mine_page = ft\.Column\(\[", src, re.M)
assert m, "找不到 mine_page"
ind = m.group(1)

BLOCK = f'''{ind}# 一键切换：省心模式（智谱免费额度） ↔ 深度模式（DeepSeek V4.1 Pro + High）
{ind}def _set_ai_mode(mode):
{ind}    cfg = load_ai_config()
{ind}    if mode == "light":
{ind}        cfg["provider"] = "zhipu"
{ind}        cfg["deepseek_thinking"] = False
{ind}    else:
{ind}        cfg["provider"] = "deepseek"
{ind}        cfg["deepseek_model"] = "deepseek-v4-pro"
{ind}        cfg["deepseek_reasoning"] = "high"
{ind}        cfg["deepseek_thinking"] = True
{ind}    save_ai_config(cfg)
{ind}    try:
{ind}        provider_dropdown.value = cfg.get("provider", "zhipu")
{ind}        deepseek_model_input.value = cfg.get("deepseek_model", "deepseek-flash")
{ind}        deepseek_reasoning_dropdown.value = cfg.get("deepseek_reasoning", "medium")
{ind}        deepseek_thinking_switch.value = bool(cfg.get("deepseek_thinking", True))
{ind}        page.update()
{ind}    except BaseException:
{ind}        pass
{ind}    show_toast("已切到省心模式（智谱免费）" if mode == "light" else "已切到深度模式（V4.1 Pro · High）",
{ind}               "green")

{ind}mode_switch_row = ft.Row([
{ind}    ft.ElevatedButton("🪶 省心模式", icon=ft.Icons.ECO,
{ind}                      on_click=lambda e: _set_ai_mode("light")),
{ind}    ft.ElevatedButton("🚀 深度模式", icon=ft.Icons.ROCKET_LAUNCH,
{ind}                      on_click=lambda e: _set_ai_mode("deep")),
{ind}], spacing=8, wrap=True)

'''
src = src[:m.start()] + BLOCK + src[m.start():]

# 放进页面列（provider_dropdown 前）
m2 = re.search(r"^(\s*)provider_dropdown,\s*$", src, re.M)
assert m2, "找不到 provider_dropdown 列表项"
src = src[:m2.start()] + f"{m2.group(1)}mode_switch_row,\n" + src[m2.start():]

# ---------- 2) 换个讲法按钮 ----------
OLD = "                    collect_btn = ft.IconButton("
NEW = """                    retry_btn = ft.IconButton(
                        icon=ft.Icons.SWAP_HORIZ, icon_size=16,
                        tooltip="换个讲法：用另一种思路重讲",
                        icon_color="#A9B1D6",
                        on_click=lambda e: handle_send(
                            "换个讲法：请换一种思路把刚才的问题重新讲一遍，"
                            "换更直观的切入角度（能举例举例、能画图就画图），"
                            "不要重复上一条回答里的说法。"))

                    collect_btn = ft.IconButton("""
assert OLD in src
src = src.replace(OLD, NEW, 1)
src = src.replace("action_row = ft.Row([copy_btn, regen_btn, del_btn, add_btn, collect_btn],",
                  "action_row = ft.Row([copy_btn, retry_btn, regen_btn, del_btn, add_btn, collect_btn],", 1)

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(src)
print("已写入")

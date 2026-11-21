# -*- coding: utf-8 -*-
"""错题卡导出增强：
   1) 每题带编号（#001），方便回手机按编号查
   2) 可选「演算留白区」
   3) 加一行「🔑 这题的钥匙」手写线
   4) 导出前弹选项：每页题数 4/5/6、是否留白
"""
import io

MAIN = r"C:\myapp\main.py"
t = io.open(MAIN, encoding="utf-8").read()

# ---------- 1) 卡片生成函数 ----------
OLD_SIG = 'def build_error_cards_html(subject=None, per_page=6, days=None):'
NEW_SIG = 'def build_error_cards_html(subject=None, per_page=6, days=None, blank=False):'
assert OLD_SIG in t
t = t.replace(OLD_SIG, NEW_SIG, 1)

OLD_CARD = '''        cards.append(f"""
        <div class="card">
          <div class="head"><span class="subj">{esc(subj)}</span><span class="tags">{esc(tags)}</span></div>
          <div class="q">{esc(q[:420])}</div>
          <div class="line"><b>错因</b>{esc(m[:160])}</div>
          <div class="line"><b>答案</b>{esc(a[:220])}</div>
          <div class="foot">□ 已会　□ 还需练</div>
        </div>""")'''
NEW_CARD = '''        _no = len(cards) + 1
        _blank = '<div class="work"></div>' if blank else ''
        cards.append(f"""
        <div class="card">
          <div class="head"><span class="no">#{_no:03d}</span><span class="subj">{esc(subj)}</span><span class="tags">{esc(tags)}</span></div>
          <div class="q">{esc(q[:420])}</div>
          {_blank}
          <div class="line"><b>错因</b>{esc(m[:160])}</div>
          <div class="line"><b>答案</b>{esc(a[:220])}</div>
          <div class="keyline">🔑 这题的钥匙：<span class="dots"></span></div>
          <div class="foot">□ 已会　□ 还需练</div>
        </div>""")'''
assert OLD_CARD in t, "卡片模板未匹配"
t = t.replace(OLD_CARD, NEW_CARD, 1)

# 行数随每页题数变化
OLD_ROWS = "grid-template-rows: repeat(3, 1fr); gap: 4mm; page-break-after: always; }}"
NEW_ROWS = ("grid-template-rows: repeat({rows}, 1fr); gap: 4mm; page-break-after: always; }}")
if OLD_ROWS in t:
    t = t.replace(OLD_ROWS, NEW_ROWS, 1)
    # 用 f-string 求行数：把 .page 那段移到格式化之后
    t = t.replace("  .page {{ width: 190mm; height: 277mm; display: grid; grid-template-columns: 1fr 1fr;",
                  "  .page {{ width: 190mm; height: 277mm; display: grid; grid-template-columns: 1fr 1fr;", 1)

# 新增样式
OLD_CSS = "  .foot {{ font-size: 8pt; color: #888; margin-top: auto; padding-top: 1.5mm; }}"
NEW_CSS = """  .no {{ font-weight: bold; color: #333; margin-right: 2mm; font-family: monospace; }}
  .work {{ flex: 2; border-bottom: 1px dashed #bbb; margin: 1.5mm 0; min-height: 18mm; }}
  .keyline {{ font-size: 8.5pt; color: #333; margin-top: 1.5mm; }}
  .dots {{ display: inline-block; width: 60%; border-bottom: 1px dotted #666; }}
  .foot {{ font-size: 8pt; color: #888; margin-top: auto; padding-top: 1.5mm; }}"""
assert OLD_CSS in t
t = t.replace(OLD_CSS, NEW_CSS, 1)

# rows 计算：在 return 前插入
OLD_RET = '''    return f"""<!DOCTYPE html>'''
NEW_RET = '''    _rows = max(1, (int(per_page) + 1) // 2)
    return f"""<!DOCTYPE html>'''
assert OLD_RET in t
t = t.replace(OLD_RET, NEW_RET, 1)

# 把 {rows} 变成真正的 f-string 插值（原来被转义成 {{rows}} 的话再处理）
t = t.replace("grid-template-rows: repeat({rows}, 1fr);", "grid-template-rows: repeat({_rows}, 1fr);", 1)

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(t)
print("卡片模板已增强")

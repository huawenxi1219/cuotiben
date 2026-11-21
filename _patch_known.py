# -*- coding: utf-8 -*-
"""修正「已认识」的判定：以最近一次作答为准，认识即计入，不会即剔除。"""
import io, os

ROOT = r"C:\Users\黄\Doubao\chats\2026-10-17\new-chat-1\band-word-app\vela-app"

# 1) srs.answer 记录最近一次动作
sp = os.path.join(ROOT, "src", "common", "srs.js")
s = io.open(sp, encoding="utf-8").read()
s = s.replace("return { p: p, t: t, c: c, wc: wc, last: now }",
              "return { p: p, t: t, c: c, wc: wc, last: now, a: action }")
io.open(sp, "w", encoding="utf-8", newline="\n").write(s)
print("srs.answer 现在会记录最近动作")

# 2) 统计规则
ux = os.path.join(ROOT, "src", "pages", "index", "index.ux")
t = io.open(ux, encoding="utf-8").read()

OLD = """			var known = 0, wk = 0, pk = 0
			for (var k in map) {
				var e = map[k]
				if (!e || typeof e.p !== 'number') continue
				if (e.p < KNOWN_P) continue
				known++
				if (e.ph) pk++
				else wk++
			}"""
NEW = """			var known = 0, wk = 0, pk = 0
			for (var k in map) {
				var e = map[k]
				if (!e || typeof e.p !== 'number') continue
				// 认不认识，看两件事：最近一次点的是"认识"，或熟练度已经足够高
				var ok = (e.a === 'know' && e.p >= 15) || e.p >= KNOWN_P
				if (!ok) continue
				known++
				if (e.ph) pk++
				else wk++
			}"""
if OLD not in t:
    raise SystemExit("!! 未匹配统计段落")
t = t.replace(OLD, NEW)
t = t.replace("const KNOWN_P = 60        // 熟练度 ≥ 60 算「认识」（大约连续答对 3 次）",
              "const KNOWN_P = 40        // 熟练度 ≥ 40 也算「认识」（多次答对后即使最近点了模糊也保留）")
io.open(ux, "w", encoding="utf-8", newline="\n").write(t)
print("统计规则已更新")

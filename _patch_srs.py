# -*- coding: utf-8 -*-
"""修正 srs.answer：不认识 → 10 分钟后再问；模糊 → 2 小时后再问；认识才走遗忘曲线。"""
import io, os

ROOT = r"C:\Users\黄\Doubao\chats\2026-10-17\new-chat-1\band-word-app\vela-app"
P = os.path.join(ROOT, "src", "common", "srs.js")

NEW_ANSWER = r'''// 回答一次 → 新的词条状态 {p, t, c, wc, last}
// 规则（按用户实际用法定）：
//   认识 → 熟练度涨，下次按遗忘曲线（几小时后 ~ 几十天后）
//   模糊 → 熟练度略降，2 小时后再问一次
//   不会 → 熟练度腰斩，10 分钟后再问一次（就是"多问几遍"）
function answer(entry, action, rt, dwell) {
	var e = entry || {}
	var p = (typeof e.p === 'number') ? e.p : 0
	var c = e.c || 0
	var wc = e.wc || 0
	var f = rtFactor(rt) * dwellFactor(dwell)
	var now = Date.now()
	var t
	if (action === 'know') {
		p = clamp(p + 18 * f, 0, 100)
		c++
		t = alignDaytime(now + gapDays(p) * DAY)
	} else if (action === 'fuzzy') {
		p = clamp(p * 0.9 - 2, 0, 100)
		t = now + 2 * HOUR
	} else {
		p = clamp(p * 0.5, 0, 100)
		wc++
		t = now + 10 * 60 * 1000
	}
	return { p: p, t: t, c: c, wc: wc, last: now }
}
'''

txt = io.open(P, encoding="utf-8").read()
a = txt.index("// 回答一次 → 新的词条状态")
b = txt.index("export default {")
txt = txt[:a] + NEW_ANSWER + "\n" + txt[b:]
io.open(P, "w", encoding="utf-8", newline="\n").write(txt)
print("srs.js answer() 已更新")

# -*- coding: utf-8 -*-
"""修手表背单词：背过的词不该第二天又全冒出来。

问题：点「认识」只加 18 点熟练度 → 间隔约 3~4 小时 → 第二天全部到期，新词推不动。
改法：
1. 「认识」按连对次数给最短间隔：1次=1天，2次=2天，3次=4天，4次=8天，5次=15天，6次=30天
2. 连对 3 次以上直接判为已掌握（p 拉满），基本不再出现
3. 模糊 = 4 小时后重问；不会 = 20 分钟后重问
"""
import io

P = r"C:\Users\黄\Doubao\chats\2026-10-17\new-chat-1\band-word-app\vela-app\src\common\srs.js"
t = io.open(P, encoding="utf-8").read()

OLD_GAP = '''function gapDays(p) {
	return clamp(0.02 * Math.pow(2.4, clamp(p, 0, 100) / 10), 0.02, 60)
}'''
NEW_GAP = '''function gapDays(p) {
	return clamp(0.02 * Math.pow(2.4, clamp(p, 0, 100) / 10), 0.02, 60)
}

// 连对 n 次对应的「最短间隔（天）」：保证背过的词不会当天/次日反复出现
var MIN_GAP = { 1: 1, 2: 2, 3: 4, 4: 8, 5: 15, 6: 30 }

function minGapDays(c) {
	var n = Math.min(c || 0, 6)
	return MIN_GAP[n] || 0.02
}'''
assert OLD_GAP in t
t = t.replace(OLD_GAP, NEW_GAP, 1)

OLD_ANS = '''	if (action === 'know') {
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
	}'''
NEW_ANS = '''	if (action === 'know') {
		c++
		if (c >= 3) {
			// 连对 3 次：判为已掌握，间隔 30 天以上
			p = 100
			t = alignDaytime(now + 30 * DAY)
		} else {
			p = clamp(p + 25 * f, 0, 100)
			var gap = Math.max(gapDays(p), minGapDays(c))
			t = alignDaytime(now + gap * DAY)
		}
	} else if (action === 'fuzzy') {
		p = clamp(p * 0.9 - 2, 0, 100)
		c = 0
		t = now + 4 * HOUR
	} else {
		p = clamp(p * 0.5, 0, 100)
		c = 0
		wc++
		t = now + 20 * 60 * 1000
	}'''
assert OLD_ANS in t
t = t.replace(OLD_ANS, NEW_ANS, 1)

# 导出 minGapDays（便于调试/统计）
t = t.replace("	urgency: urgency,", "	urgency: urgency,\n	minGapDays: minGapDays,")

io.open(P, "w", encoding="utf-8", newline="\n").write(t)
print("SRS 间隔已修")

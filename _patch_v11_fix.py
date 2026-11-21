# -*- coding: utf-8 -*-
"""修复 v1.1 的写盘竞态：nextWord 必须等 saveAll 完成后再取下一个词。"""
import io, os

ROOT = r"C:\Users\黄\Doubao\chats\2026-10-17\new-chat-1\band-word-app\vela-app"
UX = os.path.join(ROOT, "src", "pages", "index", "index.ux")

OLD = """		// 一次读 + 一次写：更新熟练度 + 追加记录
		storage.getAll().then(function (db) {
			db = db || {}
			var map = db.map || {}
			var ne = srs.answer(map[cw.i] || {}, act, rt, dwell)
			ne.ph = cw.ph
			map[cw.i] = ne
			db.map = map
			var recs = db.records || []
			recs.push({
				word: cw.w,
				action: act,
				t: timeStr(Date.now()),
				rt: rt,
				d: dwell,
				p: ne.p
			})
			if (recs.length > REC_KEEP) recs = recs.slice(recs.length - REC_KEEP)
			db.records = recs
			storage.saveAll(db).then(function () { that.refreshStats() })
		})

		this.pickNext()"""

NEW = """		// 一次读 + 一次写；必须等保存完成再取下一个词，否则两个"读-改-写"会互相覆盖
		storage.getAll().then(function (db) {
			db = db || {}
			var map = db.map || {}
			var ne = srs.answer(map[cw.i] || {}, act, rt, dwell)
			ne.ph = cw.ph
			map[cw.i] = ne
			db.map = map
			var recs = db.records || []
			recs.push({
				word: cw.w,
				action: act,
				t: timeStr(Date.now()),
				rt: rt,
				d: dwell,
				p: ne.p
			})
			if (recs.length > REC_KEEP) recs = recs.slice(recs.length - REC_KEEP)
			db.records = recs
			return storage.saveAll(db)
		}).then(function () {
			that.refreshStats()
			that.pickNext()
		})"""

txt = io.open(UX, encoding="utf-8").read()
if OLD not in txt:
    raise SystemExit("!! 未匹配到 nextWord 段落")
txt = txt.replace(OLD, NEW)
io.open(UX, "w", encoding="utf-8", newline="\n").write(txt)
print("nextWord 已改为串行写盘")

# pickNext 里新词计数那次 saveAll 也改成链式，避免同样问题
OLD2 = """			db.lastNewDay = day
			db.newLearned = newCnt + 1
			storage.saveAll(db)
			that.showWord(idx)"""
NEW2 = """			db.lastNewDay = day
			db.newLearned = newCnt + 1
			storage.saveAll(db).then(function () { that.showWord(idx) })"""
txt = io.open(UX, encoding="utf-8").read()
if OLD2 in txt:
    txt = txt.replace(OLD2, NEW2)
    io.open(UX, "w", encoding="utf-8", newline="\n").write(txt)
    print("pickNext 新词计数改为链式")
else:
    print("(pickNext 无需修改)")

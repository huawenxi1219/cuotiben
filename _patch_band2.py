# -*- coding: utf-8 -*-
"""第二轮小改：把每答一词的 4 次整文件读写，合并成 1 次。"""
import io, os, re

ROOT = r"C:\Users\黄\Doubao\chats\2026-10-17\new-chat-1\band-word-app\vela-app"
UX = os.path.join(ROOT, "src", "pages", "index", "index.ux")

OLD = """		// 落盘：熟练度 + 学习记录（供手机周同步）
		storage.get('map', {}).then(function (map) {
			map = map || {}
			var old = map[cw.i] || {}
			var ne = srs.answer(old, act, that._pendingRt, dwell)
			map[cw.i] = ne
			storage.set('map', map)
			storage.get('records', []).then(function (recs) {
				recs = recs || []
				recs.push({
					w: cw.w,
					a: act,
					rt: that._pendingRt,
					d: dwell,
					t: timeStr(Date.now()),
					p: ne.p
				})
				if (recs.length > REC_KEEP) recs = recs.slice(recs.length - REC_KEEP)
				storage.set('records', recs)
			})
		})"""

NEW = """		// 落盘：一次读 + 一次写，避免多次整文件读写拖慢手环
		var _rt = this._pendingRt
		storage.getAll().then(function (db) {
			db = db || {}
			var map = db.map || {}
			var ne = srs.answer(map[cw.i] || {}, act, _rt, dwell)
			map[cw.i] = ne
			db.map = map
			var recs = db.records || []
			recs.push({
				w: cw.w,
				a: act,
				rt: _rt,
				d: dwell,
				t: timeStr(Date.now()),
				p: ne.p
			})
			if (recs.length > REC_KEEP) recs = recs.slice(recs.length - REC_KEEP)
			db.records = recs
			storage.saveAll(db)
		})"""

txt = io.open(UX, encoding="utf-8").read()
if OLD not in txt:
    raise SystemExit("!! 没有匹配到要替换的段落，未做修改")
txt = txt.replace(OLD, NEW)
io.open(UX, "w", encoding="utf-8", newline="\n").write(txt)
print("patched nextWord -> 1 read + 1 write")

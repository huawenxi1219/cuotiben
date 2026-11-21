# -*- coding: utf-8 -*-
"""手环端：取消每日 30 词上限；加内存缓存，答题不再每点一次整库读写。"""
import io, os

UX = r"C:\Users\黄\Doubao\chats\2026-10-17\new-chat-1\band-word-app\vela-app\src\pages\index\index.ux"
t = io.open(UX, encoding="utf-8").read()

# 1) 上限取消（保留字段，方便以后想恢复时改回数字）
t = t.replace("const DAILY_NEW = 30      // 每天最多引入多少个新词",
              "const DAILY_NEW = 100000  // 新词上限（改为不限；想恢复限制就改回 30）")

# 2) 内存缓存：一次读入，平时只改内存，每 6 次答题或退出时落盘
HELPER = '''
// ===== 存储缓存：整个 db 只读入一次，答题时只改内存，攒几次再写盘 =====
var _db = null
var _pend = 0

function loadDb() {
	if (_db) return Promise.resolve(_db)
	return storage.getAll().then(function (d) {
		_db = d || {}
		return _db
	})
}

function persist(force) {
	if (!_db) return Promise.resolve()
	_pend++
	if (!force && _pend < 6) return Promise.resolve()
	_pend = 0
	try {
		return storage.saveAll(_db)
	} catch (e) {
		return Promise.resolve()
	}
}

'''
anchor = "const DAILY_NEW = 100000"
i = t.index(anchor)
j = t.index("\n\n", t.index("const REC_KEEP", i)) + 2
t = t[:j] + HELPER + t[j:]

# 3) 统计改用缓存 + 核心标记按 CORE 位判断
t = t.replace("""		storage.get('map', {}).then(function (map) {
			map = map || {}""",
              """		loadDb().then(function (_d) {
			var map = (_d && _d.map) || {}""", 1)
t = t.replace("""				if (e.core) ck++
				else ek++""",
              """				if (CORE.charCodeAt(parseInt(k, 10)) === 49) ck++
				else ek++""", 1)

# 4) 选词读缓存
t = t.replace("""		this.debug = ''
		storage.getAll().then(function (db) {""",
              """		this.debug = ''
		loadDb().then(function (db) {""", 1)

# 5) 新词计数：写缓存，不阻塞
t = t.replace("""			db.lastNewDay = day
			db.newLearned = newCnt + 1
			storage.saveAll(db).then(function () { that.showWord(idx) })""",
              """			db.lastNewDay = day
			db.newLearned = newCnt + 1
			persist()
			that.showWord(idx)""", 1)

# 6) 答题：只改内存，攒批落盘
t = t.replace("""		// 一次读 + 一次写；必须等保存完成再取下一个词，否则两个"读-改-写"会互相覆盖
		storage.getAll().then(function (db) {""",
              """		// 只改内存缓存，不等写盘；每 6 题或退出时统一落盘
		loadDb().then(function (db) {""", 1)
t = t.replace("""			ne.core = cw.core ? 1 : 0
""", "")
t = t.replace("""			db.records = recs
			return storage.saveAll(db)
		}).then(function () {""",
              """			db.records = recs
			persist()
			return null
		}).then(function () {""", 1)

# 7) 退出/隐藏时强制落盘
t = t.replace("""	onHide() {
	},""",
              """	onHide() {
		persist(true)
	},""", 1)
t = t.replace("""	exitApp() {
		try { brightness.setKeepScreenOn({ keepScreenOn: false }) } catch (e) { }""",
              """	exitApp() {
		persist(true)
		try { brightness.setKeepScreenOn({ keepScreenOn: false }) } catch (e) { }""", 1)

io.open(UX, "w", encoding="utf-8", newline="\n").write(t)
print("手环端已优化")

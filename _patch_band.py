# -*- coding: utf-8 -*-
"""一次性改造脚本：把 vela-app 改成「内置词库 + 熟练度推送」的轻量版。
只改这四处：
1) src/common/srs.js         —— 换成按熟练度算间隔的算法
2) src/pages/index/index.ux  —— 换掉 <script> 段（词库按索引按需解析）
3) src/common/logo.png       —— 448x448/142KB 压到 192x192
4) src/manifest.json         —— 名称/版本/平台版本
"""
import io, os, re, json, struct

ROOT = r"C:\Users\黄\Doubao\chats\2026-10-17\new-chat-1\band-word-app\vela-app"
SRC = os.path.join(ROOT, "src")


def w(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print("written:", path, len(text), "chars")


SRS = r'''// 池鱼单词 · 熟练度算法（手环端）
// 每个词只存一个「综合熟练度 p(0-100)」和「下次该问的时间 t」。
// p 由三件事共同决定：看到单词的反应时间、看释义的停留时长、以及这次学习发生的时刻；
// 下次推送时间由 p 反推间隔，再对齐到白天。

const DAY = 86400000
const HOUR = 3600000

function clamp(v, a, b) { return v < a ? a : (v > b ? b : v) }

// 反应时间系数：越快点掉，说明越熟
function rtFactor(rt) {
	if (!rt || rt <= 0) return 1
	if (rt <= 1200) return 1.25
	if (rt <= 3000) return 1.0
	if (rt <= 6000) return 0.85
	return 0.7
}

// 释义停留系数：停得久说明在认真看
function dwellFactor(d) {
	if (!d || d <= 0) return 1
	if (d >= 4000) return 1.2
	if (d >= 1500) return 1.0
	return 0.8
}

// 一次回答对熟练度的增量
function delta(action, rt, dwell) {
	var base = action === 'know' ? 18 : (action === 'fuzzy' ? -3 : -12)
	return base * rtFactor(rt) * dwellFactor(dwell)
}

// 熟练度 → 下次间隔（天）：p=0 约半小时，p=50 约 1.6 天，p=80 约 29 天
function gapDays(p) {
	return clamp(0.02 * Math.pow(2.4, clamp(p, 0, 100) / 10), 0.02, 60)
}

// 对齐到白天，避免凌晨叫人背单词
function alignDaytime(ts) {
	var d = new Date(ts)
	var h = d.getHours()
	if (h < 7) return ts + (7 - h) * HOUR
	if (h >= 23) return ts + (24 - h + 7) * HOUR
	return ts
}

// 紧急度：熟练度越低、过期越久、错得越多，越该被问到
function urgency(e) {
	var p = (e && typeof e.p === 'number') ? e.p : 0
	var t = (e && typeof e.t === 'number') ? e.t : 0
	var over = t ? Math.max(0, (Date.now() - t) / DAY) : 0
	var wc = (e && e.wc) ? e.wc : 0
	return (100 - p) * 0.6 + Math.min(over, 30) * 8 + Math.min(wc, 5) * 2 + Math.random() * 8
}

// 回答一次 → 新的词条状态 {p, t, c, wc, last}
function answer(entry, action, rt, dwell) {
	var e = entry || {}
	var p = (typeof e.p === 'number') ? e.p : 0
	var c = e.c || 0
	var wc = e.wc || 0
	p = clamp(p + delta(action, rt, dwell), 0, 100)
	if (action === 'know') c++
	else if (action === 'forget') wc++
	var now = Date.now()
	return { p: p, t: alignDaytime(now + gapDays(p) * DAY), c: c, wc: wc, last: now }
}

export default {
	rtFactor: rtFactor,
	dwellFactor: dwellFactor,
	gapDays: gapDays,
	urgency: urgency,
	answer: answer
}
'''


SCRIPT = r'''
<script>
import storage from '../../common/storage.js'
import srs from '../../common/srs.js'
import DICT from '../../common/dict.js'
import brightness from '@system.brightness'
import app from '@system.app'
import router from '@system.router'

// ===== 词库：4678 词内置，但不拆成对象数组 =====
// 只记录每行的起始偏移（4678 个整数），用到哪个词才截取哪一行。
// 这是为了避开「一次性生成 4678 个对象 → 手环内存爆掉重启」。
var _off = null

function offsets() {
	if (_off) return _off
	var a = [0], s = DICT, n = s.length
	for (var i = 0; i < n; i++) {
		if (s.charCodeAt(i) === 10) a.push(i + 1)
	}
	_off = a
	return a
}

function dictCount() {
	return offsets().length
}

function dictWord(i) {
	var o = offsets()
	if (i < 0 || i >= o.length) return null
	var end = (i + 1 < o.length) ? o[i + 1] - 1 : DICT.length
	var line = DICT.substring(o[i], end)
	var t = line.indexOf('\t')
	if (t < 0) return { i: i, w: line, m: '' }
	return { i: i, w: line.substring(0, t), m: line.substring(t + 1) }
}

function pad2(n) { return (n < 10 ? '0' : '') + n }

function todayStr() {
	var d = new Date()
	return d.getFullYear() + '-' + pad2(d.getMonth() + 1) + '-' + pad2(d.getDate())
}

function timeStr(ts) {
	var d = new Date(ts)
	return d.getFullYear() + '-' + pad2(d.getMonth() + 1) + '-' + pad2(d.getDate()) +
		' ' + pad2(d.getHours()) + ':' + pad2(d.getMinutes()) + ':' + pad2(d.getSeconds())
}

const BATCH_SIZE = 30    // 每批 30 个词，控制内存
const DAILY_NEW = 25     // 每天最多引入的新词
const REC_KEEP = 800     // 本地最多保留多少条学习记录（供手机周同步）

export default {
	private: {
		mode: 'home',          // home | study | meaning | done
		words: [],             // 当前批次的词（≤30 个对象）
		roundNo: 0,
		batchSize: 0,
		idx: 0,
		curWord: { w: '', m: '' },
		totalCount: 0,
		statK: 0,
		statF: 0,
		statN: 0,
		lastActText: '',
		studyStart: 0,
		meaningStart: 0,
		animClass: 'animIn',
		roundDone: 0,
		progPct: 0,
		retryCount: 0,
		retryQueue: [],
		sinceRetry: 0,
		debug: ''
	},

	touch: { sx: 0, sy: 0, active: false },

	// 本轮临时状态（不放进 viewModel，减少数据代理开销）
	_pending: null,
	_pendingAct: '',
	_pendingRt: 0,
	_answered: null,

	onShow() {
		this.totalCount = dictCount()
		this._answered = {}
		this.retryQueue = []
		this.sinceRetry = 0
		try { globalThis.conn && globalThis.conn.send('__hs__', { count: 1 }) } catch (e) { }
	},

	startRound() {
		this.statK = 0
		this.statF = 0
		this.statN = 0
		this.retryCount = 0
		this.roundNo = 0
		this.debug = ''
		this._answered = {}
		this.loadNextBatch()
	},

	// 选一批词：先取「到期该复习的」，不够再用随机新词补齐
	loadNextBatch() {
		var that = this
		this.debug = '准备单词...'
		storage.get('map', {}).then(function (map) {
			map = map || {}
			storage.get('lastNewDay', '').then(function (day) {
				storage.get('newLearned', 0).then(function (newCnt) {
					var today = todayStr()
					if (day !== today) newCnt = 0
					var now = Date.now()
					var total = dictCount()

					// 1) 到期词：只遍历「学过的词」，绝不扫全库
					var due = []
					for (var k in map) {
						var e = map[k]
						if (!e) continue
						if (e.t && e.t > now) continue
						due.push({ i: parseInt(k, 10), u: srs.urgency(e) })
					}
					due.sort(function (a, b) { return b.u - a.u })

					var picked = []
					var taken = {}
					var n = Math.min(BATCH_SIZE, due.length)
					for (var j = 0; j < n; j++) {
						picked.push(due[j].i)
						taken[due[j].i] = true
					}
					due = null

					// 2) 新词：随机抽，每天有配额
					var room = Math.min(DAILY_NEW - newCnt, BATCH_SIZE - picked.length)
					var guard = 0
					while (room > 0 && guard < 3000) {
						guard++
						var idx = Math.floor(Math.random() * total)
						if (map[idx] || taken[idx]) continue
						taken[idx] = true
						picked.push(idx)
						room--
						newCnt++
					}
					taken = null

					if (!picked.length) {
						that.mode = 'done'
						that.words = []
						that.debug = ''
						try { brightness.setKeepScreenOn({ keepScreenOn: false }) } catch (e) { }
						return
					}

					storage.set('lastNewDay', today)
					storage.set('newLearned', newCnt)

					// 3) 只把这 30 个词真正解析成对象
					var batch = []
					for (var m = 0; m < picked.length; m++) {
						var wd = dictWord(picked[m])
						if (wd) batch.push(wd)
					}
					// 轻量打乱，避免总是同一顺序
					for (var q = batch.length - 1; q > 0; q--) {
						var r = Math.floor(Math.random() * (q + 1))
						var tmp = batch[q]; batch[q] = batch[r]; batch[r] = tmp
					}

					that.words = batch
					that.batchSize = batch.length
					that.roundNo++
					that.idx = 0
					that._answered = {}
					that.retryQueue = []
					that.sinceRetry = 0
					that.roundDone = 0
					that.progPct = 0
					that.animClass = 'animIn'
					that.curWord = batch[0]
					that.studyStart = Date.now()
					that.mode = 'study'
					that.debug = ''
					try { brightness.setKeepScreenOn({ keepScreenOn: true }) } catch (e) { }
				})
			})
		})
	},

	chooseBtn(action) {
		this.choose(action, Date.now() - this.studyStart)
	},

	choose(action, rt) {
		// 同步执行，不做异步等待，避免手环卡死
		this._pendingAct = action
		this._pendingRt = rt
		if (action === 'know') this.statK++
		else if (action === 'fuzzy') this.statF++
		else this.statN++
		this.lastActText = action === 'know' ? '认识 ✓' : (action === 'fuzzy' ? '模糊 ~' : '不会 ✗')
		this.roundDone++
		this.progPct = Math.min(100, Math.round(this.roundDone / this.batchSize * 100))
		// 不会/模糊的词，两个之后插回来再考一次
		if (action !== 'know') {
			var key = this.curWord.i
			var inQ = false
			for (var q = 0; q < this.retryQueue.length; q++) {
				if (this.retryQueue[q].i === key) { inQ = true; break }
			}
			if (!inQ) this.retryQueue.push({ i: key, word: this.curWord })
		}
		this.mode = 'meaning'
		this.meaningStart = Date.now()
	},

	nextWord() {
		var that = this
		var cw = this.curWord
		var dwell = Date.now() - this.meaningStart
		var act = this._pendingAct

		// 落盘：熟练度 + 学习记录（供手机周同步）
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
		})

		this._answered[cw.i] = true
		this._pendingAct = ''
		this._pendingRt = 0

		// 轮内复考
		this.sinceRetry++
		if (this.retryQueue.length && this.sinceRetry >= 2) {
			var rw = this.retryQueue.shift()
			this.sinceRetry = 0
			this.retryCount++
			this.curWord = rw.word
			this.studyStart = Date.now()
			this.mode = 'study'
			this.animClass = 'animIn'
			return
		}

		this.idx++
		if (this.idx < this.words.length) {
			this.curWord = this.words[this.idx]
			this.studyStart = Date.now()
			this.mode = 'study'
			this.animClass = 'animIn'
		} else {
			this.batchDone()
		}
	},

	batchDone() {
		// 释放本批对象，继续下一批（今天还有该复习的就接着来）
		this.words = []
		this._answered = {}
		try { global.runGC && global.runGC() } catch (e) { }
		this.loadNextBatch()
	},

	onTouchStart(e) {
		var t = e.touches[0]
		this.touch.sx = t.clientX
		this.touch.sy = t.clientY
		this.touch.active = true
	},

	onTouchMove() { },

	onTouchEnd(e) {
		if (!this.touch.active) return
		this.touch.active = false
		var t = (e && e.changedTouches && e.changedTouches[0]) ? e.changedTouches[0]
			: ((e && e.touches && e.touches[0]) || null)
		if (!t || typeof t.clientX !== 'number') return
		var dx = t.clientX - this.touch.sx
		var dy = t.clientY - this.touch.sy
		var ax = Math.abs(dx), ay = Math.abs(dy)
		var isTap = ax < 20 && ay < 20
		// 右滑退出
		if (ax >= ay && dx > 0) { this.exitApp(); return }
		if (this.mode === 'meaning' && isTap) { this.nextWord(); return }
		if (isTap) return
		if (this.mode !== 'study') return
		var action = null
		if (ay > ax && dy < 0) action = 'fuzzy'
		else if (ay > ax && dy > 0) action = 'forget'
		else if (ax >= ay && dx < 0) action = 'know'
		if (action) this.choose(action, Date.now() - this.studyStart)
	},

	exitApp() {
		try { brightness.setKeepScreenOn({ keepScreenOn: false }) } catch (e) { }
		try { app.terminate() } catch (e) { }
		setTimeout(function () {
			try { router.clear() } catch (e) { }
		}, 300)
	},

	onBackPress() {
		if (this.mode === 'study' || this.mode === 'meaning') {
			this.mode = 'home'
			try { brightness.setKeepScreenOn({ keepScreenOn: false }) } catch (e) { }
		} else {
			this.exitApp()
		}
		return true
	}
}
</script>
'''


def patch_index_ux():
    p = os.path.join(SRC, "pages", "index", "index.ux")
    txt = io.open(p, encoding="utf-8").read()
    a = txt.index("<script>")
    b = txt.index("</script>") + len("</script>")
    new = txt[:a] + SCRIPT.strip() + txt[b:]
    new = new.replace("<text class=\"ver\">v0.26</text>", "<text class=\"ver\">v1.0</text>")
    new = new.replace("内置词库 {{totalCount}} 词 · 标准版", "内置 {{totalCount}} 词 · 高考3500")
    io.open(p, "w", encoding="utf-8", newline="\n").write(new)
    print("patched:", p, "->", len(new), "chars")


def patch_manifest():
    p = os.path.join(SRC, "manifest.json")
    txt = io.open(p, encoding="utf-8").read()
    txt = re.sub(r'"name":\s*"[^"]*"', '"name": "池鱼单词"', txt, count=1)
    txt = re.sub(r'"versionName":\s*"[^"]*"', '"versionName": "1.0.0"', txt, count=1)
    txt = re.sub(r'"versionCode":\s*\d+', '"versionCode": 100', txt, count=1)
    txt = re.sub(r'"minPlatformVersion":\s*\d+', '"minPlatformVersion": 1000', txt, count=1)
    txt = re.sub(r'"designWidth":\s*[^,\n]+', '"designWidth": 212', txt, count=1)
    io.open(p, "w", encoding="utf-8", newline="\n").write(txt)
    print("patched:", p)
    print(txt)


def shrink_logo():
    p = os.path.join(SRC, "common", "logo.png")
    try:
        from PIL import Image
    except ImportError:
        print("!! PIL 不可用，跳过图标压缩")
        return
    im = Image.open(p).convert("RGBA")
    im = im.resize((192, 192), Image.LANCZOS)
    im.save(p, "PNG", optimize=True)
    print("logo:", os.path.getsize(p), "bytes")


if __name__ == "__main__":
    w(os.path.join(SRC, "common", "srs.js"), SRS)
    patch_index_ux()
    patch_manifest()
    shrink_logo()
    print("DONE")

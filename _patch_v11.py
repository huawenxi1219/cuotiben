# -*- coding: utf-8 -*-
"""v1.1：去掉"批"的概念 → 一次一个词、随时退出随时接上；主界面显示认识百分比。"""
import io, os

ROOT = r"C:\Users\黄\Doubao\chats\2026-10-17\new-chat-1\band-word-app\vela-app"
UX = os.path.join(ROOT, "src", "pages", "index", "index.ux")

TEMPLATE = r'''<template>
	<div class="page" @touchstart="onTouchStart" @touchmove="onTouchMove" @touchend="onTouchEnd">

		<!-- 首页：认识进度 -->
		<div if="{{mode === 'home'}}" class="home">
			<div class="homeCard">
				<text class="appName">池鱼单词</text>
				<text class="ver">v1.1</text>
				<text class="pct">{{pct}}%</text>
				<text class="stat">已认识 {{knownCount}} / {{totalCount}}</text>
				<text class="stat2">单词 {{wordKnown}}/{{wordTotal}}</text>
				<text class="stat2">短语 {{phraseKnown}}/{{phraseTotal}}</text>
				<div class="btn" @click="startRound">
					<text class="btnText">开始背单词</text>
				</div>
				<text if="{{debug}}" class="dbg">{{debug}}</text>
				<div class="btnExit" @click="exitApp">
					<text class="btnExitText">退出</text>
				</div>
			</div>
		</div>

		<!-- 背单词：一次一个词 -->
		<div if="{{mode === 'study'}}" class="card {{animClass}}">
			<div class="miniExit" @click="exitApp"><text class="miniExitText">退</text></div>
			<div class="prog"><div class="progFill" style="width: {{pct}}%"></div></div>
			<text class="word">{{curWord.w}}</text>
			<text class="pos">本次第 {{sessionCount}} 个 · 已认识 {{pct}}%</text>
			<div class="btnRow">
				<div class="btnK" @click="chooseBtn('know')"><text class="btnKText">认识</text></div>
				<div class="btnF" @click="chooseBtn('fuzzy')"><text class="btnFText">模糊</text></div>
				<div class="btnN" @click="chooseBtn('forget')"><text class="btnNText">不会</text></div>
			</div>
		</div>

		<!-- 释义页 -->
		<div if="{{mode === 'meaning'}}" class="card animIn">
			<div class="miniExit" @click="exitApp"><text class="miniExitText">退</text></div>
			<text class="word">{{curWord.w}}</text>
			<text class="mean">{{curWord.m}}</text>
			<text class="actText">{{lastActText}}</text>
			<text class="hint2">轻点或点按钮继续</text>
			<div class="btnNext" @click="nextWord"><text class="btnNextText">下一个</text></div>
		</div>

		<!-- 今天没有该复习的了 -->
		<div if="{{mode === 'done'}}" class="card animIn">
			<text class="title2">今天先到这</text>
			<text class="stat">本次背了 {{sessionCount}} 个</text>
			<text class="stat2">已认识 {{knownCount}} / {{totalCount}}（{{pct}}%）</text>
			<text class="stat2">该复习的都复习完了</text>
			<div class="btnExit" @click="exitApp">
				<text class="btnExitText">退出</text>
			</div>
			<text class="hint2">过一会儿再来，会按熟练度提醒你</text>
		</div>
	</div>
</template>'''

SCRIPT = r'''<script>
import storage from '../../common/storage.js'
import srs from '../../common/srs.js'
import DICT from '../../common/dict.js'
import brightness from '@system.brightness'
import app from '@system.app'
import router from '@system.router'

// ===== 词库：4678 词内置，但不拆成对象数组 =====
// 只记录每行起始偏移，用到哪个词才截哪一行，避免一次性建 4678 个对象把内存撑爆。
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

function dictCount() { return offsets().length }

function dictWord(i) {
	var o = offsets()
	if (i < 0 || i >= o.length) return null
	var end = (i + 1 < o.length) ? o[i + 1] - 1 : DICT.length
	var line = DICT.substring(o[i], end)
	var t = line.indexOf('\t')
	if (t < 0) return { i: i, w: line, m: '', ph: 0 }
	var w = line.substring(0, t)
	return { i: i, w: w, m: line.substring(t + 1), ph: (w.indexOf(' ') >= 0 ? 1 : 0) }
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

const DAILY_NEW = 30      // 每天最多引入多少个新词
const REC_KEEP = 800      // 本地最多保留多少条记录（供手机周同步）
const KNOWN_P = 60        // 熟练度 ≥ 60 算「认识」（大约连续答对 3 次）
const WORD_TOTAL = 4425   // 词库里单词条数（不含短语）
const PHRASE_TOTAL = 253  // 词库里短语条数

export default {
	private: {
		mode: 'home',            // home | study | meaning | done
		curWord: { w: '', m: '', i: -1, ph: 0 },
		totalCount: 0,
		knownCount: 0,
		wordKnown: 0,
		phraseKnown: 0,
		wordTotal: WORD_TOTAL,
		phraseTotal: PHRASE_TOTAL,
		pct: 0,
		sessionCount: 0,
		lastActText: '',
		animClass: 'animIn',
		debug: ''
	},

	touch: { sx: 0, sy: 0, active: false },
	_shownAt: 0,
	_meaningAt: 0,
	_act: '',
	_rt: 0,

	onShow() {
		var that = this
		this.totalCount = dictCount()
		this.sessionCount = 0
		this.refreshStats()
		// 与手机握手
		try { globalThis.conn && globalThis.conn.send('__hs__', { count: 1 }) } catch (e) { }
	},

	// 统计：只遍历「学过的词」，不扫全库
	refreshStats() {
		var that = this
		storage.get('map', {}).then(function (map) {
			map = map || {}
			var known = 0, wk = 0, pk = 0
			for (var k in map) {
				var e = map[k]
				if (!e || typeof e.p !== 'number') continue
				if (e.p < KNOWN_P) continue
				known++
				if (e.ph) pk++
				else wk++
			}
			that.knownCount = known
			that.wordKnown = wk
			that.phraseKnown = pk
			that.pct = Math.round(known / that.totalCount * 1000) / 10
		})
	},

	startRound() {
		this.sessionCount = 0
		this.debug = ''
		this.pickNext()
	},

	// 取下一个该背的词：先到期复习词，再新词，都没有就收工
	pickNext() {
		var that = this
		this.debug = ''
		storage.getAll().then(function (db) {
			db = db || {}
			var map = db.map || {}
			var now = Date.now()

			// 1) 到期词里挑最急的一个（只遍历学过的词）
			var best = -1, bestU = -1
			for (var k in map) {
				var e = map[k]
				if (!e) continue
				if (e.t && e.t > now) continue
				var u = srs.urgency(e)
				if (u > bestU) { bestU = u; best = parseInt(k, 10) }
			}
			if (best >= 0) {
				that.showWord(best)
				return
			}

			// 2) 新词：随机抽一个没学过的，受每日配额限制
			var day = todayStr()
			var newCnt = (db.lastNewDay === day) ? (db.newLearned || 0) : 0
			if (newCnt >= DAILY_NEW) {
				that.mode = 'done'
				try { brightness.setKeepScreenOn({ keepScreenOn: false }) } catch (e) { }
				return
			}
			var total = dictCount()
			var idx = -1
			for (var g = 0; g < 60; g++) {
				var r = Math.floor(Math.random() * total)
				if (!map[r]) { idx = r; break }
			}
			if (idx < 0) {
				that.mode = 'done'
				try { brightness.setKeepScreenOn({ keepScreenOn: false }) } catch (e) { }
				return
			}
			db.lastNewDay = day
			db.newLearned = newCnt + 1
			storage.saveAll(db)
			that.showWord(idx)
		})
	},

	showWord(i) {
		var wd = dictWord(i)
		if (!wd) { this.mode = 'done'; return }
		this.curWord = wd
		this._shownAt = Date.now()
		this._act = ''
		this._rt = 0
		this.mode = 'study'
		this.animClass = 'animIn'
		this.sessionCount++
		try { brightness.setKeepScreenOn({ keepScreenOn: true }) } catch (e) { }
	},

	chooseBtn(action) {
		this.choose(action, Date.now() - this._shownAt)
	},

	choose(action, rt) {
		this._act = action
		this._rt = rt
		this.lastActText = action === 'know' ? '认识 ✓' : (action === 'fuzzy' ? '模糊 ~' : '不会 ✗')
		this.mode = 'meaning'
		this._meaningAt = Date.now()
	},

	nextWord() {
		var that = this
		var cw = this.curWord
		var dwell = Date.now() - this._meaningAt
		var act = this._act || 'fuzzy'
		var rt = this._rt

		// 一次读 + 一次写：更新熟练度 + 追加记录
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

		this.pickNext()
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
		if (ax >= ay && dx > 0) { this.exitApp(); return }
		if (this.mode === 'meaning' && isTap) { this.nextWord(); return }
		if (isTap) return
		if (this.mode !== 'study') return
		var action = null
		if (ay > ax && dy < 0) action = 'fuzzy'
		else if (ay > ax && dy > 0) action = 'forget'
		else if (ax >= ay && dx < 0) action = 'know'
		if (action) this.choose(action, Date.now() - this._shownAt)
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
			this.refreshStats()
			try { brightness.setKeepScreenOn({ keepScreenOn: false }) } catch (e) { }
		} else {
			this.exitApp()
		}
		return true
	}
}
</script>'''

PCT_STYLE = r'''
/* v1.1 首页大号百分比 */
.pct {
	font-size: 64px;
	font-weight: bold;
	color: #1781FF;
	margin-top: 22px;
}
'''

txt = io.open(UX, encoding="utf-8").read()

a = txt.index("<template>")
b = txt.index("</template>") + len("</template>")
txt = txt[:a] + TEMPLATE + txt[b:]

a = txt.index("<script>")
b = txt.index("</script>") + len("</script>")
txt = txt[:a] + SCRIPT + txt[b:]

txt = txt.replace("</style>", PCT_STYLE + "</style>")

io.open(UX, "w", encoding="utf-8", newline="\n").write(txt)
print("index.ux 已重写:", len(txt), "chars")

# 版本号
mf = os.path.join(ROOT, "src", "manifest.json")
m = io.open(mf, encoding="utf-8").read()
m = m.replace('"versionName": "1.0.0"', '"versionName": "1.1.0"').replace('"versionCode": 100', '"versionCode": 110')
io.open(mf, "w", encoding="utf-8", newline="\n").write(m)
print("manifest -> 1.1.0 / 110")

# -*- coding: utf-8 -*-
"""v1.3：首页加"范围"开关，默认只背高考核心词，点一下可放开到全部。"""
import io, os

ROOT = r"C:\Users\黄\Doubao\chats\2026-10-17\new-chat-1\band-word-app\vela-app"
SRC = os.path.join(ROOT, "src")
UX = os.path.join(SRC, "pages", "index", "index.ux")

t = io.open(UX, encoding="utf-8").read()

# 1) 模板：首页三行数字下面加范围开关
OLD_TPL = """				<text class="stat2">扩展词汇 {{extraKnown}} / {{extraTotal}}</text>
				<div class="btn" @click="startRound">"""
NEW_TPL = """				<text class="stat2">扩展词汇 {{extraKnown}} / {{extraTotal}}</text>
				<div class="scope" @click="toggleScope">
					<text class="scopeText">范围：{{scopeText}}</text>
				</div>
				<div class="btn" @click="startRound">"""
if OLD_TPL not in t:
    raise SystemExit("!! 模板未匹配")
t = t.replace(OLD_TPL, NEW_TPL)

# 2) private 字段
OLD_PRIV = """		coreTag: '',"""
NEW_PRIV = """		coreTag: '',
		scopeText: '只看核心词',"""
t = t.replace(OLD_PRIV, NEW_PRIV)

# 3) 实例字段
t = t.replace("""	_shownAt: 0,""", """	_onlyCore: 1,
	_shownAt: 0,""")

# 4) onShow 读取范围设置
OLD_SHOW = """		this.sessionCount = 0
		this.refreshStats()"""
NEW_SHOW = """		this.sessionCount = 0
		var that0 = this
		storage.get('only_core', 1).then(function (v) {
			that0._onlyCore = (v === 0 || v === false) ? 0 : 1
			that0.scopeText = that0._onlyCore ? '只看核心词' : '核心+扩展'
		})
		this.refreshStats()"""
if OLD_SHOW not in t:
    raise SystemExit("!! onShow 未匹配")
t = t.replace(OLD_SHOW, NEW_SHOW)

# 5) 切换方法（放在 startRound 前）
OLD_START = """	startRound() {"""
NEW_START = """	// 切换背诵范围：只背核心 / 核心+扩展
	toggleScope() {
		this._onlyCore = this._onlyCore ? 0 : 1
		this.scopeText = this._onlyCore ? '只看核心词' : '核心+扩展'
		storage.set('only_core', this._onlyCore)
	},

	startRound() {"""
t = t.replace(OLD_START, NEW_START, 1)

# 6) pickNext：按范围过滤
OLD_DUE = """			var best = -1, bestU = -1
			for (var k in map) {
				var e = map[k]
				if (!e) continue
				if (e.t && e.t > now) continue
				var u = srs.urgency(e)
				if (u > bestU) { bestU = u; best = parseInt(k, 10) }
			}"""
NEW_DUE = """			var onlyCore = that._onlyCore ? 1 : 0
			var best = -1, bestU = -1
			for (var k in map) {
				var e = map[k]
				if (!e) continue
				if (e.t && e.t > now) continue
				if (onlyCore && CORE.charCodeAt(parseInt(k, 10)) !== 49) continue
				var u = srs.urgency(e)
				if (u > bestU) { bestU = u; best = parseInt(k, 10) }
			}"""
if OLD_DUE not in t:
    raise SystemExit("!! 到期选词未匹配")
t = t.replace(OLD_DUE, NEW_DUE)

OLD_NEW = """			var total = dictCount()
			var idx = -1
			for (var g = 0; g < 60; g++) {
				var r = Math.floor(Math.random() * total)
				if (!map[r]) { idx = r; break }
			}"""
NEW_NEW = """			var total = dictCount()
			var idx = -1
			for (var g = 0; g < 200; g++) {
				var r = Math.floor(Math.random() * total)
				if (map[r]) continue
				if (onlyCore && CORE.charCodeAt(r) !== 49) continue
				idx = r
				break
			}"""
if OLD_NEW not in t:
    raise SystemExit("!! 新词选词未匹配")
t = t.replace(OLD_NEW, NEW_NEW)

# 7) 样式
t = t.replace("</style>", """
/* v1.3 范围开关 */
.scope {
	width: 168px;
	height: 44px;
	border-radius: 22px;
	background-color: rgba(255, 255, 255, 0.06);
	border: 1px solid rgba(90, 160, 255, 0.5);
	align-items: center;
	justify-content: center;
	margin-top: 14px;
}

.scopeText {
	font-size: 20px;
	color: #7FB3FF;
}
</style>""")

io.open(UX, "w", encoding="utf-8", newline="\n").write(t)
print("index.ux -> v1.3", len(t))

mf = os.path.join(SRC, "manifest.json")
m = io.open(mf, encoding="utf-8").read()
m = m.replace('"versionName": "1.2.0"', '"versionName": "1.3.0"').replace('"versionCode": 120', '"versionCode": 130')
io.open(mf, "w", encoding="utf-8", newline="\n").write(m)
print("manifest -> 1.3.0")

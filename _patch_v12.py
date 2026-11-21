# -*- coding: utf-8 -*-
"""v1.2：标出高考核心词（3573）与扩展词（1105），首页分开展示进度。"""
import io, json, os

ROOT = r"C:\Users\黄\Doubao\chats\2026-10-17\new-chat-1\band-word-app\vela-app"
SRC = os.path.join(ROOT, "src")
UX = os.path.join(SRC, "pages", "index", "index.ux")

data = json.load(open(r"C:\myapp\_core_map.json", encoding="utf-8"))
dict_words = data["dict"]
core = set(w.lower().strip() for w in data["core"])

bits = "".join("1" if w.lower().strip() in core else "0" for w in dict_words)
core_n = bits.count("1")
extra_n = len(bits) - core_n
print("core", core_n, "extra", extra_n, "total", len(bits))

# 1) core.js
with io.open(os.path.join(SRC, "common", "core.js"), "w", encoding="utf-8", newline="\n") as f:
    f.write("// 池鱼单词 · 核心词标记：与 dict.js 行号一一对应，1=高考考纲核心词，0=外研扩展\n")
    f.write("export default " + json.dumps(bits) + "\n")
print("core.js bytes", os.path.getsize(os.path.join(SRC, "common", "core.js")))

# 2) 页面改造
t = io.open(UX, encoding="utf-8").read()

t = t.replace(
    "import DICT from '../../common/dict.js'",
    "import DICT from '../../common/dict.js'\nimport CORE from '../../common/core.js'")

t = t.replace(
    """	if (t < 0) return { i: i, w: line, m: '', ph: 0 }
	var w = line.substring(0, t)
	return { i: i, w: w, m: line.substring(t + 1), ph: (w.indexOf(' ') >= 0 ? 1 : 0) }""",
    """	if (t < 0) return { i: i, w: line, m: '', core: 0 }
	var w = line.substring(0, t)
	return { i: i, w: w, m: line.substring(t + 1), core: (CORE.charCodeAt(i) === 49 ? 1 : 0) }""")

t = t.replace(
    """const KNOWN_P = 40        // 熟练度 ≥ 40 也算「认识」（多次答对后即使最近点了模糊也保留）
const WORD_TOTAL = 4425   // 词库里单词条数（不含短语）
const PHRASE_TOTAL = 253  // 词库里短语条数""",
    """const KNOWN_P = 40        // 熟练度 ≥ 40 也算「认识」（多次答对后即使最近点了模糊也保留）""")

t = t.replace(
    """		wordKnown: 0,
		phraseKnown: 0,
		wordTotal: WORD_TOTAL,
		phraseTotal: PHRASE_TOTAL,""",
    """		coreKnown: 0,
		extraKnown: 0,
		coreTotal: 0,
		extraTotal: 0,
		coreTag: '',""")

t = t.replace(
    """		this.totalCount = dictCount()
		this.sessionCount = 0""",
    """		this.totalCount = dictCount()
		var cn = 0
		for (var i = 0; i < CORE.length; i++) { if (CORE.charCodeAt(i) === 49) cn++ }
		this.coreTotal = cn
		this.extraTotal = this.totalCount - cn
		this.sessionCount = 0""")

# 统计循环：按核心标记分桶
OLD_STATS = """			var known = 0, wk = 0, pk = 0
			for (var k in map) {
				var e = map[k]
				if (!e || typeof e.p !== 'number') continue
				// 认不认识，看两件事：最近一次点的是"认识"，或熟练度已经足够高
				var ok = (e.a === 'know' && e.p >= 15) || e.p >= KNOWN_P
				if (!ok) continue
				known++
				if (e.ph) pk++
				else wk++
			}
			that.knownCount = known
			that.wordKnown = wk
			that.phraseKnown = pk
			that.pct = Math.round(known / that.totalCount * 1000) / 10"""
NEW_STATS = """			var known = 0, ck = 0, ek = 0
			for (var k in map) {
				var e = map[k]
				if (!e || typeof e.p !== 'number') continue
				// 认不认识，看两件事：最近一次点的是"认识"，或熟练度已经足够高
				var ok = (e.a === 'know' && e.p >= 15) || e.p >= KNOWN_P
				if (!ok) continue
				known++
				if (e.core) ck++
				else ek++
			}
			that.knownCount = known
			that.coreKnown = ck
			that.extraKnown = ek
			that.pct = Math.round(known / that.totalCount * 1000) / 10"""
if OLD_STATS not in t:
    raise SystemExit("!! 统计段落未匹配")
t = t.replace(OLD_STATS, NEW_STATS)

# 答题时把 core 标记写进词条
t = t.replace("			ne.ph = cw.ph", "			ne.core = cw.core ? 1 : 0")

# 展示当前词属于核心还是扩展
t = t.replace("""		this.mode = 'study'
		this.animClass = 'animIn'
		this.sessionCount++""",
              """		this.mode = 'study'
		this.animClass = 'animIn'
		this.coreTag = wd.core ? '高考核心' : '扩展词'
		this.sessionCount++""")

# 3) 模板
t = t.replace(
    """				<text class="stat2">单词 {{wordKnown}}/{{wordTotal}}</text>
				<text class="stat2">短语 {{phraseKnown}}/{{phraseTotal}}</text>""",
    """				<text class="stat2">高考核心 {{coreKnown}} / {{coreTotal}}</text>
				<text class="stat2">扩展词汇 {{extraKnown}} / {{extraTotal}}</text>""")

t = t.replace(
    """			<text class="word">{{curWord.w}}</text>
			<text class="pos">本次第 {{sessionCount}} 个 · 已认识 {{pct}}%</text>""",
    """			<text class="tag">{{coreTag}}</text>
			<text class="word">{{curWord.w}}</text>
			<text class="pos">本次第 {{sessionCount}} 个 · 已认识 {{pct}}%</text>""")

t = t.replace("</style>", """
/* v1.2 核心/扩展标签 */
.tag {
	font-size: 20px;
	color: #5BA3FF;
	background-color: rgba(23, 129, 255, 0.18);
	padding: 4px 14px;
	border-radius: 14px;
	margin-top: 8px;
}
</style>""")

io.open(UX, "w", encoding="utf-8", newline="\n").write(t)
print("index.ux patched", len(t))

# 4) 版本
mf = os.path.join(SRC, "manifest.json")
m = io.open(mf, encoding="utf-8").read()
m = m.replace('"versionName": "1.1.0"', '"versionName": "1.2.0"').replace('"versionCode": 110', '"versionCode": 120')
io.open(mf, "w", encoding="utf-8", newline="\n").write(m)
print("manifest -> 1.2.0")

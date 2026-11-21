# -*- coding: utf-8 -*-
"""手表词库：加入第三档「核心 680」，范围循环 680 → 3500 → 全部。"""
import io

UX = r"C:\Users\黄\Doubao\chats\2026-10-17\new-chat-1\band-word-app\vela-app\src\pages\index\index.ux"
t = io.open(UX, encoding="utf-8").read()

# 1) 导入 HOT
t = t.replace("import CORE from '../../common/core.js'",
              "import CORE from '../../common/core.js'\nimport HOT from '../../common/hot.js'", 1)

# 2) 状态：_onlyCore → _scope（默认 2 = 核心680）
t = t.replace("\t_onlyCore: 1,", "\t_scope: 2,   // 2=核心680 1=核心3500 0=全部", 1)

# 3) onShow 读取
t = t.replace("""		storage.get('only_core', 1).then(function (v) {
			that0._onlyCore = (v === 0 || v === false) ? 0 : 1
			that0.scopeText = that0._onlyCore ? '只看核心词' : '核心+扩展'
		})""",
              """		storage.get('scope', 2).then(function (v) {
			that0._scope = (v === 0 || v === 1 || v === 2) ? v : 2
			that0.scopeText = SCOPE_TEXT[that0._scope]
			that0.coreTotal = that0._scope === 2 ? hotCount() : that0.coreTotal
		})""", 1)

# 4) 切换逻辑
t = t.replace("""	// 切换背诵范围：只背核心 / 核心+扩展
	toggleScope() {
		this._onlyCore = this._onlyCore ? 0 : 1
		this.scopeText = this._onlyCore ? '只看核心词' : '核心+扩展'
		storage.set('only_core', this._onlyCore)
	},""",
              """	// 切换背诵范围：核心680 → 核心3500 → 全部
	toggleScope() {
		this._scope = (this._scope + 2) % 3
		this.scopeText = SCOPE_TEXT[this._scope]
		storage.set('scope', this._scope)
	},""", 1)

# 5) 过滤逻辑
t = t.replace("""			var onlyCore = that._onlyCore ? 1 : 0""",
              """			var scope = that._scope""", 1)
t = t.replace("""				if (onlyCore && CORE.charCodeAt(parseInt(k, 10)) !== 49) continue""",
              """				if (scope === 1 && CORE.charCodeAt(parseInt(k, 10)) !== 49) continue
				if (scope === 2 && HOT.charCodeAt(parseInt(k, 10)) !== 49) continue""", 1)
t = t.replace("""				if (onlyCore && CORE.charCodeAt(r) !== 49) continue""",
              """				if (scope === 1 && CORE.charCodeAt(r) !== 49) continue
				if (scope === 2 && HOT.charCodeAt(r) !== 49) continue""", 1)

# 6) 常量与辅助函数
t = t.replace("const DAILY_NEW = 100000",
              "const DAILY_NEW = 100000\nconst SCOPE_TEXT = ['全部词库', '核心3500', '核心680 · 高频']\n"
              "function hotCount() { var n = 0; for (var i = 0; i < HOT.length; i++) { if (HOT.charCodeAt(i) === 49) n++ } return n }", 1)

io.open(UX, "w", encoding="utf-8", newline="\n").write(t)
print("index.ux 已改为三档范围")

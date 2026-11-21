# -*- coding: utf-8 -*-
"""v1.1 逻辑测试：一次一个词、中途退出不丢进度、认识百分比。"""
import io, os, re

ROOT = r"C:\Users\黄\Doubao\chats\2026-10-17\new-chat-1\band-word-app\vela-app"
OUT = r"C:\myapp\_band_logic_test.mjs"

ux = io.open(os.path.join(ROOT, "src", "pages", "index", "index.ux"), encoding="utf-8").read()
script = re.search(r"<script>(.*?)</script>", ux, re.S).group(1)
script = re.sub(r"^\s*import .*$", "", script, flags=re.M)
script = script.replace("export default {", "const PAGE = {", 1)

srs_src = io.open(os.path.join(ROOT, "src", "common", "srs.js"), encoding="utf-8").read()
srs_src = re.sub(r"^\s*export default \{", "const srs = {", srs_src, flags=re.M)

dict_src = io.open(os.path.join(ROOT, "src", "common", "dict.js"), encoding="utf-8").read()
DICT = dict_src.split("export default ", 1)[1].strip()

core_src = io.open(os.path.join(ROOT, "src", "common", "core.js"), encoding="utf-8").read()
CORE = core_src.split("export default ", 1)[1].strip()

HARNESS = r"""
const DICT = __DICT__;
const CORE = __CORE__;

let DB = {};
const storage = {
  get: (k, d) => Promise.resolve(DB[k] === undefined ? (d === undefined ? '' : d) : JSON.parse(JSON.stringify(DB[k]))),
  set: (k, v) => { DB[k] = v; return Promise.resolve(true); },
  getAll: () => Promise.resolve(JSON.parse(JSON.stringify(DB))),
  saveAll: (o) => { DB = JSON.parse(JSON.stringify(o)); return Promise.resolve(true); }
};
const brightness = { setKeepScreenOn: () => {} };
const app = { terminate: () => {} };
const router = { clear: () => {} };
const global = globalThis;

__SRS__

__SCRIPT__

Object.assign(PAGE, PAGE.private || {});   // 模拟框架把 private 映射到实例
const sleep = (ms) => new Promise(r => setTimeout(r, ms));
let fails = 0;
const check = (n, ok, ex) => {
  console.log((ok ? 'PASS  ' : 'FAIL  ') + n + (ex !== undefined ? '  [' + ex + ']' : ''));
  if (!ok) fails++;
};

// ---- 首页统计 ----
PAGE.onShow();
await sleep(40);
check('词库总数 4678', PAGE.totalCount === 4678, PAGE.totalCount);
check('初始已认识 0', PAGE.knownCount === 0, PAGE.knownCount);
check('初始百分比 0', PAGE.pct === 0, PAGE.pct);
check('核心词 3573 / 扩展 1105', PAGE.coreTotal === 3573 && PAGE.extraTotal === 1105,
  PAGE.coreTotal + '/' + PAGE.extraTotal);

// ---- 开始背 ----
PAGE.startRound();
await sleep(40);
check('进入背词模式', PAGE.mode === 'study', PAGE.mode);
check('拿到词且有释义', !!PAGE.curWord.w && !!PAGE.curWord.m, PAGE.curWord.w);
check('curWord 带索引', typeof PAGE.curWord.i === 'number', PAGE.curWord.i);

const firstWord = PAGE.curWord.w;
const firstIdx = PAGE.curWord.i;

// ---- 背 5 个后「退出」 ----
for (let n = 0; n < 5; n++) {
  PAGE.chooseBtn('know');
  check('答题后进释义 #' + n, PAGE.mode === 'meaning', PAGE.mode);
  PAGE.nextWord();
  await sleep(20);
}
check('本次已显示第 6 个词', PAGE.sessionCount === 6, PAGE.sessionCount);
PAGE.onHide();          // 触发落盘（现在攒批写盘）
await sleep(30);
const mapAfter5 = Object.keys(DB.map || {}).length;
check('5 个词已入库', mapAfter5 === 5, mapAfter5);

// ---- 模拟退出重进：重新 onShow ----
PAGE.mode = 'home';
PAGE.onShow();
await sleep(40);
check('重进后本次计数归零', PAGE.sessionCount === 0, PAGE.sessionCount);
check('重进后进度保留 5 个', PAGE.knownCount === 5, PAGE.knownCount);
check('百分比 > 0', PAGE.pct > 0 && PAGE.pct < 1, PAGE.pct);

// ---- 再开始：不应该把刚背过的 5 个重新给一遍 ----
PAGE.startRound();
await sleep(40);
check('新一轮仍在背词模式', PAGE.mode === 'study', PAGE.mode);
check('不会立刻重复上一个词', PAGE.curWord.w !== firstWord || PAGE.curWord.i !== firstIdx,
  PAGE.curWord.w);
check('新词不在已学集合里', !(DB.map || {})[PAGE.curWord.i], PAGE.curWord.i);

// ---- 连背 40 个，看统计变化 ----
let done = 0;
for (let n = 0; n < 40 && PAGE.mode !== 'done'; n++) {
  PAGE.chooseBtn(n % 3 === 0 ? 'forget' : 'know');
  PAGE.nextWord();
  await sleep(8);
  done++;
}
check('不再卡 30 个上限', done === 40, done + '/' + PAGE.mode);
check('已认识数量增加', PAGE.knownCount >= 5, PAGE.knownCount);
check('核心+扩展统计等于总认识', PAGE.coreKnown + PAGE.extraKnown === PAGE.knownCount,
  PAGE.coreKnown + '+' + PAGE.extraKnown + '=' + PAGE.knownCount);
check('记录字段兼容池鱼Study', DB.records && DB.records[0].word && DB.records[0].action && DB.records[0].t,
  DB.records && Object.keys(DB.records[0]).join(','));
check('记录带熟练度', DB.records && typeof DB.records[0].p === 'number', DB.records && DB.records[0].p);

// ---- 范围开关（v1.3）----
PAGE.mode = 'home';
PAGE.onShow();
await sleep(30);
check('默认只看核心词', PAGE.scopeText === '只看核心词', PAGE.scopeText);

const coreIdx = [], extIdx = [];
for (let i = 0; i < CORE.length; i++) { (CORE[i] === '1' ? coreIdx : extIdx).push(i); }
const d0 = new Date();
const today = d0.getFullYear() + '-' + String(d0.getMonth() + 1).padStart(2, '0') + '-' + String(d0.getDate()).padStart(2, '0');
const coreMap = {};
coreIdx.forEach(i => { coreMap[i] = { p: 60, t: Date.now() + 7 * 86400000, a: 'know' }; });
_db = { map: coreMap, records: [], newLearned: 0, lastNewDay: today };
_pend = 0;   // 直接改内存缓存（页面现在走缓存，不再每次读盘）

PAGE.startRound();
await sleep(40);
check('核心全学完后不出扩展词', PAGE.mode === 'done', PAGE.mode);

PAGE.toggleScope();
check('开关切到核心+扩展', PAGE.scopeText === '核心+扩展', PAGE.scopeText);
PAGE.startRound();
await sleep(40);
check('放开后能出扩展词', PAGE.mode === 'study' && PAGE.curWord.core === 0,
  PAGE.curWord.core + ':' + PAGE.curWord.w);

// ---- 慢速作答也必须算「掌握」（手环上真人要读好几秒）----
_db = { map: {}, records: [], newLearned: 0, lastNewDay: today }; _pend = 0;
PAGE.mode = 'home';
PAGE.onShow();
await sleep(30);
PAGE.startRound();
await sleep(40);
PAGE._shownAt = Date.now() - 9000;    // 假装盯着单词看了 9 秒
PAGE.chooseBtn('know');
PAGE._meaningAt = Date.now() - 600;   // 释义只扫了一眼
PAGE.nextWord();
await sleep(60);
check('慢速点认识也算掌握', PAGE.knownCount === 1, PAGE.knownCount + ' / 已学 ' + PAGE.seenCount);
check('已学数 > 0', PAGE.seenCount >= 1, PAGE.seenCount);

// ---- 算法单调性 ----
const e1 = srs.answer({}, 'know', 800, 4000);
const e2 = srs.answer(e1, 'know', 800, 4000);
const e3 = srs.answer(e2, 'forget', 6000, 500);
check('认识→熟练度上升', e1.p > 0, e1.p);
check('连续认识继续升', e2.p > e1.p, e1.p + ' -> ' + e2.p);
check('越熟问得越晚', (e2.t - Date.now()) > (e1.t - Date.now()),
  Math.round((e1.t - Date.now()) / 3600000) + 'h -> ' + Math.round((e2.t - Date.now()) / 3600000) + 'h');
check('不会→熟练度腰斩', e3.p < e2.p / 2 + 10, e2.p + ' -> ' + e3.p);
check('不会→10 分钟后重问', (e3.t - Date.now()) <= 11 * 60 * 1000,
  Math.round((e3.t - Date.now()) / 60000) + ' 分钟');

console.log('');
console.log(fails ? ('==== ' + fails + ' 项失败 ====') : '==== 全部通过 ====');
process.exit(fails ? 1 : 0);
"""

HARNESS = (HARNESS.replace("__DICT__", DICT)
                  .replace("__CORE__", CORE)
                  .replace("__SRS__", srs_src)
                  .replace("__SCRIPT__", script))
io.open(OUT, "w", encoding="utf-8", newline="\n").write(HARNESS)
print("generated", len(HARNESS))

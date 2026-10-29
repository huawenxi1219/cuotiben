# -*- coding: utf-8 -*-
import flet as ft
import json
import os
import re
import time
import shutil
import random
import requests
import threading
import sys
import base64
import uuid
import zipfile
from datetime import datetime, timedelta
import traceback
import http.server
import urllib.parse

DEBUG = True

_IS_ANDROID = os.path.exists("/system/build.prop")

if _IS_ANDROID:
    _pkg = "com.flet.chiyu_study"
    _try_dirs = [
        f"/storage/emulated/0/Android/data/{_pkg}/files/智能错题笔记",
        f"/sdcard/Android/data/{_pkg}/files/智能错题笔记",
        f"/data/data/{_pkg}/files/智能错题笔记",
    ]
    DATA_DIR = None
    DIAG_TEXT = ""
    for _d in _try_dirs:
        try:
            os.makedirs(_d, exist_ok=True)
            _t = os.path.join(_d, ".wtest")
            with open(_t, "w") as _f:
                _f.write("ok")
            os.remove(_t)
            DATA_DIR = _d
            DIAG_TEXT = f"OK: {_d}"
            break
        except Exception as _e:
            DIAG_TEXT += f" | FAIL: {str(_e)[:60]}"
    if DATA_DIR is None:
        DATA_DIR = f"/data/data/{_pkg}/files/flet/app/data"
        DIAG_TEXT = "ALL FAIL -> fallback"
else:
    DATA_DIR = os.path.join(os.getcwd(), "data")
    DIAG_TEXT = "dev mode"
os.makedirs(DATA_DIR, exist_ok=True)

IMAGES_DIR = os.path.join(DATA_DIR, "images")
VIDEOS_DIR = os.path.join(DATA_DIR, "videos")
DOCS_DIR = os.path.join(DATA_DIR, "documents")
ERRORS_FILE = os.path.join(DATA_DIR, "errors.jsonl")
NOTES_FILE = os.path.join(DATA_DIR, "notes.jsonl")
RECYCLE_FILE = os.path.join(DATA_DIR, "recycle.jsonl")
REVIEW_CARDS_FILE = os.path.join(DATA_DIR, "review_cards.jsonl")
TASKS_FILE = os.path.join(DATA_DIR, "tasks.jsonl")
AI_CONFIG_FILE = os.path.join(DATA_DIR, "ai_config.json")
USER_PROFILE_FILE = os.path.join(DATA_DIR, "user_profile.json")
CUSTOM_SKILL_FILE = os.path.join(DATA_DIR, "custom_skill.txt")
CHAT_HISTORY_DIR = os.path.join(DATA_DIR, "chat_history")
CONTENT_LIB_DIR = os.path.join(DATA_DIR, "content_lib")
NEW_WORDS_FILE = os.path.join(DATA_DIR, "vocabulary.jsonl")
VOCAB_FILE = os.path.join(DATA_DIR, "vocabulary.jsonl")
SENTENCES_FILE = os.path.join(DATA_DIR, "sentences.jsonl")
LEARNING_EVENTS_FILE = os.path.join(DATA_DIR, "learning_events.jsonl")
VOCAB_SETTINGS_FILE = os.path.join(DATA_DIR, "vocab_settings.json")
_jsonl_lock = threading.Lock()
_vocab_rw_lock = threading.Lock()   # 词库"读→改→写"原子锁（AI 补齐/派生词生成用）
def now_ms():
    """统一的毫秒级时间戳，以后所有事件时间线都用这个"""
    return int(time.time() * 1000)


def gen_uid():
    """生成短唯一 ID"""
    return uuid.uuid4().hex[:16]


def dedup_keys(item, extra_fields):
    """返回一条记录的去重键集合。任意一个键撞上就算重复"""
    keys = set()
    eid = item.get("event_id")
    if eid:
        keys.add(f"eid:{eid}")
    parts = []
    for f in extra_fields:
        v = item.get(f, "")
        if isinstance(v, str):
            v = v[:80].strip()
        parts.append(str(v))
    if any(parts):
        keys.add("c:" + "|".join(parts))
    return keys

DEFAULT_VOCAB_SETTINGS = {
    "daily_new": 20,
    "daily_review_limit": 100,
    "quiz_mode": "mix",
    "show_phonetic": True,
}

for d in [DATA_DIR, IMAGES_DIR, VIDEOS_DIR, DOCS_DIR, CHAT_HISTORY_DIR, CONTENT_LIB_DIR]:
    os.makedirs(d, exist_ok=True)


def load_vocab_settings():
    if not os.path.exists(VOCAB_SETTINGS_FILE):
        return dict(DEFAULT_VOCAB_SETTINGS)
    try:
        with open(VOCAB_SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        for k, v in DEFAULT_VOCAB_SETTINGS.items():
            data.setdefault(k, v)
        return data
    except BaseException:
        return dict(DEFAULT_VOCAB_SETTINGS)


def save_vocab_settings(settings):
    with open(VOCAB_SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)


REVIEW_INTERVALS = [1, 2, 4, 7, 15, 30, 60, 120]


def ensure_learning_field(word_data):
    if "learning" not in word_data or not isinstance(word_data.get("learning"), dict):
        word_data["learning"] = {
            "status": "new", "level": 0,
            "next_review": datetime.now().strftime("%Y-%m-%d"),
            "review_count": 0, "correct_count": 0, "wrong_count": 0, "last_review": "",
            "synced": True   # 是否已推送到手环（新增词为 False，同步后置 True）
        }
    else:
        L = word_data["learning"]
        L.setdefault("status", "new")
        L.setdefault("level", 0)
        L.setdefault("next_review", datetime.now().strftime("%Y-%m-%d"))
        L.setdefault("synced", True)
        L.setdefault("review_count", 0)
        L.setdefault("correct_count", 0)
        L.setdefault("wrong_count", 0)
        L.setdefault("last_review", "")
    return word_data


def schedule_next_review(level):
    idx = min(max(level, 0), len(REVIEW_INTERVALS) - 1)
    return REVIEW_INTERVALS[idx]


def update_word_learning(word, result, review_time=None):
    """SM-2 间隔重复算法：记录每次选择的确切时间，按难度系数动态安排复习
    review_time: 可选，手环同步时传入原始选择时间（格式 YYYY-MM-DD HH:MM:SS）"""
    existing = load_jsonl(VOCAB_FILE)
    now_dt = datetime.now()
    if review_time:
        try:
            now_dt = datetime.strptime(str(review_time).strip(), "%Y-%m-%d %H:%M:%S")
        except Exception:
            now_dt = datetime.now()
    now_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")
    for i, w in enumerate(existing):
        if w.get("word", "").lower() == word.lower():
            ensure_learning_field(existing[i])
            L = existing[i]["learning"]
            L["review_count"] = L.get("review_count", 0) + 1
            L["last_review"] = now_str
            # 初始化 SRS 字段
            if "ease" not in L or not isinstance(L.get("ease"), (int, float)):
                L["ease"] = 2.5
            if "interval" not in L or not isinstance(L.get("interval"), (int, float)):
                L["interval"] = 0
            if "history" not in L or not isinstance(L.get("history"), list):
                L["history"] = []
            # SM-2 质量分：认识/答对=5，模糊=3，忘记/答错=1
            if result in ("know", "quiz_correct"):
                q = 5
            elif result == "fuzzy":
                q = 3
            else:  # forget / quiz_wrong
                q = 1
            ease = float(L["ease"])
            interval = int(L["interval"])
            if q >= 3:
                if interval == 0:
                    interval = 1
                elif interval == 1:
                    interval = 3
                else:
                    interval = max(2, round(interval * ease))
                ease = max(1.3, ease + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02)))
                L["correct_count"] = L.get("correct_count", 0) + 1
                L["level"] = min(L.get("level", 0) + 1, len(REVIEW_INTERVALS) - 1)
                L["status"] = "mastered" if L["level"] >= 4 else "review"
            else:
                # 答错/忘记：大幅缩短间隔，降低难度系数，重新进入学习
                if interval <= 1:
                    interval = 1
                else:
                    interval = max(1, round(interval * 0.3))
                ease = max(1.3, ease - 0.2)
                L["level"] = max(0, L.get("level", 0) - 2)
                L["wrong_count"] = L.get("wrong_count", 0) + 1
                L["status"] = "learning"
            L["ease"] = round(ease, 2)
            L["interval"] = interval
            L["next_review"] = (now_dt + timedelta(days=interval)).strftime("%Y-%m-%d")
            L["history"].append({"time": now_str, "action": result})
            L["history"] = L["history"][-200:]  # 只保留最近 200 次选择记录
            existing[i] = w
            break
    save_jsonl(VOCAB_FILE, existing)


# ========== 手环背单词：词表导出 / 记录回收（与手环端「池鱼单词」协议一致） ==========
BAND_DAY_MS = 86400000


def _str_to_ms(date_str):
    """YYYY-MM-DD HH:MM:SS → 毫秒时间戳；解析失败返回 0"""
    try:
        dt = datetime.strptime(str(date_str).strip(), "%Y-%m-%d %H:%M:%S")
        return int(dt.timestamp() * 1000)
    except Exception:
        return 0


def count_unsynced_words():
    """统计新增后尚未推送到手环的单词数"""
    n = 0
    try:
        for w in load_jsonl(VOCAB_FILE):
            ensure_learning_field(w)
            if not w["learning"].get("synced", True):
                n += 1
    except Exception:
        pass
    return n


def export_wordbook(path):
    """导出单词本：用户词库格式 JSONL（word/phonetic/meaning/example/forms/grammar/phrases）
    不含学习状态字段，便于分享/更新词库"""
    words = load_jsonl(VOCAB_FILE)
    lines = []
    for w in words:
        entry = {
            "word": w.get("word", ""),
            "phonetic": w.get("phonetic", ""),
            "meaning": w.get("meaning", ""),
            "example": w.get("example", ""),
            "forms": w.get("forms", ""),
            "grammar": w.get("grammar", {}) if isinstance(w.get("grammar"), dict) else {},
            "phrases": w.get("phrases", []) if isinstance(w.get("phrases"), list) else [],
        }
        lines.append(json.dumps(entry, ensure_ascii=False))
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + ("\n" if lines else ""))
    return len(lines)


def build_band_wordlist(scope="due", count=50):
    """按协议生成词表 JSON：{version, words:[{w,m,e,i,lvl,c,wc,next}]}
    scope: due=今日到期优先 low=熟练度低优先 new=新词优先 unsynced=未同步手环的词优先 all=全部按紧急度"""
    all_words = load_jsonl(VOCAB_FILE)
    today = datetime.now().strftime("%Y-%m-%d")
    now_ms = int(datetime.now().timestamp() * 1000)
    scored = []
    for w in all_words:
        ensure_learning_field(w)
        L = w["learning"]
        word = w.get("word", "")
        if not word:
            continue
        lvl = int(L.get("level", 0))
        status = L.get("status", "new")
        nxt = L.get("next_review", "")
        due = 1 if (nxt and nxt <= today) else 0
        wrong = int(L.get("wrong_count", 0))
        if scope == "due":
            key = (-due, lvl, -wrong)          # 到期 > 低熟练 > 错多
        elif scope == "low":
            key = (lvl, -due, -wrong)
        elif scope == "new":
            key = (0 if status == "new" else 1, lvl, -due)
        elif scope == "unsynced":
            key = (0 if not L.get("synced", True) else 1, lvl, -due)   # 未同步的词排最前
        else:  # all
            key = (-due, lvl, -wrong, w.get("word", "").lower())
        scored.append((key, w, L, word))
    if scope == "unsynced":
        # 一键同步新词：只推未同步的词
        scored = [x for x in scored if not x[2].get("synced", True)]
    scored.sort(key=lambda x: x[0])
    selected = scored[:max(1, min(count, len(scored)))]
    words_out = []
    for _key, w, L, word in selected:
        last_review = L.get("last_review", "")
        next_ts = _str_to_ms(last_review)
        if next_ts <= 0:
            # 从未学过的新词：标记为 3 天前，手环端会按"到期"优先问
            next_ts = now_ms - 3 * BAND_DAY_MS
        words_out.append({
            "w": word,
            "m": w.get("meaning", "") or w.get("释义", ""),
            "e": float(L.get("ease", 2.5)),
            "i": int(L.get("interval", 0)),
            "lvl": int(L.get("level", 0)),
            "c": int(L.get("correct_count", 0)),
            "wc": int(L.get("wrong_count", 0)),
            "next": next_ts,
        })
    return {"version": 1, "words": words_out}


def merge_band_records(records):
    """智能合并手环学习记录：
    - 按 (单词, 选择时间) 去重
    - 用原始选择时间更新手机 SRS（SM-2）
    - 返回 (回收条数, 更新词数, 新增待复习词数, 连续错词列表)"""
    seen = set()
    merged_count = 0
    words_updated = set()
    consecutive_wrong = {}
    today = datetime.now().strftime("%Y-%m-%d")
    new_due = set()
    for r in records or []:
        if not isinstance(r, dict):
            continue
        word = r.get("word", "")
        t = r.get("t", "")
        action = r.get("action", "")
        if not word or not t or action not in ("know", "fuzzy", "forget"):
            continue
        key = (word.lower(), str(t))
        if key in seen:
            continue
        seen.add(key)
        merged_count += 1
        try:
            update_word_learning(word, action, review_time=t)
        except Exception:
            continue
        words_updated.add(word.lower())
        if action == "forget":
            consecutive_wrong[word] = consecutive_wrong.get(word, 0) + 1
        else:
            consecutive_wrong[word] = 0
    # 统计合并后今日待复习新增（更新过的词里 next_review <= 今天 且 状态非 new）
    if words_updated:
        for w in load_jsonl(VOCAB_FILE):
            if w.get("word", "").lower() not in words_updated:
                continue
            ensure_learning_field(w)
            L = w["learning"]
            if L.get("status") == "new":
                continue
            if L.get("next_review", "") and L["next_review"] <= today:
                new_due.add(w["word"])
    bad = [w for w, n in consecutive_wrong.items() if n >= 2]
    return merged_count, len(words_updated), len(new_due), bad


# ========== 手环本地同步服务（伴生App「池鱼手环同步」直连，无需手动传文件） ==========
BAND_HTTP_PORT = 8765
band_http_server = None
band_http_running = False
band_http_lock = threading.Lock()


def start_band_http_server():
    """在 127.0.0.1:8765 起本地同步服务：
    GET  /api/wordlist?scope=due&count=50   → 词表 JSON（伴生App推送用）
    POST /api/records                       → 接收手环记录并智能合并
    POST /api/sync_ack                      → 伴生App推送成功回执，标记对应词"已同步"
    GET  /health                            → 服务状态"""
    global band_http_server, band_http_running
    if band_http_running:
        return True

    class _Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _send(self, obj, code=200):
            try:
                data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            except Exception:
                pass

        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path == "/health":
                self._send({"ok": True, "name": "池鱼Study同步服务", "port": BAND_HTTP_PORT})
            elif parsed.path == "/api/wordlist":
                q = urllib.parse.parse_qs(parsed.query)
                scope = q.get("scope", ["due"])[0]
                try:
                    count = int(q.get("count", ["50"])[0])
                except Exception:
                    count = 50
                with band_http_lock:
                    try:
                        payload = build_band_wordlist(scope, count)
                        self._send(payload)
                    except Exception as ex:
                        self._send({"error": str(ex)}, 500)
            else:
                self._send({"error": "not found"}, 404)

        def do_POST(self):
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path == "/api/records":
                try:
                    length = int(self.headers.get("Content-Length", 0))
                    body = self.rfile.read(length).decode("utf-8") if length else "[]"
                    records = json.loads(body)
                    if isinstance(records, dict):
                        records = records.get("records", [])
                    with band_http_lock:
                        merged, updated, new_due, bad = merge_band_records(records)
                    self._send({"merged": merged, "updated": updated,
                                "new_due": new_due, "bad": bad})
                except Exception as ex:
                    self._send({"error": str(ex)}, 500)
            elif parsed.path == "/api/sync_ack":
                # 伴生App 推送词表成功 → 标记这些词"已同步"
                try:
                    length = int(self.headers.get("Content-Length", 0))
                    body = self.rfile.read(length).decode("utf-8") if length else "{}"
                    payload = json.loads(body) if body else {}
                    if isinstance(payload, dict):
                        word_list = payload.get("words", [])
                    else:
                        word_list = []
                    marked = 0
                    with band_http_lock:
                        existing = load_jsonl(VOCAB_FILE)
                        wset = {str(x).lower() for x in word_list if str(x)}
                        if wset:
                            for w in existing:
                                ensure_learning_field(w)
                                if w.get("word", "").lower() in wset and not w["learning"].get("synced", True):
                                    w["learning"]["synced"] = True
                                    marked += 1
                            if marked:
                                save_jsonl(VOCAB_FILE, existing)
                    self._send({"ok": True, "marked": marked})
                except Exception as ex:
                    self._send({"error": str(ex)}, 500)
            else:
                self._send({"error": "not found"}, 404)

    try:
        server = http.server.HTTPServer(("127.0.0.1", BAND_HTTP_PORT), _Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        band_http_server = server
        band_http_running = True
        return True
    except Exception:
        band_http_running = False
        return False


def stop_band_http_server():
    global band_http_server, band_http_running
    if band_http_server:
        try:
            band_http_server.shutdown()
        except Exception:
            pass
        band_http_server = None
    band_http_running = False


def get_today_new_words(limit):
    all_words = load_jsonl(VOCAB_FILE)
    new_words = []
    for w in all_words:
        ensure_learning_field(w)
        if w["learning"].get("status") == "new":
            new_words.append(w)
    return new_words[:limit]


def get_today_review_words(limit):
    all_words = load_jsonl(VOCAB_FILE)
    today = datetime.now().strftime("%Y-%m-%d")
    review = []
    for w in all_words:
        ensure_learning_field(w)
        L = w["learning"]
        if L.get("status") == "new":
            continue
        nxt = L.get("next_review", "")
        if nxt and nxt <= today:
            review.append(w)
    return review[:limit]


def get_wrong_words(limit=500):
    all_words = load_jsonl(VOCAB_FILE)
    wrong = []
    for w in all_words:
        ensure_learning_field(w)
        L = w["learning"]
        if L.get("wrong_count", 0) > 0 and L.get("level", 0) < 3:
            wrong.append(w)
    wrong.sort(key=lambda x: -x["learning"].get("wrong_count", 0))
    return wrong[:limit]


def update_data_dir(new_path: str):
    global DATA_DIR, IMAGES_DIR, VIDEOS_DIR, DOCS_DIR, ERRORS_FILE, NOTES_FILE
    global RECYCLE_FILE, REVIEW_CARDS_FILE, TASKS_FILE, AI_CONFIG_FILE, USER_PROFILE_FILE
    global CUSTOM_SKILL_FILE, CHAT_HISTORY_DIR, CONTENT_LIB_DIR, NEW_WORDS_FILE
    global VOCAB_FILE, SENTENCES_FILE, LEARNING_EVENTS_FILE, VOCAB_SETTINGS_FILE
    DATA_DIR = new_path
    IMAGES_DIR = os.path.join(DATA_DIR, "images")
    VIDEOS_DIR = os.path.join(DATA_DIR, "videos")
    DOCS_DIR = os.path.join(DATA_DIR, "documents")
    ERRORS_FILE = os.path.join(DATA_DIR, "errors.jsonl")
    NOTES_FILE = os.path.join(DATA_DIR, "notes.jsonl")
    RECYCLE_FILE = os.path.join(DATA_DIR, "recycle.jsonl")
    REVIEW_CARDS_FILE = os.path.join(DATA_DIR, "review_cards.jsonl")
    TASKS_FILE = os.path.join(DATA_DIR, "tasks.jsonl")
    AI_CONFIG_FILE = os.path.join(DATA_DIR, "ai_config.json")
    USER_PROFILE_FILE = os.path.join(DATA_DIR, "user_profile.json")
    CUSTOM_SKILL_FILE = os.path.join(DATA_DIR, "custom_skill.txt")
    CHAT_HISTORY_DIR = os.path.join(DATA_DIR, "chat_history")
    CONTENT_LIB_DIR = os.path.join(DATA_DIR, "content_lib")
    NEW_WORDS_FILE = os.path.join(DATA_DIR, "vocabulary.jsonl")
    VOCAB_FILE = os.path.join(DATA_DIR, "vocabulary.jsonl")
    SENTENCES_FILE = os.path.join(DATA_DIR, "sentences.jsonl")
    LEARNING_EVENTS_FILE = os.path.join(DATA_DIR, "learning_events.jsonl")
    VOCAB_SETTINGS_FILE = os.path.join(DATA_DIR, "vocab_settings.json")
    for d in [DATA_DIR, IMAGES_DIR, VIDEOS_DIR, DOCS_DIR, CHAT_HISTORY_DIR, CONTENT_LIB_DIR]:
        os.makedirs(d, exist_ok=True)

def merge_restore_from_zip(zip_path):
    """合并恢复：zip 数据合进当前数据，两边都保留，不覆盖"""
    stats = {"errors": 0, "notes": 0, "vocab": 0, "sentences": 0, "events": 0, "images": 0}
    tmp_dir = os.path.join(DATA_DIR, "_restore_tmp")
    try:
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)
        os.makedirs(tmp_dir, exist_ok=True)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(tmp_dir)

        def _normalize(it):
            if not it.get("event_id"):
                it["event_id"] = gen_uid()
            ts = it.get("timestamp", 0)
            if isinstance(ts, (int, float)) and ts and ts < 10000000000:
                it["timestamp"] = int(ts) * 1000

        rules = [
            ("errors.jsonl", ["subject", "original", "mistake"], ERRORS_FILE, "errors"),
            ("notes.jsonl", ["subject", "content"], NOTES_FILE, "notes"),
            ("learning_events.jsonl", ["type", "subject", "kp", "detail"], LEARNING_EVENTS_FILE, "events"),
        ]
        for fname, fields, dst_path, stat_key in rules:
            src = os.path.join(tmp_dir, fname)
            if not os.path.exists(src):
                continue
            incoming = load_jsonl(src)
            existing = load_jsonl(dst_path)
            seen = set()
            for it in existing:
                seen |= dedup_keys(it, fields)
            added = 0
            for it in incoming:
                _normalize(it)
                keys = dedup_keys(it, fields)
                if keys & seen:
                    continue
                existing.append(it)
                seen |= keys
                added += 1
            save_jsonl(dst_path, existing)
            stats[stat_key] = added

        src_v = os.path.join(tmp_dir, "vocabulary.jsonl")
        if os.path.exists(src_v):
            incoming = load_jsonl(src_v)
            existing = load_jsonl(VOCAB_FILE)
            seen = set(str(w.get("word", "")).lower() for w in existing if w.get("word"))
            added = 0
            for w in incoming:
                word = str(w.get("word", "")).lower()
                if not word or word in seen:
                    continue
                if not w.get("event_id"):
                    w["event_id"] = gen_uid()
                existing.append(w)
                seen.add(word)
                added += 1
            save_jsonl(VOCAB_FILE, existing)
            stats["vocab"] = added

        src_s = os.path.join(tmp_dir, "sentences.jsonl")
        if os.path.exists(src_s):
            incoming = load_jsonl(src_s)
            existing = load_jsonl(SENTENCES_FILE)
            seen_text = set(s.get("sentence", "") for s in existing)
            max_id = max([s.get("id", 0) for s in existing], default=0)
            added = 0
            for s in incoming:
                t = s.get("sentence", "")
                if not t or t in seen_text:
                    continue
                max_id += 1
                s["id"] = max_id
                if not s.get("event_id"):
                    s["event_id"] = gen_uid()
                if not s.get("timestamp"):
                    s["timestamp"] = now_ms()
                existing.append(s)
                seen_text.add(t)
                added += 1
            save_jsonl(SENTENCES_FILE, existing)
            stats["sentences"] = added

        src_t = os.path.join(tmp_dir, "tasks.jsonl")
        if os.path.exists(src_t):
            incoming = load_jsonl(src_t)
            existing = load_jsonl(TASKS_FILE)
            seen_t = set(t.get("created", "") for t in existing)
            for t in incoming:
                c = t.get("created", "")
                if c and c not in seen_t:
                    if not t.get("event_id"):
                        t["event_id"] = gen_uid()
                    existing.append(t)
                    seen_t.add(c)
            save_jsonl(TASKS_FILE, existing)

        src_chat = os.path.join(tmp_dir, "chat_history")
        if os.path.exists(src_chat):
            os.makedirs(CHAT_HISTORY_DIR, exist_ok=True)
            for fname in os.listdir(src_chat):
                if not fname.endswith(".jsonl"):
                    continue
                incoming = load_jsonl(os.path.join(src_chat, fname))
                dst_f = os.path.join(CHAT_HISTORY_DIR, fname)
                existing = load_jsonl(dst_f)
                seen = set(m.get("event_id", "") for m in existing if m.get("event_id"))
                for m in incoming:
                    if not m.get("event_id"):
                        m["event_id"] = gen_uid()
                    if m["event_id"] in seen:
                        continue
                    existing.append(m)
                    seen.add(m["event_id"])
                save_jsonl(dst_f, existing)

        for sub in ["images", "videos", "documents"]:
            src_d = os.path.join(tmp_dir, sub)
            if not os.path.exists(src_d):
                continue
            dst_d = os.path.join(DATA_DIR, sub)
            os.makedirs(dst_d, exist_ok=True)
            for fname in os.listdir(src_d):
                src_f = os.path.join(src_d, fname)
                dst_f = os.path.join(dst_d, fname)
                if os.path.isfile(src_f) and not os.path.exists(dst_f):
                    try:
                        shutil.copy2(src_f, dst_f)
                        if sub == "images":
                            stats["images"] += 1
                    except BaseException:
                        pass

        for sub in ["content_lib"]:
            src_d = os.path.join(tmp_dir, sub)
            if not os.path.exists(src_d):
                continue
            dst_d = os.path.join(DATA_DIR, sub)
            os.makedirs(dst_d, exist_ok=True)
            for fname in os.listdir(src_d):
                src_f = os.path.join(src_d, fname)
                dst_f = os.path.join(dst_d, fname)
                if os.path.isfile(src_f) and not os.path.exists(dst_f):
                    shutil.copy2(src_f, dst_f)

        for fname in ["ai_config.json", "custom_skill.txt", "vocab_settings.json"]:
            src_f = os.path.join(tmp_dir, fname)
            dst_f = os.path.join(DATA_DIR, fname)
            if os.path.exists(src_f) and not os.path.exists(dst_f):
                shutil.copy2(src_f, dst_f)

        src_p = os.path.join(tmp_dir, "user_profile.json")
        dst_p = os.path.join(DATA_DIR, "user_profile.json")
        if os.path.exists(src_p):
            try:
                with open(src_p, "r", encoding="utf-8") as f:
                    sp = json.load(f)
                if os.path.exists(dst_p):
                    with open(dst_p, "r", encoding="utf-8") as f:
                        dp = json.load(f)
                else:
                    dp = {}
                for k in ["weak_subjects", "weak_knowledge", "error_types"]:
                    sd = sp.get(k, {}) or {}
                    dd = dp.get(k, {}) or {}
                    for kk, vv in sd.items():
                        if isinstance(vv, (int, float)):
                            dd[kk] = max(dd.get(kk, 0), vv)
                    dp[k] = dd
                skm = sp.get("knowledge_memory", {}) or {}
                dkm = dp.get("knowledge_memory", {}) or {}
                for kk, vv in skm.items():
                    if kk not in dkm:
                        dkm[kk] = vv
                    elif (vv.get("events", 0) or 0) > (dkm[kk].get("events", 0) or 0):
                        dkm[kk] = vv
                dp["knowledge_memory"] = dkm
                sem = sp.get("error_memory", []) or []
                dem = dp.get("error_memory", []) or []
                seen_em = set(e.get("timestamp") for e in dem if e.get("timestamp"))
                for e in sem:
                    ts = e.get("timestamp")
                    if ts and ts not in seen_em:
                        dem.append(e)
                        seen_em.add(ts)
                dp["error_memory"] = dem[-50:]
                dp["total_errors"] = max(dp.get("total_errors", 0), sp.get("total_errors", 0))
                dp["total_chats"] = max(dp.get("total_chats", 0), sp.get("total_chats", 0))
                with open(dst_p, "w", encoding="utf-8") as f:
                    json.dump(dp, f, ensure_ascii=False, indent=2)
            except BaseException:
                pass

        evs = load_jsonl(LEARNING_EVENTS_FILE)
        if len(evs) > 1000:
            archive_file = os.path.join(DATA_DIR, "learning_events_archive.jsonl")
            archive = load_jsonl(archive_file)
            archive.extend(evs[:-1000])
            save_jsonl(archive_file, archive)
            save_jsonl(LEARNING_EVENTS_FILE, evs[-1000:])

        return stats, None
    except Exception as e:
        return None, str(e)
    finally:
        try:
            if os.path.exists(tmp_dir):
                shutil.rmtree(tmp_dir)
        except BaseException:
            pass
def retry_request(max_retries=3, base_delay=2, backoff=2,
                  exceptions=(requests.exceptions.Timeout, requests.exceptions.ConnectionError)):
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_retries:
                        raise
                    delay = base_delay * (backoff ** attempt)
                    print(f"[重试] 第{attempt + 1}次失败，{delay}秒后重试... 错误: {e}")
                    time.sleep(delay)
                except Exception as e:
                    raise e
            raise last_exception
        return wrapper
    return decorator


def init_vocabulary():
    if not os.path.exists(VOCAB_FILE):
        with open(VOCAB_FILE, "w", encoding="utf-8") as f:
            pass


def load_jsonl(filepath):
    with _jsonl_lock:
        data = []
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            data.append(json.loads(line))
                        except BaseException:
                            pass
    return data


def save_jsonl(filepath, data_list):
    with _jsonl_lock:
        with open(filepath, "w", encoding="utf-8") as f:
            for item in data_list:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")

_vocab_cache = {"data": None, "ts": 0.0}
def load_vocab_cached(max_age=2.0):
    """词库短缓存：详情页高频打开时避免每次都全量读文件"""
    now = time.time()
    if _vocab_cache["data"] is not None and now - _vocab_cache["ts"] < max_age:
        return _vocab_cache["data"]
    data = load_jsonl(VOCAB_FILE)
    _vocab_cache["data"] = data
    _vocab_cache["ts"] = now
    return data

def migrate_timestamps():
    """一次性迁移：给所有历史数据补 event_id 和毫秒级 timestamp"""
    marker = os.path.join(DATA_DIR, ".migrated_v2")
    if os.path.exists(marker):
        return
    try:
        def _ensure(e):
            changed = False
            if not e.get("event_id"):
                e["event_id"] = gen_uid()
                changed = True
            ts = e.get("timestamp", 0)
            if isinstance(ts, (int, float)) and ts and ts < 10000000000:
                e["timestamp"] = int(ts) * 1000
                changed = True
            return changed

        targets = [
            ERRORS_FILE, NOTES_FILE, LEARNING_EVENTS_FILE, SENTENCES_FILE, TASKS_FILE,
            os.path.join(DATA_DIR, "learning_events_archive.jsonl"),
        ]
        for path in targets:
            if not os.path.exists(path):
                continue
            items = load_jsonl(path)
            changed = False
            for it in items:
                if _ensure(it):
                    changed = True
            if changed:
                save_jsonl(path, items)

        if os.path.exists(CHAT_HISTORY_DIR):
            for fname in os.listdir(CHAT_HISTORY_DIR):
                if not fname.endswith(".jsonl"):
                    continue
                fp = os.path.join(CHAT_HISTORY_DIR, fname)
                items = load_jsonl(fp)
                changed = False
                for it in items:
                    if not it.get("event_id"):
                        it["event_id"] = gen_uid()
                        changed = True
                    ts = it.get("timestamp", 0)
                    if isinstance(ts, (int, float)) and ts and ts < 10000000000:
                        it["timestamp"] = int(ts) * 1000
                        changed = True
                    elif not ts:
                        try:
                            dt = datetime.strptime(it.get("time", ""), "%Y-%m-%d %H:%M:%S")
                            it["timestamp"] = int(dt.timestamp() * 1000)
                            changed = True
                        except BaseException:
                            it["timestamp"] = now_ms()
                            changed = True
                if changed:
                    save_jsonl(fp, items)

        recycle = load_jsonl(RECYCLE_FILE)
        changed = False
        for r in recycle:
            ts = r.get("delete_ts", 0)
            if isinstance(ts, (int, float)) and ts and ts < 10000000000:
                r["delete_ts"] = int(ts) * 1000
                changed = True
            if not r.get("event_id"):
                r["event_id"] = gen_uid()
                changed = True
            d = r.get("data", {})
            if d and _ensure(d):
                changed = True
        if changed:
            save_jsonl(RECYCLE_FILE, recycle)

        with open(marker, "w", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S"))
    except BaseException as e:
        print(f"迁移失败：{e}")
def load_custom_skill():
    if os.path.exists(CUSTOM_SKILL_FILE):
        with open(CUSTOM_SKILL_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""


def save_custom_skill(text):
    with open(CUSTOM_SKILL_FILE, "w", encoding="utf-8") as f:
        f.write(text)


def log_learning_event(event_type, subject, kp="", detail="", correct=None, difficulty=None):
    event = {
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "timestamp": now_ms(),
        "event_id": gen_uid(),
        "type": event_type,
        "subject": subject,
        "kp": kp,
        "detail": detail[:500],
        "correct": correct,
        "difficulty": difficulty,
    }
    events = load_jsonl(LEARNING_EVENTS_FILE)
    events.append(event)
    if len(events) > 1000:
        archive_file = os.path.join(DATA_DIR, "learning_events_archive.jsonl")
        archive = load_jsonl(archive_file)
        archive.extend(events[:-1000])
        save_jsonl(archive_file, archive)
        events = events[-1000:]
    save_jsonl(LEARNING_EVENTS_FILE, events)


def update_knowledge_memory(kp, summary="", error_type=""):
    profile = load_user_profile()
    km = profile.get("knowledge_memory", {})
    if kp not in km:
        km[kp] = {"level": 0.3, "events": 0, "last_discussed": "", "summary": "", "error_types": []}
    km[kp]["events"] = km[kp].get("events", 0) + 1
    km[kp]["last_discussed"] = time.strftime("%Y-%m-%d")
    if summary:
        km[kp]["summary"] = summary[:200]
    if error_type and error_type not in km[kp].get("error_types", []):
        km[kp].setdefault("error_types", []).append(error_type)
    profile["knowledge_memory"] = km
    save_user_profile(profile)


def add_error_memory(subject, summary, knowledge_point="", discussed=False):
    profile = load_user_profile()
    em = profile.get("error_memory", [])
    em.append({
        "timestamp": now_ms(),
        "event_id": gen_uid(),
        "subject": subject,
        "summary": summary[:200],
        "knowledge_point": knowledge_point,
        "discussed": discussed
    })
    em = em[-50:]
    profile["error_memory"] = em
    save_user_profile(profile)


@retry_request(max_retries=2, base_delay=1)
def update_chat_memory(subject, user_msg, ai_response):
    def do_update():
        _cfg = load_ai_config()
        _provider = _cfg.get("provider", "zhipu")
        _info = PROVIDERS.get(_provider, PROVIDERS["zhipu"])
        api_key = _cfg.get(_info["key_field"], "").strip()
        if not api_key:
            return
        prompt = f"""请从以下对话中提取关键学习信息，返回JSON格式：
{{
  "topics": ["讨论的知识点1", "知识点2"],
  "weak_points": ["学生薄弱点1", "薄弱点2"],
  "summary": "本次对话核心内容摘要（一句话）"
}}
学科：{subject}
学生问题：{user_msg[:300]}
AI回答：{ai_response[:500]}
只返回JSON。"""
        try:
            resp = requests.post(_info["url"],
                                 headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                                 json={"model": _info["model"], "messages": [{"role": "user", "content": prompt}],
                                       "temperature": 0.3, "max_tokens": 300}, timeout=15)
            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"]
                try:
                    info = json.loads(content)
                except BaseException:
                    match = re.search(r'\{[^}]+\}', content)
                    info = json.loads(match.group()) if match else {}
                if info:
                    profile = load_user_profile()
                    memory = profile.get("chat_memory", {})
                    topics = info.get("topics", [])
                    for t in topics:
                        if t not in memory.get("recent_topics", []):
                            memory["recent_topics"].insert(0, t)
                    memory["recent_topics"] = memory["recent_topics"][:10]
                    weaks = info.get("weak_points", [])
                    for w in weaks:
                        if w not in memory.get("weak_points", []):
                            memory["weak_points"].append(w)
                    memory["weak_points"] = memory["weak_points"][:20]
                    if info.get("summary"):
                        memory["last_question_summary"] = info["summary"]
                    memory["last_update"] = time.strftime("%Y-%m-%d %H:%M:%S")
                    profile["chat_memory"] = memory
                    save_user_profile(profile)
                    for t in topics[:2]:
                        update_knowledge_memory(f"{subject}-{t}", summary=info.get("summary", ""))
                    log_learning_event("chat", subject, kp=topics[0] if topics else "",
                                       detail=user_msg[:80])
        except BaseException:
            pass
    threading.Thread(target=do_update, daemon=True).start()


def get_memory_context(subject=None):
    profile = load_user_profile()
    parts = []
    km = profile.get("knowledge_memory", {})
    filtered_km = {k: v for k, v in km.items() if k.startswith(f"{subject}-")} if subject else km
    if filtered_km:
        sorted_km = sorted(filtered_km.items(), key=lambda x: x[1].get("events", 0), reverse=True)[:5]
        lines = []
        for kp, info in sorted_km:
            level = info.get("level", 0.3)
            summary = info.get("summary", "")
            line = f"- {kp}（掌握度 {level:.2f}，事件 {info.get('events', 0)} 次）"
            if summary:
                line += f"：{summary}"
            lines.append(line)
        parts.append("【知识点记忆】\n" + "\n".join(lines))
    em = profile.get("error_memory", [])
    if subject:
        em = [e for e in em if e.get("subject") == subject]
    if em:
        recent_em = em[-5:]
        lines = [f"- [{e.get('subject', '')}] {e.get('summary', '')}" for e in recent_em]
        parts.append("【错题内容记忆（最近5条）】\n" + "\n".join(lines))
    chat_mem = profile.get("chat_memory", {})
    if chat_mem.get("recent_topics"):
        parts.append(f"【近期讨论话题】{', '.join(chat_mem['recent_topics'][:5])}")
    if chat_mem.get("weak_points"):
        parts.append(f"【薄弱点】{', '.join(chat_mem['weak_points'][:5])}")
    if chat_mem.get("last_question_summary"):
        parts.append(f"【上次问题】{chat_mem['last_question_summary']}")
    error_types = profile.get("error_types", {})
    if error_types:
        top_et = sorted(error_types.items(), key=lambda x: x[1], reverse=True)[:3]
        parts.append(f"【高频错因】{', '.join(f'{k}({v}次)' for k, v in top_et)}")
    return "\n\n".join(parts) if parts else ""


_TEXTBOOK_CACHE = {}

def load_textbook_index(subject):
    if subject in _TEXTBOOK_CACHE:
        return _TEXTBOOK_CACHE[subject]
    fp = os.path.join(DATA_DIR, "textbook_index", f"{subject}.json")
    if not os.path.exists(fp):
        return None
    try:
        with open(fp, "r", encoding="utf-8") as f:
            idx = json.load(f)
        _TEXTBOOK_CACHE[subject] = idx
        return idx
    except BaseException:
        return None


def search_textbook(subject, query, top=3):
    """教材知识库检索：TF 关键词打分，返回最相关的教材章节块"""
    idx = load_textbook_index(subject)
    if not idx:
        return ""
    blocks = idx.get("blocks", [])
    if not blocks or not query:
        return ""
    q_words = [w for w in re.split(r"[\s，。；、：？！,.!?;:（）()\"\"''《》<>\[\]【】+-]", query)
               if len(w) >= 2]
    scored = []
    for b in blocks:
        t = b.get("text", "")
        s = 0
        for w in q_words:
            s += t.count(w)
        if s > 0:
            scored.append((s, b))
    scored.sort(key=lambda x: -x[0])
    parts = []
    for s, b in scored[:top]:
        parts.append(f"[{b.get('book', '')} P{b.get('pages', '')}]\n{b.get('text', '')[:1200]}")
    return "\n\n".join(parts)


def get_teaching_strategy(subject):
    profile = load_user_profile()
    error_types = profile.get("error_types", {})
    if not error_types:
        return ""
    top = sorted(error_types.items(), key=lambda x: x[1], reverse=True)
    strategy_map = {
        "计算错误": "多强调计算步骤，提醒逐项检查",
        "概念不清": "先讲清概念本质，再讲题",
        "审题偏差": "先带读题，划关键词",
        "公式遗忘": "先复习相关公式，再套用",
        "方法错误": "对比正确方法和错误方法，讲清为什么",
        "其他": "多举例，循序渐进",
    }
    lines = []
    for et, count in top[:3]:
        if et in strategy_map:
            lines.append(f"- 学生常犯「{et}」（{count}次），讲题时{strategy_map[et]}")
    return "【讲题策略】\n" + "\n".join(lines) if lines else ""


def get_profile_summary():
    p = load_user_profile()
    ws = sorted(p["weak_subjects"].items(), key=lambda x: x[1], reverse=True)[:3]
    wk = sorted(p["weak_knowledge"].items(), key=lambda x: x[1], reverse=True)[:5]
    s = "【学习画像】\n"
    if ws:
        s += f"薄弱学科：{'、'.join(f'{a}({b:.1f})' for a, b in ws)}\n"
    if wk:
        s += f"薄弱知识点：{'、'.join(f'{a}({b:.1f})' for a, b in wk)}\n"
    s += f"总错题：{p['total_errors']} | 总对话：{p['total_chats']}"
    return s


def analyze_knowledge_framework():
    errors = load_jsonl(ERRORS_FILE)
    ec = {}
    for e in errors:
        ec[e.get("subject", "未知")] = ec.get(e.get("subject", "未知"), 0) + 1
    p = load_user_profile()
    p["total_errors"] = len(errors)
    save_user_profile(p)
    return {"error_counts": ec, "total_errors": len(errors)}


def load_user_profile():
    if not os.path.exists(USER_PROFILE_FILE):
        return {
            "name": "学生", "grade": "高三",
            "weak_subjects": {}, "weak_knowledge": {},
            "error_types": {}, "recent_focus": [],
            "total_errors": 0, "total_chats": 0,
            "chat_memory": {"last_update": "", "recent_topics": [], "weak_points": [],
                            "discussed_errors": [], "last_question_summary": ""},
            "knowledge_memory": {}, "error_memory": [],
            "subject_profile": {}
        }
    with open(USER_PROFILE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        data.setdefault("name", "学生")
        data.setdefault("grade", "高三")
        data.setdefault("weak_subjects", {})
        data.setdefault("weak_knowledge", {})
        data.setdefault("error_types", {})
        data.setdefault("recent_focus", [])
        data.setdefault("total_errors", 0)
        data.setdefault("total_chats", 0)
        data.setdefault("knowledge_memory", {})
        data.setdefault("error_memory", [])
        data.setdefault("subject_profile", {})
        if "chat_memory" not in data:
            data["chat_memory"] = {"last_update": "", "recent_topics": [], "weak_points": [],
                                   "discussed_errors": [], "last_question_summary": ""}
        else:
            cm = data["chat_memory"]
            cm.setdefault("last_update", "")
            cm.setdefault("recent_topics", [])
            cm.setdefault("weak_points", [])
            cm.setdefault("discussed_errors", [])
            cm.setdefault("last_question_summary", "")
        return data


def save_user_profile(profile):
    with open(USER_PROFILE_FILE, "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)


def update_weak_subject(subject, w=0.1):
    p = load_user_profile()
    p["weak_subjects"][subject] = min(1.0, p["weak_subjects"].get(subject, 0) + w)
    save_user_profile(p)


def update_weak_knowledge(kp, w=0.1):
    p = load_user_profile()
    p["weak_knowledge"][kp] = min(1.0, p["weak_knowledge"].get(kp, 0) + w)
    save_user_profile(p)


def update_chat_stats(subject):
    p = load_user_profile()
    p["total_chats"] += 1
    save_user_profile(p)


def update_subject_profile(subject, question="", is_question=True):
    """对话后完善个人画像：学科问答计数 + 最近问题摘要 + 知识点关注提取。"""
    if not subject or subject == "总AI":
        return
    p = load_user_profile()
    sp = p.setdefault("subject_profile", {})
    rec = sp.setdefault(subject, {"asked": 0, "recent_questions": [],
                                  "topics": [], "mistake_themes": []})
    rec["asked"] = rec.get("asked", 0) + 1
    q = (question or "").strip()
    if q:
        rec["recent_questions"].insert(0, q[:80])
        rec["recent_questions"] = rec["recent_questions"][:8]
        # 从问题/错题文本里抓学科主题词（2-4字连续中文片段，取高频）
        frags = re.findall(r"[\u4e00-\u9fa5]{2,4}", q)
        topics = [f for f in frags if not f.endswith(("什么", "怎么", "为什么", "多少", "一下", "这个", "那个"))]
        for t in topics[:4]:
            if t not in rec["topics"]:
                rec["topics"].append(t)
        rec["topics"] = rec["topics"][:20]
    p["chat_memory"]["last_question_summary"] = q[:100] if q else p["chat_memory"].get("last_question_summary", "")
    p["chat_memory"]["last_update"] = time.strftime("%Y-%m-%d %H:%M")
    save_user_profile(p)


def profile_to_prompt_text(profile, subject=None):
    """把个人画像转成给 AI 的自然语言摘要（具体、可执行）。"""
    parts = []
    # 学科画像
    sp = profile.get("subject_profile", {})
    if sp:
        if subject and subject != "总AI" and subject in sp:
            rec = sp[subject]
            parts.append(f"【你在{subject}上的画像】累计问过{rec.get('asked', 0)}个问题")
            if rec.get("recent_questions"):
                parts.append("最近问过：" + "；".join(rec["recent_questions"][:5]))
            if rec.get("topics"):
                parts.append("常涉及知识点/题型：" + "、".join(rec["topics"][:12]))
        else:
            parts.append("【跨学科画像】" + "；".join(
                f"{k}（问过{v.get('asked', 0)}题，关注：{'、'.join(v.get('topics', [])[:6]) or '无'}"
                for k, v in list(sp.items())[:6]))
    # 薄弱知识点
    wk = profile.get("weak_knowledge", {})
    if wk:
        weak_items = sorted(wk.items(), key=lambda x: -x[1])[:8]
        parts.append("薄弱知识点（按强度）：" + "、".join(f"{k}({v:.0%})" for k, v in weak_items))
    # 错误类型
    et = profile.get("error_types", {})
    if et:
        top_et = sorted(et.items(), key=lambda x: -x[1])[:5]
        parts.append("高频错误类型：" + "、".join(f"{k}×{v}" for k, v in top_et))
    # 最近关注
    rf = profile.get("recent_focus", [])
    if rf:
        parts.append("最近在攻克：" + "、".join(rf[:5]))
    if profile.get("total_errors"):
        parts.append(f"错题本累计 {profile['total_errors']} 道")
    if profile.get("total_chats"):
        parts.append(f"累计 AI 对话 {profile['total_chats']} 次")
    if not parts:
        return ""
    return "【学生个人画像（基于历史对话与错题自动完善，请据此个性化教学）】\n" + "\n".join(parts)


def add_recent_focus(kp):
    p = load_user_profile()
    if kp not in p["recent_focus"]:
        p["recent_focus"].insert(0, kp)
        p["recent_focus"] = p["recent_focus"][:10]
        save_user_profile(p)


def load_ai_config():
    _defaults = {"provider": "zhipu", "model": "free", "api_key_free": "", "api_key_deepseek": "",
                 "api_key_enhanced": "", "monthly_limit": 5.0, "subject_models": {},
                 "deepseek_model": "deepseek-flash", "deepseek_thinking": True,
                 "ctx_chars": "auto"}
    if not os.path.exists(AI_CONFIG_FILE):
        return _defaults
    with open(AI_CONFIG_FILE, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    for _k, _v in _defaults.items():
        cfg.setdefault(_k, _v)
    # 旧模型名自动迁移 → deepseek-flash（DeepSeek-V4.1-Flash-1017）
    _dm = cfg.get("deepseek_model", "")
    if _dm in ("", "deepseek-chat", "deepseek-reasoner", "deepseek-v4-flash", "deepseek-v4-flash-vision-exp"):
        cfg["deepseek_model"] = "deepseek-flash"
    return cfg


def save_ai_config(config):
    with open(AI_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


PROVIDERS = {
    "zhipu": {
        "name": "智谱 GLM",
        "url": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        "model": "glm-4-flash",
        "vision_model": "glm-4v-flash",
        "key_field": "api_key_free",
        "supports_vision": True,
    },
    "deepseek": {
        "name": "DeepSeek",
        "url": "https://api.deepseek.com/chat/completions",
        # deepseek-flash = DeepSeek-V4.1-Flash-1017（官方最新），原生支持图片理解
        "model": "deepseek-flash",
        "vision_model": "deepseek-flash",
        "key_field": "api_key_deepseek",
        "supports_vision": True,
    },
}


def get_api_endpoint():
    cfg = load_ai_config()
    provider = cfg.get("provider", "zhipu")
    info = PROVIDERS.get(provider, PROVIDERS["zhipu"])
    key = cfg.get(info["key_field"], "").strip()
    model = info["model"]
    if provider == "deepseek":
        # DeepSeek 支持自定义模型：deepseek-chat / deepseek-reasoner / 新版模型 ID
        model = (cfg.get("deepseek_model") or "deepseek-v4-flash").strip() or "deepseek-v4-flash"
    return key, info["url"], model, info["vision_model"]


def endpoint_for(task="smart"):
    """DeepTutor 式任务分工：
    cheap → 免费模型（打标签/错题自动分析/单词补齐/金句/诊断）
    smart → 增强模型（AI 对话/深度分析/难度出题/今日计划）
    增强 key 缺省时依次回退 DeepSeek、免费模型。"""
    cfg = load_ai_config()
    provider = cfg.get("provider", "zhipu")
    info = PROVIDERS.get(provider, PROVIDERS["zhipu"])
    if task == "cheap":
        key = cfg.get(info["key_field"], "").strip()
        return key, info["url"], info["model"], info.get("vision_model", "")
    key_enh = cfg.get("api_key_enhanced", "").strip()
    if key_enh:
        zi = PROVIDERS["zhipu"]
        return key_enh, zi["url"], "glm-4-air", zi.get("vision_model", "")
    key_ds = cfg.get("api_key_deepseek", "").strip()
    if key_ds:
        dk = PROVIDERS["deepseek"]
        model = (cfg.get("deepseek_model") or "deepseek-v4-flash").strip() or "deepseek-v4-flash"
        return key_ds, dk["url"], model, dk.get("vision_model", "")
    return endpoint_for("cheap")


def provider_supports_vision():
    cfg = load_ai_config()
    provider = cfg.get("provider", "zhipu")
    return PROVIDERS.get(provider, PROVIDERS["zhipu"]).get("supports_vision", False)


# —— DeepSeek 自研网络搜索 / 网页抓取（Search & Fetch API，官方文档 guides/search）——
def deepseek_search(query, count=5):
    """DeepSeek Search：自研搜索引擎，返回结构化结果。失败返回 None。"""
    cfg = load_ai_config()
    key = cfg.get("api_key_deepseek", "").strip()
    if not key:
        return None
    try:
        r = requests.post(
            "https://api.deepseek.com/v1/tools/search",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"query": (query or "")[:128], "count": count, "need_content": False},
            timeout=15)
        if r.status_code != 200:
            return None
        results = r.json().get("results", [])
        lines = []
        for it in results[:count]:
            title = it.get("title", "")
            url = it.get("url", "")
            summary = it.get("summary", "") or it.get("snippet", "")
            if not title and not summary:
                continue
            lines.append(f"- {title}\n  {summary[:200]}\n  来源: {url}")
        return "\n".join(lines) if lines else None
    except BaseException:
        return None


def deepseek_fetch(url):
    """DeepSeek Fetch：抓取单个网页为 Markdown。失败返回 None。"""
    cfg = load_ai_config()
    key = cfg.get("api_key_deepseek", "").strip()
    if not key:
        return None
    try:
        r = requests.post(
            "https://api.deepseek.com/v1/tools/fetch",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"url": url[:8192]},
            timeout=15)
        if r.status_code != 200:
            return None
        return r.json().get("content", "")[:3000]
    except BaseException:
        return None


def deepseek_enrich(query, force=False):
    """按用户消息做联网增强：含 URL → 抓取网页；否则 → 网络搜索。返回注入文本或空串。
    force=True（对话页联网开关开启）时无条件搜索。"""
    urls = re.findall(r"https?://[^\s]+", query)
    if urls:
        content = deepseek_fetch(urls[0])
        if content:
            return f"【用户提到的网页内容（已自动抓取，请优先参考）】\n{content}"
        return ""
    if not force:
        # 联网意图检测：显式词或时效性问题
        _intent = re.search(r"(联网|搜索一下|查一下|最新|今天|本周|今年|新闻|实时|天气|比赛|发布|上市)", query)
        if not _intent:
            return ""
    res = deepseek_search(query)
    if res:
        return f"【DeepSeek 实时联网结果（请基于这些信息回答，并注明来源链接）】\n{res}"
    return ""


# 对话页"联网搜索"开关状态（默认开启，像官方 App 一样）
_WEB_SEARCH_ON = {"on": True}


def get_chat_history_file(subject):
    safe = re.sub(r'[\\/*?:"<>|]', "_", subject)
    return os.path.join(CHAT_HISTORY_DIR, f"chat_{safe}.jsonl")


def load_chat_history(subject):
    return load_jsonl(get_chat_history_file(subject))


def save_chat_message(subject, role, content):
    fp = get_chat_history_file(subject)
    data = load_jsonl(fp)
    data.append({"role": role, "content": content,
                 "time": time.strftime("%Y-%m-%d %H:%M:%S"),
                 "timestamp": now_ms(), "event_id": gen_uid()})
    save_jsonl(fp, data)


def move_to_recycle(item):
    recycle = load_jsonl(RECYCLE_FILE)
    recycle.append({
        "original_type": item.get("type"), "data": item,
        "delete_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "delete_ts": now_ms(), "event_id": gen_uid(),
    })
    save_jsonl(RECYCLE_FILE, recycle)


def restore_from_recycle(delete_ts):
    recycle, target, keep = load_jsonl(RECYCLE_FILE), None, []
    for item in recycle:
        if item.get("delete_ts", 0) == delete_ts:
            target = item
        else:
            keep.append(item)
    if target:
        save_jsonl(RECYCLE_FILE, keep)
        d, t = target.get("data", {}), target.get("original_type", "")
        if t == "error":
            errors = load_jsonl(ERRORS_FILE)
            errors.append(d)
            save_jsonl(ERRORS_FILE, errors)
        elif t == "note":
            notes = load_jsonl(NOTES_FILE)
            notes.append(d)
            save_jsonl(NOTES_FILE, notes)
        return True
    return False


def empty_recycle():
    save_jsonl(RECYCLE_FILE, [])


def copy_file_to_lib(src_path, target_dir, allowed_exts):
    if not os.path.exists(src_path):
        return ""
    ext = os.path.splitext(src_path)[1].lower()
    if ext not in allowed_exts:
        return ""
    new_name = str(uuid.uuid4().hex) + ext
    dst = os.path.join(target_dir, new_name)
    shutil.copy(src_path, dst)
    return dst


IMG_EXTS = [".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp"]
VIDEO_EXTS = [".mp4", ".mov", ".avi", ".mkv", ".flv", ".wmv"]
DOC_EXTS = [".pdf", ".doc", ".docx", ".txt", ".md", ".ppt", ".pptx", ".xls", ".xlsx"]


def save_error(subject, original="", original_media=None, answer="", answer_media=None,
               mistake="", idea="", idea_media=None, manual_tags=""):
    if original_media is None:
        original_media = []
    if answer_media is None:
        answer_media = []
    if idea_media is None:
        idea_media = []
    user_tags = [t.strip() for t in manual_tags.split(",") if t.strip()] if manual_tags.strip() else []
    data = load_jsonl(ERRORS_FILE)
    seen = set()
    question_media = []
    for m in original_media:
        if m not in seen:
            seen.add(m)
            question_media.append(m)
    entry = {
        "type": "error", "subject": subject, "original": original, "original_media": original_media,
        "answer": answer, "answer_media": answer_media, "mistake": mistake, "idea": idea,
        "idea_media": idea_media, "question": original, "question_media": question_media,
        "tags": [subject] + user_tags if user_tags else [subject],
        "error_type": "", "difficulty": 0, "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "timestamp": now_ms(), "event_id": gen_uid(),
        "deep_analysis": "", "status": "未看",
        "tags_done": bool(user_tags)
    }
    data.append(entry)
    save_jsonl(ERRORS_FILE, data)
    log_learning_event("error_upload", subject, kp="",
                       detail=f"上传错题：{original[:80]} | 错因：{mistake[:60]}")
    if not user_tags:
        threading.Thread(target=auto_tag_error, args=(entry["timestamp"],), daemon=True).start()


@retry_request(max_retries=3, base_delay=2)
def auto_tag_error(timestamp):
    errors = load_jsonl(ERRORS_FILE)
    target = None
    for err in errors:
        if err.get("timestamp") == timestamp:
            target = err
            break
    if not target:
        return
    content_parts = []
    if target.get("original"):
        content_parts.append(f"题目：{target['original']}")
    if target.get("mistake"):
        content_parts.append(f"学生错误：{target['mistake']}")
    if target.get("idea"):
        content_parts.append(f"学生见解：{target['idea']}")
    if target.get("answer"):
        content_parts.append(f"标准答案：{target['answer']}")
    content_text = "\n".join(content_parts)
    if not content_text:
        return
    api_key, api_url, api_model, _v = endpoint_for("cheap")
    if not api_key:
        return
    prompt = f"""你是一个专业的高中老师。请给下面这道错题打尽量多且精准的标签。

标签要覆盖以下角度（每个角度都可打多个，不必每道题都齐，但多多益善）：
- 知识点（如：二次函数、导数应用、电磁感应、非谓语动词）
- 题型（如：求最值、证明题、实验题、选择题）
- 易错点（如：忽略定义域、符号错误、单位漏写、时态混用）
- 方法（如：配方法、数形结合、控制变量法、排除法）
- 难度（如：基础、中档、压轴）
- 陷阱（如：分类讨论遗漏、隐含条件、干扰项设计）

要求：
- 至少 8 个标签，最多 30 个，每个都必须精准有用，不要凑数
- 每个标签 2-8 个字，简洁
- 不要重复
- 不要出现"数学""题目""易错"这种泛泛无意义的词
- 标签越具体越好（如"氧化还原配平"好于"化学"）

题目内容：
{content_text[:600]}

返回 JSON：
{{"tags": ["标签1", "标签2", "标签3", "标签4", "标签5", "标签6", "标签7", "标签8"], "error_type": "计算错误/概念不清/审题偏差/公式遗忘/方法错误/其他", "difficulty": 1-5, "reason": "简短错误分析"}}
只输出 JSON。"""
    try:
        resp = requests.post(api_url,
                             headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                             json={"model": api_model, "messages": [{"role": "user", "content": prompt}],
                                   "temperature": 0.3, "max_tokens": 500}, timeout=30)
        if resp.status_code == 200:
            content = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            try:
                tag_data = json.loads(content)
            except BaseException:
                match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
                tag_data = json.loads(match.group()) if match else {}
            subject = target.get("subject", "")
            ai_tags = tag_data.get("tags", [])
            if not isinstance(ai_tags, list):
                ai_tags = []
            ai_tags = [str(t).strip() for t in ai_tags if str(t).strip()]
            tags = [subject]
            for t in ai_tags:
                if t and t != subject and t not in tags:
                    tags.append(t)
            if len(tags) <= 1:
                fallback_kp = extract_keywords_fallback(content_text)
                if fallback_kp:
                    tags.append(fallback_kp)
            tags = tags[:30]
            error_type = tag_data.get("error_type", "")
            difficulty = tag_data.get("difficulty", 0)
            errors = load_jsonl(ERRORS_FILE)
            for err in errors:
                if err.get("timestamp") == timestamp:
                    err["tags"] = tags
                    err["error_type"] = error_type
                    err["difficulty"] = difficulty
                    err["tags_done"] = True
                    break
            save_jsonl(ERRORS_FILE, errors)
            if subject:
                update_weak_subject(subject, 0.1)
            kp_main = tags[1] if len(tags) > 1 else ""
            if kp_main:
                update_weak_knowledge(f"{subject}-{kp_main}", 0.15)
                update_knowledge_memory(f"{subject}-{kp_main}",
                                        summary=tag_data.get("reason", ""), error_type=error_type)
                log_learning_event("error_analyzed", subject, kp=kp_main,
                                   detail=tag_data.get("reason", ""), difficulty=difficulty)
            if error_type:
                profile = load_user_profile()
                profile["error_types"][error_type] = profile["error_types"].get(error_type, 0) + 1
                save_user_profile(profile)
            if kp_main:
                add_recent_focus(f"{subject}-{kp_main}")
    except BaseException:
        pass


def save_note(subject, content, media):
    data = load_jsonl(NOTES_FILE)
    data.append({"type": "note", "subject": subject, "content": content, "media": media,
                 "time": time.strftime("%Y-%m-%d %H:%M:%S"), "timestamp": int(time.time())})
    save_jsonl(NOTES_FILE, data)
    log_learning_event("note_upload", subject, detail=f"上传笔记：{content[:80] if content else '（图片笔记）'}")
    # 带图笔记：后台让 AI 自动理解图片内容，写回 ai_text（不阻塞上传）
    if media:
        try:
            import threading as _th

            def _understand(note_ts):
                try:
                    notes2 = load_jsonl(NOTES_FILE)
                    for n in notes2:
                        if n.get("timestamp") == note_ts and not n.get("ai_text"):
                            txt = vision_describe_image(n.get("media", [])[0])
                            if txt:
                                n["ai_text"] = txt
                                save_jsonl(NOTES_FILE, notes2)
                                break
                except BaseException:
                    pass

            _th.Thread(target=_understand, args=(data[-1].get("timestamp"),), daemon=True).start()
        except BaseException:
            pass


def _note_sort_key(x):
    """笔记排序键：timestamp 可能缺失/字符串/旧格式，统一转 float，兜底解析 time。"""
    ts = x.get("timestamp", 0)
    if isinstance(ts, (int, float)):
        return float(ts)
    if isinstance(ts, str) and ts.strip().isdigit():
        return float(ts)
    t = x.get("time", "") or x.get("created_at", "")
    if isinstance(t, str) and t.strip():
        try:
            return time.mktime(time.strptime(t[:19], "%Y-%m-%d %H:%M:%S"))
        except (ValueError, TypeError):
            pass
    return 0.0


def pick_relevant_notes(query, subject=None, limit=4):
    """按关键词检索相关笔记，供 AI 对话引用（类似错题检索）。"""
    notes = load_jsonl(NOTES_FILE)
    if subject and subject != "总AI":
        notes = [n for n in notes if n.get("subject") == subject]
    if not notes:
        return []
    kws = [k.lower() for k in re.findall(r"[\u4e00-\u9fa5]{2,}|[a-zA-Z]{3,}", query or "")]
    scored = []
    for n in notes:
        s = 0.0
        text = (str(n.get("content", "")) + " " + " ".join(str(t) for t in n.get("tags", []))).lower()
        for kw in kws:
            if kw and kw in text:
                s += 3
        if s > 0:
            scored.append((s, n))
    scored.sort(key=lambda x: -x[0])
    return [n for _, n in scored[:limit]]


# ============ 学科思维导图（XMind 式 + 结合错题本） ============
def mindmap_file(subject):
    return os.path.join(DATA_DIR, "mindmaps", f"{subject}.json")


def load_mindmap(subject):
    p = mindmap_file(subject)
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except BaseException:
            pass
    return None


def save_mindmap(subject, tree):
    d = os.path.join(DATA_DIR, "mindmaps")
    os.makedirs(d, exist_ok=True)
    with open(mindmap_file(subject), "w", encoding="utf-8") as f:
        json.dump(tree, f, ensure_ascii=False, indent=2)


def build_mindmap(subject):
    """从错题自动聚类生成学科知识树；已有人工编辑的树则增量合并新知识点。"""
    errors = load_jsonl(ERRORS_FILE)
    subj_errors = [e for e in errors if e.get("subject") == subject]
    # 按知识点标签聚类（每个错题的主要标签）
    clusters = {}
    for e in subj_errors:
        tags = [str(t) for t in e.get("tags", []) if str(t).strip()] or ["未分类"]
        main_tag = tags[0]
        kp = (e.get("kp") or main_tag).strip()
        clusters.setdefault(kp, {"title": kp, "children": [], "kp": kp, "count": 0})
        clusters[kp]["count"] += 1
    # 分层：每个知识点节点下自动挂「笔记层 / 错题层」两个子层（像导航分层）
    for kp, nd in clusters.items():
        nd.setdefault("children", []).insert(0, {"title": "📓 笔记", "kind": "notes", "kp": kp})
        nd.setdefault("children", []).append({"title": "📕 错题", "kind": "errors", "kp": kp})
    # 一级主题：优先用学科常见模块名兜底
    root_children = []
    for kp in sorted(clusters.keys()):
        root_children.append(clusters[kp])
    tree = {"title": subject, "children": root_children}
    # 与已有手动树合并：保留已有结构，补充新聚类出来的知识点
    old = load_mindmap(subject)
    if old and old.get("children"):
        old_titles = {c.get("title") for c in old["children"]}
        for c in root_children:
            if c["title"] not in old_titles:
                old["children"].append(c)
        # 已有节点也补充新错题计数 + 补齐分层子节点
        old_by_title = {c.get("title"): c for c in old["children"]}
        for c in root_children:
            if c["title"] in old_by_title:
                nd0 = old_by_title[c["title"]]
                nd0["count"] = c.get("count", 0)
                kinds = {x.get("kind") for x in nd0.get("children", [])}
                if "notes" not in kinds:
                    nd0.setdefault("children", []).insert(0, {"title": "📓 笔记", "kind": "notes", "kp": c["title"]})
                if "errors" not in kinds:
                    nd0.setdefault("children", []).append({"title": "📕 错题", "kind": "errors", "kp": c["title"]})
        tree = old
    save_mindmap(subject, tree)
    return tree


@retry_request(max_retries=3, base_delay=2)
def generate_word_info(word):
    api_key, api_url, api_model, _v = endpoint_for("cheap")
    if not api_key:
        return None
    prompt = f"""请为英语单词 "{word}" 生成词条信息，格式为 JSON：
{{
    "word": "{word}",
    "phonetic": "音标",
    "meaning": "中文释义",
    "example": "一个例句",
    "forms": "变形",
    "grammar": {{"collocations": [], "notes": [], "test_points": []}},
    "phrases": []
}}
只返回 JSON 对象。"""
    try:
        resp = requests.post(api_url,
                             headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                             json={"model": api_model, "messages": [{"role": "user", "content": prompt}],
                                   "temperature": 0.3, "max_tokens": 600}, timeout=20)
        if resp.status_code == 200:
            content = resp.json()["choices"][0]["message"]["content"]
            try:
                new_data = json.loads(content)
            except BaseException:
                match = re.search(r'\{.*\}', content, re.S)
                new_data = json.loads(match.group()) if match else None
            if new_data:
                new_data.setdefault("phonetic", "")
                new_data.setdefault("meaning", "")
                new_data.setdefault("example", "")
                new_data.setdefault("forms", "")
                new_data.setdefault("grammar", {})
                new_data.setdefault("phrases", [])
                return new_data
    except Exception as e:
        print(f"[生成] 异常 {word}: {e}")
    return None


def load_sentences():
    return load_jsonl(SENTENCES_FILE)


def save_sentences(sentences):
    save_jsonl(SENTENCES_FILE, sentences)


def add_sentence(category, sentence, translation="", favorite=False):
    sentences = load_sentences()
    new_id = max([s.get("id", 0) for s in sentences]) + 1 if sentences else 1
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    sentences.append({"id": new_id, "category": category, "sentence": sentence,
                      "translation": translation, "favorite": favorite,
                      "created": now, "updated": now,
                      "timestamp": now_ms(), "event_id": gen_uid()})
    save_sentences(sentences)
    return new_id


def delete_sentence(sentence_id):
    sentences = [s for s in load_sentences() if s.get("id") != sentence_id]
    save_sentences(sentences)


def toggle_favorite(sentence_id):
    sentences = load_sentences()
    for s in sentences:
        if s.get("id") == sentence_id:
            s["favorite"] = not s.get("favorite", False)
            break
    save_sentences(sentences)


def update_sentence(sentence_id, category=None, sentence=None, translation=None):
    sentences = load_sentences()
    for s in sentences:
        if s.get("id") == sentence_id:
            if category is not None:
                s["category"] = category
            if sentence is not None:
                s["sentence"] = sentence
            if translation is not None:
                s["translation"] = translation
            s["updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
            break
    save_sentences(sentences)


def extract_keywords_fallback(text):
    if not text:
        return ""
    patterns = [
        (r'二次函数', '二次函数'), (r'一次函数', '一次函数'),
        (r'反比例函数', '反比例函数'), (r'指数函数', '指数函数'),
        (r'对数函数', '对数函数'), (r'三角函数', '三角函数'),
        (r'数列', '数列'), (r'导数', '导数'), (r'不等式', '不等式'),
        (r'立体几何', '立体几何'), (r'解析几何', '解析几何'),
        (r'概率', '概率'), (r'排列组合', '排列组合'),
        (r'集合', '集合'), (r'复数', '复数'),
        (r'向量', '向量'), (r'圆锥曲线', '圆锥曲线'),
        (r'牛顿|力学', '力学'), (r'电场|电路|电流|欧姆', '电学'),
        (r'磁场|电磁', '电磁学'), (r'运动学|匀变速', '运动学'),
        (r'动量', '动量'), (r'动能|机械能', '机械能'),
        (r'热学|热力学', '热学'), (r'光学|折射|反射', '光学'),
        (r'氧化还原', '氧化还原'), (r'离子方程', '离子方程式'),
        (r'化学平衡', '化学平衡'), (r'有机化学|烃|醇|酸', '有机化学'),
        (r'摩尔|物质的量', '物质的量'),
        (r'定语从句', '定语从句'), (r'状语从句', '状语从句'),
        (r'名词性从句', '名词性从句'), (r'虚拟语气', '虚拟语气'),
        (r'时态', '时态'), (r'非谓语', '非谓语动词'),
        (r'文言文', '文言文'), (r'诗歌鉴赏', '诗歌鉴赏'),
        (r'阅读理解', '阅读理解'), (r'作文', '作文'),
        (r'遗传|基因|DNA|RNA', '遗传学'), (r'细胞', '细胞'),
        (r'光合作用', '光合作用'), (r'呼吸作用', '呼吸作用'),
        (r'生态系统', '生态系统'),
        (r'近代史|鸦片战争|戊戌|辛亥', '中国近代史'),
        (r'古代史|先秦|秦汉|唐宋', '中国古代史'),
        (r'经济生活', '经济生活'), (r'政治生活', '政治生活'),
        (r'文化生活', '文化生活'), (r'哲学', '哲学'),
        (r'气候|季风|气压', '气候'), (r'地形|地貌', '地形'),
        (r'人口|城市|城市化', '人文地理'),
    ]
    for pattern, kp in patterns:
        if re.search(pattern, text):
            return kp
    return ""
def pick_relevant_errors(query, subject=None, limit=5):
    errors = load_jsonl(ERRORS_FILE)
    if subject and subject != "总AI":
        errors = [e for e in errors if e.get("subject") == subject]
    if not errors:
        return []
    kws = [k.lower() for k in (query or "").split() if k.strip()]
    scored = []
    for e in errors:
        s = 0.5
        tags = " ".join(str(t) for t in e.get("tags", [])).lower()
        text = ((e.get("original", "") or e.get("question", "")) + " " + str(e.get("mistake", ""))).lower()
        for kw in kws:
            if kw and kw in tags:
                s += 5
            if kw and kw in text:
                s += 2
        scored.append((s, e))
    scored.sort(key=lambda x: -x[0])
    return [e for _, e in scored[:limit]]
def weighted_search_errors(items, query):
    """多关键词加权搜索错题。返回 (按分数降序的items, 分数map)"""
    if not query or not query.strip():
        return items, {}
    keywords = [k.strip().lower() for k in query.split() if k.strip()]
    if not keywords:
        return items, {}
    scored = []
    for idx, item in enumerate(items):
        tags = [str(t).lower() for t in item.get("tags", [])]
        original = str(item.get("original", "") or item.get("question", "")).lower()
        mistake = str(item.get("mistake", "")).lower()
        total_score = 0
        for kw in keywords:
            kw_score = 0
            hit_tags = []
            for tag in tags:
                if kw == tag:
                    kw_score += 10
                    hit_tags.append(tag)
                elif kw in tag or tag in kw:
                    kw_score += 6
                    hit_tags.append(tag)
            if kw in original:
                kw_score += 3
            if kw in mistake:
                kw_score += 2
            if kw_score > 0 and len(hit_tags) >= 2:
                kw_score += 2
            total_score += kw_score
        if total_score > 0:
            scored.append((idx, total_score))
    if not scored:
        return [], {}
    scored.sort(key=lambda x: -x[1])
    ordered_items = [items[i] for i, _ in scored]
    score_map = {i: s for i, s in scored}
    return ordered_items, score_map
def _svg_bar(title, labels, values, unit=""):
    n = len(labels)
    if n == 0:
        return ""
    W, H = 660, 380
    pad_l, pad_r, pad_t, pad_b = 60, 40, 60, 80
    cw = W - pad_l - pad_r
    ch = H - pad_t - pad_b
    max_v = max(values) if values else 1
    max_v = max(max_v, 1)
    bar_w = cw / n * 0.6
    gap = cw / n
    colors = ["#7AA2F7", "#BB9AF7", "#9ECE6A", "#E0AF68", "#73DACA",
              "#DB9DF7", "#F7768E", "#E1C7FA", "#A9B1D6"]
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="sans-serif">',
         f'<rect width="{W}" height="{H}" fill="#1A1B26" rx="16"/>',
         f'<text x="{W/2}" y="34" fill="#EEEEEE" font-size="17" font-weight="bold" text-anchor="middle">{title}</text>']
    for i in range(5):
        y = pad_t + ch * i / 4
        v = max_v * (4 - i) / 4
        p.append(f'<line x1="{pad_l}" y1="{y}" x2="{W-pad_r}" y2="{y}" stroke="#2A2E44" stroke-width="1"/>')
        p.append(f'<text x="{pad_l-8}" y="{y+4}" fill="#777777" font-size="10" text-anchor="end">{v:.0f}{unit}</text>')
    for i, (lb, v) in enumerate(zip(labels, values)):
        x = pad_l + gap * i + (gap - bar_w) / 2
        bh = ch * (v / max_v) if max_v else 0
        y = pad_t + ch - bh
        c = colors[i % len(colors)]
        p.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{bh:.1f}" fill="{c}" rx="5"/>')
        p.append(f'<text x="{x+bar_w/2:.1f}" y="{y-6:.1f}" fill="#EEEEEE" font-size="12" font-weight="bold" text-anchor="middle">{v}</text>')
        lb2 = lb if len(lb) <= 6 else lb[:6]
        p.append(f'<text x="{x+bar_w/2:.1f}" y="{H-pad_b+22}" fill="#CCCCCC" font-size="12" text-anchor="middle">{lb2}</text>')
    p.append('</svg>')
    return "".join(p)


def _svg_pie(title, items):
    import math
    if not items:
        return ""
    W, H = 660, 400
    cx, cy, r, r2 = 220, 220, 120, 72
    total = sum(it.get("value", 0) for it in items) or 1
    colors = ["#7AA2F7", "#BB9AF7", "#9ECE6A", "#E0AF68", "#73DACA",
              "#DB9DF7", "#F7768E", "#E1C7FA", "#A9B1D6"]
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="sans-serif">',
         f'<rect width="{W}" height="{H}" fill="#1A1B26" rx="16"/>',
         f'<text x="{W/2}" y="34" fill="#EEEEEE" font-size="17" font-weight="bold" text-anchor="middle">{title}</text>']
    angle = -math.pi / 2
    for i, it in enumerate(items):
        frac = it.get("value", 0) / total
        a2 = angle + frac * 2 * math.pi
        x1 = cx + r * math.cos(angle); y1 = cy + r * math.sin(angle)
        x2 = cx + r * math.cos(a2); y2 = cy + r * math.sin(a2)
        x3 = cx + r2 * math.cos(a2); y3 = cy + r2 * math.sin(a2)
        x4 = cx + r2 * math.cos(angle); y4 = cy + r2 * math.sin(angle)
        large = 1 if frac > 0.5 else 0
        d = f"M {x1:.1f} {y1:.1f} A {r} {r} 0 {large} 1 {x2:.1f} {y2:.1f} L {x3:.1f} {y3:.1f} A {r2} {r2} 0 {large} 0 {x4:.1f} {y4:.1f} Z"
        c = colors[i % len(colors)]
        p.append(f'<path d="{d}" fill="{c}"/>')
        angle = a2
    p.append(f'<text x="{cx}" y="{cy-2}" fill="#EEEEEE" font-size="24" font-weight="bold" text-anchor="middle">{int(total)}</text>')
    p.append(f'<text x="{cx}" y="{cy+20}" fill="#888888" font-size="12" text-anchor="middle">总计</text>')
    ly = 110
    for i, it in enumerate(items):
        c = colors[i % len(colors)]
        p.append(f'<rect x="420" y="{ly-12}" width="14" height="14" fill="{c}" rx="3"/>')
        p.append(f'<text x="444" y="{ly}" fill="#CCCCCC" font-size="13">{it.get("name","")}</text>')
        p.append(f'<text x="620" y="{ly}" fill="#EEEEEE" font-size="13" text-anchor="end">{it.get("value",0)}</text>')
        ly += 30
    p.append('</svg>')
    return "".join(p)


def _svg_timeline(title, events):
    if not events:
        return ""
    W = 660
    n = len(events)
    row_h = 88
    H = 100 + n * row_h
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="sans-serif">',
         f'<rect width="{W}" height="{H}" fill="#1A1B26" rx="16"/>',
         f'<text x="{W/2}" y="36" fill="#EEEEEE" font-size="17" font-weight="bold" text-anchor="middle">{title}</text>',
         f'<line x1="130" y1="70" x2="130" y2="{H-30}" stroke="#414868" stroke-width="2"/>']
    for i, ev in enumerate(events):
        y = 90 + i * row_h
        p.append(f'<circle cx="130" cy="{y}" r="7" fill="#7AA2F7"/>')
        p.append(f'<circle cx="130" cy="{y}" r="13" fill="none" stroke="#7AA2F7" stroke-opacity="0.3" stroke-width="2"/>')
        p.append(f'<text x="108" y="{y+4}" fill="#888888" font-size="11" text-anchor="end">{ev.get("date","")}</text>')
        p.append(f'<text x="160" y="{y-2}" fill="#EEEEEE" font-size="14" font-weight="bold">{ev.get("title","")}</text>')
        desc = ev.get("desc", "")
        if len(desc) > 42:
            desc = desc[:42] + "..."
        p.append(f'<text x="160" y="{y+18}" fill="#AAAAAA" font-size="12">{desc}</text>')
    p.append('</svg>')
    return "".join(p)


def _svg_flow(title, steps):
    if not steps:
        return ""
    n = len(steps)
    card_w, card_h, gap = 138, 116, 16
    W = 40 + n * card_w + (n - 1) * gap + 40
    H = 250
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="sans-serif">',
         f'<rect width="{W}" height="{H}" fill="#1A1B26" rx="16"/>',
         f'<text x="{W/2}" y="38" fill="#EEEEEE" font-size="17" font-weight="bold" text-anchor="middle">{title}</text>']
    sm = {"ok": ("#1E3A22", "#66BB6A", "✓"),
          "warn": ("#3A3418", "#E0AF68", "!"),
          "err": ("#3A1E1E", "#EF5350", "✗"),
          "none": ("#2A2A32", "#888888", "·")}
    for i, st in enumerate(steps):
        x = 40 + i * (card_w + gap)
        y = 76
        bg, border, mark = sm.get(st.get("status", "none"), sm["none"])
        p.append(f'<rect x="{x}" y="{y}" width="{card_w}" height="{card_h}" rx="14" fill="{bg}" stroke="{border}" stroke-width="1.5"/>')
        p.append(f'<text x="{x+14}" y="{y+26}" fill="{border}" font-size="13" font-weight="bold">{i+1} {mark}</text>')
        label = st.get("label", "")
        if len(label) > 9:
            label = label[:9]
        p.append(f'<text x="{x+14}" y="{y+52}" fill="#EEEEEE" font-size="14" font-weight="bold">{label}</text>')
        desc = st.get("desc", "")
        l1 = desc[:15]
        l2 = desc[15:30]
        p.append(f'<text x="{x+14}" y="{y+74}" fill="#AAAAAA" font-size="11">{l1}</text>')
        if l2:
            p.append(f'<text x="{x+14}" y="{y+90}" fill="#AAAAAA" font-size="11">{l2}</text>')
        if i < n - 1:
            ax = x + card_w
            ay = y + card_h / 2
            p.append(f'<path d="M {ax} {ay} L {ax+gap-4} {ay} L {ax+gap-9} {ay-5} M {ax+gap-4} {ay} L {ax+gap-9} {ay+5}" stroke="#555" stroke-width="1.5" fill="none"/>')
    p.append('</svg>')
    return "".join(p)


def render_chart_from_spec(spec):
    t = spec.get("type", "")
    title = spec.get("title", "")
    try:
        if t == "bar":
            return _svg_bar(title, spec.get("labels", []), spec.get("values", []), spec.get("unit", ""))
        if t == "pie":
            return _svg_pie(title, spec.get("items", []))
        if t == "timeline":
            return _svg_timeline(title, spec.get("events", []))
        if t == "flow":
            return _svg_flow(title, spec.get("steps", []))
    except BaseException:
        return ""
    return ""


def extract_chart_block(text):
    if not text:
        return text, None
    m = re.search(r'```chart\s*\n(.*?)```', text, re.DOTALL | re.IGNORECASE)
    if m:
        raw = m.group(1).strip()
        clean = (text[:m.start()] + text[m.end():]).strip()
        try:
            spec = json.loads(raw)
            svg = render_chart_from_spec(spec)
            if svg:
                return clean, svg
        except BaseException:
            pass
        return clean, None
    m = re.search(r'```(svg|xml)\s*\n(.*?)```', text, re.DOTALL | re.IGNORECASE)
    if m and "<svg" in m.group(2).lower():
        return (text[:m.start()] + text[m.end():]).strip(), m.group(2).strip()
    m2 = re.search(r'(<svg[\s\S]*?</svg>)', text, re.IGNORECASE)
    if m2:
        return (text[:m2.start()] + text[m2.end():]).strip(), m2.group(1).strip()
    return text, None


def build_ctx(history, max_chars=50000, per_msg_cap=1500):
    """按字符预算从历史中取最近的对话，尽量多带上下文。
    返回按时间正序的消息列表（每条截断到 per_msg_cap 字符）。"""
    ctx = []
    total = 0
    for msg in reversed(history):
        c = msg.get("content", "")
        if not isinstance(c, str) or not c.strip():
            continue
        c = c[:per_msg_cap]
        if total + len(c) > max_chars:
            break
        total += len(c)
        ctx.append({"role": msg["role"], "content": c})
    ctx.reverse()
    return ctx


# ============ 长记忆：滚动摘要（早期对话自动压缩，长期保存） ============
def memory_file():
    return os.path.join(DATA_DIR, "ai_memory.json")


def load_ai_memory():
    if os.path.exists(memory_file()):
        try:
            with open(memory_file(), "r", encoding="utf-8") as f:
                return json.load(f)
        except BaseException:
            pass
    return {}


def save_ai_memory(mem):
    try:
        with open(memory_file(), "w", encoding="utf-8") as f:
            json.dump(mem, f, ensure_ascii=False, indent=2)
    except BaseException:
        pass


def get_subject_summary(subject):
    """返回该科已压缩的早期对话摘要（用于注入 system prompt）。"""
    mem = load_ai_memory()
    rec = mem.get(subject) or {}
    return rec.get("summary", "")


def compress_old_history(subject, hist):
    """历史过长时，把早期对话交给 AI 压缩成摘要，长期保存（异步调用方自行处理）。
    返回压缩条数；无需压缩返回 0。"""
    try:
        total = sum(len(m.get("content", "") or "") for m in hist)
        if total < 40000:
            return 0
        mem = load_ai_memory()
        rec = mem.setdefault(subject, {"summary": "", "count": 0})
        compressed = rec.get("count", 0)
        remain = hist[compressed:]
        # 至少积累 8 条新消息才压缩一次，且每次只压新增的一半
        if len(remain) < 8:
            return 0
        batch = remain[: max(8, len(remain) // 2)]
        text = "\n".join(
            ("学生说：" if m.get("role") == "user" else "老师答：") + str(m.get("content", ""))[:600]
            for m in batch)
        key, url, model, _v = endpoint_for("cheap")
        if not key:
            return 0
        prompt = ("你是学习助手的记忆压缩器。把下面这段师生对话压缩成不超过500字的中文摘要，"
                  "必须保留：①学生问过的具体知识点/题型/题目关键词 ②AI给出的关键方法、结论、公式或思路 "
                  "③学生暴露的薄弱点/常错点。只输出摘要正文，不要任何前缀。\n\n" + text[:12000])
        r = requests.post(url, headers={"Authorization": f"Bearer {key}",
                                        "Content-Type": "application/json"},
                          json={"model": model, "messages": [{"role": "user", "content": prompt}],
                                "temperature": 0.3, "max_tokens": 800}, timeout=30)
        if r.status_code != 200:
            return 0
        c = r.json()["choices"][0]["message"]["content"].strip()
        if not c:
            return 0
        # 合并：旧摘要 + 新摘要（旧的在前面），控制总长
        old = rec.get("summary", "")
        if old:
            rec["summary"] = (old + "\n" + c)[-3000:]
        else:
            rec["summary"] = c[:3000]
        rec["count"] = compressed + len(batch)
        save_ai_memory(mem)
        return len(batch)
    except BaseException:
        return 0


# ============ AI 读图理解：笔记/错题照片自动识别并融入知识体系 ============
def vision_describe_image(img_path):
    """让视觉模型概括一张图片（笔记/题目），返回 ≤90 字理解文本；失败返回空串。"""
    try:
        key, url, model, vision_model = endpoint_for("cheap")
        if not key or not vision_model:
            return ""
        full = img_path if os.path.isabs(img_path) else os.path.join(DATA_DIR, img_path)
        if not os.path.exists(full):
            return ""
        with open(full, "rb") as f:
            raw = f.read()
        # 压缩到长边 1280 以内，控制请求体大小
        try:
            import PIL.Image as _PI
            import io as _io
            im = _PI.open(_io.BytesIO(raw))
            im.thumbnail((1280, 1280))
            buf = _io.BytesIO()
            im.convert("RGB").save(buf, format="JPEG", quality=82)
            raw = buf.getvalue()
        except BaseException:
            pass
        b64 = base64.b64encode(raw).decode("utf-8")
        payload = {"model": vision_model, "temperature": 0.3, "max_tokens": 200,
                   "messages": [{"role": "user", "content": [
                       {"type": "text",
                        "text": "请用不超过90字概括这张图片：①是笔记还是题目？②关键知识点/考点是什么？③如果是题目，核心思路一句话。只输出概括，不要前缀。"},
                       {"type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}]}]}
        r = requests.post(url, headers={"Authorization": f"Bearer {key}",
                                        "Content-Type": "application/json"},
                          json=payload, timeout=30)
        if r.status_code != 200:
            return ""
        c = r.json()["choices"][0]["message"]["content"].strip()
        return c[:200]
    except BaseException:
        return ""


def auto_understand_media(subject, limit=12):
    """批量让 AI 理解该科所有笔记/错题里的图片，结果写入 ai_text 字段。
    返回本次理解条数；无新图片或失败返回 0。"""
    done = 0
    # 笔记图片
    notes = load_jsonl(NOTES_FILE)
    for n in notes:
        if done >= limit:
            break
        if n.get("subject") != subject:
            continue
        if n.get("ai_text"):
            continue
        imgs = n.get("media", []) or n.get("images", [])
        if not imgs:
            continue
        txt = vision_describe_image(imgs[0])
        if txt:
            n["ai_text"] = txt
            done += 1
    if done:
        save_jsonl(NOTES_FILE, notes)
    # 错题图片
    errors = load_jsonl(ERRORS_FILE)
    e_done = 0
    for e in errors:
        if done >= limit:
            break
        if e.get("subject") != subject:
            continue
        if e.get("ai_text"):
            continue
        imgs = e.get("images", []) or e.get("media", [])
        if not imgs:
            continue
        txt = vision_describe_image(imgs[0])
        if txt:
            e["ai_text"] = txt
            done += 1
            e_done += 1
    if e_done:
        save_jsonl(ERRORS_FILE, errors)
    return done


def save_svg_chart(svg_text):
    """把 SVG 图表存成文件，返回路径；失败返回 None"""
    try:
        svg_dir = os.path.join(DATA_DIR, "charts")
        os.makedirs(svg_dir, exist_ok=True)
        fname = f"chart_{int(time.time()*1000)}.svg"
        fpath = os.path.join(svg_dir, fname)
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(svg_text)
        return fpath
    except BaseException:
        return None


def clean_latex(text):
    superscript_map = {'0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴', '5': '⁵',
                       '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
                       '+': '⁺', '-': '⁻', '=': '⁼', '(': '⁽', ')': '⁾', 'n': 'ⁿ', 'i': 'ⁱ'}
    subscript_map = {'0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄', '5': '₅',
                     '6': '₆', '7': '₇', '8': '₈', '9': '₉',
                     '+': '₊', '-': '₋', '=': '₌', '(': '₍', ')': '₎', 'x': 'ₓ', 'a': 'ₐ', 'e': 'ₑ', 'n': 'ₙ'}
    symbol_map = {r'\pi': 'π', r'\theta': 'θ', r'\alpha': 'α', r'\beta': 'β', r'\gamma': 'γ',
                  r'\delta': 'δ', r'\Delta': 'Δ', r'\lambda': 'λ', r'\mu': 'μ', r'\sigma': 'σ',
                  r'\omega': 'ω', r'\infty': '∞', r'\pm': '±', r'\sqrt': '√', r'\times': '×',
                  r'\cdot': '·', r'\div': '÷', r'\leq': '≤', r'\geq': '≥', r'\neq': '≠',
                  r'\approx': '≈', r'\sum': '∑', r'\int': '∫', r'\partial': '∂', r'\angle': '∠',
                  r'\triangle': '△', r'\perp': '⊥', r'\rightarrow': '→', r'\Rightarrow': '⇒'}

    def sup_repl(match):
        return ''.join(superscript_map.get(c, c) for c in match.group(1))

    def sub_repl(match):
        return ''.join(subscript_map.get(c, c) for c in match.group(1))

    text = re.sub(r'\^\{([^}]+)\}', sup_repl, text)
    text = re.sub(r'\_\{([^}]+)\}', sub_repl, text)
    text = re.sub(r'\^(\d+)', lambda m: ''.join(superscript_map.get(c, c) for c in m.group(1)), text)
    text = re.sub(r'\_(\d+)', lambda m: ''.join(subscript_map.get(c, c) for c in m.group(1)), text)
    for latex, unicode_char in symbol_map.items():
        text = text.replace(latex, unicode_char)
    return text.strip()


def convert_chemical_formula(text):
    text = re.sub(r'([A-Z][a-z]?)(\d+[+-])(?![^{])', lambda m: f"{m.group(1)}^{{{m.group(2)}}}", text)
    text = re.sub(r'([A-Z][a-z]?)([+-])(?![^{])', lambda m: f"{m.group(1)}^{{{m.group(2)}}}", text)
    text = re.sub(r'\)(\d+)(?![_{])', r')_{\1}', text)
    text = re.sub(r'([A-Z][a-z]?)(\d+)(?![_{^])', lambda m: f"{m.group(1)}_{{{m.group(2)}}}", text)
    return text


CONTENT_LIB_FILES = {
    "语文": "chinese.json", "数学": "math.json", "英语": "english.json",
    "物理": "physics.json", "化学": "chemistry.json", "生物": "biology.json",
    "历史": "history.json", "政治": "politics.json", "地理": "geography.json",
}


def init_content_lib():
    defaults = {
        "语文": {"subject": "语文", "poems": [], "classical_chinese": [], "writing_templates": []},
        "数学": {"subject": "数学", "formulas": [], "question_types": [], "common_mistakes": []},
        "英语": {"subject": "英语", "core_vocabulary": [], "grammar_points": [], "writing_patterns": []},
        "物理": {"subject": "物理", "formulas": [], "models": [], "experiments": []},
        "化学": {"subject": "化学", "equations": [], "principles": [], "experiments": []},
        "生物": {"subject": "生物", "concepts": [], "processes": [], "experiments": []},
        "历史": {"subject": "历史", "timeline": [], "causal_chains": [], "figures": []},
        "政治": {"subject": "政治", "core_concepts": [], "answer_templates": []},
        "地理": {"subject": "地理", "map_points": [], "principles": [], "regions": []},
    }
    for subject, filename in CONTENT_LIB_FILES.items():
        filepath = os.path.join(CONTENT_LIB_DIR, filename)
        if not os.path.exists(filepath):
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(defaults.get(subject, {"subject": subject}), f, ensure_ascii=False, indent=2)


def load_content_lib(subject):
    filename = CONTENT_LIB_FILES.get(subject)
    if not filename:
        return {"subject": subject}
    filepath = os.path.join(CONTENT_LIB_DIR, filename)
    if not os.path.exists(filepath):
        init_content_lib()
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except BaseException:
        return {"subject": subject}


def main(page: ft.Page):
    page.padding = 0
    page.spacing = 0
    try:
        splash_view = ft.Container(
            content=ft.Image(src="splash.png", fit=ft.ImageFit.COVER, expand=True),
            expand=True,
            bgcolor="#131318",
            alignment=ft.alignment.center,
        )
        page.add(splash_view)
        page.update()
        time.sleep(0.6)
        page.controls.clear()
        page.update()
    except Exception as splash_err:
        print(f"splash 加载失败：{splash_err}")
    page.add(ft.Text("⏳ 应用启动中..."))
    page.update()
    print("=== main 函数开始 ===")

    try:
        for d in [DATA_DIR, IMAGES_DIR, VIDEOS_DIR, DOCS_DIR, CHAT_HISTORY_DIR, CONTENT_LIB_DIR]:
            os.makedirs(d, exist_ok=True)
        print("数据目录:", DATA_DIR)

        init_vocabulary()
        init_content_lib()
        migrate_timestamps()

        def load_ui():
            page.controls.clear()
            page.update()
            print("=== load_ui 开始 ===")
            app_state = {"busy": None}

            is_mobile = page.platform in [ft.PagePlatform.ANDROID, ft.PagePlatform.IOS]
            if not is_mobile:
                page.window.width = 900
                page.window.height = 700
                page.window.min_width = 360
                page.window.min_height = 450
            else:
                page.window.width = None
                page.window.min_width = 320
                page.padding = 0
                page.spacing = 0
            page.title = "池鱼Study"
            page.responsive = True
            page.theme_mode = ft.ThemeMode.DARK
            # 全局毛玻璃底色：深紫蓝渐变，配合各处的半透明 blur 卡片
            page.bgcolor = ft.Colors.TRANSPARENT
            try:
                page.window.title_bar_hidden = False
            except BaseException:
                pass

            try:
                # 苹果风组件主题：全局限一次生效（按钮/输入框/卡片/弹窗/底部导航）
                _shared_btn_style = ft.ButtonStyle(
                    shape=ft.RoundedRectangleBorder(radius=14),
                    padding=ft.Padding(left=20, right=20, top=12, bottom=12),
                    elevation=0.5,
                    overlay_color="#267AA2F7",
                )
                page.theme = ft.Theme(
                    font_family="Segoe UI, -apple-system, Roboto, sans-serif",
                    color_scheme=ft.ColorScheme(
                        primary="#7AA2F7",        # Tokyo Night 蓝紫（主操作色）
                        primary_container="#24283B",
                        secondary="#BB9AF7",      # 紫（辅助强调）
                        tertiary="#73DACA",
                        surface="#1A1B26",
                        surface_variant="#24283B",
                        background="#16161E",
                        on_surface="#C0CAF5",
                        on_background="#C0CAF5",
                    ),
                    visual_density=ft.VisualDensity.STANDARD,
                    navigation_bar_theme=ft.NavigationBarThemeData(
                        background_color="#D914141C",
                        indicator_color="#7AA2F7",
                        height=72,
                    ),
                    elevated_button_theme=ft.ElevatedButtonThemeData(style=_shared_btn_style),
                    text_button_theme=ft.TextButtonThemeData(style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=12),
                        padding=ft.Padding(left=16, right=16, top=10, bottom=10))),
                    input_decoration_theme=ft.InputDecorationThemeData(
                        filled=True, fill_color="#CC1F1F26",
                        border_radius=14, border=ft.border.all(1, "#414868")),
                    card_theme=ft.CardThemeData(
                        color="#B31A1B26", elevation=6,
                        shape=ft.RoundedRectangleBorder(radius=18)),
                    dialog_theme=ft.DialogThemeData(
                        backgroundColor="#F21A1B26", elevation=24,
                        shape=ft.RoundedRectangleBorder(radius=26)),
                    snack_bar_theme=ft.SnackBarThemeData(
                        bgcolor="#E61A1B26", elevation=6,
                        shape=ft.RoundedRectangleBorder(radius=14)),
                )
                page.dark_theme = page.theme
            except BaseException:
                pass

            main_subject_page = None
            subject_page_content = ft.Container(expand=True)

            def show_toast(text, color="green", duration=1.6):
                if color == "green":
                    bg = "#337AA2F7"   # Tokyo Night 蓝紫（正向反馈）
                    icon = "✅"
                elif color == "red":
                    bg = "#33EF5350"
                    icon = "❌"
                else:
                    bg = "#33E0AF68"
                    icon = "ℹ️"

                toast = ft.Container(
                    content=ft.Row([
                        ft.Text(icon, size=22),
                        ft.Text(text, size=16, color=ft.Colors.WHITE, weight=ft.FontWeight.W_500),
                    ], spacing=10, tight=True, alignment=ft.MainAxisAlignment.CENTER),
                    bgcolor=bg,
                    blur=30,
                    border_radius=26,
                    padding=ft.Padding(left=30, right=30, top=16, bottom=16),
                    border=ft.border.all(1, "#44FFFFFF"),
                    shadow=ft.BoxShadow(blur_radius=36, color="#88000000",
                                        offset=ft.Offset(0, 8)),
                    opacity=0,
                    offset=ft.Offset(0, 0.3),
                    animate_opacity=ft.Animation(350, ft.AnimationCurve.EASE_OUT),
                    animate_offset=ft.Animation(350, ft.AnimationCurve.EASE_OUT_BACK),
                )
                page.overlay.append(toast)
                try:
                    w = page.width or (page.window.width if page.window else None) or 360
                except Exception:
                    w = 360
                try:
                    h = page.height or (page.window.height if page.window else None) or 640
                except Exception:
                    h = 640
                toast.left = max((w - 240) / 2, 10)
                toast.top = max((h - 100) / 2, 10)
                page.update()
                time.sleep(0.05)
                toast.opacity = 1
                toast.offset = ft.Offset(0, 0)
                page.update()

                def fade_out():
                    time.sleep(duration)
                    toast.opacity = 0
                    toast.offset = ft.Offset(0, 0.3)
                    page.update()
                    time.sleep(0.4)
                    try:
                        page.overlay.remove(toast)
                    except BaseException:
                        pass
                    page.update()

                threading.Thread(target=fade_out, daemon=True).start()

            def show_message(target_text, text, color="green"):
                target_text.value = text
                target_text.color = color
                page.update()
                threading.Thread(
                    target=lambda: (time.sleep(2), setattr(target_text, 'value', ''), page.update()),
                    daemon=True
                ).start()

            def show_image_gallery(image_paths, start_index=0, on_close=None):
                if not image_paths:
                    return

                valid_paths = []
                for p in image_paths:
                    full = p if os.path.isabs(p) else os.path.join(DATA_DIR, p)
                    if os.path.exists(full):
                        valid_paths.append(full)

                if not valid_paths:
                    show_toast("图片不存在", "red")
                    return

                if start_index >= len(valid_paths):
                    start_index = 0

                total = len(valid_paths)
                state = {"index": start_index}

                img_ctrl = ft.Image(src=valid_paths[start_index], fit=ft.ImageFit.CONTAIN)
                image_view = ft.InteractiveViewer(
                    content=img_ctrl,
                    min_scale=1.0,
                    max_scale=6.0,
                    pan_enabled=True,
                    scale_enabled=True,
                    expand=True,
                )

                counter_text = ft.Text(
                    f"{start_index+1} / {total}",
                    size=12,
                    color="#FFFFFF",
                    weight=ft.FontWeight.W_500,
                )

                def close_gallery(e=None):
                    try:
                        page.close(gallery_dlg)
                    except BaseException:
                        pass
                    if on_close:
                        try:
                            def _delayed():
                                time.sleep(0.15)
                                try:
                                    on_close()
                                except BaseException:
                                    pass
                            threading.Thread(target=_delayed, daemon=True).start()
                        except BaseException:
                            pass

                def update_image(idx):
                    if 0 <= idx < total:
                        state["index"] = idx
                        img_ctrl.src = valid_paths[idx]
                        counter_text.value = f"{idx+1} / {total}"
                        refresh_thumbs()
                        try:
                            page.update()
                        except BaseException:
                            pass

                def open_in_system(e):
                    try:
                        idx = state["index"]
                        p = valid_paths[idx]
                        page.launch_url(f"file://{p}")
                    except Exception as ex:
                        show_toast(f"打开失败：{str(ex)[:40]}", "red")

                close_btn = ft.Container(
                    content=ft.Icon(ft.Icons.CLOSE, size=22, color="#FFFFFF"),
                    width=44, height=44, border_radius=22,
                    bgcolor="#88000000",
                    alignment=ft.alignment.center,
                    on_click=close_gallery,
                    ink=True,
                )

                open_btn = ft.Container(
                    content=ft.Icon(ft.Icons.OPEN_IN_NEW, size=20, color="#FFFFFF"),
                    width=44, height=44, border_radius=22,
                    bgcolor="#88000000",
                    alignment=ft.alignment.center,
                    on_click=open_in_system,
                    ink=True,
                )

                thumbs_row = ft.Row(spacing=8, scroll=ft.ScrollMode.AUTO)

                def refresh_thumbs():
                    thumbs_row.controls.clear()
                    for i, p in enumerate(valid_paths):
                        is_active = (i == state["index"])
                        thumb = ft.Container(
                            content=ft.Image(src=p, width=44, height=44, fit=ft.ImageFit.COVER),
                            width=48, height=48,
                            border_radius=8,
                            border=ft.border.all(2, "#7AA2F7" if is_active else "#555555"),
                            on_click=lambda e, idx=i: update_image(idx),
                            ink=True,
                        )
                        thumbs_row.controls.append(thumb)

                refresh_thumbs()

                bottom_bar = ft.Container(
                    content=ft.Row([
                        counter_text,
                        ft.Container(width=10),
                        ft.Container(content=thumbs_row, expand=True),
                    ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    bgcolor="#66000000",
                    blur=10,
                    border_radius=14,
                    padding=ft.Padding(left=14, right=14, top=8, bottom=8),
                )

                try:
                    w = page.width or (page.window.width if page.window else None) or 400
                    h = page.height or (page.window.height if page.window else None) or 800
                except Exception:
                    w, h = 400, 800

                gallery_dlg = ft.AlertDialog(
                    content=ft.Container(
                        content=ft.Stack([
                            ft.Container(
                                content=image_view,
                                left=0, top=0, right=0, bottom=0,
                            ),
                            ft.Container(
                                content=close_btn,
                                left=14, top=14,
                            ),
                            ft.Container(
                                content=open_btn,
                                right=14, top=14,
                            ),
                            ft.Container(
                                content=bottom_bar,
                                left=14, right=14, bottom=20,
                            ),
                        ], expand=True),
                        bgcolor="#EE000000",
                        width=w,
                        height=h,
                    ),
                    inset_padding=ft.Padding(0, 0, 0, 0),
                    content_padding=0,
                    title_padding=0,
                    actions=[],
                    actions_padding=0,
                )

                page.open(gallery_dlg)
                page.update()
            def show_chart_overlay(svg_or_html):
                try:
                    content = svg_or_html.strip()
                    if content == "ECHARTS_UNSUPPORTED" or "<html" in content.lower() or "<script" in content.lower():
                        show_toast("Android 版暂不支持 ECharts，请让 AI 输出 SVG", "red")
                        return
                    if "<svg" not in content.lower():
                        show_toast("不是有效的 SVG", "red")
                        return
                    svg_dir = os.path.join(DATA_DIR, "charts")
                    os.makedirs(svg_dir, exist_ok=True)
                    fname = f"chart_{int(time.time()*1000)}.svg"
                    fpath = os.path.join(svg_dir, fname)
                    with open(fpath, "w", encoding="utf-8") as f:
                        f.write(content)
                    dlg = ft.AlertDialog(
                        title=ft.Text("📊 图表"),
                        content=ft.Container(
                            content=ft.InteractiveViewer(
                                content=ft.Image(src=fpath, fit=ft.ImageFit.CONTAIN),
                                min_scale=1.0, max_scale=6.0,
                                pan_enabled=True, scale_enabled=True, expand=True,
                            ),
                            width=420, height=620, bgcolor="#1A1B26",
                        ),
                        actions=[ft.TextButton("关闭", on_click=lambda e: page.close(dlg))],
                    )
                    page.open(dlg)
                    page.update()
                except Exception as ex:
                    show_toast(f"渲染失败：{str(ex)[:40]}", "red")

            sync_status_text = ft.Text("", size=14)
            sync_folder_picker = ft.FilePicker(on_result=lambda e: on_sync_folder_selected(e))
            page.overlay.append(sync_folder_picker)

            def on_sync_folder_selected(e: ft.FilePickerResultEvent):
                if e.path:
                    update_data_dir(e.path)
                    try:
                        page.client_storage.set("data_path", e.path)
                    except BaseException:
                        pass
                    sync_status_text.value = f"✅ 已切换到：{e.path}"
                    sync_status_text.color = "green"
                    page.update()
                    refresh_tasks()
                    refresh_recycle()
                    nonlocal main_subject_page
                    main_subject_page = build_subject_page()
                    subject_page_content.content = main_subject_page
                    page.update()
                    show_toast(f"数据已切换到 {e.path}")

            def make_file_picker_button(button_text, allowed_types="image", on_complete=None):
                selected_files = []
                file_list = ft.Column(spacing=4)
                picker = ft.FilePicker(on_result=lambda e: handle_picker_result(e))
                page.overlay.append(picker)
                progress_row = ft.Row(visible=False, spacing=10)
                progress_bar = ft.ProgressBar(width=200, height=8, value=0)
                progress_text = ft.Text("0%", size=14)
                progress_row.controls.extend([progress_bar, progress_text])

                def refresh_file_list():
                    file_list.controls.clear()
                    row = ft.Row(spacing=8, scroll=ft.ScrollMode.AUTO)
                    for idx, f_path in enumerate(selected_files):
                        try:
                            img = ft.Image(src=f_path, width=60, height=60,
                                           fit=ft.ImageFit.COVER, border_radius=8)
                        except BaseException:
                            img = ft.Text("🖼️", size=40)
                        del_btn = ft.IconButton(icon=ft.Icons.CLOSE, icon_size=16,
                                                on_click=lambda e, i=idx: remove_file(i))
                        col = ft.Column([img, del_btn], spacing=2,
                                        horizontal_alignment=ft.CrossAxisAlignment.CENTER)
                        row.controls.append(col)
                    file_list.controls.append(row)
                    complete_btn.disabled = len(selected_files) == 0
                    page.update()

                def handle_picker_result(e: ft.FilePickerResultEvent):
                    if e.files:
                        for f in e.files:
                            ext = os.path.splitext(f.name)[1].lower()
                            saved = None
                            if ext in IMG_EXTS and allowed_types in ["image", "all"]:
                                saved = copy_file_to_lib(f.path, IMAGES_DIR, IMG_EXTS)
                            elif ext in VIDEO_EXTS and allowed_types in ["video", "all"]:
                                saved = copy_file_to_lib(f.path, VIDEOS_DIR, VIDEO_EXTS)
                            elif ext in DOC_EXTS and allowed_types in ["document", "all"]:
                                saved = copy_file_to_lib(f.path, DOCS_DIR, DOC_EXTS)
                            if saved:
                                selected_files.append(saved)
                        refresh_file_list()
                        show_toast(f"已添加 {len(e.files)} 个文件", "green")

                def remove_file(idx):
                    if 0 <= idx < len(selected_files):
                        selected_files.pop(idx)
                        refresh_file_list()

                def pick_files(e):
                    picker.pick_files(file_type=ft.FilePickerFileType.IMAGE, allow_multiple=True)

                complete_btn = ft.ElevatedButton(
                    "✅ 完成上传", icon=ft.Icons.DONE,
                    on_click=lambda e: on_complete(selected_files) if on_complete else None,
                    disabled=True, visible=False,
                )

                def reset():
                    selected_files.clear()
                    file_list.controls.clear()
                    complete_btn.disabled = True
                    progress_row.visible = False
                    page.update()

                return ft.Column([
                    ft.ElevatedButton(button_text, icon=ft.Icons.ATTACH_FILE, on_click=pick_files),
                    file_list,
                    progress_row,
                    complete_btn,
                ], spacing=8), selected_files, reset

            subj_dd = ft.Dropdown(
                label="科目",
                options=[ft.dropdown.Option(s) for s in ["数学", "语文", "英语", "物理", "化学", "生物", "历史", "政治", "地理"]],
                value="数学", width=150,
            )
            original_input = ft.TextField(label="原题（题干）", multiline=True, min_lines=3,
                                           border_radius=14, filled=True, fill_color="#1F1F26",
                                           border_color="#414868", focused_border_color="#7AA2F7")
            mistake_input = ft.TextField(label="错因", multiline=True, min_lines=2,
                                         border_radius=14, filled=True, fill_color="#1F1F26",
                                         border_color="#414868", focused_border_color="#7AA2F7")
            answer_input = ft.TextField(label="标准答案", multiline=True, min_lines=2,
                                        border_radius=14, filled=True, fill_color="#1F1F26",
                                        border_color="#414868", focused_border_color="#7AA2F7")
            idea_input = ft.TextField(label="我的理解", multiline=True, min_lines=2,
                                      border_radius=14, filled=True, fill_color="#1F1F26",
                                      border_color="#414868", focused_border_color="#7AA2F7")
            tags_input = ft.TextField(label="手动标签（逗号分隔）", multiline=False,
                                      border_radius=14, filled=True, fill_color="#1F1F26",
                                      border_color="#414868", focused_border_color="#7AA2F7")

            progress_status = ft.Text("", size=14)
            progress_bar = ft.ProgressBar(width=200, height=8, value=0, visible=False)
            progress_row = ft.Row([progress_bar, progress_status], spacing=10, visible=False)

            def on_picker_complete(selected_files):
                if selected_files:
                    analyze_images(selected_files)

            picker_col1, original_files, reset_picker1 = make_file_picker_button(
                "📷 题目图片（可多选）", "image", on_complete=on_picker_complete)
            picker_col2, answer_files, reset_picker2 = make_file_picker_button(
                "📷 答案图片", "image", on_complete=None)
            picker_col3, idea_files, reset_picker3 = make_file_picker_button(
                "📷 笔记图片（错题补充）", "image", on_complete=None)

            def analyze_images(image_paths):
                progress_row.visible = True
                progress_bar.value = 0
                progress_status.value = "准备分析..."
                page.update()

                def do_analyze():
                    total = len(image_paths)
                    for idx, path in enumerate(image_paths):
                        progress = (idx + 1) / total
                        progress_bar.value = progress
                        progress_status.value = f"正在分析第 {idx+1}/{total} 张图片..."
                        page.update()
                        result = analyze_single_image(path)
                        if result:
                            if result.get("question"):
                                q_text = str(result["question"]).strip()
                                if q_text and q_text.lower() != "null":
                                    if original_input.value.strip():
                                        original_input.value += "\n\n" + q_text
                                    else:
                                        original_input.value = q_text
                            if result.get("answer"):
                                a_text = str(result["answer"]).strip()
                                if a_text and a_text.lower() != "null":
                                    if answer_input.value.strip():
                                        answer_input.value += "\n\n" + a_text
                                    else:
                                        answer_input.value = a_text
                            if result.get("knowledge_point"):
                                current_tags = tags_input.value.strip()
                                if current_tags:
                                    tags_input.value = f"{current_tags}, {result['knowledge_point']}"
                                else:
                                    tags_input.value = result['knowledge_point']
                            if result.get("error_type"):
                                mistake_input.value = result['error_type']
                        time.sleep(0.5)
                    progress_status.value = "✅ 分析完成！"
                    progress_bar.value = 1.0
                    page.update()
                    show_toast("图片分析完成，已自动填充标签和错因", "green")
                    time.sleep(2)
                    progress_row.visible = False
                    page.update()

                threading.Thread(target=do_analyze, daemon=True).start()

            @retry_request(max_retries=2, base_delay=2)
            def analyze_single_image(image_path):
                if not provider_supports_vision():
                    show_toast("当前 API 不支持图像识别，请切换到智谱 GLM", "red")
                    return None
                api_key, api_url, _m, vision_model = endpoint_for("cheap")
                if not api_key:
                    return None
                try:
                    with open(image_path, "rb") as f:
                        img_b64 = base64.b64encode(f.read()).decode("utf-8")
                except BaseException:
                    return None
                prompt = """请仔细识别这张图片中的题目内容，并返回以下 JSON 格式：
{
  "question": "【最重要】完整、逐字抄录图片中的题目原文，包括题干和全部选项（A. B. C. D. 等）以及图表中的关键文字，一字不差，不要省略、不要概括、不要翻译；如果一张图有多道题，只识别最完整、最清晰的一道题",
  "answer": "如果图片中可见标准答案或解析，照录答案内容；没有则填空字符串",
  "knowledge_point": "该题涉及的知识点（如：三角函数、力学、非谓语动词等）",
  "error_type": "学生可能的错因（如：公式记错、审题不清、计算错误）",
  "difficulty": 1-5 的整数（1最简单，5最难）
}
只返回 JSON，不要其他文字。"""
                messages = [{"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
                ]}]
                try:
                    resp = requests.post(
                        api_url,
                        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                        json={"model": vision_model, "messages": messages, "max_tokens": 300},
                        timeout=30)
                    if resp.status_code == 200:
                        content = resp.json()["choices"][0]["message"]["content"]
                        try:
                            result = json.loads(content)
                            return result
                        except BaseException:
                            match = re.search(r'\{[^{}]*\}', content)
                            if match:
                                try:
                                    result = json.loads(match.group())
                                    return result
                                except BaseException:
                                    pass
                    return None
                except BaseException:
                    return None

            def submit_error(e):
                subj = subj_dd.value
                orig = original_input.value.strip()
                mis = mistake_input.value.strip()
                ans = answer_input.value.strip()
                idea = idea_input.value.strip()
                tags = tags_input.value.strip()
                if not orig and not original_files:
                    show_toast("请至少输入原题或拍照上传", "red")
                    return
                save_error(subj, orig, list(original_files), ans, list(answer_files), mis, idea, list(idea_files), tags)
                original_input.value = ""
                mistake_input.value = ""
                answer_input.value = ""
                idea_input.value = ""
                tags_input.value = ""
                reset_picker1()
                reset_picker2()
                reset_picker3()
                show_toast(f"✅ {subj} 错题已保存！", "green")

            note_subject_dd = ft.Dropdown(
                label="科目",
                options=[ft.dropdown.Option(s) for s in ["数学", "语文", "英语", "物理", "化学", "生物", "历史", "政治", "地理"]],
                value="数学", width=150,
            )
            note_content_input = ft.TextField(label="笔记内容（可选）", multiline=True, min_lines=4,
                                               border_radius=14, filled=True, fill_color="#1F1F26",
                                               border_color="#414868", focused_border_color="#7AA2F7")
            note_picker_col, note_files, reset_note_picker = make_file_picker_button(
                "📷 笔记图片（可多选）", "image", on_complete=None)

            def submit_note(e):
                subj = note_subject_dd.value
                content = note_content_input.value.strip()
                if not content and not note_files:
                    show_toast("请输入笔记内容或上传图片", "red")
                    return
                save_note(subj, content, list(note_files))
                note_content_input.value = ""
                reset_note_picker()
                show_toast(f"✅ {subj} 笔记已保存！", "green")

            # ===== 苹果风 UI 组件 =====
            def u_section(title, icon=None):
                """分区标题：小号灰色字 + 细线"""
                return ft.Row([
                    ft.Text((icon + "  " if icon else "") + title,
                            size=13, weight=ft.FontWeight.W_600, color="#8E8E93"),
                    ft.Container(expand=True, height=1, bgcolor="#2A2A32"),
                ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER)

            def u_card(content, padding=18, radius=22, bg="#CC1A1B26"):
                """苹果风液态玻璃卡片：半透明底色 + 背景模糊 + 细亮边 + 柔和阴影"""
                def _on_hover(e):
                    try:
                        card.scale = 1.012 if e.data == "true" else 1.0
                        card.shadow = (ft.BoxShadow(blur_radius=26, color="#44000000",
                                                    offset=ft.Offset(0, 8)) if e.data == "true"
                                       else ft.BoxShadow(blur_radius=18, color="#33000000",
                                                         offset=ft.Offset(0, 6)))
                        page.update()
                    except BaseException:
                        pass

                card = ft.Container(
                    content=content,
                    padding=padding,
                    border_radius=radius,
                    bgcolor=bg,
                    blur=ft.Blur(18, 18, ft.BlurTileMode.CLAMP),
                    border=ft.border.all(1, "#33FFFFFF"),
                    shadow=ft.BoxShadow(blur_radius=18, color="#33000000",
                                        offset=ft.Offset(0, 6)),
                    scale=1.0,
                    animate_scale=ft.Animation(160, ft.AnimationCurve.EASE_OUT),
                    animate_shadow=ft.Animation(160, ft.AnimationCurve.EASE_OUT),
                    on_hover=_on_hover,
                )
                return card

            def u_primary_btn(text, on_click, icon=None, color="#7AA2F7"):
                """全宽圆角主按钮"""
                return ft.ElevatedButton(
                    text, icon=icon, on_click=on_click,
                    bgcolor=color, color="#FFFFFF",
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=14),
                        padding=ft.Padding(left=20, right=20, top=14, bottom=14)),
                    expand=True)

            home_page = ft.Column([
                ft.Container(height=6),
                ft.Text("📸 拍照录题", size=24, weight=ft.FontWeight.BOLD),
                ft.Text("拍下题目，AI 自动读取原文并分析错因", size=13, color="#8E8E93"),
                u_card(ft.Column([
                    ft.Row([subj_dd], spacing=15) if not is_mobile else ft.Column([subj_dd]),
                    original_input,
                    mistake_input,
                ], spacing=12)),
                u_section("可选补充", "✨"),
                u_card(ft.Column([
                    answer_input,
                    idea_input,
                    tags_input,
                ], spacing=12)),
                u_section("附件上传", "📎"),
                u_card(ft.Column([
                    picker_col1,
                    picker_col2,
                    picker_col3,
                    progress_row,
                ], spacing=10)),
                ft.Container(height=4),
                u_primary_btn("保存错题", submit_error, ft.Icons.SAVE),
                ft.Container(height=18),
                ft.Text("📝 记笔记", size=24, weight=ft.FontWeight.BOLD),
                ft.Text("随手记录课堂重点与灵感", size=13, color="#8E8E93"),
                u_card(ft.Column([
                    ft.Row([note_subject_dd], spacing=15) if not is_mobile else ft.Column([note_subject_dd]),
                    note_content_input,
                    note_picker_col,
                ], spacing=12)),
                ft.Container(height=4),
                u_primary_btn("保存笔记", submit_note, ft.Icons.SAVE_OUTLINED),
                ft.Container(height=24),
            ], spacing=14, scroll=ft.ScrollMode.AUTO)

            AI_SUBJECTS = [("总AI", "🤖"), ("数学", "📐"), ("语文", "📜"), ("英语", "📝"),
                           ("物理", "⚛️"), ("化学", "🧪"), ("生物", "🧬"),
                           ("历史", "🏛️"), ("政治", "⚖️"), ("地理", "🌍")]

            contact_panel = ft.Container(
                visible=False,
                bgcolor="#CC242424",
                blur=16,
                border_radius=16,
                padding=15,
                width=220,
                border=ft.border.all(1, ft.Colors.WHITE24),
                shadow=ft.BoxShadow(blur_radius=20, color="#88000000"),
                animate_opacity=ft.Animation(250, ft.AnimationCurve.EASE_OUT),
            )

            def close_contact_panel(e=None):
                contact_panel.visible = False
                page.update()

            def open_contact_panel(e):
                try:
                    w = page.width or (page.window.width if page.window else None) or 360
                    h = page.height or (page.window.height if page.window else None) or 640
                except Exception:
                    w, h = 360, 640
                panel_w = 220
                panel_h = 420
                bx = ball_state["ball_x"]
                by = ball_state["ball_y"]
                if bx < w / 2:
                    panel_x = bx + 64
                else:
                    panel_x = bx - panel_w - 8
                panel_y = by
                panel_x = max(8, min(panel_x, w - panel_w - 8))
                panel_y = max(8, min(panel_y, h - panel_h - 8))
                contact_panel.left = panel_x
                contact_panel.top = panel_y
                contact_panel.right = None
                contact_panel.bottom = None
                contact_panel.visible = True
                page.update()

            contact_list = ft.Column(spacing=8)
            for subj_name, subj_icon in AI_SUBJECTS:
                btn = ft.TextButton(
                    text=f"{subj_icon} {subj_name}",
                    on_click=lambda e, s=subj_name: open_chat(s))
                contact_list.controls.append(btn)
            contact_panel.content = ft.Column(
                [ft.Text("🧠 AI 助手", size=18), ft.Divider(), contact_list],
                spacing=5)

            ball_state = {"dragging": False, "moved": False, "ball_x": 300, "ball_y": 500}

            def on_ball_pan_start(e):
                ball_state["dragging"] = True
                ball_state["moved"] = False
                ball_inner.scale = 0.9  # 按压反馈

            def on_ball_pan_update(e):
                if not ball_state["dragging"]:
                    return
                if abs(e.delta_x) + abs(e.delta_y) > 2:
                    ball_state["moved"] = True
                ball_state["ball_x"] += e.delta_x
                ball_state["ball_y"] += e.delta_y
                try:
                    w = page.width or (page.window.width if page.window else None) or 360
                    h = page.height or (page.window.height if page.window else None) or 640
                except Exception:
                    w, h = 360, 640
                ball_state["ball_x"] = max(0, min(ball_state["ball_x"], w - 56))
                ball_state["ball_y"] = max(0, min(ball_state["ball_y"], h - 56))
                ball_container.left = ball_state["ball_x"]
                ball_container.top = ball_state["ball_y"]
                ball_container.right = None
                ball_container.bottom = None
                if contact_panel.visible:
                    panel_w = 220
                    panel_h = 420
                    bx = ball_state["ball_x"]
                    by = ball_state["ball_y"]
                    if bx < w / 2:
                        panel_x = bx + 64
                    else:
                        panel_x = bx - panel_w - 8
                    panel_y = by
                    panel_x = max(8, min(panel_x, w - panel_w - 8))
                    panel_y = max(8, min(panel_y, h - panel_h - 8))
                    contact_panel.left = panel_x
                    contact_panel.top = panel_y
                page.update()

            def on_ball_pan_end(e):
                ball_state["dragging"] = False
                ball_inner.scale = 1.0  # 松开恢复
                try:
                    w = page.width or (page.window.width if page.window else None) or 360
                    h = page.height or (page.window.height if page.window else None) or 640
                except Exception:
                    w, h = 360, 640
                if ball_state["ball_x"] + 28 < w / 2:
                    ball_state["ball_x"] = 8
                else:
                    ball_state["ball_x"] = w - 56 - 8
                ball_state["ball_y"] = max(80, min(ball_state["ball_y"], h - 56 - 100))
                ball_container.left = ball_state["ball_x"]
                ball_container.top = ball_state["ball_y"]
                ball_container.animate_left = ft.Animation(250, ft.AnimationCurve.EASE_OUT)
                ball_container.animate_top = ft.Animation(250, ft.AnimationCurve.EASE_OUT)
                page.update()

            def on_ball_tap(e):
                ball_inner.scale = 1.0
                if ball_state.get("moved"):
                    ball_state["moved"] = False
                    return
                if contact_panel.visible:
                    close_contact_panel()
                else:
                    open_contact_panel(e)

            ball_inner = ft.Container(
                content=ft.Text("AI", size=20, color="white", weight=ft.FontWeight.BOLD),
                width=56,
                height=56,
                border_radius=28,
                bgcolor="#CC1C1C26",
                blur=16,
                border=ft.border.all(1, "#44FFFFFF"),
                shadow=ft.BoxShadow(blur_radius=24, color="#887AA2F7", spread_radius=1),
                alignment=ft.alignment.center,
                ink=True,
                animate_scale=ft.Animation(160, ft.AnimationCurve.EASE_OUT),
            )
            ai_ball = ft.GestureDetector(
                content=ball_inner,
                drag_interval=20,
                on_tap=on_ball_tap,
                on_pan_start=on_ball_pan_start,
                on_pan_update=on_ball_pan_update,
                on_pan_end=on_ball_pan_end,
            )
            ball_container = ft.Container(
                content=ai_ball,
                left=ball_state["ball_x"],
                top=ball_state["ball_y"],
            )

            chat_dialog = ft.Container(
                visible=False,
                left=0,
                top=0,
                right=0,
                bottom=0,
                bgcolor="#F616161E",
                border_radius=0,
                padding=0,
                border=None,
                offset=ft.Offset(0, 0.02),
                animate_offset=ft.Animation(180, ft.AnimationCurve.EASE_OUT),
                animate_opacity=ft.Animation(180, ft.AnimationCurve.EASE_OUT),
                opacity=0,
            )
            current_chat_subject = "总AI"
            stop_flag = False
            generation_active = False

            def open_chat(subject, initial_message=None, auto_send=False):
                nonlocal current_chat_subject, stop_flag, generation_active
                if generation_active:
                    stop_flag = True
                    time.sleep(0.2)
                generation_active = False
                stop_flag = False
                current_chat_subject = subject
                close_contact_panel()
                chat_dialog.content = build_chat_window(subject, initial_message, auto_send)
                # 弹入动画：先下沉+透明，再滑上来淡入
                chat_dialog.offset = ft.Offset(0, 0.04)
                chat_dialog.opacity = 0
                chat_dialog.visible = True
                page.update()
                chat_dialog.offset = ft.Offset(0, 0)
                chat_dialog.opacity = 1
                page.update()

            def call_ai_stream(messages, model_name, on_chunk, need_vision=False):
                # 多模态（含图片）→ 自动走视觉模型；否则走 smart 增强对话
                if need_vision:
                    if not provider_supports_vision():
                        on_chunk("❌ 当前模型不支持图片识别，请在设置中切换智谱 GLM（视觉模型）")
                        return None
                    api_key, api_url, _m, vision_model = endpoint_for("cheap")
                    if not api_key:
                        on_chunk("❌ 未配置API密钥")
                        return None
                    api_model = vision_model or "glm-4v"
                else:
                    api_key, api_url, api_model, _v = endpoint_for("smart")
                    if not api_key:
                        on_chunk("❌ 未配置API密钥")
                        return None
                headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                payload = {"model": api_model, "messages": messages,
                           "temperature": 0.7, "max_tokens": 2048, "stream": True}
                # DeepSeek：按设置开关思考模式（V4.1 默认思考，含 reasoning_content）
                if api_model.startswith("deepseek"):
                    _cfg = load_ai_config()
                    if _cfg.get("deepseek_thinking", True):
                        payload["thinking"] = {"type": "enabled"}
                        payload["reasoning_effort"] = "high"
                try:
                    resp = requests.post(
                        api_url,
                        headers=headers, json=payload, stream=True, timeout=60)
                    if resp.status_code != 200:
                        on_chunk(f"❌ API错误 {resp.status_code}")
                        return
                    accumulated = ""
                    for line in resp.iter_lines(decode_unicode=True):
                        if stop_flag:
                            break
                        if line and line.startswith('data: ') and line[6:].strip() != '[DONE]':
                            try:
                                data = json.loads(line[6:])
                                delta = data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                if delta:
                                    accumulated += delta
                                    on_chunk(accumulated)
                            except BaseException:
                                continue
                    return accumulated
                except Exception as e:
                    on_chunk(f"❌ 异常: {str(e)}")
                    return None

            _MM_HIGHLIGHT = {"kp": None}  # 错题/笔记本 → 思维导图 高亮通道

            def build_chat_window(subject, initial_message=None, auto_send=False):
                nonlocal stop_flag, generation_active
                display_name = subject if subject != "总AI" else "总AI"
                try:
                    _cfg = load_ai_config()
                    _provider_key = _cfg.get("provider", "zhipu")
                    _provider_name = PROVIDERS.get(_provider_key, PROVIDERS["zhipu"])["name"]
                    _model_name = PROVIDERS.get(_provider_key, PROVIDERS["zhipu"])["model"]
                except Exception:
                    _provider_name = "AI"
                    _model_name = ""
                history = load_chat_history(subject)
                context_messages = build_ctx(history, max_chars=20000)
                memory_context = get_memory_context(subject if subject != "总AI" else None)
                profile_summary = get_profile_summary()
                strategy = get_teaching_strategy(subject if subject != "总AI" else None)
                system_prompt = f"""你是「池鱼」里的{display_name}老师——一位真正了解{display_name}的私教。请像真人老师一样自然地和学生对话，别端着、别啰嗦、别用"作为AI"这类开头。

回答风格（像豆包 / DeepSeek 手机版那样好聊）：
- 自然口语化，但保持专业；句子短一点，多用"你/咱们"，少用机械的"第一、第二"模板。
- 简洁优先：先直接给结论/答案，再展开解释；能一句话说清就别写三段；别堆砌"首先/其次/最后"。
- 下方注入的记忆（画像/错题/笔记/摘要/联网）是让你更懂他的背景，不是任务清单——自然融入回答即可，不要逐条复述。
- 知识类问题：讲清原理与关键点，能串上他学过的内容就主动提一句。
- 解题类问题：先讲思路（为什么这么做），再给步骤，最后点出易错点；不要一上来甩答案。
- 学生卡壳时：主动降难度、换个角度、举个生活化的例子再讲一遍。
- 讲解完随手问一句"这步明白吗？"，让学生能接话。

你真正了解这个学生：下方附有他的学习画像、薄弱点、错题、历史对话等真实记忆。回答时自然引用这些记忆（比如"上次你在这个知识点错过""你最近在练XX"），让他感到你真的记得他——但不要生硬复述标签和数据。

【教学法（借鉴港大 DeepTutor 深度辅导思路）】
- 先诊断后讲解：回答前先想学生当前水平，讲解按"他听得懂"的难度来。
- 引导式：题目类问题先让他自己想/说，再判对错讲解；不要直接给答案。
- 主动关联：他问的东西如果和你记得的薄弱点/错题有关，主动串联旧知识。
- 学情闭环：讲完给他一句"下一步建议练什么"，让他能持续进步。"""
                
                custom_skill = load_custom_skill()
                if custom_skill:
                    system_prompt += f"\n\n额外的教学指导：{custom_skill}"
                if memory_context:
                    system_prompt += f"\n\n{memory_context}"
                if profile_summary:
                    system_prompt += f"\n\n{profile_summary}"
                if strategy:
                    system_prompt += f"\n\n{strategy}"

                # —— 教材知识库：按科目检索最近提问相关的教材章节，优先引用原文 ——
                try:
                    if subject != "总AI":
                        _tq = ""
                        for _m in history[-3:]:
                            if _m.get("role") == "user":
                                _tq = str(_m.get("content", ""))[:80]
                                break
                        if _tq:
                            _tb = search_textbook(subject, _tq)
                            if _tb:
                                system_prompt += (f"\n\n【教材参考（人教版{subject}）】\n"
                                                  "以下为教材原文摘录（含页码），回答时优先遵循教材定义与表述：\n"
                                                  + _tb)
                except BaseException:
                    pass

                # —— DeepTutor 混合个性化：实时学情注入（薄弱点 + 上次遗留问题）——
                try:
                    _p_now = load_user_profile()
                    _wk_now = sorted(_p_now.get("weak_knowledge", {}).items(), key=lambda x: x[1], reverse=True)[:5]
                    _lq_now = (_p_now.get("last_question") or "").strip()
                    _live_parts = []
                    if _lq_now:
                        _live_parts.append(f"上次没完全搞懂的问题：{_lq_now[:150]}")
                    if _wk_now:
                        _live_parts.append("最新薄弱知识点：" + "、".join(f"{k}" for k, _v in _wk_now))
                    if _live_parts:
                        system_prompt += ("\n\n【实时学情】\n" + "\n".join(_live_parts) +
                                          "\n- 优先讲解这些薄弱点；若用户问题与薄弱点相关，主动串联旧知识，让学生感到你在持续跟进。"
                                          "- 引用时用自然的说法，比如\"我看你最近在这个点上栽过跟头\"，别念数据。")
                except BaseException:
                    pass

                system_prompt += """

【继续生成规则】
- 如果历史对话里最后一条 assistant 消息带有「〔未完成，等待继续〕」标记，或明显只写了一半就结束，用户又说"继续""接着说"等，请直接从上次断掉的最后一个字后面接着写，不要重新开始、不要做总结、不要重复已经写过的内容。

【可视化规则 - 必须遵守】
当回答涉及趋势、占比、比较、流程、机制、因果、架构、关系、时间线、状态机、算法步骤、参数变化时，在回复最末尾附一个 ```chart 代码块，内容必须是 JSON。

四种图表格式（按需选 1 个，严格替换里面的文字，不要加注释）：

1. 柱状图：
```chart
{"type":"bar","title":"标题","labels":["A","B"],"values":[1,2],"unit":""}
```

2. 环形图：
```chart
{"type":"pie","title":"标题","items":[{"name":"A","value":10},{"name":"B","value":20}]}
```

3. 时间线：
```chart
{"type":"timeline","title":"标题","events":[{"date":"10-05","title":"事件","desc":"描述"}]}
```

4. 流程图：
```chart
{"type":"flow","title":"标题","steps":[{"label":"步骤1","status":"ok","desc":"说明"},{"label":"步骤2","status":"warn","desc":"说明"}]}
```

要求：
- 必须严格合法 JSON，不要用单引号，不要多余的标点。
- status 取值只能是：ok（绿） / warn（黄） / err（红） / none（灰）。
- 一条回复最多 1 个 chart 块。
- 不要自己手画 <svg> 标签，不要用 ECharts，不要用 HTML。
- 不适合图形时，直接用纯文本，不要输出 chart 块。
"""

                if context_messages:
                    system_prompt += "\n\n以下是最近的对话历史（仅作上下文参考，不要重复历史内容）：\n"
                    for msg in context_messages[-6:]:
                        role_label = "学生" if msg["role"] == "user" else "老师"
                        _c = re.sub(r"(\n)?【图】\S+", "[图片]", str(msg["content"]))[:300]
                        system_prompt += f"[{role_label}]: {_c}\n"
                all_messages = [{"role": "system", "content": system_prompt}]
                for msg in context_messages:
                    all_messages.append(msg)

                chat_history_display = ft.ListView(spacing=12, expand=True, auto_scroll=True)

                def make_user_bubble(text):
                    # 支持多模态图片：消息里以【图】标记携带本地图片路径，拆出文本+图片渲染
                    txt = re.sub(r"(\n)?【图】\S+", "", text).strip()
                    img_paths = re.findall(r"【图】(\S+)", text)
                    inner = []
                    if txt:
                        inner.append(ft.Text(txt, size=14, selectable=True, color="#FFFFFF"))
                    for p in img_paths:
                        full = p if os.path.isabs(p) else os.path.join(DATA_DIR, p)
                        if os.path.exists(full):
                            inner.append(ft.Image(src=full, width=170,
                                                  border_radius=8, fit=ft.ImageFit.CONTAIN))
                    if not inner:
                        inner.append(ft.Text(text, size=14, selectable=True, color="#FFFFFF"))
                    return ft.Row([
                        ft.Container(expand=True),
                        ft.Container(
                            content=ft.Column(inner, spacing=4),
                            padding=ft.Padding(left=14, right=14, top=10, bottom=10),
                            border_radius=ft.BorderRadius(16, 16, 4, 16),
                            bgcolor="#B07AA2F7",
                            blur=ft.Blur(8, 8, ft.BlurTileMode.CLAMP),
                            border=ft.border.all(1, "#557AA2F7"),
                            shadow=ft.BoxShadow(blur_radius=10, color="#44000000"),
                            width=300,
                        ),
                    ], alignment=ft.MainAxisAlignment.END)

                def make_ai_bubble(text, can_regenerate=True, content_ref=None):
                    if content_ref is None:
                        content_ref = {"col": None, "md": None, "stream": None, "row": None, "actions": None}
                    stream_text = ft.Text(text or "▌", size=14, selectable=True, color="#EEEEEE")
                    md = ft.Markdown(
                        value="",
                        selectable=True,
                        extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                        code_theme="atom-one-dark",
                        on_tap_link=lambda e: page.launch_url(e.data),
                    )
                    content_col = ft.Column([stream_text], spacing=4)
                    content_ref["col"] = content_col
                    content_ref["md"] = md
                    content_ref["stream"] = stream_text
                    content_ref["raw"] = text

                    def _do_copy(e):
                        try:
                            src = md.value if md.value else (stream_text.value or "")
                            page.set_clipboard(src)
                            show_toast("已复制", "green")
                        except Exception:
                            show_toast("复制失败", "red")

                    def _delete_self(e):
                        try:
                            target_row = content_ref.get("row")
                            if target_row and target_row in chat_history_display.controls:
                                chat_history_display.controls.remove(target_row)
                                page.update()
                                try:
                                    fp = get_chat_history_file(subject)
                                    hs = load_jsonl(fp)
                                    raw = content_ref.get("raw", "")
                                    raw_clean = extract_chart_block(raw)[0] if raw else ""
                                    hs = [m for m in hs if not (
                                        m.get("role") == "assistant"
                                        and (
                                            m.get("content", "") == raw
                                            or (raw_clean and extract_chart_block(m.get("content", ""))[0] == raw_clean)
                                        )
                                    )]
                                    save_jsonl(fp, hs)
                                except Exception:
                                    pass
                                show_toast("已删除本条", "info")
                        except Exception as ex:
                            show_toast(f"删除失败：{str(ex)[:30]}", "red")

                    copy_btn = ft.IconButton(
                        icon=ft.Icons.COPY_OUTLINED, icon_size=16, tooltip="复制",
                        icon_color="#888888", on_click=_do_copy, visible=True)
                    regen_btn = ft.IconButton(
                        icon=ft.Icons.REFRESH, icon_size=16, tooltip="重新思考",
                        icon_color="#888888",
                        on_click=lambda e: regenerate_last(),
                        visible=can_regenerate)
                    del_btn = ft.IconButton(
                        icon=ft.Icons.DELETE_OUTLINE, icon_size=16, tooltip="删除本条",
                        icon_color="#888888",
                        on_click=_delete_self,
                        visible=can_regenerate)
                    add_btn = ft.IconButton(
                        icon=ft.Icons.PLAYLIST_ADD, icon_size=16, tooltip="把这道题收进错题本",
                        icon_color="#888888",
                        on_click=lambda e: add_to_errorbook(),
                        visible=False)
                    action_row = ft.Row([copy_btn, regen_btn, del_btn, add_btn], spacing=2, tight=True)
                    content_ref["actions"] = (regen_btn, del_btn, add_btn)

                    bubble = ft.Container(
                        content=ft.Column([content_col, action_row], spacing=4),
                        padding=ft.Padding(left=14, right=8, top=10, bottom=6),
                        border_radius=ft.BorderRadius(16, 16, 16, 4),
                        bgcolor="#8F24283B",
                        blur=ft.Blur(8, 8, ft.BlurTileMode.CLAMP),
                        border=ft.border.all(1, "#55414868"),
                        shadow=ft.BoxShadow(blur_radius=10, color="#33000000"),
                        width=300,
                    )
                    avatar = ft.Container(
                        content=ft.Text(display_name[:1] if display_name != "总AI" else "AI",
                                        size=11, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
                        width=30, height=30, border_radius=15,
                        bgcolor="#7AA2F7", alignment=ft.alignment.center,
                        shadow=ft.BoxShadow(blur_radius=6, color="#44BB9AF7"),
                    )
                    row = ft.Row([avatar, bubble, ft.Container(expand=True)],
                                 alignment=ft.MainAxisAlignment.START,
                                 vertical_alignment=ft.CrossAxisAlignment.START)
                    content_ref["row"] = row
                    return row, content_col

                for msg in history:
                    if msg["role"] == "user":
                        chat_history_display.controls.append(make_user_bubble(msg["content"]))
                    else:
                        clean_text, chart_html = extract_chart_block(msg["content"])
                        bubble_row, content_col = make_ai_bubble(clean_text if clean_text else msg["content"])
                        if chart_html and content_col:
                            def make_view(h=chart_html):
                                def view(e):
                                    show_chart_overlay(h)
                                return view
                            _svg_path = save_svg_chart(chart_html)
                            if _svg_path:
                                content_col.controls.append(
                                    ft.Container(
                                        content=ft.Image(src=_svg_path, fit=ft.ImageFit.CONTAIN,
                                                         width=250, border_radius=12),
                                        on_click=make_view(), ink=True,
                                        border=ft.border.all(1, "#414868"),
                                        border_radius=12,
                                    ))
                            chart_btn = ft.Container(
                                content=ft.Row([
                                    ft.Text("📊", size=16),
                                    ft.Text("查看图表", size=13, color="#FFCCCC"),
                                ], spacing=4, tight=True),
                                bgcolor="#24283B",
                                border_radius=12,
                                padding=ft.Padding(left=12, right=12, top=6, bottom=6),
                                border=ft.border.all(1, "#6B4A3A"),
                                on_click=make_view(),
                                ink=True,
                            )
                            content_col.controls.append(chart_btn)
                        chat_history_display.controls.append(bubble_row)

                chat_input = ft.TextField(
                    hint_text="和" + display_name + "老师聊点什么...",
                    multiline=True, min_lines=1, max_lines=8,
                    border_radius=20,
                    border_color="#414868",
                    focused_border_color="#7AA2F7",
                    filled=True,
                    fill_color="#CC1F1F26",
                    text_size=14,
                    content_padding=ft.Padding(left=14, right=14, top=10, bottom=10),
                    expand=True,
                )
                web_btn = ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.PUBLIC, size=18, color="#9AA5CE"),
                        ft.Text("联网", size=9, color="#9AA5CE"),
                    ], spacing=0, alignment=ft.MainAxisAlignment.CENTER,
                       horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    width=44, height=40, border_radius=12,
                    bgcolor="#24283B",
                    border=ft.border.all(1, "#414868"),
                    alignment=ft.alignment.center,
                    on_click=lambda e: toggle_web_search(),
                    ink=True,
                    tooltip="联网搜索：开启后每轮自动联网检索（DeepSeek）",
                )

                def toggle_web_search(e=None):
                    _WEB_SEARCH_ON["on"] = not _WEB_SEARCH_ON["on"]
                    if _WEB_SEARCH_ON["on"]:
                        web_btn.bgcolor = "#7AA2F7"
                        web_btn.border = ft.border.all(1, "#7AA2F7")
                        web_btn.content.controls[0].color = "#FFFFFF"
                        web_btn.content.controls[1].color = "#FFFFFF"
                        show_toast("🌐 联网搜索已开启", "green")
                    else:
                        web_btn.bgcolor = "#24283B"
                        web_btn.border = ft.border.all(1, "#414868")
                        web_btn.content.controls[0].color = "#9AA5CE"
                        web_btn.content.controls[1].color = "#9AA5CE"
                        show_toast("联网搜索已关闭", "grey")
                    page.update()
                send_btn = ft.Container(
                    content=ft.Icon(ft.Icons.ARROW_UPWARD, size=20, color="#FFFFFF"),
                    width=40, height=40, border_radius=20,
                    bgcolor="#7AA2F7",
                    alignment=ft.alignment.center,
                    on_click=lambda e: handle_send(),
                    ink=True,
                    shadow=ft.BoxShadow(blur_radius=8, color="#44BB9AF7"),
                )
                stop_btn = ft.TextButton("停止生成", visible=False)
                continue_btn = ft.TextButton("继续生成", visible=False)

                quick_row = ft.Row([
                    ft.Container(
                        content=ft.Text("讲简单点", size=12, color="#CCCCCC"),
                        padding=ft.Padding(left=12, right=12, top=6, bottom=6),
                        border_radius=14, bgcolor="#24283B",
                        border=ft.border.all(1, "#414868"),
                        on_click=lambda e: handle_send("请再用更简单的方式讲一遍"),
                        ink=True),
                    ft.Container(
                        content=ft.Text("举个栗子", size=12, color="#CCCCCC"),
                        padding=ft.Padding(left=12, right=12, top=6, bottom=6),
                        border_radius=14, bgcolor="#24283B",
                        border=ft.border.all(1, "#414868"),
                        on_click=lambda e: handle_send("请举一个具体例子"),
                        ink=True),
                    ft.Container(
                        content=ft.Text("考考我", size=12, color="#CCCCCC"),
                        padding=ft.Padding(left=12, right=12, top=6, bottom=6),
                        border_radius=14, bgcolor="#24283B",
                        border=ft.border.all(1, "#414868"),
                        on_click=lambda e: ask_similar_q(),
                        ink=True),
                ], spacing=8, scroll=ft.ScrollMode.AUTO)

                last_user_msg = {"text": ""}
                last_ai_content_ref = {"col": None}
                gen_token = {"id": 0}  # 代次令牌：防止旧生成线程串台/重复保存
                _added_questions = set()  # 防重复：同一条问答只入一次错题本

                def add_to_errorbook(e=None):
                    """把当前一轮问答（用户题目 + AI 解答）一键收进错题本"""
                    q = (last_user_msg.get("text") or "").strip()
                    ref_ = last_ai_content_ref.get("ref") or {}
                    ans = str(ref_.get("raw", "") or "")[:1500]
                    if not q or not ans:
                        show_toast("没有可加入的问答内容", "grey")
                        return
                    if subject == "总AI":
                        show_toast("请先进入具体学科对话，再把题收进该科错题本", "orange")
                        return
                    if q in _added_questions:
                        show_toast("这条问答已经收进错题本啦", "info")
                        return
                    clean_ans = re.sub(r"```chart.*?```", "", ans, flags=re.S).strip()
                    # 题目段：问题本身（可能带【图】标记，去掉）
                    orig_txt = re.sub(r"(\n)?【图】\S+", "", q).strip()[:800]
                    try:
                        save_error(subject,
                                   original=orig_txt,
                                   answer=clean_ans[:800],
                                   idea=clean_ans[:400],
                                   manual_tags="")
                    except BaseException as ex:
                        show_toast(f"加入失败：{str(ex)[:40]}", "red")
                        return
                    _added_questions.add(q)
                    show_toast("📥 已加入错题本，AI 正在后台打标签；知识树会同步生长", "green")

                def ask_similar_q(e=None):
                    """DeepTutor 式难度校准出题：
                    1) 免费模型快速学情诊断（结合画像薄弱点 → 水平/难度建议）
                    2) 按诊断结果组装「难度匹配出题」指令，走增强对话
                    3) 诊断失败自动降级为普通出题，不阻塞使用"""
                    def _run():
                        diag = None
                        try:
                            d_key, d_url, d_model, _v = endpoint_for("cheap")
                            if d_key:
                                weak = []
                                try:
                                    p_ = load_user_profile()
                                    wk = p_.get("weak_knowledge", {}) or {}
                                    for k, v in sorted(wk.items(), key=lambda x: x[1], reverse=True)[:4]:
                                        weak.append(f"{k}(薄弱度{round(v,2)})")
                                    if not weak:
                                        km = p_.get("knowledge_memory", {}) or {}
                                        weak = list(km.keys())[:4]
                                except BaseException:
                                    pass
                                diag_prompt = (
                                    "你是资深高中老师，负责给学生做学情诊断。请只输出 JSON，不要任何其他内容："
                                    '{"weak_point":"一句话指出学生当前最需要练的知识点",'
                                    '"level":"基础/中档/压轴",'
                                    '"advice":"一句有针对性的学习建议"}。'
                                    f"该学生最近的薄弱点：{json.dumps(weak, ensure_ascii=False)}。")
                                r_ = requests.post(
                                    d_url,
                                    headers={"Authorization": f"Bearer {d_key}", "Content-Type": "application/json"},
                                    json={"model": d_model, "messages": [{"role": "user", "content": diag_prompt}],
                                          "temperature": 0.3, "max_tokens": 300},
                                    timeout=15)
                                if r_.status_code == 200:
                                    c_ = r_.json()["choices"][0]["message"]["content"]
                                    try:
                                        diag = json.loads(c_)
                                    except BaseException:
                                        m_ = re.search(r'\{.*\}', c_, re.S)
                                        diag = json.loads(m_.group()) if m_ else None
                        except BaseException:
                            diag = None
                        if diag and diag.get("weak_point"):
                            msg = (
                                f"请结合我刚刚暴露出来的薄弱点【{diag.get('weak_point','')}】，"
                                f"给我出一道难度匹配我当前水平（{diag.get('level','中档')}）的类似题让我练练："
                                "先出题让我自己先想一下，不要直接给答案；"
                                "等我说出答案后你再判对错并详细讲解；"
                                f"最后告诉我下一步该练什么难度。{diag.get('advice','')}")
                        else:
                            msg = "出一道类似的题让我练练：先出题，等我给出答案后再讲解判对错。"
                        handle_send(msg)
                    threading.Thread(target=_run, daemon=True).start()

                def regenerate_last():
                    if not last_user_msg["text"]:
                        return
                    # 先删掉历史文件里末尾的 assistant 消息，避免重新生成后出现重复回答
                    try:
                        fp = get_chat_history_file(subject)
                        hs = load_jsonl(fp)
                        while hs and hs[-1].get("role") == "assistant":
                            hs.pop()
                        save_jsonl(fp, hs)
                    except Exception:
                        pass
                    if last_ai_content_ref["col"]:
                        try:
                            chat_history_display.controls.pop()
                        except Exception:
                            pass
                    _send_internal(last_user_msg["text"], insert_user_bubble=False)

                def handle_send(msg_text=None):
                    content = msg_text if msg_text else (chat_input.value or "").strip()
                    if not content:
                        return
                    if not msg_text:
                        chat_input.value = ""
                    last_user_msg["text"] = content
                    _send_internal(content, insert_user_bubble=True)

                def _send_internal(content, insert_user_bubble=True):
                    nonlocal generation_active, stop_flag
                    # 如果正在生成，先停掉旧生成，防止并发线程串台
                    if generation_active:
                        stop_flag = True
                        time.sleep(0.3)
                    generation_active = False
                    stop_flag = False
                    gen_token["id"] += 1
                    my_gen = gen_token["id"]
                    if insert_user_bubble:
                        chat_history_display.controls.append(make_user_bubble(content))
                    send_btn.visible = False
                    stop_btn.visible = True
                    page.update()
                    if insert_user_bubble:
                        save_chat_message(subject, "user", content)
                    hist_now = load_chat_history(subject)
                    # 长记忆：auto 模式按历史长度动态给预算（自动，像官方 App 一样越聊记得越多）
                    _ctx_cfg = load_ai_config().get("ctx_chars", "auto")
                    if _ctx_cfg == "auto":
                        _hist_len = sum(len(m.get("content", "") or "") for m in hist_now)
                        _ctx_chars = int(min(max(_hist_len, 20000), 80000))
                    else:
                        try:
                            _ctx_chars = int(_ctx_cfg)
                        except BaseException:
                            _ctx_chars = 50000
                    rebuilt = [{"role": "system", "content": system_prompt}]
                    # 个人画像注入：让 AI 基于学生画像个性化教学（按当前学科优先）
                    try:
                        _prof = load_user_profile()
                        _pt = profile_to_prompt_text(_prof, subject)
                        if _pt:
                            rebuilt[0]["content"] = rebuilt[0]["content"] + "\n\n" + _pt
                    except BaseException:
                        pass
                    # 早期对话摘要注入（滚动记忆）
                    try:
                        _sum = get_subject_summary(subject)
                        if _sum:
                            rebuilt[0]["content"] = (rebuilt[0]["content"] +
                                                     "\n\n【更早的对话摘要（AI 自动压缩的长期记忆，仍有效）】\n" + _sum)
                    except BaseException:
                        pass
                    # 发送后异步完善画像（问过计数/最近问题/主题词）
                    try:
                        update_subject_profile(subject, content)
                    except BaseException:
                        pass
                    for _m in build_ctx(hist_now, max_chars=_ctx_chars):
                        rebuilt.append({"role": _m["role"], "content": _m["content"]})
                    if (not rebuilt) or rebuilt[-1].get("role") != "user" or rebuilt[-1].get("content") != content:
                        rebuilt.append({"role": "user", "content": content})
                    try:
                        rel = pick_relevant_errors(content, subject if subject != "总AI" else None, limit=5)
                        if rel:
                            lines = ["【学生错题本中的相关错题（请务必结合这些具体内容回答，不要泛泛而谈）】"]
                            for i, e in enumerate(rel):
                                tags = "、".join(str(t) for t in e.get("tags", []))
                                orig = (e.get("original", "") or e.get("question", ""))[:200]
                                mis = str(e.get("mistake", ""))[:120]
                                ans = str(e.get("answer", ""))[:120]
                                lines.append(f"[{i+1}] 科目：{e.get('subject','')}  标签：{tags}")
                                lines.append(f"  题目：{orig}")
                                if mis:
                                    lines.append(f"  学生错误：{mis}")
                                if ans:
                                    lines.append(f"  正确答案：{ans}")
                            rebuilt[0] = {"role": "system",
                                          "content": rebuilt[0]["content"] + "\n\n" + "\n".join(lines)}
                    except BaseException:
                        pass
                    # 笔记检索注入：让 AI 能读取学生自己的笔记内容
                    try:
                        rel_notes = pick_relevant_notes(content, subject if subject != "总AI" else None, limit=3)
                        if rel_notes:
                            nlines = ["【学生笔记本中的相关笔记（回答时优先呼应笔记里的知识要点与写法）】"]
                            for i, n in enumerate(rel_notes):
                                ntext = str(n.get("content", ""))[:300]
                                nlines.append(f"[{i+1}] {n.get('time','')}：{ntext}")
                            rebuilt[0] = {"role": "system",
                                          "content": rebuilt[0]["content"] + "\n\n" + "\n".join(nlines)}
                    except BaseException:
                        pass
                    # DeepSeek 联网增强：联网开关开启时每轮强制检索；否则按 URL/意图自动触发
                    try:
                        if load_ai_config().get("provider") == "deepseek":
                            _enrich = deepseek_enrich(content, force=_WEB_SEARCH_ON.get("on", False))
                            if _enrich:
                                rebuilt[0] = {"role": "system",
                                              "content": rebuilt[0]["content"] + "\n\n" + _enrich}
                    except BaseException:
                        pass
                    # 多模态转换：历史/当前消息里带【图】标记的 user 消息 → OpenAI 多模态 content 数组
                    def _to_modal(m):
                        if m.get("role") != "user" or not isinstance(m.get("content"), str):
                            return m
                        if "【图】" not in m["content"]:
                            return m
                        txt = re.sub(r"(\n)?【图】\S+", "", m["content"]).strip() or "请看这张图片"
                        imgs = []
                        for p in re.findall(r"【图】(\S+)", m["content"]):
                            full = p if os.path.isabs(p) else os.path.join(DATA_DIR, p)
                            if not os.path.exists(full):
                                continue
                            try:
                                import PIL.Image as _PIL_IMG  # 可选压缩，失败则原图
                                _im = _PIL_IMG.open(full)
                                if _im.mode == "RGBA":
                                    _im = _im.convert("RGB")
                                _w, _h = _im.size
                                _max = 1280
                                if max(_w, _h) > _max:
                                    _r = _max / max(_w, _h)
                                    _im = _im.resize((int(_w * _r), int(_h * _r)))
                                import io
                                _buf = io.BytesIO()
                                _im.save(_buf, format="JPEG", quality=85)
                                _raw = _buf.getvalue()
                            except BaseException:
                                with open(full, "rb") as _f:
                                    _raw = _f.read()
                            imgs.append({"type": "image_url",
                                         "image_url": {"url": "data:image/jpeg;base64," +
                                                          base64.b64encode(_raw).decode("utf-8")}})
                        if not imgs:
                            return m
                        return {"role": "user", "content": [{"type": "text", "text": txt}] + imgs}

                    current_messages = [_to_modal(m) for m in rebuilt]
                    _need_vision = any(isinstance(m.get("content"), list) for m in current_messages)
                    ai_response = {"text": ""}

                    content_ref = {"col": None, "md": None, "stream": None, "row": None, "actions": None}
                    bubble_row, content_col = make_ai_bubble("▌", can_regenerate=False, content_ref=content_ref)
                    last_ai_content_ref["col"] = content_col
                    last_ai_content_ref["ref"] = content_ref
                    chat_history_display.controls.append(bubble_row)
                    page.update()

                    last_update_t = {"t": 0.0}
                    def on_chunk(text):
                        if gen_token["id"] != my_gen:
                            return  # 旧代次的流式回调直接丢弃
                        ai_response["text"] = text
                        now = time.time()
                        if now - last_update_t["t"] < 0.1:
                            return
                        last_update_t["t"] = now
                        try:
                            if content_ref.get("stream"):
                                content_ref["stream"].value = text if text else "▌"
                            page.update()
                        except Exception:
                            pass

                    def ai_thread():
                        nonlocal generation_active, stop_flag
                        generation_active = True
                        stop_flag = False
                        was_stopped = {"v": False}
                        try:
                            final_accum = call_ai_stream(current_messages, "auto", on_chunk, need_vision=_need_vision)
                            was_stopped["v"] = bool(stop_flag)
                            if final_accum is not None:
                                ai_response["text"] = final_accum
                        finally:
                            if gen_token["id"] == my_gen:
                                generation_active = False
                        if gen_token["id"] != my_gen:
                            return  # 过期线程，不再写界面/不保存历史
                        if was_stopped["v"] and ai_response["text"]:
                            ai_response["text"] = ai_response["text"].rstrip() + "〔未完成，等待继续〕"
                        content_ref["raw"] = ai_response["text"]
                        try:
                            final_text = ai_response["text"] if ai_response["text"] else "（无回应）"
                            clean_text, chart_html = extract_chart_block(final_text)
                            display_text = clean_text if clean_text else "（无回应）"
                            if content_ref.get("md") and content_ref.get("col"):
                                content_ref["md"].value = display_text
                                content_ref["col"].controls[0] = content_ref["md"]
                            if chart_html and content_ref["col"]:
                                def make_view(h=chart_html):
                                    def view(e):
                                        show_chart_overlay(h)
                                    return view
                                _svg_path = save_svg_chart(chart_html)
                                if _svg_path:
                                    content_ref["col"].controls.append(
                                        ft.Container(
                                            content=ft.Image(src=_svg_path, fit=ft.ImageFit.CONTAIN,
                                                             width=250, border_radius=12),
                                            on_click=make_view(), ink=True,
                                            border=ft.border.all(1, "#414868"),
                                            border_radius=12,
                                        ))
                                chart_btn = ft.Container(
                                    content=ft.Row([
                                        ft.Text("📊", size=16),
                                        ft.Text("查看图表", size=13, color="#FFCCCC"),
                                    ], spacing=4, tight=True),
                                    bgcolor="#24283B",
                                    border_radius=12,
                                    padding=ft.Padding(left=12, right=12, top=6, bottom=6),
                                    border=ft.border.all(1, "#6B4A3A"),
                                    on_click=make_view(),
                                    ink=True,
                                )
                                content_ref["col"].controls.append(chart_btn)
                            acts = content_ref.get("actions")
                            if acts:
                                for _a in acts:
                                    try:
                                        _a.visible = True
                                    except BaseException:
                                        pass
                        except Exception:
                            pass
                        send_btn.visible = True
                        stop_btn.visible = False
                        if ai_response["text"]:
                            save_chat_message(subject, "assistant", ai_response["text"])
                            update_chat_memory(subject, content, ai_response["text"])
                        update_chat_stats(subject)
                        # —— 长记忆：历史过长时后台压缩早期对话为摘要（不阻塞，失败静默）——
                        try:
                            _hh = load_chat_history(subject)
                            if sum(len(m.get("content", "") or "") for m in _hh) > 40000:
                                compress_old_history(subject, _hh)
                        except BaseException:
                            pass
                        # —— 断点续传闭环：续写完成后把「半截+续写」合并为一条历史 ——
                        if continuing["v"]:
                            continuing["v"] = False
                            try:
                                fp_c = get_chat_history_file(subject)
                                hs_c = load_jsonl(fp_c)
                                if len(hs_c) >= 3 and hs_c[-1].get("role") == "assistant" \
                                        and hs_c[-2].get("role") == "user" and hs_c[-3].get("role") == "assistant":
                                    half_c = hs_c[-3]["content"]
                                    cont_c = hs_c[-1]["content"]
                                    hs_c[-3]["content"] = (half_c.rstrip() + "\n\n" + cont_c).strip() if cont_c else half_c
                                    hs_c = hs_c[:-2]
                                    save_jsonl(fp_c, hs_c)
                            except BaseException:
                                pass
                        try:
                            _hs = load_chat_history(subject)
                            continue_btn.visible = bool(_hs and _hs[-1].get("role") == "assistant"
                                                        and "〔未完成，等待继续〕" in _hs[-1].get("content", ""))
                        except BaseException:
                            continue_btn.visible = False
                        try:
                            _looks_q = any(k in content for k in
                                           ("求", "怎么做", "怎么解", "这题", "题目", "为什么", "请讲", "？", "?"))
                            if subject != "总AI" and _looks_q:
                                show_toast("💡 点回答右下角的 📥，可把这道题收进错题本", "info")
                        except BaseException:
                            pass
                        # —— DeepTutor 闭环：识别"未掌握"信号 → 记录遗留问题 + 回写科目薄弱度 ——
                        try:
                            _p_ = load_user_profile()
                            _q_ = content or ""
                            if any(_s in _q_ for _s in ("不会", "不懂", "不明白", "错了", "做错", "选错", "蒙的", "忘了", "没懂", "卡住", "太难", "不理解", "没听懂", "怎么解", "为什么")):
                                _p_["last_question"] = _q_[-200:]
                                _sub_ = subject if subject != "总AI" else ""
                                if _sub_:
                                    _ws_ = _p_.setdefault("weak_subjects", {})
                                    _ws_[_sub_] = min(1.0, _ws_.get(_sub_, 0.2) + 0.15)
                                save_user_profile(_p_)
                        except BaseException:
                            pass
                        page.update()

                    threading.Thread(target=ai_thread, daemon=True).start()

                def stop_generation(e):
                    nonlocal stop_flag
                    stop_flag = True
                stop_btn.on_click = stop_generation

                continuing = {"v": False}

                def _continue_generation(e=None):
                    """真断点续传：从历史最后一条带〔未完成〕标记的半截消息继续写，
                    续写完成后自动与半截合并为一条完整记录。"""
                    if generation_active:
                        return
                    hs = load_chat_history(subject)
                    if not hs or hs[-1].get("role") != "assistant" or "〔未完成，等待继续〕" not in hs[-1].get("content", ""):
                        continue_btn.visible = False
                        page.update()
                        return
                    continuing["v"] = True
                    hs[-1]["content"] = hs[-1]["content"].replace("〔未完成，等待继续〕", "").rstrip()
                    try:
                        save_jsonl(get_chat_history_file(subject), hs)
                    except BaseException:
                        pass
                    # 原气泡更新为干净半截（去掉标记）
                    try:
                        _ref = last_ai_content_ref.get("ref")
                        if _ref and _ref.get("col"):
                            _half = hs[-1]["content"]
                            _ref["col"].controls.clear()
                            _md2 = ft.Markdown(value=_half, selectable=True,
                                                extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                                                code_theme="atom-one-dark",
                                                on_tap_link=lambda ev: page.launch_url(ev.data))
                            _ref["md"] = _md2
                            _ref["raw"] = _half
                            _ref["col"].controls.append(_md2)
                    except BaseException:
                        pass
                    handle_send("（继续）请直接接着上面没写完的讲解继续写，不要重复已经写过的内容，从断点处最后一个字接着往下写。")
                continue_btn.on_click = _continue_generation

                def clear_history(e):
                    fp = get_chat_history_file(subject)
                    save_jsonl(fp, [])
                    chat_history_display.controls.clear()
                    page.update()
                    show_toast("✅ 对话历史已清除", "green")

                # —— 图片按钮：选图插入对话（多模态发送，走视觉模型）——
                chat_img_btn = ft.Container(
                    content=ft.Icon(ft.Icons.IMAGE_OUTLINED, size=20, color="#BBBBBB"),
                    width=38, height=38, border_radius=19,
                    bgcolor="#24283B", border=ft.border.all(1, "#414868"),
                    alignment=ft.alignment.center,
                    on_click=lambda e: pick_chat_image(),
                    ink=True, tooltip="发图片（需要视觉模型）",
                )

                def on_chat_img_picked(e: ft.FilePickerResultEvent):
                    if not e.files:
                        return
                    saved = []
                    try:
                        _chat_dir = os.path.join(IMAGES_DIR, "chat")
                        os.makedirs(_chat_dir, exist_ok=True)
                        for _f in e.files:
                            _dest = os.path.join(_chat_dir, os.path.basename(_f.name))
                            shutil.copy2(_f.path, _dest)
                            saved.append(os.path.relpath(_dest, DATA_DIR))
                    except BaseException as _ex:
                        show_toast(f"图片保存失败：{str(_ex)[:30]}", "red")
                        return
                    if not saved:
                        return
                    cur = chat_input.value or ""
                    marks = "".join(f"\n【图】{p}" for p in saved)
                    chat_input.value = (cur + marks) if cur else marks.lstrip("\n")
                    page.update()
                    show_toast(f"已添加 {len(saved)} 张图片，按发送即可", "green")

                def pick_chat_image():
                    _pkr = ft.FilePicker(on_result=on_chat_img_picked)
                    page.overlay.append(_pkr)
                    page.update()
                    _pkr.pick_files(file_type=ft.FilePickerFileType.IMAGE, allow_multiple=True)

                result_col = ft.Column([
                    ft.Container(
                        content=ft.Row([
                            ft.IconButton(icon=ft.Icons.ARROW_BACK, icon_size=22,
                                          tooltip="返回",
                                          on_click=lambda e: (setattr(chat_dialog, 'visible', False), page.update())),
                            ft.Column([
                                ft.Text(f"💬 {display_name}", size=18, weight=ft.FontWeight.BOLD),
                                ft.Text(f"{_provider_name} · {_model_name}", size=11, color="#888888"),
                            ], spacing=2, expand=True),
                            ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, icon_size=20,
                                          tooltip="清除历史", on_click=clear_history),
                            ft.IconButton(icon=ft.Icons.CLOSE, icon_size=22,
                                          on_click=lambda e: (setattr(chat_dialog, 'visible', False), page.update())),
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        padding=ft.Padding(left=4, right=4, top=10, bottom=8),
                    ),
                    ft.Divider(height=1, color="#2A2E44"),
                    ft.Container(content=chat_history_display, expand=True, padding=ft.Padding(left=6, right=6, top=10, bottom=8)),
                    quick_row,
                    ft.Container(
                        content=ft.Row([
                            web_btn,
                            chat_img_btn,
                            chat_input,
                            send_btn,
                            stop_btn,
                            continue_btn,
                        ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.END),
                        padding=ft.Padding(left=6, right=6, top=8, bottom=10),
                    ),
                ], spacing=6, expand=True)

                if initial_message:
                    chat_input.value = initial_message
                if auto_send and initial_message:
                    def trigger():
                        time.sleep(0.6)
                        handle_send()
                    threading.Thread(target=trigger, daemon=True).start()
                return result_col

            mine_msg = ft.Text("", size=16)

            def _load_user_new_words():
                profile = load_user_profile()
                return profile.get("new_words", [])

            def _save_user_new_words(words_list):
                profile = load_user_profile()
                profile["new_words"] = words_list
                save_user_profile(profile)

            def _add_to_new_words(word):
                nw = _load_user_new_words()
                if word not in nw:
                    nw.append(word)
                    _save_user_new_words(nw)
                return nw

            def _remove_from_new_words(word):
                nw = _load_user_new_words()
                if word in nw:
                    nw.remove(word)
                    _save_user_new_words(nw)
                return nw

            def _needs_completion(w):
                if not w.get("phonetic") or not w.get("meaning"):
                    return True
                if not w.get("example") or not w.get("forms"):
                    return True
                if not w.get("grammar") and not w.get("phrases"):
                    return True
                return False

            def _fill_word_with_ai(word_data):
                word = word_data.get("word", "")
                if not word or not _needs_completion(word_data):
                    return word_data
                new_data = generate_word_info(word)
                if not new_data:
                    return None   # 失败：调用处负责提示，避免假成功
                with _vocab_rw_lock:
                    existing = load_jsonl(VOCAB_FILE)
                    for i, w in enumerate(existing):
                        if w.get("word", "").lower() == word.lower():
                            for k, v in new_data.items():
                                if k == "grammar":
                                    existing[i]["grammar"] = v if v else existing[i].get("grammar", {})
                                elif k == "phrases":
                                    existing[i]["phrases"] = v if v else existing[i].get("phrases", [])
                                elif v:
                                    existing[i][k] = v
                            word_data = existing[i]
                            break
                    save_jsonl(VOCAB_FILE, existing)
                return word_data

            def _open_word_detail(word_data, on_close=None):
                # 不再直接自动请求，防止卡死 UI
                word = word_data.get("word", "")
                phonetic = word_data.get("phonetic", "")
                meaning = word_data.get("meaning", "")
                example = word_data.get("example", "")
                forms = word_data.get("forms", "")
                grammar = word_data.get("grammar", {})
                phrases = word_data.get("phrases", [])
                content_children = []
                content_children.append(ft.Text(f"📖 {word}", size=24, weight=ft.FontWeight.BOLD))
                if phonetic:
                    content_children.append(ft.Text(f"🔊 {phonetic}", size=16, color="#A9B1D6"))
                if meaning:
                    content_children.append(ft.Text(meaning, size=16, color="#81C784"))
                if example:
                    content_children.append(ft.Text(f"例句：{example}", size=14, italic=True, color=ft.Colors.GREY_400))
                if forms:
                    forms_words = [f.strip() for f in forms.replace(',', ' ').split() if f.strip()]
                    if forms_words:
                        forms_row = ft.Row(spacing=8, wrap=True)
                        forms_row.controls.append(ft.Text("变形：", size=14, weight=ft.FontWeight.BOLD))
                        all_vocab_now = load_vocab_cached()
                        for fw in forms_words:
                            target_word_data = next((w for w in all_vocab_now if w.get("word", "").lower() == fw.lower()), None)
                            if target_word_data:
                                btn = ft.TextButton(
                                    text=fw,
                                    on_click=lambda e, wd=target_word_data: _open_word_detail(wd),
                                    style=ft.ButtonStyle(color="#A9B1D6",
                                                         text_style=ft.TextStyle(decoration=ft.TextDecoration.UNDERLINE)))
                            else:
                                def make_gen_click(fw_word):
                                    _gen_state = {"running": False}
                                    def on_click(e):
                                        if _gen_state["running"]:
                                            return   # 防抖：该词生成中不重复触发
                                        _cfg_now = load_ai_config()
                                        _info_now = PROVIDERS.get(_cfg_now.get("provider", "zhipu"), PROVIDERS["zhipu"])
                                        if not _cfg_now.get(_info_now["key_field"], "").strip():
                                            show_toast("⚠ 请先在 AI 设置中配置 API Key 再生成派生词", "red")
                                            return
                                        _gen_state["running"] = True
                                        _orig_text = e.control.text
                                        try:
                                            e.control.disabled = True
                                            e.control.text = "⏳ 生成中..."
                                        except BaseException:
                                            pass
                                        page.update()
                                        def _bg():
                                            try:
                                                new_d = generate_word_info(fw_word)
                                                if new_d:
                                                    with _vocab_rw_lock:
                                                        ev = load_jsonl(VOCAB_FILE)
                                                        if any(w.get("word", "").lower() == fw_word.lower() for w in ev):
                                                            show_toast(f"ℹ️ {fw_word} 已在词库中", "info")
                                                        else:
                                                            ev.append(new_d)
                                                            save_jsonl(VOCAB_FILE, ev)
                                                            show_toast(f"✅ 已生成并添加 {fw_word}", "green")
                                                else:
                                                    show_toast(f"❌ 生成 {fw_word} 失败：未返回有效信息（检查网络或 Key）", "red")
                                            except Exception as ex:
                                                show_toast(f"❌ 生成异常：{str(ex)[:40]}", "red")
                                            finally:
                                                _gen_state["running"] = False
                                                try:
                                                    e.control.disabled = False
                                                    e.control.text = _orig_text
                                                    page.update()
                                                except BaseException:
                                                    pass
                                        threading.Thread(target=_bg, daemon=True).start()
                                    return on_click
                                btn = ft.TextButton(
                                    text=fw, on_click=make_gen_click(fw),
                                    style=ft.ButtonStyle(color="#E0AF68",
                                                         text_style=ft.TextStyle(decoration=ft.TextDecoration.UNDERLINE)))
                            forms_row.controls.append(btn)
                        content_children.append(forms_row)
                if grammar:
                    gp_parts = []
                    if grammar.get("collocations"):
                        gp_parts.append(f"搭配：{', '.join(grammar['collocations'])}")
                    if grammar.get("notes"):
                        gp_parts.append(f"笔记：{' ; '.join(grammar['notes'])}")
                    if grammar.get("test_points"):
                        gp_parts.append(f"考点：{' ; '.join(grammar['test_points'])}")
                    if gp_parts:
                        content_children.append(ft.Text("📚 语法", size=14, weight=ft.FontWeight.BOLD))
                        for gp in gp_parts:
                            content_children.append(ft.Text(gp, size=13, color="#A9B1D6"))
                if phrases:
                    content_children.append(ft.Text("🔗 短语", size=14, weight=ft.FontWeight.BOLD))
                    for ph in phrases:
                        content_children.append(ft.Text(f"• {ph}", size=13, color="#4DB6AC"))

                # 学习记录：每次选择 会/不会/模糊 的时间与结果
                _hist = word_data.get("learning", {}).get("history", []) if isinstance(word_data.get("learning"), dict) else []
                _act_labels = {"know": "✅ 认识", "forget": "❌ 不认识", "fuzzy": "🤔 模糊",
                               "quiz_correct": "✅ 答对", "quiz_wrong": "❌ 答错"}
                _next_rev = word_data.get("learning", {}).get("next_review", "") if isinstance(word_data.get("learning"), dict) else ""
                _ease = word_data.get("learning", {}).get("ease", 2.5) if isinstance(word_data.get("learning"), dict) else 2.5
                if _hist:
                    content_children.append(ft.Divider(height=1))
                    content_children.append(ft.Text("⏱ 学习记录", size=14, weight=ft.FontWeight.BOLD))
                    for h in _hist[-8:][::-1]:
                        act = _act_labels.get(str(h.get("action", "")), str(h.get("action", "")))
                        content_children.append(
                            ft.Text(f"  {h.get('time', '')}  {act}",
                                    size=12, color=ft.Colors.GREY_400))
                    content_children.append(
                        ft.Text(f"  难度系数 {_ease} · 下次复习 {_next_rev or '—'}",
                                size=12, color="#E0AF68"))
                
                nw_set = set(_load_user_new_words())
                is_in_nw = word in nw_set

                def toggle_nw(e, w=word):
                    if w in _load_user_new_words():
                        _remove_from_new_words(w)
                        show_toast(f"已移出生词本：{w}", "info")
                    else:
                        _add_to_new_words(w)
                        show_toast(f"已加入生词本：{w}", "green")
                    page.close(dialog)
                    if on_close:
                        on_close()
                    page.update()

                content_children.append(
                    ft.Container(
                        content=ft.Text("✅ 已在生词本" if is_in_nw else "➕ 加入生词本",
                                        size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                        bgcolor="#66BB6A" if is_in_nw else "#7AA2F7",
                        border_radius=20,
                        padding=ft.Padding(left=16, right=16, top=8, bottom=8),
                        on_click=toggle_nw, ink=True))

                if _needs_completion(word_data):
                    ai_status = ft.Text("", size=13, color="#A9B1D6", italic=True)

                    def do_fill_ai(e):
                        _cfg_now = load_ai_config()
                        _info_now = PROVIDERS.get(_cfg_now.get("provider", "zhipu"), PROVIDERS["zhipu"])
                        if not _cfg_now.get(_info_now["key_field"], "").strip():
                            ai_status.value = "⚠ 请先在「AI 设置」中配置 API Key 再使用补齐"
                            show_toast("⚠ 请先在 AI 设置中配置 API Key 再使用补齐", "red")
                            page.update()
                            return
                        if getattr(ai_btn, "_running", False):
                            ai_status.value = "⏳ 正在生成中，请稍候（勿重复点击）..."
                            page.update()
                            return
                        ai_btn._running = True
                        ai_status.value = "⏳ 正在调用 AI 生成词条信息，请稍候..."
                        ai_btn.content.value = "⏳ 请求中..."
                        ai_btn.disabled = True
                        page.update()
                        def _bg():
                            try:
                                filled_data = _fill_word_with_ai(word_data)
                                if filled_data is None:
                                    ai_status.value = "❌ 补齐失败：未返回有效信息（检查网络或 Key）"
                                    show_toast("❌ AI 补齐失败：未返回有效信息（检查网络或 Key）", "red")
                                elif filled_data is word_data:
                                    ai_status.value = "ℹ️ 该单词信息已完整，无需补齐"
                                    show_toast("ℹ️ 该单词信息已完整，无需补齐", "info")
                                else:
                                    page.close(dialog)
                                    _open_word_detail(filled_data, on_close=on_close)
                                    show_toast("✅ 补齐成功", "green")
                            except Exception as ex:
                                ai_status.value = f"❌ 补齐异常：{str(ex)[:40]}"
                                show_toast(f"❌ 补齐异常：{str(ex)[:40]}", "red")
                            finally:
                                try:
                                    ai_btn._running = False
                                    ai_btn.content.value = "🤖 使用 AI 补齐缺失信息"
                                    ai_btn.disabled = False
                                    page.update()
                                except BaseException:
                                    pass
                        threading.Thread(target=_bg, daemon=True).start()

                    ai_btn = ft.ElevatedButton(
                        "🤖 使用 AI 补齐缺失信息",
                        icon=ft.Icons.AUTO_AWESOME,
                        bgcolor="#24283B",
                        color="#E0AF68",
                        on_click=do_fill_ai
                    )
                    content_children.append(ai_btn)
                    content_children.append(ai_status)

                dialog = ft.AlertDialog(
                    title=ft.Text(""),
                    content=ft.Container(
                        content=ft.Column(content_children, spacing=8, scroll=ft.ScrollMode.AUTO),
                        width=400, height=None, padding=10),
                    actions=[ft.TextButton("关闭", on_click=lambda e: page.close(dialog))])
                page.open(dialog)
                page.update()

            def build_vocab_page(subject):
                settings = load_vocab_settings()
                tab_index = [0]
                tab_content = ft.Container(expand=True)
                tab_row = ft.Row(spacing=6)
                tab_defs = [("📚", "词库"), ("⭐", "生词"), ("🧠", "学习"), ("✍️", "考核"), ("❌", "错词")]
                tab_buttons = []

                def set_tab(idx):
                    tab_index[0] = idx
                    for i, btn in enumerate(tab_buttons):
                        btn.bgcolor = "#7AA2F7" if i == idx else "#24283B"
                        for c in btn.content.controls:
                            if isinstance(c, ft.Text):
                                c.color = "#FFFFFF" if i == idx else "#CCCCCC"
                    render_tab()
                    page.update()

                def make_tab_btn(icon, label, idx):
                    return ft.Container(
                        content=ft.Row([
                            ft.Text(icon, size=14),
                            ft.Text(label, size=13, weight=ft.FontWeight.BOLD, color="#CCCCCC"),
                        ], spacing=3, tight=True),
                        padding=ft.Padding(left=10, right=10, top=6, bottom=6),
                        border_radius=10, bgcolor="#24283B",
                        on_click=lambda e, i=idx: set_tab(i), ink=True)

                for i, (ic, lb) in enumerate(tab_defs):
                    btn = make_tab_btn(ic, lb, i)
                    tab_buttons.append(btn)
                    tab_row.controls.append(btn)

                def build_lib_tab():
                    all_vocab = load_jsonl(VOCAB_FILE)
                    all_words = sorted(all_vocab, key=lambda x: x.get("word", "").lower())
                    vocab_list_view = ft.ListView(spacing=2, expand=True)
                    search_field = ft.TextField(label="🔍 搜索单词", hint_text="英文前缀或中文关键词", expand=True)
                    count_text = ft.Text(f"共 {len(all_words)} 词", size=13, color=ft.Colors.GREY_500)

                    def _render_list(keyword=""):
                        vocab_list_view.controls.clear()
                        kw = keyword.strip()
                        kws = kw.lower()
                        filtered = all_words
                        if kws:
                            has_chinese = bool(re.search(r'[\u4e00-\u9fff]', kws))
                            if has_chinese:
                                filtered = [w for w in all_words
                                            if kws in w.get("word", "").lower()
                                            or kws in w.get("meaning", "")]
                            else:
                                filtered = [w for w in all_words
                                            if w.get("word", "").lower().startswith(kws)]
                        
                        BATCH = 100
                        total = len(filtered)
                        shown = min(BATCH, total)
                        count_text.value = f"共 {total} 词" + (f"（前 {shown} 条）" if total > BATCH else "")
                        nw_set = set(_load_user_new_words())
                        for w in filtered[:BATCH]:
                            word = w.get("word", "")
                            phonetic = w.get("phonetic", "")
                            meaning_short = w.get("meaning", "")[:50]
                            is_new = word in nw_set

                            def _show_detail(e, wd=w):
                                _open_word_detail(wd, on_close=lambda: _render_list(search_field.value))

                            tile = ft.ListTile(
                                leading=ft.Icon(ft.Icons.BOOKMARK if is_new else ft.Icons.CIRCLE, size=16,
                                                color="#E0AF68" if is_new else ft.Colors.GREY_500),
                                title=ft.Text(f"{word}  {phonetic}", size=15),
                                subtitle=ft.Text(meaning_short, size=12, color=ft.Colors.GREY_400),
                                trailing=ft.IconButton(icon=ft.Icons.PLAY_ARROW, icon_size=20,
                                                       tooltip="查看详情", on_click=_show_detail),
                                on_click=_show_detail, dense=True)
                            vocab_list_view.controls.append(tile)
                        page.update()

                    search_field.on_change = lambda e: _render_list(search_field.value)
                    add_word_input = ft.TextField(label="新增单词", hint_text="英文或中文", expand=True)

                    def _add_custom_word(e):
                        raw = add_word_input.value.strip()
                        if not raw:
                            return
                        word = raw.lower()
                        existing = load_jsonl(VOCAB_FILE)
                        if any(w.get("word", "").lower() == word for w in existing):
                            show_toast(f"单词 {word} 已存在", "info")
                            add_word_input.value = ""
                            return
                        new_entry = {"word": word, "phonetic": "", "meaning": "", "example": "",
                                     "forms": "", "grammar": {}, "phrases": []}
                        ensure_learning_field(new_entry)
                        new_entry["learning"]["synced"] = False   # 新词未同步手环
                        existing.append(new_entry)
                        save_jsonl(VOCAB_FILE, existing)
                        show_toast(f"已添加 {word}，点开自动补齐", "green")
                        add_word_input.value = ""
                        nonlocal all_vocab, all_words
                        all_vocab = load_jsonl(VOCAB_FILE)
                        all_words = sorted(all_vocab, key=lambda x: x.get("word", "").lower())
                        _render_list(search_field.value)

                    _render_list()
                    import_picker = ft.FilePicker(on_result=lambda e: on_import_result(e))
                    page.overlay.append(import_picker)

                    def on_import_result(e: ft.FilePickerResultEvent):
                        if e.files:
                            file_path = e.files[0].path
                            if not file_path.lower().endswith('.jsonl'):
                                show_toast("请选择 .jsonl 文件", "red")
                                return
                            try:
                                imported = load_jsonl(file_path)
                                if not imported:
                                    show_toast("文件内容为空", "red")
                                    return
                                existing = load_jsonl(VOCAB_FILE)
                                existing_words = {w.get("word", "").lower() for w in existing}
                                added = 0
                                for w in imported:
                                    wd = w.get("word", "").lower()
                                    if not wd or wd in existing_words:
                                        continue
                                    ensure_learning_field(w)
                                    w["learning"]["synced"] = False   # 导入的新词未同步手环
                                    existing.append(w)
                                    existing_words.add(wd)
                                    added += 1
                                save_jsonl(VOCAB_FILE, existing)
                                show_toast(f"✅ 已追加 {added} 个词", "green")
                                nonlocal all_vocab, all_words
                                all_vocab = load_jsonl(VOCAB_FILE)
                                all_words = sorted(all_vocab, key=lambda x: x.get("word", "").lower())
                                _render_list(search_field.value)
                            except Exception as ex:
                                show_toast(f"❌ 导入失败: {str(ex)[:50]}", "red")

                    import_btn = ft.ElevatedButton(
                        "📥 导入词汇文件", icon=ft.Icons.UPLOAD_FILE,
                        on_click=lambda e: import_picker.pick_files(
                            file_type=ft.FilePickerFileType.CUSTOM, allowed_extensions=["jsonl"]))

                    export_picker = ft.FilePicker(on_result=lambda e: on_export_result(e))
                    page.overlay.append(export_picker)

                    def on_export_result(e: ft.FilePickerResultEvent):
                        if e.path:
                            try:
                                n = export_wordbook(e.path)
                                show_toast(f"✅ 已导出 {n} 词", "green")
                            except Exception as ex:
                                show_toast(f"❌ 导出失败: {str(ex)[:50]}", "red")

                    export_btn = ft.ElevatedButton(
                        "📤 导出单词本", icon=ft.Icons.DOWNLOAD,
                        on_click=lambda e: export_picker.save_file(
                            dialog_title="导出单词本",
                            file_name="vocabulary.jsonl",
                            file_type=ft.FilePickerFileType.CUSTOM,
                            allowed_extensions=["jsonl"]))
                    return ft.Column([
                        ft.Row([import_btn, export_btn], spacing=8),
                        ft.Text("点击单词查看详情，缺字段自动 AI 补齐", size=13, color=ft.Colors.GREY_500),
                        ft.Row([search_field, count_text], spacing=10),
                        ft.Divider(height=1),
                        ft.Container(content=vocab_list_view, expand=True),
                        ft.Divider(height=1),
                        ft.Row([add_word_input, ft.ElevatedButton("添加", on_click=_add_custom_word)], spacing=10),
                    ], spacing=8, expand=True)

                def build_nw_tab():
                    nw_list_view = ft.ListView(spacing=2, expand=True)

                    def refresh_nw():
                        nw_list_view.controls.clear()
                        user_nw2 = set(_load_user_new_words())
                        all_v2 = load_jsonl(VOCAB_FILE)
                        nw2 = sorted([w for w in all_v2 if w.get("word", "") in user_nw2],
                                     key=lambda x: x.get("word", "").lower())
                        if not nw2:
                            nw_list_view.controls.append(ft.Container(
                                content=ft.Text("  生词本还是空的\n  在词库中点开单词，点「加入生词本」即可",
                                                size=14, color=ft.Colors.GREY_500), padding=20))
                        else:
                            for w in nw2:
                                word = w.get("word", "")
                                tile = ft.ListTile(
                                    leading=ft.Icon(ft.Icons.BOOKMARK, size=18, color="#E0AF68"),
                                    title=ft.Text(f"{word}  {w.get('phonetic', '')}", size=15),
                                    subtitle=ft.Text(w.get("meaning", "")[:50], size=12, color=ft.Colors.GREY_400),
                                    trailing=ft.IconButton(
                                        icon=ft.Icons.DELETE_OUTLINE, icon_size=18,
                                        on_click=lambda e, ww=word: (
                                            _remove_from_new_words(ww),
                                            show_toast(f"已移出：{ww}", "info"), refresh_nw())),
                                    on_click=lambda e, wd=w: _open_word_detail(wd, on_close=refresh_nw),
                                    dense=True)
                                nw_list_view.controls.append(tile)
                        page.update()

                    refresh_nw()
                    return ft.Column([
                        ft.Text(f"你标记的待背生词", size=13, color=ft.Colors.GREY_500),
                        ft.Divider(height=1),
                        ft.Container(content=nw_list_view, expand=True),
                    ], spacing=8, expand=True)

                def build_study_tab():
                    all_words = load_jsonl(VOCAB_FILE)
                    now = datetime.now()
                    pool = []
                    for w in all_words:
                        ensure_learning_field(w)
                        L = w["learning"]
                        base = 1.0
                        base += L.get("wrong_count", 0) * 2.5
                        base += max(0, 7 - L.get("level", 0)) * 1.2
                        nxt = L.get("next_review", "")
                        if nxt:
                            try:
                                d = datetime.strptime(nxt, "%Y-%m-%d")
                                if d <= now:
                                    base *= 3.0
                            except BaseException:
                                pass
                        last = L.get("last_review", "")
                        if last:
                            try:
                                dt = datetime.strptime(last, "%Y-%m-%d %H:%M:%S")
                                days_since = (now - dt).days
                                if days_since > 30:
                                    base *= 4.0
                                elif days_since > 14:
                                    base *= 2.0
                            except BaseException:
                                pass
                        if L.get("level", 0) >= 6:
                            base *= 0.3
                        pool.append([w, base])

                    state = {"current": None, "flipped": False, "seen": {}, "learned": 0}
                    card_area = ft.Container(expand=True)
                    counter_text = ft.Text("", size=14, color=ft.Colors.GREY_500)
                    action_area = ft.Container()

                    def pick_next():
                        if not pool:
                            return None
                        words = [p[0] for p in pool]
                        weights = []
                        for w, base in pool:
                            wd = w.get("word", "")
                            seen_n = state["seen"].get(wd, 0)
                            weights.append(base / (1 + seen_n * 2))
                        total = sum(weights)
                        if total <= 0:
                            return random.choice(words)
                        r = random.random() * total
                        acc = 0
                        for w, wt in zip(words, weights):
                            acc += wt
                            if r <= acc:
                                return w
                        return words[-1]

                    def render_card():
                        card_area.content = None
                        action_area.content = None
                        if not pool:
                            card_area.content = ft.Container(
                                content=ft.Column([
                                    ft.Text("📚", size=60),
                                    ft.Text("词库是空的", size=18, color=ft.Colors.GREY_500),
                                    ft.Text("先去「词库」tab 添加单词", size=13, color=ft.Colors.GREY_500),
                                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                    alignment=ft.MainAxisAlignment.CENTER, spacing=10),
                                alignment=ft.alignment.center, expand=True)
                            counter_text.value = ""
                            page.update()
                            return
                        if state["current"] is None:
                            state["current"] = pick_next()
                            state["flipped"] = False
                        w = state["current"]
                        if w is None:
                            return
                        word = w.get("word", "")
                        phonetic = w.get("phonetic", "")
                        meaning = w.get("meaning", "")
                        example = w.get("example", "")
                        forms = w.get("forms", "")
                        L = w.get("learning", {})
                        level = L.get("level", 0)
                        wrong_n = L.get("wrong_count", 0)
                        counter_text.value = f"已学 {state['learned']} 张 · 等级 {level}/7 · 错 {wrong_n}"
                        if not state["flipped"]:
                            front = ft.Container(
                                content=ft.Column([
                                    ft.Text("🔊", size=28),
                                    ft.Text(word, size=42, weight=ft.FontWeight.BOLD,
                                            text_align=ft.TextAlign.CENTER),
                                    ft.Container(height=20),
                                    ft.Text("点击卡片显示释义" if wrong_n == 0
                                            else f"这个词你错过 {wrong_n} 次",
                                            size=13, color=ft.Colors.GREY_500),
                                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                    alignment=ft.MainAxisAlignment.CENTER, spacing=10),
                                alignment=ft.alignment.center, expand=True,
                                bgcolor="#24283B", border_radius=20,
                                border=ft.border.all(1, ft.Colors.WHITE10),
                                padding=30, ink=True,
                                on_click=lambda e: (state.update({"flipped": True}), render_card()))
                            card_area.content = front
                            action_area.content = ft.Row([
                                ft.ElevatedButton("显示答案", icon=ft.Icons.VISIBILITY,
                                                  on_click=lambda e: (state.update({"flipped": True}), render_card()),
                                                  bgcolor="#7AA2F7", color="#FFFFFF", expand=True)
                            ], spacing=10)
                        else:
                            back = ft.Container(
                                content=ft.Column([
                                    ft.Text(word, size=30, weight=ft.FontWeight.BOLD),
                                    ft.Text(phonetic, size=16, color="#7AA2F7") if phonetic else ft.Text(""),
                                    ft.Divider(),
                                    ft.Text(meaning, size=18, color="#81C784"),
                                    ft.Text(f"例句：{example}", size=13, italic=True,
                                            color=ft.Colors.GREY_400) if example else ft.Text(""),
                                    ft.Text(f"变形：{forms}", size=13,
                                            color=ft.Colors.GREY_400) if forms else ft.Text(""),
                                ], spacing=8, scroll=ft.ScrollMode.AUTO),
                                alignment=ft.alignment.top_left,
                                bgcolor="#24283B", border_radius=20,
                                border=ft.border.all(1, ft.Colors.WHITE10),
                                padding=20, expand=True)
                            card_area.content = back
                            action_area.content = ft.Row([
                                ft.ElevatedButton("❌ 不认识", on_click=lambda e: mark("forget"),
                                                  bgcolor="#EF5350", color="#FFFFFF", expand=True),
                                ft.ElevatedButton("🤔 模糊", on_click=lambda e: mark("fuzzy"),
                                                  bgcolor="#E0AF68", color="#FFFFFF", expand=True),
                                ft.ElevatedButton("✅ 认识", on_click=lambda e: mark("know"),
                                                  bgcolor="#66BB6A", color="#FFFFFF", expand=True),
                            ], spacing=10)
                        page.update()

                    def mark(result):
                        w = state["current"]
                        if not w:
                            return
                        word = w.get("word", "")
                        update_word_learning(word, result)
                        log_learning_event("vocab_study", "英语", kp=word,
                                           detail=result, correct=(result == "know"))
                        state["learned"] += 1
                        state["seen"][word] = state["seen"].get(word, 0) + 1
                        all_now = load_jsonl(VOCAB_FILE)
                        for i, p in enumerate(pool):
                            if p[0].get("word", "") == word:
                                for nw in all_now:
                                    if nw.get("word", "") == word:
                                        pool[i][0] = nw
                                        break
                                L2 = pool[i][0].get("learning", {})
                                base = 1.0
                                base += L2.get("wrong_count", 0) * 2.5
                                base += max(0, 7 - L2.get("level", 0)) * 1.2
                                if L2.get("level", 0) >= 6:
                                    base *= 0.3
                                pool[i][1] = base
                                break
                        state["current"] = None
                        state["flipped"] = False
                        render_card()

                    render_card()
                    return ft.Column([
                        ft.Row([counter_text], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Container(content=card_area, expand=True),
                        action_area,
                    ], spacing=12, expand=True)

                def build_quiz_tab():
                    today_review = get_today_review_words(50)
                    if not today_review:
                        return ft.Container(
                            content=ft.Column([
                                ft.Text("📭", size=60),
                                ft.Text("今天没有需要考核的词", size=18, color=ft.Colors.GREY_500),
                                ft.Text("先去「学习」tab 学几个新词吧", size=13, color=ft.Colors.GREY_500),
                            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                alignment=ft.MainAxisAlignment.CENTER, spacing=10),
                            alignment=ft.alignment.center, expand=True)
                    queue = today_review[:20]
                    state = {"idx": 0, "answered": False}
                    quiz_area = ft.Container(expand=True)
                    counter_text = ft.Text("", size=15, weight=ft.FontWeight.BOLD)
                    score_text = ft.Text("", size=13, color=ft.Colors.GREY_500)
                    score = {"correct": 0, "total": 0}

                    def next_question():
                        state["answered"] = False
                        state["idx"] += 1
                        render_question()

                    def render_question():
                        quiz_area.content = None
                        if state["idx"] >= len(queue):
                            quiz_area.content = ft.Container(
                                content=ft.Column([
                                    ft.Text("🏆", size=60),
                                    ft.Text("考核完成！", size=22, weight=ft.FontWeight.BOLD, color="#81C784"),
                                    ft.Text(f"正确率 {score['correct']}/{score['total']}", size=16, color=ft.Colors.GREY_400),
                                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                    alignment=ft.MainAxisAlignment.CENTER, spacing=10),
                                alignment=ft.alignment.center, expand=True)
                            page.update()
                            return
                        w = queue[state["idx"]]
                        word = w.get("word", "")
                        meaning = w.get("meaning", "")
                        phonetic = w.get("phonetic", "")
                        counter_text.value = f"{state['idx']+1} / {len(queue)}"
                        score_text.value = f"✅ {score['correct']} / {score['total']}"
                        mode = settings.get("quiz_mode", "mix")
                        if mode == "mix":
                            mode = random.choice(["word2meaning", "meaning2word"])
                        if mode == "word2meaning":
                            options = [meaning]
                            others = random.sample([x for x in queue if x.get("word", "") != word],
                                                   min(3, max(0, len(queue) - 1))) if len(queue) > 1 else []
                            for o in others:
                                options.append(o.get("meaning", ""))
                            random.shuffle(options)
                            correct = meaning
                            opt_btns = []
                            result_text = ft.Text("", size=14)

                            def make_click(opt, is_correct):
                                def click(e):
                                    if state["answered"]:
                                        return
                                    state["answered"] = True
                                    score["total"] += 1
                                    if is_correct:
                                        score["correct"] += 1
                                        update_word_learning(word, "quiz_correct")
                                        result_text.value = "✅ 答对了！"
                                        result_text.color = "#66BB6A"
                                    else:
                                        update_word_learning(word, "quiz_wrong")
                                        result_text.value = f"❌ 错了，正确答案：{correct}"
                                        result_text.color = "#EF5350"
                                    log_learning_event("vocab_test", "英语", kp=word,
                                                       detail="word2meaning", correct=is_correct)
                                    page.update()
                                return click

                            for opt in options:
                                b = ft.ElevatedButton(opt, on_click=make_click(opt, opt == correct),
                                                      expand=True, bgcolor="#24283B", color="#FFFFFF")
                                opt_btns.append(b)
                            quiz_area.content = ft.Column([
                                ft.Text("选择正确的中文释义", size=13, color=ft.Colors.GREY_500),
                                ft.Text(word, size=36, weight=ft.FontWeight.BOLD),
                                ft.Text(phonetic, size=14, color="#7AA2F7") if phonetic else ft.Text(""),
                                ft.Container(height=20),
                                ft.Column(opt_btns, spacing=8),
                                ft.Container(height=10),
                                result_text,
                                ft.Container(height=10),
                                ft.Row([ft.ElevatedButton("下一题", on_click=lambda e: next_question(),
                                                          bgcolor="#7AA2F7", color="#FFFFFF")],
                                       alignment=ft.MainAxisAlignment.CENTER),
                            ], spacing=8, scroll=ft.ScrollMode.AUTO)
                        elif mode == "meaning2word":
                            options = [word]
                            others = random.sample([x for x in queue if x.get("word", "") != word],
                                                   min(3, max(0, len(queue) - 1))) if len(queue) > 1 else []
                            for o in others:
                                options.append(o.get("word", ""))
                            random.shuffle(options)
                            correct = word
                            opt_btns = []
                            result_text = ft.Text("", size=14)

                            def make_click2(opt, is_correct):
                                def click(e):
                                    if state["answered"]:
                                        return
                                    state["answered"] = True
                                    score["total"] += 1
                                    if is_correct:
                                        score["correct"] += 1
                                        update_word_learning(word, "quiz_correct")
                                        result_text.value = "✅ 答对了！"
                                        result_text.color = "#66BB6A"
                                    else:
                                        update_word_learning(word, "quiz_wrong")
                                        result_text.value = f"❌ 错了，正确答案：{correct}"
                                        result_text.color = "#EF5350"
                                    log_learning_event("vocab_test", "英语", kp=word,
                                                       detail="meaning2word", correct=is_correct)
                                    page.update()
                                return click

                            for opt in options:
                                b = ft.ElevatedButton(opt, on_click=make_click2(opt, opt == correct),
                                                      expand=True, bgcolor="#24283B", color="#FFFFFF")
                                opt_btns.append(b)
                            quiz_area.content = ft.Column([
                                ft.Text("选择正确的英文单词", size=13, color=ft.Colors.GREY_500),
                                ft.Text(meaning, size=22, weight=ft.FontWeight.BOLD),
                                ft.Container(height=20),
                                ft.Column(opt_btns, spacing=8),
                                ft.Container(height=10),
                                result_text,
                                ft.Container(height=10),
                                ft.Row([ft.ElevatedButton("下一题", on_click=lambda e: next_question(),
                                                          bgcolor="#7AA2F7", color="#FFFFFF")],
                                       alignment=ft.MainAxisAlignment.CENTER),
                            ], spacing=8, scroll=ft.ScrollMode.AUTO)
                        else:
                            input_field = ft.TextField(label="输入英文单词", autofocus=True)
                            result_text = ft.Text("", size=14)

                            def check(e):
                                if state["answered"]:
                                    return
                                state["answered"] = True
                                user_ans = input_field.value.strip().lower()
                                score["total"] += 1
                                is_correct = user_ans == word.lower()
                                if is_correct:
                                    score["correct"] += 1
                                    update_word_learning(word, "quiz_correct")
                                    result_text.value = "✅ 拼写正确！"
                                    result_text.color = "#66BB6A"
                                else:
                                    update_word_learning(word, "quiz_wrong")
                                    result_text.value = f"❌ 正确拼写：{word}"
                                    result_text.color = "#EF5350"
                                log_learning_event("vocab_test", "英语", kp=word,
                                                   detail="spelling", correct=is_correct)
                                page.update()

                            quiz_area.content = ft.Column([
                                ft.Text("根据释义拼写单词", size=13, color=ft.Colors.GREY_500),
                                ft.Text(meaning, size=20, weight=ft.FontWeight.BOLD),
                                ft.Container(height=20),
                                input_field,
                                ft.Container(height=10),
                                ft.Row([
                                    ft.ElevatedButton("提交", on_click=check, bgcolor="#7AA2F7", color="#FFFFFF"),
                                    ft.ElevatedButton("下一题", on_click=lambda e: next_question(),
                                                      bgcolor="#24283B", color="#FFFFFF"),
                                ], spacing=10, alignment=ft.MainAxisAlignment.CENTER),
                                ft.Container(height=10),
                                result_text,
                            ], spacing=8, scroll=ft.ScrollMode.AUTO)
                        page.update()

                    render_question()
                    return ft.Column([
                        ft.Row([counter_text, score_text], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Container(content=quiz_area, expand=True),
                    ], spacing=12, expand=True)

                def build_wrong_tab():
                    wrong_words = get_wrong_words(200)
                    ww_list = ft.ListView(spacing=2, expand=True)
                    if not wrong_words:
                        ww_list.controls.append(ft.Container(
                            content=ft.Text("  暂无错词，去「考核」tab 练练吧", size=14, color=ft.Colors.GREY_500),
                            padding=20))
                    else:
                        for w in wrong_words:
                            word = w.get("word", "")
                            L = w.get("learning", {})
                            wrong_count = L.get("wrong_count", 0)
                            tile = ft.ListTile(
                                leading=ft.Container(
                                    content=ft.Text(str(wrong_count), size=12, color=ft.Colors.WHITE,
                                                    weight=ft.FontWeight.BOLD),
                                    width=30, height=30, border_radius=15, bgcolor="#EF5350",
                                    alignment=ft.alignment.center),
                                title=ft.Text(f"{word}  {w.get('phonetic', '')}", size=15),
                                subtitle=ft.Text(w.get("meaning", "")[:50], size=12, color=ft.Colors.GREY_400),
                                on_click=lambda e, wd=w: _open_word_detail(wd, on_close=lambda: build_wrong_tab()),
                                dense=True)
                            ww_list.controls.append(tile)
                    return ft.Column([
                        ft.Text(f"错词本（{len(wrong_words)} 个）", size=13, color=ft.Colors.GREY_500),
                        ft.Divider(height=1),
                        ft.Container(content=ww_list, expand=True),
                    ], spacing=8, expand=True)

                def render_tab():
                    idx = tab_index[0]
                    if idx == 0:
                        tab_content.content = build_lib_tab()
                    elif idx == 1:
                        tab_content.content = build_nw_tab()
                    elif idx == 2:
                        tab_content.content = build_study_tab()
                    elif idx == 3:
                        tab_content.content = build_quiz_tab()
                    elif idx == 4:
                        tab_content.content = build_wrong_tab()

                set_tab(0)
                return ft.Column([
                    ft.Text("📖 单词本", size=20, weight=ft.FontWeight.BOLD),
                    tab_row,
                    ft.Divider(height=1),
                    ft.Container(content=tab_content, expand=True),
                ], spacing=8, expand=True)

            def build_error_list_page(subject):
                items = load_jsonl(ERRORS_FILE)
                subject_items = [i for i in items if i.get("subject") == subject]
                subject_items.sort(key=lambda x: x.get("timestamp", 0), reverse=True)

                def clean_time_str(t):
                    if not t:
                        return ""
                    return re.sub(r'\s+', ' ', t).strip()

                search_input = ft.TextField(
                    label="🔍 搜索错题",
                    hint_text="多个词用空格分隔，如：导数 单调性 易错",
                    expand=True, border_color="#7AA2F7", border_width=2)
                local_search_btn = ft.ElevatedButton(
                    "搜索", on_click=lambda e: do_local_search(), icon=ft.Icons.SEARCH,
                    bgcolor="#7AA2F7", color=ft.Colors.WHITE)
                ai_search_btn = ft.TextButton(
                    "🤖 AI 深度搜索", on_click=lambda e: perform_search(e))
                search_status = ft.Text("", size=13, color=ft.Colors.GREY_500)
                search_row = ft.Row([search_input, local_search_btn, ai_search_btn], spacing=10)
                list_view = ft.ListView(spacing=10, expand=True)

                def render_list(display_list=None, matched_count=None):
                    list_view.controls.clear()
                    if display_list is None:
                        display_list = [(it, None) for it in subject_items]
                    if not display_list:
                        list_view.controls.append(ft.Container(
                            content=ft.Text("  暂无错题", size=16, color=ft.Colors.GREY_500),
                            padding=20))
                        page.update()
                        return
                    divider_added = False
                    for idx, pair in enumerate(display_list):
                        try:
                            item, score = pair
                            is_matched = score is not None and score > 0
                            if matched_count is not None and not is_matched and not divider_added and idx > 0:
                                divider_added = True
                                list_view.controls.append(ft.Container(
                                    content=ft.Text("──── 以下为其他错题 ────", size=12,
                                                    color=ft.Colors.GREY_600,
                                                    text_align=ft.TextAlign.CENTER),
                                    alignment=ft.alignment.center,
                                    padding=ft.Padding(left=0, right=0, top=14, bottom=8)))
                            original = item.get("original", "")
                            mistake = item.get("mistake", "")
                            answer = item.get("answer", "")
                            idea = item.get("idea", "")
                            q_media = item.get("question_media", []) or item.get("question_images", [])
                            ts_clean = clean_time_str(item.get("time", ""))
                            tags = item.get("tags", [])
                            shown_tags = tags[:3]
                            tag_text = "、".join(shown_tags) if shown_tags else "未分类"
                            if len(tags) > 3:
                                tag_text += f" +{len(tags) - 3}"
                            is_highlighted = is_matched
                            bg_color = "#3D3A28" if is_highlighted else "#1F1F26"
                            status = item.get("status", "未看")
                            status_color = {"未看": "#9E9E9E", "已看": "#4CAF50",
                                            "重要": "#F44336", "已掌握": "#2196F3"}.get(status, "#9E9E9E")
                            status_dot = ft.Container(width=12, height=12, border_radius=6,
                                                      bgcolor=status_color, tooltip=status)
                            thumb_container = None
                            if q_media and len(q_media) > 0:
                                first_img = q_media[0]
                                full_path = first_img if os.path.isabs(first_img) else os.path.join(DATA_DIR, first_img)
                                if os.path.exists(full_path):
                                    try:
                                        thumb_img = ft.Image(src=full_path, width=80, height=80,
                                                             fit=ft.ImageFit.COVER)
                                        thumb_container = ft.GestureDetector(
                                            content=ft.Container(
                                                content=thumb_img, width=80, height=80,
                                                border_radius=10,
                                                clip_behavior=ft.ClipBehavior.ANTI_ALIAS),
                                            on_long_press=lambda e, paths=q_media: show_image_gallery(paths, 0))
                                    except Exception as e:
                                        print(f"缩略图加载失败: {e}")
                                else:
                                    thumb_container = ft.Container(
                                        width=80, height=80, border_radius=10,
                                        bgcolor="#2A2E44", alignment=ft.alignment.center,
                                        content=ft.Text("🖼️", size=28, opacity=0.4))
                            detail_lines = []
                            if original:
                                detail_lines.append(f"📝 {original[:80]}")
                            if mistake:
                                detail_lines.append(f"❌ {mistake[:80]}")
                            if answer:
                                detail_lines.append(f"✅ {answer[:80]}")
                            if idea:
                                detail_lines.append(f"💡 {idea[:80]}")
                            if q_media:
                                detail_lines.append(f"🖼️ 包含 {len(q_media)} 张图片")
                            if not detail_lines:
                                detail_lines.append("点击查看详情")
                            detail_text = "\n".join(detail_lines[:2])
                            tag_display = ft.Container(
                                content=ft.Text(f"🏷️ {tag_text}", size=11, color=ft.Colors.GREY_400),
                                padding=ft.Padding(left=6, right=6, top=2, bottom=2),
                                bgcolor="#2A2E44", border_radius=8)

                            def make_show_detail_card(item_data=item):
                                def show(e):
                                    detail_children = []
                                    detail_children.append(ft.Text("📋 错题详情", size=20,
                                                                   weight=ft.FontWeight.BOLD))
                                    time_str = clean_time_str(item_data.get("time", ""))
                                    detail_children.append(
                                        ft.Text(f"科目：{item_data.get('subject', '未知')}  时间：{time_str}",
                                                size=14, color=ft.Colors.GREY_400))
                                    orig_val = item_data.get("original", "") or item_data.get("question", "")
                                    if orig_val:
                                        detail_children.append(
                                            ft.Text(f"📝 题目：{clean_latex(orig_val)}", size=15, selectable=True))
                                    if item_data.get("mistake"):
                                        detail_children.append(
                                            ft.Text(f"❌ 错因：{item_data['mistake']}", size=14,
                                                    color="#EF9A9A", selectable=True))
                                    if item_data.get("answer"):
                                        detail_children.append(
                                            ft.Text(f"✅ 答案：{clean_latex(item_data['answer'])}",
                                                    size=14, color="#A5D6A7", selectable=True))
                                    if item_data.get("idea"):
                                        detail_children.append(
                                            ft.Text(f"💡 理解：{item_data['idea']}",
                                                    size=14, color="#90CAF9", selectable=True))
                                    tags_now = item_data.get("tags", [])
                                    if tags_now:
                                        tag_chips = ft.Row(spacing=6, wrap=True)
                                        for t in tags_now:
                                            tag_chips.controls.append(ft.Container(
                                                content=ft.Text(t, size=12, color="#FFCCBC"),
                                                bgcolor="#24283B", border_radius=10,
                                                padding=ft.Padding(left=8, right=8, top=3, bottom=3),
                                                border=ft.border.all(1, "#6B4A3A")))
                                        detail_children.append(
                                            ft.Text(f"🏷️ 标签（{len(tags_now)}个）：", size=13,
                                                    color=ft.Colors.GREY_400))
                                        detail_children.append(tag_chips)
                                    all_media = []
                                    all_media.extend(item_data.get("question_media", []))
                                    all_media.extend(item_data.get("original_media", []))
                                    all_media.extend(item_data.get("answer_media", []))
                                    all_media.extend(item_data.get("idea_media", []))
                                    unique_media = []
                                    seen = set()
                                    for p in all_media:
                                        if p not in seen:
                                            seen.add(p)
                                            unique_media.append(p)
                                    if unique_media:
                                        detail_children.append(ft.Divider(height=1, color=ft.Colors.GREY_700))
                                        detail_children.append(
                                            ft.Text(f"🖼️ 图片附件（{len(unique_media)}张，点击查看）",
                                                    size=14, weight=ft.FontWeight.BOLD))
                                        img_row = ft.Row(spacing=8, wrap=True)
                                        for img_path in unique_media:
                                            full_path = img_path if os.path.isabs(img_path) else os.path.join(DATA_DIR, img_path)
                                            if os.path.exists(full_path):
                                                try:
                                                    img = ft.Container(
                                                        content=ft.Image(src=full_path, width=100, height=100,
                                                                         fit=ft.ImageFit.COVER, border_radius=8),
                                                        on_click=lambda e, paths=unique_media,
                                                                       idx=unique_media.index(img_path): show_image_gallery(paths, idx),
                                                        ink=True, border_radius=8)
                                                    img_row.controls.append(img)
                                                except BaseException:
                                                    pass
                                        if img_row.controls:
                                            detail_children.append(img_row)

                                    def open_edit(e):
                                        page.close(detail_dlg)
                                        make_show_detail(item_data)(e)

                                    def open_ask_teacher(e):
                                        page.close(detail_dlg)
                                        subj_ask = item_data.get("subject", "总AI")
                                        orig_val2 = item_data.get("original", "") or item_data.get("question", "")
                                        prompt = f"""我在复习这道错题，请你用适合我的方式讲讲：

📝 原题：{orig_val2}
❌ 我错在：{item_data.get('mistake', '')}
✅ 标准答案：{item_data.get('answer', '')}
💡 我的理解：{item_data.get('idea', '')}
🏷️ 标签：{', '.join(item_data.get('tags', []))}

请按以下步骤回答：
1. 先指出我的理解或做法哪里有问题
2. 用我容易懂的方式把这道题讲一遍
3. 告诉我这类题的通用解法
4. 出一两道类似的题，验证我是否真的懂了"""
                                        log_learning_event("ask_teacher", subj_ask,
                                                           kp=item_data.get("tags", [""])[0] if item_data.get("tags") else "",
                                                           detail=f"问老师：{orig_val2[:60]}")
                                        add_error_memory(subj_ask,
                                                         summary=f"{orig_val2[:80]} | 错因：{item_data.get('mistake', '')[:60]}",
                                                         knowledge_point=item_data.get("tags", [""])[0] if item_data.get("tags") else "",
                                                         discussed=True)
                                        open_chat(subj_ask, initial_message=prompt, auto_send=True)

                                    def open_mm_view(e):
                                        kp_title = ""
                                        try:
                                            _tg = item_data.get("tags", []) or []
                                            _subj = item_data.get("subject", subject)
                                            for t in _tg:
                                                if t and str(t) != _subj:
                                                    kp_title = str(t)
                                                    break
                                            if not kp_title and item_data.get("idea"):
                                                kp_title = str(item_data["idea"]).split("，")[0][:12]
                                        except BaseException:
                                            kp_title = ""
                                        if not kp_title:
                                            show_toast("该错题还没有知识点标签，先点一次 AI 理解/标签后再试", "orange")
                                            return
                                        page.close(detail_dlg)
                                        _MM_HIGHLIGHT["kp"] = kp_title
                                        open_function_page(item_data.get("subject", subject), "思维导图")

                                    action_row = ft.Row([
                                        ft.ElevatedButton("🎓 问老师", on_click=open_ask_teacher,
                                                          icon=ft.Icons.SCHOOL, bgcolor="#7AA2F7",
                                                          color=ft.Colors.WHITE),
                                        ft.ElevatedButton("🧭 导图", on_click=open_mm_view,
                                                          icon=ft.Icons.ACCOUNT_TREE),
                                        ft.ElevatedButton("✏️ 编辑", on_click=open_edit, icon=ft.Icons.EDIT),
                                        ft.TextButton("关闭", on_click=lambda ev: page.close(detail_dlg)),
                                    ], alignment=ft.MainAxisAlignment.END, spacing=8)
                                    detail_dlg = ft.AlertDialog(
                                        title=ft.Text(""),
                                        content=ft.Container(
                                            content=ft.Column(detail_children, spacing=8,
                                                              scroll=ft.ScrollMode.AUTO),
                                            width=450, height=500, padding=10),
                                        actions=[action_row])
                                    page.open(detail_dlg)
                                    page.update()
                                return show

                            def make_show_detail(item_data=item):
                                def show(e):
                                    orig_val = item_data.get("original", "")
                                    mis_val = item_data.get("mistake", "")
                                    ans_val = item_data.get("answer", "")
                                    idea_val = item_data.get("idea", "")
                                    q_val = item_data.get("question", "")
                                    time_val = item_data.get("time", "")
                                    ts_int = item_data.get("timestamp", 0)
                                    current_status = item_data.get("status", "未看")
                                    orig_input = ft.TextField(label="题目 🔒（锁定中）", value=orig_val,
                                                              multiline=True, min_lines=2, disabled=True)
                                    mis_input = ft.TextField(label="错因", value=mis_val,
                                                             multiline=True, min_lines=2)
                                    ans_input = ft.TextField(label="答案", value=ans_val,
                                                             multiline=True, min_lines=2)
                                    idea_input = ft.TextField(label="我的理解 ✏️（可编辑）", value=idea_val,
                                                              multiline=True, min_lines=2)
                                    tags_input_edit = ft.TextField(
                                        label="标签（逗号分隔）",
                                        value=", ".join(item_data.get("tags", [])),
                                        multiline=True, min_lines=2)
                                    status_dropdown = ft.Dropdown(
                                        label="标记状态",
                                        options=[ft.dropdown.Option("未看"), ft.dropdown.Option("已看"),
                                                 ft.dropdown.Option("重要"), ft.dropdown.Option("已掌握")],
                                        value=current_status)
                                    unlock_btn = ft.TextButton("🔓 解锁题目", icon=ft.Icons.LOCK_OPEN)

                                    def toggle_unlock(e):
                                        if orig_input.disabled:
                                            orig_input.disabled = False
                                            orig_input.label = "题目 ✏️（已解锁）"
                                            unlock_btn.text = "🔒 锁定题目"
                                            unlock_btn.icon = ft.Icons.LOCK
                                        else:
                                            orig_input.disabled = True
                                            orig_input.label = "题目 🔒（锁定中）"
                                            unlock_btn.text = "🔓 解锁题目"
                                            unlock_btn.icon = ft.Icons.LOCK_OPEN
                                        page.update()

                                    unlock_btn.on_click = toggle_unlock

                                    def save_edit(e):
                                        all_items = load_jsonl(ERRORS_FILE)
                                        new_tags = [t.strip() for t in tags_input_edit.value.split(",") if t.strip()]
                                        if not new_tags:
                                            new_tags = [item_data.get("subject", "未知")]
                                        elif item_data.get("subject") not in new_tags:
                                            new_tags.insert(0, item_data.get("subject", "未知"))
                                        for d in all_items:
                                            if d.get("timestamp") == ts_int or (
                                                    d.get("question") == q_val and d.get("time") == time_val):
                                                d["original"] = orig_input.value
                                                d["question"] = orig_input.value
                                                d["mistake"] = mis_input.value
                                                d["answer"] = ans_input.value
                                                d["idea"] = idea_input.value
                                                d["tags"] = new_tags
                                                d["tags_done"] = True
                                                d["status"] = status_dropdown.value
                                                d["update_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
                                                break
                                        save_jsonl(ERRORS_FILE, all_items)
                                        page.close(edit_dlg)
                                        show_toast("✅ 已保存", "green")
                                        open_function_page(subject, "错题本")
                                        page.update()

                                    def delete_item(e):
                                        all_items = load_jsonl(ERRORS_FILE)
                                        filtered = [d for d in all_items if not (
                                                d.get("timestamp") == ts_int or (
                                                d.get("question") == q_val and d.get("time") == time_val))]
                                        save_jsonl(ERRORS_FILE, filtered)
                                        page.close(edit_dlg)
                                        show_toast("🗑️ 已删除", "green")
                                        open_function_page(subject, "错题本")
                                        page.update()

                                    edit_dlg = ft.AlertDialog(
                                        title=ft.Text("编辑错题"),
                                        content=ft.Column([
                                            orig_input,
                                            ft.Row([unlock_btn], alignment=ft.MainAxisAlignment.END),
                                            mis_input,
                                            ans_input,
                                            idea_input,
                                            tags_input_edit,
                                            status_dropdown,
                                        ], scroll=ft.ScrollMode.AUTO, width=400, height=480),
                                        actions=[
                                            ft.TextButton("🗑️ 删除", on_click=delete_item),
                                            ft.TextButton("取消", on_click=lambda e: page.close(edit_dlg)),
                                            ft.ElevatedButton("💾 保存", on_click=save_edit),
                                        ])
                                    page.open(edit_dlg)
                                return show

                            inner_children = [
                                ft.Row([
                                    status_dot,
                                    ft.Text(f"📋 {ts_clean}", size=12, color=ft.Colors.GREY_500,
                                            expand=True, max_lines=1,
                                            overflow=ft.TextOverflow.ELLIPSIS),
                                    tag_display,
                                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ]
                            if thumb_container is not None:
                                inner_children.append(thumb_container)
                            inner_children.append(
                                ft.Text(detail_text, size=14, max_lines=2, color=ft.Colors.WHITE70))
                            container = ft.Container(
                                content=ft.Column(inner_children, spacing=4),
                                padding=12, border_radius=14, bgcolor=bg_color,
                                border=ft.border.all(2 if is_highlighted else 1,
                                                    "#7AA2F7" if is_highlighted else "#4A4A55"),
                                on_click=make_show_detail_card(item), ink=True)
                            container.key = str(idx)
                            list_view.controls.append(container)
                        except Exception as e:
                            print(f"⚠️ 加载错题条目失败（idx={idx}），已跳过，错误: {e}")
                            continue
                    if not list_view.controls:
                        list_view.controls.append(ft.Container(
                            content=ft.Text("  数据加载失败，请检查数据文件", size=16,
                                            color="#EF5350"), padding=20))
                    page.update()

                def do_local_search(e=None):
                    q = search_input.value.strip()
                    if not q:
                        render_list(None)
                        search_status.value = ""
                        search_status.color = ft.Colors.GREY_500
                        page.update()
                        return
                    _, score_map = weighted_search_errors(subject_items, q)
                    if not score_map:
                        search_status.value = f"❌ 本地没有匹配「{q}」的错题（下方显示全部）"
                        search_status.color = "#E0AF68"
                        render_list(None)
                        page.update()
                        return
                    ranked = sorted(score_map.items(), key=lambda x: -x[1])
                    matched = [(subject_items[i], s) for i, s in ranked]
                    matched_idx = set(i for i, _ in ranked)
                    unmatched = [(it, None) for i, it in enumerate(subject_items) if i not in matched_idx]
                    render_list(matched + unmatched, matched_count=len(matched))
                    search_status.value = f"✅ 匹配 {len(matched)} 条（已置顶），其余 {len(unmatched)} 条在下"
                    search_status.color = "#81C784"
                    page.update()

                def perform_search(e):
                    query = search_input.value.strip()
                    if not query:
                        search_status.value = "请输入搜索内容"
                        search_status.color = "#E0AF68"
                        page.update()
                        return
                    search_status.value = f"⏳ AI 正在分析：{query}"
                    search_status.color = "#7AA2F7"
                    page.update()

                    def do_search():
                        api_key, api_url, api_model, _v = endpoint_for("smart")
                        if not api_key:
                            search_status.value = "❌ 未配置API密钥"
                            search_status.color = "#EF5350"
                            page.update()
                            return
                        prompt = f"""请分析以下错题列表，找出与用户查询匹配的题目。
用户查询：{query}

错题列表：
{chr(10).join([f"[{i+1}] {e.get('original', '')[:100]}" for i, e in enumerate(subject_items)])}

返回匹配的题目序号（从1开始），JSON数组格式，如：[1, 3, 5]
只返回JSON数组。"""
                        try:
                            resp = requests.post(api_url,
                                                 headers={"Authorization": f"Bearer {api_key}",
                                                          "Content-Type": "application/json"},
                                                 json={"model": api_model,
                                                       "messages": [{"role": "user", "content": prompt}],
                                                       "temperature": 0.3, "max_tokens": 500}, timeout=30)
                            if resp.status_code == 200:
                                content = resp.json()["choices"][0]["message"]["content"]
                                try:
                                    matches = json.loads(content)
                                except BaseException:
                                    match = re.search(r'\[[0-9,\s]*\]', content)
                                    matches = json.loads(match.group()) if match else []
                                if matches and isinstance(matches, list):
                                    highlight_indices = [m - 1 for m in matches if 1 <= m <= len(subject_items)]
                                    if highlight_indices:
                                        matched_items = [(subject_items[i], 99) for i in highlight_indices]
                                        other_items = [(item, None) for i, item in enumerate(subject_items)
                                                       if i not in highlight_indices]
                                        render_list(matched_items + other_items)
                                        search_status.value = f"✅ AI 找到 {len(highlight_indices)} 个匹配（已置顶）"
                                        search_status.color = "#81C784"
                                    else:
                                        search_status.value = "❌ 未找到匹配的错题"
                                        search_status.color = "#E0AF68"
                                else:
                                    search_status.value = "❌ AI未返回有效结果"
                                    search_status.color = "#EF5350"
                            else:
                                search_status.value = f"❌ API错误: {resp.status_code}"
                                search_status.color = "#EF5350"
                        except Exception as ex:
                            search_status.value = f"❌ 搜索失败: {str(ex)[:50]}"
                            search_status.color = "#EF5350"
                        page.update()

                    threading.Thread(target=do_search, daemon=True).start()

                search_input.on_submit = lambda e: do_local_search()
                render_list()
                return ft.Column([
                    ft.Text("📋 错题本", size=20, weight=ft.FontWeight.BOLD),
                    ft.Text("🔍 本地加权搜索（多个词空格分隔）｜AI 深度搜索可选", size=13,
                            color="#7AA2F7"),
                    search_row,
                    search_status,
                    ft.Divider(height=1),
                    ft.Container(content=list_view, expand=True),
                ], spacing=8, expand=True)

            def build_note_list_page(subject):
                items = load_jsonl(NOTES_FILE)
                subject_items = [i for i in items if i.get("subject") == subject]
                # 新笔记置顶：统一按真实时间倒序（兼容 timestamp 缺失/字符串的旧数据）
                subject_items.sort(key=_note_sort_key, reverse=True)
                list_view = ft.ListView(spacing=10, expand=True)
                if not subject_items:
                    list_view.controls.append(ft.Container(
                        content=ft.Text("  暂无笔记", size=16, color=ft.Colors.GREY_500),
                        padding=20))
                else:
                    for item in subject_items:
                        try:
                            content = item.get("content", "")
                            images = item.get("images", []) or item.get("media", [])
                            ts = item.get("time", "")
                            thumb_container = None
                            if images and len(images) > 0:
                                first_img = images[0]
                                full_path = first_img if os.path.isabs(first_img) else os.path.join(DATA_DIR, first_img)
                                if os.path.exists(full_path):
                                    try:
                                        thumb_img = ft.Image(src=full_path, width=80, height=80,
                                                             fit=ft.ImageFit.COVER)
                                        thumb_container = ft.GestureDetector(
                                            content=ft.Container(
                                                content=thumb_img, width=80, height=80,
                                                border_radius=10,
                                                clip_behavior=ft.ClipBehavior.ANTI_ALIAS),
                                            on_long_press=lambda e, paths=images: show_image_gallery(paths, 0))
                                    except BaseException:
                                        pass

                            def make_show_note(item_data=item):
                                def show(e):
                                    note_ts = item_data.get("time", "")
                                    note_content = item_data.get("content", "")
                                    note_images = item_data.get("images", []) or item_data.get("media", [])
                                    detail_children = [ft.Text("📝 笔记详情", size=20,
                                                               weight=ft.FontWeight.BOLD),
                                                       ft.Text(f"时间：{note_ts}", size=13,
                                                               color=ft.Colors.GREY_500)]
                                    if note_content:
                                        detail_children.append(ft.Text(note_content, size=15, selectable=True))
                                    else:
                                        detail_children.append(ft.Text("（无文字内容）", size=14,
                                                                       color=ft.Colors.GREY_500))
                                    if note_images:
                                        detail_children.append(ft.Divider(height=1, color=ft.Colors.GREY_700))
                                        detail_children.append(
                                            ft.Text(f"🖼️ 图片附件（{len(note_images)}张）", size=14,
                                                    weight=ft.FontWeight.BOLD))
                                        img_row = ft.Row(spacing=8, wrap=True)
                                        for img_path in note_images:
                                            full_path = img_path if os.path.isabs(img_path) else os.path.join(DATA_DIR, img_path)
                                            if os.path.exists(full_path):
                                                try:
                                                    img = ft.Container(
                                                        content=ft.Image(src=full_path, width=100, height=100,
                                                                         fit=ft.ImageFit.COVER, border_radius=8),
                                                        on_click=lambda e, paths=note_images,
                                                                       idx=note_images.index(img_path): show_image_gallery(paths, idx, on_close=lambda: show(None)),
                                                        ink=True, border_radius=8)
                                                    img_row.controls.append(img)
                                                except BaseException:
                                                    pass
                                        if img_row.controls:
                                            detail_children.append(img_row)

                                    def open_edit(e):
                                        page.close(detail_dlg)
                                        make_edit_note(item_data)(e)

                                    def open_mm_from_note(e):
                                        kp_title = ""
                                        try:
                                            note_content_txt = str(item_data.get("content", "") or "")
                                            tree_now = load_mindmap(subject)
                                            if tree_now:
                                                for c_nd in (tree_now.get("children") or []):
                                                    t_nd = str(c_nd.get("title", ""))
                                                    if t_nd and (t_nd in note_content_txt or
                                                                (note_content_txt and t_nd[:4] in note_content_txt)):
                                                        kp_title = t_nd
                                                        break
                                                if not kp_title and (tree_now.get("children") or []):
                                                    kp_title = tree_now["children"][0].get("title", "")
                                        except BaseException:
                                            kp_title = ""
                                        page.close(detail_dlg)
                                        _MM_HIGHLIGHT["kp"] = kp_title
                                        open_function_page(subject, "思维导图")

                                    action_row = ft.Row([
                                        ft.ElevatedButton("🧭 导图", on_click=open_mm_from_note,
                                                          icon=ft.Icons.ACCOUNT_TREE),
                                        ft.ElevatedButton("✏️ 编辑", on_click=open_edit, icon=ft.Icons.EDIT),
                                        ft.TextButton("关闭", on_click=lambda ev: page.close(detail_dlg)),
                                    ], alignment=ft.MainAxisAlignment.END)
                                    detail_dlg = ft.AlertDialog(
                                        title=ft.Text(""),
                                        content=ft.Container(
                                            content=ft.Column(detail_children, spacing=8,
                                                              scroll=ft.ScrollMode.AUTO),
                                            width=450, height=500, padding=10),
                                        actions=[action_row])
                                    page.open(detail_dlg)
                                    page.update()
                                return show

                            def make_edit_note(item_data=item):
                                def show(e):
                                    current_ts = item_data.get("timestamp", 0)
                                    content_input = ft.TextField(label="笔记内容",
                                                                 value=item_data.get("content", ""),
                                                                 multiline=True, min_lines=4)

                                    def save_edit(e):
                                        all_items = load_jsonl(NOTES_FILE)
                                        for d in all_items:
                                            if d.get("timestamp") == current_ts:
                                                d["content"] = content_input.value
                                                break
                                        save_jsonl(NOTES_FILE, all_items)
                                        page.close(edit_dlg)
                                        show_toast("✅ 已保存", "green")
                                        open_function_page(subject, "笔记本")
                                        page.update()

                                    def delete_item(e):
                                        all_items = load_jsonl(NOTES_FILE)
                                        filtered = [d for d in all_items if d.get("timestamp") != current_ts]
                                        save_jsonl(NOTES_FILE, filtered)
                                        page.close(edit_dlg)
                                        show_toast("🗑️ 已删除", "green")
                                        open_function_page(subject, "笔记本")
                                        page.update()

                                    edit_dlg = ft.AlertDialog(
                                        title=ft.Text("编辑笔记"),
                                        content=ft.Column([content_input], scroll=ft.ScrollMode.AUTO,
                                                          width=400, height=300),
                                        actions=[
                                            ft.TextButton("🗑️ 删除", on_click=delete_item),
                                            ft.TextButton("取消", on_click=lambda e: page.close(edit_dlg)),
                                            ft.ElevatedButton("💾 保存", on_click=save_edit),
                                        ])
                                    page.open(edit_dlg)
                                    page.update()
                                return show

                            preview = content[:80] if content else "（空）"
                            img_hint = f" 🖼️{len(images)}张" if images else ""
                            inner_children = [
                                ft.Row([
                                    ft.Text(f"📝 {ts}{img_hint}", size=13, color=ft.Colors.GREY_500),
                                    ft.TextButton("编辑", on_click=make_edit_note()),
                                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ]
                            if thumb_container is not None:
                                inner_children.append(thumb_container)
                            inner_children.append(ft.Text(preview, size=14, max_lines=3))
                            list_view.controls.append(ft.Container(
                                content=ft.Column(inner_children, spacing=4),
                                padding=12, border_radius=14,
                                bgcolor="#2A2620", border=ft.border.all(1, "#6B5838"),
                                on_click=make_show_note(), ink=True))
                        except Exception as e:
                            print(f"⚠️ 加载笔记条目失败，已跳过: {e}")
                            continue

                def make_upload_note():
                    """笔记本页上传入口：文字/图片均可，保存后即时刷新列表（新笔记置顶）"""
                    up_subject = subject
                    up_content = ft.TextField(label="笔记内容（可选）", multiline=True, min_lines=3,
                                              border_radius=12, filled=True)
                    up_files = []
                    up_picker_col, up_files, reset_picker = make_file_picker_button(
                        "📷 图片（可多选）", "image", on_complete=None)

                    def do_upload(e):
                        nonlocal up_files
                        content = up_content.value.strip()
                        if not content and not up_files:
                            show_toast("请输入内容或选图片", "red")
                            return
                        save_note(up_subject, content, list(up_files))
                        page.close(up_dlg)
                        show_toast(f"✅ {up_subject} 笔记已保存（已置顶）", "green")
                        open_function_page(up_subject, "笔记本")
                        page.update()

                    up_dlg = ft.AlertDialog(
                        title=ft.Text("📝 上传笔记"),
                        content=ft.Column([
                            ft.Text(f"学科：{up_subject}", size=14, color=ft.Colors.GREY_400),
                            up_content, up_picker_col,
                        ], width=420, spacing=8, scroll=ft.ScrollMode.AUTO),
                        actions=[
                            ft.TextButton("取消", on_click=lambda e: page.close(up_dlg)),
                            ft.ElevatedButton("💾 保存", on_click=do_upload),
                        ])
                    page.open(up_dlg)
                    page.update()

                upload_bar = ft.Row([
                    ft.ElevatedButton("➕ 上传笔记", on_click=lambda e: make_upload_note(),
                                      icon=ft.Icons.ADD),
                    ft.Text(f"共 {len(subject_items)} 条", size=13, color=ft.Colors.GREY_500),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                return ft.Column([upload_bar, ft.Divider(height=1), list_view], spacing=8, expand=True)

            def build_mindmap_page(subject, highlight_kp=None):
                """学科思维导图：XMind 式横向展开 + 缩放/平移 + 知识点挂错题可点开详情"""
                tree = build_mindmap(subject)
                view_state = {"scale": 1.0, "dx": 0.0, "dy": 0.0,
                              "base_scale": 1.0, "base_dx": 0.0, "base_dy": 0.0,
                              "layout": {}, "open": set(), "grown": False,
                              "grow_nodes": [], "hl": highlight_kp,
                              "rebuild_count": 0}
                # 掌握度：画像薄弱度 + 复习卡熟练度 + 错题数 综合（0~1，越高越熟）
                def mastery_for(kp_title):
                    try:
                        prof = load_user_profile()
                        wk = prof.get("weak_knowledge", {}) or {}
                        weak = wk.get(kp_title)
                        if weak is None:
                            for k, v in wk.items():
                                if kp_title and (k in kp_title or kp_title in k):
                                    weak = v
                                    break
                        base = 1.0 if weak is None else max(0.0, 1.0 - float(weak) * 1.6)
                        rc = 0.0
                        try:
                            cards = load_jsonl(REVIEW_CARDS_FILE)
                            prs = [float(c.get("proficiency", 0)) for c in cards
                                   if c.get("knowledge_point") and
                                   (c["knowledge_point"] == kp_title or
                                    kp_title in str(c.get("knowledge_point", "")))]
                            if prs:
                                rc = min(1.0, sum(prs) / len(prs) / 100.0)
                        except BaseException:
                            pass
                        return min(1.0, base * 0.6 + rc * 0.4)
                    except BaseException:
                        return None

                # 深度优先布局：返回该节点子树的垂直范围 (top, bottom)，节点置于自身子树垂直中心
                NODE_W, NODE_H, DX, DY = 180, 46, 210, 24

                def layout_node(node, x, y, depth=0):
                    if not node.get("children") or node["title"] in view_state["open"]:
                        node["_x"], node["_y"] = x, y
                        view_state["layout"][node["title"]] = (x, y, depth)
                        return y, y + NODE_H
                    node["_x"], node["_y"] = x, y
                    cy = y
                    y = y + NODE_H + 12
                    sub_tops, sub_bots = [], []
                    for ch in node.get("children", []):
                        t, b = layout_node(ch, x + DX, y, depth + 1)
                        sub_tops.append(t)
                        sub_bots.append(b)
                        y = b + DY
                    top = min(sub_tops) - 12
                    bottom = max(sub_bots) + 12
                    center = (top + bottom) / 2
                    node["_y"] = center - NODE_H / 2
                    view_state["layout"][node["title"]] = (x, center - NODE_H / 2, depth)
                    return top, bottom

                layout_node(tree, 24, 40)
                max_x = max(v[0] for v in view_state["layout"].values()) + NODE_W + 60
                max_y = max(v[1] for v in view_state["layout"].values()) + NODE_H + 60
                LAYOUT_W, LAYOUT_H = max(700, int(max_x)), max(600, int(max_y))
                _mm_root_ref = {"v": None}

                def mm_error_detail(kp_title):
                    errors = [e for e in load_jsonl(ERRORS_FILE)
                              if e.get("subject") == subject and
                              ((e.get("kp") or "").strip() == kp_title or
                               (str(e.get("tags", [])[0]) if e.get("tags") else "") == kp_title)]
                    if not errors:
                        show_toast("该知识点暂无错题", "grey")
                        return
                    children = [ft.Text(f"{kp_title} · 共{len(errors)}道错题", size=17,
                                        weight=ft.FontWeight.BOLD)]
                    for i, e in enumerate(errors[:20]):
                        orig = (e.get("original", "") or e.get("question", ""))[:90]
                        mis = str(e.get("mistake", ""))[:60]
                        ans = str(e.get("answer", ""))[:60]
                        card = ft.Container(
                            content=ft.Column([
                                ft.Text(f"[{i+1}] {orig}", size=13),
                                ft.Text(f"❌ 错因：{mis}", size=12, color="#EF5350") if mis else ft.Text(""),
                                ft.Text(f"✅ 正解：{ans}", size=12, color="#81C784") if ans else ft.Text(""),
                            ], spacing=3),
                            padding=10, border_radius=10, bgcolor="#1F1F26",
                            border=ft.border.all(1, "#414868"),
                            on_click=lambda ev, idx=i: show_error_detail_dialog(subject, kp_title, idx),
                            ink=True)
                        children.append(card)
                    dlg = ft.AlertDialog(
                        title=ft.Text("🧩 知识点错题"),
                        content=ft.Container(
                            content=ft.Column(children, spacing=8, scroll=ft.ScrollMode.AUTO),
                            width=460, height=500, padding=10),
                        actions=[ft.TextButton("关闭", on_click=lambda e: page.close(dlg))])
                    page.open(dlg)
                    page.update()

                def show_error_detail_dialog(subject2, kp2, idx2):
                    errors = [e for e in load_jsonl(ERRORS_FILE)
                              if e.get("subject") == subject2 and
                              ((e.get("kp") or "").strip() == kp2 or
                               (str(e.get("tags", [])[0]) if e.get("tags") else "") == kp2)]
                    if not (0 <= idx2 < len(errors)):
                        return
                    e = errors[idx2]
                    body = [
                        ft.Text("📄 题目", size=15, weight=ft.FontWeight.BOLD),
                        ft.Text(str(e.get("original", "") or e.get("question", "")), size=14,
                                selectable=True),
                    ]
                    if e.get("mistake"):
                        body += [ft.Divider(height=1, color="#33364D"),
                                 ft.Text("❌ 我的错误", size=15, weight=ft.FontWeight.BOLD),
                                 ft.Text(str(e["mistake"]), size=14, selectable=True)]
                    if e.get("answer"):
                        body += [ft.Divider(height=1, color="#33364D"),
                                 ft.Text("✅ 正确答案", size=15, weight=ft.FontWeight.BOLD),
                                 ft.Text(str(e["answer"]), size=14, selectable=True)]
                    if e.get("analysis") or e.get("note"):
                        body += [ft.Divider(height=1, color="#33364D"),
                                 ft.Text("💡 解析", size=15, weight=ft.FontWeight.BOLD),
                                 ft.Text(str(e.get("analysis", "") or e.get("note", "")), size=13,
                                         selectable=True)]
                    dlg = ft.AlertDialog(
                        title=ft.Text(f"错题 {idx2+1}"),
                        content=ft.Container(
                            content=ft.Column(body, spacing=6, scroll=ft.ScrollMode.AUTO),
                            width=480, height=520, padding=10),
                        actions=[ft.TextButton("关闭", on_click=lambda e: page.close(dlg))])
                    page.open(dlg)
                    page.update()

                def add_kp_dialog(parent_title):
                    kp_input = ft.TextField(label="知识点名称", hint_text="例如：离子共存的条件判断",
                                            autofocus=True)
                    def do_add(e):
                        name = kp_input.value.strip()
                        if not name:
                            return
                        t2 = load_mindmap(subject) or {"title": subject, "children": []}
                        if parent_title == subject:
                            t2.setdefault("children", []).append(
                                {"title": name, "children": [], "kp": name, "count": 0})
                        else:
                            for nd in t2.get("children", []):
                                if nd.get("title") == parent_title:
                                    nd.setdefault("children", []).append(
                                        {"title": name, "children": [], "kp": name, "count": 0})
                                    break
                        save_mindmap(subject, t2)
                        page.close(dlg)
                        show_toast("✅ 已添加知识点", "green")
                        open_function_page(subject, "思维导图")
                        page.update()
                    dlg = ft.AlertDialog(
                        title=ft.Text("➕ 添加知识点（挂到「" + parent_title + "」）"),
                        content=ft.Column([kp_input], width=360),
                        actions=[
                            ft.TextButton("取消", on_click=lambda e: page.close(dlg)),
                            ft.ElevatedButton("添加", on_click=do_add)])
                    page.open(dlg)
                    page.update()

                def make_node_widget(title, depth, count, is_root=False, kind=None, kp=""):
                    box_w, box_h = NODE_W, NODE_H
                    colors = ["#7AA2F7", "#BB9AF7", "#7DCFFF", "#9ECE6A", "#FF9E64", "#F7768E"]
                    is_hl = (not is_root) and view_state.get("hl") and view_state["hl"] == title
                    if is_root:
                        bg, border, fg = "#414868", "#7AA2F7", "#FFFFFF"
                    elif kind == "notes":
                        bg, border, fg = "#1F2A22", "#4DB6AC", "#A7E8DC"   # 笔记层：绿色
                    elif kind == "errors":
                        bg, border, fg = "#2A1F22", "#F7768E", "#FFB3C1"  # 错题层：玫红
                    else:
                        bg, border, fg = "#1A1B26", colors[min(depth, len(colors) - 1)], "#E0E3F0"
                    badge = f"  ·{count}题" if count else ""
                    if is_hl:
                        border, fg = "#FFD54F", "#FFECB3"
                        bg = "#3B3110"
                        badge = (badge + " ·定位") if badge else " ·定位"
                    elif kind is None and not is_root:
                        # 世界树掌握度：不会的知识点暗淡，会的点亮
                        mv = mastery_for(title)
                        if mv is not None:
                            if mv < 0.35:
                                bg, border, fg = "#191921", "#45454F", "#6E6E7C"
                                badge = (badge + " ·弱") if badge else " ·弱"
                            elif mv >= 0.7:
                                bg, border = "#1C2630", "#4DB6AC"
                                badge = (badge + " ·熟") if badge else " ·熟"
                    shadow_c = (ft.BoxShadow(blur_radius=20, spread_radius=2, color="#99FFD54F")
                                if is_hl else ft.BoxShadow(blur_radius=10, color="#33000000"))

                    def _on_click(e):
                        if is_root:
                            _toggle_node(title)
                        elif kind == "notes":
                            mm_note_list(kp or title)
                        elif kind == "errors":
                            mm_error_detail(kp or title)
                        elif _node_has_children(title):
                            _toggle_node(title)
                        else:
                            mm_error_detail(title)

                    return ft.Container(
                        content=ft.Row([
                            ft.Text(f"{title}{badge}", size=13 if not is_root else 15,
                                    weight=ft.FontWeight.BOLD if is_root else ft.FontWeight.W_600,
                                    color=fg, max_lines=2, width=box_w - 24),
                        ], spacing=4),
                        width=box_w, height=box_h, padding=ft.Padding(left=12, top=6, right=12, bottom=6),
                        border_radius=12, bgcolor=bg, border=ft.border.all(1, border),
                        shadow=shadow_c,
                        ink=True,
                        on_click=_on_click,
                    )

                def mm_note_list(kp):
                    """笔记层：展示该知识点下的相关笔记（含 AI 理解的图片内容）"""
                    notes = load_jsonl(NOTES_FILE)
                    rel = [n for n in notes if n.get("subject") == subject and
                           (kp in str(n.get("content", "")) or kp in str(n.get("tags", [])) or
                            (n.get("ai_text") and kp in n.get("ai_text", "")))]
                    if not rel:
                        # 该科所有笔记兜底
                        rel = [n for n in notes if n.get("subject") == subject]
                    if not rel:
                        show_toast("该知识点暂无笔记", "grey")
                        return
                    children = [ft.Text(f"📓 {kp} · 相关笔记 {len(rel)} 条", size=17,
                                        weight=ft.FontWeight.BOLD)]
                    for i, n in enumerate(rel[:15]):
                        content = str(n.get("content", ""))
                        ai_text = str(n.get("ai_text", ""))
                        ntime = n.get("time", "")
                        imgs = n.get("media", []) or n.get("images", [])
                        card_lines = []
                        if content:
                            card_lines.append(ft.Text(f"[{i+1}] {content[:120]}", size=13))
                        if ai_text:
                            card_lines.append(ft.Text(f"🔍 AI 理解：{ai_text[:160]}", size=12,
                                                      color="#4DB6AC"))
                        if not content and not ai_text:
                            card_lines.append(ft.Text(f"[{i+1}]（图片笔记 {len(imgs)}张）", size=13))
                        card_lines.append(ft.Text(ntime, size=11, color="#888888"))
                        children.append(ft.Container(
                            content=ft.Column(card_lines, spacing=2),
                            padding=10, border_radius=10, bgcolor="#1F1F26",
                            border=ft.border.all(1, "#414868"),
                            on_click=lambda ev, nn=n: show_note_media_dialog(nn), ink=True))
                    dlg = ft.AlertDialog(
                        title=ft.Text("📓 笔记层"),
                        content=ft.Container(
                            content=ft.Column(children, spacing=8, scroll=ft.ScrollMode.AUTO),
                            width=480, height=500, padding=10),
                        actions=[ft.TextButton("关闭", on_click=lambda e: page.close(dlg))])
                    page.open(dlg)
                    page.update()

                def show_note_media_dialog(n):
                    """展示笔记条目（含图片缩略图）"""
                    imgs = n.get("media", []) or n.get("images", [])
                    body = []
                    if n.get("content"):
                        body.append(ft.Text(str(n["content"]), size=14, selectable=True))
                    if n.get("ai_text"):
                        body.append(ft.Text(f"🔍 AI 理解：{n['ai_text']}", size=13, color="#4DB6AC"))
                    img_row = ft.Row(spacing=8, wrap=True)
                    for p in imgs:
                        full = p if os.path.isabs(p) else os.path.join(DATA_DIR, p)
                        if os.path.exists(full):
                            img_row.controls.append(ft.Container(
                                content=ft.Image(src=full, width=120, height=120,
                                                 fit=ft.ImageFit.COVER, border_radius=8),
                                on_click=lambda e, paths=imgs: show_image_gallery(paths, 0),
                                ink=True, border_radius=8))
                    if img_row.controls:
                        body.append(img_row)
                    if not body:
                        body.append(ft.Text("（空笔记）", size=13, color="#888888"))
                    dlg = ft.AlertDialog(
                        title=ft.Text("📝 笔记详情"),
                        content=ft.Container(
                            content=ft.Column(body, spacing=8, scroll=ft.ScrollMode.AUTO),
                            width=480, height=460, padding=10),
                        actions=[ft.TextButton("关闭", on_click=lambda e: page.close(dlg))])
                    page.open(dlg)
                    page.update()

                def _node_has_children(t):
                    t2 = load_mindmap(subject)
                    for nd in (t2 or {}).get("children", []):
                        if nd.get("title") == t and nd.get("children"):
                            return True
                    return False

                def _toggle_node(t):
                    if t in view_state["open"]:
                        view_state["open"].discard(t)
                    else:
                        view_state["open"].add(t)
                    # 重建视图（保持当前缩放/平移），刷新折叠状态
                    viewport.content = ft.Transform(
                        scale=view_state["scale"],
                        translate=ft.Offset(view_state["dx"], view_state["dy"]),
                        content=rebuild_mindmap_view())
                    viewport.update()

                def rebuild_mindmap_view():
                    view_state["rebuild_count"] = view_state.get("rebuild_count", 0) + 1
                    layout_node(tree, 24, 40)
                    shapes = []
                    # 连线：父 → 每个直接子节点
                    for nd in tree.get("children", []):
                        p = view_state["layout"].get(tree["title"])
                        c = view_state["layout"].get(nd["title"])
                        if p and c:
                            shapes.append(ft.canvas.Line(
                                p[0] + NODE_W, p[1] + NODE_H / 2,
                                c[0] - 8, c[1] + NODE_H / 2,
                                paint=ft.canvas.Paint(stroke_width=2, color="#414868")))
                        for ch in nd.get("children", []):
                            cp = view_state["layout"].get(nd["title"])
                            cc = view_state["layout"].get(ch["title"])
                            if cp and cc:
                                shapes.append(ft.canvas.Line(
                                    cp[0] + NODE_W, cp[1] + NODE_H / 2,
                                    cc[0] - 8, cc[1] + NODE_H / 2,
                                    paint=ft.canvas.Paint(stroke_width=2, color="#33364D")))
                    canvas = ft.canvas.Canvas(width=LAYOUT_W, height=LAYOUT_H, shapes=shapes)
                    nodes = []
                    if not view_state.get("grown"):
                        view_state["grow_nodes"] = []

                    def _node_box(content, pos):
                        """世界树生长：首帧节点透明，动画点亮；已生长完则直接显示"""
                        if view_state.get("grown"):
                            return ft.Container(content=content, left=pos[0], top=pos[1])
                        c = ft.Container(content=content, left=pos[0], top=pos[1],
                                         opacity=0.0,
                                         animate_opacity=ft.animation.Animation(
                                             360, ft.AnimationCurve.EASE_OUT_CUBIC))
                        view_state["grow_nodes"].append(c)
                        return c

                    root_pos = view_state["layout"].get(tree["title"])
                    if root_pos:
                        nodes.append(ft.Stack([
                            ft.Container(width=1, height=1),
                            _node_box(make_node_widget(tree["title"], 0, 0, is_root=True),
                                      (root_pos[0], root_pos[1])),
                        ]))
                    for nd in tree.get("children", []):
                        pos = view_state["layout"].get(nd["title"])
                        if not pos:
                            continue
                        has_children = bool(nd.get("children"))
                        nodes.append(ft.Stack([
                            ft.Container(width=1, height=1),
                            _node_box(make_node_widget(nd["title"], pos[2], nd.get("count", 0),
                                                       is_root=False),
                                      (pos[0], pos[1])),
                        ]))
                        for ch in nd.get("children", []):
                            chp = view_state["layout"].get(ch["title"])
                            if not chp:
                                continue
                            nodes.append(ft.Stack([
                                ft.Container(width=1, height=1),
                                _node_box(make_node_widget(ch["title"], chp[2], ch.get("count", 0),
                                                           is_root=False, kind=ch.get("kind"),
                                                           kp=ch.get("kp", "")),
                                          (chp[0], chp[1])),
                            ]))
                    return ft.Stack([canvas] + nodes, width=LAYOUT_W, height=LAYOUT_H)

                content_holder = ft.Container(content=rebuild_mindmap_view())

                def on_scale_start(e):
                    view_state["base_scale"] = view_state["scale"]
                    view_state["base_dx"] = view_state["dx"]
                    view_state["base_dy"] = view_state["dy"]
                    if e.contact_count == 2:
                        view_state["_pinch_x"] = e.focal_point.x
                        view_state["_pinch_y"] = e.focal_point.y

                def on_scale_update(e):
                    if e.contact_count >= 2:
                        view_state["scale"] = min(2.6, max(0.4, view_state["base_scale"] * e.scale))
                        fx, fy = e.focal_point.x, e.focal_point.y
                        pfx, pfy = view_state.get("_pinch_x", fx), view_state.get("_pinch_y", fy)
                        view_state["dx"] += (fx - pfx)
                        view_state["dy"] += (fy - pfy)
                        view_state["_pinch_x"], view_state["_pinch_y"] = fx, fy
                    else:
                        view_state["scale"] = min(2.6, max(0.4, view_state["base_scale"] * e.scale))
                    _apply_transform()

                def on_pan_start(e):
                    view_state["base_dx"] = view_state["dx"]
                    view_state["base_dy"] = view_state["dy"]

                def on_pan_update(e):
                    view_state["dx"] = view_state["base_dx"] + e.delta.x * 2
                    view_state["dy"] = view_state["base_dy"] + e.delta.y * 2
                    _apply_transform()

                def _apply_transform():
                    # 双指缩放/拖动 → 更新真正显示的 viewport（历史版本曾更新未挂载的 content_holder 导致手势无效）
                    viewport.content = ft.Transform(
                        scale=view_state["scale"],
                        translate=ft.Offset(view_state["dx"], view_state["dy"]),
                        content=rebuild_mindmap_view())
                    viewport.update()

                def zoom_by(delta):
                    view_state["scale"] = min(2.6, max(0.4, view_state["scale"] + delta))
                    viewport.content = ft.Transform(
                        scale=view_state["scale"],
                        translate=ft.Offset(view_state["dx"], view_state["dy"]),
                        content=rebuild_mindmap_view())
                    viewport.update()

                def reset_view():
                    view_state.update({"scale": 1.0, "dx": 0.0, "dy": 0.0})
                    viewport.content = ft.Transform(scale=1.0, translate=ft.Offset(0, 0),
                                                    content=rebuild_mindmap_view())
                    viewport.update()

                top_bar = ft.Row([
                    ft.ElevatedButton("➕ 添加知识点", icon=ft.Icons.ADD,
                                      on_click=lambda e: add_kp_dialog(subject)),
                    ft.ElevatedButton("🔁 重建（按错题聚类）", icon=ft.Icons.REFRESH,
                                      on_click=lambda e: (build_mindmap(subject),
                                                          open_function_page(subject, "思维导图"))),
                    ft.ElevatedButton("🔍 AI 理解图片", icon=ft.Icons.VISIBILITY,
                                      on_click=lambda e: _run_understand()),
                    ft.IconButton(icon=ft.Icons.ZOOM_IN, on_click=lambda e: zoom_by(0.2)),
                    ft.IconButton(icon=ft.Icons.ZOOM_OUT, on_click=lambda e: zoom_by(-0.2)),
                    ft.IconButton(icon=ft.Icons.CENTER_FOCUS_STRONG, on_click=lambda e: reset_view()),
                    ft.Text(f"{subject} 思维导图 · 双指/按钮缩放 · 拖动平移 · 点知识分层看内容",
                            size=12, color=ft.Colors.GREY_500),
                ], spacing=10, alignment=ft.MainAxisAlignment.START)

                def _run_understand():
                    def _job():
                        n = auto_understand_media(subject, limit=12)
                        try:
                            build_mindmap(subject)
                            open_function_page(subject, "思维导图")
                            page.update()
                        except BaseException:
                            pass
                        if n:
                            show_toast(f"✅ AI 已理解 {n} 张图片，已加入知识树", "green")
                        else:
                            show_toast("没有待理解的图片（或已全部理解）", "grey")
                    import threading as _th
                    _th.Thread(target=_job, daemon=True).start()
                    show_toast("🔍 正在让 AI 理解图片（每张约几秒）...", "orange")
                viewport = ft.Container(
                    content=ft.Transform(
                        scale=1.0, translate=ft.Offset(0, 0),
                        content=rebuild_mindmap_view()),
                    expand=True,
                    bgcolor="#12121A",
                    clip_behavior=ft.ClipBehavior.HARD_EDGE,
                    border_radius=12,
                    border=ft.border.all(1, "#2A2E44"))
                viewport.content = ft.Transform(
                    scale=view_state["scale"], translate=ft.Offset(0, 0),
                    content=rebuild_mindmap_view())
                _mm_root_ref["v"] = viewport

                # —— 高亮定位：平移视图使知识点节点居中（从错题/笔记本跳转而来）——
                def _apply_highlight(kp_title):
                    layout = view_state["layout"]
                    target = None
                    if kp_title and kp_title in layout:
                        target = kp_title
                    elif kp_title:
                        for t, _p in layout.items():
                            if t != tree["title"] and (kp_title in t or t in kp_title):
                                target = t
                                break
                    if not target:
                        return False
                    pos = layout[target]
                    view_state["dx"] = -(pos[0]) + (LAYOUT_W - NODE_W) / 2.0
                    view_state["dy"] = -(pos[1]) + (LAYOUT_H - NODE_H) / 2.0
                    view_state["hl"] = target
                    try:
                        viewport.content = ft.Transform(
                            scale=view_state["scale"],
                            translate=ft.Offset(view_state["dx"], view_state["dy"]),
                            content=rebuild_mindmap_view())
                        viewport.update()
                        show_toast(f"🧭 已定位知识点：{target}", "orange")
                    except BaseException:
                        pass
                    return True

                # —— 世界树生长：从根向外逐节点点亮（像树枝蔓延）——
                def _start_grow():
                    if view_state.get("grown"):
                        return
                    import threading as _th
                    def _job():
                        time.sleep(0.15)
                        start_cnt = view_state.get("rebuild_count", 0)
                        gn = list(view_state.get("grow_nodes", []))
                        for i, c in enumerate(gn):
                            if view_state.get("rebuild_count", 0) != start_cnt:
                                # 生长期间视图被重建（用户点击折叠/缩放）→ 直接点亮新批次，跳过动画
                                for cc in list(view_state.get("grow_nodes", [])):
                                    try:
                                        cc.opacity = 1.0
                                    except BaseException:
                                        pass
                                break
                            try:
                                c.opacity = 1.0
                                if i % 3 == 0:
                                    page.update()
                                time.sleep(0.045)
                            except BaseException:
                                pass
                        view_state["grown"] = True
                        page.update()
                        _hl = view_state.get("hl")
                        if _hl:
                            try:
                                _apply_highlight(_hl)
                            except BaseException:
                                pass
                    _th.Thread(target=_job, daemon=True).start()

                if not view_state.get("grown"):
                    _start_grow()
                vd = ft.GestureDetector(
                    content=viewport, expand=True,
                    on_scale_start=on_scale_start, on_scale_update=on_scale_update,
                    on_pan_start=on_pan_start, on_pan_update=on_pan_update)
                return ft.Column([
                    top_bar,
                    ft.Divider(height=1),
                    ft.Container(content=vd, expand=True),
                ], spacing=8, expand=True)

            def build_sentence_page(subject):
                CATEGORIES = ["全部", "开头", "转折", "结尾", "观点", "举例", "读后续写", "其他"]
                category_colors = {"开头": "#1A2840", "转折": "#3A2A18", "结尾": "#1A2E1A",
                                   "观点": "#3A1A28", "举例": "#2E1A3A", "读后续写": "#1A2E3A",
                                   "其他": "#24283B"}
                search_input = ft.TextField(label="🔍 搜索句子", hint_text="输入关键词...", expand=True)
                category_dropdown = ft.Dropdown(
                    label="分类", options=[ft.dropdown.Option(c) for c in CATEGORIES],
                    value="全部", width=120)
                fav_switch = ft.Switch(label="仅收藏", value=False)
                sentence_list = ft.ListView(spacing=8, expand=True)
                status_text = ft.Text("", size=14)

                def show_add_dialog(edit_data=None):
                    is_edit = edit_data is not None
                    cat_drop = ft.Dropdown(
                        label="分类",
                        options=[ft.dropdown.Option(c) for c in CATEGORIES if c != "全部"],
                        value=edit_data.get("category", "观点") if is_edit else "观点",
                        width=150)
                    sent_input = ft.TextField(
                        label="英文句子",
                        value=edit_data.get("sentence", "") if is_edit else "",
                        multiline=True, min_lines=3, max_lines=5, expand=True)
                    trans_input = ft.TextField(
                        label="中文翻译（可选）",
                        value=edit_data.get("translation", "") if is_edit else "",
                        multiline=True, min_lines=2, max_lines=3, expand=True)

                    def do_save(e):
                        cat = cat_drop.value
                        sent = sent_input.value.strip()
                        trans = trans_input.value.strip()
                        if not sent:
                            show_toast("请输入句子内容", "red")
                            return
                        if is_edit:
                            update_sentence(edit_data["id"], cat, sent, trans)
                        else:
                            add_sentence(cat, sent, trans)
                        page.close(dialog)
                        refresh_list()
                        show_toast("✅ 已保存" if not is_edit else "✅ 已更新", "green")

                    dialog = ft.AlertDialog(
                        title=ft.Text("编辑金句" if is_edit else "添加金句"),
                        content=ft.Column([cat_drop, sent_input, trans_input], spacing=10, width=400),
                        actions=[ft.TextButton("取消", on_click=lambda e: page.close(dialog)),
                                 ft.ElevatedButton("保存", on_click=do_save)])
                    page.open(dialog)

                def show_ai_dialog():
                    topic_input = ft.TextField(label="输入主题",
                                               hint_text="例如：环境保护、科技发展...",
                                               multiline=True, min_lines=2, max_lines=3, expand=True)
                    count_row = ft.Row(spacing=10)
                    count_drop = ft.Dropdown(
                        label="快速选择",
                        options=[ft.dropdown.Option(str(i)) for i in [3, 5, 8, 10]],
                        value="5", width=120)
                    count_input = ft.TextField(label="自定义", width=100,
                                               text_align=ft.TextAlign.CENTER)
                    count_row.controls.extend([count_drop, ft.Text("或", size=14), count_input])

                    def do_generate(e):
                        topic = topic_input.value.strip()
                        if not topic:
                            show_toast("请输入主题", "red")
                            return
                        custom_val = count_input.value.strip()
                        count = int(custom_val) if custom_val and custom_val.isdigit() else int(count_drop.value)
                        count = max(1, min(count, 20))
                        page.close(dialog)
                        status_text.value = f"⏳ AI正在生成 {count} 个金句..."
                        status_text.color = "#7AA2F7"
                        page.update()

                        def gen_thread():
                            api_key, api_url, api_model, _v = endpoint_for("cheap")
                            if not api_key:
                                status_text.value = "❌ 未配置API密钥"
                                status_text.color = "#EF5350"
                                page.update()
                                return
                            prompt = f"""请为主题 "{topic}" 生成 {count} 个高考英语作文万能金句。
输出 JSON 数组：[{{"sentence": "英文", "translation": "中文", "category": "开头/转折/结尾/观点/举例/读后续写"}}]
只返回 JSON。"""
                            try:
                                resp = requests.post(api_url,
                                                     headers={"Authorization": f"Bearer {api_key}",
                                                              "Content-Type": "application/json"},
                                                     json={"model": api_model,
                                                           "messages": [{"role": "user", "content": prompt}],
                                                           "temperature": 0.7, "max_tokens": 1500}, timeout=45)
                                if resp.status_code == 200:
                                    content = resp.json()["choices"][0]["message"]["content"]
                                    try:
                                        items = json.loads(content)
                                    except BaseException:
                                        match = re.search(r'\[.*\]', content, re.DOTALL)
                                        items = json.loads(match.group()) if match else None
                                    if items:
                                        added = 0
                                        for item in items:
                                            cat = item.get("category", "其他")
                                            if cat not in CATEGORIES:
                                                cat = "其他"
                                            add_sentence(cat, item.get("sentence", ""),
                                                         item.get("translation", ""))
                                            added += 1
                                        refresh_list()
                                        status_text.value = f"✅ 成功添加 {added} 个金句"
                                        status_text.color = "#81C784"
                                    else:
                                        status_text.value = "❌ AI返回格式异常"
                                        status_text.color = "#EF5350"
                                else:
                                    status_text.value = f"❌ API错误: {resp.status_code}"
                                    status_text.color = "#EF5350"
                            except Exception as ex:
                                status_text.value = f"❌ 失败: {str(ex)[:50]}"
                                status_text.color = "#EF5350"
                            page.update()

                        threading.Thread(target=gen_thread, daemon=True).start()

                    dialog = ft.AlertDialog(
                        title=ft.Text("🤖 AI生成金句"),
                        content=ft.Column([topic_input, count_row], spacing=10, width=400),
                        actions=[ft.TextButton("取消", on_click=lambda e: page.close(dialog)),
                                 ft.ElevatedButton("生成并添加", on_click=do_generate)])
                    page.open(dialog)

                def render_list(filter_category="全部", keyword="", only_fav=False):
                    sentence_list.controls.clear()
                    sentences = load_sentences()
                    sentences.sort(key=lambda x: (not x.get("favorite", False),
                                                  x.get("updated", x.get("created", ""))), reverse=True)
                    filtered = []
                    for s in sentences:
                        if only_fav and not s.get("favorite", False):
                            continue
                        if filter_category != "全部" and s.get("category") != filter_category:
                            continue
                        if keyword:
                            kw = keyword.lower()
                            if kw not in s.get("sentence", "").lower() and \
                               kw not in s.get("translation", "").lower():
                                continue
                        filtered.append(s)
                    if not filtered:
                        sentence_list.controls.append(ft.Container(
                            content=ft.Text("  暂无金句", size=14, color=ft.Colors.GREY_500),
                            padding=20))
                        page.update()
                        return
                    for s in filtered:
                        sid = s.get("id")
                        cat = s.get("category", "其他")
                        sentence = s.get("sentence", "")
                        translation = s.get("translation", "")
                        favorite = s.get("favorite", False)
                        updated = s.get("updated", s.get("created", ""))
                        bg_color = category_colors.get(cat, "#24283B")
                        card = ft.Container(
                            content=ft.Column([
                                ft.Row([
                                    ft.Container(
                                        content=ft.Text(cat, size=11, color=ft.Colors.WHITE,
                                                        weight=ft.FontWeight.BOLD),
                                        bgcolor="#2196F3", border_radius=10,
                                        padding=ft.Padding(left=8, right=8, top=2, bottom=2)),
                                    ft.Row([
                                        ft.IconButton(
                                            icon=ft.Icons.STAR if favorite else ft.Icons.STAR_BORDER,
                                            icon_color="#E0AF68" if favorite else ft.Colors.GREY_500,
                                            icon_size=20,
                                            on_click=lambda e, sid=sid: (toggle_favorite(sid), refresh_list())),
                                        ft.IconButton(
                                            icon=ft.Icons.COPY, icon_size=18,
                                            on_click=lambda e, text=sentence: page.set_clipboard(text)),
                                        ft.IconButton(
                                            icon=ft.Icons.EDIT, icon_size=18,
                                            on_click=lambda e, data=s: show_add_dialog(data)),
                                        ft.IconButton(
                                            icon=ft.Icons.DELETE, icon_size=18,
                                            on_click=lambda e, sid=sid: (delete_sentence(sid), refresh_list())),
                                    ], spacing=2),
                                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                ft.Text(sentence, size=15, selectable=True),
                                ft.Text(translation, size=13, color=ft.Colors.GREY_400,
                                        italic=True, selectable=True) if translation else ft.Text(""),
                                ft.Text(f"📅 {updated}", size=10, color=ft.Colors.GREY_500),
                            ], spacing=4),
                            padding=10, border_radius=12, bgcolor=bg_color,
                            margin=ft.margin.only(bottom=4),
                            border=ft.border.all(1, "#E0AF68" if favorite else "#2A2E44"))
                        sentence_list.controls.append(card)
                    page.update()

                def refresh_list():
                    render_list(category_dropdown.value, search_input.value.strip(), fav_switch.value)

                search_input.on_change = lambda e: refresh_list()
                category_dropdown.on_change = lambda e: refresh_list()
                fav_switch.on_change = lambda e: refresh_list()
                render_list()
                return ft.Column([
                    ft.Row([
                        ft.Text("💬 金句列表", size=20, weight=ft.FontWeight.BOLD),
                        ft.Row([
                            ft.ElevatedButton("➕ 添加", on_click=lambda e: show_add_dialog(),
                                              icon=ft.Icons.ADD),
                            ft.ElevatedButton("🤖 AI生成", on_click=lambda e: show_ai_dialog(),
                                              icon=ft.Icons.AUTO_AWESOME),
                        ], spacing=8),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Text("英语作文万能句子", size=14, color=ft.Colors.GREY_500),
                    ft.Row([search_input, category_dropdown, fav_switch], spacing=10),
                    status_text,
                    ft.Divider(height=1),
                    ft.Container(content=sentence_list, expand=True),
                ], spacing=8, expand=True)

            selected_subject_for_page = "数学"

            def build_function_card_grid(subject):
                all_cards = [
                    ("📋", "错题本", "#24283B"),
                    ("📝", "笔记本", "#223A22"),
                    ("🧠", "思维导图", "#1F2A44"),
                    ("📖", "单词本", "#3A2F22"),
                    ("💬", "金句", "#3A2233"),
                ]
                cards_config = all_cards if subject == "英语" else all_cards[:3]
                grid = ft.ResponsiveRow(spacing=20, run_spacing=20, expand=True)
                for i, (icon, name, bg) in enumerate(cards_config):
                    def _card_hover(e, _card=None):
                        try:
                            _card.scale = 1.02 if e.data == "true" else 1.0
                            _card.shadow = (ft.BoxShadow(blur_radius=24, color="#66000000",
                                                         offset=ft.Offset(0, 10)) if e.data == "true"
                                            else ft.BoxShadow(blur_radius=16, color="#44000000",
                                                              offset=ft.Offset(0, 5)))
                            page.update()
                        except BaseException:
                            pass

                    card = ft.Container(
                        content=ft.Column([
                            ft.Text(icon, size=36),
                            ft.Text(name, size=16, weight=ft.FontWeight.BOLD),
                            ft.Text(("词典/考核/生词" if name == "单词本" else
                                     "直达知识点世界树" if name == "思维导图" else
                                     "按学科整理" if name == "错题本" else
                                     "随手记录灵感" if name == "笔记本" else
                                     "摘抄与回看"), size=12, color="#8E8E93"),
                        ], alignment=ft.MainAxisAlignment.CENTER,
                           horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
                        bgcolor="#CC" + bg[1:] if bg.startswith("#") else bg,
                        blur=ft.Blur(14, 14, ft.BlurTileMode.CLAMP),
                        border_radius=22, padding=22,
                        border=ft.border.all(1, "#33FFFFFF"),
                        shadow=ft.BoxShadow(blur_radius=16, color="#44000000",
                                            offset=ft.Offset(0, 5)),
                        ink=True,
                        scale=1.0,
                        animate_scale=ft.Animation(150, ft.AnimationCurve.EASE_OUT),
                        animate_shadow=ft.Animation(150, ft.AnimationCurve.EASE_OUT),
                        on_hover=lambda e, c=card: _card_hover(e, c),
                        on_click=lambda e, subj=subject, fn=name: open_function_page(subj, fn),
                        expand=True)
                    grid.controls.append(
                        ft.Container(content=card,
                                     col={"xs": 12, "sm": 6, "md": 6, "lg": 4, "xl": 3}))
                return grid

            def open_function_page(subject, function_name):
                def go_back(e):
                    nonlocal selected_subject_for_page
                    selected_subject_for_page = subject
                    subject_page_content.content = build_subject_page()
                    page.update()
                _mm_hl = None
                try:
                    if _MM_HIGHLIGHT and _MM_HIGHLIGHT.get("kp"):
                        _mm_hl = _MM_HIGHLIGHT.pop("kp")
                except BaseException:
                    _mm_hl = None
                func_pages = {
                    "错题本": build_error_list_page(subject),
                    "笔记本": build_note_list_page(subject),
                    "思维导图": build_mindmap_page(subject, highlight_kp=_mm_hl),
                    "单词本": build_vocab_page(subject),
                    "金句": build_sentence_page(subject),
                }
                func_content = func_pages.get(function_name)
                full_page = ft.Column([
                    ft.Row([
                        ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=go_back),
                        ft.Text(f"{subject} - {function_name}", size=20,
                                weight=ft.FontWeight.BOLD),
                    ]),
                    ft.Divider(),
                    ft.Container(content=func_content, expand=True) if func_content
                    else ft.Container(content=ft.Text("暂无内容"), expand=True),
                ], spacing=10, expand=True,
                   animate_opacity=ft.Animation(220, ft.AnimationCurve.EASE_OUT),
                   animate_offset=ft.Animation(240, ft.AnimationCurve.EASE_OUT_BACK))
                # 苹果风进入动画：上浮淡入
                full_page.opacity = 0
                full_page.offset = ft.Offset(0, 0.015)
                subject_page_content.content = full_page
                page.update()
                full_page.opacity = 1
                full_page.offset = ft.Offset(0, 0)
                page.update()

            def build_subject_left_panel(subj):
                subjects = ["语文", "数学", "英语", "物理", "化学", "生物", "历史", "政治", "地理"]
                subj_buttons = []
                for s in subjects:
                    is_selected = s == subj
                    btn = ft.Container(
                        content=ft.Text(s, size=16, weight=ft.FontWeight.BOLD,
                                        color="white" if is_selected else "#CCCCCC"),
                        padding=ft.Padding(left=16, top=12, right=16, bottom=12),
                        border_radius=12,
                        bgcolor="#7AA2F7" if is_selected else "#24283B",
                        on_click=lambda e, ss=s: on_subject_selected(ss))
                    subj_buttons.append(btn)
                return ft.Container(content=ft.Column(subj_buttons, spacing=6), width=100, padding=10)

            def build_subject_page():
                nonlocal selected_subject_for_page
                left_panel = build_subject_left_panel(selected_subject_for_page)
                right_panel = build_function_card_grid(selected_subject_for_page)
                return ft.Row([
                    left_panel,
                    ft.VerticalDivider(width=1, color="#2A2E44"),
                    ft.Container(content=right_panel, expand=True,
                                 padding=ft.Padding(left=20, right=20, top=20, bottom=20)),
                ], expand=True)

            def on_subject_selected(subj):
                nonlocal selected_subject_for_page
                selected_subject_for_page = subj
                subject_page_content.content = build_subject_page()
                page.update()

            main_subject_page = build_subject_page()
            subject_page_content.content = main_subject_page
            subject_page = ft.Column([
                ft.Container(height=10),
                ft.Text("📚 学科浏览", size=24, weight=ft.FontWeight.BOLD),
                ft.Container(content=subject_page_content, expand=True),
            ], spacing=15, scroll=ft.ScrollMode.AUTO)

            @retry_request(max_retries=3, base_delay=2)
            def generate_today_plan(result_text=None):
                target = result_text
                if target is None:
                    return
                target.value = "⏳ AI 正在分析你的学习数据..."
                target.color = "#A9B1D6"
                page.update()

                def do_generate():
                    profile = load_user_profile()
                    errors = load_jsonl(ERRORS_FILE)
                    try:
                        days_left = (datetime(2026, 6, 7) - datetime.now()).days
                    except BaseException:
                        days_left = 365
                    subject_errors = {}
                    for err in errors:
                        s = err.get("subject", "未知")
                        subject_errors[s] = subject_errors.get(s, 0) + 1
                    weak_know = sorted(profile.get("weak_knowledge", {}).items(),
                                       key=lambda x: x[1], reverse=True)[:5]
                    errors_sorted = sorted(errors, key=lambda x: x.get("timestamp", 0), reverse=True)
                    recent = errors_sorted[:15]
                    detail_lines = []
                    for i, e in enumerate(recent):
                        tags = "、".join(e.get("tags", []))
                        orig = (e.get("original", "") or e.get("question", ""))[:150]
                        mistake = e.get("mistake", "")[:100]
                        answer = e.get("answer", "")[:100]
                        detail_lines.append(
                            f"[{i+1}][{e.get('subject', '')}][{tags}]\n"
                            f"  题目：{orig}\n"
                            f"  错因：{mistake}\n"
                            f"  答案：{answer}"
                        )
                    error_block = "\n".join(detail_lines) if detail_lines else "（暂无错题）"

                    prompt = f"""你是高三学习规划师，距离高考还有 {days_left} 天。请分析下面这些**真实错题**，给出具体、可执行的学习建议。

【硬性要求】
- 禁止出现"多练习""加强理解""夯实基础""查漏补缺"这类空话
- 每条建议必须点名具体题目或具体知识点
- 指出每道题真正的错误原因（不是照抄"错因"字段，而是从题目推断）
- 给出 3-5 个今天就能做的任务，每个任务必须包含：科目、具体内容、预计耗时
- 最后 2-3 句真诚的鼓励，不要套话

【最近错题（按时间倒序）】
{error_block}

【各科错题数】
{json.dumps(subject_errors, ensure_ascii=False)}

【系统统计的薄弱知识点】
{json.dumps(weak_know, ensure_ascii=False)}
"""
                    api_key, api_url, api_model, _v = endpoint_for("smart")
                    if not api_key:
                        target.value = "❌ 未配置 API 密钥"
                        target.color = "#EF5350"
                        page.update()
                        return
                    try:
                        resp = requests.post(api_url,
                                             headers={"Authorization": f"Bearer {api_key}",
                                                      "Content-Type": "application/json"},
                                             json={"model": api_model,
                                                   "messages": [{"role": "user", "content": prompt}],
                                                   "temperature": 0.5, "max_tokens": 1500}, timeout=60)
                        if resp.status_code == 200:
                            target.value = resp.json()["choices"][0]["message"]["content"]
                            target.color = "#FFFFFF"
                        else:
                            target.value = f"❌ API错误：{resp.status_code}"
                            target.color = "#EF5350"
                    except Exception as ex:
                        target.value = f"❌ 请求失败：{str(ex)}"
                        target.color = "#EF5350"
                    page.update()

                threading.Thread(target=do_generate, daemon=True).start()

            today_plan_text = ft.Text("点击「生成今日计划」获取 AI 学习建议", size=15,
                                      color="#888888", selectable=True)
            today_plan_card = ft.Container(
                content=ft.Column([
                    ft.Row([ft.Text("📅 今日学习计划", size=18),
                            ft.ElevatedButton("生成今日计划",
                                              on_click=lambda e: generate_today_plan(today_plan_text),
                                              height=30)]),
                    ft.Divider(height=5), today_plan_text
                ], spacing=8),
                # AstroBox 风格：半透明毛玻璃卡片 + 大圆角 + 主色细边框
                padding=15, border_radius=24, bgcolor="#CC16161E", blur=12,
                border=ft.border.all(1, "#401781FF"),
                shadow=ft.BoxShadow(blur_radius=20, color="#44000000"))

            task_list = ft.Column(spacing=6)
            new_task_input = ft.TextField(label="新学习任务", expand=True)

            def add_task(e):
                text = new_task_input.value.strip()
                if text:
                    tasks = load_jsonl(TASKS_FILE)
                    tasks.append({"text": text, "done": False,
                                  "created": time.strftime("%Y-%m-%d %H:%M:%S"),
                                  "timestamp": now_ms(), "event_id": gen_uid()})
                    save_jsonl(TASKS_FILE, tasks)
                    new_task_input.value = ""
                    refresh_tasks()

            def refresh_tasks():
                task_list.controls.clear()
                tasks = load_jsonl(TASKS_FILE)
                if not tasks:
                    task_list.controls.append(ft.Text("  暂无任务", size=16))
                else:
                    for task in tasks:
                        def toggle_task(e, t=task):
                            t["done"] = not t.get("done", False)
                            all_tasks = load_jsonl(TASKS_FILE)
                            for d in all_tasks:
                                if d.get("created") == t.get("created"):
                                    d["done"] = t["done"]
                                    break
                            save_jsonl(TASKS_FILE, all_tasks)
                            refresh_tasks()

                        task_list.controls.append(ft.Row([
                            ft.Checkbox(value=task.get("done", False), on_change=toggle_task),
                            ft.Text(task["text"], size=16, expand=True),
                            ft.TextButton("删除", on_click=lambda e, t=task: (
                                save_jsonl(TASKS_FILE, [d for d in load_jsonl(TASKS_FILE)
                                                        if d.get("created") != t.get("created")]),
                                refresh_tasks()))
                        ], spacing=10))
                page.update()

            refresh_tasks()

            recycle_list = ft.Column(spacing=6)

            def refresh_recycle():
                recycle_list.controls.clear()
                for item in reversed(load_jsonl(RECYCLE_FILE)):
                    data = item.get("data", {})
                    preview = data.get("original", data.get("content", ""))[:40]
                    ts = item.get("delete_ts", 0)
                    recycle_list.controls.append(ft.Row([
                        ft.Text(f"[{data.get('subject', '未知')}] {preview}",
                                size=16, expand=True),
                        ft.TextButton("恢复", on_click=lambda e, t=ts: (
                            restore_from_recycle(t), refresh_recycle(),
                            show_toast("已恢复", "green")))
                    ], spacing=10))
                page.update()

            refresh_recycle()

            ai_config = load_ai_config()

            provider_dropdown = ft.Dropdown(
                label="AI 提供商",
                options=[
                    ft.dropdown.Option("zhipu", "智谱 GLM（免费）"),
                    ft.dropdown.Option("deepseek", "DeepSeek"),
                ],
                value=ai_config.get("provider", "zhipu"),
                width=280,
            )

            free_key_input = ft.TextField(label="智谱 GLM API 密钥",
                                          value=ai_config.get("api_key_free", ""),
                                          password=True)
            deepseek_key_input = ft.TextField(label="DeepSeek API 密钥",
                                              value=ai_config.get("api_key_deepseek", ""),
                                              password=True)
            deepseek_model_input = ft.TextField(
                label="DeepSeek 模型（deepseek-flash / deepseek-v4-pro）",
                value=ai_config.get("deepseek_model", "deepseek-flash"),
                hint_text="deepseek-flash = V4.1-Flash-1017（默认，含图片理解）；更强选 deepseek-v4-pro",
                width=280)
            deepseek_thinking_switch = ft.Switch(
                label="DeepSeek 思考模式",
                value=ai_config.get("deepseek_thinking", True),
                tooltip="开启后模型先深度思考再回答（更强但稍慢）")

            def save_keys(e):
                cfg = load_ai_config()
                cfg["provider"] = provider_dropdown.value
                cfg["api_key_free"] = free_key_input.value.strip()
                cfg["api_key_deepseek"] = deepseek_key_input.value.strip()
                cfg["deepseek_model"] = (deepseek_model_input.value or "deepseek-flash").strip()
                cfg["deepseek_thinking"] = deepseek_thinking_switch.value
                try:
                    cfg["ctx_chars"] = memory_dropdown.value or "auto"
                except BaseException:
                    cfg["ctx_chars"] = "auto"
                save_ai_config(cfg)
                show_toast("API 配置已保存", "green")

            test_conn_result = ft.Text("", size=14)

            def test_ai_connection(e):
                test_conn_result.value = "⏳ 测试中..."
                test_conn_result.color = "#A9B1D6"
                page.update()

                def _test():
                    api_key, api_url, api_model, _v = get_api_endpoint()
                    if not api_key:
                        test_conn_result.value = "❌ 未配置API密钥"
                        test_conn_result.color = "#EF5350"
                        page.update()
                        return
                    try:
                        headers = {"Authorization": f"Bearer {api_key}",
                                   "Content-Type": "application/json"}
                        payload = {"model": api_model,
                                   "messages": [{"role": "user", "content": "仅回复OK"}],
                                   "max_tokens": 5, "temperature": 0}
                        resp = requests.post(api_url,
                                             headers=headers, json=payload, timeout=10)
                        if resp.status_code == 200:
                            content = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
                            if content.strip():
                                test_conn_result.value = f"✅ 连接成功！返回：{content.strip()}"
                                test_conn_result.color = "#81C784"
                            else:
                                test_conn_result.value = "⚠️ 连接成功但返回为空"
                                test_conn_result.color = "#E0AF68"
                        else:
                            test_conn_result.value = f"❌ 连接失败 (HTTP {resp.status_code})"
                            test_conn_result.color = "#EF5350"
                    except requests.exceptions.Timeout:
                        test_conn_result.value = "❌ 连接超时"
                        test_conn_result.color = "#EF5350"
                    except Exception as ex:
                        test_conn_result.value = f"❌ 异常: {str(ex)[:50]}"
                        test_conn_result.color = "#EF5350"
                    page.update()

                threading.Thread(target=_test, daemon=True).start()

            skill_input = ft.TextField(label="自定义 AI Skill", multiline=True,
                                       min_lines=4, max_lines=10, value=load_custom_skill())

            def save_skill(e):
                save_custom_skill(skill_input.value)
                show_toast("Skill 已保存", "green")
            retag_status = ft.Text("", size=13, color="#888888")
            retag_state = {"running": False}

            def batch_retag(e):
                if retag_state["running"]:
                    show_toast("⏳ 正在跑，别点两次", "info")
                    return
                all_errors = load_jsonl(ERRORS_FILE)
                todo = [err for err in all_errors if not err.get("tags_done")]
                if not todo:
                    show_toast("✅ 所有错题标签都已打好", "green")
                    retag_status.value = "✅ 无需重打"
                    retag_status.color = "#81C784"
                    page.update()
                    return
                total = len(todo)
                retag_state["running"] = True
                retag_status.value = f"⏳ 排队中：共 {total} 条待重打"
                retag_status.color = "#7AA2F7"
                page.update()

                def do_retag():
                    done = 0
                    fail = 0
                    try:
                        for err in todo:
                            ts = err.get("timestamp")
                            if not ts:
                                continue
                            try:
                                auto_tag_error(ts)
                                check = load_jsonl(ERRORS_FILE)
                                ok = any(x.get("timestamp") == ts and x.get("tags_done") for x in check)
                                if ok:
                                    done += 1
                                else:
                                    fail += 1
                            except BaseException:
                                fail += 1
                            retag_status.value = f"⏳ 重打标签 {done+fail}/{total}（成功 {done}，失败 {fail}）"
                            page.update()
                            time.sleep(0.8)
                    finally:
                        retag_state["running"] = False
                    retag_status.value = f"✅ 完成：成功 {done} 条，失败 {fail} 条"
                    retag_status.color = "#81C784"
                    page.update()
                    show_toast(f"批量重打完成：成功 {done}，失败 {fail}", "green")

                threading.Thread(target=do_retag, daemon=True).start()

            def show_learning_profile(e):
                profile = load_user_profile()
                events = load_jsonl(LEARNING_EVENTS_FILE)
                error_types = profile.get("error_types", {})
                km = profile.get("knowledge_memory", {})
                content_children = []
                content_children.append(
                    ft.Text(f"🎯 学习画像（总事件：{len(events)}）", size=18,
                            weight=ft.FontWeight.BOLD))
                content_children.append(ft.Divider(height=1, color=ft.Colors.GREY_700))
                if error_types:
                    content_children.append(ft.Text("📊 错因分布", size=15,
                                                    weight=ft.FontWeight.BOLD))
                    max_count = max(error_types.values())
                    color_map = {"计算错误": "#EF5350", "概念不清": "#FFA726",
                                 "审题偏差": "#AB47BC", "公式遗忘": "#42A5F5",
                                 "方法错误": "#26A69A", "其他": "#78909C"}
                    for et, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True):
                        pct = count / max_count
                        bar = ft.ProgressBar(value=pct, width=200, height=8,
                                             color=color_map.get(et, "#78909C"),
                                             bgcolor="#2A2E44", border_radius=4)
                        content_children.append(ft.Row([
                            ft.Text(f"{et}：{count}", size=13, width=110), bar,
                        ], spacing=8))
                else:
                    content_children.append(ft.Text("暂无错因数据", size=13, color="#888888"))
                content_children.append(ft.Divider(height=1, color=ft.Colors.GREY_700))
                if km:
                    content_children.append(ft.Text("📚 知识点掌握度（低 → 高）", size=15,
                                                    weight=ft.FontWeight.BOLD))
                    sorted_km = sorted(km.items(), key=lambda x: x[1].get("level", 0.3))[:8]
                    for kp, info in sorted_km:
                        level = info.get("level", 0.3)
                        events_count = info.get("events", 0)
                        summary = info.get("summary", "")[:40]
                        bar_color = "#EF5350" if level < 0.4 else ("#FFA726" if level < 0.7 else "#81C784")
                        content_children.append(
                            ft.Text(f"{kp}（{events_count}次，掌握 {level:.0%}）", size=13))
                        content_children.append(
                            ft.ProgressBar(value=level, width=300, height=6,
                                           color=bar_color, bgcolor="#2A2E44"))
                        if summary:
                            content_children.append(
                                ft.Text(f"  → {summary}", size=11, color="#888888"))
                else:
                    content_children.append(ft.Text("暂无知识点数据", size=13, color="#888888"))
                content_children.append(ft.Divider(height=1, color=ft.Colors.GREY_700))
                # —— AI 对话画像：各学科问过多少题、最近问什么、常涉及知识点 ——
                sp = profile.get("subject_profile", {})
                if sp:
                    content_children.append(ft.Text("💬 AI 对话画像（按学科）", size=15,
                                                    weight=ft.FontWeight.BOLD))
                    for subj, rec in sorted(sp.items(), key=lambda x: x[1].get("asked", 0), reverse=True):
                        asked = rec.get("asked", 0)
                        rqs = rec.get("recent_questions", [])
                        tops = rec.get("topics", [])
                        head = f"{subj}：问过 {asked} 题"
                        if tops:
                            head += f"，常涉及：{'、'.join(tops[:8])}"
                        content_children.append(ft.Text(head, size=13,
                                                        weight=ft.FontWeight.W_600))
                        if rqs:
                            for rq in rqs[:3]:
                                content_children.append(ft.Text(f"  · {rq}", size=12,
                                                                color="#B8C0E0"))
                else:
                    content_children.append(ft.Text("💬 暂无对话画像（多和 AI 聊题目会自动建立）",
                                                    size=13, color="#888888"))
                content_children.append(ft.Divider(height=1, color=ft.Colors.GREY_700))
                wk2 = profile.get("weak_knowledge", {})
                if wk2:
                    content_children.append(ft.Text("⚠️ 薄弱知识点 TOP5", size=15,
                                                    weight=ft.FontWeight.BOLD))
                    for k, v in sorted(wk2.items(), key=lambda x: -x[1])[:5]:
                        content_children.append(ft.Text(f"· {k}（薄弱度 {v:.0%}）", size=13,
                                                        color="#FFA726"))
                    content_children.append(ft.Divider(height=1, color=ft.Colors.GREY_700))
                rf2 = profile.get("recent_focus", [])
                if rf2:
                    content_children.append(ft.Text("🎓 最近在攻克", size=15,
                                                    weight=ft.FontWeight.BOLD))
                    content_children.append(ft.Text(" · ".join(rf2[:6]), size=13, color="#CCCCCC"))
                    content_children.append(ft.Divider(height=1, color=ft.Colors.GREY_700))
                content_children.append(ft.Text(
                    f"📈 累计：错题 {profile.get('total_errors', 0)} 道 · AI 对话 {profile.get('total_chats', 0)} 次",
                    size=13, color="#9AA5CE"))
                if events:
                    content_children.append(ft.Text("🕒 最近学习事件", size=15,
                                                    weight=ft.FontWeight.BOLD))
                    for ev in reversed(events[-10:]):
                        t = ev.get("time", "")[5:16]
                        tp = ev.get("type", "")
                        subj = ev.get("subject", "")
                        detail = ev.get("detail", "")[:50]
                        content_children.append(
                            ft.Text(f"[{t}] {subj} · {tp}\n  {detail}", size=12,
                                    color="#CCCCCC"))
                dlg = ft.AlertDialog(
                    title=ft.Text("🎯 学习画像"),
                    content=ft.Container(
                        content=ft.Column(content_children, spacing=8, scroll=ft.ScrollMode.AUTO),
                        width=420, height=500, padding=10),
                    actions=[ft.TextButton("关闭", on_click=lambda e: page.close(dlg))])
                page.open(dlg)
                page.update()

            def show_knowledge_framework(e):
                data = analyze_knowledge_framework()
                error_counts = data.get("error_counts", {})
                total = data.get("total_errors", 0)
                sorted_subjects = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)
                content_children = [
                    ft.Text(f"📊 知识框架（总错题：{total} 道）", size=18,
                            weight=ft.FontWeight.BOLD),
                    ft.Divider(height=1, color=ft.Colors.GREY_700),
                ]
                max_count = max([c for _, c in error_counts.items()]) if error_counts else 1
                color_map = {"语文": "#A9B1D6", "数学": "#EF5350", "英语": "#81C784",
                             "物理": "#BA68C8", "化学": "#FFA726", "生物": "#4DB6AC",
                             "历史": "#FFD54F", "政治": "#F06292", "地理": "#4DD0E1"}
                for subject, count in sorted_subjects:
                    percentage = min((count / max_count) * 100, 100) if max_count > 0 else 0
                    color = color_map.get(subject, "#78909C")
                    progress_bar = ft.ProgressBar(value=percentage / 100, width=200,
                                                  height=8, color=color, bgcolor="#2A2E44",
                                                  border_radius=4)
                    content_children.append(ft.Row([
                        ft.Text(f"{subject}：{count} 题", size=14, width=80),
                        progress_bar,
                        ft.Text(f"{int(percentage)}%", size=12, color="#888888", width=40),
                    ], spacing=10, alignment=ft.MainAxisAlignment.START))
                if not error_counts:
                    content_children.append(ft.Text("暂无错题数据，继续加油！", size=14,
                                                    color="#888888"))
                dlg = ft.AlertDialog(
                    title=ft.Text("📊 知识框架"),
                    content=ft.Container(
                        content=ft.Column(content_children, spacing=8, scroll=ft.ScrollMode.AUTO),
                        width=400, height=300, padding=10),
                    actions=[ft.TextButton("关闭", on_click=lambda e: page.close(dlg))])
                page.open(dlg)
                page.update()

            backup_status = ft.Text("", size=13, color=ft.Colors.GREY_500)
            backup_picker = ft.FilePicker(on_result=lambda e: on_backup_result(e))
            restore_picker = ft.FilePicker(on_result=lambda e: on_restore_result(e))
            merge_picker = ft.FilePicker(on_result=lambda e: on_merge_result(e))
            page.overlay.append(backup_picker)
            page.overlay.append(restore_picker)
            page.overlay.append(merge_picker)

            # ---------- 手环背单词 操控中心 ----------
            band_status = ft.Text("", size=13, color=ft.Colors.GREY_500)
            band_sync_status = ft.Text("", size=13, color="#E0AF68")
            band_http_status = ft.Text("🔌 本地同步服务：未启动", size=13, color=ft.Colors.GREY_500)
            band_http_btn = ft.ElevatedButton(
                "🔗 启动本地同步", icon=ft.Icons.SENSOR_DOOR,
                on_click=lambda e: toggle_band_http(e))
            band_scope = ft.Dropdown(
                label="单词来源",
                width=170,
                options=[ft.dropdown.Option("due", "今日到期优先"),
                         ft.dropdown.Option("low", "熟练度低优先"),
                         ft.dropdown.Option("new", "新词优先"),
                         ft.dropdown.Option("all", "全部按紧急度")],
                value="due")
            band_count_field = ft.TextField(label="导出数量", value="50", width=120,
                                            keyboard_type=ft.KeyboardType.NUMBER)
            band_export_picker = ft.FilePicker(on_result=lambda e: on_band_export_result(e))
            band_records_picker = ft.FilePicker(on_result=lambda e: on_band_records_result(e))
            page.overlay.append(band_export_picker)
            page.overlay.append(band_records_picker)

            def refresh_band_sync_status():
                """刷新"未同步新词"提醒：新增词推送成功后由 sync_ack 置 True"""
                n = count_unsynced_words()
                if n > 0:
                    band_sync_status.value = f"⚠ 有 {n} 个新增单词尚未同步到手环"
                    band_sync_status.color = "#E0AF68"
                else:
                    band_sync_status.value = "✅ 单词本与手环已同步"
                    band_sync_status.color = "#81C784"
                page.update()

            def on_band_sync_new_words(e):
                """一键同步新词：把新增未同步的词推到手环（scope=unsynced）"""
                if app_state["busy"]:
                    show_toast(f"⏳ 正在「{app_state['busy']}」，先等它跑完", "orange")
                    return
                n = count_unsynced_words()
                if n == 0:
                    show_toast("没有需要同步的新词", "info")
                    return
                if not band_http_running:
                    if not start_band_http_server():
                        show_toast("本地同步未启动，先点启动", "red")
                        return
                    refresh_band_http_ui()
                try:
                    page.launch_url(f"chiyu-sync://push?scope=unsynced&count={min(n, 500)}")
                    show_toast(f"正在推送 {min(n, 500)} 个新词到手环…", "green")
                except Exception as ex:
                    show_toast(f"拉起失败（装了伴生App吗？）：{ex}", "red")

            def refresh_band_http_ui():
                if band_http_running:
                    band_http_btn.text = "🔗 停止本地同步"
                    band_http_status.value = (f"🟢 服务运行中：http://127.0.0.1:{BAND_HTTP_PORT}"
                                              f"\n伴生App「池鱼手环同步」可直连，收回记录自动回传")
                    band_http_status.color = "#81C784"
                else:
                    band_http_btn.text = "🔗 启动本地同步"
                    band_http_status.value = "🔌 本地同步服务：未启动"
                    band_http_status.color = ft.Colors.GREY_500
                page.update()

            def toggle_band_http(e):
                if band_http_running:
                    stop_band_http_server()
                    show_toast("已停止本地同步", "orange")
                else:
                    if start_band_http_server():
                        show_toast("本地同步已启动，可一键推送", "green")
                    else:
                        show_toast("启动失败（端口占用？），改用文件方式", "red")
                refresh_band_http_ui()

            def on_band_quick_push(e):
                """一键推送：拉起伴生App，从本地服务拉词表推手环"""
                if app_state["busy"]:
                    show_toast(f"⏳ 正在「{app_state['busy']}」，先等它跑完", "orange")
                    return
                if not band_http_running:
                    if not start_band_http_server():
                        show_toast("本地同步未启动，先点启动", "red")
                        return
                    refresh_band_http_ui()
                scope = band_scope.value or "due"
                count = 50
                try:
                    count = int((band_count_field.value or "50").strip())
                except Exception:
                    count = 50
                try:
                    page.launch_url(f"chiyu-sync://push?scope={scope}&count={count}")
                    show_toast("已拉起伴生App，正在推送…", "green")
                except Exception as ex:
                    show_toast(f"拉起失败（装了伴生App吗？）：{ex}", "red")

            def on_band_export_click(e):
                if app_state["busy"]:
                    show_toast(f"⏳ 正在「{app_state['busy']}」，先等它跑完", "orange")
                    return
                ts = time.strftime("%Y%m%d_%H%M%S")
                band_export_picker.save_file(
                    dialog_title="保存词表文件（供手环同步使用）",
                    file_name=f"池鱼词表_{ts}.json",
                    file_type=ft.FilePickerFileType.ANY,
                    allowed_extensions=["json"])

            def on_band_export_result(e: ft.FilePickerResultEvent):
                try:
                    count = int((band_count_field.value or "50").strip())
                except Exception:
                    count = 50
                count = max(1, min(count, 2000))
                try:
                    payload = build_band_wordlist(band_scope.value or "due", count)
                except Exception as ex:
                    band_status.value = f"❌ 生成词表失败：{ex}"
                    band_status.color = "#EF5350"
                    page.update()
                    return
                n = len(payload["words"])

                def do_save():
                    try:
                        if e.path:
                            with open(e.path, "w", encoding="utf-8") as f:
                                json.dump(payload, f, ensure_ascii=False)
                            band_status.value = f"✅ 已导出 {n} 词：{e.path}"
                        else:
                            # 保存对话框取消或平台不支持 → 兜底写应用目录
                            fallback = os.path.join(
                                DATA_DIR, f"手环词表_{time.strftime('%Y%m%d_%H%M%S')}.json")
                            with open(fallback, "w", encoding="utf-8") as f:
                                json.dump(payload, f, ensure_ascii=False)
                            band_status.value = f"✅ 已生成 {n} 词：{fallback}"
                        band_status.color = "#81C784"
                    except Exception as ex:
                        band_status.value = f"❌ 导出失败：{ex}"
                        band_status.color = "#EF5350"
                    page.update()

                threading.Thread(target=do_save, daemon=True).start()

            def on_band_records_click(e):
                if app_state["busy"]:
                    show_toast(f"⏳ 正在「{app_state['busy']}」，先等它跑完", "orange")
                    return
                band_records_picker.pick_files(
                    dialog_title="选择手环同步的 records 记录文件",
                    allowed_extensions=["json"], allow_multiple=False)

            def on_band_records_result(e: ft.FilePickerResultEvent):
                if not e.files or len(e.files) == 0:
                    return
                path = e.files[0].path

                def do_merge():
                    try:
                        with open(path, encoding="utf-8") as f:
                            payload = json.load(f)
                        records = payload.get("records") if isinstance(payload, dict) else payload
                        merged, updated, new_due, bad = merge_band_records(records)
                        msg = (f"📥 回收 {merged} 条\n✏️ 更新 {updated} 个单词\n"
                               f"📅 新增待复习 {new_due} 个")
                        if bad:
                            msg += f"\n\n⚠️ 连续错词提醒：{'、'.join(bad[:10])}"
                        dlg = ft.AlertDialog(
                            title=ft.Text("⌚ 手环学习记录已同步"),
                            content=ft.Text(msg, size=14, selectable=True),
                            actions=[ft.TextButton("好", on_click=lambda x: page.close(dlg))])
                        page.open(dlg)
                    except Exception as ex:
                        dlg = ft.AlertDialog(
                            title=ft.Text("⌚ 同步失败"),
                            content=ft.Text(f"解析记录文件出错：\n{ex}", size=14, selectable=True),
                            actions=[ft.TextButton("好", on_click=lambda x: page.close(dlg))])
                        page.open(dlg)
                    page.update()

                threading.Thread(target=do_merge, daemon=True).start()

            def on_backup_result(e: ft.FilePickerResultEvent):
                if not e.path:
                    return
                dest_dir = e.path
                backup_status.value = "⏳ 正在打包..."
                backup_status.color = "#A9B1D6"
                page.update()

                def do_backup():
                    try:
                        ts = time.strftime("%Y%m%d_%H%M%S")
                        zip_path = os.path.join(dest_dir, f"池鱼Study备份_{ts}.zip")
                        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                            for root, dirs, files in os.walk(DATA_DIR):
                                if "_restore_tmp" in root.split(os.sep):
                                    continue
                                for f in files:
                                    if f.startswith("."):
                                        continue
                                    full = os.path.join(root, f)
                                    arc = os.path.relpath(full, DATA_DIR)
                                    zf.write(full, arc)
                        backup_status.value = f"✅ 备份成功：{zip_path}"
                        backup_status.color = "#81C784"
                    except Exception as ex:
                        backup_status.value = f"❌ 备份失败：{str(ex)[:80]}"
                        backup_status.color = "#EF5350"
                    page.update()

                threading.Thread(target=do_backup, daemon=True).start()

            def on_restore_result(e: ft.FilePickerResultEvent):
                if not e.files or len(e.files) == 0:
                    return
                zip_path = e.files[0].path
                backup_status.value = "⏳ 正在恢复..."
                backup_status.color = "#A9B1D6"
                page.update()

                def do_restore():
                    try:
                        os.makedirs(DATA_DIR, exist_ok=True)
                        with zipfile.ZipFile(zip_path, "r") as zf:
                            zf.extractall(DATA_DIR)
                        backup_status.value = "✅ 恢复成功！请重启应用"
                        backup_status.color = "#81C784"
                    except Exception as ex:
                        backup_status.value = f"❌ 恢复失败：{str(ex)[:80]}"
                        backup_status.color = "#EF5350"
                    page.update()

                threading.Thread(target=do_restore, daemon=True).start()

            def on_merge_result(e: ft.FilePickerResultEvent):
                if not e.files or len(e.files) == 0:
                    return
                if app_state["busy"]:
                    backup_status.value = f"⏳ 正在「{app_state['busy']}」，先等它跑完"
                    backup_status.color = "#E0AF68"
                    page.update()
                    return
                zip_path = e.files[0].path
                app_state["busy"] = "合并恢复"
                backup_status.value = "⏳ 正在合并恢复..."
                backup_status.color = "#A9B1D6"
                page.update()

                def do_merge():
                    try:
                        stats, err = merge_restore_from_zip(zip_path)
                        if err:
                            backup_status.value = f"❌ 合并失败：{err[:80]}"
                            backup_status.color = "#EF5350"
                        else:
                            backup_status.value = (
                                f"✅ 合并完成！新增 错题 {stats['errors']} · 笔记 {stats['notes']} · "
                                f"单词 {stats['vocab']} · 金句 {stats['sentences']} · "
                                f"事件 {stats['events']} · 图片 {stats['images']}"
                                f"（请重新进入错题本查看）"
                            )
                            backup_status.color = "#81C784"
                    finally:
                        app_state["busy"] = None
                    page.update()

                threading.Thread(target=do_merge, daemon=True).start()

            def show_vocab_settings_dialog(e):
                settings_now = load_vocab_settings()
                daily_new_field = ft.TextField(label="每日新词数",
                                               value=str(settings_now.get("daily_new", 20)),
                                               keyboard_type=ft.KeyboardType.NUMBER)
                review_limit_field = ft.TextField(
                    label="每日复习上限",
                    value=str(settings_now.get("daily_review_limit", 100)),
                    keyboard_type=ft.KeyboardType.NUMBER)
                mode_dropdown = ft.Dropdown(
                    label="考核模式",
                    options=[ft.dropdown.Option("mix", "混合"),
                             ft.dropdown.Option("word2meaning", "看词选义"),
                             ft.dropdown.Option("meaning2word", "看义选词"),
                             ft.dropdown.Option("spelling", "拼写")],
                    value=settings_now.get("quiz_mode", "mix"))

                def do_save(e):
                    try:
                        new_settings = {
                            "daily_new": int(daily_new_field.value or 20),
                            "daily_review_limit": int(review_limit_field.value or 100),
                            "quiz_mode": mode_dropdown.value,
                            "show_phonetic": True,
                        }
                        save_vocab_settings(new_settings)
                        page.close(dlg)
                        show_toast("✅ 设置已保存", "green")
                    except Exception as ex:
                        show_toast(f"❌ 保存失败: {ex}", "red")

                dlg = ft.AlertDialog(
                    title=ft.Text("⚙️ 单词本设置"),
                    content=ft.Column([daily_new_field, review_limit_field, mode_dropdown],
                                      spacing=10, width=350),
                    actions=[ft.TextButton("取消", on_click=lambda e: page.close(dlg)),
                             ft.ElevatedButton("保存", on_click=do_save)])
                page.open(dlg)

            mine_page = ft.Column([
                ft.Container(height=10),
                ft.Text("⚙️ 个人中心", size=24, weight=ft.FontWeight.BOLD),
                today_plan_card,
                ft.Divider(),
                ft.ElevatedButton("🎯 学习画像", on_click=lambda e: show_learning_profile(e),
                                  icon=ft.Icons.PERSON_OUTLINE),
                ft.ElevatedButton("🏷️ 批量重打标签", on_click=lambda e: batch_retag(e),
                                  icon=ft.Icons.LABEL),
                retag_status,
                ft.ElevatedButton("⚙️ 单词本设置", on_click=lambda e: show_vocab_settings_dialog(e),
                                  icon=ft.Icons.SETTINGS),
                mine_msg,
                ft.Divider(),
                ft.Text("⌚ 手环背单词", size=20),
                band_sync_status,
                band_http_btn,
                band_http_status,
                ft.Row([band_scope, band_count_field]),
                ft.Row([
                    ft.ElevatedButton("🔄 一键同步新词", icon=ft.Icons.SYNC,
                                      on_click=on_band_sync_new_words),
                    ft.ElevatedButton("🚀 一键推送", icon=ft.Icons.SEND,
                                      on_click=on_band_quick_push),
                    ft.ElevatedButton("📤 存为文件", icon=ft.Icons.UPLOAD_FILE,
                                      on_click=on_band_export_click),
                    ft.ElevatedButton("📥 导入记录", icon=ft.Icons.DOWNLOAD_DONE,
                                      on_click=on_band_records_click),
                ]),
                band_status,
                ft.Divider(),
                ft.Text("✅ 学习任务清单", size=20),
                ft.Row([new_task_input, ft.ElevatedButton("添加", on_click=add_task)]),
                task_list,
                ft.Divider(),
                ft.Text("🗑️ 回收站", size=20), recycle_list,
                ft.ElevatedButton("清空回收站", on_click=lambda e: (
                    empty_recycle(), refresh_recycle(), show_toast("已清空", "green"))),
                ft.Divider(),
                ft.Text("🧠 AI 引擎设置", size=20),
                ft.ElevatedButton("👤 查看我的 AI 画像", on_click=lambda e: show_learning_profile(e),
                                  icon=ft.Icons.PERSON_OUTLINE),
                memory_dropdown := ft.Dropdown(
                    label="对话记忆长度",
                    options=[
                        ft.dropdown.Option("auto", "自动（动态，推荐）·像官方App"),
                        ft.dropdown.Option("20000", "短（约1万词）·省额度"),
                        ft.dropdown.Option("50000", "中（约2.5万词）"),
                        ft.dropdown.Option("80000", "长（约4万词）·记忆最强"),
                    ],
                    value=str(ai_config.get("ctx_chars", "auto")),
                    width=280),
                provider_dropdown,
                free_key_input,
                deepseek_key_input,
                deepseek_model_input,
                deepseek_thinking_switch,
                ft.ElevatedButton("保存密钥", on_click=save_keys),
                ft.Row([ft.ElevatedButton("🔌 测试连接", on_click=test_ai_connection),
                        test_conn_result]),
                ft.Divider(),
                ft.Text("🎓 自定义教学 Skill", size=18),
                skill_input, ft.ElevatedButton("保存 Skill", on_click=save_skill),
                ft.Divider(),
                ft.Text("📁 数据文件夹", size=18, weight=ft.FontWeight.BOLD),
                ft.Text("所有数据都保存在此文件夹中", size=13, color="#888888"),
                ft.Row([
                    ft.Text(f"📂 {DATA_DIR}", size=14, expand=True, selectable=True),
                ], spacing=10),
                ft.Text(f"🔍 {DIAG_TEXT}", size=10, color="#888888", selectable=True),
                ft.ElevatedButton("📂 切换文件夹",
                                  on_click=lambda e: sync_folder_picker.get_directory_path(),
                                  icon=ft.Icons.FOLDER_OPEN),
                ft.Text("长按路径可复制", size=12, color="#888888"),
                sync_status_text,
                ft.Divider(),
                ft.Text("💾 数据备份与恢复", size=18, weight=ft.FontWeight.BOLD),
                ft.Row([
                    ft.ElevatedButton("📤 备份数据",
                                      on_click=lambda e: backup_picker.get_directory_path(),
                                      icon=ft.Icons.BACKUP),
                    ft.ElevatedButton("📥 覆盖恢复",
                                      on_click=lambda e: restore_picker.pick_files(
                                          file_type=ft.FilePickerFileType.CUSTOM,
                                          allowed_extensions=["zip"]),
                                      icon=ft.Icons.RESTORE),
                    ft.ElevatedButton("🔀 合并恢复",
                                      on_click=lambda e: merge_picker.pick_files(
                                          file_type=ft.FilePickerFileType.CUSTOM,
                                          allowed_extensions=["zip"]),
                                      icon=ft.Icons.MERGE_TYPE),
                ], spacing=10),
                backup_status,
                ft.Container(height=20),
            ], spacing=20, scroll=ft.ScrollMode.AUTO)

            current_page = ft.Container(expand=True,
                                        animate_opacity=ft.Animation(240, ft.AnimationCurve.EASE_OUT),
                                        animate_scale=ft.Animation(260, ft.AnimationCurve.EASE_OUT),
                                        scale=1.0)

            def switch_page(index):
                if index == 0:
                    current_page.content = home_page
                elif index == 1:
                    current_page.content = subject_page
                elif index == 2:
                    current_page.content = mine_page
                    try:
                        refresh_band_sync_status()
                    except Exception:
                        pass
                # 苹果风页面切换：轻微缩放 + 淡入
                current_page.scale = 0.98
                current_page.opacity = 0.6
                page.update()
                current_page.scale = 1.0
                current_page.opacity = 1.0
                page.update()

            page.navigation_bar = ft.NavigationBar(
                selected_index=0, on_change=lambda e: switch_page(e.control.selected_index),
                destinations=[
                    ft.NavigationBarDestination(icon=ft.Icons.ADD, label="首页"),
                    ft.NavigationBarDestination(icon=ft.Icons.SCHOOL, label="学科"),
                    ft.NavigationBarDestination(icon=ft.Icons.PERSON, label="我的"),
                ])
            switch_page(0)
            _gradient_bg = ft.Stack([
                # 液态玻璃底色：深蓝黑渐变（iOS 动态壁纸质感）
                ft.Container(expand=True, gradient=ft.LinearGradient(
                    begin=ft.alignment.top_left, end=ft.alignment.bottom_right,
                    colors=["#12121C", "#16161E", "#0E0E16"])),
                # 右上蓝紫柔光 + 左下紫光晕（模拟液态玻璃反射）
                ft.Container(expand=True, gradient=ft.RadialGradient(
                    center=ft.alignment.top_right, radius=1.5,
                    colors=["#441A2B5E", "#00000000"])),
                ft.Container(expand=True, gradient=ft.RadialGradient(
                    center=ft.alignment.bottom_left, radius=1.2,
                    colors=["#22BB9AF7", "#00000000"])),
            ], expand=True)
            page.add(ft.Stack([
                _gradient_bg,
                ft.Stack([current_page, chat_dialog, contact_panel, ball_container], expand=True),
            ], expand=True))
            print("步骤7: UI 加载完成")

        load_ui()

    except Exception as e:
        page.controls.clear()
        page.add(ft.Text(f"❌ 启动出错: {str(e)}", color="#EF5350"))
        page.add(ft.Text(f"详细错误:\n{traceback.format_exc()}", size=12, selectable=True))
        page.update()
        print("=== 启动异常 ===")
        traceback.print_exc()


if __name__ == "__main__":
    ft.app(target=main)
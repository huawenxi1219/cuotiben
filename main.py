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
            "review_count": 0, "correct_count": 0, "wrong_count": 0, "last_review": ""
        }
    else:
        L = word_data["learning"]
        L.setdefault("status", "new")
        L.setdefault("level", 0)
        L.setdefault("next_review", datetime.now().strftime("%Y-%m-%d"))
        L.setdefault("review_count", 0)
        L.setdefault("correct_count", 0)
        L.setdefault("wrong_count", 0)
        L.setdefault("last_review", "")
    return word_data


def schedule_next_review(level):
    idx = min(max(level, 0), len(REVIEW_INTERVALS) - 1)
    return REVIEW_INTERVALS[idx]


def update_word_learning(word, result):
    existing = load_jsonl(VOCAB_FILE)
    today = datetime.now().strftime("%Y-%m-%d")
    for i, w in enumerate(existing):
        if w.get("word", "").lower() == word.lower():
            ensure_learning_field(existing[i])
            L = existing[i]["learning"]
            L["review_count"] = L.get("review_count", 0) + 1
            L["last_review"] = time.strftime("%Y-%m-%d %H:%M:%S")
            if result in ("know", "quiz_correct"):
                L["level"] = min(L.get("level", 0) + 1, len(REVIEW_INTERVALS) - 1)
                L["correct_count"] = L.get("correct_count", 0) + 1
                days = schedule_next_review(L["level"])
                L["next_review"] = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
                L["status"] = "mastered" if L["level"] >= 4 else "review"
            elif result == "fuzzy":
                L["next_review"] = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
                L["status"] = "learning"
            elif result in ("forget", "quiz_wrong"):
                L["level"] = 0
                L["wrong_count"] = L.get("wrong_count", 0) + 1
                L["next_review"] = today
                L["status"] = "learning"
            existing[i] = w
            break
    save_jsonl(VOCAB_FILE, existing)


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
        "timestamp": int(time.time()),
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
        "timestamp": int(time.time()),
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
            "knowledge_memory": {}, "error_memory": []
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


def add_recent_focus(kp):
    p = load_user_profile()
    if kp not in p["recent_focus"]:
        p["recent_focus"].insert(0, kp)
        p["recent_focus"] = p["recent_focus"][:10]
        save_user_profile(p)


def load_ai_config():
    if not os.path.exists(AI_CONFIG_FILE):
        return {"provider": "zhipu", "model": "free", "api_key_free": "", "api_key_deepseek": "",
                "api_key_enhanced": "", "monthly_limit": 5.0, "subject_models": {}}
    with open(AI_CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


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
        "url": "https://api.deepseek.com/v1/chat/completions",
        "model": "deepseek-chat",
        "vision_model": "",
        "key_field": "api_key_deepseek",
        "supports_vision": False,
    },
}


def get_api_endpoint():
    cfg = load_ai_config()
    provider = cfg.get("provider", "zhipu")
    info = PROVIDERS.get(provider, PROVIDERS["zhipu"])
    key = cfg.get(info["key_field"], "").strip()
    return key, info["url"], info["model"], info["vision_model"]


def provider_supports_vision():
    cfg = load_ai_config()
    provider = cfg.get("provider", "zhipu")
    return PROVIDERS.get(provider, PROVIDERS["zhipu"]).get("supports_vision", False)


def get_chat_history_file(subject):
    safe = re.sub(r'[\\/*?:"<>|]', "_", subject)
    return os.path.join(CHAT_HISTORY_DIR, f"chat_{safe}.jsonl")


def load_chat_history(subject):
    return load_jsonl(get_chat_history_file(subject))


def save_chat_message(subject, role, content):
    fp = get_chat_history_file(subject)
    data = load_jsonl(fp)
    data.append({"role": role, "content": content, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    save_jsonl(fp, data)


def move_to_recycle(item):
    recycle = load_jsonl(RECYCLE_FILE)
    recycle.append({
        "original_type": item.get("type"), "data": item,
        "delete_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "delete_ts": int(time.time()),
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
        "timestamp": int(time.time()), "deep_analysis": "", "status": "未看",
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
    _cfg = load_ai_config()
    _provider = _cfg.get("provider", "zhipu")
    _info = PROVIDERS.get(_provider, PROVIDERS["zhipu"])
    api_key = _cfg.get(_info["key_field"], "").strip()
    if not api_key:
        return
    prompt = f"""你是一个专业的高中老师。请给下面这道错题打 5-8 个标签。

标签要覆盖以下角度（不必每个都有，但尽量丰富）：
- 知识点（如：二次函数、导数应用、电磁感应）
- 题型（如：求最值、证明题、实验题）
- 易错点（如：忽略定义域、符号错误、单位漏写）
- 方法（如：配方法、数形结合、控制变量法）
- 难度（如：基础、中档、压轴）
- 陷阱（如：分类讨论遗漏、隐含条件）

要求：
- 每个标签 2-6 个字，简洁
- 不要重复
- 不要出现"数学""题目"这种无意义的词

题目内容：
{content_text[:600]}

返回 JSON：
{{"tags": ["标签1", "标签2", "标签3", "标签4", "标签5"], "error_type": "计算错误/概念不清/审题偏差/公式遗忘/方法错误/其他", "difficulty": 1-5, "reason": "简短错误分析"}}
只输出 JSON。"""
    try:
        resp = requests.post(_info["url"],
                             headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                             json={"model": _info["model"], "messages": [{"role": "user", "content": prompt}],
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
            tags = tags[:9]
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


@retry_request(max_retries=3, base_delay=2)
def generate_word_info(word):
    _cfg = load_ai_config()
    _provider = _cfg.get("provider", "zhipu")
    _info = PROVIDERS.get(_provider, PROVIDERS["zhipu"])
    api_key = _cfg.get(_info["key_field"], "").strip()
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
        resp = requests.post(_info["url"],
                             headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                             json={"model": _info["model"], "messages": [{"role": "user", "content": prompt}],
                                   "temperature": 0.3, "max_tokens": 600}, timeout=20)
        if resp.status_code == 200:
            content = resp.json()["choices"][0]["message"]["content"]
            try:
                new_data = json.loads(content)
            except BaseException:
                match = re.search(r'\{[^}]+\}', content)
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
                      "created": now, "updated": now})
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

        def load_ui():
            page.controls.clear()
            page.update()
            print("=== load_ui 开始 ===")

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

            page.theme = ft.Theme(
                font_family="Segoe UI, -apple-system, Roboto, sans-serif",
                color_scheme=ft.ColorScheme(
                    primary="#FF8A65",
                    primary_container="#3A2A22",
                    secondary="#FFB74D",
                    surface="#FAFAFA",
                    surface_variant="#F5F5F5",
                    background="#FAFAFA",
                    on_surface="#1A1A1A",
                    on_background="#1A1A1A",
                ),
                visual_density=ft.VisualDensity.STANDARD,
            )

            page.dark_theme = ft.Theme(
                font_family="Segoe UI, -apple-system, Roboto, sans-serif",
                color_scheme=ft.ColorScheme(
                    primary="#FF8A65",
                    primary_container="#3A2A22",
                    secondary="#FFB74D",
                    surface="#1C1C22",
                    surface_variant="#26262E",
                    background="#131318",
                    on_surface="#FFFFFF",
                    on_background="#FFFFFF",
                ),
                visual_density=ft.VisualDensity.STANDARD,
            )

            main_subject_page = None
            subject_page_content = ft.Container(expand=True)

            def show_toast(text, color="green", duration=1.6):
                if color == "green":
                    bg = "#33FF8A65"
                    icon = "✅"
                elif color == "red":
                    bg = "#33EF5350"
                    icon = "❌"
                else:
                    bg = "#33FFB74D"
                    icon = "ℹ️"

                toast = ft.Container(
                    content=ft.Row([
                        ft.Text(icon, size=22),
                        ft.Text(text, size=16, color=ft.Colors.WHITE, weight=ft.FontWeight.W_500),
                    ], spacing=10, tight=True, alignment=ft.MainAxisAlignment.CENTER),
                    bgcolor=bg,
                    blur=20,
                    border_radius=24,
                    padding=ft.Padding(left=28, right=28, top=16, bottom=16),
                    border=ft.border.all(1, ft.Colors.WHITE24),
                    shadow=ft.BoxShadow(blur_radius=30, color="#88000000"),
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
                            border=ft.border.all(2, "#FF8A65" if is_active else "#555555"),
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
            original_input = ft.TextField(label="原题（题干）", multiline=True, min_lines=3)
            mistake_input = ft.TextField(label="错因", multiline=True, min_lines=2)
            answer_input = ft.TextField(label="标准答案", multiline=True, min_lines=2)
            idea_input = ft.TextField(label="我的理解", multiline=True, min_lines=2)
            tags_input = ft.TextField(label="手动标签（逗号分隔）", multiline=False)

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
                api_key, api_url, _m, vision_model = get_api_endpoint()
                if not api_key:
                    return None
                try:
                    with open(image_path, "rb") as f:
                        img_b64 = base64.b64encode(f.read()).decode("utf-8")
                except BaseException:
                    return None
                prompt = """请分析这张图片中的题目内容，并返回以下 JSON 格式：
{
  "knowledge_point": "该题涉及的知识点（如：三角函数、力学、语法等）",
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
            note_content_input = ft.TextField(label="笔记内容（可选）", multiline=True, min_lines=4)
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

            home_page = ft.Column([
                ft.Container(height=10),
                ft.Text("📸 拍照录题", size=22, weight=ft.FontWeight.BOLD),
                ft.Row([subj_dd], spacing=15) if not is_mobile else ft.Column([subj_dd]),
                original_input,
                mistake_input,
                ft.Divider(),
                ft.Text("🔄 可选补充", size=16),
                answer_input,
                idea_input,
                tags_input,
                ft.Divider(),
                ft.Text("📎 附件上传", size=16),
                picker_col1,
                picker_col2,
                picker_col3,
                progress_row,
                ft.ElevatedButton("💾 保存错题", on_click=submit_error),
                ft.Divider(height=20),
                ft.Text("📝 记笔记", size=22, weight=ft.FontWeight.BOLD),
                ft.Row([note_subject_dd], spacing=15) if not is_mobile else ft.Column([note_subject_dd]),
                note_content_input,
                note_picker_col,
                ft.ElevatedButton("💾 保存笔记", on_click=submit_note),
                ft.Container(height=20),
            ], spacing=15, scroll=ft.ScrollMode.AUTO)

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
                if ball_state.get("moved"):
                    ball_state["moved"] = False
                    return
                if contact_panel.visible:
                    close_contact_panel()
                else:
                    open_contact_panel(e)

            ai_ball = ft.GestureDetector(
                content=ft.Container(
                    content=ft.Text("AI", size=20, color="white", weight=ft.FontWeight.BOLD),
                    width=56,
                    height=56,
                    border_radius=28,
                    bgcolor="#DD1C1C22",
                    blur=12,
                    border=ft.border.all(1, ft.Colors.WHITE24),
                    shadow=ft.BoxShadow(blur_radius=22, color="#99000000"),
                    alignment=ft.alignment.center,
                    ink=True,
                ),
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
                left=20,
                top=20,
                right=20,
                bottom=20,
                bgcolor="#F0242424",
                blur=20,
                border_radius=20,
                padding=20,
                border=ft.border.all(1, ft.Colors.WHITE24),
                shadow=ft.BoxShadow(blur_radius=30, color="#88000000"),
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
                chat_dialog.visible = True
                page.update()

            def call_ai_stream(messages, model_name, on_chunk):
                api_key, api_url, api_model, _v = get_api_endpoint()
                if not api_key:
                    on_chunk("❌ 未配置API密钥")
                    return
                headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                payload = {"model": api_model, "messages": messages,
                           "temperature": 0.7, "max_tokens": 2048, "stream": True}
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
                            on_chunk(accumulated + "\n\n[已停止]")
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
                context_messages = []
                for msg in history[-20:]:
                    context_messages.append({"role": msg["role"], "content": msg["content"]})
                memory_context = get_memory_context(subject if subject != "总AI" else None)
                profile_summary = get_profile_summary()
                strategy = get_teaching_strategy(subject if subject != "总AI" else None)
                system_prompt = f"""你是{display_name}老师，请用结构化方式回答。
- 对于知识类问题，请分点列出要点。
- 对于解题类问题，请先给出思路，再给出步骤。
- 对于作文类问题，请提供框架和例句。
- 回答要简洁、准确、有条理。
- 请主动引用你对这个学生的记忆，让学生感到你了解他。"""
                custom_skill = load_custom_skill()
                if custom_skill:
                    system_prompt += f"\n\n额外的教学指导：{custom_skill}"
                if memory_context:
                    system_prompt += f"\n\n{memory_context}"
                if profile_summary:
                    system_prompt += f"\n\n{profile_summary}"
                if strategy:
                    system_prompt += f"\n\n{strategy}"
                if context_messages:
                    system_prompt += "\n\n以下是最近的对话历史（仅作上下文参考，不要重复历史内容）：\n"
                    for msg in context_messages[-15:]:
                        role_label = "学生" if msg["role"] == "user" else "老师"
                        system_prompt += f"[{role_label}]: {msg['content'][:200]}\n"
                all_messages = [{"role": "system", "content": system_prompt}]
                for msg in context_messages[-15:]:
                    all_messages.append(msg)

                chat_history_display = ft.ListView(spacing=12, expand=True, auto_scroll=True)

                def make_user_bubble(text):
                    return ft.Row([
                        ft.Container(expand=True),
                        ft.Container(
                            content=ft.Text(text, size=14, selectable=True, color="#FFFFFF"),
                            padding=ft.Padding(left=14, right=14, top=10, bottom=10),
                            border_radius=ft.BorderRadius(16, 16, 4, 16),
                            bgcolor="#FF8A65",
                            shadow=ft.BoxShadow(blur_radius=8, color="#33000000"),
                            width=280,
                        ),
                    ], alignment=ft.MainAxisAlignment.END)

                def make_ai_bubble(text, can_regenerate=True, content_ref=None):
                    if content_ref is None:
                        content_ref = {"col": None}
                    content_col = ft.Column([
                        ft.Text(text, size=14, selectable=True, color="#EEEEEE"),
                    ], spacing=4)
                    content_ref["col"] = content_col

                    def _do_copy(e):
                        try:
                            current = content_col.controls[0].value or ""
                            page.set_clipboard(current)
                            show_toast("已复制", "green")
                        except Exception:
                            show_toast("复制失败", "red")

                    action_row = ft.Row([
                        ft.IconButton(
                            icon=ft.Icons.COPY_OUTLINED, icon_size=16, tooltip="复制",
                            icon_color="#888888",
                            on_click=_do_copy),
                        ft.IconButton(
                            icon=ft.Icons.REFRESH, icon_size=16, tooltip="重新生成",
                            icon_color="#888888",
                            on_click=lambda e: regenerate_last(),
                        ) if can_regenerate else ft.Container(width=0),
                    ], spacing=2, tight=True)
                    bubble = ft.Container(
                        content=ft.Column([content_col, action_row], spacing=4),
                        padding=ft.Padding(left=14, right=8, top=10, bottom=6),
                        border_radius=ft.BorderRadius(16, 16, 16, 4),
                        bgcolor="#26262E",
                        border=ft.border.all(1, "#3A3A45"),
                        shadow=ft.BoxShadow(blur_radius=8, color="#33000000"),
                        width=300,
                    )
                    return ft.Row([
                        bubble,
                        ft.Container(expand=True),
                    ], alignment=ft.MainAxisAlignment.START), content_col

                for msg in history:
                    if msg["role"] == "user":
                        chat_history_display.controls.append(make_user_bubble(msg["content"]))
                    else:
                        bubble_row, _ = make_ai_bubble(msg["content"])
                        chat_history_display.controls.append(bubble_row)

                chat_input = ft.TextField(
                    hint_text=f"向{display_name}老师提问...",
                    multiline=True, min_lines=1, max_lines=8,
                    border_radius=20,
                    border_color="#3A3A45",
                    focused_border_color="#FF8A65",
                    filled=True,
                    fill_color="#1F1F26",
                    text_size=14,
                    content_padding=ft.Padding(left=14, right=14, top=10, bottom=10),
                    expand=True,
                )
                send_btn = ft.Container(
                    content=ft.Icon(ft.Icons.ARROW_UPWARD, size=20, color="#FFFFFF"),
                    width=40, height=40, border_radius=20,
                    bgcolor="#FF8A65",
                    alignment=ft.alignment.center,
                    on_click=lambda e: handle_send(),
                    ink=True,
                    shadow=ft.BoxShadow(blur_radius=8, color="#44FF8A65"),
                )
                stop_btn = ft.TextButton("停止生成", visible=False)

                quick_row = ft.Row([
                    ft.Container(
                        content=ft.Text("再讲一遍", size=12, color="#CCCCCC"),
                        padding=ft.Padding(left=12, right=12, top=6, bottom=6),
                        border_radius=14, bgcolor="#26262E",
                        border=ft.border.all(1, "#3A3A45"),
                        on_click=lambda e: handle_send("请再用更简单的方式讲一遍"),
                        ink=True),
                    ft.Container(
                        content=ft.Text("举个例子", size=12, color="#CCCCCC"),
                        padding=ft.Padding(left=12, right=12, top=6, bottom=6),
                        border_radius=14, bgcolor="#26262E",
                        border=ft.border.all(1, "#3A3A45"),
                        on_click=lambda e: handle_send("请举一个具体例子"),
                        ink=True),
                    ft.Container(
                        content=ft.Text("出类似的题", size=12, color="#CCCCCC"),
                        padding=ft.Padding(left=12, right=12, top=6, bottom=6),
                        border_radius=14, bgcolor="#26262E",
                        border=ft.border.all(1, "#3A3A45"),
                        on_click=lambda e: handle_send("出一道类似的题让我练练"),
                        ink=True),
                ], spacing=8, scroll=ft.ScrollMode.AUTO)

                last_user_msg = {"text": ""}
                last_ai_content_ref = {"col": None}

                def regenerate_last():
                    if not last_user_msg["text"]:
                        return
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
                    if insert_user_bubble:
                        chat_history_display.controls.append(make_user_bubble(content))
                    send_btn.visible = False
                    stop_btn.visible = True
                    page.update()
                    if insert_user_bubble:
                        save_chat_message(subject, "user", content)
                    current_messages = list(all_messages)
                    current_messages.append({"role": "user", "content": content})
                    ai_response = {"text": ""}

                    content_ref = {"col": None}
                    bubble_row, content_col = make_ai_bubble("▌", can_regenerate=False, content_ref=content_ref)
                    last_ai_content_ref["col"] = content_col
                    chat_history_display.controls.append(bubble_row)
                    page.update()

                    def on_chunk(text):
                        ai_response["text"] = text
                        try:
                            if content_ref["col"] and len(content_ref["col"].controls) > 0:
                                content_ref["col"].controls[0].value = text if text else "▌"
                                page.update()
                        except Exception:
                            pass

                    def ai_thread():
                        nonlocal generation_active, stop_flag
                        generation_active = True
                        stop_flag = False
                        try:
                            call_ai_stream(current_messages, "auto", on_chunk)
                        finally:
                            generation_active = False
                        try:
                            if content_ref["col"] and len(content_ref["col"].controls) > 0:
                                content_ref["col"].controls[0].value = ai_response["text"] if ai_response["text"] else "（无回应）"
                        except Exception:
                            pass
                        send_btn.visible = True
                        stop_btn.visible = False
                        if ai_response["text"]:
                            save_chat_message(subject, "assistant", ai_response["text"])
                            update_chat_memory(subject, content, ai_response["text"])
                        update_chat_stats(subject)
                        page.update()

                    threading.Thread(target=ai_thread, daemon=True).start()

                def stop_generation(e):
                    nonlocal stop_flag
                    stop_flag = True
                stop_btn.on_click = stop_generation

                def clear_history(e):
                    fp = get_chat_history_file(subject)
                    save_jsonl(fp, [])
                    chat_history_display.controls.clear()
                    page.update()
                    show_toast("✅ 对话历史已清除", "green")

                result_col = ft.Column([
                    ft.Container(
                        content=ft.Row([
                            ft.Column([
                                ft.Text(f"💬 {display_name}", size=18, weight=ft.FontWeight.BOLD),
                                ft.Text(f"{_provider_name} · {_model_name}", size=11, color="#888888"),
                            ], spacing=2, expand=True),
                            ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, icon_size=20,
                                          tooltip="清除历史", on_click=clear_history),
                            ft.IconButton(icon=ft.Icons.CLOSE, icon_size=22,
                                          on_click=lambda e: (setattr(chat_dialog, 'visible', False), page.update())),
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        padding=ft.Padding(left=4, right=4, top=8, bottom=8),
                    ),
                    ft.Divider(height=1, color="#2F2F38"),
                    ft.Container(content=chat_history_display, expand=True, padding=ft.Padding(left=4, right=4, top=8, bottom=8)),
                    quick_row,
                    ft.Container(
                        content=ft.Row([
                            chat_input,
                            send_btn,
                            stop_btn,
                        ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.END),
                        padding=ft.Padding(left=0, right=0, top=6, bottom=4),
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
                    return word_data
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
                word_data = _fill_word_with_ai(word_data)
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
                    content_children.append(ft.Text(f"🔊 {phonetic}", size=16, color="#FF8A65"))
                if meaning:
                    content_children.append(ft.Text(meaning, size=16, color="#81C784"))
                if example:
                    content_children.append(ft.Text(f"例句：{example}", size=14, italic=True, color=ft.Colors.GREY_400))
                if forms:
                    forms_words = [f.strip() for f in forms.replace(',', ' ').split() if f.strip()]
                    if forms_words:
                        forms_row = ft.Row(spacing=8, wrap=True)
                        forms_row.controls.append(ft.Text("变形：", size=14, weight=ft.FontWeight.BOLD))
                        all_vocab_now = load_jsonl(VOCAB_FILE)
                        for fw in forms_words:
                            target_word_data = next((w for w in all_vocab_now if w.get("word", "").lower() == fw.lower()), None)
                            if target_word_data:
                                btn = ft.TextButton(
                                    text=fw,
                                    on_click=lambda e, wd=target_word_data: _open_word_detail(wd),
                                    style=ft.ButtonStyle(color="#64B5F6",
                                                         text_style=ft.TextStyle(decoration=ft.TextDecoration.UNDERLINE)))
                            else:
                                def make_gen_click(fw_word):
                                    def on_click(e):
                                        show_toast(f"⏳ 正在生成 {fw_word}...", "info")
                                        new_d = generate_word_info(fw_word)
                                        if new_d:
                                            ev = load_jsonl(VOCAB_FILE)
                                            ev.append(new_d)
                                            save_jsonl(VOCAB_FILE, ev)
                                            show_toast(f"✅ 已添加 {fw_word}", "green")
                                        else:
                                            show_toast(f"❌ 生成失败", "red")
                                    return on_click
                                btn = ft.TextButton(
                                    text=fw, on_click=make_gen_click(fw),
                                    style=ft.ButtonStyle(color="#FFB74D",
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
                            content_children.append(ft.Text(gp, size=13, color="#64B5F6"))
                if phrases:
                    content_children.append(ft.Text("🔗 短语", size=14, weight=ft.FontWeight.BOLD))
                    for ph in phrases:
                        content_children.append(ft.Text(f"• {ph}", size=13, color="#4DB6AC"))
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
                        bgcolor="#66BB6A" if is_in_nw else "#FF8A65",
                        border_radius=20,
                        padding=ft.Padding(left=16, right=16, top=8, bottom=8),
                        on_click=toggle_nw, ink=True))
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
                        btn.bgcolor = "#FF8A65" if i == idx else "#26262E"
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
                        border_radius=10, bgcolor="#26262E",
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
                                                color="#FFB74D" if is_new else ft.Colors.GREY_500),
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
                    return ft.Column([
                        import_btn,
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
                                    leading=ft.Icon(ft.Icons.BOOKMARK, size=18, color="#FFB74D"),
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
                    today_new_limit = settings.get("daily_new", 20)
                    today_new = get_today_new_words(today_new_limit)
                    today_review = get_today_review_words(settings.get("daily_review_limit", 100))
                    queue = [{"word": w, "mode": "review"} for w in today_review] + \
                            [{"word": w, "mode": "new"} for w in today_new]
                    state = {"idx": 0, "flipped": False}
                    card_area = ft.Container(expand=True)
                    progress_text = ft.Text("", size=13, color=ft.Colors.GREY_500)
                    counter_text = ft.Text("", size=15, weight=ft.FontWeight.BOLD)
                    action_area = ft.Container()

                    def render_card():
                        card_area.content = None
                        action_area.content = None
                        if state["idx"] >= len(queue):
                            card_area.content = ft.Container(
                                content=ft.Column([
                                    ft.Text("🎉", size=60),
                                    ft.Text("今日学习任务完成！", size=22, weight=ft.FontWeight.BOLD, color="#81C784"),
                                    ft.Text(f"共复习 {len(today_review)} 词，新学 {len(today_new)} 词",
                                            size=14, color=ft.Colors.GREY_500),
                                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                    alignment=ft.MainAxisAlignment.CENTER, spacing=10),
                                alignment=ft.alignment.center, expand=True)
                            progress_text.value = ""
                            counter_text.value = ""
                            page.update()
                            return
                        item = queue[state["idx"]]
                        w = item["word"]
                        word = w.get("word", "")
                        phonetic = w.get("phonetic", "")
                        meaning = w.get("meaning", "")
                        example = w.get("example", "")
                        forms = w.get("forms", "")
                        counter_text.value = f"{state['idx']+1} / {len(queue)}"
                        progress_text.value = "复习" if item["mode"] == "review" else "新词"
                        if not state["flipped"]:
                            front = ft.Container(
                                content=ft.Column([
                                    ft.Text("🔊" if settings.get("show_phonetic") else "", size=30),
                                    ft.Text(word, size=42, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                                    ft.Container(height=20),
                                    ft.Text("点击卡片显示释义", size=13, color=ft.Colors.GREY_500),
                                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                    alignment=ft.MainAxisAlignment.CENTER, spacing=10),
                                alignment=ft.alignment.center, expand=True,
                                bgcolor="#26262E", border_radius=20,
                                border=ft.border.all(1, ft.Colors.WHITE10),
                                padding=30, ink=True,
                                on_click=lambda e: (state.update({"flipped": True}), render_card()))
                            card_area.content = front
                            action_area.content = ft.Row([
                                ft.ElevatedButton("显示答案", icon=ft.Icons.VISIBILITY,
                                                  on_click=lambda e: (state.update({"flipped": True}), render_card()),
                                                  bgcolor="#FF8A65", color="#FFFFFF", expand=True)
                            ], spacing=10)
                        else:
                            back = ft.Container(
                                content=ft.Column([
                                    ft.Text(word, size=30, weight=ft.FontWeight.BOLD),
                                    ft.Text(phonetic, size=16, color="#FF8A65") if phonetic else ft.Text(""),
                                    ft.Divider(),
                                    ft.Text(meaning, size=18, color="#81C784"),
                                    ft.Text(f"例句：{example}", size=13, italic=True, color=ft.Colors.GREY_400) if example else ft.Text(""),
                                    ft.Text(f"变形：{forms}", size=13, color=ft.Colors.GREY_400) if forms else ft.Text(""),
                                ], spacing=8, scroll=ft.ScrollMode.AUTO),
                                alignment=ft.alignment.top_left,
                                bgcolor="#26262E", border_radius=20,
                                border=ft.border.all(1, ft.Colors.WHITE10),
                                padding=20, expand=True)
                            card_area.content = back
                            action_area.content = ft.Row([
                                ft.ElevatedButton("❌ 不认识", on_click=lambda e: mark("forget"),
                                                  bgcolor="#EF5350", color="#FFFFFF", expand=True),
                                ft.ElevatedButton("🤔 模糊", on_click=lambda e: mark("fuzzy"),
                                                  bgcolor="#FFB74D", color="#FFFFFF", expand=True),
                                ft.ElevatedButton("✅ 认识", on_click=lambda e: mark("know"),
                                                  bgcolor="#66BB6A", color="#FFFFFF", expand=True),
                            ], spacing=10)
                        page.update()

                    def mark(result):
                        if state["idx"] >= len(queue):
                            return
                        item = queue[state["idx"]]
                        word = item["word"].get("word", "")
                        update_word_learning(word, result)
                        log_learning_event("vocab_study", "英语", kp=word,
                                           detail=f"{item['mode']} - {result}",
                                           correct=(result == "know"))
                        state["idx"] += 1
                        state["flipped"] = False
                        render_card()

                    render_card()
                    return ft.Column([
                        ft.Row([counter_text, progress_text], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
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
                                                      expand=True, bgcolor="#26262E", color="#FFFFFF")
                                opt_btns.append(b)
                            quiz_area.content = ft.Column([
                                ft.Text("选择正确的中文释义", size=13, color=ft.Colors.GREY_500),
                                ft.Text(word, size=36, weight=ft.FontWeight.BOLD),
                                ft.Text(phonetic, size=14, color="#FF8A65") if phonetic else ft.Text(""),
                                ft.Container(height=20),
                                ft.Column(opt_btns, spacing=8),
                                ft.Container(height=10),
                                result_text,
                                ft.Container(height=10),
                                ft.Row([ft.ElevatedButton("下一题", on_click=lambda e: next_question(),
                                                          bgcolor="#FF8A65", color="#FFFFFF")],
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
                                                      expand=True, bgcolor="#26262E", color="#FFFFFF")
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
                                                          bgcolor="#FF8A65", color="#FFFFFF")],
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
                                    ft.ElevatedButton("提交", on_click=check, bgcolor="#FF8A65", color="#FFFFFF"),
                                    ft.ElevatedButton("下一题", on_click=lambda e: next_question(),
                                                      bgcolor="#26262E", color="#FFFFFF"),
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
                    expand=True, border_color="#FF8A65", border_width=2)
                local_search_btn = ft.ElevatedButton(
                    "搜索", on_click=lambda e: do_local_search(), icon=ft.Icons.SEARCH,
                    bgcolor="#FF8A65", color=ft.Colors.WHITE)
                ai_search_btn = ft.TextButton(
                    "🤖 AI 深度搜索", on_click=lambda e: perform_search(e))
                search_status = ft.Text("", size=13, color=ft.Colors.GREY_500)
                search_row = ft.Row([search_input, local_search_btn, ai_search_btn], spacing=10)
                list_view = ft.ListView(spacing=10, expand=True)

                def render_list(display_list=None):
                    list_view.controls.clear()
                    if display_list is None:
                        display_list = [(it, None) for it in subject_items]
                    if not display_list:
                        list_view.controls.append(ft.Container(
                            content=ft.Text("  暂无错题", size=16, color=ft.Colors.GREY_500),
                            padding=20))
                        page.update()
                        return
                    for idx, pair in enumerate(display_list):
                        try:
                            item, score = pair
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
                            is_highlighted = score is not None and score > 0
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
                                        bgcolor="#2F2F38", alignment=ft.alignment.center,
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
                                bgcolor="#2F2F38", border_radius=8)

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
                                                bgcolor="#3A2A22", border_radius=10,
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

                                    action_row = ft.Row([
                                        ft.ElevatedButton("🎓 问老师", on_click=open_ask_teacher,
                                                          icon=ft.Icons.SCHOOL, bgcolor="#FF8A65",
                                                          color=ft.Colors.WHITE),
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
                                                    "#FF8A65" if is_highlighted else "#4A4A55"),
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
                        search_status.value = f"❌ 本地没有匹配「{q}」的错题"
                        search_status.color = "#FFB74D"
                        render_list([])
                        page.update()
                        return
                    ranked = sorted(score_map.items(), key=lambda x: -x[1])
                    display_list = [(subject_items[i], s) for i, s in ranked]
                    render_list(display_list)
                    search_status.value = f"✅ 本地加权搜索：{len(display_list)} 条（按匹配度排序）"
                    search_status.color = "#81C784"
                    page.update()

                def perform_search(e):
                    query = search_input.value.strip()
                    if not query:
                        search_status.value = "请输入搜索内容"
                        search_status.color = "#FFB74D"
                        page.update()
                        return
                    search_status.value = f"⏳ AI 正在分析：{query}"
                    search_status.color = "#FF8A65"
                    page.update()

                    def do_search():
                        api_key, api_url, api_model, _v = get_api_endpoint()
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
                                        search_status.color = "#FFB74D"
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
                            color="#FF8A65"),
                    search_row,
                    search_status,
                    ft.Divider(height=1),
                    ft.Container(content=list_view, expand=True),
                ], spacing=8, expand=True)

            def build_note_list_page(subject):
                items = load_jsonl(NOTES_FILE)
                subject_items = [i for i in items if i.get("subject") == subject]
                subject_items.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
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

                                    action_row = ft.Row([
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
                return list_view

            def build_sentence_page(subject):
                CATEGORIES = ["全部", "开头", "转折", "结尾", "观点", "举例", "读后续写", "其他"]
                category_colors = {"开头": "#1A2840", "转折": "#3A2A18", "结尾": "#1A2E1A",
                                   "观点": "#3A1A28", "举例": "#2E1A3A", "读后续写": "#1A2E3A",
                                   "其他": "#26262E"}
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
                        status_text.color = "#FF8A65"
                        page.update()

                        def gen_thread():
                            api_key, api_url, api_model, _v = get_api_endpoint()
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
                        bg_color = category_colors.get(cat, "#26262E")
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
                                            icon_color="#FFB74D" if favorite else ft.Colors.GREY_500,
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
                            border=ft.border.all(1, "#FFB74D" if favorite else "#2F2F38"))
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
                    ("📋", "错题本", "#3A2A22"),
                    ("📝", "笔记本", "#223A22"),
                    ("📖", "单词本", "#3A2F22"),
                    ("💬", "金句", "#3A2233"),
                ]
                cards_config = all_cards if subject == "英语" else all_cards[:2]
                grid = ft.ResponsiveRow(spacing=20, run_spacing=20, expand=True)
                for icon, name, bg in cards_config:
                    card = ft.Container(
                        content=ft.Column([
                            ft.Text(icon, size=36),
                            ft.Text(name, size=16, weight=ft.FontWeight.BOLD),
                        ], alignment=ft.MainAxisAlignment.CENTER,
                           horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
                        bgcolor=bg, border_radius=18, padding=20,
                        border=ft.border.all(1, ft.Colors.WHITE10),
                        shadow=ft.BoxShadow(blur_radius=12, color="#44000000"),
                        ink=True,
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

                func_pages = {
                    "错题本": build_error_list_page(subject),
                    "笔记本": build_note_list_page(subject),
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
                ], spacing=10, expand=True)
                subject_page_content.content = full_page
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
                        bgcolor="#FF8A65" if is_selected else "#26262E",
                        on_click=lambda e, ss=s: on_subject_selected(ss))
                    subj_buttons.append(btn)
                return ft.Container(content=ft.Column(subj_buttons, spacing=6), width=100, padding=10)

            def build_subject_page():
                nonlocal selected_subject_for_page
                left_panel = build_subject_left_panel(selected_subject_for_page)
                right_panel = build_function_card_grid(selected_subject_for_page)
                return ft.Row([
                    left_panel,
                    ft.VerticalDivider(width=1, color="#2F2F38"),
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
                target.color = "#64B5F6"
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
                        subject_errors[err.get("subject", "未知")] = \
                            subject_errors.get(err.get("subject", "未知"), 0) + 1
                    weak_know = sorted(profile.get("weak_knowledge", {}).items(),
                                       key=lambda x: x[1], reverse=True)[:5]
                    prompt = f"""你是高三学习规划师。距离高考{days_left}天。请生成今日学习计划（纯文本）：
各科错题数：{json.dumps(subject_errors, ensure_ascii=False)}
薄弱知识点：{json.dumps(weak_know, ensure_ascii=False)}
格式：1.总体建议 2.3-5个具体任务（科目+内容+耗时） 3.鼓励语"""
                    api_key, api_url, api_model, _v = get_api_endpoint()
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
                                                   "temperature": 0.7, "max_tokens": 800}, timeout=30)
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
                padding=15, border_radius=16, bgcolor="#2A2620",
                border=ft.border.all(1, "#6B5838"),
                shadow=ft.BoxShadow(blur_radius=12, color="#44000000"))

            task_list = ft.Column(spacing=6)
            new_task_input = ft.TextField(label="新学习任务", expand=True)

            def add_task(e):
                text = new_task_input.value.strip()
                if text:
                    tasks = load_jsonl(TASKS_FILE)
                    tasks.append({"text": text, "done": False,
                                  "created": time.strftime("%Y-%m-%d %H:%M:%S")})
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

            def save_keys(e):
                cfg = load_ai_config()
                cfg["provider"] = provider_dropdown.value
                cfg["api_key_free"] = free_key_input.value.strip()
                cfg["api_key_deepseek"] = deepseek_key_input.value.strip()
                save_ai_config(cfg)
                show_toast("API 配置已保存", "green")

            test_conn_result = ft.Text("", size=14)

            def test_ai_connection(e):
                test_conn_result.value = "⏳ 测试中..."
                test_conn_result.color = "#64B5F6"
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
                                test_conn_result.color = "#FFB74D"
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
                retag_status.color = "#FF8A65"
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
                                             bgcolor="#2F2F38", border_radius=4)
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
                                           color=bar_color, bgcolor="#2F2F38"))
                        if summary:
                            content_children.append(
                                ft.Text(f"  → {summary}", size=11, color="#888888"))
                else:
                    content_children.append(ft.Text("暂无知识点数据", size=13, color="#888888"))
                content_children.append(ft.Divider(height=1, color=ft.Colors.GREY_700))
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
                color_map = {"语文": "#64B5F6", "数学": "#EF5350", "英语": "#81C784",
                             "物理": "#BA68C8", "化学": "#FFA726", "生物": "#4DB6AC",
                             "历史": "#FFD54F", "政治": "#F06292", "地理": "#4DD0E1"}
                for subject, count in sorted_subjects:
                    percentage = min((count / max_count) * 100, 100) if max_count > 0 else 0
                    color = color_map.get(subject, "#78909C")
                    progress_bar = ft.ProgressBar(value=percentage / 100, width=200,
                                                  height=8, color=color, bgcolor="#2F2F38",
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
            page.overlay.append(backup_picker)
            page.overlay.append(restore_picker)

            def on_backup_result(e: ft.FilePickerResultEvent):
                if not e.path:
                    return
                dest_dir = e.path
                backup_status.value = "⏳ 正在打包..."
                backup_status.color = "#64B5F6"
                page.update()

                def do_backup():
                    try:
                        ts = time.strftime("%Y%m%d_%H%M%S")
                        zip_path = os.path.join(dest_dir, f"池鱼Study备份_{ts}.zip")
                        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                            for root, dirs, files in os.walk(DATA_DIR):
                                for f in files:
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
                backup_status.color = "#64B5F6"
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
                ft.Text("✅ 学习任务清单", size=20),
                ft.Row([new_task_input, ft.ElevatedButton("添加", on_click=add_task)]),
                task_list,
                ft.Divider(),
                ft.Text("🗑️ 回收站", size=20), recycle_list,
                ft.ElevatedButton("清空回收站", on_click=lambda e: (
                    empty_recycle(), refresh_recycle(), show_toast("已清空", "green"))),
                ft.Divider(),
                ft.Text("🧠 AI 引擎设置", size=20),
                provider_dropdown,
                free_key_input,
                deepseek_key_input,
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
                    ft.ElevatedButton("📥 恢复数据",
                                      on_click=lambda e: restore_picker.pick_files(
                                          file_type=ft.FilePickerFileType.CUSTOM,
                                          allowed_extensions=["zip"]),
                                      icon=ft.Icons.RESTORE),
                ], spacing=10),
                backup_status,
                ft.Container(height=20),
            ], spacing=20, scroll=ft.ScrollMode.AUTO)

            current_page = ft.Container(expand=True)

            def switch_page(index):
                if index == 0:
                    current_page.content = home_page
                elif index == 1:
                    current_page.content = subject_page
                elif index == 2:
                    current_page.content = mine_page
                page.update()

            page.navigation_bar = ft.NavigationBar(
                selected_index=0, on_change=lambda e: switch_page(e.control.selected_index),
                destinations=[
                    ft.NavigationBarDestination(icon=ft.Icons.ADD, label="首页"),
                    ft.NavigationBarDestination(icon=ft.Icons.SCHOOL, label="学科"),
                    ft.NavigationBarDestination(icon=ft.Icons.PERSON, label="我的"),
                ])
            switch_page(0)
            page.add(ft.Stack([current_page, chat_dialog, contact_panel, ball_container], expand=True))
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
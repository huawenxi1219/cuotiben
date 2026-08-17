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
import string
import sys
import base64
from datetime import datetime, timedelta
import traceback

# ==================== 固定数据目录（外部存储） ====================
DATA_DIR = "/storage/emulated/0/智能错题助手"

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

_jsonl_lock = threading.Lock()
TARGET_VOCAB_COUNT = 3500

# ==================== 调试开关 ====================
DEBUG = True

# ==================== API 自动重试装饰器 ====================
def retry_request(max_retries=3, base_delay=2, backoff=2, exceptions=(requests.exceptions.Timeout, requests.exceptions.ConnectionError)):
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    if kwargs.get('stream', False):
                        return func(*args, **kwargs)
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_retries:
                        raise
                    delay = base_delay * (backoff ** attempt)
                    print(f"[重试] 第{attempt+1}次失败，{delay}秒后重试... 错误: {e}")
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
                        except:
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

def save_error(subject, original="", original_media=None, answer="", answer_media=None,
               mistake="", idea="", idea_media=None, manual_tags=""):
    if original_media is None:
        original_media = []
    if answer_media is None:
        answer_media = []
    if idea_media is None:
        idea_media = []
    user_tags = []
    if manual_tags.strip():
        user_tags = [tag.strip() for tag in manual_tags.split(",") if tag.strip()]
    data = load_jsonl(ERRORS_FILE)
    question_media = list(set(original_media))
    entry = {
        "type": "error", "subject": subject, "original": original, "original_media": original_media,
        "answer": answer, "answer_media": answer_media, "mistake": mistake, "idea": idea,
        "idea_media": idea_media, "question": original, "question_media": question_media,
        "tags": [subject] + user_tags if user_tags else [subject],
        "error_type": "", "difficulty": 0, "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "timestamp": int(time.time()), "deep_analysis": ""
    }
    data.append(entry)
    save_jsonl(ERRORS_FILE, data)
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
    ai_config = load_ai_config()
    api_key = ai_config.get("api_key_free", "").strip()
    if not api_key:
        return
    prompt = f"""你是一个专业的高中教师。请分析以下错题，并严格按照JSON格式输出标签信息：
{{
  "knowledge_point": "三级知识点",
  "sub_knowledge": "四级细分题型",
  "error_type": "计算错误/概念不清/审题偏差/公式遗忘/方法错误/其他",
  "difficulty": 1-5,
  "reason": "简短错误分析"
}}
题目内容：
{content_text[:500]}
只输出JSON。"""
    try:
        resp = requests.post("https://open.bigmodel.cn/api/paas/v4/chat/completions",
                             headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                             json={"model": "glm-4-flash", "messages": [{"role": "user", "content": prompt}],
                                   "temperature": 0.3, "max_tokens": 300}, timeout=30)
        if resp.status_code == 200:
            content = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            try:
                tag_data = json.loads(content)
            except:
                match = re.search(r'\{[^}]+\}', content)
                tag_data = json.loads(match.group()) if match else {}
            tags = [target.get("subject", "")]
            if tag_data.get("knowledge_point"):
                tags.append(tag_data["knowledge_point"])
            if tag_data.get("sub_knowledge"):
                tags.append(tag_data["sub_knowledge"])
            error_type = tag_data.get("error_type", "")
            difficulty = tag_data.get("difficulty", 0)
            errors = load_jsonl(ERRORS_FILE)
            for err in errors:
                if err.get("timestamp") == timestamp:
                    err["tags"] = tags
                    err["error_type"] = error_type
                    err["difficulty"] = difficulty
                    break
            save_jsonl(ERRORS_FILE, errors)
            subject = target.get("subject", "")
            if subject:
                update_weak_subject(subject, 0.1)
            if tag_data.get("knowledge_point"):
                update_weak_knowledge(f"{subject}-{tag_data['knowledge_point']}", 0.15)
            if error_type:
                profile = load_user_profile()
                profile["error_types"][error_type] = profile["error_types"].get(error_type, 0) + 1
                save_user_profile(profile)
            if tag_data.get("knowledge_point"):
                add_recent_focus(f"{subject}-{tag_data['knowledge_point']}")
    except:
        pass

def save_note(subject, content, media):
    data = load_jsonl(NOTES_FILE)
    data.append({"type": "note", "subject": subject, "content": content, "media": media,
                 "time": time.strftime("%Y-%m-%d %H:%M:%S"), "timestamp": int(time.time())})
    save_jsonl(NOTES_FILE, data)

def search_related_errors(subject, question_text, limit=3):
    all_errors = load_jsonl(ERRORS_FILE)
    if not all_errors:
        return []
    subject_errors = [e for e in all_errors if e.get("subject") == subject]
    if not subject_errors:
        return []
    keywords = set(re.findall(r'[\w\u4e00-\u9fff]{2,}', question_text))
    scored = []
    for err in subject_errors[-20:]:
        score = 0
        for tag in err.get("tags", []):
            for kw in keywords:
                if kw in tag:
                    score += 3
        for field in ["original", "mistake", "idea"]:
            for kw in keywords:
                if kw in err.get(field, ""):
                    score += 1
        if score > 0:
            scored.append((score, err))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [err for _, err in scored[:limit]]

def load_new_words():
    return load_jsonl(NEW_WORDS_FILE)

def load_sentences():
    return load_jsonl(SENTENCES_FILE)

def save_sentences(sentences):
    save_jsonl(SENTENCES_FILE, sentences)

def add_sentence(category, sentence, translation="", favorite=False):
    sentences = load_sentences()
    new_id = max([s.get("id", 0) for s in sentences]) + 1 if sentences else 1
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    sentences.append({
        "id": new_id,
        "category": category,
        "sentence": sentence,
        "translation": translation,
        "favorite": favorite,
        "created": now,
        "updated": now
    })
    save_sentences(sentences)
    return new_id

def delete_sentence(sentence_id):
    sentences = load_sentences()
    sentences = [s for s in sentences if s.get("id") != sentence_id]
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

def save_new_words(data):
    save_jsonl(NEW_WORDS_FILE, data)

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
    except:
        return {"subject": subject}

def clean_latex(text):
    superscript_map = {
        '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴', '5': '⁵',
        '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
        '+': '⁺', '-': '⁻', '=': '⁼', '(': '⁽', ')': '⁾', 'n': 'ⁿ', 'i': 'ⁱ'
    }
    subscript_map = {
        '0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄', '5': '₅',
        '6': '₆', '7': '₇', '8': '₈', '9': '₉',
        '+': '₊', '-': '₋', '=': '₌', '(': '₍', ')': '₎', 'x': 'ₓ', 'a': 'ₐ', 'e': 'ₑ', 'n': 'ₙ'
    }
    symbol_map = {
        r'\pi': 'π', r'\Pi': 'Π', r'\theta': 'θ', r'\Theta': 'Θ', r'\alpha': 'α',
        r'\beta': 'β', r'\gamma': 'γ', r'\Gamma': 'Γ', r'\delta': 'δ', r'\Delta': 'Δ',
        r'\epsilon': 'ε', r'\lambda': 'λ', r'\Lambda': 'Λ', r'\mu': 'μ', r'\sigma': 'σ',
        r'\Sigma': 'Σ', r'\omega': 'ω', r'\Omega': 'Ω', r'\infty': '∞', r'\pm': '±',
        r'\sqrt': '√', r'\times': '×', r'\cdot': '·', r'\div': '÷', r'\leq': '≤',
        r'\geq': '≥', r'\neq': '≠', r'\approx': '≈', r'\equiv': '≡', r'\sum': '∑',
        r'\prod': '∏', r'\int': '∫', r'\partial': '∂', r'\degree': '°', r'\angle': '∠',
        r'\triangle': '△', r'\perp': '⊥', r'\parallel': '∥', r'\rightarrow': '→',
        r'\Rightarrow': '⇒', r'\leftarrow': '←', r'\Leftarrow': '⇐', r'\leftrightarrow': '↔',
        r'\circ': '∘', r'\bullet': '•', r'\cdots': '⋯', r'\vdots': '⋮', r'\ddots': '⋱',
        r'\bar': '̄', r'\hat': '̂', r'\dot': '̇', r'\ddot': '̈', r'\vec': '⃗',
    }

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

def build_katex_html(content_items):
    parts = []
    for item in content_items:
        if isinstance(item, tuple) and item[0] == 'text':
            parts.append(str(item[1]))
        elif isinstance(item, tuple) and item[0] == 'latex':
            text = str(item[1])
            text = convert_chemical_formula(text)
            parts.append(clean_latex(text))
        else:
            parts.append(str(item))
    return '\n\n'.join(parts)

def calculate_next_review(proficiency, review_count=0):
    intervals = [1, 3, 7, 14, 30, 60]
    return intervals[review_count] if review_count < len(intervals) else 60

def get_todays_cards():
    all_cards = load_jsonl(REVIEW_CARDS_FILE)
    today = datetime.now().strftime("%Y-%m-%d")
    return [c for c in all_cards if not c.get("next_review") or c["next_review"] <= today][::-1]

def add_review_card(card_data):
    cards = load_jsonl(REVIEW_CARDS_FILE)
    cards.append(card_data)
    save_jsonl(REVIEW_CARDS_FILE, cards)

def update_review_card(card_id, proficiency, correct):
    cards = load_jsonl(REVIEW_CARDS_FILE)
    for card in cards:
        if card.get("id") == card_id:
            card["proficiency"] = proficiency
            card["review_count"] = card.get("review_count", 0) + 1
            card["last_review"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            card["answered_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if correct:
                interval = calculate_next_review(proficiency, card["review_count"])
                card["next_review"] = (datetime.now() + timedelta(days=interval)).strftime("%Y-%m-%d")
            else:
                card["next_review"] = datetime.now().strftime("%Y-%m-%d")
            break
    save_jsonl(REVIEW_CARDS_FILE, cards)

@retry_request(max_retries=3, base_delay=2)
def generate_review_cards(subject="数学", count=3, difficulty="中等"):
    profile = load_user_profile()
    weak_know = sorted([(k, v) for k, v in profile.get("weak_knowledge", {}).items() if k.startswith(f"{subject}-")],
                       key=lambda x: x[1], reverse=True)[:3]
    weak_text = ', '.join([k.split('-')[-1] for k, _ in weak_know]) if weak_know else '无'

    difficulty_prompt = {
        "简单": "题目为基础题，注重概念理解，不需要复杂计算",
        "中等": "题目要有一定难度，包含计算和推理，相当于高考中等题",
        "困难": "题目要难，包含多步计算、图像分析、数据推导，相当于高考压轴题"
    }.get(difficulty, "中等")

    prompt = f"""你是高中{subject}老师。生成{count}道{subject}复习题。
薄弱知识点：{weak_text}
难度要求：{difficulty_prompt}
严格要求：
1. 选择题：题目必须包含具体数值或条件，字数不少于100字，选项要有3个以上干扰项。
2. 填空题：必须包含数据计算，答案不是简单的概念填空。
3. 简答题：必须包含至少两个计算步骤或推理过程，字数不少于200字。
4. 所有题目必须包含实际数据（如具体数字、函数表达式、反应条件等）。
5. 返回 JSON 数组，格式：[{{"type":"选择题/填空题/简答题","question":"题目","answer":"答案","knowledge_point":"知识点"}}]
6. 选择题必须在 question 中包含 A. B. C. D. 选项
7. 只返回 JSON 数组，不要其他文字"""

    api_key = load_ai_config().get("api_key_free", "").strip()
    if not api_key:
        print("[复习] ❌ 未配置API密钥")
        return None
    try:
        print(f"[复习] 开始请求，学科: {subject}, 数量: {count}, 难度: {difficulty}")
        resp = requests.post("https://open.bigmodel.cn/api/paas/v4/chat/completions",
                             headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                             json={"model": "glm-4-flash", "messages": [{"role": "user", "content": prompt}],
                                   "temperature": 0.7, "max_tokens": 4000}, timeout=120)
        if resp.status_code == 200:
            content = resp.json()["choices"][0]["message"]["content"]
            if DEBUG:
                print(f"[复习] ✅ API 返回成功，内容长度: {len(content)}")
                print(f"[复习] 原始内容:\n{content[:800]}...")
            cards = None
            try:
                cards = json.loads(content)
            except json.JSONDecodeError:
                match = re.search(r'\[\s*\{[\s\S]*\}\s*\]', content)
                if match:
                    try:
                        cards = json.loads(match.group())
                        print("[复习] ✅ 从内容中提取 JSON 数组成功")
                    except json.JSONDecodeError as je2:
                        print(f"[复习] ❌ 提取的 JSON 数组解析失败: {je2}")
                        fixed = match.group()
                        if fixed.endswith('"') or fixed.endswith('}'):
                            pass
                        elif fixed.endswith('...'):
                            fixed = fixed[:-3] + '"}'
                        try:
                            cards = json.loads(fixed)
                            print("[复习] ✅ 修复后解析成功")
                        except:
                            cards = None
                else:
                    print("[复习] ❌ 未找到 JSON 数组")
            if cards and isinstance(cards, list):
                for c in cards:
                    if "question" in c:
                        c["question"] = c["question"]
                    if "answer" in c:
                        c["answer"] = c["answer"]
                print(f"[复习] ✅ 成功生成 {len(cards)} 张卡片")
                return cards
            else:
                print("[复习] ❌ 返回内容非数组")
                return None
        else:
            print(f"[复习] ❌ API 错误: {resp.status_code}")
            print(f"[复习] 响应内容: {resp.text[:300]}")
            return None
    except requests.exceptions.Timeout:
        print("[复习] ❌ 请求超时（120秒）")
        return None
    except Exception as e:
        print(f"[复习] ❌ 异常: {e}")
        return None

@retry_request(max_retries=3, base_delay=2)
def generate_exam_paper(subject, count=5, difficulty="中等"):
    profile = load_user_profile()
    weak_kps = [k for k, v in profile.get("weak_knowledge", {}).items() if k.startswith(f"{subject}-")]
    weak_text = ', '.join([k.split('-')[-1] for k in weak_kps[:5]]) if weak_kps else '无'

    difficulty_prompt = {
        "简单": "基础题，注重概念",
        "中等": "有一定难度，含计算和推理",
        "困难": "压轴题难度，含多步计算和图像分析"
    }.get(difficulty, "中等")

    prompt = f"""你是高中{subject}老师。生成一份{subject}复习卷，共{count}道题，包含选择题、填空题、简答题。
薄弱知识点：{weak_text}
难度要求：{difficulty_prompt}
严格要求：
1. 每道题必须包含具体数据或条件，题目长度至少60字以上。
2. 简答题要有多步推理或计算过程，至少3个步骤。
3. 选择题选项要有区分度，包含干扰项。
4. 返回 JSON 数组：[{{"type":"选择题","question":"题目（含A.B.C.D.选项）","answer":"正确答案","knowledge_point":"知识点","difficulty":1-5}}]"""

    api_key = load_ai_config().get("api_key_free", "").strip()
    if not api_key:
        print("[复习卷] ❌ 未配置API密钥")
        return None
    try:
        print(f"[复习卷] 开始请求，学科: {subject}, 数量: {count}, 难度: {difficulty}")
        resp = requests.post("https://open.bigmodel.cn/api/paas/v4/chat/completions",
                             headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                             json={"model": "glm-4-flash", "messages": [{"role": "user", "content": prompt}],
                                   "temperature": 0.7, "max_tokens": 4000}, timeout=120)
        if resp.status_code == 200:
            content = resp.json()["choices"][0]["message"]["content"]
            if DEBUG:
                print(f"[复习卷] ✅ API 返回成功，内容长度: {len(content)}")
                print(f"[复习卷] 原始内容:\n{content[:800]}...")
            try:
                cards = json.loads(content)
            except:
                match = re.search(r'\[[\s\S]*\]', content)
                cards = json.loads(match.group()) if match else None
            if cards and isinstance(cards, list):
                print(f"[复习卷] ✅ 成功生成 {len(cards)} 道题")
                return cards
            else:
                print("[复习卷] ❌ 返回内容非数组")
                return None
        else:
            print(f"[复习卷] ❌ API 错误: {resp.status_code}")
            return None
    except requests.exceptions.Timeout:
        print("[复习卷] ❌ 请求超时（120秒）")
        return None
    except Exception as e:
        print(f"[复习卷] ❌ 异常: {e}")
        return None

def move_to_recycle(item):
    recycle = load_jsonl(RECYCLE_FILE)
    recycle.append({"original_type": item.get("type"), "data": item,
                    "delete_time": time.strftime("%Y-%m-%d %H:%M:%S"), "delete_ts": int(time.time())})
    save_jsonl(RECYCLE_FILE, recycle)

def delete_error_by_timestamp(timestamp):
    all_data, target, keep = load_jsonl(ERRORS_FILE), None, []
    for d in all_data:
        if d.get("timestamp") == timestamp:
            target = d
        else:
            keep.append(d)
    if target:
        move_to_recycle(target)
        save_jsonl(ERRORS_FILE, keep)
        return True
    return False

def delete_note_by_timestamp(timestamp):
    all_data, target, keep = load_jsonl(NOTES_FILE), None, []
    for d in all_data:
        if d.get("timestamp") == timestamp:
            target = d
        else:
            keep.append(d)
    if target:
        move_to_recycle(target)
        save_jsonl(NOTES_FILE, keep)
        return True
    return False

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
    new_name = str(int(time.time() * 1000)) + ext
    dst = os.path.join(target_dir, new_name)
    shutil.copy(src_path, dst)
    return dst

IMG_EXTS = [".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp"]
VIDEO_EXTS = [".mp4", ".mov", ".avi", ".mkv", ".flv", ".wmv"]
DOC_EXTS = [".pdf", ".doc", ".docx", ".txt", ".md", ".ppt", ".pptx", ".xls", ".xlsx"]

def load_ai_config():
    if not os.path.exists(AI_CONFIG_FILE):
        return {"model": "free", "api_key_free": "", "api_key_enhanced": "", "monthly_limit": 5.0, "subject_models": {}}
    try:
        with open(AI_CONFIG_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return {"model": "free", "api_key_free": "", "api_key_enhanced": "", "monthly_limit": 5.0, "subject_models": {}}
            return json.loads(content)
    except json.JSONDecodeError:
        return {"model": "free", "api_key_free": "", "api_key_enhanced": "", "monthly_limit": 5.0, "subject_models": {}}

def save_ai_config(config):
    with open(AI_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

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

def load_user_profile():
    if not os.path.exists(USER_PROFILE_FILE):
        default = {
            "name": "学生", "grade": "高三",
            "weak_subjects": {}, "weak_knowledge": {},
            "error_types": {}, "recent_focus": [],
            "total_errors": 0, "total_chats": 0,
            "chat_memory": {
                "last_update": "",
                "recent_topics": [],
                "weak_points": [],
                "discussed_errors": [],
                "last_question_summary": ""
            }
        }
        return default
    with open(USER_PROFILE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        if "chat_memory" not in data:
            data["chat_memory"] = {
                "last_update": "",
                "recent_topics": [],
                "weak_points": [],
                "discussed_errors": [],
                "last_question_summary": ""
            }
        return data

def save_user_profile(profile):
    with open(USER_PROFILE_FILE, "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)

@retry_request(max_retries=2, base_delay=1)
def update_chat_memory(subject, user_msg, ai_response):
    def do_update():
        api_key = load_ai_config().get("api_key_free", "").strip()
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
            resp = requests.post("https://open.bigmodel.cn/api/paas/v4/chat/completions",
                                 headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                                 json={"model": "glm-4-flash", "messages": [{"role": "user", "content": prompt}],
                                       "temperature": 0.3, "max_tokens": 300}, timeout=15)
            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"]
                try:
                    info = json.loads(content)
                except:
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
                    print("[记忆库] 已更新")
        except Exception as e:
            print(f"[记忆库] 更新失败: {e}")
    threading.Thread(target=do_update, daemon=True).start()

def get_memory_summary():
    profile = load_user_profile()
    memory = profile.get("chat_memory", {})
    parts = []
    if memory.get("recent_topics"):
        parts.append(f"近期讨论：{', '.join(memory['recent_topics'][:5])}")
    if memory.get("weak_points"):
        parts.append(f"薄弱点：{', '.join(memory['weak_points'][:5])}")
    if memory.get("last_question_summary"):
        parts.append(f"上次问题：{memory['last_question_summary']}")
    if parts:
        return "【记忆摘要】" + " | ".join(parts)
    return ""

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

@retry_request(max_retries=3, base_delay=2)
def generate_word_info(word):
    api_key = load_ai_config().get("api_key_free", "").strip()
    if not api_key:
        print(f"[生成] 未配置 API 密钥，无法生成 {word}")
        return None
    prompt = f"""请为英语单词 "{word}" 生成词条信息，格式为 JSON：
{{
    "word": "{word}",
    "phonetic": "音标（如 /əˈbændən/）",
    "meaning": "中文释义（如 放弃；抛弃）",
    "example": "一个例句",
    "forms": "变形（如 abandons, abandoning, abandoned）",
    "grammar": {{"collocations": ["搭配1", "搭配2"], "notes": ["注意点"], "test_points": ["考点"]}},
    "phrases": ["短语1", "短语2"]
}}
只返回 JSON 对象。"""
    try:
        resp = requests.post("https://open.bigmodel.cn/api/paas/v4/chat/completions",
                             headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                             json={"model": "glm-4-flash", "messages": [{"role": "user", "content": prompt}],
                                   "temperature": 0.3, "max_tokens": 600}, timeout=20)
        if resp.status_code == 200:
            content = resp.json()["choices"][0]["message"]["content"]
            try:
                new_data = json.loads(content)
            except:
                match = re.search(r'\{[^}]+\}', content)
                new_data = json.loads(match.group()) if match else None
            if new_data:
                new_data.setdefault("phonetic", "")
                new_data.setdefault("meaning", "")
                new_data.setdefault("example", "")
                new_data.setdefault("forms", "")
                new_data.setdefault("grammar", {})
                new_data.setdefault("phrases", [])
                print(f"[生成] ✅ 成功生成单词: {word}")
                return new_data
            else:
                print(f"[生成] ❌ 解析 JSON 失败: {content[:100]}")
        else:
            print(f"[生成] ❌ API 错误 {resp.status_code} 生成 {word}")
    except Exception as e:
        print(f"[生成] ❌ 异常生成 {word}: {e}")
    return None

def add_word_to_vocab(word_data):
    existing = load_jsonl(VOCAB_FILE)
    word = word_data.get("word", "")
    if not word:
        return False
    if any(w.get("word", "").lower() == word.lower() for w in existing):
        print(f"[添加] 单词 {word} 已存在，跳过")
        return False
    existing.append(word_data)
    save_jsonl(VOCAB_FILE, existing)
    print(f"[添加] ✅ 已添加单词: {word}")
    return True

def build_sentence_page(subject, page):
    CATEGORIES = ["全部", "开头", "转折", "结尾", "观点", "举例", "读后续写", "其他"]
    category_colors = {
        "开头": "#E3F2FD", "转折": "#FFF3E0", "结尾": "#E8F5E9",
        "观点": "#FCE4EC", "举例": "#F3E5F5", "读后续写": "#E0F7FA",
        "其他": "#F5F5F5"
    }

    search_input = ft.TextField(label="🔍 搜索句子", hint_text="输入关键词...", expand=True)
    category_dropdown = ft.Dropdown(
        label="分类",
        options=[ft.dropdown.Option(c) for c in CATEGORIES],
        value="全部",
        width=120,
    )
    favorite_filter_switch = ft.Switch(label="仅收藏", value=False)

    sentence_list = ft.ListView(spacing=8, expand=True)
    status_text = ft.Text("", size=14)

    def show_add_dialog(edit_data=None):
        is_edit = edit_data is not None
        cat_drop = ft.Dropdown(
            label="分类",
            options=[ft.dropdown.Option(c) for c in CATEGORIES if c != "全部"],
            value=edit_data.get("category", "观点") if is_edit else "观点",
            width=150,
        )
        sent_input = ft.TextField(
            label="英文句子",
            value=edit_data.get("sentence", "") if is_edit else "",
            multiline=True,
            min_lines=3,
            max_lines=5,
            expand=True,
        )
        trans_input = ft.TextField(
            label="中文翻译（可选）",
            value=edit_data.get("translation", "") if is_edit else "",
            multiline=True,
            min_lines=2,
            max_lines=3,
            expand=True,
        )

        def do_save(e):
            cat = cat_drop.value
            sent = sent_input.value.strip()
            trans = trans_input.value.strip()
            if not sent:
                page.snack_bar = ft.SnackBar(ft.Text("请输入句子内容"))
                page.snack_bar.open = True
                page.update()
                return
            if is_edit:
                update_sentence(edit_data["id"], cat, sent, trans)
            else:
                add_sentence(cat, sent, trans)
            page.close(dialog)
            refresh_list()
            page.snack_bar = ft.SnackBar(ft.Text("✅ 已保存" if not is_edit else "✅ 已更新"))
            page.snack_bar.open = True
            page.update()

        dialog = ft.AlertDialog(
            title=ft.Text("编辑金句" if is_edit else "添加金句"),
            content=ft.Column([
                cat_drop,
                sent_input,
                trans_input,
            ], spacing=10, width=400),
            actions=[
                ft.TextButton("取消", on_click=lambda e: page.close(dialog)),
                ft.ElevatedButton("保存", on_click=do_save),
            ]
        )
        page.open(dialog)

    def show_ai_generate_dialog():
        topic_input = ft.TextField(
            label="输入主题",
            hint_text="例如：环境保护、科技发展、个人成长...",
            multiline=True,
            min_lines=2,
            max_lines=3,
            expand=True,
        )
        count_row = ft.Row(spacing=10)
        count_drop = ft.Dropdown(
            label="快速选择",
            options=[ft.dropdown.Option(str(i)) for i in [3, 5, 8, 10]],
            value="5",
            width=120,
        )
        count_input = ft.TextField(
            label="自定义数量",
            hint_text="输入数字（如 6）",
            width=100,
            text_align=ft.TextAlign.CENTER,
        )
        count_row.controls.extend([count_drop, ft.Text("或", size=14), count_input])

        def do_generate(e):
            topic = topic_input.value.strip()
            if not topic:
                page.snack_bar = ft.SnackBar(ft.Text("请输入主题"))
                page.snack_bar.open = True
                page.update()
                return
            custom_val = count_input.value.strip()
            if custom_val and custom_val.isdigit():
                count = int(custom_val)
            else:
                count = int(count_drop.value)
            if count < 1:
                count = 3
            if count > 20:
                count = 20
            page.close(dialog)
            status_text.value = f"⏳ AI正在生成 {count} 个金句..."
            status_text.color = "blue"
            page.update()

            def generate_thread():
                api_key = load_ai_config().get("api_key_free", "").strip()
                if not api_key:
                    status_text.value = "❌ 未配置API密钥"
                    status_text.color = "red"
                    page.update()
                    return
                prompt = f"""你是一位英语写作专家。请为作文主题 "{topic}" 生成 {count} 个实用的万能金句（英语），适合高考英语作文使用。
每个句子要附带中文翻译。
输出格式为 JSON 数组：
[
  {{"sentence": "英文句子", "translation": "中文翻译", "category": "自动判断分类（开头/转折/结尾/观点/举例/读后续写）"}}
]
只返回 JSON 数组。"""
                try:
                    resp = requests.post("https://open.bigmodel.cn/api/paas/v4/chat/completions",
                                         headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                                         json={"model": "glm-4-flash", "messages": [{"role": "user", "content": prompt}],
                                               "temperature": 0.7, "max_tokens": 1500}, timeout=45)
                    if resp.status_code == 200:
                        content = resp.json()["choices"][0]["message"]["content"]
                        try:
                            items = json.loads(content)
                        except:
                            match = re.search(r'\[.*\]', content, re.DOTALL)
                            items = json.loads(match.group()) if match else None
                        if items:
                            added = 0
                            for item in items:
                                cat = item.get("category", "其他")
                                if cat not in CATEGORIES:
                                    cat = "其他"
                                add_sentence(cat, item.get("sentence", ""), item.get("translation", ""))
                                added += 1
                            refresh_list()
                            status_text.value = f"✅ 成功添加 {added} 个金句"
                            status_text.color = "green"
                        else:
                            status_text.value = "❌ AI返回格式异常"
                            status_text.color = "red"
                    else:
                        status_text.value = f"❌ API错误: {resp.status_code}"
                        status_text.color = "red"
                except Exception as ex:
                    status_text.value = f"❌ 生成失败: {str(ex)[:50]}"
                    status_text.color = "red"
                page.update()

            threading.Thread(target=generate_thread, daemon=True).start()

        dialog = ft.AlertDialog(
            title=ft.Text("🤖 AI生成金句"),
            content=ft.Column([
                topic_input,
                count_row,
            ], spacing=10, width=400),
            actions=[
                ft.TextButton("取消", on_click=lambda e: page.close(dialog)),
                ft.ElevatedButton("生成并添加", on_click=do_generate),
            ]
        )
        page.open(dialog)

    def render_sentence_list(filter_category="全部", keyword="", only_favorite=False):
        sentence_list.controls.clear()
        sentences = load_sentences()
        sentences.sort(key=lambda x: (not x.get("favorite", False), x.get("updated", x.get("created", ""))), reverse=True)

        filtered = []
        for s in sentences:
            if only_favorite and not s.get("favorite", False):
                continue
            if filter_category != "全部" and s.get("category") != filter_category:
                continue
            if keyword:
                kw = keyword.lower()
                if kw not in s.get("sentence", "").lower() and kw not in s.get("translation", "").lower():
                    continue
            filtered.append(s)

        if not filtered:
            sentence_list.controls.append(
                ft.Container(
                    content=ft.Text("  暂无金句，点击「添加」或「AI生成」来创建", size=14, color=ft.Colors.GREY_600),
                    padding=20,
                )
            )
            page.update()
            return

        for s in filtered:
            sid = s.get("id")
            cat = s.get("category", "其他")
            sentence = s.get("sentence", "")
            translation = s.get("translation", "")
            favorite = s.get("favorite", False)
            updated = s.get("updated", s.get("created", ""))
            bg_color = category_colors.get(cat, "#F5F5F5")

            fav_btn = ft.IconButton(
                icon=ft.Icons.STAR if favorite else ft.Icons.STAR_BORDER,
                icon_color=ft.Colors.AMBER if favorite else ft.Colors.GREY_400,
                icon_size=20,
                on_click=lambda e, sid=sid: (toggle_favorite(sid), refresh_list()),
                tooltip="收藏/取消收藏"
            )

            copy_btn = ft.IconButton(
                icon=ft.Icons.COPY,
                icon_size=18,
                on_click=lambda e, text=sentence: page.set_clipboard(text),
                tooltip="复制句子"
            )

            edit_btn = ft.IconButton(
                icon=ft.Icons.EDIT,
                icon_size=18,
                on_click=lambda e, data=s: show_add_dialog(data),
                tooltip="编辑"
            )

            del_btn = ft.IconButton(
                icon=ft.Icons.DELETE,
                icon_size=18,
                on_click=lambda e, sid=sid: (delete_sentence(sid), refresh_list()),
                tooltip="删除"
            )

            card = ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Container(
                            content=ft.Text(cat, size=11, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
                            bgcolor=ft.Colors.BLUE_600,
                            border_radius=10,
                            padding=ft.Padding(left=8, right=8, top=2, bottom=2),
                        ),
                        ft.Row([fav_btn, copy_btn, edit_btn, del_btn], spacing=2),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Text(sentence, size=15, selectable=True),
                    ft.Text(translation, size=13, color=ft.Colors.GREY_700, italic=True, selectable=True) if translation else ft.Text(""),
                    ft.Text(f"📅 {updated}", size=10, color=ft.Colors.GREY_500),
                ], spacing=4),
                padding=10,
                border_radius=12,
                bgcolor=bg_color,
                margin=ft.margin.only(bottom=4),
                border=ft.border.all(1, ft.Colors.AMBER_200 if favorite else ft.Colors.GREY_200),
            )
            sentence_list.controls.append(card)
        page.update()

    def refresh_list():
        render_sentence_list(
            category_dropdown.value,
            search_input.value.strip(),
            favorite_filter_switch.value
        )

    search_input.on_change = lambda e: refresh_list()
    category_dropdown.on_change = lambda e: refresh_list()
    favorite_filter_switch.on_change = lambda e: refresh_list()

    render_sentence_list()

    return ft.Column([
        ft.Row([
            ft.Text("💬 金句列表", size=20, weight=ft.FontWeight.BOLD),
            ft.Row([
                ft.ElevatedButton("➕ 添加", on_click=lambda e: show_add_dialog(), icon=ft.Icons.ADD),
                ft.ElevatedButton("🤖 AI生成", on_click=lambda e: show_ai_generate_dialog(), icon=ft.Icons.AUTO_AWESOME),
            ], spacing=8),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ft.Text("英语作文万能句子，可收藏、搜索、分类筛选", size=14, color=ft.Colors.GREY_600),
        ft.Row([
            search_input,
            category_dropdown,
            favorite_filter_switch,
        ], spacing=10),
        status_text,
        ft.Divider(height=1),
        ft.Container(content=sentence_list, expand=True),
    ], spacing=8, expand=True)

# ==================== main 函数 ====================
def main(page: ft.Page):
    page.add(ft.Text("Hello World - 如果看到这行，说明框架正常"))

if __name__ == "__main__":
    ft.app(target=main)
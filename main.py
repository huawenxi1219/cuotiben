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

# ==================== 路径配置（将在 main 中初始化） ====================
DATA_DIR = None
IMAGES_DIR = None
VIDEOS_DIR = None
DOCS_DIR = None
ERRORS_FILE = None
NOTES_FILE = None
RECYCLE_FILE = None
REVIEW_CARDS_FILE = None
TASKS_FILE = None
AI_CONFIG_FILE = None
USER_PROFILE_FILE = None
CUSTOM_SKILL_FILE = None
CHAT_HISTORY_DIR = None
CONTENT_LIB_DIR = None
NEW_WORDS_FILE = None
VOCAB_FILE = None
SENTENCES_FILE = None

_jsonl_lock = threading.Lock()
TARGET_VOCAB_COUNT = 3500

# ==================== 调试开关 ====================
DEBUG = True

# ==================== 诊断工具 ====================
def diagnose_data_files():
    """检查所有数据文件，返回诊断报告"""
    report = {}
    files_to_check = {
        "错题本": ERRORS_FILE,
        "笔记本": NOTES_FILE,
        "复习卡片": REVIEW_CARDS_FILE,
        "任务清单": TASKS_FILE,
        "AI配置": AI_CONFIG_FILE,
        "用户画像": USER_PROFILE_FILE,
        "单词本": VOCAB_FILE,
        "金句库": SENTENCES_FILE,
        "回收站": RECYCLE_FILE,
    }
    for name, path in files_to_check.items():
        status = "不存在"
        size = 0
        lines_ok = 0
        lines_err = 0
        if os.path.exists(path):
            size = os.path.getsize(path)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for i, line in enumerate(f, 1):
                        if line.strip():
                            try:
                                json.loads(line)
                                lines_ok += 1
                            except:
                                lines_err += 1
                if lines_err == 0:
                    status = "正常"
                else:
                    status = f"有 {lines_err} 行格式错误（已跳过）"
            except Exception as e:
                status = f"读取失败: {e}"
        report[name] = {"状态": status, "大小": size, "行数": lines_ok + lines_err, "错误行": lines_err}
    return report

def repair_jsonl_file(filepath):
    """尝试修复 JSONL 文件：备份并过滤掉格式错误的行"""
    if not os.path.exists(filepath):
        return False
    backup = filepath + ".bak"
    shutil.copy2(filepath, backup)
    new_lines = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    json.loads(line)
                    new_lines.append(line)
                except:
                    continue
    with open(filepath, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    return True

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
                            pass  # 跳过损坏的行
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
    # 存储相对路径（相对于 DATA_DIR）
    def to_rel(paths):
        rels = []
        for p in paths:
            if p.startswith(DATA_DIR):
                rels.append(os.path.relpath(p, DATA_DIR))
            else:
                rels.append(p)
        return rels
    original_media_rel = to_rel(original_media)
    answer_media_rel = to_rel(answer_media)
    idea_media_rel = to_rel(idea_media)
    entry = {
        "type": "error", "subject": subject, "original": original,
        "original_media": original_media_rel,
        "answer": answer, "answer_media": answer_media_rel,
        "mistake": mistake, "idea": idea,
        "idea_media": idea_media_rel,
        "question": original, "question_media": original_media_rel,
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
    # 返回相对路径
    return os.path.relpath(dst, DATA_DIR)

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
  "summary": "本次对话核心内容摘要（一句话）
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
    global DATA_DIR, IMAGES_DIR, VIDEOS_DIR, DOCS_DIR, ERRORS_FILE, NOTES_FILE, RECYCLE_FILE, REVIEW_CARDS_FILE, TASKS_FILE, AI_CONFIG_FILE, USER_PROFILE_FILE, CUSTOM_SKILL_FILE, CHAT_HISTORY_DIR, CONTENT_LIB_DIR, NEW_WORDS_FILE, VOCAB_FILE, SENTENCES_FILE

    try:
        # ========== 1. 数据目录（使用当前工作目录，Android 上为应用私有目录） ==========
        DATA_DIR = os.getcwd()

        # ========== 2. 子目录和文件路径 ==========
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

        # ========== 3. 创建目录和空文件 ==========
        for d in [IMAGES_DIR, VIDEOS_DIR, DOCS_DIR, CHAT_HISTORY_DIR, CONTENT_LIB_DIR]:
            os.makedirs(d, exist_ok=True)
        required_files = [
            ERRORS_FILE, NOTES_FILE, RECYCLE_FILE, REVIEW_CARDS_FILE,
            TASKS_FILE, AI_CONFIG_FILE, USER_PROFILE_FILE,
            NEW_WORDS_FILE, VOCAB_FILE, SENTENCES_FILE
        ]
        for filepath in required_files:
            if not os.path.exists(filepath):
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write("")

        init_vocabulary()
        init_content_lib()

        # ========== 4. 从 assets 复制初始数据（仅当目标文件不存在） ==========
        import sys
        assets_path = None
        possible_paths = [
            os.path.join(os.getcwd(), "assets"),
            os.path.join(sys._MEIPASS, "assets") if hasattr(sys, '_MEIPASS') else None,
            os.path.join(os.path.dirname(sys.argv[0]), "assets") if hasattr(sys, 'argv') else None,
        ]
        for p in possible_paths:
            if p and os.path.isdir(p):
                assets_path = p
                break
        
        if assets_path:
            print(f"[初始化] 找到 assets 目录: {assets_path}")
            needed_files = ["vocabulary.jsonl", "ai_config.json", "sentences.jsonl"]
            for filename in needed_files:
                src = os.path.join(assets_path, filename)
                dst = os.path.join(DATA_DIR, filename)
                if os.path.exists(src) and not os.path.exists(dst):
                    try:
                        shutil.copy2(src, dst)
                        print(f"[初始化] ✅ 复制 {filename} 成功 -> {dst}")
                    except Exception as e:
                        print(f"[初始化] ⚠️ 复制 {filename} 失败: {e}")
        else:
            print("[初始化] ⚠️ 未找到 assets 目录，跳过复制")

        # ========== 5. 窗口设置 ==========
        is_mobile = page.platform in [ft.PagePlatform.ANDROID, ft.PagePlatform.IOS]
        if not is_mobile:
            page.window.width = 900
            page.window.height = 700
            page.window.min_width = 360
            page.window.min_height = 450
        else:
            page.window.width = None
            page.window.min_width = 320
            page.padding = 10
            page.spacing = 8
        page.title = "智能错题笔记助手"
        page.responsive = True
        page.theme_mode = ft.ThemeMode.LIGHT

        # ========== 6. 主题 ==========
        page.theme = ft.Theme(
            font_family="Segoe UI, -apple-system, Roboto, sans-serif",
            color_scheme=ft.ColorScheme(
                primary=ft.Colors.BLUE_600,
                primary_container=ft.Colors.BLUE_50,
                secondary=ft.Colors.BLUE_400,
                surface=ft.Colors.WHITE,
                surface_variant=ft.Colors.GREY_50,
            ),
            visual_density=ft.VisualDensity.STANDARD,
            page_transitions=ft.PageTransitionsTheme(
                android=ft.PageTransitionTheme.ZOOM,
                ios=ft.PageTransitionTheme.CUPERTINO,
                macos=ft.PageTransitionTheme.CUPERTINO,
                linux=ft.PageTransitionTheme.ZOOM,
                windows=ft.PageTransitionTheme.ZOOM,
            ),
        )
        page.theme.text_theme = ft.TextTheme(
            display_large=ft.TextStyle(size=28, weight=ft.FontWeight.BOLD, color=ft.Colors.BLACK87),
            display_medium=ft.TextStyle(size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.BLACK87),
            display_small=ft.TextStyle(size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.BLACK87),
            headline_medium=ft.TextStyle(size=18, weight=ft.FontWeight.W_600, color=ft.Colors.BLACK87),
            headline_small=ft.TextStyle(size=16, weight=ft.FontWeight.W_600, color=ft.Colors.BLACK87),
            body_large=ft.TextStyle(size=16, weight=ft.FontWeight.NORMAL, color=ft.Colors.BLACK87),
            body_medium=ft.TextStyle(size=14, weight=ft.FontWeight.NORMAL, color=ft.Colors.BLACK87),
            body_small=ft.TextStyle(size=12, weight=ft.FontWeight.NORMAL, color=ft.Colors.GREY_600),
            label_large=ft.TextStyle(size=14, weight=ft.FontWeight.W_500, color=ft.Colors.BLUE_600),
        )
        page.dark_theme = ft.Theme(
            font_family="Segoe UI, -apple-system, Roboto, sans-serif",
            color_scheme=ft.ColorScheme(
                primary=ft.Colors.BLUE_400,
                primary_container=ft.Colors.BLUE_900,
                secondary=ft.Colors.BLUE_300,
                surface=ft.Colors.GREY_900,
                surface_variant=ft.Colors.GREY_800,
            ),
            visual_density=ft.VisualDensity.STANDARD,
        )
        page.dark_theme.text_theme = ft.TextTheme(
            display_large=ft.TextStyle(size=28, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
            display_medium=ft.TextStyle(size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
            display_small=ft.TextStyle(size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
            headline_medium=ft.TextStyle(size=18, weight=ft.FontWeight.W_600, color=ft.Colors.WHITE),
            headline_small=ft.TextStyle(size=16, weight=ft.FontWeight.W_600, color=ft.Colors.WHITE),
            body_large=ft.TextStyle(size=16, weight=ft.FontWeight.NORMAL, color=ft.Colors.WHITE),
            body_medium=ft.TextStyle(size=14, weight=ft.FontWeight.NORMAL, color=ft.Colors.WHITE),
            body_small=ft.TextStyle(size=12, weight=ft.FontWeight.NORMAL, color=ft.Colors.GREY_400),
            label_large=ft.TextStyle(size=14, weight=ft.FontWeight.W_500, color=ft.Colors.BLUE_400),
        )

        # ========== 7. 全局变量和函数 ==========
        main_subject_page = None
        subject_page_content = ft.Container(expand=True)

        def show_toast(text, color="green"):
            toast = ft.Container(
                content=ft.Text(text, size=18, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
                bgcolor=ft.Colors.GREEN_600 if color == "green" else ft.Colors.RED_600,
                border_radius=20,
                padding=ft.Padding(left=30, right=30, top=15, bottom=15),
                shadow=ft.BoxShadow(blur_radius=20, color=ft.Colors.BLACK26),
                opacity=0,
                animate_opacity=ft.Animation(300, ft.AnimationCurve.EASE_IN_OUT),
            )
            page.overlay.append(toast)
            toast.left = (page.window.width - 200) / 2 if not is_mobile else (page.width - 200) / 2
            toast.top = (page.window.height - 80) / 2 if not is_mobile else (page.height - 80) / 2
            toast.opacity = 1
            page.update()

            def fade_out():
                time.sleep(1.5)
                toast.opacity = 0
                page.update()
                time.sleep(0.4)
                page.overlay.remove(toast)
                page.update()

            threading.Thread(target=fade_out, daemon=True).start()

        def show_message(target_text, text, color="green"):
            target_text.value = text
            target_text.color = color
            page.update()
            threading.Thread(target=lambda: (time.sleep(2), setattr(target_text, 'value', ''), page.update()), daemon=True).start()

        # ---------- 首页 ----------
        home_msg = ft.Text("", size=16)
        subj_dd = ft.Dropdown(
            label="科目",
            options=[ft.dropdown.Option(s) for s in ["数学", "语文", "英语", "物理", "化学", "生物", "历史", "政治", "地理"]],
            value="数学",
            width=150,
        )
        original_input = ft.TextField(label="原题（题干）", multiline=True, min_lines=3)
        mistake_input = ft.TextField(label="错因", multiline=True, min_lines=2)
        answer_input = ft.TextField(label="标准答案", multiline=True, min_lines=2)
        idea_input = ft.TextField(label="我的理解", multiline=True, min_lines=2)
        tags_input = ft.TextField(label="手动标签（逗号分隔）", multiline=False)

        progress_status = ft.Text("", size=14)
        progress_bar = ft.ProgressBar(width=200, height=8, value=0, visible=False)
        progress_row = ft.Row([progress_bar, progress_status], spacing=10, visible=False)

        # ---------- 自定义图片选择器 ----------
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
                for idx, f_path in enumerate(selected_files):
                    name = os.path.basename(f_path)
                    icon_text = "🖼️" if os.path.splitext(f_path)[1].lower() in IMG_EXTS else "📄"
                    row = ft.Row([
                        ft.Text(f"{icon_text} {name}", size=14, expand=True),
                        ft.IconButton(icon=ft.Icons.CLOSE, icon_size=16, on_click=lambda e, i=idx: remove_file(i)),
                    ], spacing=4)
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
                    page.snack_bar = ft.SnackBar(ft.Text(f"已添加 {len(e.files)} 个文件"))
                    page.snack_bar.open = True
                    page.update()

            def remove_file(idx):
                if 0 <= idx < len(selected_files):
                    selected_files.pop(idx)
                    refresh_file_list()

            def pick_files(e):
                exts = {
                    'image': ['jpg', 'jpeg', 'png'],
                    'video': ['mp4', 'mov', 'avi'],
                    'document': ['pdf', 'doc', 'docx', 'txt'],
                    'all': ['jpg', 'jpeg', 'png', 'mp4', 'pdf', 'doc', 'docx', 'txt']
                }
                picker.pick_files(file_type=ft.FilePickerFileType.CUSTOM,
                                  allowed_extensions=exts.get(allowed_types, exts['all']),
                                  allow_multiple=True)

            complete_btn = ft.ElevatedButton(
                "✅ 完成上传",
                icon=ft.Icons.DONE,
                on_click=lambda e: on_complete(selected_files) if on_complete else None,
                disabled=True,
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

        def on_picker_complete(selected_files):
            if selected_files:
                analyze_images(selected_files)

        picker_col1, original_files, reset_picker1 = make_file_picker_button(
            "📷 题目图片（可多选）", "image",
            on_complete=on_picker_complete
        )
        picker_col2, answer_files, reset_picker2 = make_file_picker_button(
            "📷 答案图片", "image",
            on_complete=None
        )
        picker_col3, idea_files, reset_picker3 = make_file_picker_button(
            "📷 笔记图片", "image",
            on_complete=None
        )

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
                    full_path = path if os.path.isabs(path) else os.path.join(DATA_DIR, path)
                    result = analyze_single_image(full_path)
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
            api_key = load_ai_config().get("api_key_free", "").strip()
            if not api_key:
                return None
            try:
                with open(image_path, "rb") as f:
                    img_b64 = base64.b64encode(f.read()).decode("utf-8")
            except:
                return None
            prompt = """请分析这张图片中的题目内容，并返回以下 JSON 格式：
{
  "knowledge_point": "该题涉及的知识点（如：三角函数、力学、语法等）",
  "error_type": "学生可能的错因（如：公式记错、审题不清、计算错误）",
  "difficulty": 1-5 的整数（1最简单，5最难）
}
只返回 JSON，不要其他文字。"""
            messages = [
                {"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
                ]}
            ]
            try:
                resp = requests.post(
                    "https://open.bigmodel.cn/api/paas/v4/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={"model": "glm-4v-flash", "messages": messages, "max_tokens": 300},
                    timeout=30
                )
                if resp.status_code == 200:
                    content = resp.json()["choices"][0]["message"]["content"]
                    try:
                        result = json.loads(content)
                        return result
                    except:
                        match = re.search(r'\{[^{}]*\}', content)
                        if match:
                            try:
                                result = json.loads(match.group())
                                return result
                            except:
                                pass
                return None
            except:
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
            refresh_review_view()

        home_page = ft.Column([
            ft.Text("📸 拍照录题", size=24),
            ft.Row([subj_dd], spacing=15) if not is_mobile else ft.Column([subj_dd]),
            original_input,
            picker_col1,
            progress_row,
            mistake_input,
            answer_input,
            picker_col2,
            idea_input,
            picker_col3,
            tags_input,
            ft.ElevatedButton("💾 保存错题", on_click=submit_error),
            home_msg,
        ], spacing=15, scroll=ft.ScrollMode.AUTO)

        # ==================== AI聊天 ====================
        AI_SUBJECTS = [("总AI", "🤖"), ("数学", "📐"), ("语文", "📜"), ("英语", "📝"),
                       ("物理", "⚛️"), ("化学", "🧪"), ("生物", "🧬"),
                       ("历史", "🏛️"), ("政治", "⚖️"), ("地理", "🌍")]

        contact_panel = ft.Container(visible=False, bgcolor="#E0E0E0", border_radius=16, padding=15, width=220)

        def close_contact_panel(e=None):
            contact_panel.visible = False
            page.update()

        def open_contact_panel(e):
            contact_panel.right = 10
            contact_panel.bottom = 76
            contact_panel.visible = True
            page.update()

        contact_list = ft.Column(spacing=8)
        for subj_name, subj_icon in AI_SUBJECTS:
            btn = ft.TextButton(text=f"{subj_icon} {subj_name}", on_click=lambda e, s=subj_name: open_chat(s))
            contact_list.controls.append(btn)
        contact_panel.content = ft.Column([ft.Text("🧠 AI 助手", size=18), ft.Divider(), contact_list], spacing=5)

        ai_ball = ft.Container(content=ft.Text("AI", size=20, color="white"), width=56, height=56,
                               border_radius=28, bgcolor="#1976D2", alignment=ft.alignment.center,
                               on_click=lambda e: (close_contact_panel() if contact_panel.visible else open_contact_panel(e)))
        ball_container = ft.Container(content=ai_ball, right=10, bottom=10)

        chat_dialog = ft.Container(visible=False, left=20, top=20, right=20, bottom=20,
                                   bgcolor="white", border_radius=16, padding=20)
        current_chat_subject = "总AI"
        stop_flag = False
        generation_active = False

        def open_chat(subject, initial_message=None):
            try:
                nonlocal current_chat_subject, stop_flag, generation_active
                if generation_active:
                    stop_flag = True
                    time.sleep(0.2)
                generation_active = False
                stop_flag = False
                current_chat_subject = subject
                close_contact_panel()
                chat_dialog.content = build_chat_window(subject, initial_message)
                chat_dialog.visible = True
                page.update()
            except Exception as e:
                error_dlg = ft.AlertDialog(
                    title=ft.Text("❌ AI 对话加载失败"),
                    content=ft.Text(f"错误信息：{str(e)}\n\n堆栈：{traceback.format_exc()}", size=14, selectable=True),
                    actions=[ft.TextButton("关闭", on_click=lambda ev: page.close(error_dlg))]
                )
                page.open(error_dlg)
                page.update()
                raise

        def call_ai_stream(messages, model_name, on_chunk):
            api_key = load_ai_config().get("api_key_free", "").strip()
            if not api_key:
                on_chunk("❌ 未配置API密钥")
                return
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {"model": "glm-4-flash", "messages": messages, "temperature": 0.7, "max_tokens": 2048, "stream": True}
            try:
                resp = requests.post("https://open.bigmodel.cn/api/paas/v4/chat/completions",
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
                        except:
                            continue
                return accumulated
            except Exception as e:
                on_chunk(f"❌ 异常: {str(e)}")
                return None

        def build_chat_window(subject, initial_message=None):
            try:
                display_name = subject if subject != "总AI" else "总AI"
                history = load_chat_history(subject)
                context_messages = []
                for msg in history[-20:]:
                    context_messages.append({"role": msg["role"], "content": msg["content"]})

                memory_summary = get_memory_summary()
                profile_summary = get_profile_summary()

                system_prompt = f"""你是{display_name}老师，请用结构化方式回答。
- 对于知识类问题，请分点列出要点。
- 对于解题类问题，请先给出思路，再给出步骤。
- 对于作文类问题，请提供框架和例句。
- 回答要简洁、准确、有条理。"""
                custom_skill = load_custom_skill()
                if custom_skill:
                    system_prompt += f"\n\n额外的教学指导：{custom_skill}"
                if memory_summary:
                    system_prompt += f"\n\n{memory_summary}"
                if profile_summary:
                    system_prompt += f"\n\n{profile_summary}"
                if context_messages:
                    system_prompt += "\n\n以下是最近的对话历史（仅作上下文参考，不要重复历史内容）：\n"
                    for msg in context_messages[-15:]:
                        role_label = "学生" if msg["role"] == "user" else "老师"
                        system_prompt += f"[{role_label}]: {msg['content'][:200]}\n"

                all_messages = [{"role": "system", "content": system_prompt}]
                for msg in context_messages[-15:]:
                    all_messages.append(msg)

                chat_history_display = ft.ListView(spacing=12, expand=True)
                chat_input = ft.TextField(label=f"向{display_name}老师提问...", multiline=True, min_lines=2, max_lines=5)
                send_btn = ft.ElevatedButton("发送", icon=ft.Icons.SEND)
                stop_btn = ft.TextButton("停止生成", visible=False)
                chat_status = ft.Text("", size=14)

                for msg in history:
                    is_user = msg["role"] == "user"
                    chat_history_display.controls.append(
                        ft.Container(
                            content=ft.Column([
                                ft.Text("你" if is_user else display_name, size=12, weight=ft.FontWeight.BOLD,
                                        color=ft.Colors.BLUE if is_user else ft.Colors.GREEN),
                                ft.Text(msg["content"], size=14),
                            ], spacing=4),
                            padding=10, border_radius=12, bgcolor="#E3F2FD" if is_user else "#E8F5E9",
                        )
                    )

                if initial_message:
                    chat_input.value = initial_message

                def handle_send(msg_text=None):
                    try:
                        nonlocal generation_active, stop_flag
                        content = msg_text if msg_text else chat_input.value.strip()
                        if not content:
                            return
                        if not msg_text:
                            chat_input.value = ""

                        chat_history_display.controls.append(
                            ft.Container(
                                content=ft.Column([
                                    ft.Text("你", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE),
                                    ft.Text(content, size=14),
                                ], spacing=4),
                                padding=10, border_radius=12, bgcolor="#E3F2FD",
                            )
                        )
                        send_btn.visible = False
                        stop_btn.visible = True
                        chat_status.value = "⏳ 生成中..."
                        page.update()

                        save_chat_message(subject, "user", content)

                        current_messages = list(all_messages)
                        current_messages.append({"role": "user", "content": content})

                        ai_response = ""

                        def on_chunk(text):
                            nonlocal ai_response
                            ai_response = text

                        def ai_thread():
                            nonlocal generation_active, stop_flag, ai_response
                            generation_active = True
                            stop_flag = False
                            try:
                                call_ai_stream(current_messages, "glm-4-flash", on_chunk)
                            finally:
                                generation_active = False

                            if len(chat_history_display.controls) > 0:
                                last_child = chat_history_display.controls[-1]
                                if hasattr(last_child, 'bgcolor') and last_child.bgcolor == "#E8F5E9":
                                    chat_history_display.controls.pop()

                            chat_history_display.controls.append(
                                ft.Container(
                                    content=ft.Column([
                                        ft.Text(display_name, size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN),
                                        ft.Text(ai_response if ai_response else "（无回应）", size=14),
                                    ], spacing=4),
                                    padding=10, border_radius=12, bgcolor="#E8F5E9",
                                )
                            )
                            send_btn.visible = True
                            stop_btn.visible = False
                            chat_status.value = ""
                            if ai_response:
                                save_chat_message(subject, "assistant", ai_response)
                                update_chat_memory(subject, content, ai_response)
                            update_chat_stats(subject)
                            page.update()

                        threading.Thread(target=ai_thread, daemon=True).start()
                    except Exception as e:
                        chat_status.value = f"❌ 发送失败：{str(e)}"
                        page.update()

                send_btn.on_click = lambda e: handle_send()
                stop_btn.on_click = lambda e: setattr(sys.modules[__name__], 'stop_flag', True)

                def clear_history(e):
                    fp = get_chat_history_file(subject)
                    save_jsonl(fp, [])
                    chat_history_display.controls.clear()
                    page.update()
                    page.snack_bar = ft.SnackBar(ft.Text("✅ 对话历史已清除"))
                    page.snack_bar.open = True
                    page.update()

                return ft.Column([
                    ft.Row([
                        ft.Text(f"💬 {display_name} 对话", size=20, weight=ft.FontWeight.BOLD),
                        ft.TextButton("🗑️ 清除历史", on_click=clear_history),
                        ft.IconButton(icon=ft.Icons.CLOSE,
                                      on_click=lambda e: (setattr(chat_dialog, 'visible', False), page.update())),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Divider(),
                    ft.Container(content=chat_history_display, expand=True),
                    ft.Row([chat_input, send_btn, stop_btn], spacing=10),
                    chat_status,
                ], spacing=10, expand=True)
            except Exception as e:
                return ft.Column([
                    ft.Text("❌ 对话窗口加载失败", size=20, color="red"),
                    ft.Text(f"错误信息：{str(e)}", size=16, selectable=True),
                    ft.Text(f"堆栈：\n{traceback.format_exc()}", size=12, selectable=True),
                ])

        # ==================== 智能复习 ====================
        review_subject_dropdown = ft.Dropdown(
            label="选择科目",
            options=[ft.dropdown.Option(sub) for sub in
                     ["数学", "语文", "英语", "物理", "化学", "生物", "历史", "政治", "地理"]],
            value="数学",
            on_change=lambda e: refresh_review_view()
        )
        review_card_list = ft.ListView(spacing=10, expand=True)
        review_status = ft.Text("", size=16)

        difficulty_dropdown = ft.Dropdown(
            label="难度",
            options=[ft.dropdown.Option("简单"), ft.dropdown.Option("中等"), ft.dropdown.Option("困难")],
            value="中等",
            width=100,
        )

        @retry_request(max_retries=3, base_delay=2)
        def generate_today_plan(result_text=None):
            target = result_text
            if target is None:
                return
            target.value = "⏳ AI 正在分析你的学习数据..."
            target.color = "blue"
            page.update()

            def do_generate():
                profile = load_user_profile()
                errors = load_jsonl(ERRORS_FILE)
                try:
                    days_left = (datetime(2026, 6, 7) - datetime.now()).days
                except:
                    days_left = 365
                subject_errors = {}
                for err in errors:
                    subject_errors[err.get("subject", "未知")] = subject_errors.get(err.get("subject", "未知"), 0) + 1
                weak_know = sorted(profile.get("weak_knowledge", {}).items(), key=lambda x: x[1], reverse=True)[:5]
                prompt = f"""你是高三学习规划师。距离高考{days_left}天。请生成今日学习计划（纯文本）：
各科错题数：{json.dumps(subject_errors, ensure_ascii=False)}
薄弱知识点：{json.dumps(weak_know, ensure_ascii=False)}
格式：1.总体建议 2.3-5个具体任务（科目+内容+耗时） 3.鼓励语"""
                api_key = load_ai_config().get("api_key_free", "").strip()
                if not api_key:
                    target.value = "❌ 未配置 API 密钥"
                    target.color = "red"
                    page.update()
                    return
                try:
                    resp = requests.post("https://open.bigmodel.cn/api/paas/v4/chat/completions",
                                         headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                                         json={"model": "glm-4-flash", "messages": [{"role": "user", "content": prompt}],
                                               "temperature": 0.7, "max_tokens": 800}, timeout=30)
                    if resp.status_code == 200:
                        target.value = resp.json()["choices"][0]["message"]["content"]
                        target.color = "black"
                    else:
                        target.value = f"❌ API错误：{resp.status_code}"
                        target.color = "red"
                except Exception as ex:
                    target.value = f"❌ 请求失败：{str(ex)}"
                    target.color = "red"
                page.update()

            threading.Thread(target=do_generate, daemon=True).start()

        def ai_judge_answer(user_answer, correct_answer, question_text="", question_type="简答"):
            user_answer = user_answer.strip()
            correct_answer = correct_answer.strip()
            if not user_answer or not correct_answer:
                return False, "答案不完整", []

            if user_answer.upper() == correct_answer.upper():
                return True, "答案完全匹配", []

            if question_type == "选择":
                ua_letter = user_answer.upper()[:1]
                ca_letter = correct_answer.upper()[:1]
                if ua_letter == ca_letter:
                    return True, "选项匹配正确", []
                if ua_letter in ca_letter or ca_letter in ua_letter:
                    return True, "选项匹配正确", []
                return False, f"正确答案是 {ca_letter}", []

            if question_type == "填空":
                sep_candidates = ['；', ';', '、', '，', ',', '\n']
                sep = None
                for s in sep_candidates:
                    if s in correct_answer and s in user_answer:
                        sep = s
                        break
                if sep:
                    correct_parts = [p.strip() for p in correct_answer.split(sep) if p.strip()]
                    user_parts = [p.strip() for p in user_answer.split(sep) if p.strip()]
                    blanks = []
                    overall = True
                    for i in range(len(correct_parts)):
                        if i < len(user_parts):
                            ua = user_parts[i]
                        else:
                            ua = ""
                        ca = correct_parts[i]
                        is_correct = ua.upper() == ca.upper()
                        if not is_correct:
                            try:
                                u_num = float(ua)
                                c_num = float(ca)
                                if abs(u_num - c_num) < 1e-6:
                                    is_correct = True
                            except:
                                pass
                        blanks.append({"index": i+1, "user_answer": ua, "correct_answer": ca, "is_correct": is_correct})
                        if not is_correct:
                            overall = False
                    explanation = "、".join([f"空{i+1}: {'✅' if b['is_correct'] else '❌'}" for i, b in enumerate(blanks)])
                    return overall, explanation, blanks

            api_key = load_ai_config().get("api_key_free", "").strip()
            if not api_key:
                ua_nums = re.findall(r'\d+\.?\d*', user_answer)
                ca_nums = re.findall(r'\d+\.?\d*', correct_answer)
                if ua_nums and ca_nums and ua_nums == ca_nums:
                    return True, "数值等价判定正确", []
                if correct_answer in user_answer or user_answer in correct_answer:
                    return True, "答案包含匹配正确", []
                return False, "未通过自动判定", []

            prompt = f"""你是一位严谨的高中老师。请判断学生的答案是否正确，并给出解释。
【强制规则】：
1. 如果题目有多个空（请根据题目中的“____”、“（ ）”或序号判断），请分别给出每个空的正误。
2. 若无多空，则返回整体判定。
3. 输出必须为JSON，格式：
   - 单空：{{"correct": true/false, "explanation": "解释"}}
   - 多空：{{"blanks": [{{"index":1, "user_answer":"...", "correct_answer":"...", "is_correct":true/false}}], "overall": true/false, "explanation": "简要说明"}}
题型：{question_type}
题目：{question_text[:300]}
标准答案：{correct_answer}
学生答案：{user_answer}
只返回JSON对象，不要多余文字。"""

            try:
                resp = requests.post(
                    "https://open.bigmodel.cn/api/paas/v4/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={"model": "glm-4-flash", "messages": [{"role": "user", "content": prompt}],
                          "temperature": 0.0, "max_tokens": 500},
                    timeout=20
                )
                if resp.status_code == 200:
                    data = resp.json()["choices"][0]["message"]["content"]
                    try:
                        result = json.loads(data)
                    except:
                        match = re.search(r'\{[^}]+\}', data)
                        result = json.loads(match.group()) if match else {}
                    if "blanks" in result:
                        blanks = result["blanks"]
                        overall = result.get("overall", all(b["is_correct"] for b in blanks))
                        explanation = result.get("explanation", "")
                        return overall, explanation, blanks
                    else:
                        correct = result.get("correct", False)
                        explanation = result.get("explanation", "")
                        return correct, explanation, []
            except:
                pass
            return False, "AI判定失败", []

        def refresh_review_view():
            try:
                review_card_list.controls.clear()
                all_cards = load_jsonl(REVIEW_CARDS_FILE)
                current_subject = review_subject_dropdown.value
                subject_cards = [c for c in all_cards if c.get("subject") == current_subject]
                subject_cards.sort(key=lambda x: x.get("created", ""), reverse=True)
                if not subject_cards:
                    review_card_list.controls.append(ft.Container(content=ft.Text("  暂无复习卡片", size=16), padding=10))
                else:
                    for card in subject_cards:
                        q_text = clean_latex(card.get("question", "无题目"))
                        a_text = card.get("answer", "")
                        kp = card.get("knowledge_point", "")
                        ctype = card.get("type", "简答")
                        created_time = card.get("created", "")
                        answered_time = card.get("answered_time", "")
                        is_answered = bool(answered_time)
                        is_correct = card.get("proficiency", 0) >= 70

                        is_choice = ctype == "选择"
                        if ctype == "选择":
                            border_color = "#90CAF9"
                            bg_color = "#E3F2FD"
                            type_label = "🔤 选择题"
                        elif ctype == "填空":
                            border_color = "#A5D6A7"
                            bg_color = "#E8F5E9"
                            type_label = "✏️ 填空题"
                        elif ctype in ("综合", "综合大题"):
                            border_color = "#CE93D8"
                            bg_color = "#F3E5F5"
                            type_label = "📝 综合题"
                        else:
                            border_color = "#FFCC80"
                            bg_color = "#FFF3E0"
                            type_label = "💬 简答题"

                        card_state = {"submitted": False, "selected": "", "answer_text": a_text, "kp": kp, "options": [],
                                      "choice_buttons": [],
                                      "result_text": None, "knowledge_tip": None, "answer_btn": None, "submit_btn": None,
                                      "answer_input": None, "choice_column": None, "question_text": q_text,
                                      "question_type": ctype}
                        choice_column = ft.Column(spacing=6, visible=False)
                        answer_input = ft.TextField(label="你的答案", multiline=True, disabled=True, visible=not is_choice)
                        result_text = ft.Text("", size=14)
                        knowledge_tip = ft.Text("", size=14, visible=False)
                        answer_btn = ft.ElevatedButton("作答", visible=not is_answered)
                        submit_btn = ft.ElevatedButton("提交", visible=False)
                        options = []
                        choice_buttons = []
                        if is_choice:
                            if card.get("options"):
                                options = [(opt[:2].strip(" .、"), opt[2:].strip()) for opt in card.get("options", [])]
                            else:
                                matches = re.findall(r'([A-D])[\.\、\s]\s*(.+?)(?=[A-D][\.\、\s]|$)', q_text)
                                if matches:
                                    options = [(m[0], m[1].strip()) for m in matches]
                            if not options:
                                options = [("A", "A"), ("B", "B"), ("C", "C"), ("D", "D")]
                            for letter, opt_text in options:
                                btn = ft.TextButton(text=f"{letter}. {opt_text}", data={"letter": letter, "state": card_state},
                                                    on_click=on_option_click)
                                choice_buttons.append(btn)
                                choice_column.controls.append(btn)
                            choice_column.visible = True
                            answer_input.visible = False
                            card_state["options"] = options
                            card_state["choice_buttons"] = choice_buttons
                        card_state["answer_input"] = answer_input
                        card_state["result_text"] = result_text
                        card_state["knowledge_tip"] = knowledge_tip
                        card_state["answer_btn"] = answer_btn
                        card_state["submit_btn"] = submit_btn
                        card_state["choice_column"] = choice_column
                        card_state["card_id"] = card.get("id", str(random.randint(1000, 9999)))
                        card_state["is_choice"] = is_choice

                        def enable_answer(e, state=card_state):
                            if state["is_choice"]:
                                for btn in state["choice_buttons"]:
                                    btn.disabled = False
                            else:
                                state["answer_input"].disabled = False
                            state["answer_btn"].visible = False
                            state["submit_btn"].visible = True
                            page.update()

                        answer_btn.on_click = enable_answer

                        def make_submit(state, card_data=card):
                            def submit(e):
                                if state["submitted"]:
                                    return
                                user_ans = state["selected"].strip() if state["is_choice"] else state["answer_input"].value.strip()
                                if not user_ans:
                                    state["result_text"].value = "请输入答案"
                                    page.update()
                                    return
                                state["submitted"] = True
                                is_correct_ans, explanation, blanks_info = ai_judge_answer(
                                    user_ans, state["answer_text"],
                                    state.get("question_text", ""),
                                    state.get("question_type", "简答")
                                )
                                if state["is_choice"]:
                                    for i, btn in enumerate(state["choice_buttons"]):
                                        btn.disabled = True
                                        opt_letter = state["options"][i][0]
                                        correct_letter = state["answer_text"].strip().upper()[:1]
                                        if is_correct_ans:
                                            btn.style = ft.ButtonStyle(
                                                bgcolor="#66BB6A" if opt_letter == correct_letter else "#F5F5F5")
                                        else:
                                            btn.style = ft.ButtonStyle(bgcolor="#66BB6A" if opt_letter == correct_letter else (
                                                "#EF5350" if opt_letter == user_ans.upper() else "#F5F5F5"))
                                        btn.update()
                                else:
                                    state["answer_input"].disabled = True

                                if blanks_info:
                                    detail_lines = []
                                    for b in blanks_info:
                                        icon = "✅" if b["is_correct"] else "❌"
                                        detail_lines.append(f"  空{b['index']}: {icon} 你的答案: {b['user_answer']}  正确答案: {b['correct_answer']}")
                                    result_msg = "整体：" + ("✅ 正确" if is_correct_ans else "❌ 错误") + "\n" + "\n".join(detail_lines)
                                    state["result_text"].value = result_msg
                                else:
                                    state["result_text"].value = f"{'✅ 正确！' if is_correct_ans else '❌ 错误'}\n{explanation}"

                                if is_correct_ans:
                                    update_review_card(state["card_id"], 80, True)
                                else:
                                    if state["kp"]:
                                        state["knowledge_tip"].value = f"📚 知识点：{state['kp']}"
                                        state["knowledge_tip"].visible = True
                                    update_review_card(state["card_id"], 50, False)
                                state["answer_btn"].visible = False
                                state["submit_btn"].visible = False
                                page.update()

                            return submit

                        submit_btn.on_click = make_submit(card_state)

                        status_label = ft.Text("", size=12)
                        if is_answered:
                            status_label.value = f"✅ 已答对 ({answered_time})" if is_correct else f"❌ 已答错 ({answered_time})"
                            status_label.color = "green" if is_correct else "red"
                            if is_choice:
                                for btn in choice_buttons:
                                    btn.disabled = True
                            else:
                                answer_input.disabled = True
                            answer_btn.visible = False
                            submit_btn.visible = False

                        def show_detail(card_data=card):
                            detail_text = f"""题目：{card_data.get('question','')}

标准答案：{card_data.get('answer','')}

知识点：{card_data.get('knowledge_point','')}

出题时间：{card_data.get('created','')}
答题时间：{card_data.get('answered_time','未作答')}"""

                            def open_chat_for_detail():
                                page.close(detail_dlg)
                                subj = card_data.get("subject", "总AI")
                                prompt = f"""我正在复习一道错题，请帮我举一反三：

📝 原题：{card_data.get('question','')}
✅ 标准答案：{card_data.get('answer','')}
📚 知识点：{card_data.get('knowledge_point','')}

请根据以上错题、标准答案和知识点，生成3道同类型的巩固练习题，帮助我举一反三、彻底掌握该知识点。"""
                                open_chat(subj, initial_message=prompt)

                            detail_dlg = ft.AlertDialog(
                                title=ft.Text("题目详情"),
                                content=ft.Column([ft.Text(detail_text, size=14)], scroll=ft.ScrollMode.AUTO, height=300),
                                actions=[
                                    ft.TextButton("关闭", on_click=lambda e: page.close(detail_dlg)),
                                    ft.ElevatedButton("🔄 举一反三", on_click=lambda e: open_chat_for_detail())
                                ]
                            )
                            page.open(detail_dlg)

                        review_card_list.controls.append(ft.Container(
                            content=ft.Column([
                                ft.Row([ft.Text(type_label, size=14), ft.Text(kp, size=14)]),
                                ft.Text(q_text, size=16),
                                answer_input, choice_column,
                                ft.Row([answer_btn, submit_btn]),
                                result_text, knowledge_tip,
                                ft.Row([status_label, ft.TextButton("查看详情", on_click=lambda e, cd=card: show_detail(cd))]),
                            ], spacing=8),
                            padding=14, border_radius=14, border=ft.border.all(2, border_color), bgcolor=bg_color
                        ))
                page.update()
            except Exception as e:
                review_card_list.controls.clear()
                review_card_list.controls.append(
                    ft.Container(
                        content=ft.Text(f"❌ 加载复习卡片失败：{str(e)}", size=16, color="red"),
                        padding=20
                    )
                )
                page.update()

        def on_option_click(e):
            state = e.control.data["state"]
            letter = e.control.data["letter"]
            state["selected"] = "" if state["selected"] == letter else letter
            for i, b in enumerate(state["choice_buttons"]):
                b.style = ft.ButtonStyle(bgcolor="#66BB6A" if state["options"][i][0] == state["selected"] else "#F5F5F5")
                b.update()
            page.update()

        def generate_new_cards(e):
            subj = review_subject_dropdown.value
            if not subj:
                return
            difficulty = difficulty_dropdown.value
            review_status.value = f"⏳ 生成{difficulty}难度卡片..."
            page.update()

            def generate():
                cards = generate_review_cards(subj, 3, difficulty)
                if cards:
                    for c in cards:
                        card_data = {
                            "id": str(random.randint(10000, 99999)), "subject": subj,
                            "type": c.get("type", "简答"), "question": c.get("question", ""),
                            "answer": c.get("answer", ""), "options": c.get("options", []),
                            "knowledge_point": c.get("knowledge_point", ""),
                            "proficiency": 0, "review_count": 0,
                            "next_review": datetime.now().strftime("%Y-%m-%d"),
                            "created": time.strftime("%Y-%m-%d %H:%M:%S"),
                            "answered_time": ""
                        }
                        add_review_card(card_data)
                    review_status.value = f"✅ 已生成{len(cards)}张卡片"
                else:
                    review_status.value = "❌ 生成失败"
                refresh_review_view()

            threading.Thread(target=generate, daemon=True).start()

        def generate_exam(e):
            subj = review_subject_dropdown.value
            if not subj:
                return
            difficulty = difficulty_dropdown.value
            review_status.value = f"⏳ 正在生成{difficulty}难度复习卷..."
            page.update()

            def generate():
                cards = generate_exam_paper(subj, 5, difficulty)
                if cards:
                    for c in cards:
                        card_data = {
                            "id": str(random.randint(10000, 99999)), "subject": subj,
                            "type": c.get("type", "简答"), "question": c.get("question", ""),
                            "answer": c.get("answer", ""), "options": c.get("options", []),
                            "knowledge_point": c.get("knowledge_point", ""),
                            "proficiency": 0, "review_count": 0,
                            "next_review": datetime.now().strftime("%Y-%m-%d"),
                            "created": time.strftime("%Y-%m-%d %H:%M:%S"),
                            "answered_time": ""
                        }
                        add_review_card(card_data)
                    review_status.value = f"✅ 已生成{len(cards)}道复习卷"
                else:
                    review_status.value = "❌ 生成失败，请重试或尝试生成复习卡片"
                refresh_review_view()

            threading.Thread(target=generate, daemon=True).start()

        def open_precision_review_dialog(e):
            subj = review_subject_dropdown.value
            if not subj:
                review_status.value = "请先选择科目"
                page.update()
                return
            req_input = ft.TextField(label="描述你的复习需求", multiline=True, min_lines=3, max_lines=6,
                                     hint_text="例：我想复习三角函数的恒等变换题型")
            knowledge_input = ft.TextField(label="知识点（选填，精确匹配）", multiline=False,
                                           hint_text="例：三角函数恒等变换、向量的数量积")
            question_type_dropdown = ft.Dropdown(
                label="题型",
                options=[ft.dropdown.Option(t) for t in ["不限", "选择题", "填空题", "简答题", "综合大题"]],
                value="不限",
                width=200,
            )
            count_dropdown = ft.Dropdown(
                label="出题数量",
                options=[ft.dropdown.Option(str(n)) for n in [1, 2, 3, 5, 10]],
                value="3",
                width=120,
            )

            def do_precision_review(e):
                req = req_input.value.strip()
                knowledge = knowledge_input.value.strip()
                qtype = question_type_dropdown.value
                count_str = count_dropdown.value
                count = int(count_str) if count_str and count_str.isdigit() else 3
                if not req:
                    page.snack_bar = ft.SnackBar(ft.Text("请输入复习需求"))
                    page.snack_bar.open = True
                    page.update()
                    return
                page.close(precision_dlg)
                review_status.value = "⏳ AI正在根据你的需求出题..."
                page.update()

                def _generate():
                    try:
                        profile = load_user_profile()
                        weak_know = sorted([(k, v) for k, v in profile.get("weak_knowledge", {}).items() if
                                            k.startswith(f"{subj}-")], key=lambda x: x[1], reverse=True)[:5]
                        focus = profile.get("recent_focus", [])[:5]
                        type_constraint = f"\n题目类型必须全部为：{qtype}" if qtype and qtype != "不限" else ""
                        knowledge_constraint = f"\n知识点严格限定为：{knowledge}" if knowledge else ""
                        prompt = f"""你是高中{subj}老师。用户需求：{req}{knowledge_constraint}{type_constraint}
学习画像信息：
薄弱知识点：{', '.join([k for k,_ in weak_know]) if weak_know else '无'}
近期关注：{', '.join(focus) if focus else '无'}
请根据用户需求、知识点约束和题型约束，严格生成{count}道针对性巩固练习题。
返回JSON数组：[{{"type":"选择/填空/简答/综合","question":"...","answer":"...","knowledge_point":"...","options":["A.xxx","B.xxx","C.xxx","D.xxx"]}}]
选择题必须提供options字段（4个选项）。只返回JSON数组。"""
                        api_key = load_ai_config().get("api_key_free", "").strip()
                        if not api_key:
                            review_status.value = "❌ 未配置API密钥"
                            page.update()
                            return
                        resp = requests.post("https://open.bigmodel.cn/api/paas/v4/chat/completions",
                                             headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                                             json={"model": "glm-4-flash", "messages": [{"role": "user", "content": prompt}],
                                                   "temperature": 0.7, "max_tokens": 1500}, timeout=45)
                        if resp.status_code == 200:
                            content = resp.json()["choices"][0]["message"]["content"]
                            try:
                                cards = json.loads(content)
                            except:
                                match = re.search(r'\[.*\]', content, re.DOTALL)
                                cards = json.loads(match.group()) if match else None
                            if cards:
                                for c in cards:
                                    c["question"] = c.get("question", "")
                                    c["answer"] = c.get("answer", "")
                                    card_data = {
                                        "id": str(random.randint(10000, 99999)), "subject": subj,
                                        "type": c.get("type", "简答"), "question": c.get("question", ""),
                                        "answer": c.get("answer", ""), "options": c.get("options", []),
                                        "knowledge_point": c.get("knowledge_point", ""),
                                        "proficiency": 0, "review_count": 0,
                                        "next_review": datetime.now().strftime("%Y-%m-%d"),
                                        "created": time.strftime("%Y-%m-%d %H:%M:%S"),
                                        "answered_time": ""
                                    }
                                    add_review_card(card_data)
                                review_status.value = f"✅ 精准复习已生成{len(cards)}道题目"
                            else:
                                review_status.value = "❌ AI返回格式异常，请重试"
                        else:
                            review_status.value = f"❌ API错误: {resp.status_code}"
                    except Exception as ex:
                        review_status.value = f"❌ 生成失败: {str(ex)[:60]}"
                    refresh_review_view()

                threading.Thread(target=_generate, daemon=True).start()

            precision_dlg = ft.AlertDialog(
                title=ft.Text("🎯 精准复习"),
                content=ft.Column([
                    ft.Text(f"科目：{subj}", size=16),
                    req_input,
                    knowledge_input,
                    ft.Row([question_type_dropdown, count_dropdown], spacing=10),
                ], spacing=10),
                actions=[
                    ft.TextButton("取消", on_click=lambda e: page.close(precision_dlg)),
                    ft.ElevatedButton("生成题目", on_click=do_precision_review)
                ]
            )
            page.open(precision_dlg)

        review_page = ft.Column([
            ft.Text("🧠 智能复习", size=24),
            ft.Row([
                review_subject_dropdown,
                difficulty_dropdown,
                ft.ElevatedButton("🎯 精准复习", on_click=open_precision_review_dialog),
                ft.ElevatedButton("生成卡片", on_click=generate_new_cards),
                ft.ElevatedButton("生成复习卷", on_click=generate_exam)
            ], spacing=10),
            review_status, ft.Divider(),
            ft.Text("📝 复习任务", size=20),
            ft.Container(content=review_card_list, expand=True)
        ], spacing=15, expand=True)
        refresh_review_view()

        # ==================== 英语单词本 ====================
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

        def build_vocab_page(subject, mode="vocab"):
            try:
                all_vocab = load_jsonl(VOCAB_FILE)
                all_words = sorted(all_vocab, key=lambda x: x.get("word", "").lower())

                if mode == "new_words":
                    user_nw = set(_load_user_new_words())
                    all_words = [w for w in all_words if w.get("word", "") in user_nw]

                vocab_list_view = ft.ListView(spacing=2, expand=True)
                search_field = ft.TextField(label="🔍 搜索单词", hint_text="输入单词搜索...", expand=True)
                count_text = ft.Text("", size=14, color=ft.Colors.GREY_600)

                def _generate_and_add_word(word):
                    existing = load_jsonl(VOCAB_FILE)
                    if any(w.get("word", "").lower() == word.lower() for w in existing):
                        return True
                    new_data = generate_word_info(word)
                    if new_data:
                        existing.append(new_data)
                        save_jsonl(VOCAB_FILE, existing)
                        return True
                    return False

                def _open_word_detail(word_data):
                    try:
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
                            content_children.append(ft.Text(f"🔊 {phonetic}", size=16, color=ft.Colors.PINK_700))
                        if meaning:
                            content_children.append(ft.Text(meaning, size=16, color=ft.Colors.GREEN_800))
                        if example:
                            content_children.append(ft.Text(f"例句：{example}", size=14, italic=True, color=ft.Colors.GREY_700))

                        if forms:
                            forms_words = [f.strip() for f in forms.replace(',', ' ').split() if f.strip()]
                            if forms_words:
                                forms_row = ft.Row(spacing=8)
                                forms_row.controls.append(ft.Text("变形：", size=14, weight=ft.FontWeight.BOLD))
                                for fw in forms_words:
                                    target_word_data = next(
                                        (w for w in all_vocab if w.get("word", "").lower() == fw.lower()), None)
                                    if target_word_data:
                                        btn = ft.TextButton(
                                            text=fw,
                                            on_click=lambda e, wd=target_word_data: _open_word_detail(wd),
                                            style=ft.ButtonStyle(color=ft.Colors.BLUE_700,
                                                                 text_style=ft.TextStyle(decoration=ft.TextDecoration.UNDERLINE))
                                        )
                                    else:
                                        def make_generate_click(fw_word):
                                            def on_click(e):
                                                page.snack_bar = ft.SnackBar(ft.Text(f"⏳ 正在生成单词 {fw_word}..."))
                                                page.snack_bar.open = True
                                                page.update()
                                                success = _generate_and_add_word(fw_word)
                                                if success:
                                                    nonlocal all_vocab, all_words
                                                    all_vocab = load_jsonl(VOCAB_FILE)
                                                    all_words = sorted(all_vocab, key=lambda x: x.get("word", "").lower())
                                                    _render_list(search_field.value)
                                                    page.snack_bar = ft.SnackBar(ft.Text(f"✅ 已添加单词 {fw_word}"))
                                                else:
                                                    page.snack_bar = ft.SnackBar(ft.Text(f"❌ 生成 {fw_word} 失败"))
                                                page.snack_bar.open = True
                                                page.update()
                                                _open_word_detail(word_data)

                                            return on_click

                                        btn = ft.TextButton(
                                            text=fw,
                                            on_click=make_generate_click(fw),
                                            style=ft.ButtonStyle(color=ft.Colors.ORANGE_700,
                                                                 text_style=ft.TextStyle(decoration=ft.TextDecoration.UNDERLINE))
                                        )
                                    forms_row.controls.append(btn)
                                content_children.append(forms_row)

                        if grammar:
                            grammar_parts = []
                            if grammar.get("collocations"):
                                grammar_parts.append(f"搭配：{', '.join(grammar['collocations'])}")
                            if grammar.get("notes"):
                                grammar_parts.append(f"笔记：{' ; '.join(grammar['notes'])}")
                            if grammar.get("test_points"):
                                grammar_parts.append(f"考点：{' ; '.join(grammar['test_points'])}")
                            if grammar_parts:
                                content_children.append(ft.Text("📚 语法", size=14, weight=ft.FontWeight.BOLD))
                                for gp in grammar_parts:
                                    content_children.append(ft.Text(gp, size=13, color=ft.Colors.BLUE_800))

                        if phrases:
                            content_children.append(ft.Text("🔗 短语", size=14, weight=ft.FontWeight.BOLD))
                            for ph in phrases:
                                content_children.append(ft.Text(f"• {ph}", size=13, color=ft.Colors.TEAL_700))

                        nw_set = set(_load_user_new_words())
                        is_in_nw = word in nw_set

                        def toggle_nw(e, w=word):
                            nw_list = _load_user_new_words()
                            if w in nw_list:
                                _remove_from_new_words(w)
                            else:
                                _add_to_new_words(w)
                            _render_list(search_field.value)
                            page.close(dialog)
                            _open_word_detail(word_data)
                            page.update()

                        content_children.append(
                            ft.Container(
                                content=ft.Text(
                                    "✅ 已在生词本" if is_in_nw else "➕ 加入生词本",
                                    size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE
                                ),
                                bgcolor=ft.Colors.GREEN_600 if is_in_nw else ft.Colors.AMBER_600,
                                border_radius=20,
                                padding=ft.Padding(left=16, right=16, top=8, bottom=8),
                                on_click=toggle_nw,
                                ink=True,
                            )
                        )

                        dialog = ft.AlertDialog(
                            title=ft.Text(""),
                            content=ft.Container(
                                content=ft.Column(content_children, spacing=8, scroll=ft.ScrollMode.AUTO),
                                width=400, height=450,
                                padding=10,
                            ),
                            actions=[ft.TextButton("关闭", on_click=lambda e: page.close(dialog))],
                        )
                        page.open(dialog)
                        page.update()
                    except Exception as e:
                        show_toast(f"打开单词详情失败：{str(e)}", "red")

                def _render_list(keyword=""):
                    try:
                        vocab_list_view.controls.clear()
                        kw = keyword.strip().lower()
                        filtered = all_words
                        if kw:
                            filtered = [w for w in all_words if kw in w.get("word", "").lower()
                                        or kw in w.get("meaning", "").lower()]
                        BATCH = 100
                        total = len(filtered)
                        shown = min(BATCH, total)
                        count_text.value = f"共 {total} 词" + (
                            f"（显示前 {shown} 条，请搜索缩小范围）" if total > BATCH else "")
                        nw_set = set(_load_user_new_words()) if mode == "vocab" else set()

                        for w in filtered[:BATCH]:
                            word = w.get("word", "")
                            phonetic = w.get("phonetic", "")
                            meaning_short = w.get("meaning", "")[:50]
                            is_new = word in nw_set

                            def _show_detail(e, wd=w):
                                _open_word_detail(wd)

                            tile = ft.ListTile(
                                leading=ft.Icon(ft.Icons.BOOKMARK if is_new else ft.Icons.CIRCLE, size=16,
                                                color=ft.Colors.AMBER if is_new else ft.Colors.GREY_400),
                                title=ft.Text(f"{word}  {phonetic}", size=15),
                                subtitle=ft.Text(meaning_short, size=12, color=ft.Colors.GREY_600),
                                trailing=ft.IconButton(
                                    icon=ft.Icons.PLAY_ARROW, icon_size=20,
                                    tooltip="查看详情/加入生词本",
                                    on_click=lambda e, wd=w: (
                                        _add_to_new_words(wd.get("word", "")) if wd.get("word",
                                                                                         "") not in _load_user_new_words() else None,
                                        _render_list(search_field.value),
                                    )
                                ),
                                on_click=_show_detail,
                                dense=True,
                            )
                            vocab_list_view.controls.append(tile)
                        page.update()
                    except Exception as e:
                        vocab_list_view.controls.clear()
                        vocab_list_view.controls.append(
                            ft.Container(
                                content=ft.Text(f"❌ 加载单词列表失败：{str(e)}", size=16, color="red"),
                                padding=20
                            )
                        )
                        page.update()

                def _on_search(e):
                    _render_list(search_field.value)
                    page.update()

                search_field.on_change = _on_search

                add_word_input = ft.TextField(label="新增单词", hint_text="输入英文单词", expand=True)

                def _add_custom_word(e):
                    word = add_word_input.value.strip().lower()
                    if not word:
                        return
                    existing = load_jsonl(VOCAB_FILE)
                    if any(w.get("word", "").lower() == word for w in existing):
                        show_message(mine_msg, f"单词 {word} 已存在", "orange")
                        add_word_input.value = ""
                        page.update()
                        return
                    new_entry = {"word": word, "phonetic": "", "meaning": "", "example": "", "forms": "", "grammar": {}}
                    existing.append(new_entry)
                    save_jsonl(VOCAB_FILE, existing)
                    show_message(mine_msg, f"已添加 {word}，可编辑详情", "green")
                    add_word_input.value = ""
                    _render_list(search_field.value)
                    page.update()

                title_text = "📖 单词本" if mode == "vocab" else "📘 生词表"
                _render_list()
                return ft.Column([
                    ft.Text(title_text, size=20),
                    ft.Text("英语学科专属，点击单词查看详情" if mode == "vocab" else "你标记的待背生词", size=14,
                            color=ft.Colors.GREY_600),
                    ft.Row([search_field, count_text], spacing=10),
                    ft.Divider(height=1),
                    ft.Container(content=vocab_list_view, expand=True),
                    ft.Divider(height=1),
                    ft.Row([add_word_input, ft.ElevatedButton("添加", on_click=_add_custom_word)],
                           spacing=10) if mode == "vocab" else ft.Text(""),
                ], spacing=8, expand=True)
            except Exception as e:
                return ft.Column([
                    ft.Text("❌ 单词本加载失败", size=20, color="red"),
                    ft.Text(f"错误信息：{str(e)}", size=16, selectable=True),
                    ft.Text(f"堆栈：\n{traceback.format_exc()}", size=12, selectable=True),
                ])

        def _vocab_page_dynamic(subject):
            return build_vocab_page(subject, mode="vocab")

        def _new_words_page_dynamic(subject):
            return build_vocab_page(subject, mode="new_words")

        vocab_page = _vocab_page_dynamic
        new_words_page = _new_words_page_dynamic

        # ==================== 学科页面 ====================
        selected_subject_for_page = "数学"

        def build_function_card_grid(subject):
            all_cards = [
                ("📋", "错题本", ft.Colors.BLUE_100),
                ("📝", "笔记本", ft.Colors.GREEN_100),
                ("🧠", "智能复习", ft.Colors.ORANGE_100),
                ("📖", "单词本", ft.Colors.PURPLE_100),
                ("📘", "生词表", ft.Colors.TEAL_100),
                ("💬", "金句", ft.Colors.PINK_100),
            ]
            cards_config = all_cards if subject == "英语" else all_cards[:3]

            grid = ft.ResponsiveRow(
                spacing=20,
                run_spacing=20,
                expand=True,
            )

            for icon, name, bg in cards_config:
                card = ft.Container(
                    content=ft.Column([
                        ft.Text(icon, size=36),
                        ft.Text(name, size=16, weight=ft.FontWeight.BOLD),
                    ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
                    bgcolor=bg,
                    border_radius=16,
                    padding=20,
                    ink=True,
                    on_click=lambda e, subj=subject, fn=name: open_function_page(subj, fn),
                    expand=True,
                )
                grid.controls.append(
                    ft.Container(
                        content=card,
                        col={"xs": 12, "sm": 6, "md": 6, "lg": 4, "xl": 3},
                    )
                )

            return grid

        def open_function_page(subject, function_name):
            try:
                if function_name == "智能复习":
                    review_subject_dropdown.value = subject
                    review_subject_dropdown.disabled = True
                    refresh_review_view()

                def go_back(e):
                    nonlocal selected_subject_for_page
                    if function_name == "智能复习":
                        review_subject_dropdown.disabled = False
                        refresh_review_view()
                    selected_subject_for_page = subject
                    subject_page_content.content = build_subject_page()
                    page.update()

                func_pages = {
                    "错题本": build_error_list_page(subject),
                    "笔记本": build_note_list_page(subject),
                    "单词本": vocab_page(subject),
                    "生词表": new_words_page(subject),
                    "智能复习": review_page,
                    "金句": build_sentence_page(subject, page),
                }
                func_content = func_pages.get(function_name)
                full_page = ft.Column([
                    ft.Row([
                        ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=go_back),
                        ft.Text(f"{subject} - {function_name}", size=20, weight=ft.FontWeight.BOLD),
                    ]),
                    ft.Divider(),
                    ft.Container(content=func_content, expand=True) if func_content else ft.Container(
                        content=ft.Text("暂无内容"), expand=True),
                ], spacing=10, expand=True)
                subject_page_content.content = full_page
                page.update()
            except Exception as e:
                error_page = ft.Column([
                    ft.Text(f"❌ 打开 {function_name} 失败", size=20, color="red"),
                    ft.Text(f"错误信息：{str(e)}", size=16, selectable=True),
                    ft.Text(f"堆栈：\n{traceback.format_exc()}", size=12, selectable=True),
                ])
                subject_page_content.content = error_page
                page.update()

        # ★ 错题本 ★
        def build_error_list_page(subject):
            try:
                import traceback
                import re
                items = load_jsonl(ERRORS_FILE)
                subject_items = [i for i in items if i.get("subject") == subject]
                subject_items.sort(key=lambda x: x.get("timestamp", 0), reverse=True)

                tag_colors = [
                    "#E3F2FD", "#FFF3E0", "#E8F5E9", "#FCE4EC", "#F3E5F5",
                    "#E0F7FA", "#FFF8E1", "#F1F8E9", "#FBE9E7", "#EDE7F6"
                ]

                def get_tag_color(tags):
                    if not tags:
                        return "#F8F9FA"
                    idx = abs(hash(tags[0])) % len(tag_colors)
                    return tag_colors[idx]

                def reset_all_cards():
                    for key, container in card_refs.items():
                        container.bgcolor = "#F8F9FA"
                        container.border = ft.border.all(1, "#E0E0E0")

                def clean_time_str(t):
                    if not t:
                        return ""
                    return re.sub(r'\s+', ' ', t).strip()

                search_input = ft.TextField(
                    label="🔍 智能搜索错题",
                    hint_text="输入知识点或描述，如：我想复习导数",
                    expand=True,
                    on_submit=lambda e: perform_smart_search(e),
                    border_color=ft.Colors.BLUE_400,
                    border_width=2,
                )
                search_btn = ft.ElevatedButton("搜索", on_click=lambda e: perform_smart_search(e), icon=ft.Icons.SEARCH,
                                               bgcolor=ft.Colors.BLUE_500, color=ft.Colors.WHITE)
                search_status = ft.Text("", size=13, color=ft.Colors.GREY_600)
                search_row = ft.Row([search_input, search_btn], spacing=10)

                list_view = ft.ListView(spacing=10, expand=True)
                card_refs = {}

                @retry_request(max_retries=2, base_delay=2)
                def perform_smart_search(e):
                    query = search_input.value.strip()
                    if not query:
                        search_status.value = "请输入搜索内容"
                        search_status.color = ft.Colors.ORANGE
                        page.update()
                        return

                    reset_all_cards()
                    search_status.value = f"⏳ AI正在分析：{query}"
                    search_status.color = ft.Colors.BLUE
                    page.update()

                    def do_search():
                        api_key = load_ai_config().get("api_key_free", "").strip()
                        if not api_key:
                            search_status.value = "❌ 未配置API密钥"
                            search_status.color = ft.Colors.RED
                            page.update()
                            return

                        prompt = f"""请分析以下错题列表，找出与用户查询匹配的题目。
用户查询：{query}

错题列表（仅显示题目摘要）：
{chr(10).join([f"[{i+1}] {e.get('original', '')[:100]}" for i, e in enumerate(subject_items)])}

返回匹配的题目序号（从1开始），JSON数组格式，如：[1, 3, 5]
只返回JSON数组，不要其他文字。"""
                        try:
                            resp = requests.post("https://open.bigmodel.cn/api/paas/v4/chat/completions",
                                                 headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                                                 json={"model": "glm-4-flash", "messages": [{"role": "user", "content": prompt}],
                                                       "temperature": 0.3, "max_tokens": 500}, timeout=30)
                            if resp.status_code == 200:
                                content = resp.json()["choices"][0]["message"]["content"]
                                try:
                                    matches = json.loads(content)
                                except:
                                    match = re.search(r'\[[0-9,\s]*\]', content)
                                    matches = json.loads(match.group()) if match else []

                                if matches and isinstance(matches, list):
                                    highlight_indices = [m - 1 for m in matches if 1 <= m <= len(subject_items)]
                                    if highlight_indices:
                                        for idx in highlight_indices:
                                            key = str(idx)
                                            if key in card_refs:
                                                card_refs[key].bgcolor = "#FFF3CD"
                                                card_refs[key].border = ft.border.all(2, "#FFC107")
                                        search_status.value = f"✅ 找到 {len(highlight_indices)} 个匹配的错题"
                                        search_status.color = ft.Colors.GREEN
                                        if highlight_indices:
                                            first_key = str(highlight_indices[0])
                                            if first_key in card_refs:
                                                list_view.scroll_to(key=first_key, duration=300)
                                    else:
                                        search_status.value = "❌ 未找到匹配的错题"
                                        search_status.color = ft.Colors.ORANGE
                                else:
                                    search_status.value = "❌ AI未返回有效结果"
                                    search_status.color = ft.Colors.RED
                            else:
                                search_status.value = f"❌ API错误: {resp.status_code}"
                                search_status.color = ft.Colors.RED
                        except Exception as ex:
                            search_status.value = f"❌ 搜索失败: {str(ex)[:50]}"
                            search_status.color = ft.Colors.RED
                            print("[搜索错误]")
                            traceback.print_exc()
                        page.update()

                    threading.Thread(target=do_search, daemon=True).start()

                def render_list():
                    list_view.controls.clear()
                    card_refs.clear()

                    if not subject_items:
                        list_view.controls.append(ft.Container(
                            content=ft.Text("  暂无错题", size=16, color=ft.Colors.GREY_600), padding=20
                        ))
                        page.update()
                        return

                    for idx, item in enumerate(subject_items):
                        original = item.get("original", "")
                        mistake = item.get("mistake", "")
                        answer = item.get("answer", "")
                        idea = item.get("idea", "")
                        question = item.get("question", "")
                        q_media = item.get("question_media", []) or item.get("question_images", [])
                        ts_raw = item.get("time", "")
                        ts_clean = clean_time_str(ts_raw)
                        tags = item.get("tags", [])

                        tag_text = "、".join(tags) if tags else "未分类"
                        bg_color = "#F8F9FA"

                        def make_show_detail_card(item_data=item):
                            def show(e):
                                try:
                                    detail_children = []

                                    detail_children.append(
                                        ft.Text("📋 错题详情", size=20, weight=ft.FontWeight.BOLD)
                                    )

                                    time_str = clean_time_str(item_data.get("time", ""))
                                    detail_children.append(
                                        ft.Text(f"科目：{item_data.get('subject', '未知')}  时间：{time_str}", size=14, color=ft.Colors.GREY_700)
                                    )

                                    orig_val = item_data.get("original", "") or item_data.get("question", "")
                                    if orig_val:
                                        detail_children.append(
                                            ft.Text(f"📝 题目：{clean_latex(orig_val)}", size=15, selectable=True)
                                        )

                                    if item_data.get("mistake"):
                                        detail_children.append(
                                            ft.Text(f"❌ 错因：{item_data['mistake']}", size=14, color=ft.Colors.RED_700, selectable=True)
                                        )

                                    if item_data.get("answer"):
                                        detail_children.append(
                                            ft.Text(f"✅ 答案：{clean_latex(item_data['answer'])}", size=14, color=ft.Colors.GREEN_700, selectable=True)
                                        )

                                    if item_data.get("idea"):
                                        detail_children.append(
                                            ft.Text(f"💡 理解：{item_data['idea']}", size=14, color=ft.Colors.BLUE_700, selectable=True)
                                        )

                                    if tags:
                                        detail_children.append(
                                            ft.Text(f"🏷️ 标签：{', '.join(tags)}", size=13, color=ft.Colors.GREY_700)
                                        )

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
                                        detail_children.append(ft.Divider(height=1, color=ft.Colors.GREY_300))
                                        detail_children.append(
                                            ft.Text(f"🖼️ 图片附件（{len(unique_media)}张）", size=14, weight=ft.FontWeight.BOLD)
                                        )

                                        img_row = ft.Row(spacing=8, wrap=True)
                                        for rel_path in unique_media[:5]:
                                            full_path = rel_path if os.path.isabs(rel_path) else os.path.join(DATA_DIR, rel_path)
                                            if os.path.exists(full_path):
                                                try:
                                                    img = ft.Image(
                                                        src=full_path,
                                                        width=120,
                                                        height=120,
                                                        fit=ft.ImageFit.CONTAIN,
                                                        border_radius=8,
                                                    )

                                                    def make_enlarge(p):
                                                        def enlarge(e):
                                                            enlarge_dlg = ft.AlertDialog(
                                                                title=ft.Text("图片"),
                                                                content=ft.Container(
                                                                    content=ft.Image(src=p, width=400, height=400, fit=ft.ImageFit.CONTAIN),
                                                                    width=420, height=420,
                                                                ),
                                                                actions=[ft.TextButton("关闭", on_click=lambda ev: page.close(enlarge_dlg))],
                                                            )
                                                            page.open(enlarge_dlg)
                                                            page.update()
                                                        return enlarge

                                                    img_container = ft.Container(
                                                        content=img,
                                                        on_click=make_enlarge(full_path),
                                                        ink=True,
                                                        border_radius=8,
                                                    )
                                                    img_row.controls.append(img_container)
                                                except Exception as e:
                                                    print(f"[图片加载错误] {full_path}: {e}")
                                                    img_row.controls.append(
                                                        ft.Text(f"⚠️ {os.path.basename(full_path)}", size=12, color=ft.Colors.ORANGE)
                                                    )
                                            else:
                                                img_row.controls.append(
                                                    ft.Text(f"⚠️ 文件不存在：{os.path.basename(rel_path)}", size=12, color=ft.Colors.RED)
                                                )

                                        if img_row.controls:
                                            detail_children.append(img_row)
                                        if len(unique_media) > 5:
                                            detail_children.append(
                                                ft.Text(f"...还有 {len(unique_media)-5} 张", size=12, color=ft.Colors.GREY_500)
                                            )

                                    def open_edit(e):
                                        page.close(detail_dlg)
                                        make_show_detail(item_data)(e)

                                    action_row = ft.Row([
                                        ft.ElevatedButton("✏️ 编辑", on_click=open_edit, icon=ft.Icons.EDIT),
                                        ft.TextButton("关闭", on_click=lambda ev: page.close(detail_dlg)),
                                    ], alignment=ft.MainAxisAlignment.END)

                                    detail_dlg = ft.AlertDialog(
                                        title=ft.Text(""),
                                        content=ft.Container(
                                            content=ft.Column(detail_children, spacing=8, scroll=ft.ScrollMode.AUTO),
                                            width=450, height=500,
                                            padding=10,
                                        ),
                                        actions=[action_row],
                                    )
                                    page.open(detail_dlg)
                                    page.update()
                                except Exception as e:
                                    page.snack_bar = ft.SnackBar(ft.Text(f"打开详情失败：{str(e)}"))
                                    page.snack_bar.open = True
                                    page.update()
                            return show

                        def make_show_detail(item_data=item):
                            def show(e):
                                try:
                                    orig_val = item_data.get("original", "")
                                    mis_val = item_data.get("mistake", "")
                                    ans_val = item_data.get("answer", "")
                                    idea_val = item_data.get("idea", "")
                                    q_val = item_data.get("question", "")
                                    time_val = item_data.get("time", "")
                                    ts_int = item_data.get("timestamp", 0)

                                    orig_input = ft.TextField(label="题目 🔒（锁定中）", value=orig_val, multiline=True, min_lines=2, disabled=True)
                                    mis_input = ft.TextField(label="错因", value=mis_val, multiline=True, min_lines=2)
                                    ans_input = ft.TextField(label="答案", value=ans_val, multiline=True, min_lines=2)
                                    idea_input = ft.TextField(label="我的理解 ✏️（可编辑）", value=idea_val, multiline=True, min_lines=2)
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
                                        for d in all_items:
                                            if d.get("timestamp") == ts_int or (d.get("question") == q_val and d.get("time") == time_val):
                                                d["original"] = orig_input.value
                                                d["question"] = orig_input.value
                                                d["mistake"] = mis_input.value
                                                d["answer"] = ans_input.value
                                                d["idea"] = idea_input.value
                                                d["update_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
                                                break
                                        save_jsonl(ERRORS_FILE, all_items)
                                        page.close(edit_dlg)
                                        page.snack_bar = ft.SnackBar(ft.Text("✅ 已保存"))
                                        page.snack_bar.open = True
                                        page.update()
                                        open_function_page(subject, "错题本")
                                        page.update()

                                    def delete_item(e):
                                        all_items = load_jsonl(ERRORS_FILE)
                                        filtered = [d for d in all_items if not (d.get("timestamp") == ts_int or (d.get("question") == q_val and d.get("time") == time_val))]
                                        save_jsonl(ERRORS_FILE, filtered)
                                        page.close(edit_dlg)
                                        page.snack_bar = ft.SnackBar(ft.Text("🗑️ 已删除"))
                                        page.snack_bar.open = True
                                        page.update()
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
                                        ], scroll=ft.ScrollMode.AUTO, width=400, height=400),
                                        actions=[
                                            ft.TextButton("🗑️ 删除", on_click=delete_item),
                                            ft.TextButton("取消", on_click=lambda e: page.close(edit_dlg)),
                                            ft.ElevatedButton("💾 保存", on_click=save_edit),
                                        ]
                                    )
                                    page.open(edit_dlg)
                                except Exception as e:
                                    page.snack_bar = ft.SnackBar(ft.Text(f"编辑失败：{str(e)}"))
                                    page.snack_bar.open = True
                                    page.update()
                            return show

                        detail_lines = []
                        if original:
                            detail_lines.append(f"📝 {original[:80]}")
                        if mistake:
                            detail_lines.append(f"❌ {mistake[:80]}")
                        if answer:
                            detail_lines.append(f"✅ {answer[:80]}")
                        if idea:
                            detail_lines.append(f"💡 {idea[:80]}")
                        if question:
                            detail_lines.append(f"📄 {question[:80]}")
                        if q_media:
                            detail_lines.append(f"🖼️ 包含图片")
                        if not detail_lines:
                            detail_lines.append("（内容为空）")

                        detail_text = "\n".join(detail_lines[:2])

                        tag_display = ft.Container(
                            content=ft.Text(f"🏷️ {tag_text}", size=11, color=ft.Colors.GREY_700),
                            padding=ft.Padding(left=6, right=6, top=2, bottom=2),
                            bgcolor=ft.Colors.GREY_200,
                            border_radius=8,
                        )

                        container = ft.Container(
                            content=ft.Column([
                                ft.Row([
                                    ft.Text(f"📋 {ts_clean}", size=12, color=ft.Colors.GREY_600, expand=True, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                    tag_display,
                                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                ft.Text(detail_text, size=14, max_lines=2, color=ft.Colors.BLACK87),
                            ], spacing=4),
                            padding=12,
                            border_radius=12,
                            bgcolor=bg_color,
                            border=ft.border.all(1, "#E0E0E0"),
                            on_click=make_show_detail_card(item),
                            ink=True,
                        )
                        key = str(idx)
                        container.key = key
                        card_refs[key] = container
                        list_view.controls.append(container)
                    page.update()

                render_list()

                return ft.Column([
                    ft.Text("📋 错题本", size=20, weight=ft.FontWeight.BOLD),
                    ft.Text("🔍 智能搜索：输入知识点或描述，AI自动匹配相关错题", size=13, color=ft.Colors.BLUE_600),
                    search_row,
                    search_status,
                    ft.Divider(height=1),
                    ft.Container(content=list_view, expand=True),
                ], spacing=8, expand=True)
            except Exception as e:
                return ft.Column([
                    ft.Text("❌ 错题本加载失败", size=20, color="red"),
                    ft.Text(f"错误信息：{str(e)}", size=16, selectable=True),
                    ft.Text(f"堆栈：\n{traceback.format_exc()}", size=12, selectable=True),
                ])

        def build_note_list_page(subject):
            try:
                items = load_jsonl(NOTES_FILE)
                subject_items = [i for i in items if i.get("subject") == subject]
                subject_items.sort(key=lambda x: x.get("timestamp", 0), reverse=True)

                list_view = ft.ListView(spacing=10, expand=True)
                if not subject_items:
                    list_view.controls.append(ft.Container(content=ft.Text("  暂无笔记", size=16, color=ft.Colors.GREY_600),
                                                           padding=20))
                else:
                    for item in subject_items:
                        content = item.get("content", "")
                        images = item.get("images", [])
                        ts = item.get("time", "")
                        ts_int = item.get("timestamp", 0)

                        def make_show_note(item_data=item):
                            def show(e):
                                try:
                                    content_input = ft.TextField(label="笔记内容", value=item_data.get("content", ""), multiline=True,
                                                                 min_lines=4)
                                    time_val = item_data.get("time", "")

                                    def save_edit(e):
                                        all_items = load_jsonl(NOTES_FILE)
                                        for d in all_items:
                                            if d.get("timestamp") == ts_int:
                                                d["content"] = content_input.value
                                                break
                                        save_jsonl(NOTES_FILE, all_items)
                                        page.close(edit_dlg)
                                        page.snack_bar = ft.SnackBar(ft.Text("✅ 已保存"))
                                        page.snack_bar.open = True
                                        page.update()
                                        open_function_page(subject, "笔记本")
                                        page.update()

                                    def delete_item(e):
                                        all_items = load_jsonl(NOTES_FILE)
                                        filtered = [d for d in all_items if d.get("timestamp") != ts_int]
                                        save_jsonl(NOTES_FILE, filtered)
                                        page.close(edit_dlg)
                                        page.snack_bar = ft.SnackBar(ft.Text("🗑️ 已删除"))
                                        page.snack_bar.open = True
                                        page.update()
                                        open_function_page(subject, "笔记本")
                                        page.update()

                                    edit_dlg = ft.AlertDialog(
                                        title=ft.Text("编辑笔记"),
                                        content=ft.Column([content_input], scroll=ft.ScrollMode.AUTO, width=400, height=300),
                                        actions=[
                                            ft.TextButton("🗑️ 删除", on_click=delete_item),
                                            ft.TextButton("取消", on_click=lambda e: page.close(edit_dlg)),
                                            ft.ElevatedButton("💾 保存", on_click=save_edit),
                                        ]
                                    )
                                    page.open(edit_dlg)
                                except Exception as e:
                                    page.snack_bar = ft.SnackBar(ft.Text(f"笔记编辑失败：{str(e)}"))
                                    page.snack_bar.open = True
                                    page.update()
                            return show

                        preview = content[:80] if content else "（空）"
                        img_hint = f" 🖼️{len(images)}张" if images else ""

                        list_view.controls.append(ft.Container(
                            content=ft.Column([
                                ft.Row([
                                    ft.Text(f"📝 {ts}{img_hint}", size=13, color=ft.Colors.GREY_600),
                                    ft.TextButton("编辑", on_click=make_show_note()),
                                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                ft.Text(preview, size=14, max_lines=3),
                            ], spacing=4),
                            padding=12, border_radius=12, bgcolor="#E8F5E9",
                            border=ft.border.all(1, "#A5D6A7"),
                        ))
                return list_view
            except Exception as e:
                return ft.Column([
                    ft.Text("❌ 笔记本加载失败", size=20, color="red"),
                    ft.Text(f"错误信息：{str(e)}", size=16, selectable=True),
                    ft.Text(f"堆栈：\n{traceback.format_exc()}", size=12, selectable=True),
                ])

        def build_subject_left_panel(subj):
            subjects = ["语文", "数学", "英语", "物理", "化学", "生物", "历史", "政治", "地理"]
            subj_buttons = []
            for s in subjects:
                is_selected = s == subj
                btn = ft.Container(
                    content=ft.Text(s, size=16, weight=ft.FontWeight.BOLD,
                                    color="white" if is_selected else "black"),
                    padding=ft.Padding(left=16, top=12, right=16, bottom=12),
                    border_radius=10,
                    bgcolor=ft.Colors.BLUE_600 if is_selected else ft.Colors.GREY_200,
                    on_click=lambda e, ss=s: on_subject_selected(ss),
                )
                subj_buttons.append(btn)
            return ft.Container(content=ft.Column(subj_buttons, spacing=6), width=120, padding=10)

        def build_subject_page():
            nonlocal selected_subject_for_page
            left_panel = build_subject_left_panel(selected_subject_for_page)
            right_panel = build_function_card_grid(selected_subject_for_page)
            return ft.Row([
                left_panel,
                ft.VerticalDivider(width=1),
                ft.Container(content=right_panel, expand=True, padding=ft.Padding(left=20, right=20, top=20, bottom=20)),
            ], expand=True)

        def on_subject_selected(subj):
            nonlocal selected_subject_for_page
            selected_subject_for_page = subj
            subject_page_content.content = build_subject_page()
            page.update()

        main_subject_page = build_subject_page()
        subject_page_content.content = main_subject_page
        subject_page = ft.Column([
            ft.Text("📚 学科浏览", size=24),
            ft.Container(content=subject_page_content, expand=True),
        ], spacing=15, scroll=ft.ScrollMode.AUTO)

        # ==================== 个人中心 ====================
        today_plan_text = ft.Text("点击「生成今日计划」获取 AI 学习建议", size=15, color="grey", selectable=True)
        today_plan_card = ft.Container(
            content=ft.Column([
                ft.Row([ft.Text("📅 今日学习计划", size=18),
                        ft.ElevatedButton("生成今日计划", on_click=lambda e: generate_today_plan(today_plan_text),
                                          height=30)]),
                ft.Divider(height=5), today_plan_text
            ], spacing=8),
            padding=15, border_radius=14, bgcolor="#FFF8E1", border=ft.border.all(1, "#FFE082")
        )

        task_list = ft.Column(spacing=6)
        new_task_input = ft.TextField(label="新学习任务", expand=True)

        def add_task(e):
            text = new_task_input.value.strip()
            if text:
                tasks = load_jsonl(TASKS_FILE)
                tasks.append({"text": text, "done": False, "created": time.strftime("%Y-%m-%d %H:%M:%S")})
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
                            save_jsonl(TASKS_FILE, [d for d in load_jsonl(TASKS_FILE) if d.get("created") != t.get(
                                "created")]), refresh_tasks()))
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
                    ft.Text(f"[{data.get('subject', '未知')}] {preview}", size=16, expand=True),
                    ft.TextButton("恢复", on_click=lambda e, t=ts: (
                        restore_from_recycle(t), refresh_recycle(), show_toast("已恢复")))
                ], spacing=10))
            page.update()

        refresh_recycle()

        ai_config = load_ai_config()
        free_key_input = ft.TextField(label="免费模型 API 密钥", value=ai_config.get("api_key_free", ""), password=True)

        def save_keys(e):
            ai_config = load_ai_config()
            ai_config["api_key_free"] = free_key_input.value.strip()
            save_ai_config(ai_config)
            show_toast("API 密钥已保存")

        test_conn_result = ft.Text("", size=14)

        def test_ai_connection(e):
            test_conn_result.value = "⏳ 测试中..."
            test_conn_result.color = "blue"
            page.update()

            def _test():
                api_key = load_ai_config().get("api_key_free", "").strip()
                if not api_key:
                    test_conn_result.value = "❌ 未配置API密钥"
                    test_conn_result.color = "red"
                    page.update()
                    return
                try:
                    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                    payload = {"model": "glm-4-flash", "messages": [{"role": "user", "content": "仅回复OK"}],
                               "max_tokens": 5, "temperature": 0}
                    resp = requests.post("https://open.bigmodel.cn/api/paas/v4/chat/completions",
                                         headers=headers, json=payload, timeout=10)
                    if resp.status_code == 200:
                        content = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
                        if content.strip():
                            test_conn_result.value = f"✅ 连接成功！返回：{content.strip()}"
                            test_conn_result.color = "green"
                        else:
                            test_conn_result.value = "⚠️ 连接成功但返回内容为空"
                            test_conn_result.color = "orange"
                    else:
                        test_conn_result.value = f"❌ 连接失败 (HTTP {resp.status_code})"
                        test_conn_result.color = "red"
                except requests.exceptions.Timeout:
                    test_conn_result.value = "❌ 连接超时，请检查网络"
                    test_conn_result.color = "red"
                except Exception as ex:
                    test_conn_result.value = f"❌ 连接异常: {str(ex)[:50]}"
                    test_conn_result.color = "red"
                page.update()

            threading.Thread(target=_test, daemon=True).start()

        skill_input = ft.TextField(label="自定义 AI Skill", multiline=True, min_lines=4, max_lines=10,
                                   value=load_custom_skill())

        def save_skill(e):
            save_custom_skill(skill_input.value)
            show_toast("Skill 已保存")

        def show_knowledge_framework(e):
            data = analyze_knowledge_framework()
            error_counts = data.get("error_counts", {})
            total = data.get("total_errors", 0)

            sorted_subjects = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)

            content_children = []

            content_children.append(
                ft.Text(f"📊 知识框架（总错题：{total} 道）", size=18, weight=ft.FontWeight.BOLD)
            )
            content_children.append(ft.Divider(height=1))

            max_count = max([c for _, c in error_counts.items()]) if error_counts else 1

            color_map = {
                "语文": ft.Colors.BLUE_400,
                "数学": ft.Colors.RED_400,
                "英语": ft.Colors.GREEN_400,
                "物理": ft.Colors.PURPLE_400,
                "化学": ft.Colors.ORANGE_400,
                "生物": ft.Colors.TEAL_400,
                "历史": ft.Colors.AMBER_400,
                "政治": ft.Colors.PINK_400,
                "地理": ft.Colors.CYAN_400,
            }

            for subject, count in sorted_subjects:
                percentage = min((count / max_count) * 100, 100) if max_count > 0 else 0
                color = color_map.get(subject, ft.Colors.GREY_400)

                progress_bar = ft.ProgressBar(
                    value=percentage / 100,
                    width=200,
                    height=8,
                    color=color,
                    bgcolor=ft.Colors.GREY_200,
                    border_radius=4,
                )

                row = ft.Row([
                    ft.Text(f"{subject}：{count} 题", size=14, width=80),
                    progress_bar,
                    ft.Text(f"{int(percentage)}%", size=12, color=ft.Colors.GREY_600, width=40),
                ], spacing=10, alignment=ft.MainAxisAlignment.START)
                content_children.append(row)

            if not error_counts:
                content_children.append(
                    ft.Text("暂无错题数据，继续加油！", size=14, color=ft.Colors.GREY_600)
                )

            def close_dlg(e):
                page.close(dlg)

            dlg = ft.AlertDialog(
                title=ft.Text("📊 知识框架"),
                content=ft.Container(
                    content=ft.Column(content_children, spacing=8, scroll=ft.ScrollMode.AUTO),
                    width=400,
                    height=300,
                    padding=10,
                ),
                actions=[
                    ft.TextButton("关闭", on_click=close_dlg),
                ],
            )
            page.open(dlg)
            page.update()

        # ========== 诊断功能 ==========
        def run_diagnosis(e):
            report = diagnose_data_files()
            lines = []
            for name, info in report.items():
                status = info["状态"]
                size_kb = info["大小"] / 1024
                line = f"{name}: {status} ({size_kb:.1f} KB, {info['行数']}行"
                if info["错误行"] > 0:
                    line += f", {info['错误行']}行错误"
                line += ")"
                lines.append(line)
            # 添加数据目录
            lines.append(f"\n📁 数据目录: {DATA_DIR}")
            # 检查 assets 是否存在
            assets_dir = os.path.join(DATA_DIR, "assets") if not hasattr(sys, '_MEIPASS') else None
            if assets_dir and os.path.isdir(assets_dir):
                files = os.listdir(assets_dir)
                lines.append(f"📦 assets 目录存在，包含: {', '.join(files) if files else '空'}")
            else:
                lines.append("📦 assets 目录未找到或已复制")

            # 添加修复建议
            if any(info["错误行"] > 0 for info in report.values()):
                lines.append("\n⚠️ 发现文件有格式错误，可以尝试修复。")
            else:
                lines.append("\n✅ 所有数据文件正常，无需修复。")

            dialog = ft.AlertDialog(
                title=ft.Text("🔍 数据诊断报告"),
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("\n".join(lines), size=14, selectable=True),
                    ]),
                    width=400,
                    height=400,
                    padding=10,
                ),
                actions=[
                    ft.TextButton("关闭", on_click=lambda ev: page.close(dialog)),
                ]
            )
            page.open(dialog)
            page.update()

        # 修复错误文件
        def run_repair(e):
            repaired = 0
            files_to_repair = [ERRORS_FILE, NOTES_FILE, REVIEW_CARDS_FILE, TASKS_FILE, AI_CONFIG_FILE, USER_PROFILE_FILE, VOCAB_FILE, SENTENCES_FILE, RECYCLE_FILE]
            for fp in files_to_repair:
                if os.path.exists(fp):
                    if repair_jsonl_file(fp):
                        repaired += 1
            if repaired > 0:
                show_toast(f"✅ 已修复 {repaired} 个文件", "green")
            else:
                show_toast("没有文件需要修复", "orange")
            # 刷新页面（重新加载数据）
            page.update()

        mine_page = ft.Column([
            ft.Text("⚙️ 个人中心", size=24),
            today_plan_card,
            ft.Divider(),
            ft.Row([
                ft.ElevatedButton("📊 知识框架", on_click=show_knowledge_framework, icon=ft.Icons.BAR_CHART),
                ft.ElevatedButton("🔍 数据诊断", on_click=run_diagnosis, icon=ft.Icons.HEALTH_AND_SAFETY),
                ft.ElevatedButton("🔧 修复文件", on_click=run_repair, icon=ft.Icons.BUILD),
            ], spacing=10),
            mine_msg, ft.Divider(),
            ft.Text("✅ 学习任务清单", size=20), ft.Row([new_task_input, ft.ElevatedButton("添加", on_click=add_task)]),
            task_list,
            ft.Divider(), ft.Text("🗑️ 回收站", size=20), recycle_list,
            ft.ElevatedButton("清空回收站", on_click=lambda e: (empty_recycle(), refresh_recycle(), show_toast("已清空"))),
            ft.Divider(), ft.Text("🧠 AI 引擎设置", size=20), free_key_input, ft.ElevatedButton("保存密钥", on_click=save_keys),
            ft.Row([ft.ElevatedButton("🔌 测试连接", on_click=test_ai_connection), test_conn_result]),
            ft.Divider(), ft.Text("🎓 自定义教学 Skill", size=18), skill_input, ft.ElevatedButton("保存 Skill",
                                                                                                 on_click=save_skill),
            ft.Divider(),
            ft.Text("📁 数据文件夹", size=18, weight=ft.FontWeight.BOLD),
            ft.Text("所有数据（错题、笔记、单词等）保存在：", size=13, color=ft.Colors.GREY_600),
            ft.Text(f"📂 {DATA_DIR}", size=14, selectable=True),
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
                ft.NavigationBarDestination(icon=ft.Icons.PERSON, label="我的")
            ]
        )
        switch_page(0)
        page.add(ft.Stack([current_page, contact_panel, chat_dialog, ball_container], expand=True))

    except Exception as e:
        import traceback
        page.controls.clear()
        page.add(
            ft.Text("❌ 启动错误", size=24, color="red"),
            ft.Text(f"错误信息：{str(e)}", size=16, selectable=True),
            ft.Text(f"堆栈：\n{traceback.format_exc()}", size=12, selectable=True)
        )
        page.update()
        raise

if __name__ == "__main__":
    ft.app(target=main)
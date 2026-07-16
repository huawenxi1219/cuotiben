import flet as ft
import time
import threading
import json
import os
import shutil
import re
import zipfile
import tempfile
import requests
import random
from datetime import datetime, timedelta

# ==================== 数据存储路径 ====================
DATA_PATH_CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data_path.txt")
if os.path.exists(DATA_PATH_CONFIG):
    with open(DATA_PATH_CONFIG, "r", encoding="utf-8") as f:
        custom_path = f.read().strip()
        if os.path.isdir(custom_path):
            DATA_DIR = custom_path
        else:
            DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
else:
    DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

ERRORS_FILE = os.path.join(DATA_DIR, "errors.jsonl")
NOTES_FILE = os.path.join(DATA_DIR, "notes.jsonl")
RECYCLE_FILE = os.path.join(DATA_DIR, "recycle.jsonl")
TASKS_FILE = os.path.join(DATA_DIR, "tasks.jsonl")
IMAGES_DIR = os.path.join(DATA_DIR, "images")
VIDEOS_DIR = os.path.join(DATA_DIR, "videos")
DOCS_DIR = os.path.join(DATA_DIR, "documents")
VOCAB_FILE = os.path.join(DATA_DIR, "vocabulary.jsonl")
WORD_STUDY_FILE = os.path.join(DATA_DIR, "word_study.jsonl")
AI_CONFIG_FILE = os.path.join(DATA_DIR, "ai_config.json")
AI_USAGE_FILE = os.path.join(DATA_DIR, "ai_usage.json")
CHAT_HISTORY_DIR = os.path.join(DATA_DIR, "chat_history")
USER_PROFILE_FILE = os.path.join(DATA_DIR, "user_profile.json")
CONTENT_LIB_DIR = os.path.join(DATA_DIR, "content_lib")
REVIEW_CARDS_FILE = os.path.join(DATA_DIR, "review_cards.jsonl")
NEW_WORDS_FILE = os.path.join(DATA_DIR, "new_words.jsonl")
CUSTOM_SKILL_FILE = os.path.join(DATA_DIR, "custom_skill.txt")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(VIDEOS_DIR, exist_ok=True)
os.makedirs(DOCS_DIR, exist_ok=True)
os.makedirs(CHAT_HISTORY_DIR, exist_ok=True)
os.makedirs(CONTENT_LIB_DIR, exist_ok=True)

# ==================== 词库初始化 ====================
def init_vocabulary():
    if not os.path.exists(VOCAB_FILE):
        sample_words = [
            {"word": "abandon", "phonetic": "/əˈbændən/", "meaning": "v. 放弃；遗弃；沉溺于", "example": "He abandoned his hope of being a doctor.", "grammar": {"patterns": ["abandon sth.", "abandon doing sth."], "collocations": ["abandon oneself to (沉溺于)"], "notes": ["及物动词，后接名词、代词或动名词", "abandon doing sth. 表示“放弃做某事”"], "discrimination": ["abandon (放弃)：强调彻底放弃，不再继续", "desert (抛弃)：强调背弃义务或责任", "quit (停止)：多用于非正式场合，如 quit smoking"], "test_points": ["abandon doing sth. (不是 to do)", "abandon oneself to 是固定搭配"]}, "forms": "abandons, abandoning, abandoned"},
            {"word": "able", "phonetic": "/ˈeɪbl/", "meaning": "adj. 能够的；有能力的", "example": "I am able to finish the task alone.", "grammar": {"patterns": ["be able to do sth."], "collocations": ["able person (有能力的人)"], "notes": ["表示具体的能力，可用于各种时态", "区分 can (只用于现在时和过去时)"], "discrimination": ["able (有能力的)：强调具备做某事的能力", "capable (有能力的)：强调潜在的、内在的能力，搭配 of"], "test_points": ["be able to do sth. (不是 doing)", "时态变化：was/were able to, will be able to"]}, "forms": "比较级: abler, 最高级: ablest"},
            {"word": "abroad", "phonetic": "/əˈbrɔːd/", "meaning": "adv. 在国外；到国外", "example": "She has lived abroad for many years.", "grammar": {"patterns": ["go abroad (出国)", "study abroad (留学)", "be abroad (在国外)"], "collocations": ["at home and abroad (国内外)"], "notes": ["副词，前面不加介词", "不能说 go to abroad"], "discrimination": ["abroad (在国外)：强调状态或动作方向", "overseas (海外)：较正式，可作形容词"], "test_points": ["go abroad (不是 go to abroad)", "study abroad 是固定搭配"]}, "forms": ""},
            {"word": "absent", "phonetic": "/ˈæbsənt/", "meaning": "adj. 缺席的；不在场的", "example": "He was absent from school yesterday.", "grammar": {"patterns": ["be absent from (缺席...)"], "collocations": ["absent-minded (心不在焉的)"], "notes": ["形容词，常与 from 连用"], "discrimination": ["absent (缺席的)：强调不在场", "missing (失踪的)：强调找不到"], "test_points": ["be absent from (不是 be absent in)"]}, "forms": "absence (n. 缺席)"},
            {"word": "absorb", "phonetic": "/əbˈzɔːb/", "meaning": "v. 吸收；吸引（注意力）", "example": "Plants absorb water from the soil.", "grammar": {"patterns": ["absorb sth.", "be absorbed in (全神贯注于)"], "collocations": ["absorb knowledge (吸收知识)", "be absorbed in reading (专心阅读)"], "notes": ["及物动词", "be absorbed in 是固定搭配，表示专注"], "discrimination": ["absorb (吸收)：强调物理或精神上的吸收", "attract (吸引)：强调引起注意"], "test_points": ["be absorbed in (不是 absorb in)"]}, "forms": "absorbs, absorbing, absorbed"},
            {"word": "accept", "phonetic": "/əkˈsept/", "meaning": "v. 接受；承认", "example": "I accepted his invitation.", "grammar": {"patterns": ["accept sth.", "accept that..."], "collocations": ["accept responsibility (承担责任)"], "notes": ["及物动词，后接名词、代词或从句"], "discrimination": ["accept (接受)：强调主观愿意接受", "receive (收到)：强调客观上收到"], "test_points": ["accept doing sth. (不是 to do)", "区分 accept 和 receive"]}, "forms": "accepts, accepting, accepted"},
            {"word": "access", "phonetic": "/ˈækses/", "meaning": "n. 通道；使用权 v. 访问", "example": "Students have access to the library.", "grammar": {"patterns": ["have access to (有...的途径/权利)"], "collocations": ["Internet access (网络访问)", "easy access (便捷通道)"], "notes": ["名词，不可数", "常与 to 连用"], "discrimination": ["access (通道/使用权)：强调权利或途径", "entrance (入口)：强调物理入口"], "test_points": ["have access to 是固定搭配"]}, "forms": "accessible (adj. 可接近的)"},
            {"word": "accompany", "phonetic": "/əˈkʌmpəni/", "meaning": "v. 陪伴；伴随", "example": "She accompanied me to the station.", "grammar": {"patterns": ["accompany sb. to...", "be accompanied by (由...陪同)"], "collocations": ["accompany a singer (为歌手伴奏)"], "notes": ["及物动词", "accompany sb. to... 陪伴某人去某地"], "discrimination": ["accompany (陪伴)：强调一起走", "attend (参加)：强调出席"], "test_points": ["accompany sb. to... (不是 accompany sb. do)"]}, "forms": "accompanies, accompanying, accompanied"},
            {"word": "account", "phonetic": "/əˈkaʊnt/", "meaning": "n. 账户；描述；解释 v. 说明原因", "example": "I have a bank account.", "grammar": {"patterns": ["account for (解释；占比)", "on account of (由于)", "take...into account (考虑)"], "collocations": ["bank account (银行账户)", "account number (账号)"], "notes": ["名词可数", "account for 是高频短语"], "discrimination": ["account (解释)：强调说明原因", "explain (解释)：通用词"], "test_points": ["account for 的两个含义：解释原因 / 占...比例", "on account of = because of"]}, "forms": "accounts"},
            {"word": "achieve", "phonetic": "/əˈtʃiːv/", "meaning": "v. 达到；实现；获得", "example": "He achieved his goal of entering university.", "grammar": {"patterns": ["achieve sth.", "achieve success/goal"], "collocations": ["achieve one's dream (实现梦想)"], "notes": ["及物动词", "强调经过努力而实现"], "discrimination": ["achieve (实现)：强调努力后成功", "reach (到达)：强调物理或抽象上的到达"], "test_points": ["achieve one's goal (不是 reach one's goal 更地道)"]}, "forms": "achieves, achieving, achieved, achievement (n. 成就)"},
        ]
        save_jsonl(VOCAB_FILE, sample_words)

def load_vocabulary():
    return load_jsonl(VOCAB_FILE)

def load_word_study():
    return load_jsonl(WORD_STUDY_FILE)

def save_word_study(data):
    save_jsonl(WORD_STUDY_FILE, data)

# ==================== 数据读写（已加锁） ====================
_jsonl_lock = threading.Lock()

def load_jsonl(filepath):
    if not os.path.exists(filepath):
        return []
    data = []
    with _jsonl_lock:
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

init_vocabulary()

def save_error(subject, original="", original_media=None, answer="", answer_media=None, 
               mistake="", idea="", idea_media=None):
    if original_media is None: original_media = []
    if answer_media is None: answer_media = []
    if idea_media is None: idea_media = []
    data = load_jsonl(ERRORS_FILE)
    entry = {
        "type": "error",
        "subject": subject,
        "original": original,
        "original_media": original_media,
        "answer": answer,
        "answer_media": answer_media,
        "mistake": mistake,
        "idea": idea,
        "idea_media": idea_media,
        "question": original,
        "question_media": original_media,
        "tags": [],
        "error_type": "",
        "difficulty": 0,
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "timestamp": int(time.time()),
        "deep_analysis": ""
    }
    data.append(entry)
    save_jsonl(ERRORS_FILE, data)
    threading.Thread(target=auto_tag_error, args=(entry["timestamp"],), daemon=True).start()

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
  "knowledge_point": "三级知识点，如'导数-链式法则'",
  "sub_knowledge": "四级细分题型，如'复合函数求导-给值求值'",
  "error_type": "错误类型，选一个：计算错误/概念不清/审题偏差/公式遗忘/方法错误/其他",
  "difficulty": 难度分1-5,
  "reason": "简短错误分析"
}}

题目内容：
{content_text[:500]}

只输出JSON，不要额外解释。"""
    
    messages = [{"role": "user", "content": prompt}]
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": "glm-4-flash", "messages": messages, "temperature": 0.3, "max_tokens": 300}
    
    try:
        resp = requests.post("https://open.bigmodel.cn/api/paas/v4/chat/completions", 
                           headers=headers, json=payload, timeout=30)
        if resp.status_code == 200:
            result = resp.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            try:
                tag_data = json.loads(content)
            except:
                match = re.search(r'\{[^}]+\}', content)
                if match:
                    try:
                        tag_data = json.loads(match.group())
                    except:
                        tag_data = {}
                else:
                    tag_data = {}
            
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
                
    except Exception:
        pass

def deep_analyze_errors():
    errors = load_jsonl(ERRORS_FILE)
    ai_config = load_ai_config()
    api_key = ai_config.get("api_key_free", "").strip()
    if not api_key:
        return
    for err in errors:
        if err.get("deep_analysis", ""):
            continue
        subject = err.get("subject", "")
        original = err.get("original", "")
        mistake = err.get("mistake", "")
        idea = err.get("idea", "")
        if not original or not mistake:
            continue
        prompt = f"""你是一位{subject}老师。学生这道题做错了：
题目：{original[:200]}
学生的错误分析：{mistake[:200]}
学生的深层见解：{idea[:200]}

请用200字以内深度分析这道错题反映的知识薄弱点，并给出针对性的学习建议（基于人教版教材）。
只输出分析文本，不要额外解释。"""
        messages = [{"role": "user", "content": prompt}]
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {"model": "glm-4-flash", "messages": messages, "temperature": 0.5, "max_tokens": 300}
        try:
            resp = requests.post("https://open.bigmodel.cn/api/paas/v4/chat/completions", headers=headers, json=payload, timeout=30)
            if resp.status_code == 200:
                analysis = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
                err["deep_analysis"] = analysis
        except:
            pass
    save_jsonl(ERRORS_FILE, errors)

def save_note(subject, content, media):
    data = load_jsonl(NOTES_FILE)
    data.append({
        "type": "note", "subject": subject, "content": content, "media": media,
        "time": time.strftime("%Y-%m-%d %H:%M:%S"), "timestamp": int(time.time())
    })
    save_jsonl(NOTES_FILE, data)
    if content:
        keywords = re.findall(r'[\u4e00-\u9fff]{2,}', content)[:5]
        for kw in keywords:
            update_weak_knowledge(f"{subject}-{kw}", 0.05)

def get_errors_by_subject(subject):
    all_data = load_jsonl(ERRORS_FILE)
    return sorted([d for d in all_data if d.get("subject") == subject],
                  key=lambda x: x.get("timestamp", 0), reverse=True)

def get_notes_by_subject(subject):
    all_data = load_jsonl(NOTES_FILE)
    return sorted([d for d in all_data if d.get("subject") == subject],
                  key=lambda x: x.get("timestamp", 0), reverse=True)

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
        tags = err.get("tags", [])
        for tag in tags:
            for kw in keywords:
                if kw in tag:
                    score += 3
        original = err.get("original", "")
        for kw in keywords:
            if kw in original:
                score += 1
        mistake = err.get("mistake", "")
        for kw in keywords:
            if kw in mistake:
                score += 2
        idea = err.get("idea", "")
        for kw in keywords:
            if kw in idea:
                score += 4
        if score > 0:
            scored.append((score, err))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [err for _, err in scored[:limit]]

def collect_new_words():
    new_words = []
    errors = load_jsonl(ERRORS_FILE)
    for err in errors:
        if err.get("subject") != "英语":
            continue
        text = err.get("original", "") + " " + err.get("answer", "") + " " + err.get("mistake", "") + " " + err.get("idea", "")
        words = re.findall(r'\b[a-zA-Z]+\b', text)
        for w in words:
            if len(w) >= 3:
                new_words.append(w.lower())
    chats = []
    for subj in ["英语"]:
        chat_file = get_chat_history_file(subj)
        if os.path.exists(chat_file):
            chats = load_jsonl(chat_file)
    for msg in chats:
        text = msg.get("content", "")
        words = re.findall(r'\b[a-zA-Z]+\b', text)
        for w in words:
            if len(w) >= 3:
                new_words.append(w.lower())
    vocab_words = {w["word"].lower() for w in load_vocabulary()}
    new_words = [w for w in new_words if w not in vocab_words and len(w) <= 20]
    from collections import Counter
    word_counts = Counter(new_words)
    return [{"word": w, "count": c, "added": time.strftime("%Y-%m-%d %H:%M:%S")} for w, c in word_counts.most_common(50)]

def load_new_words():
    return load_jsonl(NEW_WORDS_FILE)

def save_new_words(data):
    save_jsonl(NEW_WORDS_FILE, data)

# ==================== 学科内容库管理 ====================
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
    if not filename: return {"subject": subject}
    filepath = os.path.join(CONTENT_LIB_DIR, filename)
    if not os.path.exists(filepath): init_content_lib()
    try:
        with open(filepath, "r", encoding="utf-8") as f: return json.load(f)
    except: return {"subject": subject}

def save_content_lib(subject, data):
    filename = CONTENT_LIB_FILES.get(subject)
    if not filename: return
    filepath = os.path.join(CONTENT_LIB_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def add_content_item(subject, category, item):
    lib = load_content_lib(subject)
    if category in lib: lib[category].append(item); save_content_lib(subject, lib); return True
    return False

def get_content_summary(subject):
    lib = load_content_lib(subject)
    summary = {}
    for key, value in lib.items():
        if key != "subject" and isinstance(value, list): summary[key] = len(value)
    return summary

def search_content_lib(subject, keyword):
    lib = load_content_lib(subject)
    results = []
    for category, items in lib.items():
        if category == "subject" or not isinstance(items, list): continue
        for item in items:
            if isinstance(item, dict):
                for v in item.values():
                    if isinstance(v, str) and keyword in v: results.append({"category": category, "item": item}); break
            elif isinstance(item, str) and keyword in item: results.append({"category": category, "item": item})
    return results

init_content_lib()

# ==================== LaTeX 角标转换 ====================
def clean_latex(text):
    superscript_map = {'0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴', '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹', '+': '⁺', '-': '⁻', 'a': 'ᵃ', 'b': 'ᵇ', 'c': 'ᶜ', 'd': 'ᵈ', 'e': 'ᵉ', 'f': 'ᶠ', 'g': 'ᵍ', 'h': 'ʰ', 'i': 'ⁱ', 'j': 'ʲ', 'k': 'ᵏ', 'l': 'ˡ', 'm': 'ᵐ', 'n': 'ⁿ', 'o': 'ᵒ', 'p': 'ᵖ', 'r': 'ʳ', 's': 'ˢ', 't': 'ᵗ', 'u': 'ᵘ', 'v': 'ᵛ', 'w': 'ʷ', 'x': 'ˣ', 'y': 'ʸ', 'z': 'ᶻ'}
    subscript_map = {'0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄', '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉', '+': '₊', '-': '₋', 'a': 'ₐ', 'e': 'ₑ', 'h': 'ₕ', 'i': 'ᵢ', 'j': 'ⱼ', 'k': 'ₖ', 'l': 'ₗ', 'm': 'ₘ', 'n': 'ₙ', 'o': 'ₒ', 'p': 'ₚ', 'r': 'ᵣ', 's': 'ₛ', 't': 'ₜ', 'u': 'ᵤ', 'v': 'ᵥ', 'x': 'ₓ'}
    greek_map = {'alpha': 'α', 'beta': 'β', 'gamma': 'γ', 'delta': 'δ', 'epsilon': 'ε', 'zeta': 'ζ', 'eta': 'η', 'theta': 'θ', 'iota': 'ι', 'kappa': 'κ', 'lambda': 'λ', 'mu': 'μ', 'nu': 'ν', 'xi': 'ξ', 'pi': 'π', 'rho': 'ρ', 'sigma': 'σ', 'tau': 'τ', 'upsilon': 'υ', 'phi': 'φ', 'chi': 'χ', 'psi': 'ψ', 'omega': 'ω'}
    math_symbol_map = {'sqrt': '√', 'times': '×', 'div': '÷', 'pm': '±', 'mp': '∓', 'cdot': '·', 'leq': '≤', 'geq': '≥', 'neq': '≠', 'approx': '≈', 'equiv': '≡', 'infty': '∞', 'rightarrow': '→', 'leftarrow': '←', 'Rightarrow': '⇒', 'Leftarrow': '⇐', 'leftrightarrow': '↔', 'int': '∫', 'sum': '∑', 'prod': '∏', 'partial': '∂', 'nabla': '∇', 'angle': '∠', 'triangle': '△', 'circ': '∘'}
    keep_functions = {'sin', 'cos', 'tan', 'cot', 'sec', 'csc', 'arcsin', 'arccos', 'arctan', 'sinh', 'cosh', 'tanh', 'log', 'ln', 'lg', 'exp', 'lim', 'max', 'min'}
    
    def superscript_replacer(match):
        result = ''
        for char in match.group(1): result += superscript_map.get(char, char)
        return result
    def subscript_replacer(match):
        result = ''
        for char in match.group(1): result += subscript_map.get(char, char)
        return result
    
    text = re.sub(r'\\frac\{([^}]+)\}\{([^}]+)\}', r'(\1)/(\2)', text)
    text = re.sub(r'\\sqrt\{([^}]+)\}', r'√(\1)', text)
    text = re.sub(r'\\sqrt\[([^\]]+)\]\{([^}]+)\}', r'√[\1](\2)', text)
    for latex, unicode_char in greek_map.items(): 
        text = re.sub(r'\\' + latex + r'(?![a-zA-Z])', unicode_char, text)
    for latex, unicode_char in math_symbol_map.items(): 
        text = re.sub(r'\\' + latex + r'(?![a-zA-Z])', unicode_char, text)
    for func in keep_functions: 
        text = re.sub(r'\\' + func + r'(?![a-zA-Z])', func, text)
    text = re.sub(r'\\mathscr\{([^}]+)\}', r'\1', text)
    text = re.sub(r'\\mathbb\{([^}]+)\}', r'\1', text)
    text = re.sub(r'\\mathcal\{([^}]+)\}', r'\1', text)
    text = re.sub(r'\\mathbf\{([^}]+)\}', r'\1', text)
    text = re.sub(r'\\mathit\{([^}]+)\}', r'\1', text)
    text = re.sub(r'\^\{([^}]+)\}', superscript_replacer, text)
    text = re.sub(r'\^(\d)', lambda m: superscript_map.get(m.group(1), m.group(1)), text)
    text = re.sub(r'\^([a-zA-Z])', lambda m: superscript_map.get(m.group(1), m.group(1)), text)
    text = re.sub(r'\_\{([^}]+)\}', subscript_replacer, text)
    text = re.sub(r'\_(\d)', lambda m: subscript_map.get(m.group(1), m.group(1)), text)
    text = re.sub(r'\_([a-zA-Z])', lambda m: subscript_map.get(m.group(1), m.group(1)), text)
    text = re.sub(r'\\[a-zA-Z]+', '', text)
    text = text.replace('\\', '')
    text = re.sub(r'\{([^}]*)\}', r'\1', text)
    text = re.sub(r'\[([^\]]*)\]', r'\1', text)
    text = text.replace('$', '')
    text = re.sub(r'\s+', ' ', text)
    text = text.replace('#', '')
    return text.strip()

# ==================== 智能复习卡片系统 ====================
def calculate_next_review(proficiency, review_count=0):
    intervals = [1, 3, 7, 14, 30, 60]
    if review_count < len(intervals): return intervals[review_count]
    return 60

def get_todays_cards():
    all_cards = load_jsonl(REVIEW_CARDS_FILE)
    today = datetime.now().strftime("%Y-%m-%d")
    todays = []
    for card in all_cards:
        next_review = card.get("next_review", "")
        if not next_review or next_review <= today: todays.append(card)
    todays.reverse()
    return todays

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
            if correct:
                interval = calculate_next_review(proficiency, card["review_count"])
                card["next_review"] = (datetime.now() + timedelta(days=interval)).strftime("%Y-%m-%d")
            else:
                card["next_review"] = datetime.now().strftime("%Y-%m-%d")
            break
    save_jsonl(REVIEW_CARDS_FILE, cards)

def generate_review_cards(subject="数学", count=3):
    profile = load_user_profile()
    errors = load_jsonl(ERRORS_FILE)
    weak_know = [k for k, v in profile.get("weak_knowledge", {}).items() if k.startswith(f"{subject}-")]
    weak_know.sort(key=lambda k: profile["weak_knowledge"][k], reverse=True)
    weak_know = weak_know[:3]
    recent_errors = [e for e in errors if e.get("subject") == subject][-5:]
    
    if not weak_know and not recent_errors:
        return None
    
    error_context = ""
    if recent_errors:
        error_context = f"学生最近{subject}错题摘要：\n"
        for i, err in enumerate(recent_errors):
            error_context += f"{i+1}. 题目：{err.get('original', '无')[:100]}\n"
            error_context += f"   错误原因：{err.get('mistake', '无')[:50]}\n"
            error_context += f"   学生见解：{err.get('idea', '无')[:50]}\n"
    
    prompt = f"""你是一位高中{subject}老师，严格基于人教版{subject}教材命题。
请为高三学生生成{count}道{subject}学科的交互式复习题，以JSON数组格式输出。
每道题包含：type（填空/简答/选择）、question、answer、knowledge_point。
如果type是"选择"，请务必在question中列出所有选项，格式为"A. 选项内容 B. 选项内容 C. 选项内容 D. 选项内容"。
学生{subject}薄弱知识点：{', '.join(weak_know) if weak_know else '暂无，请基于下面错题自行判断'}
{error_context}
重要约束：
1. 所有题目必须是{subject}学科的，绝对禁止出现其他学科内容
2. 所有题目必须严格来自人教版高中{subject}教材，难度适合高三高考备考
3. 禁止出现任何大学知识或超纲内容
4. knowledge_point必须来自上面列出的薄弱知识点或错题中涉及的知识点
5. 题目难度根据薄弱程度调整：权重越高越基础，权重中等则出中等题
6. 必须保证题目和答案的数学/逻辑正确性，禁止出现自相矛盾或不符合事实的题目。
只输出JSON数组，不要额外解释。"""
    
    ai_config = load_ai_config()
    api_key = ai_config.get("api_key_free", "").strip()
    if not api_key:
        return None
    
    messages = [{"role": "user", "content": prompt}]
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": "glm-4-flash", "messages": messages, "temperature": 0.7, "max_tokens": 1000}
    
    try:
        resp = requests.post("https://open.bigmodel.cn/api/paas/v4/chat/completions", headers=headers, json=payload, timeout=30)
        if resp.status_code == 200:
            result = resp.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            try: 
                cards = json.loads(content)
            except:
                match = re.search(r'\[.*\]', content, re.DOTALL)
                if match:
                    try: 
                        cards = json.loads(match.group())
                    except: 
                        cards = None
                else:
                    cards = None
            if cards:
                for card in cards:
                    if "question" in card:
                        card["question"] = clean_latex(card["question"])
                    if "answer" in card:
                        card["answer"] = clean_latex(card["answer"])
            return cards
        return None
    except:
        return None

# ==================== 回收站 ====================
def move_to_recycle(item):
    recycle = load_jsonl(RECYCLE_FILE)
    recycle.append({"original_type": item.get("type"), "data": item, "delete_time": time.strftime("%Y-%m-%d %H:%M:%S"), "delete_ts": int(time.time())})
    save_jsonl(RECYCLE_FILE, recycle)

def delete_error_by_timestamp(timestamp):
    all_data, target, keep = load_jsonl(ERRORS_FILE), None, []
    for d in all_data:
        if d.get("timestamp") == timestamp: target = d
        else: keep.append(d)
    if target: move_to_recycle(target); save_jsonl(ERRORS_FILE, keep); return True
    return False

def delete_note_by_timestamp(timestamp):
    all_data, target, keep = load_jsonl(NOTES_FILE), None, []
    for d in all_data:
        if d.get("timestamp") == timestamp: target = d
        else: keep.append(d)
    if target: move_to_recycle(target); save_jsonl(NOTES_FILE, keep); return True
    return False

def restore_from_recycle(delete_ts):
    recycle, target, keep = load_jsonl(RECYCLE_FILE), None, []
    for item in recycle:
        if item.get("delete_ts", 0) == delete_ts: target = item
        else: keep.append(item)
    if target:
        save_jsonl(RECYCLE_FILE, keep)
        d, t = target.get("data", {}), target.get("original_type", "")
        if t == "error": errors = load_jsonl(ERRORS_FILE); errors.append(d); save_jsonl(ERRORS_FILE, errors)
        elif t == "note": notes = load_jsonl(NOTES_FILE); notes.append(d); save_jsonl(NOTES_FILE, notes)
        return True
    return False

def empty_recycle():
    save_jsonl(RECYCLE_FILE, [])

# ==================== 备份与恢复 ====================
def export_backup():
    zip_path = os.path.join(DATA_DIR, f"backup_{int(time.time())}.zip")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file in [ERRORS_FILE, NOTES_FILE, TASKS_FILE, RECYCLE_FILE, VOCAB_FILE, WORD_STUDY_FILE, REVIEW_CARDS_FILE, NEW_WORDS_FILE]:
            if os.path.exists(file): zf.write(file, os.path.basename(file))
        for dir_path in [IMAGES_DIR, VIDEOS_DIR, DOCS_DIR, CONTENT_LIB_DIR]:
            if os.path.exists(dir_path):
                for root, dirs, files in os.walk(dir_path):
                    for f in files: zf.write(os.path.join(root, f), os.path.join(os.path.basename(dir_path), f))
    return zip_path

def import_backup(zip_path):
    with zipfile.ZipFile(zip_path, 'r') as zf:
        with tempfile.TemporaryDirectory() as tmpdir:
            zf.extractall(tmpdir)
            for fname in [os.path.basename(ERRORS_FILE), os.path.basename(NOTES_FILE), os.path.basename(TASKS_FILE), os.path.basename(RECYCLE_FILE), os.path.basename(VOCAB_FILE), os.path.basename(WORD_STUDY_FILE), os.path.basename(REVIEW_CARDS_FILE), os.path.basename(NEW_WORDS_FILE)]:
                src = os.path.join(tmpdir, fname)
                if os.path.exists(src): shutil.copy2(src, os.path.join(DATA_DIR, fname))
            for dir_name in [os.path.basename(IMAGES_DIR), os.path.basename(VIDEOS_DIR), os.path.basename(DOCS_DIR), os.path.basename(CONTENT_LIB_DIR)]:
                src_dir = os.path.join(tmpdir, dir_name)
                dst_dir = os.path.join(DATA_DIR, dir_name)
                if os.path.exists(src_dir):
                    if os.path.exists(dst_dir): shutil.rmtree(dst_dir)
                    shutil.copytree(src_dir, dst_dir)

# ==================== 通用文件工具 ====================
def copy_file_to_lib(src_path, target_dir, allowed_exts):
    if not os.path.exists(src_path): return ""
    ext = os.path.splitext(src_path)[1].lower()
    if ext not in allowed_exts: return ""
    new_name = str(int(time.time() * 1000)) + ext
    dst = os.path.join(target_dir, new_name)
    shutil.copy(src_path, dst)
    return dst

IMG_EXTS = [".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp"]
VIDEO_EXTS = [".mp4", ".mov", ".avi", ".mkv", ".flv", ".wmv"]
DOC_EXTS = [".pdf", ".doc", ".docx", ".txt", ".md", ".ppt", ".pptx", ".xls", ".xlsx"]

# ==================== AI 配置管理 ====================
def load_ai_config():
    if not os.path.exists(AI_CONFIG_FILE):
        return {"model": "free", "api_key_free": "", "api_key_enhanced": "", "monthly_limit": 5.0, "subject_models": {}}
    with open(AI_CONFIG_FILE, "r", encoding="utf-8") as f:
        try:
            d = json.load(f)
            if "subject_models" not in d: d["subject_models"] = {}
            return d
        except: return {"model": "free", "api_key_free": "", "api_key_enhanced": "", "monthly_limit": 5.0, "subject_models": {}}

def save_ai_config(config):
    with open(AI_CONFIG_FILE, "w", encoding="utf-8") as f: json.dump(config, f, ensure_ascii=False, indent=2)

def load_ai_usage():
    if not os.path.exists(AI_USAGE_FILE):
        return {"month": time.strftime("%Y-%m"), "count": 0, "estimated_cost": 0.0, "subjects": {}}
    with open(AI_USAGE_FILE, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            if data.get("month") != time.strftime("%Y-%m"): return {"month": time.strftime("%Y-%m"), "count": 0, "estimated_cost": 0.0, "subjects": {}}
            if "subjects" not in data: data["subjects"] = {}
            return data
        except: return {"month": time.strftime("%Y-%m"), "count": 0, "estimated_cost": 0.0, "subjects": {}}

def save_ai_usage(usage):
    with open(AI_USAGE_FILE, "w", encoding="utf-8") as f: json.dump(usage, f, ensure_ascii=False, indent=2)

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

# ==================== 用户画像持久化 ====================
def load_user_profile():
    if not os.path.exists(USER_PROFILE_FILE):
        return {"name": "学生", "grade": "高三", "weak_subjects": {}, "weak_knowledge": {}, "error_types": {}, "learning_preferences": {"prefer_explanation_first": True, "prefer_step_by_step": True}, "recent_focus": [], "total_errors": 0, "total_chats": 0, "chat_subjects": {}, "content_lib_usage": {}, "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")}
    try:
        with open(USER_PROFILE_FILE, "r", encoding="utf-8") as f:
            profile = json.load(f)
            for key in ["weak_subjects", "weak_knowledge", "error_types", "recent_focus", "chat_subjects", "content_lib_usage"]:
                if key not in profile: profile[key] = {}
            for key in ["total_errors", "total_chats"]:
                if key not in profile: profile[key] = 0
            if "learning_preferences" not in profile: profile["learning_preferences"] = {"prefer_explanation_first": True, "prefer_step_by_step": True}
            return profile
    except: return {"name": "学生", "grade": "高三", "weak_subjects": {}, "weak_knowledge": {}, "error_types": {}, "learning_preferences": {"prefer_explanation_first": True, "prefer_step_by_step": True}, "recent_focus": [], "total_errors": 0, "total_chats": 0, "chat_subjects": {}, "content_lib_usage": {}, "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")}

def save_user_profile(profile):
    profile["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(USER_PROFILE_FILE, "w", encoding="utf-8") as f: json.dump(profile, f, ensure_ascii=False, indent=2)

def update_weak_subject(subject, weight_increment=0.1):
    profile = load_user_profile()
    profile["weak_subjects"][subject] = min(1.0, profile["weak_subjects"].get(subject, 0) + weight_increment)
    save_user_profile(profile)

def update_weak_knowledge(knowledge_point, weight_increment=0.1):
    profile = load_user_profile()
    profile["weak_knowledge"][knowledge_point] = min(1.0, profile["weak_knowledge"].get(knowledge_point, 0) + weight_increment)
    save_user_profile(profile)

def update_error_type(error_type):
    profile = load_user_profile()
    profile["error_types"][error_type] = profile["error_types"].get(error_type, 0) + 1
    profile["total_errors"] += 1
    save_user_profile(profile)

def update_chat_stats(subject):
    profile = load_user_profile()
    profile["total_chats"] += 1
    profile["chat_subjects"][subject] = profile["chat_subjects"].get(subject, 0) + 1
    save_user_profile(profile)

def add_recent_focus(knowledge_point):
    profile = load_user_profile()
    if knowledge_point not in profile["recent_focus"]:
        profile["recent_focus"].insert(0, knowledge_point)
        profile["recent_focus"] = profile["recent_focus"][:10]
        save_user_profile(profile)

def get_profile_summary():
    profile = load_user_profile()
    weak_subjs = sorted(profile["weak_subjects"].items(), key=lambda x: x[1], reverse=True)[:3]
    weak_know = sorted(profile["weak_knowledge"].items(), key=lambda x: x[1], reverse=True)[:5]
    summary = "【学生学习画像】\n"
    if weak_subjs: summary += f"薄弱学科（前3）：{'、'.join([f'{s}(权重{w:.1f})' for s,w in weak_subjs])}\n"
    if weak_know: summary += f"薄弱知识点（前5）：{'、'.join([f'{k}(权重{w:.1f})' for k,w in weak_know])}\n"
    if profile["recent_focus"]: summary += f"最近攻克：{'、'.join(profile['recent_focus'][:5])}\n"
    summary += f"总错题数：{profile['total_errors']} | 总对话数：{profile['total_chats']}\n"
    return summary

# ==================== 知识框架分析函数 ====================
def analyze_knowledge_framework():
    all_subjects = ["语文", "数学", "英语", "物理", "化学", "生物", "历史", "政治", "地理"]
    error_counts = {}
    all_errors = load_jsonl(ERRORS_FILE)
    for err in all_errors: error_counts[err.get("subject", "未知")] = error_counts.get(err.get("subject", "未知"), 0) + 1
    
    chat_counts = {}
    for subj in all_subjects:
        chat_file = get_chat_history_file(subj)
        chat_counts[subj] = len(load_jsonl(chat_file)) // 2 if os.path.exists(chat_file) else 0
    
    knowledge_stats = {}
    error_type_stats = {}
    for err in all_errors:
        for tag in err.get("tags", [])[1:]: knowledge_stats[tag] = knowledge_stats.get(tag, 0) + 1
        etype = err.get("error_type", "")
        if etype: error_type_stats[etype] = error_type_stats.get(etype, 0) + 1
    
    sorted_knowledge = sorted(knowledge_stats.items(), key=lambda x: x[1], reverse=True)[:10]
    sorted_error_types = sorted(error_type_stats.items(), key=lambda x: x[1], reverse=True)
    
    weaknesses = []
    for err in all_errors[-50:]:
        original = err.get("original", err.get("question", ""))
        if len(original) > 10: weaknesses.append({"subject": err.get("subject", "未知"), "source": "错题", "preview": original[:80] + ("..." if len(original) > 80 else "")})
    for subj in all_subjects:
        chat_file = get_chat_history_file(subj)
        if os.path.exists(chat_file):
            for msg in load_jsonl(chat_file)[-10:]:
                if msg["role"] == "user" and len(msg["content"]) > 10: weaknesses.append({"subject": subj, "source": "AI对话", "preview": msg["content"][:80] + ("..." if len(msg["content"]) > 80 else "")})
    
    sorted_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)
    weak_subjects = sorted_errors[:3] if sorted_errors else []
    
    profile = load_user_profile()
    profile["total_errors"] = len(all_errors)
    profile["total_chats"] = sum(chat_counts.values())
    for subj, cnt in error_counts.items(): profile["weak_subjects"][subj] = min(1.0, cnt * 0.05)
    save_user_profile(profile)
    
    content_stats = {subj: get_content_summary(subj) for subj in all_subjects}
    
    total_errors = len(all_errors)
    max_errors = max(error_counts.values()) if error_counts else 1
    weighted_subjects = {}
    for subj, count in error_counts.items():
        chat_count = chat_counts.get(subj, 0)
        weight = (count / max_errors) * 0.6 + (1 - min(chat_count, 20) / 20) * 0.4
        weighted_subjects[subj] = round(weight, 2)
    sorted_weighted = sorted(weighted_subjects.items(), key=lambda x: x[1], reverse=True)
    top_weak = sorted_weighted[:3]
    advice = "【优先学习建议】\n"
    if top_weak:
        advice += f"最需要加强：{top_weak[0][0]}（权重{top_weak[0][1]}）\n"
        if len(top_weak) > 1:
            advice += f"其次：{'、'.join([f'{s}({w})' for s,w in top_weak[1:]])}\n"
        advice += "建议：每天优先完成薄弱学科的复习卡片，再去问该科AI不懂的知识点。"
    
    return {"error_counts": error_counts, "chat_counts": chat_counts, "weaknesses": weaknesses[-15:], "weak_subjects": weak_subjects, "total_errors": total_errors, "total_chats": sum(chat_counts.values()), "knowledge_stats": sorted_knowledge, "error_type_stats": sorted_error_types, "content_stats": content_stats, "weighted_subjects": sorted_weighted, "advice": advice}

# ==================== 主程序 ====================
def main(page: ft.Page):
    page.title = "智能错题笔记助手"
    page.responsive = True
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window.width = 900
    page.window.height = 700
    page.window.min_width = 360
    page.window.min_height = 450

    def show_message(target_text, text, color="green"):
        target_text.value = text; target_text.color = color; page.update()
        def clear():
            time.sleep(2); target_text.value = ""; page.update()
        threading.Thread(target=clear, daemon=True).start()

    # ==================== 通用文件选择组件 ====================
    def make_file_picker_button(button_text, allowed_types="image"):
        selected_files = []
        file_list = ft.Column(spacing=4)
        picker = ft.FilePicker(on_result=lambda e: handle_picker_result(e))
        page.overlay.append(picker)
        
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
                page.snack_bar = ft.SnackBar(ft.Text(f"已添加 {len(e.files)} 个文件", color="green"))
                page.snack_bar.open = True
                page.update()
        
        def refresh_file_list():
            file_list.controls.clear()
            for idx, f_path in enumerate(selected_files):
                name = os.path.basename(f_path)
                ext = os.path.splitext(f_path)[1].lower()
                icon_text = "🖼️" if ext in IMG_EXTS else ("🎬" if ext in VIDEO_EXTS else "📄")
                def make_remove(idx2):
                    return lambda e: remove_file(idx2)
                row = ft.Row([
                    ft.Text(f"{icon_text} {name}", size=14, color=ft.colors.ON_SURFACE),
                    ft.TextButton(text="删除", on_click=make_remove(idx), style=ft.ButtonStyle(color=ft.colors.ERROR))
                ], spacing=8, alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                file_list.controls.append(row)
            page.update()
        
        def remove_file(idx):
            if 0 <= idx < len(selected_files):
                selected_files.pop(idx)
                refresh_file_list()
        
        def pick_files(e):
            if allowed_types == "image":
                picker.pick_files(
                    file_type=ft.FilePickerFileType.CUSTOM,
                    allowed_extensions=['jpg', 'jpeg', 'png', 'bmp', 'gif', 'webp'],
                    dialog_title="选择图片",
                    allow_multiple=True
                )
            elif allowed_types == "video":
                picker.pick_files(
                    file_type=ft.FilePickerFileType.CUSTOM,
                    allowed_extensions=['mp4', 'mov', 'avi', 'mkv', 'flv', 'wmv'],
                    dialog_title="选择视频",
                    allow_multiple=True
                )
            elif allowed_types == "document":
                picker.pick_files(
                    file_type=ft.FilePickerFileType.CUSTOM,
                    allowed_extensions=['pdf', 'doc', 'docx', 'txt', 'md', 'ppt', 'pptx', 'xls', 'xlsx'],
                    dialog_title="选择文档",
                    allow_multiple=True
                )
            else:
                picker.pick_files(
                    file_type=ft.FilePickerFileType.CUSTOM,
                    allowed_extensions=['jpg', 'jpeg', 'png', 'bmp', 'gif', 'webp', 'mp4', 'mov', 'avi', 'mkv', 'flv', 'wmv', 'pdf', 'doc', 'docx', 'txt', 'md', 'ppt', 'pptx', 'xls', 'xlsx'],
                    dialog_title="选择文件",
                    allow_multiple=True
                )
        
        button = ft.ElevatedButton(
            text=button_text,
            icon=ft.icons.ATTACH_FILE,
            on_click=pick_files,
            style=ft.ButtonStyle(padding=ft.padding.all(10))
        )
        return ft.Column([button, file_list], spacing=8), selected_files

    # ==================== 悬浮AI球 ====================
    AI_SUBJECTS = [("总AI", "🤖"), ("数学", "📐"), ("语文", "📜"), ("英语", "📝"), ("物理", "⚛️"), ("化学", "🧪"), ("生物", "🧬"), ("历史", "🏛️"), ("政治", "⚖️"), ("地理", "🌍")]

    contact_panel = ft.Container(visible=False, bgcolor=ft.colors.SURFACE_VARIANT, border_radius=16, padding=15, width=220, shadow=ft.BoxShadow(spread_radius=2, blur_radius=10, color="#30000000"))
    def close_contact_panel(e=None): contact_panel.visible = False; page.update()
    def open_contact_panel(e): contact_panel.right = 10; contact_panel.bottom = 76; contact_panel.visible = True; page.update()

    contact_list = ft.Column(spacing=8)
    for subj_name, subj_icon in AI_SUBJECTS:
        btn = ft.TextButton(text=f"{subj_icon} {subj_name}", on_click=lambda e, s=subj_name: open_chat(s), style=ft.ButtonStyle(color=ft.colors.ON_SURFACE_VARIANT))
        contact_list.controls.append(btn)
    contact_panel.content = ft.Column([ft.Text("🧠 AI 助手列表", size=18, weight=ft.FontWeight.BOLD, color=ft.colors.ON_SURFACE), ft.Divider(), contact_list], spacing=5)

    ai_ball = ft.Container(content=ft.Text("AI", size=20, color=ft.colors.ON_PRIMARY, weight=ft.FontWeight.BOLD), width=56, height=56, border_radius=28, bgcolor=ft.colors.PRIMARY, alignment=ft.alignment.center, shadow=ft.BoxShadow(spread_radius=2, blur_radius=8, color="#40000000"), on_click=lambda e: (close_contact_panel() if contact_panel.visible else open_contact_panel(e)))
    ball_container = ft.Container(content=ai_ball, right=10, bottom=10)

    chat_dialog = ft.Container(visible=False, left=20, top=20, right=20, bottom=20, bgcolor=ft.colors.SURFACE, border_radius=16, padding=20, shadow=ft.BoxShadow(spread_radius=2, blur_radius=10, color="#30000000"))
    current_chat_subject = "总AI"
    stop_flag = False
    generation_active = False

    def open_chat(subject):
        nonlocal current_chat_subject, stop_flag, generation_active
        if subject == current_chat_subject and generation_active:
            chat_dialog.visible = True
            page.update()
            return
        if generation_active:
            stop_flag = True
            time.sleep(0.2)
        generation_active = False
        stop_flag = False
        current_chat_subject = subject
        close_contact_panel()
        chat_dialog.content = build_chat_window(subject)
        chat_dialog.visible = True
        page.update()

    def call_ai_stream(messages, model_name, on_chunk):
        ai_config = load_ai_config()
        api_key = ai_config.get("api_key_free" if model_name == "free" else "api_key_enhanced", "").strip()
        model = "glm-4-flash" if model_name == "free" else "glm-4-air"
        if not api_key: on_chunk("❌ 未配置API密钥"); return
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {"model": model, "messages": messages, "temperature": 0.7, "max_tokens": 2048, "stream": True}
        try:
            resp = requests.post("https://open.bigmodel.cn/api/paas/v4/chat/completions", headers=headers, json=payload, stream=True, timeout=60)
            if resp.status_code != 200: on_chunk(f"❌ API错误 {resp.status_code}"); return
            accumulated = ""
            for line in resp.iter_lines(decode_unicode=True):
                if stop_flag: on_chunk(accumulated + "\n\n[生成已停止]"); break
                if not line or line.startswith(':') or line.strip() == '': continue
                if line.startswith('data: '):
                    data_str = line[6:]
                    if data_str.strip() == '[DONE]': break
                    try:
                        data = json.loads(data_str)
                        delta = data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                        if delta: accumulated += delta; on_chunk(clean_latex(accumulated))
                    except: continue
            return clean_latex(accumulated)
        except Exception as e: on_chunk(f"❌ 请求异常: {str(e)}"); return None

    def build_chat_window(subject):
        ai_config = load_ai_config()
        subj_models = ai_config.get("subject_models", {})
        current_model = subj_models.get(subject, ai_config.get("model", "free"))
        model_name = "GLM-4-Flash (免费)" if current_model == "free" else "GLM-4-Air (增强)"
        display_name = subject if subject != "总AI" else "总AI"

        base_teaching = "请多用类比、生活例子和图像化思维讲解，让学生真正理解，而不是死记硬背。一切以高考应试提分为目标，紧扣人教版教材。重要概念用**加粗**。"
        system_prompts = {
            "数学": f"你是一位经验丰富的高中数学老师，严格基于人教版高中数学教材。{base_teaching}请用分步骤的方式讲解，并用序号1. 2. 3.列出关键步骤。",
            "语文": f"你是一位资深高三语文老师，专攻高考语文（人教版）。{base_teaching}请重点围绕：1.古诗文默写与鉴赏；2.文言文实词、虚词、句式；3.作文素材、结构、审题立意；4.阅读理解答题模板与技巧。",
            "英语": f"你是一位专业的高中英语老师（人教版）。{base_teaching}请用列表形式列出语法要点和例句。",
            "物理": f"你是一位严谨的高中物理老师（人教版）。{base_teaching}请用分步骤方式讲解，公式用纯文本。",
            "化学": f"你是一位细致的高中化学老师（人教版）。{base_teaching}请用序号列出反应步骤，方程式用纯文本。",
            "生物": f"你是一位耐心的生物老师（人教版）。{base_teaching}请用分段方式解释概念。",
            "历史": f"你是一位博学的高中历史老师（人教版）。{base_teaching}请用时间线或分点方式梳理事件。关键时间、人物、事件请用**加粗**。",
            "政治": f"你是一位逻辑清晰的政治老师（人教版）。{base_teaching}请用分点方式讲解原理。",
            "地理": f"你是一位善于画图的地理老师（人教版）。{base_teaching}请用分段方式讲解知识点。",
            "总AI": f"你是学习总指挥，拥有全局视野。你每次回答必须做到以下四点：\n1. 先引用用户画像中的具体数据（薄弱学科、薄弱知识点、错误类型分布）作为判断依据\n2. 明确指出当前最需要加强的具体知识点（不是笼统学科名称，而是精确到如'二次函数区间最值''定语从句whose用法'这种粒度）\n3. 给出今日可执行的1-3个具体行动方案（如'去数学AI那里问一道关于XX的题目''完成3道XX类型的复习卡片'）\n4. 将相关任务分解到对应的分科AI去执行\n严禁笼统回复。{base_teaching}"
        }
        system_prompt = system_prompts.get(subject, f"请用结构化方式回答，{base_teaching}")

        custom_skill = load_custom_skill()
        if custom_skill:
            system_prompt = system_prompt + "\n\n【附加教学策略】\n" + custom_skill

        def show_full_dialog(content):
            dlg = ft.AlertDialog(
                title=ft.Text("完整消息"),
                content=ft.Container(
                    content=ft.Column([ft.Text(content, size=16)], scroll=ft.ScrollMode.AUTO),
                    width=450, height=350, padding=10
                ),
                actions=[ft.TextButton("关闭", on_click=lambda e: page.close(dlg))]
            )
            page.open(dlg)

        search_field = ft.TextField(hint_text="🔍 搜索对话记录...", on_change=lambda e: filter_history())
        history_list = ft.ListView(spacing=6, expand=True)
        
        def filter_history():
            history_list.controls.clear()
            query = search_field.value.strip().lower() if search_field.value else ""
            try:
                history = load_chat_history(subject)
            except:
                history = []
            for msg in history[-30:]:
                if query and query not in msg["content"].lower():
                    continue
                align = ft.MainAxisAlignment.END if msg["role"] == "user" else ft.MainAxisAlignment.START
                bg = "#DCF8C6" if msg["role"] == "user" else ft.colors.SURFACE_VARIANT
                time_raw = msg.get("time", "")
                time_str = time_raw[-8:-3] if len(time_raw) >= 8 else ""
                full_content = msg["content"]
                display_content = full_content[:80] + ("..." if len(full_content) > 80 else "")
                msg_container = ft.Container(
                    content=ft.Column([
                        ft.Text(display_content, size=16),
                        ft.Text(time_str, size=12, color=ft.colors.ON_SURFACE_VARIANT)
                    ], spacing=2),
                    padding=10,
                    border_radius=12,
                    bgcolor=bg,
                    expand=True,
                    on_click=lambda e, c=full_content: show_full_dialog(c)
                )
                history_list.controls.append(ft.Row([msg_container], alignment=align))
            page.update()
        
        filter_history()

        chat_input = ft.TextField(hint_text=f"向{display_name}提问...", expand=True, multiline=True, min_lines=1, max_lines=4)
        chat_file_picker, chat_files = make_file_picker_button("添加附件", allowed_types="all")
        send_stop_button = ft.IconButton(icon=ft.icons.SEND, on_click=lambda e: send_message(e), icon_color=ft.colors.PRIMARY)
        scroll_btn = ft.IconButton(icon=ft.icons.ARROW_DOWNWARD, tooltip="跳到底部", on_click=lambda e: scroll_to_bottom())

        def scroll_to_bottom(e=None):
            try: history_list.scroll_to(offset=-1, duration=300)
            except: pass
            page.update()

        quick_buttons = ft.Row([
            ft.TextButton("帮我分析这道题", on_click=lambda e: setattr(chat_input, 'value', "帮我分析这道题：") or chat_input.focus() or page.update()),
            ft.TextButton("这个知识点怎么理解", on_click=lambda e: setattr(chat_input, 'value', "这个知识点怎么理解？") or chat_input.focus() or page.update()),
            ft.TextButton("给我出一道同类题", on_click=lambda e: setattr(chat_input, 'value', "给我出一道同类题：") or chat_input.focus() or page.update()),
        ], spacing=5, scroll=ft.ScrollMode.AUTO, height=40)

        def toggle_subject_model():
            ai_config = load_ai_config()
            subj_models = ai_config.get("subject_models", {})
            old = subj_models.get(subject, ai_config.get("model", "free"))
            new_model = "enhanced" if old == "free" else "free"
            subj_models[subject] = new_model
            ai_config["subject_models"] = subj_models
            save_ai_config(ai_config)
            chat_dialog.content = build_chat_window(subject)
            show_message(home_msg, f"{display_name} 已切换到{'增强' if new_model == 'enhanced' else '免费'}模型", "blue")
            page.update()

        def close_chat(e):
            nonlocal stop_flag, generation_active
            chat_dialog.visible = False
            page.update()

        def send_message(e):
            nonlocal stop_flag, generation_active
            if generation_active:
                stop_flag = True
                generation_active = False
                send_stop_button.icon = ft.icons.SEND
                page.update()
                return
            text = chat_input.value.strip()
            if not text and not chat_files: return
            content = text
            if chat_files: content += "\n[附件: " + ", ".join([os.path.basename(f) for f in chat_files]) + "]"
            save_chat_message(subject, "user", content)
            update_chat_stats(subject)
            chat_input.value = ""; chat_files.clear()
            chat_file_picker.controls[-1].controls.clear()
            history_list.controls.append(ft.Row([ft.Container(content=ft.Text(content, size=16), padding=10, border_radius=12, bgcolor="#DCF8C6", expand=True)], alignment=ft.MainAxisAlignment.END))
            placeholder_text = ft.Text("⏳ 正在思考...", size=16)
            history_list.controls.append(ft.Row([ft.Container(content=placeholder_text, padding=10, border_radius=12, bgcolor=ft.colors.SURFACE_VARIANT, expand=True)], alignment=ft.MainAxisAlignment.START))
            save_chat_message(subject, "assistant", "⏳ 正在思考...")
            scroll_to_bottom()
            send_stop_button.icon = ft.icons.STOP
            generation_active = True
            page.update()
            stop_flag = False

            profile_summary = get_profile_summary()
            if subject == "总AI":
                framework = analyze_knowledge_framework()
                profile_summary += f"\n\n{framework['advice']}"
            related_errors = search_related_errors(subject, text, limit=3)
            error_context = ""
            if related_errors:
                error_context = "\n【用户相关错题历史】\n"
                for idx, err in enumerate(related_errors):
                    error_context += f"{idx+1}. 题目：{err.get('original', '无')[:60]}\n"
                    error_context += f"   标签：{' > '.join(err.get('tags', []))}\n"
                    if err.get("mistake"): error_context += f"   错误原因：{err['mistake'][:60]}\n"
                    if err.get("idea"): error_context += f"   用户见解：{err['idea'][:60]}\n"
            
            full_system_prompt = f"现在是{time.strftime('%Y年%m月%d日 %H:%M')}。\n{profile_summary}\n{error_context}\n\n{system_prompt}"
            messages = [{"role": "system", "content": full_system_prompt}]
            recent_history = load_chat_history(subject)[-10:]
            for msg in recent_history: messages.append({"role": msg["role"], "content": msg["content"]})

            def update_partial(text):
                placeholder_text.value = text
                history = load_chat_history(subject)
                if history and history[-1]["role"] == "assistant":
                    history[-1]["content"] = text
                    save_jsonl(get_chat_history_file(subject), history)
                scroll_to_bottom()
                page.update()

            def run_stream():
                nonlocal generation_active
                call_ai_stream(messages, current_model, update_partial)
                generation_active = False
                send_stop_button.icon = ft.icons.SEND
                page.update()

            threading.Thread(target=run_stream, daemon=True).start()

        return ft.Column([
            ft.Row([ft.Text(f"💬 {display_name}", size=20, weight=ft.FontWeight.BOLD), ft.Text(f"({model_name})", size=14, color=ft.colors.ON_SURFACE_VARIANT), ft.ElevatedButton("切换模型" if current_model == "free" else "切回免费", on_click=lambda e: toggle_subject_model(), height=30), ft.IconButton(icon=ft.icons.CLOSE, on_click=lambda e: close_chat(e))], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(), search_field, history_list, quick_buttons, chat_file_picker,
            ft.Row([chat_input, send_stop_button, scroll_btn], spacing=10),
        ], spacing=10, expand=True)

    chat_dialog.content = build_chat_window("总AI")

    # ==================== 首页（错题/笔记） ====================
    home_msg = ft.Text("", size=16)
    subject_dropdown = ft.Dropdown(label="选择科目", options=[ft.dropdown.Option(sub) for sub in ["语文","数学","英语","物理","化学","生物","历史","政治","地理"]])
    original_input = ft.TextField(label="📋 原题（粘贴搜题软件找到的原题，可选）", multiline=True, min_lines=3, max_lines=6)
    original_file_picker, original_files = make_file_picker_button("添加原题图片", allowed_types="image")
    answer_input = ft.TextField(label="✅ 标准答案（粘贴搜题软件找到的答案+解析，可选）", multiline=True, min_lines=3, max_lines=6)
    answer_file_picker, answer_files = make_file_picker_button("添加答案图片", allowed_types="image")
    mistake_input = ft.TextField(label="❌ 我错在哪了（哪个步骤不会、卡在哪里，可选）", multiline=True, min_lines=2, max_lines=4)
    idea_input = ft.TextField(label="💡 我的见解（深层反思总结，可选）", multiline=True, min_lines=3, max_lines=6)
    idea_file_picker, idea_files = make_file_picker_button("添加见解附件", allowed_types="all")

    camera_picker = ft.FilePicker(on_result=lambda e: handle_camera_result(e))
    page.overlay.append(camera_picker)
    camera_button = ft.ElevatedButton(text="📷 拍照录题", icon=ft.icons.CAMERA_ALT, on_click=lambda _: camera_picker.pick_files(file_type=ft.FilePickerFileType.CUSTOM, allowed_extensions=['jpg', 'jpeg', 'png'], dialog_title="拍照或选择图片"))

    def handle_camera_result(e: ft.FilePickerResultEvent):
        if not e.files: return
        f = e.files[0]
        img_name = f"{int(time.time() * 1000)}.jpg"
        dest = os.path.join(IMAGES_DIR, img_name)
        try:
            with open(f.path, "rb") as src_file: img_bytes = src_file.read()
            with open(dest, "wb") as dst_file: dst_file.write(img_bytes)
            original_files.append(dest)
            original_file_picker.controls[-1].controls.clear()
            for i, fp in enumerate(original_files):
                name = os.path.basename(fp)
                def make_remove(idx2): return lambda e: remove_original_file(idx2)
                row = ft.Row([ft.Text(f"🖼️ {name}", size=14), ft.TextButton(text="删除", on_click=make_remove(i), style=ft.ButtonStyle(color=ft.colors.ERROR))], spacing=8)
                original_file_picker.controls[-1].controls.append(row)
            page.snack_bar = ft.SnackBar(ft.Text(f"✅ 已添加图片：{img_name}", color="green"))
            page.snack_bar.open = True
            page.update()
        except Exception as ex:
            page.snack_bar = ft.SnackBar(ft.Text(f"❌ 拍照保存失败：{ex}", color="red"))
            page.snack_bar.open = True
            page.update()

    def remove_original_file(idx):
        if 0 <= idx < len(original_files):
            original_files.pop(idx)
            original_file_picker.controls[-1].controls.clear()
            for i, fp in enumerate(original_files):
                name = os.path.basename(fp)
                def make_remove(idx2): return lambda e: remove_original_file(idx2)
                row = ft.Row([ft.Text(f"🖼️ {name}", size=14), ft.TextButton(text="删除", on_click=make_remove(i), style=ft.ButtonStyle(color=ft.colors.ERROR))], spacing=8)
                original_file_picker.controls[-1].controls.append(row)
            page.update()

    def submit_error(e):
        subj = subject_dropdown.value
        orig = original_input.value; ans = answer_input.value; mistake = mistake_input.value; idea = idea_input.value
        if not subj: show_message(home_msg, "请先选择科目", "red")
        elif not orig and not original_files and not mistake: show_message(home_msg, "请至少输入原题或填写「我错在哪了」", "red")
        else:
            save_error(subj, orig, list(original_files), ans, list(answer_files), mistake, idea, list(idea_files))
            show_message(home_msg, f"已保存 {subj} 错题！", "green")
            original_input.value = ""; answer_input.value = ""; mistake_input.value = ""; idea_input.value = ""
            original_files.clear(); answer_files.clear(); idea_files.clear()
            original_file_picker.controls[-1].controls.clear(); answer_file_picker.controls[-1].controls.clear(); idea_file_picker.controls[-1].controls.clear()
            page.update()

    error_form = ft.Column([subject_dropdown, ft.Text("📋 原题", size=18, weight=ft.FontWeight.BOLD), original_input, original_file_picker, camera_button, ft.Text("✅ 标准答案", size=18, weight=ft.FontWeight.BOLD), answer_input, answer_file_picker, ft.Text("❌ 我错在哪了", size=18, weight=ft.FontWeight.BOLD), mistake_input, ft.Text("💡 我的见解", size=18, weight=ft.FontWeight.BOLD), idea_input, idea_file_picker, ft.ElevatedButton(text="提交错题", icon=ft.icons.SAVE, on_click=submit_error, style=ft.ButtonStyle(bgcolor=ft.colors.PRIMARY, color=ft.colors.ON_PRIMARY))], spacing=15)

    note_input = ft.TextField(label="笔记内容", multiline=True, min_lines=4, max_lines=8)
    note_file_picker, note_files = make_file_picker_button("添加笔记附件", allowed_types="all")
    def submit_note(e):
        subj, n = subject_dropdown.value, note_input.value
        if not subj: show_message(home_msg, "请先选择科目", "red")
        elif not n and not note_files: show_message(home_msg, "请输入笔记内容或添加文件", "red")
        else: save_note(subj, n, list(note_files)); show_message(home_msg, f"已保存 {subj} 笔记！", "green"); note_input.value = ""; note_files.clear(); note_file_picker.controls[-1].controls.clear(); page.update()
    note_form = ft.Column([subject_dropdown, note_input, note_file_picker, ft.ElevatedButton(text="提交笔记", icon=ft.icons.SAVE, on_click=submit_note, style=ft.ButtonStyle(bgcolor=ft.colors.SECONDARY, color=ft.colors.ON_SECONDARY))], spacing=15)

    home_form = ft.Container()
    def switch_home_tab(tab_name): home_form.content = error_form if tab_name == "错题" else note_form; page.update()
    home_tabs = ft.Row([ft.TextButton(text="错题", on_click=lambda e: switch_home_tab("错题"), style=ft.ButtonStyle(color=ft.colors.ON_SURFACE)), ft.TextButton(text="笔记", on_click=lambda e: switch_home_tab("笔记"), style=ft.ButtonStyle(color=ft.colors.ON_SURFACE))], spacing=10)
    home_page = ft.Column([ft.Text("📝 添加错题 / 笔记", size=24, weight=ft.FontWeight.BOLD), home_msg, home_tabs, home_form], spacing=15, scroll=ft.ScrollMode.AUTO)
    switch_home_tab("错题")

    # ==================== 学科页 ====================
    sub_msg = ft.Text("", size=16)
    detail_list = ft.Column(spacing=10)
    current_view_subject = None; current_view_type = None; current_tab = "错题本"
    filter_tag_dd = ft.Dropdown(label="标签筛选", hint_text="全部标签", expand=True, on_change=lambda e: on_subject_click(None, current_view_subject, current_tab))
    filter_error_dd = ft.Dropdown(label="错误类型", hint_text="全部类型", expand=True, on_change=lambda e: on_subject_click(None, current_view_subject, current_tab))
    sort_btn = ft.ElevatedButton("按时间倒序", icon=ft.icons.SWAP_VERT, on_click=lambda e: toggle_sort())
    current_sort = "time_desc"

    def get_filter_options():
        all_errors = load_jsonl(ERRORS_FILE)
        all_tags = set(); all_error_types = set()
        for err in all_errors:
            if current_view_subject and err.get("subject") != current_view_subject: continue
            for t in err.get("tags", []): all_tags.add(t)
            et = err.get("error_type", ""); 
            if et: all_error_types.add(et)
        return sorted(all_tags), sorted(all_error_types)

    def toggle_sort():
        nonlocal current_sort
        if current_sort == "time_desc": current_sort = "time_asc"; sort_btn.text = "按时间正序"
        elif current_sort == "time_asc": current_sort = "diff_desc"; sort_btn.text = "按难度高→低"
        elif current_sort == "diff_desc": current_sort = "diff_asc"; sort_btn.text = "按难度低→高"
        else: current_sort = "time_desc"; sort_btn.text = "按时间倒序"
        on_subject_click(None, current_view_subject, current_tab)

    vocab_list = load_vocabulary(); word_study = load_word_study()
    word_study_dict = {ws["word"]: ws for ws in word_study}
    search_input = ft.TextField(label="搜索单词", hint_text="输入单词...", expand=True, on_change=lambda e: refresh_vocab_view())
    vocab_view = ft.Column(spacing=6)

    def get_proficiency(word):
        ws = word_study_dict.get(word)
        if ws and "proficiency" in ws and ws["proficiency"] > 0: return ws["proficiency"]
        return None

    def update_proficiency(word, value):
        nonlocal word_study, word_study_dict
        ws_data = load_word_study(); found = False
        for ws in ws_data:
            if ws["word"] == word: ws["proficiency"] = value; found = True; break
        if not found: ws_data.append({"word": word, "proficiency": value, "last_review": "", "review_count": 0})
        save_word_study(ws_data); word_study = ws_data; word_study_dict = {ws["word"]: ws for ws in word_study}

    def refresh_vocab_view():
        vocab_view.controls.clear()
        query = search_input.value.strip().lower() if search_input.value else ""
        filtered = [w for w in vocab_list if query in w["word"].lower()] if query else vocab_list
        if not filtered: vocab_view.controls.append(ft.Text("  未找到匹配单词", size=16, color=ft.colors.ON_SURFACE_VARIANT))
        for w in filtered:
            prof = get_proficiency(w["word"])
            prof_text = f"掌握度: {prof}%" if prof is not None else "待评估"
            card = ft.Container(content=ft.Column([ft.Text(w["word"], size=18, weight=ft.FontWeight.W_500), ft.Text(w.get("phonetic", ""), size=14, color=ft.colors.ON_SURFACE_VARIANT), ft.Text(w.get("meaning", ""), size=16), ft.Text(prof_text, size=14, color=ft.colors.PRIMARY if prof and prof >= 50 else ft.colors.ORANGE)], spacing=4), padding=12, border_radius=12, bgcolor=ft.colors.SURFACE, shadow=ft.BoxShadow(spread_radius=1, blur_radius=4, color="#20000000"), on_click=lambda e, ww=w: show_word_detail(ww))
            vocab_view.controls.append(card)
        page.update()

    def find_word_in_vocab(word):
        for w in vocab_list:
            if w["word"].lower() == word.lower(): return w
        return None

    def open_word_or_tip(word):
        found = find_word_in_vocab(word)
        if found: show_word_detail(found)
        else: show_message(sub_msg, f"词库暂未收录「{word}」", "red")

    def parse_forms(forms_text):
        if not forms_text: return []
        parts = [p.strip() for p in forms_text.split(",") if p.strip()]
        words = []
        for part in parts:
            if ":" in part: part = part.split(":", 1)[1].strip()
            if part: words.append(part)
        return words

    def show_word_detail(word_data):
        word = word_data["word"]; prof = get_proficiency(word); prof_display = f"{prof}%" if prof is not None else "待评估"
        forms_text = word_data.get("forms", ""); form_words = parse_forms(forms_text)
        form_chips = []
        if form_words:
            for fw in form_words: form_chips.append(ft.Container(content=ft.Text(fw, size=14, color=ft.colors.PRIMARY), padding=ft.Padding(left=10, top=4, right=10, bottom=4), border_radius=16, bgcolor=ft.colors.PRIMARY_CONTAINER, on_click=lambda e, w=fw: open_word_or_tip(w)))
        grammar = word_data.get("grammar", {}); grammar_widgets = []
        if grammar:
            patterns = grammar.get("patterns", [])
            if patterns: grammar_widgets.append(ft.Text("📐 句型结构:", size=16, weight=ft.FontWeight.BOLD)); [grammar_widgets.append(ft.Container(content=ft.Text(p, size=14, color=ft.colors.ON_SURFACE), padding=ft.Padding(left=8, top=2, right=8, bottom=2), bgcolor=ft.colors.SURFACE_VARIANT, border_radius=4)) for p in patterns]
            collocations = grammar.get("collocations", [])
            if collocations: grammar_widgets.append(ft.Text("🔗 固定搭配:", size=16, weight=ft.FontWeight.BOLD)); [grammar_widgets.append(ft.Container(content=ft.Text(c, size=14, color=ft.colors.ON_SURFACE), padding=ft.Padding(left=8, top=2, right=8, bottom=2), bgcolor=ft.colors.SURFACE_VARIANT, border_radius=4)) for c in collocations]
            notes = grammar.get("notes", [])
            if notes: grammar_widgets.append(ft.Text("📝 语法要点:", size=16, weight=ft.FontWeight.BOLD)); [grammar_widgets.append(ft.Text(f"  • {n}", size=14, color=ft.colors.ON_SURFACE_VARIANT)) for n in notes]
            discrimination = grammar.get("discrimination", [])
            if discrimination: grammar_widgets.append(ft.Text("⚖️ 近义词辨析:", size=16, weight=ft.FontWeight.BOLD)); [grammar_widgets.append(ft.Text(f"  • {d}", size=14, color=ft.colors.ON_SURFACE_VARIANT)) for d in discrimination]
            test_points = grammar.get("test_points", [])
            if test_points: grammar_widgets.append(ft.Text("⭐ 常考考点:", size=16, weight=ft.FontWeight.BOLD)); [grammar_widgets.append(ft.Text(f"  • {tp}", size=14, color=ft.colors.ERROR)) for tp in test_points]
        
        def on_manual_adjust(e):
            dlg = ft.AlertDialog(title=ft.Text(f"手动调整熟练度 - {word}"), content=ft.Column([ft.Text(f"当前值: {prof_display}"), ft.TextField(label="输入0-100的数值", keyboard_type="number", autofocus=True)], spacing=10), actions=[ft.TextButton("取消", on_click=lambda e: page.close(dlg)), ft.TextButton("保存", on_click=lambda e: (update_proficiency(word, int(dlg.content.controls[1].value)), page.close(dlg), refresh_vocab_view(), show_word_detail(word_data)) if dlg.content.controls[1].value.isdigit() and 0 <= int(dlg.content.controls[1].value) <= 100 else None)])
            page.open(dlg)

        detail_col = ft.Column([ft.Text(f"音标: {word_data.get('phonetic', '')}", size=16), ft.Text(f"释义: {word_data.get('meaning', '')}", size=16), ft.Text(f"例句: {word_data.get('example', '')}", size=16, italic=True), ft.Divider()], spacing=6)
        if form_chips: detail_col.controls.append(ft.Text("变形/派生:", size=16, weight=ft.FontWeight.W_500)); detail_col.controls.append(ft.Row(form_chips, spacing=8, wrap=True)); detail_col.controls.append(ft.Divider())
        if grammar_widgets: detail_col.controls.extend(grammar_widgets); detail_col.controls.append(ft.Divider())
        detail_col.controls.append(ft.Row([ft.Text(f"AI评估熟练度: {prof_display}", size=16, weight=ft.FontWeight.BOLD), ft.IconButton(icon=ft.icons.EDIT, tooltip="手动纠偏", on_click=on_manual_adjust)], spacing=10))
        detail_card = ft.AlertDialog(title=ft.Text(word, size=22, weight=ft.FontWeight.BOLD), content=ft.Container(content=ft.Column([detail_col], scroll=ft.ScrollMode.AUTO, expand=True), width=500, height=500, padding=10), actions=[ft.TextButton("关闭", on_click=lambda e: page.close(detail_card))])
        page.open(detail_card)

    refresh_vocab_view()
    vocab_page = ft.Column([search_input, vocab_view], spacing=10)

    new_words_view = ft.Column(spacing=6)
    def refresh_new_words():
        new_words_view.controls.clear()
        new_words = load_new_words()
        if not new_words: new_words_view.controls.append(ft.Text("  暂无收集的生词", size=16, color=ft.colors.ON_SURFACE_VARIANT))
        else:
            for item in new_words[:30]:
                word = item.get("word", ""); count = item.get("count", 0)
                new_words_view.controls.append(ft.Text(f"  📝 {word} (出现{count}次)", size=16))
        page.update()
    def collect_words_action(e):
        new_words = collect_new_words(); save_new_words(new_words); refresh_new_words()
        show_message(sub_msg, f"已收集{len(new_words)}个生词", "green")
    new_words_section = ft.Column([ft.Row([ft.Text("🆕 生词表", size=18, weight=ft.FontWeight.BOLD), ft.TextButton("刷新收集", on_click=collect_words_action)]), new_words_view], spacing=6)

    # ==================== 智能复习区（完全重写，使用 data 传递状态） ====================
    review_subject_dropdown = ft.Dropdown(label="选择科目", options=[ft.dropdown.Option(sub) for sub in ["数学","语文","英语","物理","化学","生物","历史","政治","地理"]], value="数学")
    review_card_list = ft.ListView(spacing=10, expand=True, auto_scroll=False)
    review_status = ft.Text("", size=16)

    def refresh_review_view():
        review_card_list.controls.clear()
        cards = get_todays_cards()
        if not cards:
            review_card_list.controls.append(ft.Container(content=ft.Text("  今日暂无复习卡片", size=16, color=ft.colors.ON_SURFACE_VARIANT), padding=10))
        else:
            for card in cards:
                card_id = card.get("id", str(random.randint(1000, 9999)))
                q_text = card.get("question", "无题目")
                a_text = card.get("answer", "")
                kp = card.get("knowledge_point", "")
                ctype = card.get("type", "简答")
                is_choice = ctype == "选择"

                card_state = {
                    "submitted": False,
                    "selected": "",
                    "answer_text": a_text,
                    "kp": kp,
                    "options": [],
                    "choice_buttons": [],
                    "result_text": None,
                    "knowledge_tip": None,
                    "answer_btn": None,
                    "submit_btn": None,
                    "answer_input": None,
                    "choice_column": None,
                }

                if is_choice:
                    border_color, bg_color = ft.colors.BLUE_200, ft.colors.BLUE_50
                elif ctype == "填空":
                    border_color, bg_color = ft.colors.GREEN_200, ft.colors.GREEN_50
                else:
                    border_color, bg_color = ft.colors.ORANGE_200, ft.colors.ORANGE_50

                choice_column = ft.Column(spacing=6, visible=False)
                answer_input = ft.TextField(label="你的答案", multiline=True, min_lines=1, max_lines=3, disabled=True, visible=not is_choice)
                result_text = ft.Text("", size=14)
                knowledge_tip = ft.Text("", size=14, color=ft.colors.ON_SURFACE_VARIANT, visible=False)
                answer_btn = ft.ElevatedButton("作答", visible=True)
                submit_btn = ft.ElevatedButton("提交", visible=False)

                options = []
                choice_buttons = []
                if is_choice:
                    matches = re.findall(r'([A-D])[\.\、\s]\s*(.+?)(?=[A-D][\.\、\s]|$)', q_text)
                    if matches:
                        options = [(m[0], m[1].strip()) for m in matches]
                    else:
                        try:
                            ans_data = json.loads(a_text)
                            if isinstance(ans_data, dict) and "options" in ans_data:
                                options = [(opt[0], opt[1]) for opt in ans_data["options"]]
                                a_text = ans_data.get("correct", a_text)
                        except:
                            pass
                    if not options:
                        options = [("A", "A"), ("B", "B"), ("C", "C"), ("D", "D")]

                    for letter, opt_text in options:
                        btn = ft.TextButton(
                            text=f"{letter}. {opt_text}",
                            data={"letter": letter, "state": card_state},
                            on_click=on_option_click,
                            style=ft.ButtonStyle(color=ft.colors.ON_SURFACE, bgcolor=ft.colors.SURFACE_VARIANT)
                        )
                        choice_buttons.append(btn)
                        choice_column.controls.append(btn)
                    choice_column.visible = True
                    answer_input.visible = False

                    card_state["options"] = options
                    card_state["choice_buttons"] = choice_buttons

                card_state["answer_text"] = a_text
                card_state["result_text"] = result_text
                card_state["knowledge_tip"] = knowledge_tip
                card_state["answer_btn"] = answer_btn
                card_state["submit_btn"] = submit_btn
                card_state["answer_input"] = answer_input
                card_state["choice_column"] = choice_column
                card_state["card_id"] = card_id
                card_state["is_choice"] = is_choice

                def enable_answer(e, state=card_state):
                    if state["is_choice"]:
                        state["selected"] = ""
                        state["result_text"].value = ""
                        state["result_text"].color = ft.colors.ON_SURFACE
                        for btn in state["choice_buttons"]:
                            btn.disabled = False
                            btn.style = ft.ButtonStyle(bgcolor=ft.colors.SURFACE_VARIANT, color=ft.colors.ON_SURFACE)
                            btn.update()
                    else:
                        state["answer_input"].disabled = False
                        state["answer_input"].focus()
                    state["answer_btn"].visible = False
                    state["submit_btn"].visible = True
                    page.update()

                answer_btn.on_click = enable_answer

                def make_submit(state):
                    def submit(e):
                        if state["submitted"]:
                            return
                        is_ch = state["is_choice"]
                        user_ans = state["selected"].strip() if is_ch else state["answer_input"].value.strip()
                        if not user_ans:
                            state["result_text"].value = "请输入答案"
                            state["result_text"].color = ft.colors.ORANGE
                            page.update()
                            return
                        state["submitted"] = True
                        correct_ans = state["answer_text"].upper().strip()
                        correct = user_ans.upper() == correct_ans

                        if is_ch:
                            for i, btn in enumerate(state["choice_buttons"]):
                                btn.disabled = True
                                opt_letter = state["options"][i][0] if i < len(state["options"]) else ""
                                if correct:
                                    if opt_letter == correct_ans:
                                        btn.style = ft.ButtonStyle(bgcolor=ft.colors.GREEN_400, color=ft.colors.WHITE)
                                    else:
                                        btn.style = ft.ButtonStyle(bgcolor=ft.colors.SURFACE_VARIANT, color=ft.colors.ON_SURFACE)
                                else:
                                    if opt_letter == correct_ans:
                                        btn.style = ft.ButtonStyle(bgcolor=ft.colors.GREEN_400, color=ft.colors.WHITE)
                                    elif opt_letter == user_ans.upper():
                                        btn.style = ft.ButtonStyle(bgcolor=ft.colors.RED_400, color=ft.colors.WHITE)
                                    else:
                                        btn.style = ft.ButtonStyle(bgcolor=ft.colors.SURFACE_VARIANT, color=ft.colors.ON_SURFACE)
                                btn.update()
                        else:
                            state["answer_input"].disabled = True

                        if correct:
                            state["result_text"].value = "✅ 正确！"
                            state["result_text"].color = ft.colors.GREEN
                            update_review_card(state["card_id"], 80, True)
                        else:
                            state["result_text"].value = f"❌ 正确答案：{state['answer_text']}"
                            state["result_text"].color = ft.colors.ERROR
                            if state["kp"]:
                                state["knowledge_tip"].value = f"📚 知识点：{state['kp']}"
                                state["knowledge_tip"].visible = True
                            update_review_card(state["card_id"], 50, False)

                        state["answer_btn"].visible = False
                        state["submit_btn"].visible = False
                        page.update()
                    return submit

                submit_btn.on_click = make_submit(card_state)

                card_container = ft.Container(
                    content=ft.Column([
                        ft.Row([ft.Text(f"[{ctype}]", size=14, color=border_color, weight=ft.FontWeight.BOLD), ft.Text(kp, size=14, color=ft.colors.ON_SURFACE_VARIANT)]),
                        ft.Text(q_text, size=16, weight=ft.FontWeight.W_500),
                        answer_input, choice_column,
                        ft.Row([answer_btn, submit_btn], spacing=10),
                        result_text, knowledge_tip,
                    ], spacing=8),
                    padding=14, border_radius=14, border=ft.border.all(2, border_color), bgcolor=bg_color,
                    shadow=ft.BoxShadow(spread_radius=1, blur_radius=4, color="#20000000"),
                )
                review_card_list.controls.append(card_container)
        page.update()

    def on_option_click(e):
        btn = e.control
        state = btn.data["state"]
        letter = btn.data["letter"]
        if state["selected"] == letter:
            state["selected"] = ""
            state["result_text"].value = ""
            state["result_text"].color = ft.colors.ON_SURFACE
        else:
            state["selected"] = letter
            state["result_text"].value = f"已选择: {letter}"
            state["result_text"].color = ft.colors.PRIMARY

        for i, b in enumerate(state["choice_buttons"]):
            opt_letter = state["options"][i][0]
            if opt_letter == state["selected"]:
                b.style = ft.ButtonStyle(bgcolor=ft.colors.GREEN_400, color=ft.colors.WHITE)
            else:
                b.style = ft.ButtonStyle(bgcolor=ft.colors.SURFACE_VARIANT, color=ft.colors.ON_SURFACE)
            b.update()
        page.update()

    def generate_new_cards(e):
        subj = review_subject_dropdown.value
        if not subj: show_message(review_status, "请先选择科目", "red"); return
        review_status.value = "⏳ AI正在生成卡片..."; review_status.color = ft.colors.ORANGE; page.update()
        def generate():
            cards = generate_review_cards(subj, 3)
            if cards is None:
                review_status.value = "❌ 未配置API密钥"; review_status.color = ft.colors.ERROR; page.update(); return
            if not cards:
                review_status.value = "❌ 生成失败"; review_status.color = ft.colors.ERROR; page.update(); return
            for c in cards:
                card_data = {"id": str(random.randint(10000, 99999)), "subject": subj, "type": c.get("type", "简答"), "question": c.get("question", ""), "answer": c.get("answer", ""), "knowledge_point": c.get("knowledge_point", ""), "proficiency": 0, "review_count": 0, "next_review": datetime.now().strftime("%Y-%m-%d"), "created": time.strftime("%Y-%m-%d %H:%M:%S")}
                add_review_card(card_data)
            review_status.value = f"✅ 已生成{len(cards)}张卡片"; review_status.color = ft.colors.GREEN; refresh_review_view()
        threading.Thread(target=generate, daemon=True).start()

    review_page = ft.Column([
        ft.Text("🧠 智能复习", size=24, weight=ft.FontWeight.BOLD),
        ft.Row([review_subject_dropdown, ft.ElevatedButton("生成卡片", on_click=generate_new_cards, icon=ft.icons.AUTO_AWESOME)], spacing=10),
        review_status, ft.Divider(),
        ft.Text("📝 今日复习任务", size=20, weight=ft.FontWeight.BOLD),
        ft.Container(content=review_card_list, expand=True),
    ], spacing=15, expand=True)
    refresh_review_view()

    def show_detail_dialog(item, content_type):
        ts = item.get("timestamp"); time_str = item.get("time", "未知时间")
        if content_type == "错题本":
            is_error = True; title_text = item.get("original", item.get("question", "无题目"))[:60]
            full_original = item.get("original", item.get("question", "")); full_answer = item.get("answer", ""); full_mistake = item.get("mistake", ""); full_idea = item.get("idea", "")
            tags = item.get("tags", []); error_type = item.get("error_type", ""); deep = item.get("deep_analysis", "")
            all_media = (item.get("original_media", []) + item.get("answer_media", []) + item.get("idea_media", []))
        else:
            is_error = False; title_text = item.get("content", "无内容")[:60]
            full_original = item.get("content", ""); full_answer = ""; full_mistake = ""; full_idea = ""; tags = []; error_type = ""; deep = ""; all_media = item.get("media", [])
        
        content_col = ft.Column([ft.Text(f"🕒 {time_str}", size=14, color=ft.colors.ON_SURFACE_VARIANT)], spacing=4)
        if is_error:
            if tags: content_col.controls.append(ft.Text(f"🏷️ 标签：{' > '.join(tags)}", size=14, color=ft.colors.PRIMARY))
            if error_type: content_col.controls.append(ft.Text(f"⚠️ 错误类型：{error_type}", size=14, color=ft.colors.ORANGE))
            if full_original: content_col.controls.append(ft.Text("📋 原题：", size=16, weight=ft.FontWeight.BOLD)); content_col.controls.append(ft.Text(full_original, size=16))
            if full_answer: content_col.controls.append(ft.Text("✅ 标准答案：", size=16, weight=ft.FontWeight.BOLD)); content_col.controls.append(ft.Text(full_answer, size=16))
            if full_mistake: content_col.controls.append(ft.Text("❌ 我错在哪了：", size=16, weight=ft.FontWeight.BOLD)); content_col.controls.append(ft.Text(full_mistake, size=16))
            if full_idea: content_col.controls.append(ft.Text("💡 我的见解：", size=16, weight=ft.FontWeight.BOLD)); content_col.controls.append(ft.Text(full_idea, size=16))
            if deep: content_col.controls.append(ft.Text("🧠 AI深度分析：", size=16, weight=ft.FontWeight.BOLD)); content_col.controls.append(ft.Text(deep, size=16, color=ft.colors.PRIMARY))
        else:
            content_col.controls.extend([ft.Text("📝 内容：", size=16, weight=ft.FontWeight.BOLD), ft.Text(full_original, size=16)])
        if all_media:
            content_col.controls.append(ft.Text("📎 附件：", size=16, weight=ft.FontWeight.BOLD))
            for p in all_media:
                ext = os.path.splitext(p)[1].lower(); icon = "🖼️" if ext in IMG_EXTS else ("🎬" if ext in VIDEO_EXTS else "📄")
                content_col.controls.append(ft.Text(f"  {icon} {os.path.basename(p)}", size=14, color=ft.colors.ON_SURFACE_VARIANT))
        
        def confirm_delete(e):
            page.close(dialog)
            if is_error: delete_error_by_timestamp(ts)
            else: delete_note_by_timestamp(ts)
            on_subject_click(None, item.get("subject"), content_type); show_message(sub_msg, "已移入回收站", "green")
        delete_btn = ft.TextButton(text="删除", on_click=confirm_delete, style=ft.ButtonStyle(color=ft.colors.ERROR))
        dialog = ft.AlertDialog(title=ft.Text(title_text, size=18, weight=ft.FontWeight.BOLD), content=ft.Container(content=content_col, width=500, height=400, padding=10), actions=[ft.TextButton("关闭", on_click=lambda e: page.close(dialog)), delete_btn])
        page.open(dialog)

    def on_subject_click(e, subject_name, content_type):
        nonlocal current_view_subject, current_view_type
        if subject_name: current_view_subject = subject_name
        if content_type: current_view_type = content_type
        items = get_errors_by_subject(subject_name) if content_type == "错题本" else get_notes_by_subject(subject_name)
        filter_tag = filter_tag_dd.value; filter_error = filter_error_dd.value
        if filter_tag and filter_tag != "全部": items = [it for it in items if filter_tag in it.get("tags", [])]
        if filter_error and filter_error != "全部": items = [it for it in items if it.get("error_type") == filter_error]
        if current_sort == "time_asc": items.sort(key=lambda x: x.get("timestamp", 0))
        elif current_sort == "diff_desc": items.sort(key=lambda x: x.get("difficulty", 0), reverse=True)
        elif current_sort == "diff_asc": items.sort(key=lambda x: x.get("difficulty", 0))
        else: items.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
        
        detail_list.controls.clear()
        if not items: detail_list.controls.append(ft.Text(f"  暂无符合条件的内容", size=16, color=ft.colors.ON_SURFACE_VARIANT))
        else:
            for item in items:
                preview = item.get("original", item.get("question", item.get("content", "")))[:60]
                media_count = len(item.get("original_media", [])) + len(item.get("answer_media", [])) + len(item.get("idea_media", [])) if content_type == "错题本" else len(item.get("media", []))
                time_str = item.get("time", "")[:10]; tags = item.get("tags", [])
                tag_str = f"🏷️ {' > '.join(tags[1:])}" if len(tags) > 1 else ""
                card = ft.Container(content=ft.Column([ft.Text(preview + ("..." if len(preview) >= 60 else ""), size=16, weight=ft.FontWeight.W_500), ft.Row([ft.Text(time_str, size=13, color=ft.colors.ON_SURFACE_VARIANT), ft.Text(tag_str, size=13, color=ft.colors.PRIMARY) if tag_str else ft.Text(""), ft.Text(f"📎 ×{media_count}", size=13, color=ft.colors.ON_SURFACE_VARIANT) if media_count > 0 else ft.Text("")], spacing=10)], spacing=4), padding=12, border_radius=12, bgcolor=ft.colors.SURFACE, shadow=ft.BoxShadow(spread_radius=1, blur_radius=4, color="#20000000"), on_click=lambda e, it=item, ct=content_type: show_detail_dialog(it, ct))
                detail_list.controls.append(card)
        show_message(sub_msg, f"已加载 {subject_name} 的{content_type}（{len(items)}条）", "blue")
        if content_type == "错题本":
            all_tags, all_error_types = get_filter_options()
            filter_tag_dd.options = [ft.dropdown.Option("全部")] + [ft.dropdown.Option(t) for t in all_tags]
            filter_error_dd.options = [ft.dropdown.Option("全部")] + [ft.dropdown.Option(t) for t in all_error_types]
        page.update()

    def build_subject_list(content_type):
        subjects = ["语文","数学","英语","物理","化学","生物","历史","政治","地理"]
        return ft.Column([ft.Container(content=ft.Text(subj, size=18), on_click=lambda e, s=subj, t=content_type: on_subject_click(e, s, t), padding=12, border_radius=8, bgcolor=ft.colors.SURFACE_VARIANT) for subj in subjects], spacing=8)

    subject_list = ft.Column(spacing=10)
    filter_row = ft.Row([filter_tag_dd, filter_error_dd, sort_btn], spacing=10, visible=False)

    def show_subjects(content_type):
        nonlocal current_tab; current_tab = content_type; detail_list.controls.clear(); filter_row.visible = (content_type == "错题本")
        if content_type == "单词本": subject_list.controls.clear(); subject_list.controls.append(ft.Column([ft.Container(content=ft.Text("英语", size=18), padding=12, border_radius=8, bgcolor=ft.colors.SURFACE_VARIANT)], spacing=8)); detail_list.controls.append(vocab_page)
        elif content_type == "智能复习": subject_list.controls.clear(); detail_list.controls.append(review_page)
        else: detail_list.controls.append(ft.Text("  ← 点击左侧科目查看详情", size=16, color=ft.colors.ON_SURFACE_VARIANT)); subject_list.controls.clear(); subject_list.controls.append(build_subject_list(content_type))
        page.update()

    subject_tabs = ft.Row([ft.TextButton(text="错题本", on_click=lambda e: show_subjects("错题本")), ft.TextButton(text="笔记本", on_click=lambda e: show_subjects("笔记本")), ft.TextButton(text="单词本", on_click=lambda e: show_subjects("单词本")), ft.TextButton(text="智能复习", on_click=lambda e: show_subjects("智能复习"))], spacing=10)
    subject_page = ft.Column([ft.Text("📚 学科浏览", size=24, weight=ft.FontWeight.BOLD), sub_msg, subject_tabs, filter_row, ft.Row([ft.Container(content=subject_list, width=120), ft.Container(content=detail_list, expand=True)], expand=True, spacing=10)], spacing=15, scroll=ft.ScrollMode.AUTO)
    show_subjects("错题本")

    # ==================== 我的页 ====================
    mine_msg = ft.Text("", size=16)
    def show_knowledge_framework(e):
        data = analyze_knowledge_framework()
        advice_section = ft.Text(data.get("advice", ""), size=16, color=ft.colors.PRIMARY)
        weight_bars = []
        for subj, weight in data.get("weighted_subjects", [])[:5]:
            color = ft.colors.ERROR if weight >= 0.7 else (ft.colors.ORANGE if weight >= 0.4 else ft.colors.GREEN)
            weight_bars.append(ft.Column([ft.Text(f"{subj}：权重 {weight}", size=16), ft.ProgressBar(value=weight, width=300, color=color)], spacing=4))
        weak_bars = []
        for subj, count in data["error_counts"].items():
            max_count = max(data["error_counts"].values()) if data["error_counts"] else 1
            weak_bars.append(ft.Column([ft.Text(f"{subj}：{count} 条错题", size=16), ft.ProgressBar(value=count/max_count if max_count > 0 else 0, width=300, color=ft.colors.ORANGE)], spacing=4))
        
        dlg = ft.AlertDialog(title=ft.Text("知识框架"), content=ft.Container(content=ft.Column([ft.Text("📊 学习画像", size=22, weight=ft.FontWeight.BOLD), ft.Text(f"📝 总错题数：{data['total_errors']}   |   💬 总对话数：{data['total_chats']}", size=16), ft.Divider(), advice_section, ft.Text("⚖️ 学科加权分析", size=18, weight=ft.FontWeight.BOLD), *weight_bars, ft.Text("🔴 各学科错题分布", size=18, weight=ft.FontWeight.BOLD), *weak_bars], spacing=10, scroll=ft.ScrollMode.AUTO), width=550, height=550, padding=10), actions=[ft.TextButton("关闭", on_click=lambda e: page.close(dlg))])
        page.open(dlg)

    def refresh_tasks():
        task_list.controls.clear()
        tasks = load_jsonl(TASKS_FILE)
        if not tasks:
            task_list.controls.append(ft.Text("  暂无学习任务", size=16, color=ft.colors.ON_SURFACE_VARIANT))
        else:
            for task in tasks:
                is_done = task.get("done", False)
                text = task.get("text", "")
                def toggle_task(e, t=task):
                    t["done"] = not t.get("done", False)
                    all_tasks = load_jsonl(TASKS_FILE)
                    for d in all_tasks:
                        if d.get("created") == t.get("created"): d["done"] = t["done"]; break
                    save_jsonl(TASKS_FILE, all_tasks); refresh_tasks()
                def delete_task(e, t=task):
                    all_tasks = load_jsonl(TASKS_FILE)
                    save_jsonl(TASKS_FILE, [d for d in all_tasks if d.get("created") != t.get("created")])
                    refresh_tasks()
                style = ft.TextStyle(decoration=ft.TextDecoration.LINE_THROUGH) if is_done else None
                task_list.controls.append(ft.Row([ft.Checkbox(value=is_done, on_change=toggle_task), ft.Text(text, size=16, expand=True, style=style), ft.TextButton("删除", on_click=delete_task)], spacing=10))
        page.update()

    new_task_input = ft.TextField(label="新学习任务", expand=True)
    def add_task(e):
        text = new_task_input.value.strip()
        if text:
            tasks = load_jsonl(TASKS_FILE)
            tasks.append({"text": text, "done": False, "created": time.strftime("%Y-%m-%d %H:%M:%S")})
            save_jsonl(TASKS_FILE, tasks)
            new_task_input.value = ""
            refresh_tasks()
            page.update()

    task_list = ft.Column(spacing=6)
    task_section = ft.Column([ft.Text("✅ 学习任务清单", size=20, weight=ft.FontWeight.BOLD), ft.Row([new_task_input, ft.ElevatedButton("添加", on_click=add_task)], spacing=10), task_list], spacing=10)

    recycle_filter = "全部"
    def set_recycle_filter(value):
        nonlocal recycle_filter; recycle_filter = value
        refresh_recycle_list()

    def refresh_recycle_list():
        recycle_list.controls.clear(); items = load_jsonl(RECYCLE_FILE)
        if not items: recycle_list.controls.append(ft.Text("  回收站为空", size=16, color=ft.colors.ON_SURFACE_VARIANT))
        else:
            for item in reversed(items):
                original_type = item.get("original_type", "")
                if recycle_filter == "错题" and original_type != "error": continue
                if recycle_filter == "笔记" and original_type != "note": continue
                data = item.get("data", {}); subject = data.get("subject", "未知")
                preview = data.get("original", data.get("question", data.get("content", "")))[:40]
                ts = item.get("delete_ts", 0); type_tag = "📝" if original_type == "error" else "📘"
                recycle_list.controls.append(ft.Row([ft.Text(f"{type_tag} [{subject}] {preview}", size=16, expand=True), ft.TextButton("恢复", on_click=lambda e, t=ts: restore_item(t))], spacing=10))
        page.update()

    def restore_item(delete_ts):
        if restore_from_recycle(delete_ts): show_message(mine_msg, "已恢复", "green"); set_recycle_filter(recycle_filter)
        else: show_message(mine_msg, "恢复失败", "red")

    recycle_list = ft.Column(spacing=6)
    recycle_section = ft.Column([ft.Text("🗑️ 回收站", size=20, weight=ft.FontWeight.BOLD), ft.Row([ft.TextButton("全部", on_click=lambda e: set_recycle_filter("全部")), ft.TextButton("错题", on_click=lambda e: set_recycle_filter("错题")), ft.TextButton("笔记", on_click=lambda e: set_recycle_filter("笔记"))], spacing=10), recycle_list, ft.ElevatedButton("清空回收站", on_click=lambda e: [empty_recycle(), set_recycle_filter(recycle_filter), show_message(mine_msg, "回收站已清空", "green")], style=ft.ButtonStyle(color=ft.colors.ERROR))], spacing=10)

    ai_config = load_ai_config(); ai_usage = load_ai_usage()
    model_label = ft.Text(f"当前模型：{'GLM-4-Flash (免费)' if ai_config['model'] == 'free' else 'GLM-4-Air (增强)'}", size=16)
    cost_label = ft.Text(f"本月调用次数：{ai_usage['count']}  估算费用：¥{ai_usage['estimated_cost']:.4f}", size=14, color=ft.colors.ON_SURFACE_VARIANT)
    def on_switch_model(e):
        ai_config = load_ai_config(); ai_config["model"] = "enhanced" if ai_config["model"] == "free" else "free"; save_ai_config(ai_config)
        model_label.value = f"当前模型：{'GLM-4-Flash (免费)' if ai_config['model'] == 'free' else 'GLM-4-Air (增强)'}"; show_message(mine_msg, "已切换模型", "blue"); page.update()
    switch_btn = ft.ElevatedButton("切换到增强模型" if ai_config["model"] == "free" else "切换到免费模型", on_click=on_switch_model, icon=ft.icons.SWAP_HORIZ)
    free_key_input = ft.TextField(label="免费模型 API 密钥", value=ai_config.get("api_key_free", ""), password=True, hint_text="输入智谱 GLM-4-Flash 的 API Key")
    enhanced_key_input = ft.TextField(label="增强模型 API 密钥", value=ai_config.get("api_key_enhanced", ""), password=True, hint_text="输入智谱 GLM-4-Air 的 API Key")
    def save_keys(e):
        ai_config = load_ai_config(); ai_config["api_key_free"] = free_key_input.value.strip(); ai_config["api_key_enhanced"] = enhanced_key_input.value.strip(); save_ai_config(ai_config); show_message(mine_msg, "API 密钥已保存", "green")
    ai_section = ft.Column([ft.Text("🧠 AI 引擎设置", size=20, weight=ft.FontWeight.BOLD), model_label, cost_label, switch_btn, ft.Divider(), ft.Text("🔑 API 密钥", size=16, weight=ft.FontWeight.BOLD), free_key_input, enhanced_key_input, ft.ElevatedButton("保存密钥", on_click=save_keys)], spacing=10)

    skill_input = ft.TextField(label="自定义 AI Skill（粘贴提示词）", multiline=True, min_lines=4, max_lines=10, value=load_custom_skill())
    def save_skill(e):
        save_custom_skill(skill_input.value)
        show_message(mine_msg, "Skill 已保存，将在新对话中生效", "green")
    skill_section = ft.Column([ft.Text("🎓 自定义教学 Skill", size=18, weight=ft.FontWeight.BOLD), skill_input, ft.ElevatedButton("保存 Skill", on_click=save_skill)], spacing=10)

    mine_page = ft.Column([
        ft.Text("⚙️ 个人中心", size=24, weight=ft.FontWeight.BOLD),
        ft.ElevatedButton("📊 知识框架", on_click=show_knowledge_framework, icon=ft.icons.INSIGHTS),
        mine_msg,
        ft.Divider(),
        task_section,
        ft.Divider(),
        new_words_section,
        ft.Divider(),
        recycle_section,
        ft.Divider(),
        ai_section,
        ft.Divider(),
        skill_section,
    ], spacing=20, scroll=ft.ScrollMode.AUTO)
    set_recycle_filter("全部"); refresh_tasks(); refresh_new_words()

    current_page = ft.Container(expand=True)
    def switch_page(index):
        if index == 0: current_page.content = home_page
        elif index == 1: current_page.content = subject_page
        elif index == 2: current_page.content = mine_page
        page.update()

    page.navigation_bar = ft.NavigationBar(selected_index=0, on_change=lambda e: switch_page(e.control.selected_index), destinations=[ft.NavigationBarDestination(icon=ft.icons.ADD, label="首页"), ft.NavigationBarDestination(icon=ft.icons.SCHOOL, label="学科"), ft.NavigationBarDestination(icon=ft.icons.PERSON, label="我的")])
    switch_page(0)
    page.add(ft.Stack([current_page, contact_panel, chat_dialog, ball_container], expand=True))

if __name__ == "__main__":
    ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=8551)
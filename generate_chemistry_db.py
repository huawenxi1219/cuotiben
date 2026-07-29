"""
generate_chemistry_db.py
批量生成高中化学重要方程式，使用智谱 API。
支持中断续传。
"""
import json
import os
import time
import re
from zhipuai import ZhipuAI

# ---------- 配置 ----------
DATA_FILE = os.path.join("data", "chemistry_equations.jsonl")
BATCH_SIZE = 20
TOTAL_TARGET = 200
DELAY = 2
MAX_RETRIES = 3

# ---------- 读取 API 设置 ----------
def load_api_config():
    config_path = os.path.join("data", "ai_config.json")
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        api_key = config.get("api_key_free", "")
        model = config.get("model", "glm-4-flash")
        return api_key, model
    else:
        return os.environ.get("ZHIPU_API_KEY", ""), "glm-4-flash"

# ---------- 加载已有数据 ----------
def load_existing_ids():
    if not os.path.exists(DATA_FILE):
        return set()
    ids = set()
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        for line in f:
            try:
                obj = json.loads(line)
                ids.add(obj.get("id"))
            except:
                pass
    return ids

# ---------- 生成 prompt ----------
def build_prompt(batch_size, existing_count):
    topics = [
        "离子反应与离子方程式",
        "氧化还原反应",
        "钠、镁、铝及其化合物",
        "铁、铜及其化合物",
        "氯、硫、氮及其化合物",
        "硅及其化合物",
        "化学反应与能量变化",
        "电化学（原电池、电解池）",
        "化学反应速率与化学平衡",
        "水溶液中的离子平衡",
        "有机化学反应（烷、烯、炔、苯、醇、醛、酸、酯）",
        "化学实验常见反应",
        "元素周期律相关反应"
    ]
    prompt = f"""你是一位高中化学老师。请务必严格按照以下要求生成内容。

【重要规则 - 违反将导致系统无法处理】
1. 你必须生成恰好{batch_size}条方程式，不多不少。
2. 每条方程式独占一行，是一个完整的JSON对象。
3. 绝对不要用```json```等代码块包裹，直接输出纯文本。
4. 输出格式示例（注意：每行是一个独立JSON，行与行之间没有逗号）：
{{"id": "0001", "reaction": "锌与稀硫酸反应", "equation": "Zn + H2SO4 = ZnSO4 + H2↑", "ionic_equation": "Zn + 2H+ = Zn2+ + H2↑", "reaction_type": "置换反应", "conditions": "无", "knowledge_point": "金属的化学性质", "notes": "锌粒溶解，有气泡产生"}}
{{"id": "0002", "reaction": "下一反应描述", ...}}
5. id从"{existing_count+1:04d}"开始，连续递增。
6. 覆盖以下主题：{', '.join(topics)}。
7. ionic_equation如无则填"无"，conditions如无则填"无"。
8. 方程式必须配平正确。

现在直接输出{batch_size}行JSON，不要任何额外文字："""
    return prompt

# ---------- 调用 API ----------
def generate_batch(client, model, prompt):
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=4096
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"❌ API 调用失败: {e}")
        return None

# ---------- 提取代码块中的内容 ----------
def extract_json_text(text):
    """去掉可能的 markdown 代码块包裹"""
    text = text.strip()
    # 匹配 ```json ... ``` 或 ``` ... ```
    match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text

# ---------- 解析和保存 ----------
def parse_and_save(text, existing_ids):
    if not text:
        return 0
    # 先提取代码块内容
    text = extract_json_text(text)
    print("📝 解析后内容(前300字符):")
    print(text[:300])
    print("-----")
    lines = text.strip().split("\n")
    saved = 0
    with open(DATA_FILE, "a", encoding="utf-8") as f:
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # 尝试解析整行 JSON
            try:
                obj = json.loads(line)
            except:
                # 如果失败，尝试用正则提取花括号内容
                match = re.search(r'\{[^{}]*\}', line)
                if match:
                    try:
                        obj = json.loads(match.group())
                    except:
                        continue
                else:
                    continue
            if not isinstance(obj, dict) or "id" not in obj:
                continue
            if obj["id"] in existing_ids:
                continue
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
            existing_ids.add(obj["id"])
            saved += 1
    return saved

# ---------- 主流程 ----------
def main():
    api_key, model = load_api_config()
    if not api_key:
        print("❌ 未找到 Zhipu API Key。")
        return

    client = ZhipuAI(api_key=api_key)
    existing_ids = load_existing_ids()
    current_count = len(existing_ids)
    print(f"📊 当前已有 {current_count} 条方程式，目标 {TOTAL_TARGET} 条。")

    consecutive_fail = 0
    while current_count < TOTAL_TARGET:
        need = min(BATCH_SIZE, TOTAL_TARGET - current_count)
        prompt = build_prompt(need, current_count)
        print(f"⏳ 正在生成第 {current_count+1}-{current_count+need} 条...")
        text = generate_batch(client, model, prompt)
        if not text:
            consecutive_fail += 1
            print("⚠️ 重试中...")
            time.sleep(5)
            if consecutive_fail >= MAX_RETRIES:
                print("❌ 连续失败次数过多，退出。")
                break
            continue

        saved = parse_and_save(text, existing_ids)
        current_count = len(existing_ids)
        if saved == 0:
            consecutive_fail += 1
            print("⚠️ 本轮保存0条，看看上面的解析后内容是否正确。")
            if consecutive_fail >= MAX_RETRIES:
                print("❌ 连续0条保存次数过多，退出。")
                break
        else:
            consecutive_fail = 0
            print(f"✅ 本轮保存 {saved} 条，总数已达 {current_count}。")
        time.sleep(DELAY)

    print(f"🎉 结束。共 {current_count} 条方程式，保存在 {DATA_FILE}。")

if __name__ == "__main__":
    main()
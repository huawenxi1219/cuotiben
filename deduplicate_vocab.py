# deduplicate_vocab.py —— 去除词库中重复的单词，只保留第一个条目
import json, os

DATA_DIR = os.path.join(os.getcwd(), "data")
VOCAB_FILE = os.path.join(DATA_DIR, "vocabulary.jsonl")

def deduplicate():
    if not os.path.exists(VOCAB_FILE):
        print("❌ 词库文件不存在")
        return
    
    # 读取所有单词
    seen = set()
    unique_words = []
    duplicates = 0
    with open(VOCAB_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    word_data = json.loads(line)
                    word = word_data.get("word", "").lower()
                    if word and word not in seen:
                        seen.add(word)
                        unique_words.append(line)
                    else:
                        duplicates += 1
                except:
                    # 解析失败的行也保留
                    unique_words.append(line)
    
    # 重写文件，只保留去重后的结果
    with open(VOCAB_FILE, "w", encoding="utf-8") as f:
        for line in unique_words:
            f.write(line + "\n")
    
    print(f"✅ 去重完成！总共保留 {len(unique_words)} 个唯一单词，移除了 {duplicates} 条重复记录。")

if __name__ == "__main__":
    deduplicate()
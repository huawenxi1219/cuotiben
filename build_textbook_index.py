# -*- coding: utf-8 -*-
"""
池鱼Study 教材知识库构建脚本
用法: python build_textbook_index.py
扫描 data/textbooks/*.pdf（浏览器从 TapXWorld/ChinaTextbook 下载的人教版高中教材），
用 PyMuPDF 提取文本，按页分块，输出 data/textbook_index/{科目}.json。
科目按文件名关键词识别：物理 / 化学 / 地理（可自行扩展）。
"""
import os
import re
import json

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
TEXTBOOKS_DIR = os.path.join(DATA_DIR, "textbooks")
INDEX_DIR = os.path.join(DATA_DIR, "textbook_index")

SUBJECT_KEYWORDS = {
    "物理": ["物理"],
    "化学": ["化学"],
    "地理": ["地理"],
}
# 每块取 2 页（控制单块长度，检索粒度适中）
PAGES_PER_BLOCK = 2
# 单块最大字符数（防止超长）
MAX_BLOCK_CHARS = 2200


def detect_subject(filename):
    for subject, kws in SUBJECT_KEYWORDS.items():
        if any(kw in filename for kw in kws):
            return subject
    return None


def extract_pdf_text(pdf_path):
    """返回按页排列的文本列表"""
    import pymupdf  # PyMuPDF 新版包名
    pages = []
    try:
        doc = pymupdf.open(pdf_path)
        for page in doc:
            t = page.get_text("text") or ""
            # 清理：合并多余空行、去除孤立页码
            t = re.sub(r"[ \t]+", " ", t)
            t = re.sub(r"\n{2,}", "\n", t)
            t = re.sub(r"^\s*\d+\s*$", "", t)
            pages.append(t.strip())
        doc.close()
    except Exception as e:
        print(f"  [跳过] {os.path.basename(pdf_path)} 解析失败: {e}")
        return []
    return pages


def main():
    os.makedirs(INDEX_DIR, exist_ok=True)
    if not os.path.isdir(TEXTBOOKS_DIR):
        print(f"未找到教材目录 {TEXTBOOKS_DIR}，请先放入 PDF")
        return
    pdfs = [f for f in os.listdir(TEXTBOOKS_DIR) if f.lower().endswith(".pdf")]
    if not pdfs:
        print(f"{TEXTBOOKS_DIR} 下没有 PDF。下载地址参考：")
        print("  https://github.com/TapXWorld/ChinaTextbook/tree/master/高中/<物理|化学|地理>/人教版-人民教育出版社/")
        return

    # 按科目聚合
    index = {s: {"books": [], "blocks": []} for s in SUBJECT_KEYWORDS}
    for fname in sorted(pdfs):
        subj = detect_subject(fname)
        if not subj:
            print(f"  [跳过] {fname}：文件名不含 物理/化学/地理，无法判断科目")
            continue
        path = os.path.join(TEXTBOOKS_DIR, fname)
        print(f"  解析 {fname} ...")
        pages = extract_pdf_text(path)
        if not pages:
            continue
        book = {"file": fname, "pages": len(pages)}
        index[subj]["books"].append(book)
        # 分块
        cur = []
        for i, t in enumerate(pages, start=1):
            cur.append((i, t))
            if len(cur) >= PAGES_PER_BLOCK:
                block_text = "\n".join(t for _, t in cur)[:MAX_BLOCK_CHARS]
                index[subj]["blocks"].append({
                    "book": fname,
                    "pages": f"{cur[0][0]}-{cur[-1][0]}",
                    "text": block_text,
                })
                cur = []
        if cur:
            block_text = "\n".join(t for _, t in cur)[:MAX_BLOCK_CHARS]
            index[subj]["blocks"].append({
                "book": fname,
                "pages": f"{cur[0][0]}-{cur[-1][0]}",
                "text": block_text,
            })

    total = 0
    for subj, idx in index.items():
        if not idx["blocks"]:
            continue
        out = os.path.join(INDEX_DIR, f"{subj}.json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump(idx, f, ensure_ascii=False, indent=1)
        total += len(idx["blocks"])
        print(f"[OK] {subj}: {len(idx['books'])} 本, {len(idx['blocks'])} 块 -> {out}")
    print(f"完成，共 {total} 块。主程序 AI 对话将按科目自动检索这些内容。")


if __name__ == "__main__":
    main()

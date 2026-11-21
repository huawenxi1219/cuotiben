# -*- coding: utf-8 -*-
"""按人教版顺序重排知识图：必修一 → 必修二 → 选必1 → 选必2 → 选必3，章内按第N章排。"""
import io, json, glob, os, re

PAGES = r"C:\myapp\_chemmap\pages"

BOOK_ORDER = ["必修第一册", "必修第二册", "选择性必修1", "选择性必修2", "选择性必修3"]
CN_NUM = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8,
          "九": 9, "十": 10, "1": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8}


def book_key(name):
    best = 99
    for i, b in enumerate(BOOK_ORDER):
        if name.startswith(b) or b in name:
            best = min(best, i)
    return best


def chap_key(name):
    m = re.search(r"第([一二三四五六七八九十0-9]+)章", name or "")
    if m:
        return CN_NUM.get(m.group(1), 50)
    return 50


files = sorted(glob.glob(os.path.join(PAGES, "p*.json")))
rows = []
for f in files:
    d = json.load(io.open(f, encoding="utf-8"))
    rows.append(d)

rows.sort(key=lambda d: (book_key(d.get("book", "")), chap_key(d.get("chapter", "")), d.get("page", 0)))

books = {}
for d in rows:
    book = d.get("book", "未分类")
    chap = d.get("chapter", "未分类")
    books.setdefault(book, {})
    books[book].setdefault(chap, [])
    books[book][chap].append(d)

tree = {
    "version": 2,
    "subject": "化学",
    "note": "内容来自学生笔记，非完整教材；未拍到的章节不在其中",
    "books": [
        {
            "name": b,
            "chapters": [
                {"name": c, "sections": [
                    {
                        "section": x.get("section", ""),
                        "page": x.get("page"),
                        "points": x.get("points", []),
                        "equations": x.get("equations", []),
                        "pitfalls": x.get("pitfalls_summary", []),
                        "how": x.get("how", ""),
                    } for x in secs
                ]}
                for c, secs in sorted(chaps.items(), key=lambda kv: chap_key(kv[0]))
            ],
        }
        for b, chaps in sorted(books.items(), key=lambda kv: book_key(kv[0]))
    ],
}

s = json.dumps(tree, ensure_ascii=False, indent=1)
for p in (r"C:\myapp\assets\chem_tree.json", r"C:\myapp\data\chem_tree.json"):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    io.open(p, "w", encoding="utf-8", newline="\n").write(s)

print("顺序（人教版）：")
for b in tree["books"]:
    print(" ", b["name"], "→", " / ".join(c["name"] for c in b["chapters"]))

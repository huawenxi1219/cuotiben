# -*- coding: utf-8 -*-
"""导出 Word 能直接打开的 RTF（纯文字、无底纹，省墨）。

RTF 用 \\uN? 表示 Unicode 字符，Word/WPS 都能打开。
"""
import io


def _esc(s):
    out = []
    for ch in str(s):
        o = ord(ch)
        if ch in "\\{}":
            out.append("\\" + ch)
        elif o < 128:
            out.append(ch)
        else:
            if o > 32767:
                o -= 65536
            out.append("\\u%d?" % o)
    return "".join(out)


def errors_to_rtf(items, title="池鱼错题卡", with_answer=False, bind_left_mm=0):
    """每道错题一个段落：编号 + 题目 + 错因 +（可选）答案 + 复习勾。"""
    left = int(1440 * (25 + bind_left_mm) / 25.4)  # twips：25mm 左边距 + 装订边

    parts = [r"{\rtf1\ansi\ansicpg936\deff0",
             r"{\fonttbl{\f0\fnil\fcharset134 Microsoft YaHei;}}",
             r"\paperw11906\paperh16838",
             r"\margl%d\margr1134\margt1134\margb1134" % left,
             r"\f0\fs22"]

    parts.append(r"\pard\qc\b\fs36 %s\b0\fs22\par\par" % _esc(title))

    for i, e in enumerate(items, 1):
        no = e.get("no") or i
        q = _esc((e.get("original") or e.get("question") or "（未填题干）")[:400])
        parts.append(r"\pard\sb120\b #%03d \b0 %s\par" % (int(no), q))

        mis = (e.get("mistake") or "").strip()
        if mis:
            parts.append(r"\pard\li240\sb40 错在：%s\par" % _esc(mis[:300]))

        if with_answer:
            ans = (e.get("answer") or "").strip()
            if ans:
                parts.append(r"\pard\li240 答案：%s\par" % _esc(ans[:400]))

        parts.append(r"\pard\li240\sb60 复习：□D1  □D3  □D7  □D15　　○对 △半对 ✗错\par")

    parts.append("}")
    return "".join(parts).encode("ascii", "ignore")

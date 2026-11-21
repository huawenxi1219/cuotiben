# -*- coding: utf-8 -*-
"""让 AI 能"自己动手"：解析回答里的 ```action 块，自动存错题/存笔记。"""
import io

MAIN = r"C:\myapp\main.py"
t = io.open(MAIN, encoding="utf-8").read()

# ---------- 1) 动作执行器 ----------
FN = r'''
def run_ai_actions(text, subject=""):
    """解析 AI 回答里的 ```action 块并执行（目前支持 save_note / save_error）。
    返回已执行的动作描述列表，供界面提示。"""
    if not text or "```action" not in text:
        return []
    done = []
    for raw in re.findall(r"```action\s*\n(.*?)```", text, re.DOTALL):
        try:
            spec = json.loads(raw.strip())
        except BaseException:
            continue
        name = (spec.get("name") or "").strip()
        args = spec.get("args") or {}
        if not isinstance(args, dict):
            continue
        try:
            if name == "save_note":
                content = str(args.get("content") or "").strip()
                if not content:
                    continue
                tags = args.get("tags") or []
                if isinstance(tags, str):
                    tags = [x.strip() for x in tags.replace("，", ",").split(",") if x.strip()]
                save_note(subject or args.get("subject") or "总AI", content, media=[], tags=tags[:6])
                done.append(f"笔记已存（{('、'.join(tags[:3])) if tags else '无标签'}）")
            elif name == "save_error":
                q = str(args.get("question") or args.get("original") or "").strip()
                if not q:
                    continue
                tags = args.get("tags") or []
                if isinstance(tags, str):
                    tags = [x.strip() for x in tags.replace("，", ",").split(",") if x.strip()]
                save_error(subject or args.get("subject") or "总AI",
                           original=q,
                           answer=str(args.get("answer") or ""),
                           mistake=str(args.get("mistake") or ""),
                           idea=str(args.get("idea") or ""),
                           manual_tags=",".join(str(x) for x in tags[:6]))
                done.append("错题已收录")
        except BaseException as _be:
            _diag_log(_be, "L_action")
    return done


'''
anchor = "def build_error_cards_html("
assert anchor in t
t = t.replace(anchor, FN.lstrip("\n") + anchor, 1)

# ---------- 2) 回答落地后执行动作 ----------
OLD = '''                        save_chat_message(subject, "assistant", ai_response["text"])'''
NEW = '''                        save_chat_message(subject, "assistant", ai_response["text"])
                        try:
                            _acts = run_ai_actions(ai_response["text"], subject)
                            if _acts:
                                show_toast("✅ " + "；".join(_acts), "green")
                                try:
                                    refresh_stats_after_action()
                                except BaseException:
                                    pass
                        except Exception as _ae:
                            _diag_log(_ae, "L_action_run")'''
assert OLD in t
t = t.replace(OLD, NEW, 1)

# ---------- 3) 给 AI 的动作协议 ----------
OLD2 = '''【继续生成规则】'''
NEW2 = '''【动手能力（你可以替学生直接保存）】
当学生说"把这题收进错题本""帮我记下来""存到笔记里"这类话，除了正常回答，在回答**最后**附一个动作块：

```action
{"name":"save_error","args":{"question":"完整题目","mistake":"错因","answer":"标准答案或解法","tags":["知识点1","知识点2"]}}
```

记笔记用：

```action
{"name":"save_note","args":{"content":"笔记正文","tags":["知识点"]}}
```

规则：
- 只允许这两个动作，一次回答最多 2 个
- 动作块必须是合法 JSON，字段不用可以留空字符串
- 不要在动作块前后解释"我正在调用工具"这类话，学生看不到执行过程，只看到结果提示
- 学生没让你存，就不要乱存

【继续生成规则】'''
assert OLD2 in t
t = t.replace(OLD2, NEW2, 1)

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(t)
print("动作协议已加入")

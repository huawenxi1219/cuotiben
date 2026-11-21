# -*- coding: utf-8 -*-
import io, json, os, tempfile
import main

d = tempfile.mkdtemp()
main.NOTES_FILE = os.path.join(d, "n.jsonl")
main.ERRORS_FILE = os.path.join(d, "e.jsonl")

txt = (
    "好的，已经帮你整理。\n"
    "```action\n"
    '{"name":"save_note","args":{"content":"牛顿第二定律 F=ma","tags":["力学","牛顿定律"]}}\n'
    "```\n"
    "```action\n"
    '{"name":"save_error","args":{"question":"求加速度","mistake":"漏了摩擦力","answer":"a=2","tags":["受力分析"]}}\n'
    "```\n"
)
print("has block:", "```action" in txt)
acts = main.run_ai_actions(txt, "物理")
print("actions:", acts)
print("notes:", len(main.load_jsonl(main.NOTES_FILE)))
print("errors:", len(main.load_jsonl(main.ERRORS_FILE)))
if main.load_jsonl(main.NOTES_FILE):
    print("note:", main.load_jsonl(main.NOTES_FILE)[0].get("content"), main.load_jsonl(main.NOTES_FILE)[0].get("tags"))
if main.load_jsonl(main.ERRORS_FILE):
    print("err:", main.load_jsonl(main.ERRORS_FILE)[0].get("original"))

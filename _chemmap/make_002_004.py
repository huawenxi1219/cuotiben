# -*- coding: utf-8 -*-
"""把第 2~4 页笔记整理成结构化 JSON。"""
import io, json, os

OUT = r"C:\myapp\_chemmap\pages"
os.makedirs(OUT, exist_ok=True)

pages = [
    {
        "page": 2,
        "book": "选择性必修3",
        "chapter": "第五章 合成高分子",
        "section": "加聚反应与缩聚反应",
        "points": [
            {"id": "5.1.1", "title": "加聚反应", "detail": "含 C=C 的单体打开双键互相加成，无小分子生成。链节与单体组成相同。"},
            {"id": "5.1.2", "title": "二烯烃的 1,2-/1,4-加成", "detail": "1,3-丁二烯与苯乙烯等共聚时，可发生 1,2-加成（侧链双键保留）或 1,4-加成（主链保留一个双键）。"},
            {"id": "5.1.3", "title": "缩聚反应", "detail": "单体间脱去小分子（H₂O、HCl 等）形成高分子，链节组成小于单体。"},
            {"id": "5.1.4", "title": "聚酯类", "detail": "二元酸 + 二元醇 → 聚酯 + H₂O。例：乙二酸 + 乙二醇；对苯二甲酸 + 乙二醇 → PET。"},
            {"id": "5.1.5", "title": "聚酰胺类", "detail": "二元酸 + 二元胺 → 聚酰胺 + H₂O。例：己二酸 + 己二胺 → 尼龙-66。"},
            {"id": "5.1.6", "title": "羟基酸自缩聚", "detail": "同一分子既有 —OH 又有 —COOH 时可自缩聚，例：乳酸 → 聚乳酸 + nH₂O。"},
            {"id": "5.1.7", "title": "酚醛树脂", "detail": "苯酚 + 甲醛在酸/碱催化下缩聚，生成线型（酸催化）或网状（碱催化、甲醛过量）结构。"},
            {"id": "5.1.8", "title": "聚碳酸酯", "detail": "光气（COCl₂）+ 双酚 A → 聚碳酸酯 + HCl；也可用碳酸二苯酯酯交换法。"},
            {"id": "5.1.9", "title": "可降解高分子", "detail": "CO₂ 与环氧丙烷共聚可得可降解聚碳酸酯类材料。"},
            {"id": "5.1.10", "title": "书写规则", "detail": "端基要补全；缩聚物写出 n 与小分子计量数 (2n−1)/(n−1) 要匹配。"},
        ],
        "equations": [
            {"eq": "nCH₂=CH₂ → [-CH₂-CH₂-]ₙ", "note": "加聚"},
            {"eq": "nC₆H₅-CH=CH₂ → [-CH(C₆H₅)-CH₂-]ₙ", "note": "聚苯乙烯"},
            {"eq": "nHOOC-COOH + nHOCH₂CH₂OH → [-CO-CO-O-CH₂CH₂-O-]ₙ + 2nH₂O", "note": "聚酯"},
            {"eq": "nHOOC-(CH₂)₄-COOH + nH₂N-(CH₂)₆-NH₂ → [-CO-(CH₂)₄-CO-NH-(CH₂)₆-NH-]ₙ + 2nH₂O", "note": "尼龙-66"},
            {"eq": "nC₆H₅OH + nHCHO → 酚醛树脂 + nH₂O", "note": "线型/网状视条件"},
        ],
        "corrections": [
            "原笔记缩聚端基的 (2n−1) 与 (n−1) 需与具体单体对应，已统一写成小分子计量数说明。",
        ],
    },
    {
        "page": 3,
        "book": "选择性必修1",
        "chapter": "第三章 水溶液中的离子平衡 / 第一章 离子反应",
        "section": "沉淀溶解平衡·配位·离子方程式正误·连续型与量有关",
        "points": [
            {"id": "3.1.1", "title": "开始沉淀的 pH", "detail": "已知 Ksp 与金属离子浓度 c，由 c(OH⁻) = ∛(Ksp/c) 求 [OH⁻]，再算 pH。Fe(OH)₃ 与 Al(OH)₃ 均用三次方根。"},
            {"id": "3.1.2", "title": "配离子的生成与破坏", "detail": "[Cu(NH₃)₄]²⁺ 加酸会解离出 Cu²⁺；加过量氨水则生成配离子。"},
            {"id": "3.1.3", "title": "离子方程式正误判断四步", "detail": "① 能否拆（强酸强碱可溶盐拆，弱电解质/沉淀/气体/氧化物不拆）② 是否漏写 ③ 原理是否符合事实 ④ 三守恒（质量、电荷、得失电子）⑤ 配比是否正确。"},
            {"id": "3.1.4", "title": "常见错误类型", "detail": "Fe + H⁺ → Fe³⁺ + H₂（价态错）；SO₂ + ClO⁻ 写成复分解（应氧化还原）；Fe(OH)₃ 与 HI 只写中和（应氧化还原）。"},
            {"id": "3.1.5", "title": "连续型反应（与量有关）", "detail": "NaOH 溶液中通 CO₂：CO₂ 少量生成 CO₃²⁻，过量生成 HCO₃⁻；按 n(CO₂):n(OH⁻) 分段判断。"},
            {"id": "3.1.6", "title": "沉淀转化方向", "detail": "由 Ksp 大的向 Ksp 小的转化，平衡常数 K = Ksp(原)/Ksp(新)；K 很大时看作完全。"},
        ],
        "equations": [
            {"eq": "Fe³⁺ + 3OH⁻ → Fe(OH)₃↓", "note": "开始沉淀时 c(OH⁻)=∛(Ksp/c)"},
            {"eq": "2OH⁻ + CO₂ → CO₃²⁻ + H₂O", "note": "CO₂ 少量"},
            {"eq": "CO₃²⁻ + CO₂ + H₂O → 2HCO₃⁻", "note": "CO₂ 过量"},
            {"eq": "Cu²⁺ + 4NH₃ → [Cu(NH₃)₄]²⁺", "note": "配位"},
            {"eq": "FeS(s) + Cu²⁺ ⇌ CuS(s) + Fe²⁺", "note": "K = Ksp(FeS)/Ksp(CuS)"},
        ],
        "corrections": [
            "原笔记把「与量有关」的连续型放在离子方程式一节，已单列为 3.1.5。",
            "「三守恒」补全为质量、电荷、得失电子三者。",
        ],
    },
    {
        "page": 4,
        "book": "必修第一册 / 选择性必修1",
        "chapter": "第一章 物质及其变化",
        "section": "两性氢氧化物·弱酸电离·离子反应类型·氧化剂还原剂",
        "points": [
            {"id": "1.2.1", "title": "Al(OH)₃ 的两性", "detail": "碱式电离 Al(OH)₃ ⇌ Al³⁺ + 3OH⁻；酸式电离 Al(OH)₃ + H₂O ⇌ [Al(OH)₄]⁻ + H⁺（H⁺ 来自水，不是自身电离）。"},
            {"id": "1.2.2", "title": "H₃BO₃ 是一元弱酸", "detail": "H₃BO₃ + H₂O ⇌ [B(OH)₄]⁻ + H⁺；B 有空轨道，接受 OH⁻ 而显酸性（Lewis 酸）。"},
            {"id": "1.2.3", "title": "NaHSO₄ 的电离", "detail": "熔融：NaHSO₄ → Na⁺ + HSO₄⁻；水溶液：NaHSO₄ → Na⁺ + H⁺ + SO₄²⁻。"},
            {"id": "1.2.4", "title": "离子反应类型", "detail": "复分解（生成沉淀/气体/弱电解质）、氧化还原、配位、双水解；判断依据是离子浓度是否显著减小。"},
            {"id": "1.2.5", "title": "常见氧化剂", "detail": "X₂、O₂、H₂O₂、MnO₄⁻、Cr₂O₇²⁻(H⁺)、NO₃⁻(H⁺)、ClO⁻、PbO₂、MnO₂、Fe³⁺、Ag⁺。"},
            {"id": "1.2.6", "title": "常见还原剂", "detail": "H₂S、SO₂、HI、HCHO、HCOOH、S²⁻、I⁻、Fe²⁺、Br⁻、S₂O₃²⁻。"},
            {"id": "1.2.7", "title": "S₂O₃²⁻ 的歧化", "detail": "S₂O₃²⁻ + 2H⁺ → S↓ + SO₂↑ + H₂O，既是氧化剂又是还原剂。"},
        ],
        "equations": [
            {"eq": "Al(OH)₃ + H₂O ⇌ [Al(OH)₄]⁻ + H⁺", "note": "酸式电离"},
            {"eq": "H₃BO₃ + H₂O ⇌ [B(OH)₄]⁻ + H⁺", "note": "一元弱酸"},
            {"eq": "NaHSO₄ → Na⁺ + H⁺ + SO₄²⁻", "note": "水溶液中"},
            {"eq": "S₂O₃²⁻ + 2H⁺ → S↓ + SO₂↑ + H₂O", "note": "歧化"},
        ],
        "corrections": [
            "原笔记「H⁺ 不是自身电离」表述正确，已补上「来自水」的机制。",
            "「三守恒」与「氧化剂/还原剂清单」分列，避免混在一起。",
        ],
    },
]

for p in pages:
    path = os.path.join(OUT, "p%03d.json" % p["page"])
    io.open(path, "w", encoding="utf-8", newline="\n").write(
        json.dumps(p, ensure_ascii=False, indent=2))
    print("写入", path, "知识点", len(p["points"]), "方程式", len(p["equations"]))

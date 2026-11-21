# -*- coding: utf-8 -*-
"""人教版高中化学三年知识总图（SVG 矢量，紧凑版：章框内直接列要点）。"""

import io

TREE = [
    ("必修第一册", [
        ("第一章 物质及其变化", [
            "物质的分类（单质/氧化物/酸/碱/盐）",
            "分散系：溶液·胶体·浊液；胶体丁达尔效应",
            "电解质与非电解质",
            "离子反应：离子方程式书写、离子共存判断",
            "氧化还原：化合价升降、电子守恒配平",
            "氧化剂/还原剂、氧化性/还原性比较",
        ]),
        ("第二章 钠和氯", [
            "钠与水/氧气反应；Na₂O 与 Na₂O₂ 区别",
            "Na₂CO₃ 与 NaHCO₃ 的鉴别；焰色试验",
            "氯气：与金属/水/碱反应；氯水成分",
            "次氯酸盐与漂白粉",
            "物质的量 n=m/M=N/N_A；Vm=22.4L/mol（标况）",
            "物质的量浓度 c=n/V；配制一定浓度溶液",
        ]),
        ("第三章 铁 金属材料", [
            "Fe²⁺/Fe³⁺ 转化；Fe(OH)₂ 白→灰绿→红褐",
            "Fe³⁺ 检验（KSCN 变红）",
            "铝的两性：Al、Al₂O₃、Al(OH)₃",
            "铝热反应",
            "合金：钢/生铁/青铜；金属冶炼方法",
        ]),
        ("第四章 物质结构 元素周期律", [
            "原子结构：质子/中子/电子；核素与同位素",
            "元素周期表结构与周期律",
            "同周期/同主族递变规律",
            "化学键：离子键/共价键；电子式",
            "分子间作用力与氢键",
        ]),
    ]),
    ("必修第二册", [
        ("第五章 非金属元素", [
            "硫：SO₂ 还原性与漂白性",
            "浓硫酸三大特性：吸水/脱水/强氧化",
            "硫酸根检验",
            "氮：N₂ 稳定性；NO/NO₂ 转化",
            "硝酸的强氧化性",
            "氨气喷泉实验；铵盐与铵根检验",
            "硅及其化合物（半导体/玻璃）",
        ]),
        ("第六章 化学反应与能量", [
            "键断裂吸热/键形成放热",
            "放热与吸热反应判断",
            "原电池构成条件与正负极判断",
            "反应速率及影响因素",
            "可逆反应、化学平衡状态与反应限度",
        ]),
        ("第七章 有机化合物", [
            "有机物特点：同分异构",
            "甲烷取代；乙烯加成/加聚；苯的取代",
            "乙醇：羟基性质与催化氧化",
            "乙酸：羧基与酯化反应；酯的水解",
            "糖类、油脂、蛋白质",
        ]),
        ("第八章 化学与可持续发展", [
            "金属矿物开发利用",
            "海水资源利用（溴/镁）",
            "煤、石油、天然气综合利用",
            "化肥农药合理使用；安全用药",
            "环境保护与绿色化学",
        ]),
    ]),
    ("选择性必修1 化学反应原理", [
        ("第一章 化学反应的热效应", [
            "反应热与焓变 ΔH；放热 ΔH<0、吸热 ΔH>0",
            "热化学方程式书写",
            "盖斯定律",
            "燃烧热与中和热",
        ]),
        ("第二章 速率与平衡", [
            "速率 v=Δc/Δt；浓度/温度/压强/催化剂影响",
            "活化能与有效碰撞",
            "平衡常数 K；浓度商 Q 与 K 比较",
            "勒夏特列原理",
            "转化率计算、等效平衡",
        ]),
        ("第三章 水溶液中的离子平衡", [
            "弱电解质电离平衡；电离常数 Ka",
            "水的电离与 Kw；pH 计算",
            "盐类水解规律与水解离子方程式",
            "沉淀溶解平衡 Ksp；沉淀转化",
            "酸碱中和滴定与误差分析",
        ]),
        ("第四章 化学反应与电能", [
            "原电池原理与电极反应式",
            "化学电源：一次/二次/燃料电池",
            "电解池原理与电解产物判断",
            "电镀与电解精炼",
            "金属腐蚀与防护（牺牲阳极法）",
        ]),
    ]),
    ("选择性必修2 物质结构与性质", [
        ("第一章 原子结构与性质", [
            "能层与能级",
            "电子排布式与轨道表示式",
            "构造原理、洪特规则",
            "电离能与电负性；原子光谱",
        ]),
        ("第二章 分子结构与性质", [
            "共价键：σ 键与 π 键",
            "键参数：键能/键长/键角",
            "杂化轨道 sp/sp²/sp³",
            "VSEPR 模型与分子构型",
            "极性分子与非极性分子",
            "范德华力与氢键；手性分子",
        ]),
        ("第三章 晶体结构与性质", [
            "晶体与非晶体",
            "四种晶体类型与性质对比",
            "晶胞、配位数与密度计算",
            "离子晶体熔沸点比较",
            "金属晶体与电子气理论",
        ]),
    ]),
    ("选择性必修3 有机化学基础", [
        ("第一章 有机物的结构特点", [
            "碳原子成键特点",
            "同分异构体书写",
            "官能团与结构式",
            "分离提纯：蒸馏/萃取/重结晶",
            "元素分析与波谱（红外/核磁/X 射线）",
        ]),
        ("第二章 烃", [
            "烷烃：取代反应",
            "烯烃：加成/加聚/氧化",
            "炔烃",
            "芳香烃：苯及其同系物",
            "烃的燃烧规律",
        ]),
        ("第三章 烃的衍生物", [
            "卤代烃：取代与消去",
            "醇：羟基性质；酚：弱酸性",
            "醛：氧化与还原（银镜反应）；酮",
            "羧酸：酸性/酯化；酯：水解",
            "官能团检验与有机合成路线设计",
        ]),
        ("第四章 生物大分子", [
            "糖类：单糖/二糖/多糖",
            "淀粉与纤维素水解",
            "氨基酸与蛋白质；蛋白质变性",
            "酶与核酸",
        ]),
        ("第五章 合成高分子", [
            "加聚反应",
            "缩聚反应",
            "塑料/橡胶/纤维",
            "功能高分子材料",
        ]),
    ]),
]

COLORS = [
    ("#17324F", "#7AA2F7"),
    ("#173D33", "#4DB6AC"),
    ("#33204A", "#BB9AF7"),
    ("#3D2E17", "#E0AF68"),
    ("#3F1B2A", "#F7768E"),
]

X_BOOK, X_CHAP = 30, 300
BOOK_W, CHAP_W = 230, 760
LINE_H = 24
PAD = 14


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build():
    blocks = []
    y = 70
    for mi, (book, chapters) in enumerate(TREE):
        chap_pos = []
        block_h = 0
        for chap, leaves in chapters:
            h = len(leaves) * LINE_H + 44
            chap_pos.append((chap, leaves, y + block_h, h))
            block_h += h + 14
        blocks.append((mi, book, chap_pos, block_h, y))
        y += block_h + 34
    H = y + 30
    W = X_CHAP + CHAP_W + 30

    out = []
    out.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
               f'viewBox="0 0 {W} {H}" font-family="Microsoft YaHei, Noto Sans CJK SC, sans-serif">')
    out.append(f'<rect width="{W}" height="{H}" fill="#16161E"/>')
    out.append(f'<text x="30" y="40" fill="#E8EBF5" font-size="24" font-weight="bold">'
               f'人教版高中化学 · 三年知识总图</text>')

    for mi, book, chap_pos, block_h, y0 in blocks:
        fill, stroke = COLORS[mi % len(COLORS)]
        by = y0 + block_h / 2 - 26
        out.append(f'<rect x="{X_BOOK}" y="{by}" width="{BOOK_W}" height="52" rx="14" '
                   f'fill="{fill}" stroke="{stroke}" stroke-width="2"/>')
        out.append(f'<text x="{X_BOOK + BOOK_W / 2}" y="{by + 33}" fill="#F5F7FF" '
                   f'font-size="17" text-anchor="middle">{esc(book)}</text>')
        bx, byy = X_BOOK + BOOK_W, by + 26

        for chap, leaves, cy, ch in chap_pos:
            out.append(f'<rect x="{X_CHAP}" y="{cy}" width="{CHAP_W}" height="{ch}" rx="12" '
                       f'fill="#1B1F2E" stroke="{stroke}" stroke-width="1.4" opacity="0.96"/>')
            out.append(f'<text x="{X_CHAP + 14}" y="{cy + 26}" fill="#E8EBF5" font-size="16" '
                       f'font-weight="600">{esc(chap)}</text>')
            out.append(f'<path d="M{bx},{byy} C{bx + 40},{byy} {X_CHAP - 60},{cy + ch / 2} '
                       f'{X_CHAP},{cy + ch / 2}" fill="none" stroke="{stroke}" '
                       f'stroke-width="2" opacity="0.7"/>')
            for li, leaf in enumerate(leaves):
                ly = cy + 26 + 16 + li * LINE_H
                out.append(f'<circle cx="{X_CHAP + 20}" cy="{ly - 5}" r="2.6" fill="{stroke}"/>')
                out.append(f'<text x="{X_CHAP + 32}" y="{ly}" fill="#C9CFE0" font-size="14">'
                           f'{esc(leaf)}</text>')

    out.append("</svg>")
    return "\n".join(out), W, H


if __name__ == "__main__":
    s, w, h = build()
    io.open(r"C:\myapp\化学知识地图.svg", "w", encoding="utf-8", newline="\n").write(s)
    n = sum(len(l) for _, ch in TREE for _, l in ch)
    print(f"SVG {w}x{h}，章 {sum(len(c) for _, c in TREE)}，要点 {n}")

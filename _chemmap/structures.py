# -*- coding: utf-8 -*-
"""有机常见分子的键线式（SVG），嵌进背诵版，帮助“看图记结构”。

只画最基础的几个：乙醇、乙酸、乙醛、丙酮、苯、苯酚、乙酸乙酯。
坐标是手算的，保证形状正确（锯齿 / 六元环）。
"""

# 宽度统一 300，高度 110，淡灰底
_W, _H = 300, 110


def _wrap(body):
    w2, h2 = int(_W * 0.45), int(_H * 0.45)
    return (f'<svg width="{w2}" height="{h2}" viewBox="0 0 {_W} {_H}" '
            f'xmlns="http://www.w3.org/2000/svg" class="mol">'
            f'<rect width="{_W}" height="{_H}" fill="#fafbfc"/>'
            f'<g stroke="#222" stroke-width="3.4" fill="none" stroke-linecap="round">'
            + body +
            '</g></svg>')


def _txt(x, y, s, size=15, anchor="middle", color="#111"):
    return (f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" '
            f'fill="{color}" stroke="none" font-family="Consolas,Menlo,monospace">{s}</text>')


def ethanol():
    body = (
        '<path d="M40,75 L85,45 L130,75"/>'
        '<path d="M130,75 L160,58"/>'
        + _txt(40, 98, "CH₃") + _txt(85, 32, "CH₂") + _txt(178, 55, "OH")
    )
    return _wrap(body)


def acetaldehyde():
    body = (
        '<path d="M45,75 L95,45"/>'
        '<path d="M95,45 L145,75"/>'
        '<path d="M95,45 L95,20"/>'
        '<path d="M101,45 L101,20"/>'
        + _txt(45, 98, "CH₃") + _txt(95, 14, "O") + _txt(160, 82, "H")
    )
    return _wrap(body)


def acetic_acid():
    body = (
        '<path d="M40,78 L85,48"/>'
        '<path d="M85,48 L128,78"/>'
        '<path d="M85,48 L85,22"/>'
        '<path d="M91,48 L91,22"/>'
        '<path d="M128,78 L165,55"/>'
        + _txt(40, 100, "CH₃") + _txt(88, 16, "O") + _txt(178, 50, "OH")
    )
    return _wrap(body)


def acetone():
    body = (
        '<path d="M35,75 L85,45 L135,75 L180,45"/>'
        '<path d="M85,45 L85,20"/>'
        '<path d="M91,45 L91,20"/>'
        + _txt(35, 98, "CH₃") + _txt(88, 14, "O") + _txt(180, 32, "CH₃")
    )
    return _wrap(body)


def benzene():
    # 正六边形：中心 (150,55) 半径 34
    import math
    pts = []
    for k in range(6):
        a = math.radians(60 * k - 90)
        pts.append((150 + 34 * math.cos(a), 55 + 34 * math.sin(a)))
    d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + " Z"
    body = f'<path d="{d}"/>' + '<circle cx="150" cy="55" r="20"/>'
    return _wrap(body)


def phenol():
    import math
    pts = []
    for k in range(6):
        a = math.radians(60 * k - 90)
        pts.append((135 + 34 * math.cos(a), 55 + 34 * math.sin(a)))
    d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + " Z"
    body = (f'<path d="{d}"/>'
            + '<circle cx="135" cy="55" r="20"/>'
            + '<path d="M169,55 L200,55"/>'
            + _txt(215, 60, "OH"))
    return _wrap(body)


def ethyl_acetate():
    body = (
        '<path d="M30,80 L70,52 L110,80"/>'
        '<path d="M110,80 L140,62"/>'
        '<path d="M140,62 L175,80 L205,58"/>'
        '<path d="M140,62 L140,36"/>'
        '<path d="M146,62 L146,36"/>'
        + _txt(30, 102, "CH₃") + _txt(110, 102, "O") + _txt(143, 30, "O")
        + _txt(215, 52, "CH₂CH₃")
    )
    return _wrap(body)


STRUCTS = {
    "乙醇": ethanol(),
    "醇": ethanol(),
    "酚": phenol(),
    "醛": acetaldehyde(),
    "酮": acetone(),
    "羧酸": acetic_acid(),
    "乙醛": acetaldehyde(),
    "乙酸": acetic_acid(),
    "丙酮": acetone(),
    "苯": benzene(),
    "苯酚": phenol(),
    "酯": ethyl_acetate(),
}

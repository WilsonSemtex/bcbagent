"""
DXF 板材图纸解析工具：提取几何特征与尺寸标注，转为 AI 可读文本。

整合自「DXF读取工具」：
- dxf_geometry.py：圆孔/圆弧/直线等几何特征分析
- dxf_extract.py：DIMENSION 尺寸标注、文字实体、图元统计

判读原则（与知识库 bcb 一致）：矢量优先——所有尺寸/孔径/圆角以坐标与
实体数据为精确依据，视觉模型仅辅助理解布局。
"""
import math
import os
from collections import defaultdict

import ezdxf


def analyze_geometry(doc) -> dict:
    """几何特征分析：完整圆孔、圆弧碎片(圆角)、直线、CIRCLE 实体。"""
    msp = doc.modelspace()
    arcs, lines, circles = [], [], []

    for e in msp:
        t = e.dxftype()
        if t == "ARC":
            arcs.append({
                "cx": float(e.dxf.center.x), "cy": float(e.dxf.center.y),
                "r": float(e.dxf.radius),
                "s": float(e.dxf.start_angle), "e": float(e.dxf.end_angle),
            })
        elif t == "CIRCLE":
            circles.append((float(e.dxf.center.x), float(e.dxf.center.y), float(e.dxf.radius)))
        elif t == "LINE":
            p1 = (float(e.dxf.start.x), float(e.dxf.start.y))
            p2 = (float(e.dxf.end.x), float(e.dxf.end.y))
            lines.append((p1, p2))

    def sweep(a):
        sw = a["e"] - a["s"]
        return sw + 360 if sw < 0 else sw

    # 完整圆孔：同圆心同半径的多段圆弧覆盖 ~360°，或直接 CIRCLE
    hole_groups = defaultdict(list)
    for a in arcs:
        key = (round(a["cx"], 2), round(a["cy"], 2), round(a["r"], 3))
        hole_groups[key].append(a)

    round_holes = []
    arc_frags = []
    for key, lst in hole_groups.items():
        total = sum(sweep(a) for a in lst)
        cx, cy, r = key
        if total >= 355:
            round_holes.append({"diameter": round(2 * r, 4), "r": round(r, 4), "center": (round(cx, 2), round(cy, 2))})
        else:
            for a in lst:
                arc_frags.append({**a, "sweep": round(sweep(a), 2)})

    # 汇总圆弧碎片半径分布（圆角/异形孔边界）
    radius_summary = defaultdict(int)
    for f in arc_frags:
        radius_summary[round(f["r"], 4)] += 1

    return {
        "round_holes": round_holes,                      # 完整圆孔（直径/半径/圆心）
        "arc_fragment_radius_summary": dict(sorted(radius_summary.items())),  # 圆弧碎片半径→段数
        "arc_fragments_count": len(arc_frags),
        "line_count": len(lines),                        # 直线数量
        "circle_entities": [{"diameter": round(2 * r, 3), "center": (round(cx, 2), round(cy, 2))} for cx, cy, r in circles],
    }


def analyze_dimensions(doc) -> dict:
    """尺寸标注与文字实体：DIMENSION 测量值、TEXT/MTEXT、实体统计。"""
    msp = doc.modelspace()

    dimensions = []
    for dim in msp.query("DIMENSION"):
        try:
            val = dim.get_measurement()
        except Exception:
            val = None
        txt = dim.dxf.text
        defpoint = tuple(round(float(c), 3) for c in dim.dxf.defpoint)
        dimensions.append({
            "handle": dim.dxf.handle,
            "dimstyle": dim.dxf.dimstyle,
            "measurement": round(val, 4) if val is not None else None,
            "text": txt,
            "anchor": defpoint,
        })

    texts = []
    for t in msp.query("TEXT"):
        texts.append({"type": "TEXT", "text": t.dxf.text,
                      "insert": tuple(round(float(c), 3) for c in t.dxf.insert),
                      "height": round(float(t.dxf.height), 3)})
    for m in msp.query("MTEXT"):
        texts.append({"type": "MTEXT", "text": m.text.replace("\n", " "),
                      "insert": tuple(round(float(c), 3) for c in m.dxf.insert),
                      "height": round(float(getattr(m.dxf, "char_height", 0)), 3)})

    entity_counts = {}
    for e in msp:
        entity_counts[e.dxftype()] = entity_counts.get(e.dxftype(), 0) + 1

    return {
        "dimension_count": len(dimensions),
        "dimensions": dimensions,
        "text_count": len(texts),
        "texts": texts,
        "entity_counts": entity_counts,
    }


def parse_dxf(path: str) -> dict:
    """解析 DXF 文件，返回几何 + 尺寸 + 实体统计。"""
    doc = ezdxf.readfile(path)
    return {
        "file": os.path.basename(path),
        "geometry": analyze_geometry(doc),
        "dimensions": analyze_dimensions(doc),
    }


def dxf_to_text(path: str) -> str:
    """将 DXF 解析结果转为 AI 可读的结构化文本（mm 单位，矢量优先）。"""
    data = parse_dxf(path)
    parts = [f"【DXF 图纸: {data['file']}】"]

    g = data["geometry"]
    parts.append("— 几何特征 —")
    if g["round_holes"]:
        parts.append("完整圆孔:")
        for h in g["round_holes"]:
            parts.append(f"  直径 {h['diameter']}mm (半径 {h['r']}mm) @ 圆心 {h['center']}")
    else:
        parts.append("完整圆孔: 无 (无 360° 闭合圆)")
    if g["circle_entities"]:
        parts.append("CIRCLE 实体:")
        for c in g["circle_entities"]:
            parts.append(f"  直径 {c['diameter']}mm @ {c['center']}")
    if g["arc_fragment_radius_summary"]:
        parts.append("圆弧碎片(圆角/异形孔边界)半径分布:")
        for r, cnt in g["arc_fragment_radius_summary"].items():
            parts.append(f"  半径 {r}mm: {cnt} 段")
    parts.append(f"直线数量: {g['line_count']}")

    d = data["dimensions"]
    parts.append("— 尺寸标注 —")
    if d["dimensions"]:
        for dim in d["dimensions"]:
            t = f" 文字={dim['text']}" if dim["text"] else ""
            parts.append(f"  handle={dim['handle']} 测量值={dim['measurement']}mm{t} 位置={dim['anchor']}")
    else:
        parts.append("  无 DIMENSION 尺寸标注实体（尺寸需按坐标/图面文字判读）")
    if d["texts"]:
        parts.append("— 文字实体 —")
        for t in d["texts"]:
            parts.append(f"  [{t['type']}] \"{t['text']}\" @ {t['insert']}")

    parts.append("— 实体统计 —")
    parts.append("  " + ", ".join(f"{k}: {v}" for k, v in sorted(d["entity_counts"].items())))

    return "\n".join(parts)

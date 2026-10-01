"""Phase 1 图谱质量报告：把 drafts/ 草稿临时并入内存图（source=llm，不落盘、不入 reviewed/），
输出三类交付物：

1. 图谱统计：节点/边/各关系类型数量、restriction_type 分布、evidence_strength 分布
2. 典型多跳链路案例（可 --chain 追加查询）
3. 人工复核清单（--save 写入 backend/data/kg/review_checklist.md）：
   P0 含法规/明确禁忌边  P1 含模型新增节点或边  P2 仅 suggestive 证据  P3 空抽取

用法（backend/ 目录下）：
    python scripts/phase1_report.py
    python scripts/phase1_report.py --chain 明矾:儿童
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import knowledge_graph as kg  # noqa: E402

DEMO_PAIRS = [("阿斯巴甜", "儿童"), ("亚硝酸钠", "普通人群"), ("明矾", "儿童"), ("焦亚硫酸钠", "哮喘者"), ("赤藓红", "儿童")]
CHECKLIST_PATH = kg.KG_DATA_DIR / "review_checklist.md"


def load_drafts() -> list[tuple[Path, dict]]:
    entries = []
    for path in sorted(kg.DRAFT_DIR.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"[警告] 跳过无法解析的草稿 {path.name}: {exc}", file=sys.stderr)
            continue
        if isinstance(payload, dict) and payload.get("additive"):
            entries.append((path, payload))
    return entries


def build_merged_graph(drafts: list[tuple[Path, dict]]) -> kg.nx.MultiDiGraph:
    merged = kg.build_graph(include_extractions=False)
    for _, payload in drafts:
        kg.add_extraction(merged, payload, source="llm")
    return merged


def print_stats(skeleton: kg.nx.MultiDiGraph, merged: kg.nx.MultiDiGraph, drafts: list[tuple[Path, dict]]) -> None:
    print("=" * 62)
    print("一、图谱统计")
    print("=" * 62)
    base_stats = kg.graph_stats(skeleton)
    merged_stats = kg.graph_stats(merged)
    print(f"草稿并入前：{base_stats['nodes']} 节点 / {base_stats['edges']} 边")
    print(f"草稿并入后：{merged_stats['nodes']} 节点 / {merged_stats['edges']} 边")
    print(f"新增节点 {merged_stats['nodes'] - base_stats['nodes']} 个（substance/subgroup）、"
          f"新增边 {merged_stats['edges'] - base_stats['edges']} 条（模型抽取）")
    print("\n各节点类型（并入后）：")
    for kind, count in sorted(merged_stats["kinds"].items(), key=lambda item: -item[1]):
        print(f"  {kind:12s} {count}")
    print("\n各关系类型（并入后）：")
    for relation, count in sorted(merged_stats["relations"].items(), key=lambda item: -item[1]):
        print(f"  {relation:18s} {count}")

    restriction_counter: Counter = Counter()
    for _, _, attrs in merged.edges(data=True):
        if attrs.get("relation") in (kg.REL_FORBIDDEN_FOR, "cautions_for"):
            restriction_counter[(attrs["relation"], attrs.get("restriction_type", "?"))] += 1
    print("\nrestriction_type 分布（禁忌/需注意边）：")
    for (relation, restriction), count in sorted(restriction_counter.items()):
        print(f"  {relation:14s} restriction_type={restriction:10s} {count}")

    print(f"\nevidence_features（{len(drafts)} 份草稿）：")
    strength_counter = Counter()
    bool_counters = {key: Counter() for key in ("regulatory_restriction", "special_population_related", "risk_statement_exists")}
    for _, payload in drafts:
        features = payload.get("evidence_features") or {}
        strength_counter[features.get("evidence_strength", "none")] += 1
        for key, counter in bool_counters.items():
            counter[bool(features.get(key, False))] += 1
    print(f"  evidence_strength     " + "  ".join(f"{k}={v}" for k, v in sorted(strength_counter.items())))
    for key, counter in bool_counters.items():
        print(f"  {key:22s}True={counter[True]}  False={counter[False]}")


def print_demo_chains(merged: kg.nx.MultiDiGraph, pairs: list[tuple[str, str]]) -> None:
    print()
    print("=" * 62)
    print("二、典型多跳链路案例")
    print("=" * 62)
    for additive, group in pairs:
        chains = kg.find_explanation_chains(merged, additive, group, max_hops=3, max_paths=6)
        print(f"\n【{additive} × {group}】共 {len(chains)} 条链路")
        for chain in chains:
            marker = "  <- 多跳" if chain["hops"] >= 2 else ""
            print(f"  {chain['summary']}  [{'/'.join(chain['sources'])}]{marker}")


def collect_multihop_chains(merged: kg.nx.MultiDiGraph, drafts: list[tuple[Path, dict]]) -> list[dict]:
    """统计全部 (成分 × 人群/亚人群) 的多跳（>=2 跳）解释链路。"""
    results = []
    for _, payload in drafts:
        additive = payload["additive"]
        for group in list(kg.GROUP_TYPES) + ["哮喘者"]:
            for chain in kg.find_explanation_chains(merged, additive, group, max_hops=3, max_paths=8):
                if chain["hops"] >= 2:
                    results.append({"additive": additive, "group": group, **{k: v for k, v in chain.items() if k in ("hops", "summary", "sources")}})
    seen = set()
    unique = []
    for item in results:
        key = (item["additive"], item["summary"])
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def review_priority(payload: dict, skeleton_nodes: set) -> tuple[str, str]:
    edges = payload.get("edges") or []
    features = payload.get("evidence_features") or {}
    strength = features.get("evidence_strength", "none")
    notes = []
    if any(edge.get("relation") == "forbidden_for" for edge in edges):
        notes.append("含法规/明确禁忌边")
    new_nodes = [n for n in payload.get("nodes") or [] if n["id"] not in skeleton_nodes]
    if new_nodes:
        notes.append(f"模型新增实体 {len(new_nodes)} 个")
    if edges:
        notes.append(f"抽取边 {len(edges)} 条")
    if features.get("regulatory_restriction"):
        notes.append("原文含法规限制表述")
    if strength == "explicit":
        notes.append("证据强度 explicit")
    if any(edge.get("relation") == "forbidden_for" for edge in edges) or features.get("regulatory_restriction"):
        priority = "P0"
    elif new_nodes or edges or strength == "explicit":
        priority = "P1"
    elif strength == "suggestive":
        priority = "P2"
    else:
        priority = "P3"
    return priority, "；".join(notes) or "空抽取"


def write_checklist(drafts: list[tuple[Path, dict]], skeleton_nodes: set, multihop: list[dict]) -> Path:
    lines = [
        "# Phase 1 人工复核清单",
        "",
        f"草稿共 {len(drafts)} 份。复核通过后把 drafts/*.json 移入 reviewed/ 即并入知识图谱。",
        "优先级：P0 含法规/明确禁忌边（优先）；P1 含模型新增节点或边（重点审实体与关系是否忠实原文）；"
        "P2 仅 suggestive 证据；P3 空抽取（扫一眼 evidence_features 即可）。",
        "",
    ]
    rows = []
    for path, payload in drafts:
        priority, note = review_priority(payload, skeleton_nodes)
        rows.append((priority, path.name, payload, note))
    order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    rows.sort(key=lambda row: (order[row[0]], row[1]))

    current = None
    for priority, filename, payload, note in rows:
        if priority != current:
            current = priority
            lines.append(f"## {priority}（{sum(1 for r in rows if r[0] == priority)} 份）")
            lines.append("")
        lines.append(f"- [ ] `{filename}`  {note}")
        for edge in payload.get("edges") or []:
            restriction = f" [{edge['restriction_type']}]" if edge.get("restriction_type") else ""
            lines.append(f"      {edge['source']} --{edge['relation']}{restriction}--> {edge['target']} （{edge.get('evidence', '')}）")
        features = payload.get("evidence_features") or {}
        if features:
            flags = [key for key in ("regulatory_restriction", "special_population_related", "risk_statement_exists") if features.get(key)]
            lines.append(f"      特征: {'、'.join(flags) if flags else '无'}；强度 {features.get('evidence_strength', 'none')}")
        lines.append("")

    lines.append(f"## 多跳链路（≥2 跳，共 {len(multihop)} 条）")
    lines.append("")
    for item in multihop:
        lines.append(f"- {item['additive']} × {item['group']}：{item['summary']}  [{','.join(item['sources'])}]")
    lines.append("")

    CHECKLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    CHECKLIST_PATH.write_text("\n".join(lines), encoding="utf-8")
    return CHECKLIST_PATH


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 1 图谱质量报告")
    parser.add_argument("--chain", action="append", default=[], help="追加演示链路，格式 成分:人群（可多次）")
    parser.add_argument("--save", action="store_true", help="把人工复核清单写入 review_checklist.md")
    args = parser.parse_args()

    drafts = load_drafts()
    if not drafts:
        print(f"未在 {kg.DRAFT_DIR} 找到草稿", file=sys.stderr)
        return 1
    skeleton = kg.build_graph(include_extractions=False)
    merged = build_merged_graph(drafts)
    skeleton_nodes = set(skeleton.nodes)

    print_stats(skeleton, merged, drafts)
    pairs = [(item.split(":", 1)[0], item.split(":", 1)[1]) for item in args.chain] if args.chain else DEMO_PAIRS
    print_demo_chains(merged, pairs)

    multihop = collect_multihop_chains(merged, drafts)
    print()
    print("=" * 62)
    print(f"三、多跳链路盘点：全成分 × 人群 共 {len(multihop)} 条 ≥2 跳链路")
    print("=" * 62)
    for item in multihop:
        print(f"  {item['additive']} × {item['group']}：{item['summary']}")

    priority_counter = Counter()
    for _, payload in drafts:
        priority, _ = review_priority(payload, skeleton_nodes)
        priority_counter[priority] += 1
    print(f"\n复核优先级分布：{dict(sorted(priority_counter.items()))}（P0 最高）")

    if args.save:
        path = write_checklist(drafts, skeleton_nodes, multihop)
        print(f"\n人工复核清单已写入: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

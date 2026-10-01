"""Phase 2 标签草稿生成：990 对 (成分×人群) 初始风险标签。

标签形成方式（与确认口径一致）：法规约束 + 图谱证据 + risk_level 初始值 + 人工校准。
不使用旧 score.py / GROUP_PENALTY_RULES 生成标签（旧规则仅作 baseline 对比，见
compare_baseline.py）。

流程（复用 Phase 1 drafts → reviewed 模式）：
1. 生成草稿到 backend/data/kg/label_drafts/（每成分一个 JSON，含 9 个人群对）
2. 人工校准：编辑 calibrated_label 字段（high/medium/low/unknown），
   可填 note 说明；完成后将 review_status 改为 "reviewed"，
   并把文件移入 backend/data/kg/label_reviewed/
3. --materialize 把 label_reviewed/ 物化为 backend/data/kg_labels.csv
   （列：additive, group, risk_label, source, review_status）

初始标签规则（透明可审计，rule_hits 记录命中的规则）：
  R1 regulatory_forbidden: csv 法规禁忌（forbidden_group）命中该人群 → high
  R2 graph_forbidden: 人工复核抽取的 forbidden_for(restriction_type=forbidden)
     直达该人群 → high
  R3 risk_level 初始值: 高→high / 中→medium / 低→low
  R4 unknown: 成分不在库或 risk_level 为空 → unknown（拒判）

warns 与亚人群禁忌/注意链只进 evidence_flags 供人工参考，不自动改标签：
warns 是关联证据强度；亚人群链（如 苯丙酮尿症患者）对九大人群的适用性需人工判断。

用法（在 backend/ 目录下用 .venv 解释器执行）：
    python scripts/generate_label_drafts.py                 # 生成草稿（已存在则跳过）
    python scripts/generate_label_drafts.py --force         # 覆盖重新生成
    python scripts/generate_label_drafts.py --stats         # 只打印草稿统计
    python scripts/generate_label_drafts.py --materialize   # 校准文件 → kg_labels.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import features as fe  # noqa: E402
import knowledge_graph as kg  # noqa: E402
from data_store import load_reference_data  # noqa: E402

DRAFT_DIR = kg.KG_DATA_DIR / "label_drafts"
REVIEWED_DIR = kg.KG_DATA_DIR / "label_reviewed"
LABELS_CSV = BACKEND_DIR / "data" / "kg_labels.csv"

RISK_LEVEL_TO_LABEL = {"高": "high", "中": "medium", "低": "low"}
WARNS_ORDER = {"高": 3, "中": 2, "低": 1}


def _csv_forbidden_hit(graph, additive_id: str, group_id: str) -> dict | None:
    for attrs in (graph.get_edge_data(additive_id, group_id) or {}).values():
        if attrs.get("relation") == kg.REL_FORBIDDEN_FOR and str(attrs.get("source", "")).startswith("csv"):
            return attrs
    return None


def _graph_forbidden_hit(graph, additive_id: str, group_id: str) -> dict | None:
    for attrs in (graph.get_edge_data(additive_id, group_id) or {}).values():
        if (
            attrs.get("relation") == kg.REL_FORBIDDEN_FOR
            and attrs.get("source") == "human_reviewed"
            and attrs.get("restriction_type") == "forbidden"
        ):
            return attrs
    return None


def _warns_level(graph, additive_id: str, group_id: str) -> str | None:
    best, best_rank = None, 0
    for attrs in (graph.get_edge_data(additive_id, group_id) or {}).values():
        if attrs.get("relation") == kg.REL_WARNS:
            rank = WARNS_ORDER.get(str(attrs.get("level")), 0)
            if rank > best_rank:
                best, best_rank = attrs.get("level"), rank
    return best


def _subgroup_chain_flags(graph, additive_name: str, group: str) -> dict:
    """到亚人群的禁忌/注意链（人工复核抽取证据），供人工校准参考。"""
    forbidden, caution = set(), set()
    representative = None
    for chain in kg.find_explanation_chains(graph, additive_name, group, max_hops=3, max_paths=12):
        if chain["terminal"]["kind"] != kg.KIND_SUBGROUP:
            continue
        if representative is None:
            representative = chain["summary"]
        last = chain["steps"][-1]
        if last["relation"] == kg.REL_FORBIDDEN_FOR:
            forbidden.add(chain["terminal"]["name"])
        elif last["relation"] == "cautions_for":
            caution.add(chain["terminal"]["name"])
    return {
        "subgroup_forbidden_chain": sorted(forbidden),
        "subgroup_caution_chain": sorted(caution),
        "representative_chain": representative,
    }


def build_label_entry(graph, additive_id: str, group: str) -> dict:
    """单个 (成分, 人群) 对的初始标签与证据 flags。"""
    group_id = kg._node_id(kg.KIND_GROUP, group)
    attrs = graph.nodes[additive_id]
    name = attrs.get("name")

    rules = []
    csv_hit = _csv_forbidden_hit(graph, additive_id, group_id)
    graph_hit = _graph_forbidden_hit(graph, additive_id, group_id)
    if csv_hit:
        rules.append("regulatory_forbidden")
    if graph_hit:
        rules.append("graph_forbidden")

    if rules:
        initial = "high"
    else:
        level = str(attrs.get("risk_level") or "").strip()
        if level in RISK_LEVEL_TO_LABEL:
            initial = RISK_LEVEL_TO_LABEL[level]
        else:
            initial = "unknown"  # R4: 证据不足拒判

    flags = {
        "csv_forbidden": bool(csv_hit),
        "graph_forbidden": bool(graph_hit),
        "warns_level": _warns_level(graph, additive_id, group_id),
    }
    flags.update(_subgroup_chain_flags(graph, name, group))
    return {
        "group": group,
        "initial_label": initial,
        "rules": rules,
        "evidence_flags": flags,
        "calibrated_label": None,
        "note": "",
    }


def generate_drafts(graph, force: bool = False) -> list[Path]:
    DRAFT_DIR.mkdir(parents=True, exist_ok=True)
    written = []
    data = load_reference_data()
    for index, additive in enumerate(data.additives, start=1):
        path = DRAFT_DIR / f"{index:03d}_{additive.name}.json"
        if path.exists() and not force:
            continue
        additive_id = kg._node_id(kg.KIND_ADDITIVE, additive.name)
        payload = {
            "additive": additive.name,
            "risk_level": additive.risk_level,
            "review_status": "draft",
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "labels": [
                build_label_entry(graph, additive_id, group)
                for group in kg.GROUP_TYPES
            ],
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        written.append(path)
    return written


def draft_statistics(draft_dir: Path = DRAFT_DIR) -> dict:
    """草稿统计：标签分布 / 规则命中 / 证据 flags 覆盖 / 校准进度。"""
    from collections import Counter

    label_dist = Counter()
    rule_dist = Counter()
    flags_dist = Counter()
    calibrated = 0
    total = 0
    files = sorted(draft_dir.glob("*.json")) if draft_dir.is_dir() else []
    for path in files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        for entry in payload.get("labels", []):
            total += 1
            label = entry.get("calibrated_label") or entry.get("initial_label")
            label_dist[label] += 1
            for rule in entry.get("rules") or []:
                rule_dist[rule] += 1
            flags = entry.get("evidence_flags") or {}
            if flags.get("warns_level"):
                flags_dist["warns_level"] += 1
            if flags.get("subgroup_forbidden_chain"):
                flags_dist["subgroup_forbidden_chain"] += 1
            if flags.get("subgroup_caution_chain"):
                flags_dist["subgroup_caution_chain"] += 1
            if entry.get("calibrated_label"):
                calibrated += 1
    return {
        "files": len(files),
        "pairs": total,
        "label_dist": dict(label_dist),
        "rule_dist": dict(rule_dist),
        "flags_dist": dict(flags_dist),
        "calibrated": calibrated,
    }


def materialize(require_all_reviewed: bool = True) -> Path:
    """label_reviewed/ → kg_labels.csv。require_all_reviewed 时缺文件即退出。"""
    data = load_reference_data()
    expected = {additive.name for additive in data.additives}
    payloads = []
    missing = []
    for name in sorted(expected):
        matches = sorted(REVIEWED_DIR.glob(f"*_{name}.json")) if REVIEWED_DIR.is_dir() else []
        if not matches:
            missing.append(name)
            continue
        payloads.append(json.loads(matches[0].read_text(encoding="utf-8")))
    if require_all_reviewed and missing:
        print(f"[materialize] 缺少 {len(missing)} 个校准文件: {', '.join(missing[:5])}{'...' if len(missing) > 5 else ''}")
        print("将对应 label_drafts/ 中校准完成的文件移入 label_reviewed/ 后重试，或用 --force")
        sys.exit(1)

    rows = []
    for payload in payloads:
        additive = payload["additive"]
        status = payload.get("review_status", "reviewed")
        for entry in payload.get("labels", []):
            label = entry.get("calibrated_label") or entry.get("initial_label")
            if label not in fe.RISK_LABELS:
                raise ValueError(f"{additive} × {entry.get('group')}: 非法标签 {label!r}")
            source = "calibrated" if entry.get("calibrated_label") else "initial"
            rows.append((additive, entry["group"], label, source, status))

    LABELS_CSV.parent.mkdir(parents=True, exist_ok=True)
    with LABELS_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["additive", "group", "risk_label", "source", "review_status"])
        writer.writerows(rows)
    print(f"[materialize] 写出 {len(rows)} 对 → {LABELS_CSV}")
    return LABELS_CSV


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--force", action="store_true", help="覆盖已有草稿重新生成")
    parser.add_argument("--stats", action="store_true", help="只打印草稿统计，不生成")
    parser.add_argument("--materialize", action="store_true", help="label_reviewed/ → kg_labels.csv")
    parser.add_argument("--force-materialize", action="store_true", help="允许成分文件不全时物化")
    args = parser.parse_args()

    if args.materialize or args.force_materialize:
        materialize(require_all_reviewed=not args.force_materialize)
        return

    if args.stats:
        stats = draft_statistics()
        for key, value in stats.items():
            print(f"{key}: {value}")
        return

    graph = kg.get_graph()
    written = generate_drafts(graph, force=args.force)
    skipped = (110 - len(written)) if not args.force else 0
    print(f"[generate] 新写 {len(written)} 个草稿文件" + (f"，跳过已存在 {skipped} 个" if skipped else ""))
    print(f"[generate] 草稿目录: {DRAFT_DIR}")
    stats = draft_statistics()
    print(f"[stats] {stats}")


if __name__ == "__main__":
    main()

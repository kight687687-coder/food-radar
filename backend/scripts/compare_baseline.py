"""Phase 2 baseline 对比：旧 score.py 规则映射标签 vs 新 kg 标签的一致性统计。

定位（与确认口径一致）：旧规则仅作 baseline 对比，不参与新标签生成。
旧规则对单个 (成分, 人群) 的加权扣分：
    weighted = RISK_PENALTY[risk_level] × 首命中人群倍率（GROUP_PENALTY_RULES）
    BENEFICIAL_ADDITIVE_NAMES 内成分旧规则不计风险分（weighted = 0）
映射到等级（口径在报告中明示）：
    weighted >= 20 → high / >= 10 → medium / < 10 → low
（高=20→high；孕妇亚硝酸=中10×2.0→20→high 是旧倍率的典型抬升；低=5→low）

新标签来源：优先 backend/data/kg_labels.csv（人工校准后物化）；
若不存在则回退 label_drafts/ 的 initial_label，并明确提示「未校准」。

用法：
    python scripts/compare_baseline.py
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import knowledge_graph as kg  # noqa: E402
from data_store import load_reference_data  # noqa: E402
from score import BENEFICIAL_ADDITIVE_NAMES, GROUP_PENALTY_RULES, RISK_PENALTY  # noqa: E402

DRAFT_DIR = kg.KG_DATA_DIR / "label_drafts"
LABELS_CSV = BACKEND_DIR / "data" / "kg_labels.csv"

LEGACY_HIGH, LEGACY_MEDIUM = 20, 10


def legacy_weighted_penalty(additive, group_type: str) -> int:
    """旧 score.py 对单个 (成分, 人群) 的扣分语义（base + int(base×(倍率-1))）。"""
    if additive.name in BENEFICIAL_ADDITIVE_NAMES:
        return 0
    base = RISK_PENALTY.get(additive.risk_level, 0)
    if not base:
        return 0
    weighted = base
    for match_type, match_value, multiplier in GROUP_PENALTY_RULES.get(group_type, []):
        matched = (
            (match_type == "type" and additive.type == match_value)
            or (match_type == "name" and additive.name == match_value)
            or (match_type == "name_contains" and match_value in additive.name)
        )
        if matched:
            weighted = base + int(base * (multiplier - 1))
            break
    return weighted


def legacy_mapped_label(weighted: int) -> str:
    if weighted >= LEGACY_HIGH:
        return "high"
    if weighted >= LEGACY_MEDIUM:
        return "medium"
    return "low"


def load_new_labels() -> tuple[dict[tuple[str, str], str], bool]:
    """读 kg_labels.csv；不存在则回退 label_drafts 初始标签。返回 (labels, calibrated)。"""
    labels: dict[tuple[str, str], str] = {}
    if LABELS_CSV.is_file():
        with LABELS_CSV.open("r", encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                labels[(row["additive"], row["group"])] = row["risk_label"]
        return labels, True
    for path in sorted(DRAFT_DIR.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for entry in payload.get("labels", []):
            labels[(payload["additive"], entry["group"])] = entry["initial_label"]
    return labels, False


def main() -> None:
    new_labels, calibrated = load_new_labels()
    source = "kg_labels.csv（人工校准后）" if calibrated else "label_drafts 初始标签（未人工校准，结果为预览）"
    print(f"[baseline] 新标签来源: {source}")

    data = load_reference_data()
    total = 0
    agree = 0
    confusion: Counter = Counter()
    by_group: dict[str, Counter] = {}
    diffs = []
    for additive in data.additives:
        for group in kg.GROUP_TYPES:
            new_label = new_labels.get((additive.name, group))
            if new_label is None:
                continue
            weighted = legacy_weighted_penalty(additive, group)
            old_label = legacy_mapped_label(weighted)
            total += 1
            hit = new_label == old_label
            agree += hit
            confusion[(new_label, old_label)] += 1
            by_group.setdefault(group, Counter())[group]  # init
            by_group[group][hit] += 1
            if not hit:
                diffs.append({
                    "additive": additive.name,
                    "group": group,
                    "risk_level": additive.risk_level,
                    "new": new_label,
                    "old": old_label,
                    "old_weighted": weighted,
                })

    print(f"[baseline] 对比 {total} 对，一致 {agree} 对，一致率 {agree / total:.1%}")
    print("\n混淆矩阵（行=新标签，列=旧规则映射）:")
    levels = ("high", "medium", "low", "unknown")
    print(f"{'':>10}" + "".join(f"{lvl:>10}" for lvl in levels))
    for new in levels:
        print(f"{new:>10}" + "".join(f"{confusion[(new, old)]:>10}" for old in levels))

    print("\n按人群一致率:")
    for group in kg.GROUP_TYPES:
        stats = by_group.get(group, Counter())
        total_g = stats[True] + stats[False]
        print(f"  {group}: {stats[True]}/{total_g}" + (f" = {stats[True] / total_g:.1%}" if total_g else ""))

    print(f"\n差异对共 {len(diffs)} 个，按差异方向聚合:")
    direction = Counter((d["new"], d["old"]) for d in diffs)
    for (new, old), count in direction.most_common():
        print(f"  新={new} vs 旧={old}: {count} 对")

    print("\n典型差异示例（前 20，按差异方向分组取样）:")
    shown = Counter()
    for diff in diffs:
        key = (diff["new"], diff["old"])
        if shown[key] >= 5:
            continue
        shown[key] += 1
        print(
            f"  {diff['additive']} × {diff['group']}: 新={diff['new']} 旧={diff['old']}"
            f"（risk_level={diff['risk_level']}, 旧加权扣分={diff['old_weighted']}）"
        )
        if sum(shown.values()) >= 20:
            break


if __name__ == "__main__":
    main()

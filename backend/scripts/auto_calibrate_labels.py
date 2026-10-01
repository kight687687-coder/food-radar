"""Phase 2 标签自动校准：生成审核报告 + 初步校准结果（kg_labels_final.csv）。

三条自动校准检查（按优先级）：
  P0 新旧规则差异对（45 个）：逐对给出当前标签 / 证据来源 / 调整建议。
  P1 亚人群禁忌链覆盖对（103 个）：检查风险是否只作用于对应亚人群，
     避免将亚人群专属风险扩散为九大人群的升格依据。
  P2 regulatory_forbidden 命中对（42 个）：区分「明确禁用」与「限制/注意使用」，
     无明确禁用证据的自动降级 high → medium。

R1 证据判定规则（基于 forbidden 边的 reason 文本，全部对齐现有数据）：
  - 文本含 禁用/禁止 且主语为成分或监管（如「多国已禁用」「部分食品中禁用」）
    → 明确禁用 → 保持 high
  - 禁用主语为专属亚人群/特定场景（苯丙酮尿症患者禁用；婴儿食品禁用），
    查询人群不在适用范围 → 降级 medium（P1 亚人群不扩散原则）
    婴儿食品禁用 → 仅「儿童」适用（婴幼儿⊂儿童），孕妇等降级
  - 文本为 限制/限量/慎用/注意 表述 → 降级 medium
  - 文本仅风险描述或中性说明 → 降级 medium（不符合 high 条件）

输出：
  backend/data/kg/label_review_report.md   审核报告（含三节检查明细）
  backend/data/kg_labels_final.csv          初步校准标签表（等人工确认）
  backend/data/kg/label_reviewed/*.json     自动校准中间产物（可追溯）
  stdout 标签分布统计

用法：
    python scripts/auto_calibrate_labels.py
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import knowledge_graph as kg  # noqa: E402
from data_store import load_reference_data  # noqa: E402
from features import RISK_LABELS  # noqa: E402
from label_rules import (  # noqa: E402
    SUBGROUP_APPLICABILITY,
    SUBGROUP_TO_GROUPS,
    VERDICT_TO_LABEL,
    classify_forbidden_evidence,
)

sys.path.insert(0, str(BACKEND_DIR / "scripts"))
from compare_baseline import legacy_mapped_label, legacy_weighted_penalty, load_new_labels  # noqa: E402

DRAFT_DIR = kg.KG_DATA_DIR / "label_drafts"
REVIEWED_DIR = kg.KG_DATA_DIR / "label_reviewed"
REPORT_MD = kg.KG_DATA_DIR / "label_review_report.md"
FINAL_CSV = BACKEND_DIR / "data" / "kg_labels_final.csv"

# 人工确认口径覆盖（2026-10-01 用户确认）：
# 阿斯巴甜保持「风险等级随人群条件变化」设计——苯丙酮尿症相关人群（儿童/孕妇）
# 保持 high，其余普通人群根据证据等级（争议性表述，非明确禁用）保持 medium。
MANUAL_OVERRIDES = {
    ("阿斯巴甜", group): (
        "medium",
        "苯丙酮尿症相关人群（儿童/孕妇）保持 high，其余普通人群按证据等级 medium（人工确认）",
    )
    for group in ("老人", "糖尿病", "心血管", "减肥", "健身", "普通人群", "其他")
}


def subgroup_chain_verdict(subgroups: list[str], group: str) -> str:
    """P1：亚人群禁忌链对查询人群的适用性结论。"""
    parts = []
    for s in subgroups:
        mapped = SUBGROUP_TO_GROUPS.get(s)
        if mapped is None:
            parts.append(f"「{s}」为专属亚人群风险（{SUBGROUP_APPLICABILITY[s]}），不作为该人群升格依据")
        elif group in mapped:
            parts.append(f"「{s}」禁忌与该人群相关（{SUBGROUP_APPLICABILITY[s]}），作为人群条件化标签依据")
        else:
            parts.append(f"「{s}」禁忌链映射人群为「{'」「'.join(sorted(mapped))}」，不覆盖该人群，不作为升格依据")
    return "；".join(parts) if parts else "无亚人群禁忌链"


def diff_advice(new_label: str, old_label: str, rules: list[str], final_label: str) -> str:
    """P0：差异对调整建议说明。"""
    if "regulatory_forbidden" in rules:
        return f"R1 证据复核后校准为 {final_label}（见 R1 明细表判定依据）"
    if new_label == "medium" and old_label == "high":
        return "建议保持 medium：旧 high 来自人工固定倍率（如孕妇×着色剂×2.0），无数据依据，新口径已取消"
    if new_label == "low" and old_label == "medium":
        return "建议保持 low：旧 medium 来自类别一刀切倍率，该成分 risk_level=低（多为天然来源）"
    return f"维持初始 {new_label}"


def main() -> None:
    graph = kg.get_graph()
    data = load_reference_data()

    drafts = {}
    for path in sorted(DRAFT_DIR.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        drafts[payload["additive"]] = payload
    assert len(drafts) == len(data.additives) == 110

    # 旧规则映射标签（差异对比用）
    legacy_labels = {}
    for additive in data.additives:
        for group in kg.GROUP_TYPES:
            legacy_labels[(additive.name, group)] = legacy_mapped_label(
                legacy_weighted_penalty(additive, group)
            )

    # ---- 自动校准 ----
    r1_rows, p1_rows, p0_rows = [], [], []
    initial_dist, final_dist = Counter(), Counter()
    changes = []
    for additive in data.additives:
        payload = drafts[additive.name]
        for entry in payload["labels"]:
            group = entry["group"]
            initial = entry["initial_label"]
            initial_dist[initial] += 1
            final, note = initial, ""
            rules = entry.get("rules") or []
            flags = entry.get("evidence_flags") or {}

            if "regulatory_forbidden" in rules:  # P2：R1 证据复核
                record = kg.is_forbidden_for(graph, additive.name, group)
                reason = (record or {}).get("reason") or additive.reason
                verdict, verdict_note = classify_forbidden_evidence(reason, group)
                final = VERDICT_TO_LABEL[verdict]
                note = f"R1 证据判定={verdict}：{verdict_note}"
                r1_rows.append((additive.name, group, reason, verdict, verdict_note, initial, final))
            elif flags.get("subgroup_forbidden_chain") or flags.get("subgroup_caution_chain"):
                # P1：亚人群链仅标注适用性，不改变标签（初始规则本就未用其升格）
                note = subgroup_chain_verdict(
                    flags.get("subgroup_forbidden_chain") or flags.get("subgroup_caution_chain"), group
                )
                p1_rows.append((additive.name, group, initial, final, note))

            # 人工确认口径覆盖（最高优先级，见 MANUAL_OVERRIDES 说明）
            override = MANUAL_OVERRIDES.get((additive.name, group))
            if override is not None:
                final = override[0]
                note = f"{note}；人工确认口径：{override[1]}" if note else f"人工确认口径：{override[1]}"

            if final != initial:
                changes.append((additive.name, group, initial, final, note))
            final_dist[final] += 1

            # P0：差异对
            old = legacy_labels[(additive.name, group)]
            if old != final:
                p0_rows.append((
                    additive.name, group, initial, old, final,
                    diff_advice(initial, old, rules, final),
                ))
            entry["calibrated_label"] = final
            entry["auto_note"] = note

    # ---- 写中间产物：label_reviewed/（自动校准版） ----
    REVIEWED_DIR.mkdir(parents=True, exist_ok=True)
    for index, additive in enumerate(data.additives, start=1):
        payload = drafts[additive.name]
        payload["review_status"] = "auto_calibrated"
        payload["calibrated_at"] = datetime.now().isoformat(timespec="seconds")
        path = REVIEWED_DIR / f"{index:03d}_{additive.name}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---- 写 kg_labels_final.csv ----
    with FINAL_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["additive", "group", "risk_label", "source", "note"])
        for additive in data.additives:
            for entry in drafts[additive.name]["labels"]:
                source = "auto_calibrated" if entry["auto_note"] else "initial"
                writer.writerow([
                    additive.name, entry["group"], entry["calibrated_label"], source, entry["auto_note"],
                ])

    # ---- 写审核报告 ----
    lines = []
    lines.append("# 标签自动校准审核报告")
    lines.append("")
    lines.append(f"- 生成时间：{datetime.now().isoformat(timespec='seconds')}")
    lines.append(f"- 样本：990 对（110 成分 × 9 人群）")
    lines.append(f"- 初始标签分布：{dict(initial_dist)}")
    lines.append(f"- 校准后分布：{dict(final_dist)}")
    lines.append(f"- 自动调整：{len(changes)} 对（全部为 R1 证据复核降级 high→medium）")
    lines.append("")
    lines.append("## P2｜regulatory_forbidden 命中对检查（区分明确禁用 vs 限制/注意使用）")
    lines.append("")
    lines.append("判定规则：明确禁用表述（成分/监管层面）→ 保持 high；禁用主语为专属亚人群或特定场景且")
    lines.append("查询人群不在适用范围 → 降级 medium；限制/限量/慎用/注意表述 → 降级 medium；")
    lines.append("仅风险描述或中性说明 → 降级 medium。婴儿食品禁用仅映射「儿童」。")
    lines.append("")
    lines.append("| 成分 | 人群 | 证据文本 | 判定 | 初始 | 最终 |")
    lines.append("|---|---|---|---|---|---|")
    for name, group, reason, verdict, verdict_note, initial, final in r1_rows:
        reason_short = reason.replace("|", "／")
        lines.append(f"| {name} | {group} | {reason_short} | {verdict}（{verdict_note}） | {initial} | {final} |")
    lines.append("")
    lines.append("## P1｜亚人群禁忌/注意链覆盖对检查（亚人群风险不扩散原则）")
    lines.append("")
    lines.append("初始标签规则本就未将亚人群链作为升格依据（仅进 evidence_flags），")
    lines.append("本轮逐对标注适用性结论；R1 降级对（如阿斯巴甜×儿童）见 P2 表。")
    lines.append("")
    lines.append("| 成分 | 人群 | 标签 | 适用性结论 |")
    lines.append("|---|---|---|---|")
    for name, group, initial, final, note in p1_rows:
        lines.append(f"| {name} | {group} | {final} | {note} |")
    lines.append("")
    lines.append("## P0｜新旧规则差异对（45 个）调整建议")
    lines.append("")
    lines.append("旧规则映射口径：加权扣分 = RISK_PENALTY × 首命中人群倍率，≥20→high / ≥10→medium / <10→low。")
    lines.append("")
    lines.append(f"| 成分 | 人群 | 初始标签 | 旧规则映射 | 校准结果 | 建议 |")
    lines.append("|---|---|---|---|---|---|")
    for name, group, initial, old, final, advice in p0_rows:
        lines.append(f"| {name} | {group} | {initial} | {old} | {final} | {advice} |")
    lines.append("")
    lines.append("## 待人工复核清单（确认后进入 Phase 3）")
    lines.append("")
    lines.append(f"1. R1 复核降级 {len(changes)} 对（上表 P2 全部非 high 行）：重点确认亚硝酸钠×儿童/孕妇（文本为")
    lines.append("   「过量摄入有致癌风险」，无禁用表述故降级 medium）、明矾×儿童/孕妇（铝蓄积风险）、")
    lines.append("   咖啡因×儿童/孕妇（文本为「慎用」）是否接受降级口径；")
    lines.append("2. 保持 high 的 R1 对 5 个：苋菜红×儿童/孕妇（多国已禁用）、脱氢乙酸钠×儿童/孕妇（部分食品禁用）、")
    lines.append("   糖精钠×儿童（婴儿食品禁用）；糖精钠×孕妇降级为 medium，确认是否认可；")
    lines.append("3. 旧倍率抬升对 7 个（柠檬黄等合成色素×孕妇）维持 medium、天然色素×孕妇 5 对维持 low，确认口径。")
    lines.append("4. 【已确认调整】阿斯巴甜人群间标签：确认「风险等级随人群条件变化」设计，")
    lines.append("   苯丙酮尿症相关人群（儿童/孕妇）保持 high（亚人群禁忌链映射），")
    lines.append("   其余 7 对按证据等级降为 medium（争议性表述，非明确禁用）。")
    lines.append("   同步修订映射：苯丙酮尿症患者 → 儿童/孕妇（儿童期饮食管理、母源性苯丙酮尿症孕期管控）。")
    lines.append("")
    lines.append("## 人工确认记录（2026-10-01）")
    lines.append("")
    lines.append("1. 亚硝酸钠×儿童/孕妇降级 medium：接受（风险描述不直接升格 high）。")
    lines.append("2. 糖精钠×孕妇降级 medium：接受（婴儿食品禁用不映射孕妇，保持人群作用域约束）。")
    lines.append("3. 合成色素×孕妇 medium、天然色素×孕妇 low：接受（保留分类差异，不用旧倍率统一放大）。")
    lines.append("4. 阿斯巴甜：按上述口径调整完成（儿童/孕妇 high，其余 7 对 medium）。")
    lines.append("")
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")

    # ---- stdout 统计 ----
    print(f"[auto-calibrate] 初始分布: {dict(initial_dist)}")
    print(f"[auto-calibrate] 校准后分布: {dict(final_dist)}")
    print(f"[auto-calibrate] 自动调整 {len(changes)} 对:")
    for name, group, initial, final, note in changes:
        print(f"  {name} × {group}: {initial} -> {final}  [{note}]")
    verdict_dist = Counter(row[3] for row in r1_rows)
    print(f"[auto-calibrate] R1 判定分布: {dict(verdict_dist)}")
    print(f"[auto-calibrate] 报告: {REPORT_MD}")
    print(f"[auto-calibrate] 标签表: {FINAL_CSV} （source ∈ initial / auto_calibrated）")
    print(f"[auto-calibrate] 中间产物: {REVIEWED_DIR}（review_status=auto_calibrated）")


if __name__ == "__main__":
    main()

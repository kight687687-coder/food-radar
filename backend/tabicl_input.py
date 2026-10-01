"""TabICLv2 输入构造：Phase 3 少样本预测的输入层（不依赖 torch，可先行测试）。

设计要点：
- 上下文表（x_train/y_train）= 专家标注的 (成分×人群) 特征-标签对，
  来自 kg_labels.csv（法规约束 + 图谱证据 + risk_level 初始值 + 人工校准）；
- 查询表（x_test）= 按成分分组留出（features.split_by_additive），
  同成分的 9 个人群对不跨 train/test，评测「对未见成分的泛化」；
- 标签 = risk_label ∈ {high, medium, low, unknown}，类别型；
  unknown 是拒判标签，安全门控（置信度 + 图内距离）在模型外层处理；
- unknown 成分走同一特征管线（全默认向量），靠下游不确定性评估拒判，
  本模块不负责拒判逻辑。

TabICLv2 实际推理（tabicl 包 + GPU torch）在 Phase 3 接入；本模块
输出的 x_* / y_* 为纯 Python 数值表，可直接喂给 numpy / tabicl。
"""

from __future__ import annotations

import csv
from pathlib import Path

import features as fe
import knowledge_graph as kg

LABELS_CSV = Path(__file__).resolve().parent / "data" / "kg_labels_final.csv"


def load_labels(path: Path | None = None) -> dict[tuple[str, str], str]:
    """读物化标签表 kg_labels_final.csv → {(additive, group): risk_label}。"""
    path = path or LABELS_CSV
    if not path.is_file():
        raise FileNotFoundError(
            f"未找到 {path}；请先运行 scripts/auto_calibrate_labels.py "
            "生成自动校准标签表，人工确认后即为最终标签"
        )
    labels: dict[tuple[str, str], str] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            pair = (row["additive"], row["group"])
            if row["risk_label"] not in fe.RISK_LABELS:
                raise ValueError(f"{pair}: 非法标签 {row['risk_label']!r}")
            labels[pair] = row["risk_label"]
    return labels


def build_inputs(
    builder: fe.FeatureBuilder,
    labels: dict[tuple[str, str], str],
    *,
    test_ratio: float = 0.2,
    seed: int = 42,
    stratified: bool = False,
) -> dict:
    """构造 TabICLv2 输入：按成分分组留出划分后的特征表与标签。

    stratified=True 时按成分级 risk_level 分层留出
    （features.split_by_additive_stratified），确保 test 集覆盖高/中/低各档；
    risk_level 仅作划分依据，不进特征。

    返回 {feature_names, x_train, y_train, x_test, y_test, test_pairs}。
    有标签但无图节点的对会抛错（特征与标签必须同源对齐）。
    """
    pairs = sorted(pair for pair in labels if pair[1] in kg.GROUP_TYPES)
    if stratified:
        risk_levels = {additive.name: additive.risk_level for additive in fe.iter_risk_levels()}
        train_pairs, test_pairs = fe.split_by_additive_stratified(
            pairs, risk_levels, test_ratio=test_ratio, seed=seed
        )
    else:
        train_pairs, test_pairs = fe.split_by_additive(pairs, test_ratio=test_ratio, seed=seed)

    x_train = [builder.feature_row(name, group) for name, group in train_pairs]
    y_train = [labels[pair] for pair in train_pairs]
    x_test = [builder.feature_row(name, group) for name, group in test_pairs]
    y_test = [labels[pair] for pair in test_pairs]
    return {
        "feature_names": list(fe.FEATURE_NAMES),
        "x_train": x_train,
        "y_train": y_train,
        "x_test": x_test,
        "y_test": y_test,
        "test_pairs": test_pairs,
    }

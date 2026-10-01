"""Phase 3/3.5 TabICLv2 评测：按成分分组留出（risk_level 分层），测「对未见成分的泛化」。

评测协议（Phase 3.5 确认口径）：
- 标签：kg_labels_final.csv（法规约束 + 图谱证据 + risk_level 初始值 + 人工校准确认）
- 特征：features.FeatureBuilder 46 维（Phase 3.5 新增 7 个成分属性/证据强度特征；
  beneficial 边与 risk_level/csv 禁忌边不进特征——防标签语义泄漏）
- 划分：features.split_by_additive_stratified —— 同成分 9 人群对不跨 train/test，
  且按成分级 risk_level 分层留出，确保 test 集覆盖 high/medium/low 各档
- 模型：TabICLv2（本地 checkpoint，CPU），fit 上下文即专家标注表
- 拒判机制（安全门控，不追求强制分类）：
    confidence 门控：TabICLv2 predict_proba 的 max softmax
    OOD 门控：z-score 标准化后到训练集的 kNN 最近距离，
              阈值 = 训练集内部留一距离的 95 分位
  输出 risk-coverage 曲线（selective accuracy）观察拒判收益

输出指标：accuracy / macro F1 / high recall / confusion matrix / risk-coverage 曲线

用法（在 backend/ 目录下用 .venv 解释器执行）：
    python scripts/eval_tabicl.py [--seeds 42,7,2026] [--test-ratio 0.2] [--no-stratified]
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# 系统代理指向已关闭的本地端口，权重下载/联网前必须清空
for _var in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"):
    os.environ.pop(_var, None)
# HuggingFace 直连不可达时走国内镜像下载 TabICLv2 checkpoint
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

import numpy as np  # noqa: E402
from sklearn.metrics import f1_score, recall_score  # noqa: E402

import features as fe  # noqa: E402
import knowledge_graph as kg  # noqa: E402
import tabicl_input as ti  # noqa: E402
from data_store import load_reference_data  # noqa: E402

sys.path.insert(0, str(BACKEND_DIR / "scripts"))
from compare_baseline import legacy_mapped_label, legacy_weighted_penalty  # noqa: E402

LEVELS = ("high", "medium", "low", "unknown")

# 本地 checkpoint（hf-mirror 手动下载，避免 huggingface_hub 直连卡死）；
# 缺失时回退 allow_auto_download 自动下载
LOCAL_CKPT = BACKEND_DIR / "data" / "models" / "tabicl-classifier-v2-20260212.ckpt"

# risk-coverage 曲线输出的 coverage 采样点
COVERAGE_POINTS = (0.5, 0.6, 0.7, 0.8, 0.9, 1.0)


def knn_distances(z_train: np.ndarray, z_query: np.ndarray) -> np.ndarray:
    """z_query 每行到 z_train 的最近欧氏距离（矩阵一次算完）。"""
    diffs = (
        (z_query[:, None, :] - z_train[None, :, :]) ** 2
    ).sum(axis=2)
    return np.sqrt(diffs.min(axis=1))


def loo_distances(z_train: np.ndarray) -> np.ndarray:
    """训练集内部留一最近距离（OOD 阈值标定用）。"""
    squared = ((z_train[:, None, :] - z_train[None, :, :]) ** 2).sum(axis=2)
    np.fill_diagonal(squared, np.inf)
    return np.sqrt(squared.min(axis=1))


def evaluate_once(inputs: dict, legacy: dict, verbose: bool = False) -> dict:
    from tabicl import TabICLClassifier

    x_train = np.asarray(inputs["x_train"], dtype=np.float64)
    y_train = np.asarray(inputs["y_train"], dtype=object)
    x_test = np.asarray(inputs["x_test"], dtype=np.float64)
    y_test = list(inputs["y_test"])
    test_pairs = inputs["test_pairs"]

    model = TabICLClassifier(
        device="cpu", n_estimators=4,
        model_path=str(LOCAL_CKPT) if LOCAL_CKPT.is_file() else None,
        verbose=verbose,
    )
    model.fit(x_train, y_train)
    pred = list(model.predict(x_test))
    proba = np.asarray(model.predict_proba(x_test))
    confidence = np.max(proba, axis=1)

    # ---- 基础指标 ----
    present = [level for level in LEVELS if level in set(y_test)]
    accuracy = float(np.mean([p == t for p, t in zip(pred, y_test)]))
    macro_f1 = float(f1_score(y_test, pred, average="macro", labels=present, zero_division=0))
    per_class_recall = recall_score(y_test, pred, labels=present, average=None, zero_division=0)
    class_recall = dict(zip(present, (float(r) for r in per_class_recall)))
    high_recall = class_recall.get("high")
    confusion = Counter((t, p) for t, p in zip(y_test, pred))

    by_group: dict[str, list] = defaultdict(lambda: [0, 0])
    for (name, group), p, t in zip(test_pairs, pred, y_test):
        by_group[group][1] += 1
        by_group[group][0] += p == t

    majority = Counter(y_train).most_common(1)[0][0]
    majority_accuracy = float(np.mean([majority == t for t in y_test]))
    legacy_correct = sum(legacy.get(pair, "low") == t for pair, t in zip(test_pairs, y_test))
    legacy_accuracy = legacy_correct / len(y_test)

    # ---- 拒判门控：confidence + OOD distance ----
    mu = x_train.mean(axis=0)
    sigma = x_train.std(axis=0) + 1e-9
    z_train = (x_train - mu) / sigma
    z_test = (x_test - mu) / sigma
    ood_threshold = float(np.quantile(loo_distances(z_train), 0.95))
    ood_distance = knn_distances(z_train, z_test)
    is_ood = ood_distance > ood_threshold
    accepted = (~is_ood) & (confidence >= 0.75)
    n_rejected = int((~accepted).sum())
    if accepted.sum() > 0:
        accepted_accuracy = float(np.mean([
            p == t for p, t, keep in zip(pred, y_test, accepted) if keep
        ]))
        rejected_error_rate = float(np.mean([
            p != t for p, t, keep in zip(pred, y_test, accepted) if not keep
        ]))
    else:
        accepted_accuracy, rejected_error_rate = 0.0, 0.0

    # ---- risk-coverage 曲线（按 confidence 降序，selective accuracy）----
    order = np.argsort(-confidence)
    risk_coverage = []
    for point in COVERAGE_POINTS:
        n = max(1, int(round(point * len(y_test))))
        top = order[:n]
        sel_acc = float(np.mean([pred[i] == y_test[i] for i in top]))
        risk_coverage.append((point, sel_acc))

    return {
        "n_train": len(y_train),
        "n_test": len(y_test),
        "holdout_additives": sorted({name for name, _ in test_pairs}),
        "accuracy": accuracy,
        "macro_f1": macro_f1,
        "class_recall": class_recall,
        "high_recall": high_recall,
        "majority_class": majority,
        "majority_accuracy": majority_accuracy,
        "legacy_accuracy": legacy_accuracy,
        "confusion": confusion,
        "by_group": {g: tuple(v) for g, v in by_group.items()},
        "confidence_mean": float(confidence.mean()),
        "confidence_min": float(confidence.min()),
        "ood_threshold": ood_threshold,
        "n_rejected": n_rejected,
        "n_ood": int(is_ood.sum()),
        "accepted_accuracy": accepted_accuracy,
        "rejected_error_rate": rejected_error_rate,
        "risk_coverage": risk_coverage,
        "errors": [
            (test_pairs[i][0], test_pairs[i][1], y_test[i], pred[i],
             float(confidence[i]), float(ood_distance[i]))
            for i, (p, t) in enumerate(zip(pred, y_test)) if p != t
        ],
        "ood_rejected": [
            (test_pairs[i][0], test_pairs[i][1], y_test[i], pred[i], float(ood_distance[i]))
            for i in range(len(y_test)) if is_ood[i]
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="TabICLv2 按成分分层留出评测")
    parser.add_argument("--seeds", default="42", help="逗号分隔的随机种子列表")
    parser.add_argument("--test-ratio", type=float, default=0.2)
    parser.add_argument("--no-stratified", action="store_true", help="退回随机留出（不分层）")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    labels = ti.load_labels()
    builder = fe.FeatureBuilder()
    stratified = not args.no_stratified
    print(f"[eval] 标签表: {ti.LABELS_CSV.name}（{len(labels)} 对）| 特征维度: {len(fe.FEATURE_NAMES)}"
          f" | 分层留出: {stratified}")

    legacy = {}
    for additive in load_reference_data().additives:
        for group in kg.GROUP_TYPES:
            legacy[(additive.name, group)] = legacy_mapped_label(
                legacy_weighted_penalty(additive, group)
            )

    seeds = [int(s) for s in args.seeds.split(",")]
    results = []
    for seed in seeds:
        inputs = ti.build_inputs(
            builder, labels, test_ratio=args.test_ratio, seed=seed, stratified=stratified
        )
        print(f"[eval] seed={seed}: train {len(inputs['x_train'])} / test {len(inputs['x_test'])}"
              f"（留出 {len({name for name, _ in inputs['test_pairs']})} 成分）")
        result = evaluate_once(inputs, legacy, verbose=args.verbose)
        results.append(result)
        print(f"[eval] seed={seed}: acc={result['accuracy']:.1%} macroF1={result['macro_f1']:.3f} "
              f"high召回={('%.1f%%' % (result['high_recall'] * 100)) if result['high_recall'] is not None else 'n/a'} | "
              f"多数类 {result['majority_accuracy']:.1%} | 旧规则 {result['legacy_accuracy']:.1%}")

    # ---- 汇总（以 seed=42 为主样本）----
    main_result = results[0]
    print("\n===== TabICLv2 分层留出评测报告 =====")
    print(f"特征: {len(fe.FEATURE_NAMES)} 维 | 训练 {main_result['n_train']} 对 | "
          f"测试 {main_result['n_test']} 对 | 留出成分 {len(main_result['holdout_additives'])} 个")
    if len(results) > 1:
        accs = [r["accuracy"] for r in results]
        f1s = [r["macro_f1"] for r in results]
        print(f"多种子 accuracy: {', '.join(f'{a:.1%}' for a in accs)} → 均值 {np.mean(accs):.1%}")
        print(f"多种子 macro F1: {', '.join(f'{f:.3f}' for f in f1s)} → 均值 {np.mean(f1s):.3f}")

    r = main_result
    print(f"\n总体: acc={r['accuracy']:.1%} macroF1={r['macro_f1']:.3f} | "
          f"多数类={r['majority_accuracy']:.1%}({r['majority_class']}) | 旧规则={r['legacy_accuracy']:.1%}")
    print("分类召回率:", " | ".join(f"{level}={value:.1%}" for level, value in r["class_recall"].items()))

    print("\n混淆矩阵（行=真实，列=预测）:")
    present = [l for l in LEVELS if any(k[0] == l or k[1] == l for k in r["confusion"])]
    print(f"{'':>10}" + "".join(f"{l:>10}" for l in present))
    for true in present:
        print(f"{true:>10}" + "".join(f"{r['confusion'].get((true, p), 0):>10}" for p in present))

    print("\n拒判门控（confidence≥0.75 且 OOD 距离≤训练内 95 分位）:")
    print(f"  接受 {r['n_test'] - r['n_rejected']}/{r['n_test']} 对，接受集准确率 {r['accepted_accuracy']:.1%}")
    print(f"  拒判 {r['n_rejected']} 对（其中 OOD {r['n_ood']}），被拒样本错误率 {r['rejected_error_rate']:.1%}")
    print(f"  OOD 阈值 d95={r['ood_threshold']:.3f} | confidence mean={r['confidence_mean']:.3f} min={r['confidence_min']:.3f}")

    print("\nrisk-coverage 曲线（按 confidence 排序的 selective accuracy）:")
    print(f"  {'coverage':>10} {'sel_acc':>10}")
    for point, sel_acc in r["risk_coverage"]:
        print(f"  {point:>10.0%} {sel_acc:>10.1%}")

    print(f"\n全部错误 {len(r['errors'])} 个（conf=置信度, ood=到训练集最近距离）:")
    for name, group, truth, pred, conf, ood in r["errors"]:
        print(f"  {name} × {group}: 真实={truth} 预测={pred} (conf={conf:.3f}, ood={ood:.2f})")


if __name__ == "__main__":
    main()

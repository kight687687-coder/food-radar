"""Phase 0 环境冒烟：TabICLv2 在本项目数据规模下的双端时延实测。

只做测试，不改任何业务代码。模拟未来 Phase 2 将物化的 (成分 x 人群) 风险场景数据集：
- 990 行（110 成分 x 9 人群）x ~20 维特征
- 三分类（高/中/低），类别不平衡约 6% / 23% / 71%（与 additives.csv 真实分布一致）
- 按成分分组划分：留出 ~20% 成分（22 个 x 9 = 198 行）作测试组，检验"对新成分泛化"

实测场景：
  A. GPU   全量上下文（默认 n_estimators=8，kv_cache）
  B. CPU   全量上下文（模拟 Vercel 最坏情况）
  C. CPU   300 行分层子采样上下文（Vercel 精简模式）
  D. CPU   300 行子采样 + n_estimators=2（极限精简）
每场景测 fit（KV 缓存构建）与 predict（单请求 5 行 / 批量 198 行）时延。

用法：
  python scripts/phase0_smoke.py            # 自动选择 CUDA（不可用则全部走 CPU）
  python scripts/phase0_smoke.py --cpu-only # 强制 CPU
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import numpy as np

# 让输出即时可见（长任务下不至于看起来卡死）
def _log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ---------------------------------------------------------------------------
# 合成数据：模拟 990 对 (成分 x 人群) 风险场景
# ---------------------------------------------------------------------------

N_INGREDIENTS = 110
GROUPS = ["儿童", "孕妇", "老人", "糖尿病", "心血管", "减肥", "健身", "普通人群", "其他"]
N_GROUPS = len(GROUPS)
LABELS = ["高", "中", "低"]
RNG_SEED = 42


def build_synthetic_pairs():
    """返回 X(990, 20), y(990,), ingredient_ids(990,)。

    特征设计（图内图外均可计算的口径）：
      0-5    连续风险信号（含噪）
      6-13   添加剂类型 one-hot（8 类示意）
      14-17  名称模式二值特征（含糖/钠字样等示意）
      18     配料表位置序号 0-1
      19     人群编码 0-8
    """
    rng = np.random.default_rng(RNG_SEED)
    n = N_INGREDIENTS * N_GROUPS

    # 每个成分一个基线风险 logit，真实分布 4 高 / 26 中 / 80 低
    base_order = (
        [0] * 4 + [1] * 26 + [2] * 80
    )
    rng.shuffle(base_order)

    rows, labels, ing_ids = [], [], []
    for ing in range(N_INGREDIENTS):
        base = base_order[ing]
        ing_type = int(rng.integers(0, 8))          # 成分类型（固定）
        name_flags = rng.integers(0, 2, size=4)      # 名称模式（固定）
        position = rng.random()                     # 配料表位置（固定）
        for g in range(N_GROUPS):
            # 人群风险漂移：部分人群对任意成分整体加压；禁忌近似高漂移
            drift = 0.0
            if g in (0, 1):                          # 儿童/孕妇 更敏感
                drift += 0.35
            if base > 0 and g == 0 and rng.random() < 0.25:
                drift += 0.5                         # 模拟禁忌升级
            risk_signal = rng.normal(drift, 0.55, size=6) + (2 - base) * 0.4
            feat = np.concatenate([
                risk_signal,
                np.eye(8)[ing_type],
                name_flags.astype(float),
                [position],
                [float(g)],
            ])
            rows.append(feat)
            # 标签由信号强度决定（有结构、可学习，但保留噪声）
            score = risk_signal.mean() + (2 - base) * 0.9
            label = 2 if score < 0.35 else (1 if score < 1.1 else 0)
            labels.append(label)
            ing_ids.append(ing)

    X = np.asarray(rows, dtype=np.float32)
    y = np.asarray(labels, dtype=np.int64)
    return X, y, np.asarray(ing_ids)


def group_split(X, y, ing_ids, holdout_frac=0.2, seed=RNG_SEED):
    """按成分分组划分：整成分留出，其全部人群对进测试组。"""
    rng = np.random.default_rng(seed)
    uniq = np.unique(ing_ids)
    n_hold = int(len(uniq) * holdout_frac)
    holdout = set(rng.choice(uniq, size=n_hold, replace=False).tolist())
    mask = np.isin(ing_ids, list(holdout))
    return X[~mask], y[~mask], X[mask], y[mask], holdout


def stratified_subsample(X, y, n_target, seed=RNG_SEED):
    """按 (标签 x 人群) 分层抽样，模拟 Vercel 精简上下文。"""
    rng = np.random.default_rng(seed)
    group_col = X[:, -1].astype(int)
    strata = {}
    for i in range(len(y)):
        strata.setdefault((int(y[i]), group_col[i]), []).append(i)
    picked = []
    per = max(1, n_target // len(strata))
    for idxs in strata.values():
        picked.extend(rng.choice(idxs, size=min(per, len(idxs)), replace=False).tolist())
    picked = np.array(sorted(picked))[:n_target]
    return X[picked], y[picked]


# ---------------------------------------------------------------------------
# 计时工具
# ---------------------------------------------------------------------------

def timed(fn, label):
    t0 = time.perf_counter()
    out = fn()
    return out, time.perf_counter() - t0


CKPT = Path(__file__).resolve().parent.parent / "data" / "models" / "tabicl" / "tabicl-classifier-v2-20260212.ckpt"


def run_scenario(name, X_tr, y_tr, X_te_small, device, n_estimators):
    from tabicl import TabICLClassifier

    _log(f"开始场景 {name}: device={device}, context={len(X_tr)}, n_estimators={n_estimators}")
    clf = TabICLClassifier(
        n_estimators=n_estimators,
        kv_cache=True,
        device=device,
        allow_auto_download=True,
        model_path=str(CKPT) if CKPT.exists() else None,
        random_state=RNG_SEED,
    )
    _, t_fit = timed(lambda: clf.fit(X_tr, y_tr), f"{name}.fit")
    _, t_pred5 = timed(lambda: clf.predict(X_te_small), f"{name}.pred5")
    result = {
        "场景": name,
        "device": device,
        "上下文行数": len(X_tr),
        "n_estimators": n_estimators,
        "fit耗时(秒)": round(t_fit, 2),
        "预测5行耗时(秒)": round(t_pred5, 3),
    }
    if device == "cuda":
        import torch

        result["显存峰值(MB)"] = round(torch.cuda.max_memory_allocated() / 1024 / 1024, 1)
    _log(f"场景 {name} 完成: {result}")
    return clf, result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cpu-only", action="store_true")
    args = parser.parse_args()

    _log("生成合成数据 (990 行 x 20 维)...")
    X, y, ing_ids = build_synthetic_pairs()
    _log(f"类别分布: 高={int((y==0).sum())} 中={int((y==1).sum())} 低={int((y==2).sum())}")

    X_tr_all, y_tr_all, X_te, y_te, holdout = group_split(X, y, ing_ids)
    _log(f"成分分组划分: 训练={len(X_tr_all)}行({N_INGREDIENTS - len(holdout)}成分), "
         f"测试={len(X_te)}行({len(holdout)}成分留出)")

    X_ctx300, y_ctx300 = stratified_subsample(X_tr_all, y_tr_all, 300)
    rng = np.random.default_rng(7)
    small_idx = rng.choice(len(X_te), size=5, replace=False)
    X_small = X_te[small_idx]

    try:
        import torch

        has_cuda = torch.cuda.is_available()
    except Exception:
        has_cuda = False
    if args.cpu_only:
        has_cuda = False
    _log(f"CUDA 可用: {has_cuda}")

    results = []
    acc_rows = {}

    # A. GPU 全量
    if has_cuda:
        clf, r = run_scenario("A.GPU全量", X_tr_all, y_tr_all, X_small, "cuda", 8)
        results.append(r)
        _, t_pred_te = timed(lambda: clf.predict(X_te), "A.pred_test")
        acc = float((clf.predict(X_te) == y_te).mean())
        maj = float((y_te == np.bincount(y_tr_all).argmax()).mean())
        acc_rows["A"] = (round(acc, 3), round(maj, 3), round(t_pred_te, 2))

    # B. CPU 全量
    clf_b, r = run_scenario("B.CPU全量", X_tr_all, y_tr_all, X_small, "cpu", 8)
    results.append(r)

    # C. CPU 300 子采样
    _, r = run_scenario("C.CPU精简300", X_ctx300, y_ctx300, X_small, "cpu", 8)
    results.append(r)

    # D. CPU 300 + n_estimators=2
    _, r = run_scenario("D.CPU精简300x2", X_ctx300, y_ctx300, X_small, "cpu", 2)
    results.append(r)

    _log("=" * 78)
    _log("时延汇总：")
    header = f"{'场景':<14}{'device':<7}{'上下文':>6}{'est':>4}{'fit(s)':>9}{'pred5行(s)':>11}"
    _log(header)
    for r in results:
        _log(f"{r['场景']:<14}{r['device']:<7}{r['上下文行数']:>6}{r['n_estimators']:>4}"
             f"{r['fit耗时(秒)']:>9}{r['预测5行耗时(秒)']:>11}")
    if acc_rows:
        acc, maj, t = acc_rows["A"]
        _log(f"合成数据分组泛化 sanity（GPU）: 模型一致率={acc}, 多数类基线={maj}, 测试198行预测耗时={t}s")
    if has_cuda:
        import torch

        _log(f"GPU: {torch.cuda.get_device_name(0)}")
    _log("冒烟测试结束。")


if __name__ == "__main__":
    sys.exit(main())

"""Phase 4 集成预测器：法规兜底 + TabICLv2 少样本泛化 + 拒判门控。

六层架构决策顺序（与《评分核心改造方案》一致）：
  ⑤ 法规兜底（最高优先级）：csv forbidden_for 边命中后经 label_rules
     R1 证据复核（与标签校准同一口径）——仅「明确禁用」（ban_high，
     如多国已禁用/部分食品禁用/婴儿食品禁用映射儿童）才硬约束覆盖 high；
     限制/注意表述与亚人群作用域外的情况不覆盖，交模型层处理，
     保证「标签口径」与「运行时兜底行为」永远一致。
  ④ 拒判门控：unknown 成分（库外）与无效人群直接拒判；
     模型置信度 < confidence_threshold 或特征空间 OOD 距离 > 阈值 → 拒判
     （label=unknown，返回「证据不足」而非强制分类）。
  ③ TabICLv2 泛化：全量专家标注表（990 对）作 in-context 上下文，
     负责法规未覆盖的 medium/low 边界泛化（评测证实 high 由兜底层负责，
     极小类泛化不是模型的职责——见 Phase 3.5 评测报告）。

输入输出：predict(additive_text, group_type) →
{
  "additive", "group", "label": high/medium/low/unknown,
  "source": "regulatory" / "model" / "rejected",
  "confidence": float, "ood_distance": float,
  "reason": 结论依据（法规文本 / 模型置信度 / 拒判原因）,
  "explanation_chains": 图谱解释链摘要（可解释性）,
}
"""

from __future__ import annotations

import os
from pathlib import Path
from threading import Lock

import numpy as np

# Vercel（Lambda 类环境）HOME 只读，HuggingFace 默认缓存路径不可写；
# 权重未随 bundle 打包（超 100MB 上传上限）时由 tabicl 从 Hub 下载到 /tmp。
if os.getenv("VERCEL"):
    os.environ.setdefault("HF_HOME", "/tmp/hf")

import features as fe
import knowledge_graph as kg
import tabicl_input as ti
from label_rules import classify_forbidden_evidence

CKPT_PATH = Path(__file__).resolve().parent / "data" / "models" / "tabicl-classifier-v2-20260212.ckpt"
DEFAULT_CONFIDENCE_THRESHOLD = 0.75
DEFAULT_OOD_QUANTILE = 0.99  # Phase 3.5 评测：d95 过紧（误拒正确样本），放宽至 d99


def _nearest_distances(z_train: np.ndarray, z_query: np.ndarray, leave_one_out: bool = False) -> np.ndarray:
    """z_query 每行到 z_train 的最近欧氏距离；leave_one_out 时对训练集自身留一。"""
    squared = ((z_query[:, None, :] - z_train[None, :, :]) ** 2).sum(axis=2)
    if leave_one_out:
        np.fill_diagonal(squared, np.inf)
    return np.sqrt(squared.min(axis=1))


class RiskPredictor:
    def __init__(
        self,
        graph=None,
        builder: fe.FeatureBuilder | None = None,
        labels: dict | None = None,
        *,
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
        ood_quantile: float = DEFAULT_OOD_QUANTILE,
        n_estimators: int = 4,
        device: str = "cpu",
        fit_model: bool = True,
    ):
        self.graph = graph if graph is not None else kg.get_graph()
        self.builder = builder if builder is not None else fe.FeatureBuilder(self.graph)
        self.labels = labels if labels is not None else ti.load_labels()
        self.confidence_threshold = confidence_threshold
        self.ood_quantile = ood_quantile
        self._n_estimators = n_estimators
        self._device = device
        self._model = None
        self._mu = self._sigma = self._ood_threshold = None
        if fit_model:
            self._fit()

    # ---- 模型上下文 ----

    def _fit(self) -> None:
        from tabicl import TabICLClassifier

        pairs = [(additive.name, group) for additive, group in fe.iter_all_pairs()]
        x_train = np.asarray(
            [self.builder.feature_row(name, group) for name, group in pairs], dtype=np.float64
        )
        y_train = np.asarray([self.labels[pair] for pair in pairs], dtype=object)

        self._model = TabICLClassifier(
            device=self._device,
            n_estimators=self._n_estimators,
            model_path=str(CKPT_PATH) if CKPT_PATH.is_file() else None,
        )
        self._model.fit(x_train, y_train)

        self._mu = x_train.mean(axis=0)
        self._sigma = x_train.std(axis=0) + 1e-9
        z_train = (x_train - self._mu) / self._sigma
        self._z_train = z_train  # predict 时 OOD 距离复用
        self._ood_threshold = float(
            np.quantile(_nearest_distances(z_train, z_train, leave_one_out=True), self.ood_quantile)
        )

    # ---- 推理 ----

    def _model_probabilities(self, rows: list[list[float]]) -> tuple[list[str], np.ndarray]:
        proba = np.asarray(self._model.predict_proba(np.asarray(rows, dtype=np.float64)))
        classes = list(self._model.classes_)
        best = proba.argmax(axis=1)
        return [classes[i] for i in best], proba[np.arange(len(best)), best]

    def predict_batch(self, pairs: list[tuple[str, str | None]]) -> list[dict]:
        """批量预测 (成分, 人群) 对；单对 predict 是本函数的便捷封装。"""
        results: list[dict] = []
        pending: list[tuple[int, list[float]]] = []

        for index, (additive_text, group) in enumerate(pairs):
            group = (group or "").strip()
            base = {
                "additive": additive_text, "group": group,
                "label": "unknown", "source": "rejected",
                "confidence": 0.0, "ood_distance": float("inf"),
                "reason": "", "explanation_chains": [],
            }
            # ④-1 库外成分：直接拒判（不做强制泛化），特征管线仍同构返回默认向量
            additive_id = kg.resolve_additive(self.graph, additive_text)
            if additive_id is None:
                base["reason"] = "成分不在知识库中（unknown），证据不足拒判"
                results.append(base)
                continue
            # ④-2 无效人群：九大人群标签空间外，同样拒判
            if group not in kg.GROUP_TYPES:
                base["reason"] = f"人群「{group}」无效（不在九大人群内），拒判"
                results.append(base)
                continue
            # ⑤ 法规兜底：csv forbidden_for 边经 R1 证据复核（label_rules，与标签
            # 校准同一口径）——仅「明确禁用」（ban_high）才硬约束覆盖 high；
            # 限制/注意/亚人群作用域外的情况不覆盖，交模型/标签口径处理。
            name = self.graph.nodes[additive_id].get("name", additive_text)
            record = kg.is_forbidden_for(self.graph, name, group)
            if record:
                reason_text = record.get("reason") or name
                verdict, verdict_note = classify_forbidden_evidence(reason_text, group)
                if verdict == "ban_high":
                    base.update({
                        "label": "high", "source": "regulatory", "confidence": 1.0,
                        "ood_distance": 0.0,
                        "reason": f"法规明确禁用（{group}）：{reason_text}｜{verdict_note}",
                    })
                    self._attach_chains(base, name, group)
                    results.append(base)
                    continue
            # ③/④ 模型泛化 + 门控：先攒批，再统一推理
            pending.append((index, self.builder.feature_row(name, group), name))
            results.append(base)

        if pending:
            if self._model is None:
                # fit_model=False（规则测试模式）：模型分支不可用，明确拒判而非静默通过
                for index, _, _ in pending:
                    results[index]["reason"] = "模型未加载（fit_model=False 规则测试模式）"
                return results
            indices = [index for index, _, _ in pending]
            rows = [row for _, row, _ in pending]
            labels, confidences = self._model_probabilities(rows)
            z_test = (np.asarray(rows, dtype=np.float64) - self._mu) / self._sigma
            ood_distances = _nearest_distances(self._z_train, z_test)
            for slot, (index, _, name) in enumerate(pending):
                result = results[index]
                confidence = float(confidences[slot])
                ood_distance = float(ood_distances[slot])
                result["confidence"] = confidence
                result["ood_distance"] = ood_distance
                if confidence < self.confidence_threshold:
                    result["reason"] = (
                        f"模型置信度不足（{confidence:.2f} < {self.confidence_threshold}），拒判"
                    )
                    continue
                if ood_distance > self._ood_threshold:
                    result["reason"] = (
                        f"特征空间超出已知范围（OOD 距离 {ood_distance:.2f} > 阈值 {self._ood_threshold:.2f}），拒判"
                    )
                    continue
                result["label"] = labels[slot]
                result["source"] = "model"
                result["reason"] = (
                    f"TabICLv2 少样本泛化预测 {labels[slot]}（置信度 {confidence:.2f}）"
                )
                self._attach_chains(result, name, result["group"])
        return results

    def _attach_chains(self, result: dict, name: str, group: str) -> None:
        """补充图谱解释链（可解释性；找不到链路不报错）。"""
        if group not in kg.GROUP_TYPES:
            return
        try:
            chains = kg.find_explanation_chains(self.graph, name, group, max_paths=3)
        except Exception:
            return
        result["explanation_chains"] = [chain["summary"] for chain in chains]

    def predict(self, additive_text: str, group_type: str | None) -> dict:
        return self.predict_batch([(additive_text, group_type)])[0]


# 进程内单例（fit 一次约 1 分钟，避免重复初始化）
_PREDICTOR_CACHE: RiskPredictor | None = None
_PREDICTOR_LOCK = Lock()


def get_predictor(force_reload: bool = False) -> RiskPredictor:
    """进程内单例，双检锁防止并发首次请求触发双 fit
    （Flask threaded=True 下两个线程同时看到 None 会各自 fit：
    2×冷启动 CPU + 2×约 700MB 内存）。"""
    global _PREDICTOR_CACHE
    if _PREDICTOR_CACHE is None or force_reload:
        with _PREDICTOR_LOCK:
            if _PREDICTOR_CACHE is None or force_reload:
                _PREDICTOR_CACHE = RiskPredictor()
    return _PREDICTOR_CACHE

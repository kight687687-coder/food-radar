"""Phase 2/3.5 特征工程：(成分, 人群) → 固定维度风险证据特征向量。

设计原则（与确认口径一致）：
1. 防泄漏铁律：additive 节点的 risk_level 属性与 csv 来源的 forbidden_for 边
   （即 additives.csv forbidden_group 字段）是专家标注标签，绝不进入特征；
   beneficial 边不进入风险预测模型（仅用于知识展示，避免标签语义泄漏）。
   单元测试中有对应的不变量断言（改标签不动特征）。
2. warns 边编码为「关联证据强度」序数（高3/中2/低1/无0），
   仅为证据强度信号，不直接等价风险等级。
3. unknown 成分（图中无节点）与 known 成分走同一条管线：
   返回同维度全默认值向量、不抛异常——供下游不确定性门控拒判。

特征分组（46 维，顺序固定，见 FEATURE_NAMES）：
- 成分侧 33 维：evidence_strength_ordinal / regulatory_restriction /
  special_population_related / risk_statement_exists / has_gb_standard /
  natural_source / nutrient_related / synthetic_origin / evidence_density /
  evidence_count / risk_relation_count / population_relation_count /
  category one-hot(20)
- 成分×人群交互 5 维：warns_level_ordinal / chain_min_hops /
  chain_reachable_2hop / chain_has_risk_relation / chain_reaches_subgroup
- 人群侧 9 维：group one-hot

Phase 3.5 新增成分属性特征（从 reason/standard 文本与证据子图结构派生，
不使用 beneficial 边与任何标签）：natural_source（天然来源标记）/
nutrient_related（营养相关表述，如钙磷平衡、维生素）/ synthetic_origin
（人工/合成标记）/ evidence_density（证据子图出边密度，全局 max 归一化）；
证据强度特征：evidence_count（evidence_features 非零项计数）/
risk_relation_count（证据子图中风险类关系边数）/
population_relation_count（证据子图直连人群/亚人群节点数）。

链路特征在「证据子图」上计算：剔除 csv 标签禁忌边与 beneficial 展示边，
保留 warns、LLM 抽取（human_reviewed）的 forbidden_for / cautions_for 及
contains_component / converts_to / metabolizes_to / triggers / harms /
associated_with；路径不经过类别/法规依据等结构节点（不构成因果解释）。
csv 禁忌边被剔除后，子图中出现的 forbidden_for 一律是人工复核的抽取证据。
"""

from __future__ import annotations

import random
import re

import networkx as nx

import knowledge_graph as kg
from data_store import load_reference_data

# 证据强度序数（成分级，来自 evidence_features，非标签）
EVIDENCE_STRENGTH_ORDINAL = {"explicit": 2.0, "suggestive": 1.0, "none": 0.0}

# warns 边关联证据强度序数（高/中/低 → 3/2/1，无边为 0）
WARNS_LEVEL_ORDINAL = {"高": 3.0, "中": 2.0, "低": 1.0}

# 链路中视为「风险证据」的关系：禁忌/注意/触发/损害/风险关联/体内转化/代谢。
# contains_component 是链路结构关系（含某成分），不单独构成风险证据。
RISK_CHAIN_RELATIONS = frozenset({
    kg.REL_FORBIDDEN_FOR,
    "cautions_for",
    "triggers",
    "harms",
    "associated_with",
    "converts_to",
    "metabolizes_to",
})

# 类别 one-hot 的固定取值顺序（与当前图一致；未见过的类别自然全 0，与 unknown 同构）
CATEGORIES = (
    "乳化剂", "其他", "凝固剂", "增味剂", "增稠剂", "抗氧化剂", "抗结剂", "护色剂",
    "水分保持剂", "消泡剂", "漂白剂", "甜味剂", "着色剂", "稳定剂", "膨松剂",
    "营养强化剂", "被膜剂", "酸度调节剂", "防腐剂", "面粉处理剂",
)

# 监督标签空间（kg_labels.csv 的 risk_label 取值；仅作监督信号，不是特征）
RISK_LABELS = ("high", "medium", "low", "unknown")

_ADDITIVE_FEATURE_NAMES = (
    "evidence_strength_ordinal",
    "regulatory_restriction",
    "special_population_related",
    "risk_statement_exists",
    "has_gb_standard",
    "natural_source",
    "nutrient_related",
    "synthetic_origin",
    "evidence_density",
    "evidence_count",
    "risk_relation_count",
    "population_relation_count",
)

# 成分属性文本判词（Phase 3.5；依据现有 reason/standard 语料校准）：
# - 天然来源：天然色素/天然抗氧化剂/从植物提取/发酵制得等
# - 营养相关：维生素/矿物质/氨基酸/膳食纤维/蛋白质/钙磷平衡/营养强化等
# - 合成来源：人工甜味剂/人工合成色素/化学合成等
_NATURAL_PATTERN = re.compile(r"天然|提取自|从[^，。;；]{0,8}提取|发酵|来源于植物")
_NUTRIENT_PATTERN = re.compile(r"维生素|矿物质|氨基酸|膳食纤维|蛋白质|钙磷|营养")
_SYNTHETIC_PATTERN = re.compile(r"人工|合成|化工|石油")

# 人群关联关系（population_relation_count 统计用；均在证据子图内，
# 人工复核的 forbidden_for 允许，csv 标签边已被剔除）
_POPULATION_RELATIONS = frozenset({kg.REL_WARNS, "cautions_for", kg.REL_FORBIDDEN_FOR})
_INTERACTION_FEATURE_NAMES = (
    "warns_level_ordinal",
    "chain_min_hops",
    "chain_reachable_2hop",
    "chain_has_risk_relation",
    "chain_reaches_subgroup",
)

FEATURE_NAMES: tuple[str, ...] = (
    _ADDITIVE_FEATURE_NAMES
    + tuple(f"category_{name}" for name in CATEGORIES)
    + _INTERACTION_FEATURE_NAMES
    + tuple(f"group_{name}" for name in kg.GROUP_TYPES)
)


def _is_excluded_edge(attrs: dict) -> bool:
    """标签边（csv 禁忌）与展示边（beneficial）不入证据子图。"""
    relation = attrs.get("relation")
    if relation == kg.REL_BENEFICIAL:
        return True
    if relation == kg.REL_FORBIDDEN_FOR and str(attrs.get("source", "")).startswith("csv"):
        return True
    return False


class FeatureBuilder:
    """在一张知识图谱上批量计算 (成分, 人群) 特征。

    链路证据按成分缓存：每个成分只做一次 ≤max_hops 的路径枚举，
    9 个人群复用结果。
    """

    def __init__(self, graph: nx.MultiDiGraph | None = None, max_hops: int = 3):
        self.graph = graph if graph is not None else kg.get_graph()
        self.max_hops = max_hops
        self._evidence_graph = self._build_evidence_graph()
        self._chain_cache: dict[str, dict] = {}
        self._evidence_counts, self._density_max = self._count_evidence_edges()

    def _count_evidence_edges(self) -> tuple[dict[str, int], int]:
        """成分级证据统计：{additive_id: 出边数} 与全局最大值（evidence_density 归一化用）。"""
        counts = {
            node_id: self._evidence_graph.out_degree(node_id)
            for node_id, attrs in self.graph.nodes(data=True)
            if attrs.get("kind") == kg.KIND_ADDITIVE
        }
        return counts, max(counts.values(), default=0) or 1

    # ---- 图准备 ----

    def _build_evidence_graph(self) -> nx.MultiDiGraph:
        sub = nx.MultiDiGraph()
        sub.add_nodes_from(self.graph.nodes(data=True))
        sub.add_edges_from(
            (u, v, key, attrs)
            for u, v, key, attrs in self.graph.edges(keys=True, data=True)
            if not _is_excluded_edge(attrs)
        )
        return sub

    def _is_structural(self, node_id: str) -> bool:
        return self.graph.nodes[node_id].get("kind") in kg._NON_CAUSAL_KINDS

    # ---- 链路证据 ----

    def _path_has_risk_relation(self, path: list[str]) -> bool:
        for u, v in zip(path, path[1:]):
            for endpoints in ((u, v), (v, u)):
                for attrs in (self._evidence_graph.get_edge_data(*endpoints) or {}).values():
                    if attrs.get("relation") in RISK_CHAIN_RELATIONS:
                        return True
        return False

    def _chain_evidence(self, additive_id: str) -> dict:
        """per 成分缓存：到各人群的最短跳数/风险关系命中，及亚人群可达性。"""
        cached = self._chain_cache.get(additive_id)
        if cached is not None:
            return cached

        targets = [
            node_id for node_id, attrs in self.graph.nodes(data=True)
            if attrs.get("kind") in (kg.KIND_GROUP, kg.KIND_SUBGROUP)
        ]
        undirected = self._evidence_graph.to_undirected(as_view=True)

        group_stats: dict[str, dict] = {}
        subgroup_reachable = False
        subgroup_risk_relation = False
        for target in targets:
            is_group = self.graph.nodes[target].get("kind") == kg.KIND_GROUP
            min_hops = 0
            risk_relation = False
            for path in nx.all_simple_paths(undirected, additive_id, target, cutoff=self.max_hops):
                if any(self._is_structural(node_id) for node_id in path):
                    continue
                hops = len(path) - 1
                if min_hops == 0 or hops < min_hops:
                    min_hops = hops
                if not risk_relation and self._path_has_risk_relation(path):
                    risk_relation = True
            if is_group:
                group_stats[target] = {"min_hops": min_hops, "risk_relation": risk_relation}
            elif min_hops:
                subgroup_reachable = True
                if risk_relation:
                    subgroup_risk_relation = True

        evidence = {
            "group_stats": group_stats,
            "subgroup_reachable": subgroup_reachable,
            # 亚人群禁忌/注意链是成分级人群敏感证据，对 9 人群标签均有参考意义
            "subgroup_risk_relation": subgroup_risk_relation,
        }
        self._chain_cache[additive_id] = evidence
        return evidence

    # ---- 特征计算 ----

    def _warns_level(self, additive_id: str, group_id: str) -> float:
        best = 0.0
        for attrs in (self._evidence_graph.get_edge_data(additive_id, group_id) or {}).values():
            if attrs.get("relation") == kg.REL_WARNS:
                best = max(best, WARNS_LEVEL_ORDINAL.get(str(attrs.get("level")), 0.0))
        return best

    def features(self, additive_text: str | None, group_type: str | None) -> dict[str, float]:
        """单对特征：返回 {特征名: 值}。unknown 成分返回全默认值（人群 one-hot 仍生效）。"""
        row = {name: 0.0 for name in FEATURE_NAMES}
        group = (group_type or "").strip()
        if group in kg.GROUP_TYPES:
            row[f"group_{group}"] = 1.0

        additive_id = kg.resolve_additive(self.graph, additive_text)
        if additive_id is None:
            return row  # unknown 成分：除人群 one-hot 外全默认

        attrs = self.graph.nodes[additive_id]
        evidence = attrs.get("evidence_features") or {}
        row["evidence_strength_ordinal"] = EVIDENCE_STRENGTH_ORDINAL.get(
            str(evidence.get("evidence_strength", "none")), 0.0
        )
        row["regulatory_restriction"] = float(bool(evidence.get("regulatory_restriction")))
        row["special_population_related"] = float(bool(evidence.get("special_population_related")))
        row["risk_statement_exists"] = float(bool(evidence.get("risk_statement_exists")))
        row["has_gb_standard"] = float(bool(attrs.get("standard")))

        # Phase 3.5 成分属性特征：文本派生（reason/standard，非标签）
        reason = str(attrs.get("reason") or "")
        row["natural_source"] = float(bool(_NATURAL_PATTERN.search(reason)))
        row["nutrient_related"] = float(bool(_NUTRIENT_PATTERN.search(reason)))
        row["synthetic_origin"] = float(bool(_SYNTHETIC_PATTERN.search(reason)))

        # Phase 3.5 证据强度特征：evidence_features 计数 + 证据子图结构统计
        row["evidence_count"] = (
            row["regulatory_restriction"]
            + row["special_population_related"]
            + row["risk_statement_exists"]
            + row["evidence_strength_ordinal"]
        )
        row["evidence_density"] = self._evidence_counts.get(additive_id, 0) / self._density_max
        risk_edges = population_targets = 0
        seen_targets: set[str] = set()
        for _, target, edge_attrs in self._evidence_graph.out_edges(additive_id, data=True):
            relation = edge_attrs.get("relation")
            if relation in RISK_CHAIN_RELATIONS:
                risk_edges += 1
            if relation in _POPULATION_RELATIONS and target not in seen_targets:
                if self.graph.nodes[target].get("kind") in (kg.KIND_GROUP, kg.KIND_SUBGROUP):
                    seen_targets.add(target)
                    population_targets += 1
        row["risk_relation_count"] = float(risk_edges)
        row["population_relation_count"] = float(population_targets)

        category = attrs.get("type")
        if category in CATEGORIES:
            row[f"category_{category}"] = 1.0

        group_id = kg._node_id(kg.KIND_GROUP, group) if group in kg.GROUP_TYPES else None
        if group_id is not None:
            row["warns_level_ordinal"] = self._warns_level(additive_id, group_id)

        chain = self._chain_evidence(additive_id)
        if group_id is not None:
            stats = chain["group_stats"].get(group_id, {"min_hops": 0, "risk_relation": False})
            row["chain_min_hops"] = float(stats["min_hops"])
            row["chain_reachable_2hop"] = float(stats["min_hops"] >= 2)
            row["chain_has_risk_relation"] = float(
                stats["risk_relation"] or chain["subgroup_risk_relation"]
            )
        row["chain_reaches_subgroup"] = float(chain["subgroup_reachable"])
        return row

    def feature_row(self, additive_text: str | None, group_type: str | None) -> list[float]:
        """按 FEATURE_NAMES 顺序返回定长向量。"""
        row = self.features(additive_text, group_type)
        return [row[name] for name in FEATURE_NAMES]

    def assert_label_isolation(self) -> None:
        """防泄漏自检：剔除全部标签边/展示边后重算，特征必须逐位一致。

        剔除对象 = csv 禁忌边（forbidden_group 标签）与 beneficial 展示边；
        风险等级标签本身不存于任何边，天然不在特征路径上。
        供测试与 CI 调用；若不一致抛 AssertionError。
        """
        stripped = self.graph.copy()
        for u, v, key, attrs in list(stripped.edges(keys=True, data=True)):
            if _is_excluded_edge(attrs):
                stripped.remove_edge(u, v, key)
        # 把 risk_level 标签属性从副本上抹掉，特征也不应变化
        for _, attrs in stripped.nodes(data=True):
            attrs.pop("risk_level", None)
        twin = FeatureBuilder(stripped, max_hops=self.max_hops)
        for additive, group in iter_all_pairs():
            left = self.feature_row(additive.name, group)
            right = twin.feature_row(additive.name, group)
            assert left == right, f"特征随标签泄漏: {additive.name} × {group}"


def iter_all_pairs():
    """全部 (成分, 人群) 对：110 × 9 = 990，成分按 CSV 顺序。"""
    data = load_reference_data()
    for additive in data.additives:
        for group in kg.GROUP_TYPES:
            yield additive, group


def iter_risk_levels() -> tuple:
    """全部成分记录（AdditiveRecord，含成分级 risk_level）。

    risk_level 属于专家标签，仅用于评测划分/报告展示，严禁进入模型特征。
    """
    return load_reference_data().additives


def build_dataset(builder: FeatureBuilder | None = None) -> dict:
    """构建整表：{feature_names, rows, pairs}。pairs 为 [(additive, group), ...]。"""
    builder = builder or FeatureBuilder()
    pairs = [(additive.name, group) for additive, group in iter_all_pairs()]
    rows = [builder.feature_row(name, group) for name, group in pairs]
    return {"feature_names": list(FEATURE_NAMES), "rows": rows, "pairs": pairs}


def split_by_additive(
    pairs: list[tuple[str, str]],
    test_ratio: float = 0.2,
    seed: int = 42,
) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """按成分分组留出划分：同一成分的全部人群对不跨 train/test。

    少样本场景下防止「同成分换人群」的信息泄漏，评测回答的问题是
    「模型能否泛化到训练中从未见过的成分」。
    """
    additives = sorted({name for name, _ in pairs})
    rng = random.Random(seed)
    rng.shuffle(additives)
    holdout = set(additives[: max(1, int(len(additives) * test_ratio))])
    train = [pair for pair in pairs if pair[0] not in holdout]
    test = [pair for pair in pairs if pair[0] in holdout]
    return train, test


def split_by_additive_stratified(
    pairs: list[tuple[str, str]],
    additive_risk_levels: dict[str, str],
    test_ratio: float = 0.2,
    seed: int = 42,
) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """按成分级 risk_level 分层留出：确保测试集覆盖高/中/低各风险档。

    risk_level 在此仅作为评测协议的分层依据（哪些成分进 test），
    不进入特征或模型输入，与防泄漏铁律不冲突。
    每档至少留出 1 个成分（高险成分稀缺，仅 4 个，逐档保底）。
    """
    by_level: dict[str, list[str]] = {}
    for name in sorted({name for name, _ in pairs}):
        by_level.setdefault(additive_risk_levels.get(name, "低"), []).append(name)
    rng = random.Random(seed)
    holdout: set[str] = set()
    for names in by_level.values():
        pool = list(names)
        rng.shuffle(pool)
        n_hold = max(1, int(round(len(pool) * test_ratio)))
        holdout.update(pool[:n_hold])
    train = [pair for pair in pairs if pair[0] not in holdout]
    test = [pair for pair in pairs if pair[0] in holdout]
    return train, test

"""轻量领域知识图谱：CSV 结构化骨架 + 人工复核后的 LLM 抽取证据 + 多跳解释链路检索。

知识来源分级（按可信度）：
1. csv:*          additives / group_warnings / beneficial_ingredients 机读直接建边
2. derived:*      按现行 score.py 匹配语义派生的关联边
                 （如添加剂名含预警营养素 → 派生 预警 边，保持与旧评分口径一致）
3. human_reviewed DeepSeek 从 reason/standard 文本抽取、经人工复核入库的证据
                 （backend/data/kg/reviewed/*.json，build_graph 自动并入）

草稿目录 backend/data/kg/drafts/ 中的内容不参与建图，人工复核通过后移入
reviewed/ 目录才生效——「LLM 抽取 + 人工复核」是图的节点与边来源之一。

多跳链路示例（依赖 reviewed 抽取数据）：
    阿斯巴甜 --含--> 苯丙氨酸 --禁忌于--> 苯丙酮尿症患者

标签防泄漏约束（Phase 2 特征管线必须遵守）：
    additive 节点的 risk_level 属性与 forbidden_for 边属于专家标注标签，
    只能用作监督信号，严禁混入模型特征。
    节点属性 evidence_features 是 reason/standard 文本派生的证据特征（非标签），
    可以入特征；unknown 成分无该属性，特征管线须给默认值（全 false + "none"）。
"""

from __future__ import annotations

import itertools
import json
import sys
from collections import Counter
from pathlib import Path

import networkx as nx

from data_store import load_reference_data


KG_DATA_DIR = Path(__file__).resolve().parent / "data" / "kg"
DRAFT_DIR = KG_DATA_DIR / "drafts"
REVIEWED_DIR = KG_DATA_DIR / "reviewed"

# ---- 节点类型 ----
KIND_ADDITIVE = "additive"    # 添加剂/成分
KIND_CATEGORY = "category"    # 功能类别（甜味剂/防腐剂...）
KIND_GROUP = "group"          # 九大人群
KIND_SUBGROUP = "subgroup"    # 敏感亚人群（哮喘者/苯丙酮尿症患者等，不在九大人群内）
KIND_SUBSTANCE = "substance"  # 中间物质/营养素（苯丙氨酸/亚硝胺/膳食纤维...）
KIND_EVIDENCE = "evidence"    # 法规依据（GB2760-2024）

GROUP_TYPES = ("儿童", "孕妇", "老人", "糖尿病", "心血管", "减肥", "健身", "普通人群", "其他")

# forbidden_group 中的「无禁忌」占位词，不作为人群建边
FORBIDDEN_TOKEN_BLACKLIST = {"无", "无禁忌", "-", "—", "无人群", ""}

# ---- 边关系 ----
REL_BELONGS_TO = "belongs_to"       # 添加剂 -属于-> 类别
REL_FORBIDDEN_FOR = "forbidden_for"  # -禁忌于-> 人群/亚人群（法规硬约束，标签）
REL_WARNS = "warns"                 # -预警->{level 高/中/低}-> 人群
REL_BENEFICIAL = "beneficial"       # -有益于-> 人群
REL_BASED_ON = "based_on"           # 添加剂 -依据-> 法规标准

# LLM 抽取允许的关系白名单（人工复核后入库）
LLM_RELATIONS = frozenset({
    "contains_component",  # 含某成分/物质（语义上的组成或含有，不要求严格化学组成）
    "converts_to",        # 体内可转化为
    "metabolizes_to",     # 体内代谢为
    "triggers",           # 可能诱发
    "harms",              # 损害
    "associated_with",    # 与…风险关联
    "forbidden_for",      # 对某人群禁忌/限制
    "cautions_for",       # 某人群需注意
})

# forbidden_for / cautions_for 边的限制类型
RESTRICTION_TYPES = ("forbidden", "warning", "attention")

# 成分级文本证据特征（Phase 2 特征工程输入；由 reason/standard 文本结构化而来，
# 与 risk_level 标签无关。unknown 成分无此属性，特征管线需给默认值：
# 全 false + evidence_strength="none"）
EVIDENCE_FEATURE_KEYS = (
    "regulatory_restriction",    # 原文是否提及法规限制/缩紧/禁用/多国限制
    "special_population_related",  # 原文是否提及特殊人群
    "risk_statement_exists",     # 原文是否存在明确风险陈述
    "evidence_strength",         # explicit / suggestive / none
)
EVIDENCE_STRENGTHS = ("explicit", "suggestive", "none")

RELATION_LABELS = {
    REL_BELONGS_TO: "属于",
    REL_FORBIDDEN_FOR: "禁忌于",
    REL_WARNS: "预警",
    REL_BENEFICIAL: "有益于",
    REL_BASED_ON: "依据",
    "contains_component": "含成分",
    "converts_to": "可转化为",
    "metabolizes_to": "代谢为",
    "triggers": "可能诱发",
    "harms": "损害",
    "associated_with": "风险关联",
    "cautions_for": "需注意",
}

# 解释链路取边时的关系优先级（值越小越优先）
_RELATION_PRIORITY = {
    REL_FORBIDDEN_FOR: 0,
    REL_WARNS: 1,
    "cautions_for": 2,
    "harms": 3,
    "triggers": 4,
    "contains_component": 5,
    "converts_to": 6,
    "metabolizes_to": 7,
    "associated_with": 8,
    REL_BENEFICIAL: 9,
    REL_BELONGS_TO: 10,
    REL_BASED_ON: 11,
}

# 解释链路不经过的结构性节点（类别/法规依据用于归组溯源，不构成因果解释）
_NON_CAUSAL_KINDS = frozenset({KIND_CATEGORY, KIND_EVIDENCE})


def _node_id(kind: str, name: str) -> str:
    return f"{kind}:{name}"


def _ensure_node(graph: nx.MultiDiGraph, kind: str, name: str, **attrs) -> str:
    node_id = _node_id(kind, name)
    if node_id not in graph:
        graph.add_node(node_id, kind=kind, name=name, **attrs)
    return node_id


def _add_edge(graph: nx.MultiDiGraph, source_id: str, target_id: str, relation: str, provenance: str, **attrs) -> None:
    key = f"{relation}|{provenance}"
    graph.add_edge(source_id, target_id, key=key, relation=relation, source=provenance, **attrs)


def _node_view(graph: nx.MultiDiGraph, node_id: str) -> dict:
    attrs = graph.nodes[node_id]
    return {"id": node_id, "name": attrs.get("name", node_id), "kind": attrs.get("kind")}


def build_graph(include_extractions: bool = True) -> nx.MultiDiGraph:
    """从结构化 CSV 建图；include_extractions 时并入 reviewed/ 目录的人工复核抽取结果。"""
    data = load_reference_data()
    graph = nx.MultiDiGraph()

    for group in GROUP_TYPES:
        _ensure_node(graph, KIND_GROUP, group)

    for additive in data.additives:
        # risk_level / forbidden_group 是专家标注标签（防泄漏约束见模块 docstring）
        node_id = _ensure_node(
            graph,
            KIND_ADDITIVE,
            additive.name,
            aliases=list(additive.aliases),
            type=additive.type,
            risk_level=additive.risk_level,
            reason=additive.reason,
            standard=additive.standard,
        )
        if additive.type:
            _ensure_node(graph, KIND_CATEGORY, additive.type)
            _add_edge(graph, node_id, _node_id(KIND_CATEGORY, additive.type), REL_BELONGS_TO, "csv:additives")
        for token in additive.forbidden_groups:
            if token in FORBIDDEN_TOKEN_BLACKLIST:
                continue
            kind = KIND_GROUP if token in GROUP_TYPES else KIND_SUBGROUP
            target = _ensure_node(graph, kind, token)
            _add_edge(
                graph, node_id, target, REL_FORBIDDEN_FOR, "csv:additives",
                restriction_type="forbidden",
                reason=additive.reason, standard=additive.standard,
            )
        if additive.standard:
            evidence = _ensure_node(graph, KIND_EVIDENCE, additive.standard)
            _add_edge(graph, node_id, evidence, REL_BASED_ON, "csv:additives")

    # group_warnings：营养素 -预警(高/中/低)-> 人群；
    # 并按 score.py 的 substring 匹配语义，为名字命中营养素的添加剂派生同款预警边
    for warning in data.group_warnings:
        group_id = _ensure_node(graph, KIND_GROUP, warning.group_type)
        substance_id = _ensure_node(graph, KIND_SUBSTANCE, warning.nutrient)
        _add_edge(
            graph, substance_id, group_id, REL_WARNS, "csv:group_warnings",
            level=warning.level, warning_type=warning.warning_type,
            msg=warning.warning_msg, suggestion=warning.suggestion,
        )
        for additive in data.additives:
            if not warning.nutrient:
                continue
            if warning.nutrient in additive.name or any(warning.nutrient in alias for alias in additive.aliases):
                _add_edge(
                    graph, _node_id(KIND_ADDITIVE, additive.name), group_id, REL_WARNS,
                    "derived:group_warnings",
                    level=warning.level, warning_type=warning.warning_type,
                    msg=warning.warning_msg, derived_from=f"nutrient:{warning.nutrient}",
                )

    # beneficial_ingredients：营养素 -有益于-> 人群；
    # 与添加剂同名的营养素（卵磷脂/赤藓糖醇/甜菊糖苷等，对应 score.py 的
    # BENEFICIAL_ADDITIVE_NAMES 语义）额外派生 添加剂 -有益于-> 人群 边
    for item in data.beneficial_ingredients:
        group_id = _ensure_node(graph, KIND_GROUP, item.group_type)
        substance_id = _ensure_node(graph, KIND_SUBSTANCE, item.nutrient)
        _add_edge(
            graph, substance_id, group_id, REL_BENEFICIAL, "csv:beneficial_ingredients",
            benefit_category=item.benefit_category, benefit=item.benefit, suggestion=item.suggestion,
        )
        if any(additive.name == item.nutrient for additive in data.additives):
            _add_edge(
                graph, _node_id(KIND_ADDITIVE, item.nutrient), group_id, REL_BENEFICIAL,
                "derived:beneficial",
                benefit_category=item.benefit_category, benefit=item.benefit, suggestion=item.suggestion,
            )

    if include_extractions:
        for payload in load_reviewed_extractions():
            try:
                add_extraction(graph, payload, source="human_reviewed")
            except ValueError as exc:
                print(f"[knowledge_graph] 跳过无效的复核文件: {exc}", file=sys.stderr)

    return graph


_GRAPH_CACHE: nx.MultiDiGraph | None = None


def get_graph(force_reload: bool = False) -> nx.MultiDiGraph:
    """进程内缓存图；复核目录变化后用 force_reload=True 重建。"""
    global _GRAPH_CACHE
    if _GRAPH_CACHE is None or force_reload:
        _GRAPH_CACHE = build_graph()
    return _GRAPH_CACHE


def load_reviewed_extractions() -> list[dict]:
    """读取 reviewed/ 目录下全部人工复核过的抽取 JSON。草稿目录一律不读。"""
    if not REVIEWED_DIR.is_dir():
        return []
    payloads: list[dict] = []
    for path in sorted(REVIEWED_DIR.glob("*.json")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"[knowledge_graph] 无法解析复核文件 {path.name}: {exc}", file=sys.stderr)
            continue
        if isinstance(raw, list):
            entries = raw
        elif isinstance(raw, dict) and isinstance(raw.get("extractions"), list):
            entries = raw["extractions"]
        else:
            entries = [raw]
        payloads.extend(entry for entry in entries if isinstance(entry, dict))
    return payloads


def add_extraction(graph: nx.MultiDiGraph, payload: dict, source: str = "human_reviewed") -> dict:
    """把一份抽取结果并入图（人工复核后的标准入口，也用于单元测试）。

    payload 结构：
    {
      "additive": "阿斯巴甜",
      "nodes": [{"id": "substance:苯丙氨酸", "kind": "substance", "name": "苯丙氨酸"}, ...],
      "edges": [{"source": "additive:阿斯巴甜", "target": "substance:苯丙氨酸",
                 "relation": "contains_component", "evidence": "含苯丙氨酸"}, ...],
      "evidence_features": {"regulatory_restriction": false, "special_population_related": true,
                            "risk_statement_exists": true, "evidence_strength": "explicit"}  # 可选
    }
    - forbidden_for / cautions_for 边可带 restriction_type: forbidden(明确禁用/法规限制) /
      warning(需要注意) / attention(风险提示)；缺省时按关系名推断。
    - evidence_features 是成分级文本证据特征（Phase 2 特征），写入添加剂节点属性，
      与 risk_level 标签无关。
    允许掺杂其他元数据键（review_status/model 等），仅读取上述四个键。
    校验失败抛 ValueError；返回 {"nodes_added": int, "edges_added": int}。
    """
    name = str(payload.get("additive") or "").strip()
    if not name:
        raise ValueError("抽取结果缺少 additive 字段")

    nodes_before = graph.number_of_nodes()
    edges_before = graph.number_of_edges()
    additive_id = _ensure_node(graph, KIND_ADDITIVE, name)

    features = payload.get("evidence_features")
    if features is not None:
        if not isinstance(features, dict):
            raise ValueError("evidence_features 必须是对象")
        cleaned = {}
        for key in EVIDENCE_FEATURE_KEYS:
            if key not in features:
                continue
            value = features[key]
            if key == "evidence_strength":
                if value not in EVIDENCE_STRENGTHS:
                    raise ValueError(f"evidence_strength 仅允许 {EVIDENCE_STRENGTHS}: {value!r}")
                cleaned[key] = value
            else:
                cleaned[key] = bool(value)
        graph.nodes[additive_id]["evidence_features"] = cleaned

    for spec in payload.get("nodes") or []:
        if not isinstance(spec, dict):
            raise ValueError(f"非法节点定义: {spec!r}")
        kind = str(spec.get("kind") or "").strip()
        node_name = str(spec.get("name") or "").strip()
        node_id = str(spec.get("id") or "").strip()
        if kind not in (KIND_SUBSTANCE, KIND_SUBGROUP):
            raise ValueError(f"抽取节点 kind 仅允许 substance/subgroup: {kind!r}")
        if not node_name:
            raise ValueError("抽取节点缺少 name")
        if node_id and node_id != _node_id(kind, node_name):
            raise ValueError(f"节点 id 与 kind/name 不一致: {node_id} != {_node_id(kind, node_name)}")
        _ensure_node(graph, kind, node_name)

    for spec in payload.get("edges") or []:
        if not isinstance(spec, dict):
            raise ValueError(f"非法边定义: {spec!r}")
        source_id = str(spec.get("source") or "").strip()
        target_id = str(spec.get("target") or "").strip()
        relation = str(spec.get("relation") or "").strip()
        if relation not in LLM_RELATIONS:
            raise ValueError(f"非法关系 {relation!r}，允许值: {sorted(LLM_RELATIONS)}")
        for endpoint in (source_id, target_id):
            if endpoint not in graph:
                raise ValueError(f"边端点未在图中声明: {endpoint}")
        if relation in (REL_FORBIDDEN_FOR, "cautions_for") and graph.nodes[target_id].get("kind") not in (KIND_GROUP, KIND_SUBGROUP):
            raise ValueError(f"{relation} 的目标必须是人群/亚人群节点: {target_id}")
        restriction_type = str(spec.get("restriction_type") or "").strip()
        if relation in (REL_FORBIDDEN_FOR, "cautions_for"):
            if restriction_type and restriction_type not in RESTRICTION_TYPES:
                raise ValueError(f"restriction_type 仅允许 {RESTRICTION_TYPES}: {restriction_type!r}")
            if not restriction_type:
                restriction_type = "forbidden" if relation == REL_FORBIDDEN_FOR else "warning"
            _add_edge(graph, source_id, target_id, relation, source,
                      restriction_type=restriction_type,
                      evidence=str(spec.get("evidence") or "").strip())
        else:
            _add_edge(graph, source_id, target_id, relation, source,
                      evidence=str(spec.get("evidence") or "").strip())

    return {
        "nodes_added": graph.number_of_nodes() - nodes_before,
        "edges_added": graph.number_of_edges() - edges_before,
    }


def resolve_additive(graph: nx.MultiDiGraph, text: str | None) -> str | None:
    """按名称或别名解析添加剂节点 id，找不到返回 None。"""
    text = (text or "").strip()
    if not text:
        return None
    direct = _node_id(KIND_ADDITIVE, text)
    if direct in graph:
        return direct
    for node_id, attrs in graph.nodes(data=True):
        if attrs.get("kind") == KIND_ADDITIVE and text in (attrs.get("aliases") or []):
            return node_id
    return None


def is_forbidden_for(graph: nx.MultiDiGraph, additive_text: str, target_name: str) -> dict | None:
    """法规硬约束查询：该添加剂对 target_name（九大人群或亚人群名）是否禁忌。

    返回 {"name", "target", "reason", "standard", "source"}，无禁忌返回 None。
    """
    start = resolve_additive(graph, additive_text)
    if start is None:
        return None
    target = None
    for kind in (KIND_GROUP, KIND_SUBGROUP):
        candidate = _node_id(kind, target_name)
        if candidate in graph:
            target = candidate
            break
    if target is None:
        return None

    candidates = []
    edges = graph.get_edge_data(start, target) or {}
    for attrs in edges.values():
        if attrs.get("relation") == REL_FORBIDDEN_FOR:
            candidates.append(attrs)
    if not candidates:
        return None
    candidates.sort(key=lambda attrs: 0 if str(attrs.get("source", "")).startswith("csv") else 1)
    best = candidates[0]
    return {
        "name": graph.nodes[start].get("name"),
        "target": graph.nodes[target].get("name"),
        "reason": best.get("reason", ""),
        "standard": best.get("standard", ""),
        "evidence": best.get("evidence", ""),
        "restriction_type": best.get("restriction_type", "forbidden"),
        "source": best.get("source"),
    }


def _hop_candidates(graph: nx.MultiDiGraph, u: str, v: str) -> list[tuple[str, dict, bool]]:
    """取 u→v（或反向 v→u）各关系的候选边，按关系优先级排序。

    同一节点对可能存在并行边（如法规禁忌 + 派生预警），每个不同关系保留一条，
    使解释链路能分别输出「法规禁忌」与「预警」两种依据。
    返回 [(relation, 边属性, 是否反向)]，无通路返回 []。
    """
    data = graph.get_edge_data(u, v)
    reversed_dir = False
    if not data:
        data = graph.get_edge_data(v, u)
        reversed_dir = True
    if not data:
        return []
    by_relation: dict[str, dict] = {}
    for attrs in data.values():
        relation = attrs.get("relation")
        best = by_relation.get(relation)
        if best is None or (
            _RELATION_PRIORITY.get(relation, 50),
            0 if str(attrs.get("source", "")).startswith("csv") else 1,
        ) < (
            _RELATION_PRIORITY.get(relation, 50),
            0 if str(best.get("source", "")).startswith("csv") else 1,
        ):
            by_relation[relation] = attrs
    ordered = sorted(by_relation.items(), key=lambda item: _RELATION_PRIORITY.get(item[0], 50))
    return [(relation, attrs, reversed_dir) for relation, attrs in ordered]


_MAX_VARIANTS_PER_PATH = 3


def _chain_from_combo(graph: nx.MultiDiGraph, path: list[str], combo: list[tuple[str, dict, bool]], group_type: str | None) -> dict:
    steps = []
    summary_parts = [graph.nodes[path[0]].get("name", path[0])]
    for (u, v), (relation, attrs, reversed_dir) in zip(zip(path, path[1:]), combo):
        steps.append({
            "from": _node_view(graph, u),
            "relation": relation,
            "relation_label": RELATION_LABELS.get(relation, relation),
            "to": _node_view(graph, v),
            "reversed": reversed_dir,
            "source": attrs.get("source"),
            "level": attrs.get("level"),
            "msg": attrs.get("msg"),
            "evidence": attrs.get("evidence"),
        })
        summary_parts.append(f"--{RELATION_LABELS.get(relation, relation)}-->")
        summary_parts.append(graph.nodes[v].get("name", v))

    terminal = _node_view(graph, path[-1])
    return {
        "hops": len(steps),
        "steps": steps,
        "terminal": terminal,
        "is_query_group": bool(group_type) and terminal["name"] == group_type,
        "sources": sorted({step["source"] for step in steps if step["source"]}),
        "summary": " ".join(summary_parts),
    }


def find_explanation_chains(
    graph: nx.MultiDiGraph,
    additive_text: str,
    group_type: str | None = None,
    *,
    max_hops: int = 3,
    max_paths: int = 8,
    include_subgroups: bool = True,
) -> list[dict]:
    """多跳解释链路检索：(成分, 人群) → 「为什么有风险/有益」的可解释路径。

    - group_type 给定：目标为该人群节点；include_subgroups=True 时附加全部亚人群
      （如 苯丙酮尿症患者）作为补充目标，链路的 terminal.is_query_group 可区分。
    - group_type 为 None：目标是全部人群（图检索增强场景）。
    - 链路不经过类别/法规依据等结构节点（它们不构成因果解释）。
    """
    start = resolve_additive(graph, additive_text)
    if start is None:
        return []

    targets: dict[str, None] = {}
    if group_type:
        for kind in (KIND_GROUP, KIND_SUBGROUP):
            candidate = _node_id(kind, group_type)
            if candidate in graph:
                targets[candidate] = None
                break
    else:
        for node_id, attrs in graph.nodes(data=True):
            if attrs.get("kind") == KIND_GROUP:
                targets[node_id] = None
    if include_subgroups:
        for node_id, attrs in graph.nodes(data=True):
            if attrs.get("kind") == KIND_SUBGROUP:
                targets[node_id] = None
    targets.pop(start, None)

    undirected = graph.to_undirected(as_view=True)
    chains: list[dict] = []
    seen: set[tuple] = set()
    for target in targets:
        for path in nx.all_simple_paths(undirected, start, target, cutoff=max_hops):
            if any(graph.nodes[node_id].get("kind") in _NON_CAUSAL_KINDS for node_id in path):
                continue
            hops = [_hop_candidates(graph, u, v) for u, v in zip(path, path[1:])]
            if any(not candidates for candidates in hops):
                continue
            # 每跳各关系取一条候选边做组合；首组合即最优（按关系优先级）
            variants = 0
            for combo in itertools.product(*hops):
                key = (tuple(path), tuple(step[0] for step in combo))
                if key in seen:
                    continue
                seen.add(key)
                chains.append(_chain_from_combo(graph, path, list(combo), group_type))
                variants += 1
                # 每条节点路径最多保留少量关系组合，防止并行边组合爆炸
                if variants >= _MAX_VARIANTS_PER_PATH:
                    break

    chains.sort(key=lambda chain: (chain["hops"], 0 if chain["terminal"]["kind"] == KIND_GROUP else 1))
    return chains[:max_paths]


def graph_stats(graph: nx.MultiDiGraph) -> dict:
    """图规模统计（验收与 Phase 2 评测用）。"""
    kinds = Counter(attrs.get("kind", "unknown") for _, attrs in graph.nodes(data=True))
    relations = Counter(attrs.get("relation", "unknown") for _, _, attrs in graph.edges(data=True))
    return {
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges(),
        "kinds": dict(kinds),
        "relations": dict(relations),
    }

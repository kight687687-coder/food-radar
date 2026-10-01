"""Phase 1 知识图谱单元测试。"""

import json

import pytest

import knowledge_graph as kg
from data_store import load_reference_data


def node(kind, name):
    return f"{kind}:{name}"


def edge_attrs(graph, u, v, relation):
    data = graph.get_edge_data(u, v) or {}
    for attrs in data.values():
        if attrs.get("relation") == relation:
            return attrs
    return None


@pytest.fixture()
def graph():
    return kg.build_graph(include_extractions=False)


@pytest.fixture()
def data():
    return load_reference_data()


class TestSkeleton:
    def test_all_additives_in_graph(self, graph, data):
        additive_nodes = [n for n, a in graph.nodes(data=True) if a["kind"] == kg.KIND_ADDITIVE]
        assert len(additive_nodes) == len(data.additives) == 110
        for additive in data.additives:
            assert graph.has_node(node(kg.KIND_ADDITIVE, additive.name))

    def test_nine_groups_and_subgroup(self, graph):
        for group in kg.GROUP_TYPES:
            assert graph.has_node(node(kg.KIND_GROUP, group))
        # forbidden_group 中的「哮喘者」不在九大人群内，应落为亚人群节点
        assert graph.has_node(node(kg.KIND_SUBGROUP, "哮喘者"))

    def test_belongs_to_category(self, graph):
        attrs = edge_attrs(
            graph,
            node(kg.KIND_ADDITIVE, "阿斯巴甜"),
            node(kg.KIND_CATEGORY, "甜味剂"),
            kg.REL_BELONGS_TO,
        )
        assert attrs and attrs["source"] == "csv:additives"

    def test_forbidden_edges(self, graph):
        attrs = edge_attrs(
            graph, node(kg.KIND_ADDITIVE, "阿斯巴甜"), node(kg.KIND_GROUP, "儿童"), kg.REL_FORBIDDEN_FOR
        )
        assert attrs and attrs["standard"] == "GB2760-2024"
        assert edge_attrs(graph, node(kg.KIND_ADDITIVE, "糖精钠"), node(kg.KIND_GROUP, "孕妇"), kg.REL_FORBIDDEN_FOR)
        assert edge_attrs(graph, node(kg.KIND_ADDITIVE, "亚硫酸钠"), node(kg.KIND_SUBGROUP, "哮喘者"), kg.REL_FORBIDDEN_FOR)

    def test_no_fake_forbidden_edges(self, graph, data):
        """forbidden_group 为「无」的添加剂不得产生禁忌边。"""
        for additive in data.additives:
            forbidden_targets = {
                target
                for _, target, attrs in graph.out_edges(node(kg.KIND_ADDITIVE, additive.name), data=True)
                if attrs.get("relation") == kg.REL_FORBIDDEN_FOR
            }
            expected = {
                node(kg.KIND_GROUP if t in kg.GROUP_TYPES else kg.KIND_SUBGROUP, t)
                for t in additive.forbidden_groups
                if t not in kg.FORBIDDEN_TOKEN_BLACKLIST
            }
            assert forbidden_targets == expected, additive.name
        assert not edge_attrs(graph, node(kg.KIND_ADDITIVE, "三氯蔗糖"), node(kg.KIND_GROUP, "儿童"), kg.REL_FORBIDDEN_FOR)

    def test_warns_direct_and_derived(self, graph):
        direct = edge_attrs(graph, node(kg.KIND_SUBSTANCE, "亚硝酸"), node(kg.KIND_GROUP, "儿童"), kg.REL_WARNS)
        assert direct and direct["level"] == "高"
        derived = edge_attrs(graph, node(kg.KIND_ADDITIVE, "亚硝酸钠"), node(kg.KIND_GROUP, "儿童"), kg.REL_WARNS)
        assert derived and derived["level"] == "高" and derived["derived_from"] == "nutrient:亚硝酸"
        # 旧评分 substring 语义：营养素「磷酸」的预警应派生到名称含磷酸的添加剂
        assert edge_attrs(graph, node(kg.KIND_ADDITIVE, "三聚磷酸钠"), node(kg.KIND_GROUP, "儿童"), kg.REL_WARNS)

    def test_beneficial_edges(self, graph):
        assert edge_attrs(graph, node(kg.KIND_SUBSTANCE, "膳食纤维"), node(kg.KIND_GROUP, "减肥"), kg.REL_BENEFICIAL)
        # 与添加剂同名的有益营养素（对应 score.py 的 BENEFICIAL_ADDITIVE_NAMES 语义）
        assert edge_attrs(graph, node(kg.KIND_ADDITIVE, "卵磷脂"), node(kg.KIND_GROUP, "儿童"), kg.REL_BENEFICIAL)
        assert edge_attrs(graph, node(kg.KIND_ADDITIVE, "赤藓糖醇"), node(kg.KIND_GROUP, "减肥"), kg.REL_BENEFICIAL)

    def test_based_on_evidence(self, graph, data):
        with_standard = [item for item in data.additives if item.standard]
        assert with_standard
        count = sum(1 for *_, attrs in graph.edges(data=True) if attrs.get("relation") == kg.REL_BASED_ON)
        assert count == len(with_standard)
        assert graph.has_node(node(kg.KIND_EVIDENCE, "GB2760-2024"))

    def test_risk_level_stored_as_label(self, graph):
        # 标签防泄漏约束：risk_level 只作为节点标签属性存在，供 Phase 2 作监督信号
        assert graph.nodes[node(kg.KIND_ADDITIVE, "阿斯巴甜")]["risk_level"] == "高"


class TestExtractionMerge:
    payload = {
        "additive": "阿斯巴甜",
        "review_status": "draft",
        "nodes": [
            {"id": "substance:苯丙氨酸", "kind": "substance", "name": "苯丙氨酸"},
            {"id": "subgroup:苯丙酮尿症患者", "kind": "subgroup", "name": "苯丙酮尿症患者"},
        ],
        "edges": [
            {"source": "additive:阿斯巴甜", "target": "substance:苯丙氨酸", "relation": "contains_component", "evidence": "含苯丙氨酸"},
            {"source": "substance:苯丙氨酸", "target": "subgroup:苯丙酮尿症患者", "relation": "forbidden_for", "restriction_type": "forbidden", "evidence": "苯丙酮尿症患者禁用"},
        ],
        "evidence_features": {
            "regulatory_restriction": False,
            "special_population_related": True,
            "risk_statement_exists": True,
            "evidence_strength": "explicit",
        },
    }

    def test_add_extraction_builds_multihop_chain(self, graph):
        stats = kg.add_extraction(graph, self.payload)
        assert stats["edges_added"] == 2
        chains = kg.find_explanation_chains(graph, "阿斯巴甜", "儿童", max_hops=3)
        # 直接法规禁忌（1 跳）
        assert any(
            chain["hops"] == 1 and chain["steps"][0]["relation"] == kg.REL_FORBIDDEN_FOR for chain in chains
        )
        # 多跳链：阿斯巴甜 → 含苯丙氨酸 → 苯丙酮尿症患者禁忌
        pku = [chain for chain in chains if chain["terminal"]["name"] == "苯丙酮尿症患者"]
        assert pku, "应能找到两跳解释链"
        assert pku[0]["hops"] == 2
        assert [step["relation"] for step in pku[0]["steps"]] == ["contains_component", "forbidden_for"]
        assert "human_reviewed" in pku[0]["sources"]
        assert pku[0]["is_query_group"] is False

    def test_extraction_restriction_type_on_edges(self, graph):
        kg.add_extraction(graph, self.payload)
        attrs = edge_attrs(graph, "substance:苯丙氨酸", "subgroup:苯丙酮尿症患者", "forbidden_for")
        assert attrs and attrs["restriction_type"] == "forbidden"
        # csv 禁忌边也应带 restriction_type
        csv_attrs = edge_attrs(graph, "additive:阿斯巴甜", "group:儿童", "forbidden_for")
        assert csv_attrs and csv_attrs["restriction_type"] == "forbidden"

    def test_restriction_type_defaults_by_relation(self, graph):
        payload = {
            "additive": "安赛蜜",
            "nodes": [{"id": "subgroup:婴幼儿", "kind": "subgroup", "name": "婴幼儿"}],
            "edges": [{"source": "additive:安赛蜜", "target": "subgroup:婴幼儿", "relation": "cautions_for"}],
        }
        kg.add_extraction(graph, payload)
        attrs = edge_attrs(graph, "additive:安赛蜜", "subgroup:婴幼儿", "cautions_for")
        assert attrs and attrs["restriction_type"] == "warning"

    def test_rejects_invalid_restriction_type(self, graph):
        bad = {
            "additive": "阿斯巴甜",
            "nodes": [{"id": "subgroup:婴幼儿", "kind": "subgroup", "name": "婴幼儿"}],
            "edges": [{"source": "additive:阿斯巴甜", "target": "subgroup:婴幼儿", "relation": "forbidden_for", "restriction_type": "banned"}],
        }
        with pytest.raises(ValueError):
            kg.add_extraction(graph, bad)

    def test_evidence_features_stored_on_additive_node(self, graph):
        kg.add_extraction(graph, self.payload)
        features = graph.nodes[node(kg.KIND_ADDITIVE, "阿斯巴甜")]["evidence_features"]
        assert features == {
            "regulatory_restriction": False,
            "special_population_related": True,
            "risk_statement_exists": True,
            "evidence_strength": "explicit",
        }

    def test_rejects_invalid_evidence_strength(self, graph):
        bad = {
            "additive": "阿斯巴甜",
            "nodes": [],
            "edges": [],
            "evidence_features": {"evidence_strength": "strong"},
        }
        with pytest.raises(ValueError):
            kg.add_extraction(graph, bad)

    def test_rejects_unknown_relation(self, graph):
        bad = {
            "additive": "阿斯巴甜",
            "nodes": [],
            "edges": [{"source": "additive:阿斯巴甜", "target": "substance:X", "relation": "explode"}],
        }
        with pytest.raises(ValueError):
            kg.add_extraction(graph, bad)

    def test_rejects_undeclared_endpoint(self, graph):
        bad = {
            "additive": "阿斯巴甜",
            "nodes": [],
            "edges": [{"source": "additive:阿斯巴甜", "target": "substance:X", "relation": "contains"}],
        }
        with pytest.raises(ValueError):
            kg.add_extraction(graph, bad)

    def test_rejects_forbidden_for_substance_target(self, graph):
        bad = {
            "additive": "阿斯巴甜",
            "nodes": [{"id": "substance:X", "kind": "substance", "name": "X"}],
            "edges": [{"source": "additive:阿斯巴甜", "target": "substance:X", "relation": "forbidden_for"}],
        }
        with pytest.raises(ValueError):
            kg.add_extraction(graph, bad)

    def test_extraction_can_introduce_new_additive(self, graph):
        payload = {
            "additive": "测试新添加剂Z",
            "nodes": [{"id": "substance:测试物质", "kind": "substance", "name": "测试物质"}],
            "edges": [{"source": "additive:测试新添加剂Z", "target": "substance:测试物质", "relation": "contains_component", "evidence": "文本含测试物质"}],
        }
        kg.add_extraction(graph, payload)
        assert kg.resolve_additive(graph, "测试新添加剂Z") == node(kg.KIND_ADDITIVE, "测试新添加剂Z")


class TestQuery:
    def test_resolve_by_name_and_alias(self, graph):
        assert kg.resolve_additive(graph, "阿斯巴甜") == node(kg.KIND_ADDITIVE, "阿斯巴甜")
        assert kg.resolve_additive(graph, "甜味素") == node(kg.KIND_ADDITIVE, "阿斯巴甜")
        assert kg.resolve_additive(graph, "E951") == node(kg.KIND_ADDITIVE, "阿斯巴甜")
        assert kg.resolve_additive(graph, "不存在的成分") is None

    def test_is_forbidden_for(self, graph):
        record = kg.is_forbidden_for(graph, "阿斯巴甜", "儿童")
        assert record and record["standard"] == "GB2760-2024"
        assert record["restriction_type"] == "forbidden"
        assert kg.is_forbidden_for(graph, "亚硫酸钠", "哮喘者")  # 亚人群
        assert kg.is_forbidden_for(graph, "甜味素", "儿童")  # 别名解析
        assert kg.is_forbidden_for(graph, "三氯蔗糖", "儿童") is None

    def test_no_chain_for_clean_additive(self, graph):
        assert kg.find_explanation_chains(graph, "三氯蔗糖", "儿童", max_hops=3) == []

    def test_chains_direct_edges(self, graph):
        chains = kg.find_explanation_chains(graph, "亚硝酸钠", "儿童", max_hops=2)
        relations = {(chain["hops"], chain["steps"][0]["relation"]) for chain in chains}
        assert (1, kg.REL_FORBIDDEN_FOR) in relations
        assert (1, kg.REL_WARNS) in relations

    def test_chains_when_group_none(self, graph):
        chains = kg.find_explanation_chains(graph, "阿斯巴甜", None, max_hops=2)
        assert chains
        assert all(chain["terminal"]["kind"] in (kg.KIND_GROUP, kg.KIND_SUBGROUP) for chain in chains)
        # 不指定人群时应覆盖多个人群（图检索增强场景）
        terminals = {chain["terminal"]["name"] for chain in chains}
        assert len(terminals) >= 3
        assert all(chain["is_query_group"] is False for chain in chains)


class TestReviewedLoading:
    def _payload(self, additive, substance):
        return {
            "additive": additive,
            "nodes": [{"id": f"substance:{substance}", "kind": "substance", "name": substance}],
            "edges": [{"source": f"additive:{additive}", "target": f"substance:{substance}", "relation": "contains", "evidence": "文本"}],
        }

    def test_reviewed_loaded_and_drafts_not(self, tmp_path, monkeypatch):
        reviewed = tmp_path / "reviewed"
        reviewed.mkdir()
        (reviewed / "a.json").write_text(json.dumps(self._payload("阿斯巴甜", "苯丙氨酸"), ensure_ascii=False), encoding="utf-8")
        drafts = tmp_path / "drafts"
        drafts.mkdir()
        (drafts / "b.json").write_text(json.dumps(self._payload("糖精钠", "邻苯甲酰磺酰亚胺"), ensure_ascii=False), encoding="utf-8")
        monkeypatch.setattr(kg, "REVIEWED_DIR", reviewed)
        monkeypatch.setattr(kg, "DRAFT_DIR", drafts)

        graph = kg.build_graph(include_extractions=True)
        assert graph.has_node("substance:苯丙氨酸")  # reviewed 已并入
        assert not graph.has_node("substance:邻苯甲酰磺酰亚胺")  # drafts 不入图

    def test_invalid_reviewed_file_skipped(self, tmp_path, monkeypatch):
        reviewed = tmp_path / "reviewed"
        reviewed.mkdir()
        (reviewed / "bad.json").write_text("{ not json", encoding="utf-8")
        (reviewed / "invalid_relation.json").write_text(
            json.dumps({
                "additive": "阿斯巴甜",
                "nodes": [],
                "edges": [{"source": "additive:阿斯巴甜", "target": "group:儿童", "relation": "explode"}],
            }, ensure_ascii=False),
            encoding="utf-8",
        )
        monkeypatch.setattr(kg, "REVIEWED_DIR", reviewed)
        graph = kg.build_graph(include_extractions=True)
        assert graph.number_of_nodes() > 0  # 骨架不受坏文件影响


class TestStats:
    def test_graph_stats(self, graph, data):
        stats = kg.graph_stats(graph)
        assert stats["nodes"] == graph.number_of_nodes()
        assert stats["edges"] == graph.number_of_edges()
        assert stats["kinds"][kg.KIND_ADDITIVE] == 110
        assert stats["relations"][kg.REL_BELONGS_TO] == len([a for a in data.additives if a.type])
        assert stats["relations"][kg.REL_FORBIDDEN_FOR] > 0
        assert stats["relations"][kg.REL_WARNS] > 69
        assert stats["relations"][kg.REL_BENEFICIAL] >= 72

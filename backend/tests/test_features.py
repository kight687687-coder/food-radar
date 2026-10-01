"""Phase 2 特征工程单元测试。

核心不变量：特征向量与专家标注标签（risk_level / csv forbidden_for 边）
及展示信息（beneficial 边）完全无关——改标签不动特征。
"""

import pytest

import features as fe
import knowledge_graph as kg


ASPARTAME_PAYLOAD = {
    "additive": "阿斯巴甜",
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


@pytest.fixture(scope="module")
def full_builder():
    """真实全图（CSV 骨架 + 110 份人工复核抽取）。"""
    return fe.FeatureBuilder(kg.build_graph(include_extractions=True))


@pytest.fixture()
def skeleton_builder():
    """仅 CSV 骨架（无抽取证据），用于受控逻辑测试。"""
    return fe.FeatureBuilder(kg.build_graph(include_extractions=False))


class TestSchema:
    def test_feature_names_fixed_dimension(self):
        assert len(fe.FEATURE_NAMES) == 46
        assert len(set(fe.FEATURE_NAMES)) == 46

    def test_no_label_terms_in_feature_names(self):
        for name in fe.FEATURE_NAMES:
            for leak in ("risk_level", "forbidden", "beneficial", "score"):
                assert leak not in name, name

    def test_known_row_shape_and_value_range(self, full_builder):
        row = full_builder.feature_row("阿斯巴甜", "儿童")
        assert len(row) == len(fe.FEATURE_NAMES)
        # 上界 = evidence_count 理论最大值 5（3 布尔证据 + strength 序数 2）
        assert all(0.0 <= value <= 5.0 for value in row)

    def test_category_onehot(self, full_builder):
        row = full_builder.features("阿斯巴甜", "儿童")
        assert row["category_甜味剂"] == 1.0
        assert sum(row[f"category_{c}"] for c in fe.CATEGORIES) == 1.0

    def test_group_onehot(self, full_builder):
        row = full_builder.features("阿斯巴甜", "孕妇")
        assert row["group_孕妇"] == 1.0
        assert sum(row[f"group_{g}"] for g in kg.GROUP_TYPES) == 1.0


class TestUnknownIsomorphism:
    def test_unknown_additive_all_defaults(self, full_builder):
        row = full_builder.features("不存在的成分XYZ", "儿童")
        assert len(row) == len(fe.FEATURE_NAMES)
        assert row["group_儿童"] == 1.0  # 人群 one-hot 仍生效
        for name in fe.FEATURE_NAMES:
            if name != "group_儿童":
                assert row[name] == 0.0, name

    def test_unknown_group_no_onehot_and_no_raise(self, full_builder):
        row = full_builder.features("阿斯巴甜", "外星人群")
        assert sum(row[f"group_{g}"] for g in kg.GROUP_TYPES) == 0.0
        assert row["chain_min_hops"] == 0.0

    def test_alias_resolved(self, full_builder):
        assert full_builder.features("甜味素", "儿童") == full_builder.features("阿斯巴甜", "儿童")


class TestLabelIsolation:
    """防泄漏铁律：剔除标签边/抹掉 risk_level 后，990 对特征逐位不变。"""

    def test_assert_label_isolation_on_real_graph(self, full_builder):
        full_builder.assert_label_isolation()  # 内部对 990 对逐一断言

    def test_evidence_graph_excludes_label_and_display_edges(self, full_builder):
        relations = {
            attrs.get("relation")
            for _, _, attrs in full_builder._evidence_graph.edges(data=True)
        }
        assert kg.REL_BENEFICIAL not in relations
        # 子图中任何 forbidden_for 边都只能来自人工复核抽取（csv 标签边已剔除）
        for u, v, attrs in full_builder._evidence_graph.edges(data=True):
            if attrs.get("relation") == kg.REL_FORBIDDEN_FOR:
                assert attrs.get("source") == "human_reviewed"

    def test_csv_forbidden_edge_not_in_chain_features(self, skeleton_builder):
        """阿斯巴甜对儿童同时存在 csv 法规禁忌边（标签）与 warns 高预警边（证据）。

        链路信号必须只来自 warns 证据边：删 csv 标签边特征逐位不变；
        反向删 warns 边后链路归零（csv 禁忌边不补位）。
        """
        assert kg.is_forbidden_for(skeleton_builder.graph, "阿斯巴甜", "儿童")
        row = skeleton_builder.features("阿斯巴甜", "儿童")
        assert row["warns_level_ordinal"] == 3.0
        assert row["chain_min_hops"] == 1.0  # warns 直达证据链

        def strip(predicate):
            stripped = skeleton_builder.graph.copy()
            for u, v, key, attrs in list(stripped.edges(keys=True, data=True)):
                if predicate(attrs):
                    stripped.remove_edge(u, v, key)
            return fe.FeatureBuilder(stripped)

        no_csv_forbidden = strip(
            lambda a: a.get("relation") == kg.REL_FORBIDDEN_FOR and str(a.get("source", "")).startswith("csv")
        )
        assert no_csv_forbidden.features("阿斯巴甜", "儿童") == row  # 标签边零贡献

        no_warns = strip(lambda a: a.get("relation") == kg.REL_WARNS)
        row_no_warns = no_warns.features("阿斯巴甜", "儿童")
        assert row_no_warns["chain_min_hops"] == 0.0
        assert row_no_warns["warns_level_ordinal"] == 0.0


class TestChainFeatures:
    def test_reviewed_extraction_chain_features(self):
        graph = kg.build_graph(include_extractions=False)
        kg.add_extraction(graph, ASPARTAME_PAYLOAD)
        builder = fe.FeatureBuilder(graph)
        row = builder.features("阿斯巴甜", "儿童")
        # 多跳链 阿斯巴甜 → 含苯丙氨酸 → 禁忌于苯丙酮尿症患者：成分级亚人群证据
        assert row["chain_reaches_subgroup"] == 1.0
        assert row["chain_has_risk_relation"] == 1.0
        # 直达「儿童」的 1 跳只能来自 warns 证据边（csv 禁忌边已剔除），无 2 跳及以上链
        assert row["chain_min_hops"] == 1.0
        assert row["chain_reachable_2hop"] == 0.0

    def test_warns_edge_is_evidence_strength(self, skeleton_builder):
        row = skeleton_builder.features("亚硝酸钠", "儿童")
        assert row["warns_level_ordinal"] == 3.0  # 高预警（derived 营养素语义）
        assert row["chain_min_hops"] == 1.0  # warns 直达边构成 1 跳证据链

    def test_clean_additive_zero_interaction(self, skeleton_builder):
        row = skeleton_builder.features("三氯蔗糖", "儿童")
        assert row["warns_level_ordinal"] == 0.0
        assert row["chain_min_hops"] == 0.0
        assert row["chain_reachable_2hop"] == 0.0
        assert row["chain_has_risk_relation"] == 0.0
        assert row["chain_reaches_subgroup"] == 0.0


class TestEvidenceFeatures:
    def test_reviewed_evidence_features(self, full_builder):
        row = full_builder.features("阿斯巴甜", "儿童")
        assert row["evidence_strength_ordinal"] == 2.0  # explicit
        assert row["regulatory_restriction"] == 0.0
        assert row["special_population_related"] == 1.0
        assert row["risk_statement_exists"] == 1.0
        assert row["has_gb_standard"] == 1.0

    def test_missing_evidence_features_defaults(self, skeleton_builder):
        row = skeleton_builder.features("阿斯巴甜", "儿童")
        assert row["evidence_strength_ordinal"] == 0.0
        assert row["regulatory_restriction"] == 0.0
        assert row["special_population_related"] == 0.0
        assert row["risk_statement_exists"] == 0.0


class TestDatasetAndSplit:
    def test_build_dataset_shape(self, full_builder):
        dataset = fe.build_dataset(full_builder)
        assert len(dataset["pairs"]) == 990
        assert len(dataset["rows"]) == 990
        assert len(dataset["rows"][0]) == len(fe.FEATURE_NAMES)
        additives = {name for name, _ in dataset["pairs"]}
        assert len(additives) == 110

    def test_split_by_additive_no_leak(self):
        pairs = [(a.name, g) for a, g in fe.iter_all_pairs()]
        train, test = fe.split_by_additive(pairs, test_ratio=0.2, seed=42)
        train_additives = {name for name, _ in train}
        test_additives = {name for name, _ in test}
        assert not train_additives & test_additives
        assert train_additives | test_additives == {name for name, _ in pairs}
        assert len(test) / len(pairs) == pytest.approx(0.2, abs=0.05)

    def test_split_deterministic(self):
        pairs = [(a.name, g) for a, g in fe.iter_all_pairs()]
        first = fe.split_by_additive(pairs, seed=7)
        second = fe.split_by_additive(pairs, seed=7)
        assert first == second


class TestPhase35AdditiveFeatures:
    """Phase 3.5 成分属性/证据强度特征（beneficial 不进特征，文本与证据子图派生）。"""

    def test_natural_source_flags(self, full_builder):
        # 天然色素语料含「天然」标记词
        assert full_builder.features("β-胡萝卜素", "儿童")["natural_source"] == 1.0
        assert full_builder.features("叶绿素铜钠", "儿童")["natural_source"] == 1.0
        # 人工合成成分不含天然标记
        assert full_builder.features("柠檬黄", "儿童")["natural_source"] == 0.0

    def test_synthetic_origin_flags(self, full_builder):
        assert full_builder.features("柠檬黄", "儿童")["synthetic_origin"] == 1.0
        assert full_builder.features("阿斯巴甜", "儿童")["synthetic_origin"] == 1.0
        assert full_builder.features("姜黄素", "儿童")["synthetic_origin"] == 0.0

    def test_nutrient_related_flags(self, full_builder):
        # 磷酸：reason「过量摄入影响钙磷平衡」→ 钙磷命中营养相关
        assert full_builder.features("磷酸", "儿童")["nutrient_related"] == 1.0
        assert full_builder.features("维生素C", "儿童")["nutrient_related"] == 1.0
        assert full_builder.features("柠檬黄", "儿童")["nutrient_related"] == 0.0

    def test_evidence_density_normalized(self, full_builder):
        # 密度 ∈ [0, 1]，全局至少一个成分达到 1.0（归一化分母）
        densities = {
            additive.name: full_builder.features(additive.name, "儿童")["evidence_density"]
            for additive, _ in fe.iter_all_pairs()
        }
        assert all(0.0 <= value <= 1.0 for value in densities.values())
        assert max(densities.values()) == 1.0

    def test_evidence_count_composition(self, full_builder):
        # evidence_count = 三布尔证据 + strength 序数
        row = full_builder.features("阿斯巴甜", "儿童")
        expected = (
            row["regulatory_restriction"] + row["special_population_related"]
            + row["risk_statement_exists"] + row["evidence_strength_ordinal"]
        )
        assert row["evidence_count"] == expected

    def test_risk_relation_counts_human_reviewed_edges(self, full_builder):
        # 亚硝酸钠经人工复核抽取：converts_to 亚硝胺（体内转化风险关系）
        assert full_builder.features("亚硝酸钠", "儿童")["risk_relation_count"] >= 1.0
        # 阿斯巴甜的风险链在下游：出边仅含 contains_component(苯丙氨酸)，
        # 风险关系 forbidden_for 的 source 是苯丙氨酸而非阿斯巴甜 → 直连计数为 0
        assert full_builder.features("阿斯巴甜", "儿童")["risk_relation_count"] == 0.0

    def test_population_relation_counts(self, full_builder):
        # 阿斯巴甜 warns 直连人群 + 人工复核禁忌亚人群 → 至少 1 个人群节点
        assert full_builder.features("阿斯巴甜", "儿童")["population_relation_count"] >= 1.0

    def test_new_features_default_for_unknown(self, full_builder):
        row = full_builder.features("不存在的成分XYZ", "儿童")
        for name in ("natural_source", "nutrient_related", "synthetic_origin",
                     "evidence_density", "evidence_count",
                     "risk_relation_count", "population_relation_count"):
            assert row[name] == 0.0, name


class TestStratifiedSplit:
    """risk_level 分层留出：test 覆盖各风险档（risk_level 仅作划分依据，不入特征）。"""

    def test_holdout_covers_all_levels(self):
        pairs = [(a.name, g) for a, g in fe.iter_all_pairs()]
        risk_levels = {a.name: a.risk_level for a in fe.iter_risk_levels()}
        train, test = fe.split_by_additive_stratified(pairs, risk_levels, test_ratio=0.2, seed=42)
        test_levels = {risk_levels[name] for name, _ in test}
        assert test_levels == {"高", "中", "低"}

    def test_holdout_high_additive_present(self):
        pairs = [(a.name, g) for a, g in fe.iter_all_pairs()]
        risk_levels = {a.name: a.risk_level for a in fe.iter_risk_levels()}
        _, test = fe.split_by_additive_stratified(pairs, risk_levels, test_ratio=0.2, seed=42)
        high_test = {name for name, _ in test if risk_levels[name] == "高"}
        assert len(high_test) >= 1

    def test_no_additive_crosses_split(self):
        pairs = [(a.name, g) for a, g in fe.iter_all_pairs()]
        risk_levels = {a.name: a.risk_level for a in fe.iter_risk_levels()}
        train, test = fe.split_by_additive_stratified(pairs, risk_levels, seed=42)
        assert not {name for name, _ in train} & {name for name, _ in test}

    def test_stratified_deterministic(self):
        pairs = [(a.name, g) for a, g in fe.iter_all_pairs()]
        risk_levels = {a.name: a.risk_level for a in fe.iter_risk_levels()}
        assert (fe.split_by_additive_stratified(pairs, risk_levels, seed=7)
                == fe.split_by_additive_stratified(pairs, risk_levels, seed=7))

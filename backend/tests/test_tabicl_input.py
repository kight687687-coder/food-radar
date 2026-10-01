"""TabICLv2 输入构造层单元测试（不依赖 torch / tabicl 包）。"""

import csv

import pytest

import features as fe
import tabicl_input as ti


class StubBuilder:
    """不依赖真实图的桩构建器：按 (成分, 人群, 特征名) 给确定性伪值。"""

    def feature_row(self, additive_text, group_type):
        return [
            float((i * 7 + len(additive_text) * 3 + len(group_type)) % 4)
            for i in range(len(fe.FEATURE_NAMES))
        ]


@pytest.fixture()
def labels():
    return {
        (f"成分{i:02d}", group): ("high", "medium", "low")[i % 3]
        for i in range(10)
        for group in ("儿童", "孕妇")
    }


def test_load_labels_validates_and_maps(tmp_path):
    path = tmp_path / "kg_labels.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["additive", "group", "risk_label", "source", "review_status"])
        writer.writerow(["阿斯巴甜", "儿童", "high", "calibrated", "reviewed"])
        writer.writerow(["三氯蔗糖", "老人", "low", "initial", "reviewed"])
        writer.writerow(["糖精钠", "孕妇", "unknown", "calibrated", "reviewed"])
    labels = ti.load_labels(path)
    assert labels[("阿斯巴甜", "儿童")] == "high"
    assert labels[("三氯蔗糖", "老人")] == "low"
    assert labels[("糖精钠", "孕妇")] == "unknown"


def test_load_labels_rejects_invalid(tmp_path):
    path = tmp_path / "kg_labels.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["additive", "group", "risk_label", "source", "review_status"])
        writer.writerow(["阿斯巴甜", "儿童", "extreme", "initial", "reviewed"])
    with pytest.raises(ValueError):
        ti.load_labels(path)


def test_load_labels_missing_file_message(tmp_path, monkeypatch):
    monkeypatch.setattr(ti, "LABELS_CSV", tmp_path / "missing.csv")
    with pytest.raises(FileNotFoundError, match="auto_calibrate"):
        ti.load_labels()


def test_build_inputs_shape_and_group_split(labels):
    inputs = ti.build_inputs(StubBuilder(), labels, test_ratio=0.3, seed=42)
    dim = len(fe.FEATURE_NAMES)
    assert inputs["feature_names"] == list(fe.FEATURE_NAMES)
    assert all(len(row) == dim for row in inputs["x_train"] + inputs["x_test"])
    assert len(inputs["x_train"]) == len(inputs["y_train"])
    assert len(inputs["x_test"]) == len(inputs["y_test"]) == len(inputs["test_pairs"])
    assert len(inputs["x_train"]) + len(inputs["x_test"]) == len(labels)

    # 按成分分组留出：同一成分的全部人群对在同一侧
    train_additives = {
        name for name, _ in
        (pair for pair in labels if pair not in set(inputs["test_pairs"]))
    }
    test_additives = {name for name, _ in inputs["test_pairs"]}
    assert not train_additives & test_additives
    # 10 成分 × 30% → 3 个成分留出，各自 2 个人群对全部落 test
    assert len(test_additives) == 3
    by_additive: dict[str, set] = {}
    for name, group in inputs["test_pairs"]:
        by_additive.setdefault(name, set()).add(group)
    assert all(len(groups) == 2 for groups in by_additive.values())
    assert set(inputs["y_train"]) <= {"high", "medium", "low"}

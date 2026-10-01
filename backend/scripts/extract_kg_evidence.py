"""Phase 1 知识图谱证据抽取：调 DeepSeek 从添加剂 reason/standard 文本抽取中间物质与敏感人群，
输出 JSON 草稿到 backend/data/kg/drafts/。草稿不入图；人工复核（可直接编辑）后移入
backend/data/kg/reviewed/ 即自动并入知识图谱（knowledge_graph.build_graph）。

用法（在 backend/ 目录下用 .venv 解释器执行）：
    python scripts/extract_kg_evidence.py --limit 10        # 试跑前 10 个未处理成分
    python scripts/extract_kg_evidence.py --names 阿斯巴甜,亚硝酸钠
    python scripts/extract_kg_evidence.py --force            # 覆盖已有草稿全量跑
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# 系统代理指向已关闭的本地端口，联网前必须清空
for _proxy_var in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"):
    os.environ.pop(_proxy_var, None)

from openai import OpenAI  # noqa: E402

import knowledge_graph as kg  # noqa: E402
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL  # noqa: E402
from data_store import load_reference_data  # noqa: E402

DRAFT_DIR = kg.DRAFT_DIR

PROMPT_TEMPLATE = """你是食品安全知识图谱构建助手。任务：从给定文本中抽取「中间物质」「敏感亚人群」及其因果关系，用于构建多跳推理链（如：阿斯巴甜 --含--> 苯丙氨酸 --禁忌于--> 苯丙酮尿症患者）。

【添加剂】{name}（类别：{type}）
【风险说明】{reason}
【国标依据】{standard}
【相关人群预警】
{warning_lines}

抽取规则：
1. 只依据上方文本抽取，禁止引入外部知识或推测；文本中没有的信息一律不抽。
2. 中间物质示例：苯丙氨酸、亚硝胺、铝、二氧化硫、反式脂肪酸、苯甲酸等；敏感亚人群示例：苯丙酮尿症患者、哮喘者、婴幼儿、甲状腺功能异常者等。
3. relation 仅可取：contains_component(含某成分/物质，语义上的组成或含有即可，不要求严格化学组成)、converts_to(体内可转化为)、metabolizes_to(体内代谢为)、triggers(可能诱发)、harms(损害)、associated_with(与某风险关联)、forbidden_for(对某人群禁忌/限制)、cautions_for(某人群需注意)。
4. forbidden_for 与 cautions_for 的边必须带 restriction_type 字段，仅可取：forbidden(原文明确禁用/法规限制，如「禁用」「婴儿食品禁用」「多国已禁用」)、warning(原文表述需要注意/应避免/需注意)、attention(原文仅为风险提示或存争议)。
5. 节点 kind 仅可取：substance(中间物质)、subgroup(敏感亚人群)。注意：儿童、孕妇、老人、糖尿病、心血管、减肥、健身、普通人群、其他 这九大人群已在知识库中，禁止作为节点抽取，九大人群的注意事项也无需抽边（知识库已覆盖）；subgroup 仅用于九大人群之外的敏感亚人群（如苯丙酮尿症患者、哮喘者、婴幼儿、甲状腺功能异常者）。
6. edges 的 source/target 必须是 nodes 中声明的节点，或添加剂本身（id 固定为 additive:{name}）。
7. evidence 字段摘录原文短语作为依据。
8. 另外输出 evidence_features 对象（成分级文本证据特征，即使 nodes/edges 为空也必须输出）：
   - regulatory_restriction: true/false，原文是否提及法规限制（如「新国标缩紧使用范围」「多国已限制使用」「婴儿食品禁用」「限制使用量」）
   - special_population_related: true/false，原文是否提及特殊人群（儿童/孕妇/婴幼儿/哮喘/苯丙酮尿症等）
   - risk_statement_exists: true/false，原文是否存在明确的风险陈述（致癌/影响发育/蓄积/损害/诱发等）
   - evidence_strength: "explicit"(原文有明确因果/危害表述) / "suggestive"(仅有争议性、可能性、潜在风险表述) / "none"(无风险相关陈述)

严格返回 JSON（不要输出任何其他内容）：
{{
  "additive": "{name}",
  "nodes": [
    {{"id": "substance:名称", "kind": "substance", "name": "名称"}},
    {{"id": "subgroup:名称", "kind": "subgroup", "name": "名称"}}
  ],
  "edges": [
    {{"source": "additive:{name}", "target": "substance:名称", "relation": "contains_component", "evidence": "原文短语"}},
    {{"source": "substance:名称", "target": "subgroup:名称", "relation": "forbidden_for", "restriction_type": "forbidden", "evidence": "原文短语"}}
  ],
  "evidence_features": {{"regulatory_restriction": false, "special_population_related": true, "risk_statement_exists": true, "evidence_strength": "explicit"}}
}}
若文本无可靠信息，nodes 与 edges 均为空数组，但 evidence_features 仍须按原文如实输出。"""


def _parse_json_content(content: str) -> dict:
    value = (content or "").strip()
    if value.startswith("```"):
        value = value.split("\n", 1)[1] if "\n" in value else ""
    if value.endswith("```"):
        value = value[:-3].rstrip()
    return json.loads(value)


def _matched_warning_lines(additive, warnings) -> str:
    lines = []
    for warning in warnings:
        if not warning.nutrient:
            continue
        if warning.nutrient in additive.name or any(warning.nutrient in alias for alias in additive.aliases):
            lines.append(f"- [{warning.group_type}] {warning.nutrient}（{warning.level}）：{warning.warning_msg}")
    return "\n".join(lines) if lines else "（无）"


VALID_RESTRICTION_TYPES = kg.RESTRICTION_TYPES
VALID_STRENGTHS = kg.EVIDENCE_STRENGTHS


def _normalize_payload(raw: dict, additive_name: str, log_prefix: str) -> dict:
    """清洗 LLM 输出：过滤白名单外关系、未声明端点、id 不一致节点；规整 restriction_type 与 evidence_features。"""
    if str(raw.get("additive") or "").strip() != additive_name:
        raw["additive"] = additive_name  # 以输入为准
    declared = {f"additive:{additive_name}"}
    nodes = []
    for spec in raw.get("nodes") or []:
        if not isinstance(spec, dict):
            continue
        kind = str(spec.get("kind") or "").strip()
        name = str(spec.get("name") or "").strip()
        if kind not in (kg.KIND_SUBSTANCE, kg.KIND_SUBGROUP) or not name:
            print(f"{log_prefix} 丢弃非法节点: {spec!r}")
            continue
        if kind == kg.KIND_SUBGROUP and any(group in name for group in kg.GROUP_TYPES):
            # 防御：九大人群已是图内 group 节点，不得作为 subgroup 重复抽取
            print(f"{log_prefix} 丢弃九大人群亚节点: {spec!r}")
            continue
        nodes.append({"id": f"{kind}:{name}", "kind": kind, "name": name})
        declared.add(f"{kind}:{name}")
    edges = []
    for spec in raw.get("edges") or []:
        if not isinstance(spec, dict):
            continue
        source = str(spec.get("source") or "").strip()
        target = str(spec.get("target") or "").strip()
        relation = str(spec.get("relation") or "").strip()
        if relation not in kg.LLM_RELATIONS:
            print(f"{log_prefix} 丢弃白名单外关系: {spec!r}")
            continue
        if source not in declared or target not in declared:
            print(f"{log_prefix} 丢弃未声明端点的边: {spec!r}")
            continue
        edge = {"source": source, "target": target, "relation": relation,
                "evidence": str(spec.get("evidence") or "").strip()}
        if relation in ("forbidden_for", "cautions_for"):
            restriction_type = str(spec.get("restriction_type") or "").strip()
            if restriction_type not in VALID_RESTRICTION_TYPES:
                print(f"{log_prefix} restriction_type 缺失/非法，按关系名推断: {spec!r}")
                restriction_type = "forbidden" if relation == "forbidden_for" else "warning"
            edge["restriction_type"] = restriction_type
        edges.append(edge)
    if len(nodes) > 12:
        print(f"{log_prefix} 节点数超限，截断到 12（原 {len(nodes)}）")
        keep = {item["id"] for item in nodes[:12]}
        nodes = nodes[:12]
        edges = [item for item in edges if item["source"] in keep and item["target"] in keep]
    if len(edges) > 12:
        print(f"{log_prefix} 边数超限，截断到 12（原 {len(edges)}）")
        edges = edges[:12]

    raw_features = raw.get("evidence_features")
    if not isinstance(raw_features, dict):
        raw_features = {}
    features = {
        "regulatory_restriction": bool(raw_features.get("regulatory_restriction", False)),
        "special_population_related": bool(raw_features.get("special_population_related", False)),
        "risk_statement_exists": bool(raw_features.get("risk_statement_exists", False)),
    }
    strength = str(raw_features.get("evidence_strength") or "").strip()
    if strength not in VALID_STRENGTHS:
        strength = "none"
    features["evidence_strength"] = strength
    return {"additive": additive_name, "nodes": nodes, "edges": edges, "evidence_features": features}


def _extract_one(client, additive, warnings) -> dict | None:
    prompt = PROMPT_TEMPLATE.format(
        name=additive.name,
        type=additive.type or "未知",
        reason=additive.reason or "（无）",
        standard=additive.standard or "（无）",
        warning_lines=_matched_warning_lines(additive, warnings),
    )
    last_error: Exception | None = None
    for attempt in range(3):  # 推理模型 reasoning 也计入 max_tokens，偶发超预算/空返回时退避重试
        try:
            response = client.chat.completions.create(
                model=DEEPSEEK_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=6000,
                response_format={"type": "json_object"},
            )
            raw = _parse_json_content(response.choices[0].message.content)
            if not isinstance(raw, dict):
                raise ValueError("返回不是 JSON 对象")
            return _normalize_payload(raw, additive.name, f"[{additive.name}]")
        except Exception as exc:
            last_error = exc
            print(f"[{additive.name}] 第 {attempt + 1} 次尝试失败: {exc}", file=sys.stderr)
            if attempt < 2:
                time.sleep(3)
    raise last_error


def main() -> int:
    parser = argparse.ArgumentParser(description="DeepSeek 知识图谱证据抽取（输出草稿，人工复核后入图）")
    parser.add_argument("--limit", type=int, default=None, help="只处理前 N 个未处理成分（试跑用）")
    parser.add_argument("--names", type=str, default=None, help="只处理指定成分（逗号分隔）")
    parser.add_argument("--force", action="store_true", help="覆盖已有草稿")
    args = parser.parse_args()

    if not DEEPSEEK_API_KEY:
        print("错误：DEEPSEEK_API_KEY 未配置", file=sys.stderr)
        return 1

    data = load_reference_data()
    warnings = data.group_warnings
    selected = data.additives
    if args.names:
        wanted = {item.strip() for item in args.names.split(",") if item.strip()}
        selected = [item for item in selected if item.name in wanted]
        missing = wanted - {item.name for item in selected}
        if missing:
            print(f"警告：未在 additives.csv 中找到 {sorted(missing)}", file=sys.stderr)

    DRAFT_DIR.mkdir(parents=True, exist_ok=True)
    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL, timeout=60.0)

    # 用于校验 payload 可入图的空白骨架（不并入 reviewed 数据，避免污染校验）
    skeleton = kg.build_graph(include_extractions=False)

    processed = failed = skipped = 0
    global_index = {additive.name: index for index, additive in enumerate(data.additives, start=1)}
    for additive in selected:
        index = global_index[additive.name]
        draft_path = DRAFT_DIR / f"{index:03d}_{additive.name}.json"
        if draft_path.exists() and not args.force:
            skipped += 1
            continue
        if args.limit is not None and processed + failed >= args.limit:
            break
        try:
            payload = _extract_one(client, additive, warnings)
            probe = skeleton.copy()
            kg.add_extraction(probe, payload, source="llm")
        except Exception as exc:
            failed += 1
            print(f"[{additive.name}] 抽取失败: {exc}", file=sys.stderr)
            continue
        draft = {
            "review_status": "draft",
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "model": DEEPSEEK_MODEL,
            "additive": additive.name,
            "source_text": {"type": additive.type, "reason": additive.reason, "standard": additive.standard},
            "nodes": payload["nodes"],
            "edges": payload["edges"],
            "evidence_features": payload["evidence_features"],
        }
        draft_path.write_text(json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8")
        processed += 1
        features = payload["evidence_features"]
        print(
            f"[{index:03d}] {additive.name}: {len(payload['nodes'])} 节点 / {len(payload['edges'])} 边 / "
            f"证据强度 {features['evidence_strength']} -> {draft_path.name}"
        )

    print(f"\n完成：新处理 {processed}，跳过已有 {skipped}，失败 {failed}")
    print(f"草稿目录: {DRAFT_DIR}")
    print("复核方式：检查/编辑 drafts/*.json 后移入 reviewed/ 即并入知识图谱")
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    sys.exit(main())

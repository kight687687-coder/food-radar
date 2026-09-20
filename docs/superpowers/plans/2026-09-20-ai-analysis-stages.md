# 四阶段 AI 分析结果页 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** 将结果页的单一 AI 综合结论改为稳定的四阶段 AI 分析展示，并让风险成分、有益成分、忌口命中和家庭成员上下文进入 AI 判断与建议。

**Architecture:** 后端在一次分析请求中生成兼容旧字段且包含 judgment、recommendation 的结构化 AI 报告；事实型阶段由真实 OCR、评分和知识库数据渲染，语言型阶段使用 AI 报告。Web 端新增 AiAnalysisStages 展示组件，由结果页控制开场弹窗、阶段计时和忌口弹窗串行关系。

**Tech Stack:** Flask/Python、DeepSeek OpenAI-compatible client、React、CSS keyframes、Node built-in test runner、pytest。

## Global Constraints

- 后端只进行一次 AI 报告请求，不实现四次独立请求、SSE 或 WebSocket。
- AI 识别阶段只能展示 OCR/解析得到的真实配料，不能由 AI 凭空添加配料。
- AI 发现阶段完整展示风险成分、有益成分、人群提醒和忌口命中。
- 分数和风险等级继续使用现有评分引擎结果，AI 只负责解释和行动建议。
- 评分区、扫描图片、食品信息和忌口提醒内容保持不变；只将两个弹窗串行，避免遮罩重叠。
- 四张卡片顺序固定为 AI 识别、AI 发现、AI 判断、AI 建议，完成后全部展开。
- 沿用现有结果页卡片样式，AI 配色可以调整但不能引入新 UI 框架或依赖。
- AI 服务失败时必须使用基础回退文案完成所有卡片，不允许出现空白卡片。
- 遵守 prefers-reduced-motion: reduce，减少非必要动画但保留全部状态和内容。

---

### Task 1: 扩展后端结构化 AI 报告上下文

**Files:**
- Modify: backend/ai_analyze.py lines 58-104
- Modify: backend/app.py lines 176-216
- Modify: backend/tests/test_providers.py
- Modify: backend/tests/test_routes.py

**Interfaces:**
- Consumes: 现有 score_result 字典、OCR ingredients、food_category、user_type。
- Produces: ai_report 字典，至少包含 summary、detail、suggestion、long_term_risk、judgment、recommendation 六个非空字符串字段。

- [ ] **Step 1: 写失败测试，锁定新增报告字段和上下文内容**

在 backend/tests/test_providers.py 增加：

~~~python
def test_fallback_report_contains_staged_fields_and_context():
    from ai_analyze import build_fallback_report

    report = build_fallback_report(
        food_category="能量饮料",
        health_score=58,
        risk_additives=[{"name": "咖啡因", "risk_level": "中", "deduct_score": 10}],
        user_type="儿童",
        warnings=[{"msg": "儿童需关注咖啡因"}],
        beneficial_ingredients=[{"nutrient": "维生素C", "benefit_category": "维生素类"}],
        avoid_warnings=[{"name": "咖啡因敏感", "warning_msg": "已命中忌口"}],
        score_details={"group_extra_penalty": 5},
        ingredients=["水", "咖啡因", "维生素C"],
    )

    assert set(report) == {
        "summary", "detail", "suggestion", "long_term_risk",
        "judgment", "recommendation",
    }
    assert all(isinstance(value, str) and value.strip() for value in report.values())
    assert "儿童" in report["judgment"] or "儿童" in report["detail"]


def test_generate_report_prompt_contains_benefits_avoids_and_score_details(monkeypatch):
    import ai_analyze

    captured = {}

    def fake_completion(messages, **kwargs):
        captured["content"] = messages[0]["content"]
        return '{"summary":"摘要","detail":"详情","suggestion":"建议","long_term_risk":"长期","judgment":"判断","recommendation":"替代"}'

    monkeypatch.setattr(ai_analyze, "_completion", fake_completion)
    ai_analyze.generate_report(
        "饮料", 58, [{"name": "咖啡因"}], "儿童", [{"msg": "儿童提醒"}],
        beneficial_ingredients=[{"nutrient": "维生素C"}],
        avoid_warnings=[{"name": "咖啡因敏感"}],
        score_details={"group_extra_penalty": 5},
        ingredients=["水", "咖啡因", "维生素C"],
    )

    assert "维生素C" in captured["content"]
    assert "咖啡因敏感" in captured["content"]
    assert "group_extra_penalty" in captured["content"]
~~~

更新原有 test_fallback_report_has_complete_frontend_contract，将字段断言改为六个字段，保留非空字符串断言。

- [ ] **Step 2: 运行新增后端测试，确认当前实现失败**

~~~powershell
cd backend
python -m pytest tests/test_providers.py -q
~~~

预期：新增 staged fields 测试失败，因为当前 fallback 和 prompt 只有四个报告字段，且不接收完整上下文。

- [ ] **Step 3: 扩展 fallback 和 DeepSeek prompt 的精确接口**

在 backend/ai_analyze.py 中将函数签名扩展为：

~~~python
def build_fallback_report(
    food_category,
    health_score,
    risk_additives,
    user_type,
    warnings,
    *,
    beneficial_ingredients=None,
    avoid_warnings=None,
    score_details=None,
    ingredients=None,
):
    ...


def generate_report(
    food_category,
    health_score,
    risk_additives,
    user_type,
    warnings,
    *,
    beneficial_ingredients=None,
    avoid_warnings=None,
    score_details=None,
    ingredients=None,
):
    ...
~~~

实现要求：

- 将 None 统一转换为空列表或空字典后再序列化。
- prompt 明确要求只返回六个字符串字段：summary、detail、suggestion、long_term_risk、judgment、recommendation。
- prompt 同时传入配料、风险、有益、忌口、人群提醒、分数和扣分明细。
- judgment 解释当前人群下风险和有益成分的相对意义。
- recommendation 给出食用频率、注意事项或同类替代方向；不能给出诊断或处方。
- AI JSON 解析后的必填字段检查扩展为六个字段，缺字段时走 fallback。
- fallback 的 judgment 和 recommendation 使用传入的真实字段生成，不引用未检测到的成分。

fallback 返回结构：

~~~python
return {
    "summary": summary,
    "detail": detail,
    "suggestion": suggestion,
    "long_term_risk": long_term_risk,
    "judgment": judgment,
    "recommendation": recommendation,
}
~~~

- [ ] **Step 4: 从分析流水线传入完整上下文**

在 backend/app.py 的 _run_analysis_pipeline 中构造：

~~~python
score_details = {
    "beneficial_bonus": score_result["beneficial_bonus"],
    "stacking_penalty": score_result["stacking_penalty"],
    "ingredients_count_penalty": score_result["ingredients_count_penalty"],
    "group_extra_penalty": score_result["group_extra_penalty"],
    "group_extra_details": score_result["group_extra_details"],
}
ai_report = generate_report(
    food_category,
    score_result["health_score"],
    score_result["risk_additives"],
    user_type,
    score_result["group_warnings"],
    beneficial_ingredients=score_result["beneficial_ingredients"],
    avoid_warnings=score_result["avoid_warnings"],
    score_details=score_details,
    ingredients=ingredients_list,
)
~~~

将 score_details 一并放入分析结果。

- [ ] **Step 5: 运行后端测试并提交**

~~~powershell
cd backend
python -m pytest -v
~~~

预期：全部通过，包括原有 route contract、fallback 和 provider 测试。

~~~powershell
git add backend/ai_analyze.py backend/app.py backend/tests/test_providers.py backend/tests/test_routes.py
git commit -m "feat: add structured staged AI report context"
~~~

### Task 2: 建立 Web 阶段数据整理和播放状态

**Files:**
- Create: web/src/utils/aiAnalysisStages.js
- Create: web/tests/ai-analysis-stages.test.mjs
- Create: web/src/components/AiAnalysisStages.jsx

**Interfaces:**
- Consumes: ResultPage 的 result、score、level、risks、benefits、warnings、hitAvoids。
- Produces: 四阶段卡片 DOM；每阶段状态为 pending、analyzing 或 complete，最终全部 complete。

- [ ] **Step 1: 写纯函数测试，锁定事实数据整理规则**

在 web/tests/ai-analysis-stages.test.mjs 写：

~~~javascript
import test from 'node:test'
import assert from 'node:assert/strict'
import { buildAnalysisStages } from '../src/utils/aiAnalysisStages.js'

test('buildAnalysisStages keeps ingredients in recognition and merges findings', () => {
  const stages = buildAnalysisStages({
    result: {
      ingredients: '水,白砂糖,咖啡因,维生素C',
      beneficial_ingredients: [{ nutrient: '维生素C', benefit_category: '维生素类' }],
      risk_additives: [{ name: '咖啡因', risk_level: '中', deduct_score: 10 }],
      group_warnings: [{ msg: '儿童需关注咖啡因' }],
      avoid_warnings: [{ name: '咖啡因敏感' }],
      ai_report: {
        judgment: '儿童需减少摄入咖啡因。',
        recommendation: '建议偶尔食用。',
        summary: '风险指数 58 分。',
        suggestion: '选择低咖啡因替代品。',
        long_term_risk: '关注长期频率。',
      },
    },
    score: 58,
    level: '需要谨慎选择',
    risks: [{ name: '咖啡因', risk_level: '中', deduct: 10 }],
    benefits: [{ name: '维生素C' }],
    warnings: ['儿童需关注咖啡因'],
    hitAvoids: ['咖啡因敏感'],
  })

  assert.deepEqual(stages.map(stage => stage.id), ['recognition', 'findings', 'judgment', 'advice'])
  assert.deepEqual(stages[0].ingredients, ['水', '白砂糖', '咖啡因', '维生素C'])
  assert.equal(stages[1].risks[0].name, '咖啡因')
  assert.equal(stages[1].benefits[0].name, '维生素C')
  assert.deepEqual(stages[1].avoids, ['咖啡因敏感'])
  assert.equal(stages[2].text, '儿童需减少摄入咖啡因。')
  assert.equal(stages[3].recommendation, '建议偶尔食用。')
})

test('buildAnalysisStages returns explicit empty states', () => {
  const stages = buildAnalysisStages({ result: {}, score: 90, level: '可以放心食用', risks: [], benefits: [], warnings: [], hitAvoids: [] })
  assert.equal(stages[0].ingredients.length, 0)
  assert.equal(stages[1].risks.length, 0)
  assert.equal(stages[1].emptyMessage, '暂未发现需要特别关注的项目。')
})
~~~

- [ ] **Step 2: 运行 Web 单测，确认当前 helper 不存在而失败**

~~~powershell
cd web
node --test tests/ai-analysis-stages.test.mjs
~~~

预期：FAIL，提示 aiAnalysisStages.js 或 buildAnalysisStages 不存在。

- [ ] **Step 3: 实现数据整理 helper**

在 web/src/utils/aiAnalysisStages.js 中导出：

~~~javascript
export const STAGE_IDS = ['recognition', 'findings', 'judgment', 'advice']

export function splitIngredients(value) {
  return String(value || '')
    .split(/[、,，;；\n\r]+/)
    .map(item => item.trim())
    .filter(Boolean)
}

export function buildAnalysisStages({ result = {}, score = 0, level = '', risks = [], benefits = [], warnings = [], hitAvoids = [] }) {
  const report = result.ai_report || {}
  return [
    { id: 'recognition', title: 'AI 识别', source: 'OCR 识别 + AI 配料整理', ingredients: splitIngredients(result.ingredients) },
    {
      id: 'findings',
      title: 'AI 发现',
      source: '食品知识库匹配 + 家庭画像分析',
      risks,
      benefits,
      warnings,
      avoids: hitAvoids,
      emptyMessage: risks.length || benefits.length || warnings.length || hitAvoids.length ? '' : '暂未发现需要特别关注的项目。',
    },
    { id: 'judgment', title: 'AI 判断', source: 'AI 个性化判断', text: report.judgment || report.detail || '已结合当前人群和识别结果完成判断。' },
    {
      id: 'advice',
      title: 'AI 建议',
      source: '个性化建议生成',
      score,
      level,
      summary: report.summary || '',
      suggestion: report.suggestion || '建议结合食用频率、份量和个人情况进行选择。',
      recommendation: report.recommendation || '',
      longTermRisk: report.long_term_risk || '',
    },
  ]
}
~~~

- [ ] **Step 4: 实现 AiAnalysisStages 组件和串行状态机**

组件接收 stages、introVisible 和 onComplete。内部同时用 activeIndex 和 completedCount 控制阶段，保证最后一张卡片也会进入已完成：

~~~javascript
const [activeIndex, setActiveIndex] = useState(-1)
const [completedCount, setCompletedCount] = useState(0)

useEffect(() => {
  if (introVisible) return undefined
  setCompletedCount(0)
  setActiveIndex(0)
  const timers = STAGE_IDS.map((_, index) => setTimeout(() => {
    setCompletedCount(index + 1)
    if (index < STAGE_IDS.length - 1) {
      setActiveIndex(index + 1)
    } else {
      setActiveIndex(-1)
      onComplete?.()
    }
  }, index * 760 + 650))
  return () => timers.forEach(clearTimeout)
}, [introVisible, onComplete])
~~~

渲染规则：

- index >= completedCount 且 index !== activeIndex：显示等待状态，不隐藏整块布局。
- index === activeIndex：显示 AI 正在分析和加载指示。
- index < completedCount：显示完整内容和已完成。
- 当前阶段约 650 毫秒后增加 completedCount 并进入下一阶段；最后一张完成后 activeIndex 设为 -1 并调用 onComplete。
- 全部内容使用真实 stages 数据，组件不生成新的风险或配料事实。

组件内部拆分 renderRecognition、renderFindings、renderJudgment、renderAdvice，保持四个阶段结构独立。

- [ ] **Step 5: 运行 helper 单测和 lint**

~~~powershell
cd web
node --test tests/ai-analysis-stages.test.mjs
npm run lint
~~~

预期：helper 单测 PASS，lint PASS。

~~~powershell
git add web/src/utils/aiAnalysisStages.js web/src/components/AiAnalysisStages.jsx web/tests/ai-analysis-stages.test.mjs
git commit -m "feat: add staged AI analysis presentation"
~~~

### Task 3: 集成结果页、弹窗时序与样式

**Files:**
- Modify: web/src/pages/ResultPage.jsx
- Modify: web/src/styles/pages.css

**Interfaces:**
- Consumes: buildAnalysisStages 和 AiAnalysisStages 的接口；现有 getLastResult() 结果对象。
- Produces: 结果页开场弹窗、四张完整 AI 分析卡片、无遮罩重叠的忌口提醒。

- [ ] **Step 1: 为结果页集成定义状态和串行时序**

在 ResultPage 中增加：

~~~javascript
const [showAiIntro, setShowAiIntro] = useState(true)
const [showAvoid, setShowAvoid] = useState(false)

useEffect(() => {
  const introTimer = setTimeout(() => {
    setShowAiIntro(false)
    if (hitAvoids.length > 0) setShowAvoid(true)
  }, 1200)
  return () => clearTimeout(introTimer)
}, [hitAvoids.length])
~~~

忌口弹窗的内容和“我知道了”按钮不变，只在 AI 开场弹窗结束后出现，避免两个全屏遮罩同时存在。

- [ ] **Step 2: 替换单一 AI 综合结论区域**

在原 result-ai-card 区域位置构造：

~~~javascript
const stages = buildAnalysisStages({
  result,
  score,
  level,
  risks,
  benefits,
  warnings,
  hitAvoids,
})
~~~

渲染：

~~~jsx
<Section title="AI 分析过程">
  <AiAnalysisStages stages={stages} introVisible={showAiIntro} />
</Section>
~~~

移除旧的 AI 综合结论、人群提醒、风险成分、有益成分和建议卡片；这些事实不删除，而是统一由 AI 发现、AI 判断和 AI 建议卡片承载。评分区、扫描图片和独立忌口提醒保持不变。

- [ ] **Step 3: 添加开场弹窗**

~~~jsx
{showAiIntro && (
  <div className="dialog-backdrop ai-intro-backdrop" role="status" aria-live="polite">
    <section className="ai-intro-modal">
      <span className="ai-intro-icon" aria-hidden="true">AI</span>
      <h2>AI 食品分析已完成</h2>
      <p>正在为你生成个性化分析</p>
    </section>
  </div>
)}
~~~

开场弹窗不包含必须点击的按钮；CSS 负责淡入，计时器负责自动关闭。

- [ ] **Step 4: 添加 AI 卡片和状态样式**

在 web/src/styles/pages.css 的 Result parity 区域增加：

~~~css
.ai-analysis-stack { display: grid; gap: 12px; }
.ai-stage-card { padding: 14px; border-left: 3px solid var(--ai); }
.ai-stage-card.is-pending { opacity: .62; }
.ai-stage-card.is-analyzing { animation: aiStageIn .28s ease-out both; }
.ai-stage-header { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.ai-stage-title { display: flex; align-items: center; gap: 8px; color: var(--ai); font-size: 15px; }
.ai-stage-status { color: var(--muted); font-size: 11px; }
.ai-stage-status.complete { color: var(--success-dark); }
.ai-stage-body { margin-top: 11px; color: var(--body); font-size: 13px; line-height: 1.6; }
.ai-stage-source { margin-top: 10px; color: var(--weak); font-size: 10px; }
.ai-stage-finding-group + .ai-stage-finding-group { margin-top: 11px; }
.ai-stage-finding-group h3 { color: var(--title); font-size: 12px; }
.ai-stage-loading { display: inline-flex; align-items: center; gap: 7px; }
.ai-stage-loading::before { content: ''; width: 12px; height: 12px; border: 2px solid var(--ai-soft); border-top-color: var(--ai); border-radius: 50%; animation: aiStageSpin .7s linear infinite; }
.ai-stage-score { display: flex; align-items: baseline; gap: 6px; color: var(--ai); font-weight: 850; }
.ai-intro-modal { width: min(100%, 320px); padding: 24px 18px; border-radius: 12px; text-align: center; background: #fff; box-shadow: 0 16px 44px rgba(15,23,42,.16); animation: aiIntroIn .22s ease-out both; }
.ai-intro-modal h2 { margin-top: 12px; font-size: 17px; }
.ai-intro-modal p { margin-top: 6px; color: var(--body); font-size: 12px; }
.ai-intro-icon { width: 42px; height: 42px; margin: 0 auto; border-radius: 12px; display: grid; place-items: center; color: #fff; background: var(--ai); font-size: 13px; font-weight: 900; }
@keyframes aiStageIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
@keyframes aiStageSpin { to { transform: rotate(360deg); } }
@keyframes aiIntroIn { from { opacity: 0; transform: scale(.96); } to { opacity: 1; transform: scale(1); } }
@media (prefers-reduced-motion: reduce) { .ai-stage-card.is-analyzing, .ai-intro-modal, .ai-stage-loading::before { animation: none; } }
~~~

沿用 --ai、--ai-soft、--success-dark 和现有风险颜色，不新增大面积单一紫色背景。

- [ ] **Step 5: 运行 Web 构建和静态检查**

~~~powershell
cd web
node --test tests/ai-analysis-stages.test.mjs
npm run lint
npm run build
~~~

预期：单测、lint 和 Vite production build 全部 PASS。

### Task 4: 端到端验证与交付检查

**Files:**
- Test: backend/tests/test_providers.py
- Test: backend/tests/test_routes.py
- Test: web/tests/ai-analysis-stages.test.mjs
- Verify: web/src/pages/ResultPage.jsx, web/src/components/AiAnalysisStages.jsx, web/src/styles/pages.css

**Interfaces:**
- Consumes: Task 1-3 完成的 API 数据和 UI 状态。
- Produces: 可现场演示的结果页，不修改无关功能。

- [ ] **Step 1: 运行全量后端测试**

~~~powershell
cd backend
python -m pytest -v
~~~

预期：所有测试通过，/analyze 响应契约仍保留 ai_report，无 provider key 时仍能返回 fallback。

- [ ] **Step 2: 运行全量 Web 验证**

~~~powershell
cd web
node --test tests/ai-analysis-stages.test.mjs
npm run test:motion
npm run lint
npm run build
~~~

预期：所有命令退出码为 0。

- [ ] **Step 3: 启动 Web 端做手动演示检查**

~~~powershell
cd web
npm run dev -- --host 127.0.0.1
~~~

检查一个包含风险成分和忌口命中的结果：

- 开场弹窗出现并自动消失。
- AI 识别、发现、判断、建议严格按顺序进入分析中和已完成。
- 评分区、扫描图和忌口提醒内容仍存在。
- 忌口弹窗在 AI 开场弹窗之后出现，两个遮罩不重叠。
- 四张卡片最终全部展开。
- AI 发现包含风险、有益、人群和忌口四组事实。
- 窄屏下配料标签、长文案和状态文字不溢出。

- [ ] **Step 4: 检查工作树并提交集成变更**

~~~powershell
git diff --check
git status --short
git add backend web
git commit -m "feat: present staged AI analysis on result page"
~~~

只提交本功能涉及的后端、Web、测试和文档变更，不修改已有无关用户改动。

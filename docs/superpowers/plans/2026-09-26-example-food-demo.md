# 示例食品快速体验 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (inline execution is already authorized for this task). Steps use checkbox syntax.

**Goal:** 在保留健康档案和真实上传流程的前提下，为首页增加“快速体验”入口，展示三张真实食品样例，并通过固定结果复用现有 AI 分析转场和结果页。

**Architecture:** Web 端增加只读本地样例注册表，保存三张图片引用和完整结果对象。示例页从注册表渲染卡片，点击后写入现有 `lastResult` 并带上样例上下文，结果页继续使用已有 `AiAnalysisStages`，但不写入扫描历史。

**Tech Stack:** React、React Router、Vite、CSS、Node built-in test runner、PowerShell。

## Global Constraints

- 保留首次访问的健康档案页和“暂时跳过”。
- 首页只新增小型“快速体验”入口。
- 示例页只展示小烤肠、安慕希酸奶、冰红茶三张卡片。
- 示例固定结果完全本地读取，不调用 OCR、AI 或后端。
- 真实上传继续走现有 `/scan` 和后端流程。
- 示例复用现有结果页和 AI 分析转场，不创建第二套结果页。
- 示例不写入 `scanHistory`、最近识别或家庭统计。
- 沿用现有视觉、动效和响应式规则。
- 图片放在 `web/public/images/demo/`，文件名使用 ASCII。

---

### Task 1: 准备图片资源

**Files:** `web/public/images/demo/xiaokaochang.jpg`, `anmuxi-yogurt.jpg`, `ice-black-tea.jpg`

- [ ] 复制三张用户提供的图片到目标目录。
- [ ] 用 `Get-ChildItem` 确认三个文件存在并检查大小。
- [ ] 提交资源：`git add web/public/images/demo; git commit -m "feat: add example food images"`。

### Task 2: 建立固定样例数据

**Files:** Create `web/src/data/exampleFoods.js`; Create `web/tests/example-foods.test.mjs`

**Interfaces:** Export `EXAMPLE_FOODS`, `getExampleFood(id)`, `isExampleResult(result)`。

- [ ] 先写测试：断言三个 ID、中文名、图片路径，以及每个结果的 `food_category`、`ingredients`、`health_score`、风险/有益数组和六个 AI 报告字段。
- [ ] 运行 `cd web; node --test tests/example-foods.test.mjs`，确认缺模块时失败。
- [ ] 实现三个固定结果。结果包含 `exampleId`、配料、评分、风险项、有益成分、人群提醒、忌口数组和 `ai_report.summary/detail/suggestion/long_term_risk/judgment/recommendation`。文案只依据图片可见信息，避免诊断性结论。
- [ ] 运行测试和 `npm run lint`，确认通过。
- [ ] 提交：`git add web/src/data/exampleFoods.js web/tests/example-foods.test.mjs; git commit -m "feat: add fixed example food results"`。

### Task 3: 新增示例食品页

**Files:** Create `web/src/pages/ExamplesPage.jsx`; Modify `web/src/main.jsx`, `web/src/styles/pages.css`; Create `web/tests/examples-page.test.mjs`

**Interfaces:** 页面消费 `EXAMPLE_FOODS` 和 `setLastResult`，产生 `/examples` 路由。

- [ ] 先写页面契约测试：源码包含“示例食品”、三个样例名、`/scan` 上传入口，且不出现“全部示例”。
- [ ] 实现同风格 `Page` + 三张 `Card`：卡片点击 `setLastResult({ ...item.result, imageSrc: item.imageSrc, exampleId: item.id })` 后 `navigate('/result')`，不调用 `addRecord`；底部按钮导航 `/scan`。
- [ ] 注册 `<Route path="/examples" element={<ExamplesPage />} />`，保持 `ProfileGate`。
- [ ] 增加同风格响应式样式，桌面最多三列，窄屏单列，图片 `object-fit: cover`。
- [ ] 运行页面测试、`npm run lint`、`npm run build`。
- [ ] 提交：`git add web/src/pages/ExamplesPage.jsx web/src/main.jsx web/src/styles/pages.css web/tests/examples-page.test.mjs; git commit -m "feat: add example food selection page"`。

### Task 4: 首页增加小入口

**Files:** Modify `web/src/pages/HomePage.jsx`, `web/src/styles/pages.css`; Create `web/tests/home-example-entry.test.mjs`

- [ ] 测试断言可见文字“快速体验”和 `/examples`，且原 `home-scan-action` 仍存在。
- [ ] 在现有扫描主按钮之后添加小型次级按钮，不替换主按钮。
- [ ] 使用现有颜色和焦点样式，控制高度和间距，不新增大卡片。
- [ ] 运行测试和 lint。
- [ ] 提交：`git add web/src/pages/HomePage.jsx web/src/styles/pages.css web/tests/home-example-entry.test.mjs; git commit -m "feat: add quick example entry to home"`。

### Task 5: 结果页接入样例上下文

**Files:** Modify `web/src/pages/ResultPage.jsx`, `web/src/styles/pages.css`; Create `web/tests/example-result.test.mjs`

**Interfaces:** 消费 `getLastResult()`、`isExampleResult()`、`result.imageSrc`，产生示例图片和“示例分析”标识。

- [ ] 测试断言 `ResultPage` 使用 `isExampleResult`、`imageSrc`、`/examples`，示例入口没有 `addRecord`。
- [ ] 在结果页计算 `exampleResult`，食品条使用 `src={result.imageSrc}` 和 `StoredImage`，保持真实扫描 `imageKey` 行为。
- [ ] 示例结果显示“示例分析”和返回示例页按钮，普通结果保持原文案。
- [ ] 不改动 `showAiIntro`、`buildAnalysisStages`、`AiAnalysisStages`，确保沿用现有转场，不发网络请求、不写历史。
- [ ] 运行测试、lint、build。
- [ ] 提交：`git add web/src/pages/ResultPage.jsx web/src/styles/pages.css web/tests/example-result.test.mjs; git commit -m "feat: show fixed example results in existing result page"`。

### Task 6: 全量验证

- [ ] 运行 `cd web; node --test tests/*.test.mjs; npm run test:motion; npm run lint; npm run build`。
- [ ] 启动 `npm run dev -- --host 127.0.0.1`，清空站点存储，验证“暂时跳过 → 首页 → 快速体验 → 三张样例 → 现有 AI 转场 → 示例分析结果”。
- [ ] 验证“上传自己的配料表”仍到 `/scan`，示例不出现在历史和最近识别。
- [ ] 检查桌面和 390px 窄屏布局，运行 `git diff --check`。

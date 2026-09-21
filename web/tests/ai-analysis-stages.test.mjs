import assert from 'node:assert/strict'
import { test } from 'node:test'
import { buildAnalysisStages, limitIngredients, riskLevelTone, sortRiskFindings, splitIngredients, splitJudgmentText } from '../src/utils/aiAnalysisStages.js'
import { buildAssistantQuestions, buildLocalAssistantAnswer, compactAssistantContext } from '../src/utils/resultAssistant.js'

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

test('recognition keeps at most twelve unique main ingredients', () => {
  const result = limitIngredients(['水', '水', ...Array.from({ length: 14 }, (_, index) => `成分${index}`)])

  assert.equal(result.items.length, 12)
  assert.equal(result.total, 15)
  assert.equal(new Set(result.items).size, 12)
})

test('analysis stages expose the bounded recognition summary', () => {
  const stage = buildAnalysisStages({
    result: { ingredients: '水,白砂糖,蛋白质,营养成分表,乳粉' },
  })[0]

  assert.deepEqual(stage.ingredients, ['水', '白砂糖', '乳粉'])
  assert.equal(stage.ingredientTotal, 3)
})

test('recognition fallback removes obvious OCR nutrition fragments', () => {
  assert.deepEqual(splitIngredients('植 物油,蛋白质,3.2克,本产品含有乳制品,乳粉'), ['植物油', '乳粉'])
})

test('judgment text is concise and split into readable paragraphs', () => {
  assert.deepEqual(
    splitJudgmentText('当前分析对象为儿童。主要风险成分为阿斯巴甜。需要控制频率。建议选择配料更简单的产品。补充说明。'),
    ['主要风险成分为阿斯巴甜。', '需要控制频率。', '建议选择配料更简单的产品。'],
  )
})

test('risk levels keep numeric legacy records visually layered', () => {
  assert.equal(riskLevelTone('高风险'), 'danger')
  assert.equal(riskLevelTone('中'), 'warning')
  assert.equal(riskLevelTone(1), 'success')
  assert.equal(riskLevelTone(2), 'warning')
  assert.equal(riskLevelTone(3), 'danger')
})

test('findings are ordered from highest to lowest risk', () => {
  const ordered = sortRiskFindings([
    { name: '低风险', risk_level: '低', deduct_score: 5 },
    { name: '中风险', risk_level: '中', deduct_score: 10 },
    { name: '高风险', risk_level: '高', deduct_score: 20 },
    { name: '中风险更高扣分', risk_level: '中', deduct_score: 15 },
  ])

  assert.deepEqual(ordered.map(item => item.name), ['高风险', '中风险更高扣分', '中风险', '低风险'])
})

test('assistant questions adapt to the current audience and avoid hits', () => {
  const questions = buildAssistantQuestions({
    result: { food_category: '能量饮料' },
    score: 58,
    userType: '儿童',
    risks: [{ name: '咖啡因', risk_level: '中' }],
    hitAvoids: [],
  })

  assert.deepEqual(questions, ['为什么只有58分？', '儿童还能喝吗？', '有什么更合适的替代？'])
  assert.equal(buildAssistantQuestions({ score: 70, userType: '普通人群', risks: [{ name: '咖啡因' }], hitAvoids: ['咖啡因'] })[1], '为什么命中我的忌口？')
})

test('assistant context stays compact and has a deterministic fallback', () => {
  const context = compactAssistantContext({ food_category: '饮料', ingredients: '水,咖啡因', ingredients_count_penalty: 8 }, {
    score: 58,
    userType: '儿童',
    risks: [{ name: '咖啡因', risk_level: '中', deduct: 10 }],
  })

  assert.equal(context.user_type, '儿童')
  assert.equal(context.risk_additives[0].name, '咖啡因')
  assert.match(buildLocalAssistantAnswer('儿童还能喝吗？', context), /儿童/)
})

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

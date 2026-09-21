export const STAGE_IDS = ['recognition', 'findings', 'judgment', 'advice']
export const MAX_DISPLAY_INGREDIENTS = 12

export function riskLevelRank(level) {
  const normalized = String(level ?? '').trim()
  if (normalized.includes('高') || normalized === '3') return 3
  if (normalized.includes('中') || normalized === '2') return 2
  if (normalized.includes('低') || normalized === '1') return 1
  return 0
}

export function riskLevelTone(level, fallback = 'info') {
  const rank = riskLevelRank(level)
  if (rank === 3) return 'danger'
  if (rank === 2) return 'warning'
  if (rank === 1) return 'success'
  return fallback
}

export function sortRiskFindings(items = []) {
  return [...items].sort((left, right) => {
    const levelDifference = riskLevelRank(right?.risk_level) - riskLevelRank(left?.risk_level)
    if (levelDifference) return levelDifference
    return Number(right?.deduct_score ?? right?.deduct ?? 0) - Number(left?.deduct_score ?? left?.deduct ?? 0)
  })
}

export function splitIngredients(value) {
  return String(value || '')
    .split(/[、,，;；\n\r]+/)
    .map(item => item.replace(/\s+/g, '').trim())
    .filter(item => item && !isIngredientDisplayNoise(item))
}

function isIngredientDisplayNoise(item) {
  if (/^(能量|蛋白质|脂肪|碳水化合物|钠|钙|营养成分表|单|双|项|原信息)$/.test(item)) return true
  if (/(添加量|含量|每100|每百|本产品含有)/.test(item)) return true
  return /\d/.test(item) && /(克|毫升|千焦|kJ|mg|ml|%|≥|≤)/i.test(item)
}

export function limitIngredients(ingredients, limit = MAX_DISPLAY_INGREDIENTS) {
  const unique = [...new Set((ingredients || []).map(item => String(item).trim()).filter(Boolean))]
  return { items: unique.slice(0, limit), total: unique.length }
}

export function splitJudgmentText(value) {
  const text = String(value || '').replace(/当前分析对象为[^。！？；]+[。！？；]/, '').trim()
  return text.split(/(?<=[。！？；])/u).map(item => item.trim()).filter(Boolean).slice(0, 3)
}

export function buildAnalysisStages({ result = {}, score = 0, level = '', risks = [], benefits = [], warnings = [], hitAvoids = [] }) {
  const report = result.ai_report || {}
  const ingredientSummary = limitIngredients(splitIngredients(result.ingredients))
  const orderedRisks = sortRiskFindings(risks)
  return [
    {
      id: 'recognition',
      title: 'AI 识别',
      source: 'OCR 识别 + AI 配料整理',
      ingredients: ingredientSummary.items,
      ingredientTotal: ingredientSummary.total,
    },
    {
      id: 'findings',
      title: 'AI 发现',
      source: '食品知识库匹配 + 家庭画像分析',
      risks: orderedRisks,
      benefits,
      warnings,
      avoids: hitAvoids,
      emptyMessage: orderedRisks.length || benefits.length || warnings.length || hitAvoids.length
        ? ''
        : '暂未发现需要特别关注的项目。',
    },
    {
      id: 'judgment',
      title: 'AI 判断',
      source: 'AI 个性化判断',
      text: report.judgment || report.detail || '已结合当前人群和识别结果完成判断。',
    },
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

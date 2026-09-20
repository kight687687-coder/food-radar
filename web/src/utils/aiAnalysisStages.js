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
    {
      id: 'recognition',
      title: 'AI 识别',
      source: 'OCR 识别 + AI 配料整理',
      ingredients: splitIngredients(result.ingredients),
    },
    {
      id: 'findings',
      title: 'AI 发现',
      source: '食品知识库匹配 + 家庭画像分析',
      risks,
      benefits,
      warnings,
      avoids: hitAvoids,
      emptyMessage: risks.length || benefits.length || warnings.length || hitAvoids.length
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

export function buildAssistantQuestions({ result = {}, score = 0, userType = '普通人群', risks = [], hitAvoids = [] }) {
  const questions = [`为什么只有${score}分？`]
  const category = String(result.food_category || '')
  const isDrink = /饮|奶|茶|咖啡|汁|水|酒/.test(category)
  const audience = String(userType || '普通人群')

  if (hitAvoids.length) {
    questions.push('为什么命中我的忌口？')
  } else if (audience !== '普通人群') {
    questions.push(`${audience}${isDrink ? '还能喝吗？' : '能不能吃？'}`)
  } else if (risks[0]?.name) {
    questions.push(`${risks[0].name}需要注意什么？`)
  } else {
    questions.push('我适合经常吃吗？')
  }

  questions.push('有什么更合适的替代？')
  return [...new Set(questions)].slice(0, 3)
}

export function compactAssistantContext(result = {}, { score = 0, userType = '普通人群', risks = [], benefits = [], warnings = [], hitAvoids = [] } = {}) {
  return {
    food_category: result.food_category || '当前食品',
    health_score: score,
    user_type: userType,
    ingredients: String(result.ingredients || '').slice(0, 1200),
    risk_additives: risks.slice(0, 6).map(item => ({
      name: item.name,
      risk_level: item.risk_level,
      deduct_score: item.deduct_score || item.deduct || 0,
      reason: item.reason,
    })),
    beneficial_ingredients: benefits.slice(0, 6).map(item => item.name || item.nutrient || item),
    group_warnings: warnings.slice(0, 4),
    avoid_warnings: hitAvoids.slice(0, 4),
    ingredients_count_penalty: result.ingredients_count_penalty || 0,
  }
}

export function buildLocalAssistantAnswer(question, context = {}) {
  const score = Number(context.health_score || 0)
  const risks = (context.risk_additives || []).filter(item => item?.name)
  const riskNames = risks.slice(0, 3).map(item => item.name).join('、') || '暂无明确风险成分'
  const userType = context.user_type || '普通人群'
  const food = context.food_category || '当前食品'
  if (question.includes('替代')) {
    return `可以优先寻找配料更短、风险成分更少的同类${food}。重点比较${riskNames}以及糖、盐含量，并结合${userType}的饮食限制选择。`
  }
  if (question.includes('忌口')) {
    return `这款${food}命中了你设置的忌口：${(context.avoid_warnings || []).join('、') || '相关成分'}。建议优先避开，并查看同类产品的配料表。`
  }
  if (question.includes('能不能') || question.includes('还能')) {
    return `当前${food}评分为${score}分，主要需要留意${riskNames}。${userType}建议控制食用频率和份量，不作为日常高频选择。`
  }
  return `当前${food}为${score}分，主要扣分来自${riskNames}。${context.ingredients_count_penalty ? '同时配料项目较多，评分进一步受到影响。' : ''}建议结合食用频率和个人情况判断。`
}

import { BENEFICIAL_ADDITIVE_NAMES } from '../data/constants'

export function scoreOf(record) {
  return Number(record?.score ?? record?.fullResult?.health_score ?? 0)
}

export function scoreMeta(score) {
  if (score >= 80) return { label: '安心', tone: 'success', className: 'good' }
  if (score >= 60) return { label: '需留意', tone: 'warning', className: 'mid' }
  if (score > 0) return { label: '谨慎', tone: 'danger', className: 'bad' }
  return { label: '待分析', tone: 'neutral', className: 'empty' }
}

export function averageScore(records) {
  const scores = records.map(scoreOf).filter(Boolean)
  return scores.length ? Math.round(scores.reduce((sum, value) => sum + value, 0) / scores.length) : 0
}

export function recentDays(records, days, offset = 0) {
  const end = new Date()
  end.setDate(end.getDate() - offset + 1)
  end.setHours(0, 0, 0, 0)
  const start = new Date(end)
  start.setDate(start.getDate() - days)
  return records.filter(record => {
    if (!record.createTime) return false
    const date = new Date(record.createTime)
    return date >= start && date < end
  })
}

export function riskThemes(records, limit = 3) {
  const counts = new Map()
  records.forEach(record => {
    const items = record.fullResult?.risk_additives || []
    items.filter(item => !BENEFICIAL_ADDITIVE_NAMES.includes(item.name)).forEach(item => {
      const name = item.name || '风险成分'
      counts.set(name, (counts.get(name) || 0) + 1)
    })
  })
  return [...counts].map(([name, count]) => ({ name, count })).sort((a, b) => b.count - a.count).slice(0, limit)
}

export function categoryThemes(records, limit = 3) {
  const counts = new Map()
  records.forEach(record => {
    const name = record.food_category || record.fullResult?.food_category || record.foodName || '常见食品'
    counts.set(name, (counts.get(name) || 0) + 1)
  })
  const total = records.length || 1
  return [...counts].map(([name, count]) => ({ name, count, percent: Math.round(count / total * 100) }))
    .sort((a, b) => b.count - a.count).slice(0, limit)
}

export function formatDateTime(value, includeYear = false) {
  if (!value) return ''
  const date = new Date(value)
  const datePart = `${includeYear ? `${date.getFullYear()}-` : ''}${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
  return `${datePart} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}

export function buildSevenDayTrend(records) {
  const result = []
  const labels = ['日', '一', '二', '三', '四', '五', '六']
  const now = new Date()
  for (let offset = 6; offset >= 0; offset -= 1) {
    const date = new Date(now)
    date.setDate(now.getDate() - offset)
    const key = date.toDateString()
    const dayRecords = records.filter(record => record.createTime && new Date(record.createTime).toDateString() === key)
    result.push({
      label: labels[date.getDay()],
      date: `${date.getMonth() + 1}/${date.getDate()}`,
      score: averageScore(dayRecords),
      count: dayRecords.length,
    })
  }
  return result
}

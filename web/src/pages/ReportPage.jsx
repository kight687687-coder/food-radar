import { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { Avatar } from '../components/Avatar'
import { OriginalIcon } from '../components/OriginalIcon'
import { Page } from '../components/Page'
import { StoredImage } from '../components/StoredImage'
import { useApp } from '../context/AppContext'
import { setLastResult } from '../services/storage'
import { averageScore, categoryThemes, formatDateTime, recentDays, riskThemes, scoreMeta } from '../utils/analytics'

export function ReportPage() {
  const { activeMember, memberHistory } = useApp()
  const navigate = useNavigate()
  const history = useMemo(() => memberHistory.filter(record => record.type !== 'pk'), [memberHistory])
  const week = recentDays(history, 7)
  const previous = recentDays(history, 7, 7)
  const basis = week.length ? week : history.slice(0, 10)
  const score = averageScore(basis)
  const previousScore = averageScore(previous)
  const meta = scoreMeta(score)
  const risks = riskThemes(basis)
  const categories = categoryThemes(basis)
  const attentionCount = week.filter(record => Number(record.score) < 70).length
  const coveredDays = new Set(week.map(record => new Date(record.createTime).toDateString())).size
  const beneficials = [...new Set(basis.flatMap(record => (record.fullResult?.beneficial_ingredients || []).map(item => item.nutrient || item.name).filter(Boolean)))].slice(0, 3)
  const trend = !week.length ? '本周记录不足，先展示最近记录均值' : !previousScore ? '继续记录后可对比上周变化' : Math.abs(score - previousScore) <= 1 ? '与上周基本持平' : score > previousScore ? `较上周上升 ${score - previousScore} 分` : `较上周下降 ${previousScore - score} 分`
  const trendTone = !week.length || !previousScore ? 'empty' : Math.abs(score - previousScore) <= 1 ? 'flat' : score > previousScore ? 'up' : 'down'
  const healthSummary = buildHealthSummary({ history, week, basis, score, meta, attentionCount })
  const trendHint = buildTrendHint({ history, week, coveredDays, risks })
  const healthAdvice = buildHealthAdvice({ history, risks, beneficials })
  const recent = history.slice(0, 3)
  const concerns = [
    { image: '/images/feature-icons/risk.png', title: '高频添加剂', desc: risks[0]?.name || '暂无明显高频风险', meta: risks[0] ? `${risks[0].count} 次` : '保持观察', tone: risks[0] ? 'warning' : 'success' },
    { image: '/images/feature-icons/health-report.png', title: '近期风险', desc: attentionCount ? '存在需留意记录' : '暂无明显低分记录', meta: attentionCount ? `${attentionCount} 次低于 70 分` : '本周', tone: attentionCount ? 'warning' : 'success' },
    { image: '/images/feature-icons/ingredient.png', title: '重点品类', desc: categories[0]?.name || '继续积累记录', meta: categories[0] ? `${categories[0].percent}%` : '待生成', tone: 'info' },
  ]

  function openRecord(record) {
    setLastResult({ ...(record.fullResult || {}), food_category: record.food_category || record.foodName, imageKey: record.imageKey })
    navigate('/result')
  }

  return (
    <Page className="report-page">
      <div className="member-header"><Avatar src={activeMember?.avatar} name={activeMember?.nickname || '家'} /><div><div><strong>{activeMember?.nickname || '当前成员'}</strong><span className="tag success">当前成员</span></div><p>{activeMember?.userType || '普通人群'} · 家庭健康档案</p></div></div>
      <section className={`archive-hero tone-${meta.tone}`}><small>近7天安全指数</small><div className="archive-score"><strong>{score || '--'}</strong><span className={`tag ${meta.tone}`}>{history.length ? meta.label : '等待记录'}</span></div><p className={`archive-trend trend-${trendTone}`}>{trend}</p><div className="archive-insights"><div><span>健康总结</span><p>{healthSummary}</p></div><div><span>趋势提示</span><p>{trendHint}</p></div><div><span>健康建议</span><p>{healthAdvice}</p><small className="archive-nutrition-note">营养关注：蛋白质、钙、膳食纤维；控制糖、钠和饱和脂肪。</small></div></div></section>

      <section className="report-section-card"><header><h2>重点关注</h2><span>支撑当前判断</span></header>{concerns.map(item => <div className="report-list-row concern" key={item.title}><img className="report-row-image" src={item.image} alt="" /><span><strong>{item.title}</strong><small>{item.desc}</small></span><b className={`report-metric ${item.tone}`}>{item.meta}</b></div>)}</section>

      {history.length > 0 && <section className="report-section-card"><header><h2>长期画像</h2><span>基于近期记录</span></header><div className="report-profile-row">{risks.slice(0, 2).map(risk => <span key={risk.name}><strong>{risk.name}</strong><small>出现 {risk.count} 次</small></span>)}{categories.slice(0, 1).map(category => <span key={category.name}><strong>{category.name}</strong><small>占比 {category.percent}%</small></span>)}</div></section>}

      <section className="report-section-card"><header><h2>食品记录</h2><button type="button" onClick={() => navigate('/history')}>查看全部</button></header>{recent.length ? recent.map(record => <button className="report-record-row" type="button" key={record.recordId || record.createTime} onClick={() => openRecord(record)}><StoredImage imageKey={record.imageKey} className="report-record-thumb" alt="" /><span><strong>{record.foodName || '未命名食品'}</strong><small>{record.food_category || '食品'} · {formatDateTime(record.createTime)}</small></span><b className={scoreMeta(Number(record.score)).className}>{record.score || 0}<small>{scoreMeta(Number(record.score)).label}</small></b></button>) : <button className="report-empty" type="button" onClick={() => navigate('/scan')}><strong>还没有食品记录</strong><span>识别几次常吃食品后，这里会显示最近三条扫描记录。</span></button>}</section>

      <section className="report-section-card report-report-section"><button className="report-report-link" type="button" onClick={() => navigate('/card-report')}><img className="report-row-image" src="/images/feature-icons/health-report.png" alt="" /><span><strong>饮食报告</strong><small>查看长期饮食趋势与安全变化</small></span><OriginalIcon name="arrow-right" className="report-arrow" /></button></section>
    </Page>
  )
}

function buildHealthSummary({ history, week, basis, score, meta, attentionCount }) {
  if (!history.length) return '还没有食品记录，先扫描几款常吃食品，系统会生成你的健康状态。'
  if (!week.length) return `近 7 天暂无新记录，当前参考最近 ${basis.length} 条食品记录，平均安全指数 ${score} 分，整体处于${meta.label}状态。`
  return `近 7 天已记录 ${week.length} 次食品，平均安全指数 ${score} 分，整体处于${meta.label}状态。${attentionCount ? `其中 ${attentionCount} 次评分低于 70 分。` : '本周暂未出现低于 70 分的记录。'}`
}

function buildTrendHint({ history, week, coveredDays, risks }) {
  if (!history.length) return '从常吃食品开始记录，逐步形成个人饮食趋势和风险画像。'
  if (!week.length) return '近 7 天没有新记录，继续记录不同日期和不同类型的食品，趋势判断会更稳定。'
  if (risks[0]) return `近 7 天覆盖 ${coveredDays} 天，${risks[0].name} 出现 ${risks[0].count} 次，建议继续观察同类食品的出现频率。`
  return `近 7 天覆盖 ${coveredDays} 天，暂未发现重复出现的高频风险；继续记录可让趋势判断更稳定。`
}

function buildHealthAdvice({ history, risks, beneficials }) {
  if (!history.length) return '先记录常吃食品，再结合配料表和营养成分表进行比较。优先查看每 100 克或每份的糖、钠、饱和脂肪、蛋白质和钙。'
  const riskNames = risks.slice(0, 2).map(item => item.name)
  const productExamples = []
  if (riskNames.some(name => /亚硝|防腐|护色/.test(name))) productExamples.push('小烤肠、火腿肠等加工肉制品')
  if (riskNames.some(name => /糖|果葡|甜味/.test(name))) productExamples.push('冰红茶、果汁饮料等含糖饮品')
  const reduceText = productExamples.length ? `近期减少${productExamples.join('、')}的食用频率` : riskNames.length ? `近期减少含${riskNames.join('、')}的高频食品` : '优先选择配料更清晰、加工更简单的食品'
  const beneficialText = beneficials.length ? `当前记录中可关注${beneficials.join('、')}等营养成分。` : ''
  return `${reduceText}，可以用白水、无糖茶、无糖酸奶、鸡蛋或低盐食品替换。${beneficialText}营养成分表建议比较每 100 克或每份的蛋白质、钙、膳食纤维，以及糖、钠和饱和脂肪。`
}

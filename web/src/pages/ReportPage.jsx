import { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { Avatar } from '../components/Avatar'
import { OriginalIcon } from '../components/OriginalIcon'
import { Page } from '../components/Page'
import { useApp } from '../context/AppContext'
import { setLastResult } from '../services/storage'
import { averageScore, categoryThemes, recentDays, riskThemes, scoreMeta } from '../utils/analytics'

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
  const trend = !week.length ? '本周记录不足，先展示最近记录均值' : !previousScore ? '继续记录后可对比上周变化' : Math.abs(score - previousScore) <= 1 ? '与上周基本持平' : score > previousScore ? `较上周上升 ${score - previousScore} 分` : `较上周下降 ${previousScore - score} 分`
  const trendTone = !week.length || !previousScore ? 'empty' : Math.abs(score - previousScore) <= 1 ? 'flat' : score > previousScore ? 'up' : 'down'
  const reason = !history.length ? '识别几次常吃食品后，系统会解释分数变化的主要原因。' : risks[0] ? `${risks[0].name} 近 7 天出现 ${risks[0].count} 次，频率偏高。` : categories[0] ? `${categories[0].name} 占近期记录 ${categories[0].percent}%。` : '近期未发现明显高频风险。'
  const suggestion = risks[0] ? `减少含 ${risks[0].name} 的高添加剂食品，购买前多看配料表。` : '保持记录常吃食品，优先选择配料表更短、添加剂更少的产品。'
  const recent = history.slice(0, 3)
  const actions = [
    { title: risks[0] ? '查看高频添加剂说明' : '选择配料表更短的产品', desc: risks[0]?.name || '优先看前 5 位成分', image: '/images/feature-icons/ingredient.png', path: risks[0] ? `/wiki/${encodeURIComponent(risks[0].name)}` : '/wiki' },
    { title: week.length < 3 ? `本周继续识别 ${3 - week.length} 次` : '保持本周记录节奏', desc: week.length < 3 ? '让趋势判断更稳定' : '已具备基础趋势样本', image: '/images/feature-icons/score.png', path: '/scan' },
    { title: '更新忌口与偏好', desc: '让建议更贴合家庭成员', image: '/images/feature-icons/avoid.png', path: '/avoid' },
  ]
  const concerns = [
    { image: '/images/feature-icons/risk.png', title: '高频添加剂', desc: risks[0]?.name || '暂无明显高频风险', meta: risks[0] ? `${risks[0].count} 次` : '保持观察', tone: risks[0] ? 'warning' : 'success' },
    { image: '/images/feature-icons/health-report.png', title: '近期风险', desc: attentionCount ? '存在需留意记录' : '暂无明显低分记录', meta: attentionCount ? `${attentionCount} 次低于 70 分` : '本周', tone: attentionCount ? 'warning' : 'success' },
    { image: '/images/feature-icons/ingredient.png', title: '重点品类', desc: categories[0]?.name || '继续积累记录', meta: categories[0] ? `${categories[0].percent}%` : '待生成', tone: 'info' },
  ]
  const manage = [
    { image: '/images/feature-icons/history.png', title: '食品记录', desc: '查看识别历史', path: '/history' },
    { image: '/images/feature-icons/health-report.png', title: '饮食趋势', desc: '看长期变化', path: '/card-report' },
    { image: '/images/feature-icons/avoid.png', title: '风险偏好', desc: '管理忌口限制', path: '/avoid' },
    { image: '/images/feature-icons/family.png', title: '家庭成员', desc: '切换家庭档案', path: '/family' },
  ]

  function openRecord(record) {
    setLastResult({ ...(record.fullResult || {}), food_category: record.food_category || record.foodName, imageKey: record.imageKey })
    navigate('/result')
  }

  return (
    <Page className="report-page">
      <div className="member-header"><Avatar src={activeMember?.avatar} name={activeMember?.nickname || '家'} /><div><div><strong>{activeMember?.nickname || '当前成员'}</strong><span className="tag success">当前成员</span></div><p>{activeMember?.userType || '普通人群'} · 家庭健康档案</p></div></div>
      <section className={`archive-hero tone-${meta.tone}`}><small>近7天安全指数</small><div className="archive-score"><strong>{score || '--'}</strong><span className={`tag ${meta.tone}`}>{history.length ? meta.label : '等待记录'}</span></div><p className={`archive-trend trend-${trendTone}`}>{trend}</p><div className="archive-insights"><div><span>主要原因</span><p>{reason}</p></div><div><span>建议</span><p>{suggestion}</p></div></div></section>

      <section className="report-section-card"><header><h2>接下来可以做</h2><span>未来 7 天</span></header>{actions.map(item => <button className="report-list-row" key={item.title} type="button" onClick={() => navigate(item.path)}><img className="report-row-image" src={item.image} alt="" /><span><strong>{item.title}</strong><small>{item.desc}</small></span><OriginalIcon name="arrow-right" className="report-arrow" /></button>)}</section>

      <section className="report-section-card"><header><h2>重点关注</h2><span>支撑当前判断</span></header>{concerns.map(item => <div className="report-list-row concern" key={item.title}><img className="report-row-image" src={item.image} alt="" /><span><strong>{item.title}</strong><small>{item.desc}</small></span><b className={`report-metric ${item.tone}`}>{item.meta}</b></div>)}</section>

      <section className="report-section-card"><header><h2>最近记录</h2><button type="button" onClick={() => navigate('/history')}>查看全部</button></header>{recent.length ? recent.map(record => <button className="report-record-row" type="button" key={record.recordId || record.createTime} onClick={() => openRecord(record)}><span><strong>{record.foodName || '未命名食品'}</strong><small>{record.food_category || '食品'} · {new Date(record.createTime).toLocaleDateString('zh-CN')}</small></span><b className={scoreMeta(Number(record.score)).className}>{record.score || 0}<small>{scoreMeta(Number(record.score)).label}</small></b></button>) : <button className="report-empty" type="button" onClick={() => navigate('/scan')}><strong>还没有食品记录</strong><span>识别几次常吃食品后，这里会成为健康判断的证据。</span></button>}</section>

      {history.length > 0 && <section className="report-section-card"><header><h2>长期画像</h2><span>基于近期记录</span></header><div className="report-profile-row">{risks.slice(0, 2).map(risk => <span key={risk.name}><strong>{risk.name}</strong><small>出现 {risk.count} 次</small></span>)}{categories.slice(0, 1).map(category => <span key={category.name}><strong>{category.name}</strong><small>占比 {category.percent}%</small></span>)}</div></section>}

      <section className="report-section-card manage-section"><header><h2>档案管理</h2></header><div className="manage-grid">{manage.map(item => <button type="button" className="manage-card" key={item.path} onClick={() => navigate(item.path)}><img className="manage-image" src={item.image} alt="" /><span><strong>{item.title}</strong><small>{item.desc}</small></span></button>)}</div></section>
    </Page>
  )
}

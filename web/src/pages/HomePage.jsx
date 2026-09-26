import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { OriginalIcon } from '../components/OriginalIcon'
import { Card, Page, Section } from '../components/Page'
import { StoredImage } from '../components/StoredImage'
import { useApp } from '../context/AppContext'
import { setLastResult } from '../services/storage'
import { averageScore, buildSevenDayTrend, recentDays, riskThemes, scoreMeta } from '../utils/analytics'

const quickActions = [
  { title: '添加剂百科', caption: '查成分', path: '/wiki', image: '/images/entry-icons/additive-3d.png' },
  { title: '配料表 PK', caption: '比一比', path: '/compare', image: '/images/entry-icons/compare-3d.png' },
  { title: '营养师问答', caption: '问问题', path: '/ai-chat', image: '/images/entry-icons/qa-3d.png' },
  { title: '健康档案', caption: '看趋势', path: '/report', image: '/images/entry-icons/profile-3d.png' },
]

export function HomePage() {
  const { memberHistory } = useApp()
  const navigate = useNavigate()
  const [showEngine, setShowEngine] = useState(false)
  const history = useMemo(() => memberHistory.filter(record => record.type !== 'pk'), [memberHistory])
  const recentBase = history.slice(0, 10)
  const score = averageScore(recentBase)
  const scoreState = score ? scoreMeta(score) : { label: '等待记录', tone: 'empty' }
  const today = new Date().toDateString()
  const todayCount = history.filter(record => record.createTime && new Date(record.createTime).toDateString() === today).length
  const guardDays = new Set(history.filter(record => record.createTime).map(record => new Date(record.createTime).toDateString())).size
  const topRisk = riskThemes(history, 1)[0]
  const trend = buildSevenDayTrend(history)
  const weekScores = trend.map(item => item.score).filter(Boolean)
  const summary = !history.length
    ? '还没有识别记录，先选一张配料表图片看看。'
    : topRisk ? `近期 ${topRisk.name} 出现 ${topRisk.count} 次，需要多留意。`
      : score >= 80 ? '最近识别的食品整体比较安心。' : '最近有一些成分需要留意，买之前可以多比较配料表。'
  const suggestion = !history.length
    ? '从家里常吃的食品开始，几次之后就能看出更清楚的饮食变化。'
    : weekScores.length < 3 ? '继续积累本周记录，趋势判断会更稳定。' : `本周有效记录平均 ${averageScore(recentDays(history, 7))} 分。`
  const recent = history[0]
  const ringColor = score >= 80 ? '#07c160' : score >= 60 ? '#ff7d00' : score > 0 ? '#f53f3f' : '#c9cdd4'

  function openRecord(record) {
    if (!record) return
    setLastResult({ ...(record.fullResult || {}), food_category: record.food_category || record.foodName, imageKey: record.imageKey })
    navigate('/result')
  }

  return (
    <Page title="食安雷达" subtitle="家庭食品安全管家" action={<button className="standards-button" onClick={() => setShowEngine(true)} type="button"><OriginalIcon name="shield-check" />参考国家标准</button>} className="home-page">
      <Card className={`home-hero level-${scoreState.tone}`}>
        <div className="home-hero-main">
          <div className="home-hero-copy">
            <div className="home-safety-head">
              <div><strong className="home-hero-label">家庭安全指数</strong><span className="home-hero-sub">根据最近识别记录更新</span></div>
              <span className={`home-status-pill level-${scoreState.tone}`}>{scoreState.label}</span>
            </div>
            <div className={`hero-number level-${scoreState.tone}`}>{score || '--'}<small>分</small></div>
            <p>今日已分析 {todayCount} 次 · 已守护 {guardDays} 天</p>
          </div>
          <div className="home-score-ring" style={{ background: `conic-gradient(${ringColor} ${(score || 0) * 3.6}deg, #f2f3f5 0deg)` }}><span>{score || '--'}</span></div>
        </div>
        <div className="home-insight"><strong>{summary}</strong><span>{suggestion}</span></div>
        <button className="home-scan-action" type="button" onClick={() => navigate('/scan')}>
          <span className="home-camera"><img src="/images/action-icons/camera-action-3d.png" alt="" /></span>
          <span><strong>拍照识别配料表</strong><small>上传配料表，立即生成食品安全分析</small></span>
          <OriginalIcon name="arrow-right" className="home-action-arrow" />
        </button>
        <button className="home-example-link" type="button" onClick={() => navigate('/examples')}><span aria-hidden="true">✦</span> 示例体验 <OriginalIcon name="arrow-right" /></button>
      </Card>

      <Section title="常用功能">
        <div className="quick-grid">{quickActions.map(item => <button key={item.path} type="button" className="quick-card" onClick={() => navigate(item.path)}><img src={item.image} alt="" /><strong>{item.title}</strong><small>{item.caption}</small></button>)}</div>
      </Section>

      <Section title="最近识别" action={history.length ? <button className="section-action" type="button" onClick={() => navigate('/history')}>查看全部</button> : null}>
        {recent ? (
          <Card as="button" className="recent-record" type="button" onClick={() => openRecord(recent)}>
            {recent.imageKey ? <StoredImage imageKey={recent.imageKey} className="record-thumb" alt={recent.foodName || '食品图片'} /> : <span className="record-thumb record-placeholder"><OriginalIcon name="list" /></span>}
            <span className="list-main"><strong className="list-title">{recent.foodName || recent.food_category || '未命名食品'}</strong><small className="list-description">{recent.food_category || '食品'} · 最近识别</small></span>
            <span className={`home-recent-score ${scoreMeta(Number(recent.score)).className}`}><strong>{recent.score || 0}分</strong><small>{scoreMeta(Number(recent.score)).label}</small></span>
          </Card>
        ) : (
          <Card as="button" className="recent-empty" type="button" onClick={() => navigate('/scan')}><OriginalIcon name="list" className="recent-empty-icon" /><span><strong>还没有识别记录</strong><small>选一张配料表图片，生成第一份分析</small></span></Card>
        )}
      </Section>

      {showEngine && <div className="sheet-backdrop" onMouseDown={() => setShowEngine(false)} role="presentation"><section className="bottom-sheet" onMouseDown={event => event.stopPropagation()} aria-modal="true" role="dialog" aria-label="食品安全评估依据"><header><h2>食品安全评估依据</h2><button className="engine-close" type="button" onClick={() => setShowEngine(false)} aria-label="关闭">×</button></header><div className="engine-step"><span>🧩</span><div><small>输入层 · 识别</small><strong>食品信息识别</strong><p>成分 / 品类 / 加工方式</p></div></div><div className="engine-step"><span>⚙️</span><div><small>评估层 · 匹配</small><strong>风险规则映射</strong><p>参考食品安全国家标准与添加剂使用规则</p></div></div><div className="engine-step"><span>📊</span><div><small>输出层 · 生成</small><strong>风险信号生成</strong><p>轻度关注 / 中风险 / 高风险</p></div></div><p className="sheet-note">参考国家食品安全标准及公开规则，仅作日常风险提示</p></section></div>}
    </Page>
  )
}

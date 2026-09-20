import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AiAnalysisStages } from '../components/AiAnalysisStages'
import { Card, Page, Section } from '../components/Page'
import { StoredImage } from '../components/StoredImage'
import { EmptyState } from '../components/States'
import { getLastResult, setComparePreset } from '../services/storage'
import { scoreMeta } from '../utils/analytics'
import { buildAnalysisStages } from '../utils/aiAnalysisStages'

export function ResultPage() {
  const navigate = useNavigate()
  const result = getLastResult()
  const hitAvoids = useMemo(() => (result?.avoid_warnings || []).map(item => item.name || item.avoid_name || item).filter(Boolean), [result])
  const [showAiIntro, setShowAiIntro] = useState(true)
  const [showAvoid, setShowAvoid] = useState(false)

  useEffect(() => {
    const introTimer = window.setTimeout(() => {
      setShowAiIntro(false)
      if (hitAvoids.length > 0) setShowAvoid(true)
    }, 1200)
    return () => window.clearTimeout(introTimer)
  }, [hitAvoids.length])

  if (!result) return <Page title="食品分析结果" back><Card><EmptyState title="暂无分析数据" description="先上传一张清晰的配料表图片，再查看完整分析结果。" action={<button className="button primary" onClick={() => navigate('/scan')}>开始识别</button>} /></Card></Page>

  const score = Number(result.health_score || 0)
  const meta = scoreMeta(score)
  const risks = (result.risk_additives || []).slice(0, 6).map(item => { const deduct = Number(item.deduct_score || item.deduct || 0); return { ...item, deduct, tone: deduct >= 20 ? 'danger' : deduct >= 10 ? 'warning' : 'success' } })
  if (Number(result.ingredients_count_penalty) > 0) risks.push({ name: '配料较多', risk_level: '中风险', deduct: result.ingredients_count_penalty, tone: 'warning', reason: '配料项目较多，建议优先选择配料更短的同类食品。' })
  const benefits = (result.beneficial_ingredients || []).slice(0, 8).map(item => ({ name: item.nutrient || item.name || item })).filter(item => item.name)
  const warnings = (result.group_warnings || []).map(item => item.warning || item.reason || item.description || item.msg || item).filter(Boolean)
  const level = score >= 80 ? '可以放心食用' : score >= 60 ? '建议适量食用' : '需要谨慎选择'
  const stages = buildAnalysisStages({ result, score, level, risks, benefits, warnings, hitAvoids })

  function compare() { setComparePreset(result); navigate('/compare') }

  return <Page className="result-page">
    <div className="result-native-top"><button type="button" onClick={() => navigate(-1)}>返回</button><h1>食品分析结果</h1></div>
    <section className={`result-score-card tone-${meta.tone}`}><small>健康评分</small><strong className={meta.className}>{score}</strong><h2>{level}</h2><p>{risks.length} 项风险 · {benefits.length} 项有益成分</p><em>参照 GB 2760 等国家食品安全标准</em></section>

    {result.imageKey && <Section><Card className="result-food-strip"><StoredImage imageKey={result.imageKey} className="result-food-thumb" alt={result.food_category || '识别食品'} /><span><strong>{result.food_category || '识别食品'}</strong><small>配料表分析结果</small></span></Card></Section>}

    <Section title="AI 分析过程"><AiAnalysisStages stages={stages} introVisible={showAiIntro} /></Section>
    {hitAvoids.length > 0 && <Section><Card className="result-avoid-card"><h2>忌口提醒</h2><p>检测到你设置的忌口成分，建议谨慎食用或避免。</p><div className="tag-row">{hitAvoids.map(item => <span className="tag danger" key={item}>{item}</span>)}</div></Card></Section>}

    <div className="result-native-actions"><button className="button primary full" type="button" onClick={() => navigate('/scan')}>再选一张</button><div><button className="button secondary" type="button" onClick={compare}>PK 对比</button><button className="button secondary" type="button" onClick={() => navigate('/card-report')}>生成卡片</button></div></div>

    {showAiIntro && <div className="dialog-backdrop ai-intro-backdrop" role="status" aria-live="polite"><section className="ai-intro-modal"><span className="ai-intro-icon" aria-hidden="true">AI</span><h2>AI 食品分析已完成</h2><p>正在为你生成个性化分析</p></section></div>}
    {showAvoid && <div className="dialog-backdrop" role="presentation"><section className="result-avoid-modal" role="alertdialog" aria-modal="true"><h2>忌口提醒</h2><p>检测到你设置的忌口成分，请谨慎食用。</p><div className="tag-row">{hitAvoids.map(item => <span className="tag danger" key={item}>{item}</span>)}</div><button className="button primary full" type="button" onClick={() => setShowAvoid(false)}>我知道了</button></section></div>}
  </Page>
}

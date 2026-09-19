import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, Page, Section } from '../components/Page'
import { StoredImage } from '../components/StoredImage'
import { EmptyState } from '../components/States'
import { getLastResult, setComparePreset } from '../services/storage'
import { scoreMeta } from '../utils/analytics'

export function ResultPage() {
  const navigate = useNavigate()
  const result = getLastResult()
  const hitAvoids = useMemo(() => (result?.avoid_warnings || []).map(item => item.name || item.avoid_name || item).filter(Boolean), [result])
  const [showAvoid, setShowAvoid] = useState(hitAvoids.length > 0)

  if (!result) return <Page title="食品分析结果" back><Card><EmptyState title="暂无分析数据" description="先上传一张清晰的配料表图片，再查看完整分析结果。" action={<button className="button primary" onClick={() => navigate('/scan')}>开始识别</button>} /></Card></Page>

  const score = Number(result.health_score || 0)
  const meta = scoreMeta(score)
  const ai = result.ai_report || {}
  const risks = (result.risk_additives || []).slice(0, 6).map(item => { const deduct = Number(item.deduct_score || item.deduct || 0); return { ...item, deduct, tone: deduct >= 20 ? 'danger' : deduct >= 10 ? 'warning' : 'success' } })
  if (Number(result.ingredients_count_penalty) > 0) risks.push({ name: '配料较多', risk_level: '中风险', deduct: result.ingredients_count_penalty, tone: 'warning', reason: '配料项目较多，建议优先选择配料更短的同类食品。' })
  const benefits = (result.beneficial_ingredients || []).slice(0, 8).map(item => ({ name: item.nutrient || item.name || item })).filter(item => item.name)
  const warnings = (result.group_warnings || []).map(item => item.warning || item.reason || item.description || item.msg || item).filter(Boolean)
  const level = score >= 80 ? '可以放心食用' : score >= 60 ? '建议适量食用' : '需要谨慎选择'
  const aiTags = [level, risks.length ? `${risks.length} 项风险` : '整体风险较低', warnings.length ? '人群需注意' : '无额外人群提醒']

  function compare() { setComparePreset(result); navigate('/compare') }

  return <Page className="result-page">
    <div className="result-native-top"><button type="button" onClick={() => navigate(-1)}>返回</button><h1>食品分析结果</h1></div>
    <section className={`result-score-card tone-${meta.tone}`}><small>健康评分</small><strong className={meta.className}>{score}</strong><h2>{level}</h2><p>{risks.length} 项风险 · {benefits.length} 项有益成分</p><em>参照 GB 2760 等国家食品安全标准</em></section>

    {result.imageKey && <Section><Card className="result-food-strip"><StoredImage imageKey={result.imageKey} className="result-food-thumb" alt={result.food_category || '识别食品'} /><span><strong>{result.food_category || '识别食品'}</strong><small>配料表分析结果</small></span></Card></Section>}

    <Section><Card className="result-ai-card"><h2>AI 综合结论</h2><div className="tag-row">{aiTags.map(tag => <span className="tag ai" key={tag}>{tag}</span>)}</div><p>{ai.summary || (score >= 80 ? '整体风险较低，配料组成相对稳妥。' : '建议结合食用频率和个人情况谨慎选择。')}</p><p>{ai.detail || '评分综合考虑添加剂风险、人群提醒、忌口命中与有益成分。'}</p></Card></Section>
    {hitAvoids.length > 0 && <Section><Card className="result-avoid-card"><h2>忌口提醒</h2><p>检测到你设置的忌口成分，建议谨慎食用或避免。</p><div className="tag-row">{hitAvoids.map(item => <span className="tag danger" key={item}>{item}</span>)}</div></Card></Section>}
    {warnings.length > 0 && <Section><Card className="result-warning-card"><h2>人群提醒</h2>{warnings.map((warning, index) => <p key={`${warning}-${index}`}>{warning}</p>)}</Card></Section>}

    <Section><Card className="result-risk-card"><h2>风险成分</h2>{risks.length ? risks.map((risk, index) => <button className="result-risk-row" type="button" key={`${risk.name}-${index}`} onClick={() => navigate(`/wiki/${encodeURIComponent(risk.name)}`)}><i className={risk.tone} /><span><strong>{risk.name || '风险成分'}</strong><small>{risk.risk_level || (risk.tone === 'danger' ? '高风险' : '需关注')} · -{risk.deduct || 0} 分</small><p>{risk.reason || risk.description || '建议关注摄入频率。'}</p></span></button>) : <div className="result-native-empty">未发现明显风险成分，配料表整体风险较低。</div>}</Card></Section>
    <Section><Card className="result-benefit-card"><h2>有益成分</h2><p>检测到 {benefits.length} 项有益成分，本次加分 +{result.beneficial_bonus || 0}</p>{benefits.length ? <div className="tag-row">{benefits.map(item => <span className="tag success" key={item.name}>{item.name}</span>)}</div> : <span>暂未识别到明显有益成分。</span>}</Card></Section>
    <Section><Card className="result-suggestion-card"><h2>建议</h2><p>{ai.suggestion || '偶尔食用问题不大，建议结合个人情况控制频率。'}</p>{ai.long_term_risk && <div><strong>长期关注</strong><span>{ai.long_term_risk}</span></div>}</Card></Section>

    <div className="result-native-actions"><button className="button primary full" type="button" onClick={() => navigate('/scan')}>再选一张</button><div><button className="button secondary" type="button" onClick={compare}>PK 对比</button><button className="button secondary" type="button" onClick={() => navigate('/card-report')}>生成卡片</button></div></div>

    {showAvoid && <div className="dialog-backdrop" role="presentation"><section className="result-avoid-modal" role="alertdialog" aria-modal="true"><h2>忌口提醒</h2><p>检测到你设置的忌口成分，请谨慎食用。</p><div className="tag-row">{hitAvoids.map(item => <span className="tag danger" key={item}>{item}</span>)}</div><button className="button primary full" type="button" onClick={() => setShowAvoid(false)}>我知道了</button></section></div>}
  </Page>
}

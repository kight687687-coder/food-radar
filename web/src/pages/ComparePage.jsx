import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { OriginalIcon } from '../components/OriginalIcon'
import { Card, Page, Section } from '../components/Page'
import { LoadingOverlay } from '../components/States'
import { StoredImage } from '../components/StoredImage'
import { useApp } from '../context/AppContext'
import { analyzeImage, getAiComparison } from '../services/api'
import { saveImage } from '../services/imageStore'
import { createId, getCompareData, getComparePreset, setCompareData, setComparePreset } from '../services/storage'
import { prepareImage } from '../utils/image'

export function ComparePage() {
  const { activeMember, profile, addRecord, notify } = useApp()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const historyId = searchParams.get('recordId')
  const historyData = historyId ? getCompareData(historyId) : null
  const preset = !historyId ? getComparePreset() : null
  const presetFoods = preset?.foodA && preset?.foodB ? preset : { foodA: preset, foodB: null }
  const [foods, setFoods] = useState({ A: historyData?.foodA || presetFoods.foodA || null, B: historyData?.foodB || presetFoods.foodB || null })
  const [analyzing, setAnalyzing] = useState(false)
  const [advice, setAdvice] = useState(historyData?.advice || preset?.advice || '')
  const [adviceLoading, setAdviceLoading] = useState(false)
  const inputA = useRef(null), inputB = useRef(null)
  const isHistory = Boolean(historyData)
  useEffect(() => { if (preset) setComparePreset(null) }, [preset])
  const comparison = useMemo(() => computeComparison(foods.A, foods.B), [foods])

  async function selectFile(side, file) {
    if (!file || analyzing || isHistory) return
    try { const prepared = await prepareImage(file); setFoods(current => ({ ...current, [side]: { status: 'pending', previewUrl: prepared.previewUrl, prepared } })); setAdvice('') } catch (error) { notify(error.message, 'danger') }
  }
  async function resolveFood(food) {
    if (food?.status !== 'pending') return food
    const result = await analyzeImage(food.prepared.base64, { userType: activeMember?.userType || profile?.userType, userId: profile?.userId, avoidIds: activeMember?.selectedAvoids || [] })
    const imageKey = await saveImage(food.prepared.blob).catch(() => '')
    return { ...result, imageKey, previewUrl: food.previewUrl }
  }
  async function startComparison() {
    if (!foods.A || !foods.B || analyzing) return
    setAnalyzing(true)
    try {
      const [foodA, foodB] = await Promise.all([resolveFood(foods.A), resolveFood(foods.B)])
      setFoods({ A: foodA, B: foodB })
      const result = computeComparison(foodA, foodB)
      setAdviceLoading(true)
      let aiAdvice = ''
      try { aiAdvice = (await getAiComparison(foodA, foodB)).advice || '' } catch { aiAdvice = '结合个人忌口、评分和食用频率，优先选择风险成分更少的一款。' }
      setAdvice(aiAdvice); setAdviceLoading(false)
      if (!isHistory) { const recordId = createId('pk'), createTime = new Date().toISOString(); const record = addRecord({ recordId, type: 'pk', foodName: `${foodA.food_category || '食品 A'} VS ${foodB.food_category || '食品 B'}`, categoryA: foodA.food_category || '食品 A', categoryB: foodB.food_category || '食品 B', scoreA: result.scoreA, scoreB: result.scoreB, score: Math.max(result.scoreA, result.scoreB), winner: result.winner, winnerScore: Math.max(result.scoreA, result.scoreB), imageKeyA: foodA.imageKey, imageKeyB: foodB.imageKey, createTime }); setCompareData(record.recordId, { foodA, foodB, advice: aiAdvice }) }
    } catch (error) { notify(error.message || '分析失败，请稍后重试。', 'danger') } finally { setAnalyzing(false); setAdviceLoading(false) }
  }
  function reset() { setFoods({ A: null, B: null }); setAdvice(''); navigate('/compare', { replace: true }) }
  const ready = comparison && foods.A?.status !== 'pending' && foods.B?.status !== 'pending'

  return <Page title="食品对比" subtitle="选择两款食品，比较评分、风险和适用人群" back className="compare-page">
    <div className="compare-select-grid"><FoodSlot label="食品 A" food={foods.A} inputRef={inputA} disabled={isHistory || analyzing} onFile={file => selectFile('A', file)} /><FoodSlot label="食品 B" food={foods.B} inputRef={inputB} disabled={isHistory || analyzing} onFile={file => selectFile('B', file)} /></div>
    {!ready && !isHistory && foods.A && foods.B && <button className="button primary full compare-submit" type="button" disabled={analyzing} onClick={startComparison}>开始对比</button>}
    {ready && comparison && <>
      <Section><Card className="compare-result-card compare-winner-card"><small>推荐选择</small><h2>{comparison.winnerName}</h2><strong>{Math.max(comparison.scoreA, comparison.scoreB)} 分</strong><p>综合评分更高，风险成分更少。</p></Card></Section>
      <Section><Card className="compare-result-card compare-detail-card"><h2>对比详情</h2>{comparison.rows.map(row => <div className="compare-native-row" key={row.label}><strong>{row.label}</strong><div><span className={row.aWins ? 'win' : ''}>A {row.valueA}</span><span className={row.bWins ? 'win' : ''}>B {row.valueB}</span></div><small>{row.aWins ? 'A 更优' : row.bWins ? 'B 更优' : '差异不大'}</small></div>)}</Card></Section>
      <Section><Card className="compare-result-card compare-risk-card"><h2>风险差异</h2><div className="compare-risk-cols">{['A','B'].map(side => <div key={side}><strong>食品 {side}</strong><div className="tag-row">{comparison[`risk${side}`].length ? comparison[`risk${side}`].map((risk,index) => <span className={`tag ${risk.tone}`} key={`${risk.name}-${index}`}>{risk.name}</span>) : <span className="tag">暂无明显风险</span>}</div></div>)}</div><p>{comparison.winner === 'A' ? '食品 A 风险更少，建议优先选择。' : '食品 B 风险更少，建议优先选择。'}</p></Card></Section>
      <Section><Card className="compare-result-card compare-ai-card"><h2>AI 对比建议</h2><p><span className="tag ai">发现</span>{comparison.winner === 'A' ? '食品 A 综合评分更高，风险成分更少。' : '食品 B 综合评分更高，风险成分更少。'}</p><p><span className="tag success">建议</span>{adviceLoading ? '正在生成更具体的对比建议…' : advice || '结合个人忌口和食用频率选择更适合的一款。'}</p></Card></Section>
      {!isHistory && <button className="compare-reset-link" type="button" onClick={reset}>重新选择食品</button>}
    </>}
    {analyzing && <LoadingOverlay label="正在对比两款食品" />}
  </Page>
}

function FoodSlot({ label, food, inputRef, disabled, onFile }) {
  return <Card as="button" className="compare-food-slot" type="button" disabled={disabled} onClick={() => inputRef.current?.click()}><input ref={inputRef} className="visually-hidden" type="file" accept="image/*" onChange={event => { onFile(event.target.files?.[0]); event.target.value = '' }} /><small>{label}</small>{food ? (food.previewUrl || food.imageSrc ? <img src={food.previewUrl || food.imageSrc} alt={`${food.food_category || '食品'}配料表`} /> : food.imageKey ? <StoredImage imageKey={food.imageKey} className="compare-food-image" alt="" /> : <span className="compare-food-placeholder"><OriginalIcon name="list" /><em>选择图片</em></span>) : <span className="compare-food-placeholder"><OriginalIcon name="list" /><em>选择图片</em></span>}{food && <><strong>{food.food_category || '待分析图片'}</strong>{food.health_score && <b>{food.health_score}分</b>}</>}</Card>
}

function computeComparison(foodA, foodB) {
  if (!foodA || !foodB || foodA.status === 'pending' || foodB.status === 'pending') return null
  const scoreA=Number(foodA.health_score||0),scoreB=Number(foodB.health_score||0),riskA=foodA.risk_additives||[],riskB=foodB.risk_additives||[],benefitA=foodA.beneficial_ingredients||[],benefitB=foodB.beneficial_ingredients||[],warningsA=(foodA.group_warnings||[]).length+(foodA.avoid_warnings||[]).length,warningsB=(foodB.group_warnings||[]).length+(foodB.avoid_warnings||[]).length
  const winner=scoreA===scoreB?(riskA.length<=riskB.length?'A':'B'):scoreA>scoreB?'A':'B'
  return { winner, winnerName:(winner==='A'?foodA:foodB).food_category||`食品 ${winner}`, scoreA, scoreB, rows:[{label:'健康评分',valueA:`${scoreA} 分`,valueB:`${scoreB} 分`,aWins:scoreA>scoreB,bWins:scoreB>scoreA},{label:'风险成分',valueA:`${riskA.length} 项`,valueB:`${riskB.length} 项`,aWins:riskA.length<riskB.length,bWins:riskB.length<riskA.length},{label:'有益成分',valueA:`${benefitA.length} 项`,valueB:`${benefitB.length} 项`,aWins:benefitA.length>benefitB.length,bWins:benefitB.length>benefitA.length},{label:'人群提醒',valueA:`${warningsA} 条`,valueB:`${warningsB} 条`,aWins:warningsA<warningsB,bWins:warningsB<warningsA}], riskA:riskA.map(riskView), riskB:riskB.map(riskView) }
}
function riskView(item) { const deduct=Number(item.deduct_score||item.deduct||0); return {name:item.name||'风险成分',tone:deduct>=20?'danger':deduct>=10?'warning':'info'} }

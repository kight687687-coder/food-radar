import { useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { useNavigate } from 'react-router-dom'
import { AiAnalysisStages } from '../components/AiAnalysisStages'
import { Card, Page, Section } from '../components/Page'
import { StoredImage } from '../components/StoredImage'
import { EmptyState } from '../components/States'
import { useApp } from '../context/AppContext'
import { askNutritionist } from '../services/api'
import { getLastResult, setComparePreset } from '../services/storage'
import { scoreMeta } from '../utils/analytics'
import { buildAnalysisStages } from '../utils/aiAnalysisStages'
import { buildAssistantQuestions, buildLocalAssistantAnswer, compactAssistantContext } from '../utils/resultAssistant'
import { getAssistantPosition, snapAssistantEdge } from '../utils/resultAssistantPosition'

const ASSISTANT_ROBOT_SIZE = 76
const ASSISTANT_MARGIN = 16

function getViewport() {
  return {
    width: typeof window === 'undefined' ? 390 : window.innerWidth,
    height: typeof window === 'undefined' ? 844 : window.innerHeight,
  }
}

function getInitialAssistantPosition() {
  const viewport = getViewport()
  return {
    edge: 'right',
    offset: Math.max(ASSISTANT_MARGIN, Math.round(viewport.height * 0.72)),
  }
}

export function ResultPage() {
  const navigate = useNavigate()
  const { activeMember, profile } = useApp()
  const result = getLastResult()
  const hitAvoids = useMemo(() => (result?.avoid_warnings || []).map(item => item.name || item.avoid_name || item).filter(Boolean), [result])
  const [showAiIntro, setShowAiIntro] = useState(true)
  const [showAvoid, setShowAvoid] = useState(false)
  const [assistantQuestionsOpen, setAssistantQuestionsOpen] = useState(false)
  const [assistantPromptReady, setAssistantPromptReady] = useState(false)
  const assistantPromptDismissedRef = useRef(false)
  const [assistantPosition, setAssistantPosition] = useState(getInitialAssistantPosition)
  const [viewport, setViewport] = useState(getViewport)
  const [assistantExpression, setAssistantExpression] = useState(0)
  const [assistantQuestion, setAssistantQuestion] = useState('')
  const [assistantAnswer, setAssistantAnswer] = useState('')
  const [assistantLoading, setAssistantLoading] = useState(false)

  useEffect(() => {
    const introTimer = window.setTimeout(() => {
      setShowAiIntro(false)
      if (hitAvoids.length > 0) setShowAvoid(true)
    }, 1800)
    return () => window.clearTimeout(introTimer)
  }, [hitAvoids.length])

  useEffect(() => {
    const updateViewport = () => setViewport(getViewport())
    const promptTimer = window.setTimeout(() => {
      setAssistantPromptReady(true)
      if (!assistantPromptDismissedRef.current) setAssistantQuestionsOpen(true)
    }, 10000)
    window.addEventListener('resize', updateViewport)
    window.addEventListener('scroll', updateViewport, { passive: true })
    return () => {
      window.clearTimeout(promptTimer)
      window.removeEventListener('resize', updateViewport)
      window.removeEventListener('scroll', updateViewport)
    }
  }, [])

  if (!result) return <Page title="食品分析结果" back><Card><EmptyState title="暂无分析数据" description="先上传一张清晰的配料表图片，再查看完整分析结果。" action={<button className="button primary" onClick={() => navigate('/scan')}>开始识别</button>} /></Card></Page>

  const score = Number(result.health_score || 0)
  const meta = scoreMeta(score)
  const risks = (result.risk_additives || []).slice(0, 6).map(item => { const deduct = Number(item.deduct_score || item.deduct || 0); return { ...item, deduct, tone: deduct >= 20 ? 'danger' : deduct >= 10 ? 'warning' : 'success' } })
  if (Number(result.ingredients_count_penalty) > 0) risks.push({ name: '配料较多', risk_level: '中风险', deduct: result.ingredients_count_penalty, tone: 'warning', reason: '配料项目较多，建议优先选择配料更短的同类食品。' })
  const benefits = (result.beneficial_ingredients || []).slice(0, 8).map(item => ({ name: item.nutrient || item.name || item })).filter(item => item.name)
  const warnings = (result.group_warnings || []).map(item => item.warning || item.reason || item.description || item.msg || item).filter(Boolean)
  const level = score >= 80 ? '可以放心食用' : score >= 60 ? '建议适量食用' : '需要谨慎选择'
  const stages = buildAnalysisStages({ result, score, level, risks, benefits, warnings, hitAvoids })
  const userType = activeMember?.userType || profile?.userType || '普通人群'
  const assistantQuestions = buildAssistantQuestions({ result, score, userType, risks, hitAvoids })
  const assistantContext = compactAssistantContext(result, { score, userType, risks, benefits, warnings, hitAvoids })
  const expressions = [
    { name: '正常', symbol: '·ᴗ·' },
    { name: '微笑', symbol: '^ᴗ^' },
    { name: '惊讶', symbol: '⊙0⊙' },
    { name: '开心', symbol: '✦ᴗ✦' },
  ]

  function compare() { setComparePreset(result); navigate('/compare') }

  async function askCurrentAssistant(question) {
    setAssistantQuestion(question)
    setAssistantQuestionsOpen(false)
    assistantPromptDismissedRef.current = true
    setAssistantAnswer('')
    setAssistantLoading(true)
    try {
      const response = await askNutritionist(question, [], userType, profile?.userId, assistantContext)
      setAssistantAnswer(response.answer || buildLocalAssistantAnswer(question, assistantContext))
    } catch {
      setAssistantAnswer(buildLocalAssistantAnswer(question, assistantContext))
    } finally {
      setAssistantLoading(false)
    }
  }

  return <Page className="result-page">
    <div className="result-native-top"><button type="button" onClick={() => navigate(-1)}>返回</button><h1>食品分析结果</h1></div>
    <section className={`result-score-card tone-${meta.tone}`}><small>健康评分</small><strong className={meta.className}>{score}</strong><h2>{level}</h2><p>{risks.length} 项风险 · {benefits.length} 项有益成分</p><em>参照 GB 2760 等国家食品安全标准</em></section>

    {result.imageKey && <Section><Card className="result-food-strip"><StoredImage imageKey={result.imageKey} className="result-food-thumb" alt={result.food_category || '识别食品'} /><span><strong>{result.food_category || '识别食品'}</strong><small>配料表分析结果</small></span></Card></Section>}

    {hitAvoids.length > 0 && <Section><Card className="result-avoid-card"><h2>忌口提醒</h2><p>检测到你设置的忌口成分，建议谨慎食用或避免。</p><div className="tag-row">{hitAvoids.map(item => <span className="tag danger" key={item}>{item}</span>)}</div></Card></Section>}
    <Section title="AI 分析过程"><AiAnalysisStages stages={stages} introVisible={showAiIntro} /></Section>

    <div className="result-native-actions"><button className="button primary full" type="button" onClick={() => navigate('/scan')}>再选一张</button><div><button className="button secondary" type="button" onClick={compare}>PK 对比</button><button className="button secondary" type="button" onClick={() => navigate('/card-report')}>生成卡片</button></div></div>

    {showAiIntro && <div className="dialog-backdrop ai-intro-backdrop" role="status" aria-live="polite"><section className="ai-intro-modal"><div className="ai-intro-icon" aria-hidden="true"><span className="ai-intro-orbit" /><img src="/images/ai-analysis-avatar.png" alt="" /></div><div className="ai-intro-progress" aria-hidden="true"><span /></div><h2>AI 食品分析已完成</h2><p>正在为你生成个性化分析</p></section></div>}
    {showAvoid && <div className="dialog-backdrop" role="presentation"><section className="result-avoid-modal" role="alertdialog" aria-modal="true"><h2>忌口提醒</h2><p>检测到你设置的忌口成分，请谨慎食用。</p><div className="tag-row">{hitAvoids.map(item => <span className="tag danger" key={item}>{item}</span>)}</div><button className="button primary full" type="button" onClick={() => setShowAvoid(false)}>我知道了</button></section></div>}
    {typeof document !== 'undefined' && createPortal(<ResultAssistant
      questions={assistantQuestions}
      questionsOpen={assistantQuestionsOpen}
      promptReady={assistantPromptReady}
      expression={expressions[assistantExpression]}
      answer={assistantAnswer}
      question={assistantQuestion}
      loading={assistantLoading}
      position={assistantPosition}
      viewport={viewport}
      onToggleQuestions={() => setAssistantQuestionsOpen(value => {
        if (value) {
          assistantPromptDismissedRef.current = true
          return false
        }
        return true
      })}
      onPositionChange={setAssistantPosition}
      onCycleExpression={() => setAssistantExpression(index => (index + 1) % expressions.length)}
      onAsk={askCurrentAssistant}
      onCloseAnswer={() => { setAssistantAnswer(''); setAssistantQuestion('') }}
    />, document.body)}
  </Page>
}

function ResultAssistant({ questions, questionsOpen, promptReady, expression, answer, question, loading, position, viewport, onToggleQuestions, onPositionChange, onCycleExpression, onAsk, onCloseAnswer }) {
  const robotRef = useRef(null)
  const dragRef = useRef(null)
  const dragPositionRef = useRef(null)
  const movedRef = useRef(false)
  const [dragPosition, setDragPosition] = useState(null)
  const robotSize = viewport.width <= 560 ? 64 : ASSISTANT_ROBOT_SIZE
  const coordinates = dragPosition || getAssistantPosition({ edge: position.edge, offset: position.offset, viewportWidth: viewport.width, viewportHeight: viewport.height, robotSize, margin: ASSISTANT_MARGIN })

  function handlePointerDown(event) {
    if (event.button !== undefined && event.button !== 0) return
    const rect = robotRef.current?.getBoundingClientRect()
    if (!rect) return
    const startLeft = coordinates.left
    const startTop = coordinates.top
    movedRef.current = false
    dragRef.current = { pointerId: event.pointerId, startX: event.clientX, startY: event.clientY, startLeft, startTop }
    dragPositionRef.current = { left: startLeft, top: startTop }
    setDragPosition({ left: startLeft, top: startTop })
    robotRef.current?.setPointerCapture?.(event.pointerId)
    event.preventDefault()
  }

  function handlePointerMove(event) {
    const drag = dragRef.current
    if (!drag || drag.pointerId !== event.pointerId) return
    const left = Math.min(Math.max(drag.startLeft + event.clientX - drag.startX, ASSISTANT_MARGIN), Math.max(ASSISTANT_MARGIN, viewport.width - robotSize - ASSISTANT_MARGIN))
    const top = Math.min(Math.max(drag.startTop + event.clientY - drag.startY, ASSISTANT_MARGIN), Math.max(ASSISTANT_MARGIN, viewport.height - robotSize - ASSISTANT_MARGIN))
    if (Math.abs(left - drag.startLeft) > 3 || Math.abs(top - drag.startTop) > 3) movedRef.current = true
    dragPositionRef.current = { left, top }
    setDragPosition({ left, top })
    event.preventDefault()
  }

  function handlePointerUp(event) {
    const drag = dragRef.current
    if (!drag || drag.pointerId !== event.pointerId) return
    const current = dragPositionRef.current || { left: drag.startLeft, top: drag.startTop }
    onPositionChange(snapAssistantEdge({ left: current.left, top: current.top, viewportWidth: viewport.width, viewportHeight: viewport.height, robotSize, margin: ASSISTANT_MARGIN }))
    dragRef.current = null
    dragPositionRef.current = null
    setDragPosition(null)
    robotRef.current?.releasePointerCapture?.(event.pointerId)
  }

  return <>
    <aside className={`result-assistant edge-${position.edge} ${questionsOpen ? 'is-open' : 'is-collapsed'} ${dragPosition ? 'is-dragging' : ''}`} style={{ left: `${coordinates.left}px`, top: `${coordinates.top}px` }} aria-label="AI营养师助手">
      {promptReady && questionsOpen && <div className="result-assistant-prompts"><div className="result-assistant-prompt-head"><strong>想继续了解？</strong><button type="button" onClick={onToggleQuestions} aria-label="收起问题">收起</button></div><div className="result-assistant-question-list">{questions.map(item => <button type="button" key={item} onClick={() => onAsk(item)}>{item}</button>)}</div></div>}
      {promptReady && !questionsOpen && <button type="button" className="result-assistant-reopen" onClick={onToggleQuestions}>问题</button>}
      <button ref={robotRef} type="button" className="result-assistant-robot" onPointerDown={handlePointerDown} onPointerMove={handlePointerMove} onPointerUp={handlePointerUp} onPointerCancel={handlePointerUp} onClick={() => { if (!movedRef.current) onCycleExpression() }} aria-label={`AI营养师，当前${expression.name}表情，点击切换表情`}><img src="/images/entry-icons/qa-3d.png" alt="AI营养师" /><span className="result-assistant-expression" aria-hidden="true">{expression.symbol}</span></button>
    </aside>
    {(answer || loading) && <div className="result-assistant-sheet-backdrop" role="presentation"><section className="result-assistant-sheet" role="dialog" aria-modal="true" aria-label="AI营养师回答"><div className="result-assistant-sheet-bar"><span /><button type="button" onClick={onCloseAnswer} aria-label="关闭回答">关闭</button></div><div className="result-assistant-sheet-title"><img src="/images/entry-icons/qa-3d.png" alt="" /><div><strong>AI营养师</strong><small>基于本次扫描结果回答</small></div></div><p className="result-assistant-sheet-question">{question}</p>{loading ? <p className="result-assistant-loading">正在结合当前食品和用户画像分析...</p> : <p className="result-assistant-answer">{answer}</p>}</section></div>}
  </>
}

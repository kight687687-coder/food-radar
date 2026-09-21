import { useEffect, useState } from 'react'
import { Card } from './Page'
import { riskLevelTone, splitJudgmentText, STAGE_IDS } from '../utils/aiAnalysisStages'

const STAGE_DURATION = 650
const STAGE_INTERVAL = 760

export function AiAnalysisStages({ stages, introVisible, onComplete }) {
  const [activeIndex, setActiveIndex] = useState(-1)
  const [completedCount, setCompletedCount] = useState(0)

  useEffect(() => {
    if (introVisible) return undefined
    const startTimer = window.setTimeout(() => {
      setActiveIndex(0)
      setCompletedCount(0)
    }, 0)
    const timers = STAGE_IDS.map((_, index) => window.setTimeout(() => {
      setCompletedCount(index + 1)
      if (index < STAGE_IDS.length - 1) {
        setActiveIndex(index + 1)
      } else {
        setActiveIndex(-1)
        onComplete?.()
      }
    }, index * STAGE_INTERVAL + STAGE_DURATION))

    return () => {
      window.clearTimeout(startTimer)
      timers.forEach(window.clearTimeout)
    }
  }, [introVisible, onComplete])

  return (
    <div className="ai-analysis-stack">
      {stages.map((stage, index) => {
        const complete = index < completedCount
        const analyzing = activeIndex === index
        const status = complete ? '已完成' : analyzing ? 'AI 正在分析' : '等待中'
        const stateClass = complete ? 'is-complete' : analyzing ? 'is-analyzing' : 'is-pending'

        return (
          <Card className={`ai-stage-card ai-stage-tone-${stage.id} ${stateClass}`} key={stage.id}>
            <div className="ai-stage-header">
              <h3 className="ai-stage-title">{stage.title}</h3>
              <span className={`ai-stage-status ${complete ? 'complete' : ''}`}>
                {analyzing && <span className="ai-stage-loading" aria-hidden="true" />}
                {status}
              </span>
            </div>
            {complete && <div className="ai-stage-body">{renderStage(stage)}</div>}
            {analyzing && <div className="ai-stage-body ai-stage-thinking">正在整理当前食品与家庭成员信息...</div>}
            {!complete && !analyzing && <div className="ai-stage-body ai-stage-waiting">等待上一阶段完成</div>}
            {complete && <p className="ai-stage-source">{stage.source}</p>}
          </Card>
        )
      })}
    </div>
  )
}

function renderStage(stage) {
  if (stage.id === 'recognition') return renderRecognition(stage)
  if (stage.id === 'findings') return renderFindings(stage)
  if (stage.id === 'judgment') return <div className="ai-stage-judgment-copy">{splitJudgmentText(stage.text).map((paragraph, index) => <p key={`${paragraph}-${index}`}>{paragraph}</p>)}</div>
  return renderAdvice(stage)
}

function renderRecognition(stage) {
  if (!stage.ingredients.length) return <p className="ai-stage-empty">未提取到可展示的配料，请结合原始图片确认。</p>
  return (
    <>
      <p>已识别 {stage.ingredients.length} 项主要配料{stage.ingredientTotal > stage.ingredients.length ? `，其余 ${stage.ingredientTotal - stage.ingredients.length} 项已折叠` : ''}</p>
      <div className="tag-row ai-ingredient-tags">
        {stage.ingredients.map((ingredient, index) => <span className="tag ai" key={`${ingredient}-${index}`}>{ingredient}</span>)}
      </div>
    </>
  )
}

function renderFindings(stage) {
  if (stage.emptyMessage) return <p className="ai-stage-empty">{stage.emptyMessage}</p>
  return (
    <div className="ai-stage-findings">
      <FindingGroup title="需要注意" tone="info" items={stage.risks.map(item => ({ text: `${item.name || '风险成分'}${item.risk_level ? ` · ${item.risk_level}` : ''}`, tone: riskLevelTone(item.risk_level, item.tone) }))} />
      <FindingGroup title="有益信息" tone="success" items={stage.benefits.map(item => item.name || item.nutrient).filter(Boolean)} />
      <FindingGroup title="人群提醒" items={stage.warnings} plain />
      <FindingGroup title="忌口命中" tone="danger" items={stage.avoids} />
    </div>
  )
}

function FindingGroup({ title, tone = 'info', items, plain = false }) {
  if (!items.length) return null
  const entries = items.map(item => typeof item === 'string' ? { text: item, tone } : item)
  return (
    <div className="ai-stage-finding-group">
      <h4>{title}</h4>
      {plain
        ? <div className="ai-stage-plain-items">{entries.map((item, index) => <p key={`${item.text}-${index}`}>{item.text}</p>)}</div>
        : <div className="tag-row">{entries.map((item, index) => <span className={`tag ${item.tone}`} key={`${item.text}-${index}`}>{item.text}</span>)}</div>}
    </div>
  )
}

function renderAdvice(stage) {
  return (
    <>
      <div className="ai-stage-advice-score"><strong>{stage.score}</strong><span>分</span><em>{stage.level}</em></div>
      {stage.summary && <p>{stage.summary}</p>}
      <p>{stage.suggestion}</p>
      {stage.recommendation && <p>{stage.recommendation}</p>}
      {stage.longTermRisk && <div className="ai-stage-long-term"><strong>长期关注</strong><span>{stage.longTermRisk}</span></div>}
    </>
  )
}

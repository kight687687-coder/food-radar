import { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, Page, Section } from '../components/Page'
import { LoadingOverlay } from '../components/States'
import { StoredImage } from '../components/StoredImage'
import { useApp } from '../context/AppContext'
import { analyzeImage } from '../services/api'
import { saveImage } from '../services/imageStore'
import { setLastResult } from '../services/storage'
import { scoreMeta } from '../utils/analytics'
import { prepareImage } from '../utils/image'

const capabilities = [
  ['/images/feature-icons/score.png', '健康评分'],
  ['/images/feature-icons/risk.png', '风险识别'],
  ['/images/feature-icons/family.png', '人群预警'],
  ['/images/feature-icons/avoid.png', '忌口命中'],
  ['/images/feature-icons/benefit.png', '有益成分'],
  ['/images/feature-icons/ai-chat.png', 'AI 建议'],
]

export function ScanPage() {
  const { activeMember, profile, memberHistory, addRecord, notify } = useApp()
  const [analyzing, setAnalyzing] = useState(false)
  const inputRef = useRef(null)
  const navigate = useNavigate()
  const recent = memberHistory.find(record => record.type !== 'pk')

  async function handleFile(event) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file || analyzing) return
    setAnalyzing(true)
    try {
      const prepared = await prepareImage(file)
      const data = await analyzeImage(prepared.base64, { userType: activeMember?.userType || profile?.userType, userId: profile?.userId, avoidIds: activeMember?.selectedAvoids || profile?.selectedAvoids || [] })
      const imageKey = await saveImage(prepared.blob).catch(() => '')
      const result = { ...data, imageKey }
      setLastResult(result)
      addRecord({ foodName: data.food_category || '未命名食品', food_category: data.food_category || '', score: data.health_score || 0, tags: (data.risk_additives || []).slice(0, 3).map(item => item.name), createTime: new Date().toISOString(), imageKey, fullResult: result })
      navigate('/result')
    } catch (error) {
      notify(error.message || '分析失败，请稍后重试。', 'danger')
    } finally {
      setAnalyzing(false)
    }
  }

  function openRecent() {
    if (!recent) return
    setLastResult({ ...(recent.fullResult || {}), food_category: recent.food_category || recent.foodName, imageKey: recent.imageKey })
    navigate('/result')
  }

  return (
    <Page title="AI 食品识别中心" subtitle="上传配料表图片，识别风险与建议" className="scan-page">
      <input ref={inputRef} className="visually-hidden" type="file" accept="image/*" onChange={handleFile} />
      <div className="scan-hero">
        <div className="scan-visual" aria-hidden="true">
          <div className="label-paper">
            <span className="label-line label-head" />
            <span className="label-line long" />
            <span className="label-line" />
            <span className="label-line short" />
            <span className="scan-frame">
              <span className="scan-line" />
              <i className="scan-corner lt" />
              <i className="scan-corner rt" />
              <i className="scan-corner lb" />
              <i className="scan-corner rb" />
            </span>
          </div>
          <em>AI</em>
          <small>配料表</small>
        </div>
        <div className="scan-hero-copy">
          <h2>上传配料表图片</h2>
          <p>从相册选择包装背面或配料表截图</p>
          <button className="button primary scan-button" type="button" onClick={() => inputRef.current?.click()} disabled={analyzing}>{analyzing ? '分析中' : '选择图片'}</button>
        </div>
      </div>
      <div className="scan-info-grid">
        <Section><Card className="scan-advice"><h2>上传建议</h2><div className="upload-tips"><span>配料表文字尽量清晰</span><span>避免反光和大角度倾斜</span><span>上传包装背面的完整配料区域</span></div></Card></Section>
        <Section><Card className="scan-support"><h2>支持识别</h2><div className="tag-row"><span className="tag success">配料表</span><span className="tag success">食品标签</span><span className="tag success">添加剂名称</span></div></Card></Section>
      </div>
      <Section title="AI 分析能力"><div className="capability-grid">{capabilities.map(([image, label]) => <Card key={label} className="capability"><img className="feature-entry-image" src={image} alt="" /><strong>{label}</strong></Card>)}</div></Section>
      <div className="scan-bottom-grid">
        <Section><Card as="button" className="pk-banner" type="button" onClick={() => navigate('/compare')}><span><small>配料表 PK</small><strong>对比两款食品</strong><p>比较评分与风险成分，帮你选更适合的一款。</p></span><b>开始 PK</b></Card></Section>
        <Section title="最近识别" action={<button className="section-action" type="button" onClick={() => navigate('/history')}>查看全部</button>}>{recent ? <Card as="button" className="recent-record" type="button" onClick={openRecent}><StoredImage imageKey={recent.imageKey} className="record-thumb" alt={recent.foodName || '食品图片'} /><span className="list-main"><strong className="list-title">{recent.foodName || '未命名食品'}</strong><small className="list-description">{recent.food_category || '食品'} · 最近识别</small></span><span className={`record-score ${scoreMeta(Number(recent.score)).className}`}>{recent.score || 0}<small>分</small></span></Card> : <Card className="scan-empty">上传配料表图片后，会在这里显示最近一次结果。</Card>}</Section>
      </div>
      {analyzing && <LoadingOverlay />}
    </Page>
  )
}

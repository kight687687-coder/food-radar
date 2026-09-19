import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { OriginalIcon } from '../components/OriginalIcon'
import { Card, Page, Section } from '../components/Page'
import { EmptyState } from '../components/States'
import { additives } from '../data/additives'
import { queryWiki } from '../services/api'
import { getWikiCache, setWikiCache } from '../services/storage'

const categories = ['全部', ...new Set(additives.map(item => item.category))]

export function WikiPage() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const [query, setQuery] = useState(params.get('keyword') || '')
  const [category, setCategory] = useState('全部')
  const filtered = useMemo(() => additives.filter(item => {
    if (category !== '全部' && item.category !== category) return false
    const value = query.trim().toLowerCase()
    return !value || item.name.toLowerCase().includes(value) || String(item.id || '').toLowerCase().includes(value) || (item.alias || []).some(alias => alias.toLowerCase().includes(value))
  }), [category, query])
  const highRisk = additives.filter(item => Number(item.risk_level) === 3).length

  return <Page title="添加剂百科" subtitle="查名称、E 编号和常见别名，快速判断使用场景与风险等级" back className="wiki-page">
    <Card className="wiki-search-card"><label className="wiki-native-search"><OriginalIcon name="search" /><input value={query} onChange={event => setQuery(event.target.value)} placeholder="搜索添加剂名称、E 编号或别名" />{query && <button type="button" onClick={() => setQuery('')} aria-label="清除"><OriginalIcon name="shield-warning" /></button>}</label><div className="wiki-quick-stats"><span><strong>{additives.length}</strong><small>已收录</small></span><i /><span><strong className="danger">{highRisk}</strong><small>高风险</small></span></div></Card>
    <div className="category-scroll" role="tablist">{categories.map(item => <button type="button" key={item} className={category === item ? 'active' : ''} onClick={() => setCategory(item)}>{item}</button>)}</div>
    <div className="wiki-result-line"><strong>{category}</strong><span>{filtered.length} 条结果</span></div>
    {!filtered.length ? <Card><EmptyState title="没有找到匹配条目" description="换一个名称、E 编号或食品配料里的常见叫法再试试。" /></Card> : <div className="wiki-native-list">{filtered.map((item, index) => { const tone = Number(item.risk_level) >= 3 ? 'danger' : Number(item.risk_level) === 2 ? 'warning' : 'success'; return <button type="button" className="wiki-native-card" key={`${item.id || 'no-id'}-${item.name}-${index}`} onClick={() => navigate(`/wiki/${encodeURIComponent(item.name)}`)}><span><span className="wiki-native-title"><strong>{item.name}</strong><b className={`tag ${tone}`}>{Number(item.risk_level) >= 3 ? '高风险' : Number(item.risk_level) === 2 ? '中风险' : '低风险'}</b></span><small>{item.id || '未编号'} · {item.category || '未分类'}</small>{item.usage && <p>{item.usage}</p>}{item.alias?.length > 0 && <em>别名：{item.alias.filter(alias => alias !== item.name).slice(0, 2).join(' / ')}</em>}</span><OriginalIcon name="arrow-right" /></button> })}</div>}
  </Page>
}

export function WikiDetailPage() {
  const { name } = useWikiName()
  const navigate = useNavigate()
  const local = additives.find(item => item.name === name || (item.alias || []).includes(name))
  const [remote, setRemote] = useState(null)
  const [loading, setLoading] = useState(!local)
  const [error, setError] = useState('')
  const additive = local || remote
  useEffect(() => {
    if (local || !name) return undefined
    let active = true
    const cached = getWikiCache(name)
    if (cached?.value) { queueMicrotask(() => { if (active) { setRemote(cached.value); setLoading(false) } }); return () => { active = false } }
    queryWiki(name).then(result => { if (active) { setRemote(result); setWikiCache(name, result); setLoading(false) } }).catch(requestError => { if (active) { setError(requestError.message); setRemote({ name, category: '未分类', risk_level: 0, warning: '该添加剂暂未收录，请结合配料表上下文和可靠来源判断。', usage: '暂无详细数据', common_in: '暂无数据', adi: '暂无数据', special_groups: [] }); setLoading(false) } })
    return () => { active = false }
  }, [local, name])
  if (loading) return <Page title="添加剂百科" back><div className="state-block"><span className="spinner" /><h3>正在查询添加剂资料</h3><p>如果本地百科没有命中，会尝试用 AI 补全基础信息</p></div></Page>
  if (!additive) return <Page title="添加剂百科" back><Card><EmptyState title="缺少成分名称" action={<button className="button primary" onClick={() => navigate('/wiki')}>返回百科</button>} /></Card></Page>
  const tone = Number(additive.risk_level) >= 3 ? 'danger' : Number(additive.risk_level) === 2 ? 'warning' : Number(additive.risk_level) === 1 ? 'success' : 'neutral'
  const riskWidth = tone === 'danger' ? 100 : tone === 'warning' ? 66 : tone === 'success' ? 33 : 10
  return <Page back className="wiki-detail-page"><section className={`wiki-detail-native tone-${tone}`}><div><h1>{additive.name || name}</h1>{additive.id && <small>{additive.id}</small>}</div><span className={`tag ${tone}`}>{additive.risk_desc || (tone === 'danger' ? '高风险' : tone === 'warning' ? '中风险' : tone === 'success' ? '低风险' : '待确认')}</span><footer><span className="tag">{additive.category || '未分类'}</span>{!local && <span className="tag ai">AI 补全</span>}</footer></section>{error && <div className="wiki-notice">{error}</div>}
    <Section title="安全概览"><Card className="wiki-story-card"><Story label="来源与合成" value={additive.origin} /><Story label="作用机制" value={additive.mechanism || additive.usage} /><Story label="安全争议" value={additive.controversy} /><Story label="摄入参考" value={additive.intake_status || additive.adi} /></Card></Section>
    <Section title="基础信息"><Card className="wiki-info-native"><InfoRow label="常见食品" value={additive.common_in || '暂无数据'} /><InfoRow label="主要用途" value={additive.usage || '暂无数据'} /><InfoRow label="ADI 值" value={additive.adi || '暂无数据'} /></Card></Section>
    <Section title="风险判断"><Card className="wiki-risk-native"><div className="risk-track"><i className={tone} style={{ width: `${riskWidth}%` }} /></div><div className="risk-labels"><span>低</span><span>中</span><span>高</span></div><strong>{additive.risk_desc || additive.warning || '暂无风险说明'}</strong>{additive.warning && <p>{additive.warning}</p>}</Card></Section>
    <Section title="重点人群"><Card className="card-pad muted-copy">{additive.special_groups?.length ? additive.special_groups.join('、') : '暂无特殊人群提示。仍建议关注摄入频率。'}</Card></Section>
    <button className="button secondary full wiki-back-list" type="button" onClick={() => navigate('/wiki')}>返回列表</button>
  </Page>
}

function Story({ label, value }) { return value ? <div><strong>{label}</strong><p>{value}</p></div> : null }
function InfoRow({ label, value }) { return <div><span>{label}</span><strong>{value}</strong></div> }
function useWikiName() { const path = window.location.pathname.split('/').pop(); return { name: decodeURIComponent(path || '') } }

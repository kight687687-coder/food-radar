import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { OriginalIcon } from '../components/OriginalIcon'
import { Card, Page } from '../components/Page'
import { EmptyState } from '../components/States'
import { StoredImage } from '../components/StoredImage'
import { useApp } from '../context/AppContext'
import { setLastResult } from '../services/storage'
import { averageScore, formatDateTime, scoreMeta } from '../utils/analytics'

const filters = [{ key: 'all', label: '全部' }, { key: 'attention', label: '需关注' }, { key: 'pk', label: 'PK 对比' }]

export function HistoryPage() {
  const { memberHistory, renameRecord } = useApp()
  const [filter, setFilter] = useState('all')
  const [query, setQuery] = useState('')
  const [editing, setEditing] = useState(null)
  const navigate = useNavigate()
  const records = useMemo(() => memberHistory.filter(record => {
    if (filter === 'attention' && (record.type === 'pk' || Number(record.score) >= 60)) return false
    if (filter === 'pk' && record.type !== 'pk') return false
    const text = `${record.foodName || ''} ${record.food_category || ''}`.toLowerCase()
    return text.includes(query.trim().toLowerCase())
  }), [filter, memberHistory, query])
  const nonPk = memberHistory.filter(record => record.type !== 'pk')
  const groups = groupByDate(records)

  function openRecord(record) {
    if (record.type === 'pk') {
      navigate(`/compare?recordId=${encodeURIComponent(record.recordId)}`)
      return
    }
    setLastResult({ ...(record.fullResult || {}), food_category: record.food_category || record.foodName, imageKey: record.imageKey })
    navigate('/result')
  }

  function commitRename(record) {
    const value = editing?.value?.trim()
    if (value) renameRecord(record.recordId, value)
    setEditing(null)
  }

  return (
    <Page title="扫描历史" subtitle="完整记录与回看" back className="history-page">
      <Card className="history-native-stats"><h2>累计记录</h2><div><span><strong>{memberHistory.length}</strong><small>累计分析</small></span><span><strong>{nonPk.filter(record => Number(record.score) < 60).length}</strong><small>高风险</small></span><span><strong>{averageScore(nonPk)}</strong><small>平均分</small></span></div></Card>
      <div className="history-tools">
        <label className="search-field"><OriginalIcon name="search" /><input value={query} onChange={event => setQuery(event.target.value)} placeholder="搜索食品名称" /></label>
        <div className="segmented" role="group" aria-label="历史筛选">{filters.map(item => <button key={item.key} className={filter === item.key ? 'active' : ''} type="button" onClick={() => setFilter(item.key)}>{item.label}</button>)}</div>
      </div>
      {!records.length ? <Card><EmptyState title={memberHistory.length ? '没有匹配记录' : '还没有扫描记录'} description={memberHistory.length ? '更换关键词或筛选条件后再试。' : '识别配料表后，结果会自动保存在这里。'} action={!memberHistory.length && <button className="button primary" onClick={() => navigate('/scan')}>去识别</button>} /></Card> : groups.map(group => (
        <section className="history-group" key={group.key}>
          <h2>{group.label}<small>{group.records.length} 条</small></h2>
          <Card className="list history-list">
            {group.records.map(record => {
              const meta = scoreMeta(Number(record.score))
              return (
                <div className="history-row list-row" key={record.recordId || record.createTime}>
                  <button className="history-open" type="button" onClick={() => openRecord(record)} aria-label={`查看 ${record.foodName || '记录'}`}>
                    {record.type === 'pk' ? <span className="record-thumb pk-thumb">PK</span> : <StoredImage imageKey={record.imageKey} className="record-thumb" alt="" />}
                  </button>
                  <div className="list-main">
                    {editing?.id === record.recordId ? <input className="rename-input" autoFocus value={editing.value} onChange={event => setEditing({ ...editing, value: event.target.value })} onBlur={() => commitRename(record)} onKeyDown={event => { if (event.key === 'Enter') commitRename(record); if (event.key === 'Escape') setEditing(null) }} /> : <button className="history-name-button" type="button" onClick={() => record.type === 'pk' ? openRecord(record) : setEditing({ id: record.recordId, value: record.foodName || '' })}>{record.foodName || '未命名食品'}</button>}
                    <p className="list-description">{record.type === 'pk' ? '食品对比' : record.food_category || '食品'} · {formatDateTime(record.createTime)}</p>
                    <div className="tag-row">{(record.tags || []).slice(0, 3).map(tag => <span className="tag warning" key={tag}>{tag}</span>)}</div>
                  </div>
                  <span className={`record-score ${meta.className}`}>{record.score || 0}<small>分</small></span>
                </div>
              )
            })}
          </Card>
        </section>
      ))}
    </Page>
  )
}

function groupByDate(records) {
  const today = new Date().toDateString()
  const yesterdayDate = new Date(); yesterdayDate.setDate(yesterdayDate.getDate() - 1)
  const yesterday = yesterdayDate.toDateString()
  const map = new Map()
  records.forEach(record => {
    const date = new Date(record.createTime)
    const key = date.toDateString()
    const label = key === today ? '今天' : key === yesterday ? '昨天' : `${date.getMonth() + 1} 月 ${date.getDate()} 日`
    if (!map.has(key)) map.set(key, { key, label, records: [] })
    map.get(key).records.push(record)
  })
  return [...map.values()]
}

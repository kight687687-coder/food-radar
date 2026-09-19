import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { OriginalIcon } from '../components/OriginalIcon'
import { Card, Page, Section } from '../components/Page'

const tools = [
  { title: '添加剂百科', image: '/images/feature-icons/wiki.png', path: '/wiki' }, { title: '配料表 PK', image: '/images/feature-icons/compare.png', path: '/compare' },
  { title: 'AI 营养师', image: '/images/feature-icons/ai-chat.png', path: '/ai-chat' }, { title: '健康档案', image: '/images/feature-icons/health-report.png', path: '/report' },
  { title: '成分解读', image: '/images/feature-icons/ingredient.png', path: '/ingredient' }, { title: '忌口设置', image: '/images/feature-icons/avoid.png', path: '/avoid' },
  { title: '报告卡', image: '/images/feature-icons/card-report.png', path: '/card-report' }, { title: '历史记录', image: '/images/feature-icons/history.png', path: '/history' },
]
const roadmap = [['食品标准查询', '对照国家标准理解食品标签'], ['儿童饮食分析', '识别儿童慎食成分'], ['孕妇饮食助手', '关注咖啡因、防腐剂等风险']]

export function ToolboxPage() {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  function search(event) { event.preventDefault(); const value = query.trim(); navigate(value ? `/wiki?keyword=${encodeURIComponent(value)}` : '/wiki') }
  return (
    <Page title="探索" subtitle="搜索食品知识、添加剂、标准" className="toolbox-page">
      <form className="explore-search" onSubmit={search}><input value={query} onChange={event => setQuery(event.target.value)} placeholder="搜索添加剂、风险成分、食品标准" aria-label="搜索食品知识" /><button type="submit" aria-label="搜索"><OriginalIcon name="search" /></button></form>
      <Section><Card as="button" type="button" className="wiki-feature" onClick={() => navigate('/wiki')}><span><small>今日推荐</small><strong>添加剂百科</strong><p>看懂配料表里的陌生成分，查风险等级、人群提醒与食用建议。</p><b>立即查询</b></span><img className="feature-entry-image" src="/images/feature-icons/wiki.png" alt="" /></Card></Section>
      <Section title="常用服务"><div className="tool-grid">{tools.map(item => <button type="button" className="tool-card" key={item.path} onClick={() => navigate(item.path)}><img className="feature-entry-image" src={item.image} alt="" /><strong>{item.title}</strong></button>)}</div></Section>
      <Section title="AI 智能服务"><Card as="button" type="button" className="ai-tool" onClick={() => navigate('/ai-chat')}><img className="feature-entry-image" src="/images/feature-icons/ai-chat.png" alt="" /><span><small>新功能</small><strong>AI 营养师</strong><p>咨询添加剂、配料表与食品风险问题。</p></span><b>提问</b></Card></Section>
      <Section title="即将上线"><Card className="roadmap-card">{roadmap.map(([title, desc]) => <div className="roadmap-item" key={title}><span><strong>{title}</strong><small>{desc}</small></span><b>规划中</b></div>)}</Card></Section>
    </Page>
  )
}

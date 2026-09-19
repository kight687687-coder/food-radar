import { useRef, useState } from 'react'
import { Avatar } from '../components/Avatar'
import { Page } from '../components/Page'
import { useApp } from '../context/AppContext'
import { askNutritionist } from '../services/api'

const examples = ['山梨酸钾安全吗？', '儿童能喝含阿斯巴甜的饮料吗？', '配料表里哪些添加剂需要少吃？']

export function ChatPage() {
  const { activeMember, profile } = useApp()
  const [question, setQuestion] = useState('')
  const [loading, setLoading] = useState(false)
  const [messages, setMessages] = useState([{ role: 'assistant', text: '你好，我是 AI 营养师。你可以问我配料表、食品添加剂、控糖减脂、儿童或孕妇饮食风险相关的问题。' }])
  const endRef = useRef(null)
  async function send(event) {
    event?.preventDefault()
    const text = question.trim()
    if (!text || loading) return
    const history = messages.slice(-8).map(item => ({ role: item.role, content: item.text }))
    setMessages(current => [...current, { role: 'user', text }]); setQuestion(''); setLoading(true)
    try { const result = await askNutritionist(text, history, activeMember?.userType || profile?.userType || '普通人群', profile?.userId); setMessages(current => [...current, { role: 'assistant', text: cleanAnswer(result.answer || '暂时没有生成有效回答，请换个问法再试。') }]) } catch (error) { setMessages(current => [...current, { role: 'assistant', text: `${error.message} 你也可以先查查添加剂百科。` }]) } finally { setLoading(false); requestAnimationFrame(() => endRef.current?.scrollIntoView({ behavior: 'smooth' })) }
  }
  return <Page title="AI 营养师" subtitle="围绕配料表、添加剂和饮食风险提问，获得更具体的解释和建议" back className="chat-page"><section className="chat-native-scope"><span>AI</span><div><strong>食品安全问答</strong><p>适合咨询添加剂安全性、特殊人群注意事项、配料表风险和饮食选择。</p></div></section><div className="chat-native-examples">{examples.map(item => <button type="button" className="tag ai" key={item} onClick={() => setQuestion(item)}>{item}</button>)}</div><div className="chat-native-messages">{messages.map((message,index) => <div className={`message-row ${message.role}`} key={`${message.role}-${index}`}>{message.role === 'assistant' ? <span className="chat-native-avatar"><img src="/images/ai-nutritionist-avatar.png" alt="" /></span> : null}<div className="message-bubble">{message.text}</div>{message.role === 'user' ? <Avatar src={activeMember?.avatar} name={activeMember?.nickname || '我'} className="chat-native-avatar" /> : null}</div>)}{loading && <div className="message-row assistant"><span className="chat-native-avatar"><img src="/images/ai-nutritionist-avatar.png" alt="" /></span><div className="message-bubble typing">正在思考…</div></div>}<div ref={endRef} /></div><form className="chat-native-input" onSubmit={send}><input value={question} onChange={event => setQuestion(event.target.value)} placeholder="输入食品安全问题" /><button type="submit" disabled={!question.trim() || loading}>发送</button></form></Page>
}

function cleanAnswer(text) { return String(text || '').replace(/\*\*/g, '').replace(/#{1,6}\s*/g, '').replace(/```[\s\S]*?```/g, '').replace(/\n{3,}/g, '\n\n').trim() }

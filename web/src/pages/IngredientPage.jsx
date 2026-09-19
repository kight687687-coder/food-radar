import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, Page } from '../components/Page'

const examples = ['山梨酸钾', '阿斯巴甜', '柠檬黄', '黄原胶']

export function IngredientPage() {
  const navigate = useNavigate()
  const [keyword, setKeyword] = useState('')
  function submit(event) { event.preventDefault(); const value = keyword.trim(); if (value) navigate(`/wiki?keyword=${encodeURIComponent(value)}`) }
  return <Page title="成分解读" subtitle="输入配料表里的添加剂名称，跳转到百科库查看用途、常见食品和风险说明" back className="ingredient-page"><form className="ingredient-native-search" onSubmit={submit}><input autoFocus value={keyword} onChange={event => setKeyword(event.target.value)} placeholder="例如：山梨酸钾、阿斯巴甜" /><button className="button primary full" type="submit">查询成分</button></form><section className="ingredient-examples"><h2>常查成分</h2><div>{examples.map(item => <button type="button" className="tag" key={item} onClick={() => setKeyword(item)}>{item}</button>)}</div></section><Card as="button" type="button" className="ingredient-native-tip" onClick={() => navigate('/wiki')}><strong>进入完整添加剂百科</strong><small>按分类浏览防腐剂、甜味剂、色素、乳化剂等常见条目</small></Card></Page>
}

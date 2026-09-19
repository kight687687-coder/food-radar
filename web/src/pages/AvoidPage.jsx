import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Page } from '../components/Page'
import { useApp } from '../context/AppContext'
import { AVOID_GROUPS } from '../data/constants'

const descriptions = { allergy: '明确过敏源建议优先选择', intolerance: '适合乳糖、咖啡因等敏感体质', preference: '用于控制摄入或保持更清淡的配料选择' }

export function AvoidPage() {
  const { activeMember, editMember, profile, saveUserProfile, notify } = useApp()
  const navigate = useNavigate()
  const [value, setValue] = useState(activeMember?.selectedAvoids || profile?.selectedAvoids || [])
  function toggle(id) { setValue(current => current.includes(id) ? current.filter(item => item !== id) : [...current, id]) }
  function save() { if (activeMember) editMember(activeMember.memberId, { selectedAvoids: value }); else saveUserProfile({ ...(profile || {}), selectedAvoids: value }); notify('忌口设置已保存', 'success'); navigate(-1) }
  return <Page title="忌口设置" subtitle="选择需要避免的成分，扫描配料表时会自动突出提示" back className="avoid-page">{AVOID_GROUPS.map(group => <section className="avoid-native-group" key={group.key}><h2>{group.name}</h2><p>{descriptions[group.key]}</p><div>{group.items.map(([id,name]) => <button type="button" className={`${group.tone} ${value.includes(id) ? 'selected' : ''}`} key={id} onClick={() => toggle(id)} aria-pressed={value.includes(id)}>{name}</button>)}</div></section>)}<button className="button primary full avoid-save" type="button" onClick={save}>保存设置</button></Page>
}

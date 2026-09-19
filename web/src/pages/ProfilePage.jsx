import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AvoidSelector } from '../components/AvoidSelector'
import { OriginalIcon } from '../components/OriginalIcon'
import { Card, Page, Section } from '../components/Page'
import { useApp } from '../context/AppContext'
import { GENDERS, USER_TYPES } from '../data/constants'

const blankProfile = { nickname: '', gender: '', age: '', height: '', weight: '', userType: '普通人群', selectedAvoids: [] }

export function ProfilePage() {
  const { profile, saveUserProfile, notify } = useApp()
  const navigate = useNavigate()
  const initial = useMemo(() => ({ ...blankProfile, ...(profile || {}) }), [profile])
  const [form, setForm] = useState(initial)
  const [errors, setErrors] = useState({})
  const [avoidExpanded, setAvoidExpanded] = useState(false)
  const editing = Boolean(profile?.userId)

  function update(field, value) { setForm(current => ({ ...current, [field]: value })); if (errors[field]) setErrors(current => ({ ...current, [field]: '' })) }
  function save(event) {
    event.preventDefault()
    if (!form.nickname.trim()) { setErrors({ nickname: '请输入昵称' }); return }
    saveUserProfile({ ...profile, ...form, nickname: form.nickname.trim(), userId: profile?.userId || Date.now() })
    notify(editing ? '健康档案已更新' : '健康档案已保存', 'success')
    navigate('/', { replace: true })
  }
  function skip() { saveUserProfile({ userId: Date.now(), nickname: '我自己', userType: '普通人群', selectedAvoids: [] }); navigate('/', { replace: true }) }

  return (
    <Page title="健康档案" subtitle="填写基础信息后，识别结果会按你的身体状态、饮食目标和忌口偏好给出提醒" className="profile-page">
      <form onSubmit={save}>
        <Section title="基础信息"><Card className="native-form-card">
          <label className="native-form-row"><span>昵称</span><input value={form.nickname} onChange={event => update('nickname', event.target.value)} placeholder="输入昵称" maxLength={12} autoComplete="nickname" /></label>
          {errors.nickname && <span className="native-form-error">{errors.nickname}</span>}
          <label className="native-form-row"><span>性别</span><span className="native-select-wrap"><select value={form.gender} onChange={event => update('gender', event.target.value)}><option value="">请选择</option>{GENDERS.map(item => <option key={item}>{item}</option>)}</select><OriginalIcon name="arrow-right" /></span></label>
          <div className="native-metric-row"><label><span>年龄</span><input type="number" min="0" max="120" value={form.age} onChange={event => update('age', event.target.value)} placeholder="岁" /></label><label><span>身高</span><input type="number" min="40" max="250" value={form.height} onChange={event => update('height', event.target.value)} placeholder="cm" /></label><label><span>体重</span><input type="number" min="2" max="400" step="0.1" value={form.weight} onChange={event => update('weight', event.target.value)} placeholder="kg" /></label></div>
        </Card></Section>

        <Section title="分析偏好"><Card className="native-form-card">
          <label className="native-form-row"><span>人群类型</span><span className="native-select-wrap"><select value={form.userType} onChange={event => update('userType', event.target.value)}>{USER_TYPES.map(item => <option key={item}>{item}</option>)}</select><OriginalIcon name="arrow-right" /></span></label>
          <button className="native-form-row avoid-trigger-row" type="button" onClick={() => setAvoidExpanded(value => !value)}><span><strong>忌口设置</strong><small>扫描结果中会优先提示这些风险</small></span><span className="native-select-wrap"><em>{form.selectedAvoids.length ? `已选 ${form.selectedAvoids.length} 项` : '未设置'}</em><OriginalIcon name="arrow-right" className={avoidExpanded ? 'open' : ''} /></span></button>
          {avoidExpanded && <div className="native-avoid-panel"><AvoidSelector value={form.selectedAvoids} onChange={value => update('selectedAvoids', value)} /></div>}
        </Card></Section>

        <div className="profile-actions"><button className="button primary full" type="submit">{editing ? '保存修改' : '完成档案'}</button>{!editing && <button className="profile-skip" type="button" onClick={skip}>暂时跳过</button>}</div>
      </form>
    </Page>
  )
}

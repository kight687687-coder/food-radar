import { useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { AvoidSelector } from '../components/AvoidSelector'
import { Avatar } from '../components/Avatar'
import { OriginalIcon } from '../components/OriginalIcon'
import { Card, Page, Section } from '../components/Page'
import { useApp } from '../context/AppContext'
import { GENDERS, RELATIONSHIPS, USER_TYPES } from '../data/constants'
import { makeAvatarDataUrl } from '../utils/image'

export function FamilyPage() {
  const { members, activeMemberId, selectMember, removeMember, confirm, notify } = useApp()
  const navigate = useNavigate()
  async function deleteMember(member) {
    const yes = await confirm({ title: '确认删除', message: `确定要移除「${member.nickname || member.relationship || '该成员'}」吗？该成员的扫描记录将不再显示。`, confirmLabel: '移除成员', danger: true })
    if (!yes) return
    const result = removeMember(member.memberId)
    notify(result.ok ? '成员已移除' : result.message, result.ok ? 'success' : 'danger')
  }
  return <Page title="家庭成员" subtitle="切换当前成员后，识别、历史和健康报告会按该成员展示" back className="family-page">
    <section className="family-native-summary"><span><strong>{members.length}</strong><small>已添加成员</small></span><b>最多 6 位</b></section>
    <div className="family-list">{members.map(member => <Card className={`family-card ${member.memberId === activeMemberId ? 'active' : ''}`} key={member.memberId}><button type="button" className="family-native-select" onClick={() => { selectMember(member.memberId); notify('已切换当前成员', 'success') }}><Avatar src={member.avatar} name={member.nickname || member.relationship || '成'} /><span><span><strong>{member.nickname || member.relationship || '未命名成员'}</strong>{member.memberId === activeMemberId && <b>当前</b>}</span><small>{member.relationship || '家庭成员'} · {member.userType || '普通人群'}</small><em>{member.selectedAvoids?.length ? `已设置 ${member.selectedAvoids.length} 项忌口` : '未设置忌口'}</em></span></button><div className="family-native-actions"><button type="button" onClick={() => navigate(`/family/edit/${member.memberId}`)} aria-label="编辑"><OriginalIcon name="arrow-right" /></button>{members.length > 1 && <button type="button" onClick={() => deleteMember(member)} aria-label="移除"><OriginalIcon name="shield-warning" /></button>}</div></Card>)}</div>
    {members.length < 6 ? <button className="family-add-card" type="button" onClick={() => navigate('/family/new')}><span><OriginalIcon name="user-group" /></span><span><strong>添加家庭成员</strong><small>为孩子、老人或控糖人群建立独立档案</small></span></button> : <p className="family-limit">成员数量已达上限</p>}
  </Page>
}

export function FamilyEditPage({ isNew = false }) {
  const { members, activeMember, createMember, editMember, removeMember, confirm, notify } = useApp()
  const navigate = useNavigate()
  const { memberId: id } = useParams()
  const member = (!isNew && members.find(item => item.memberId === id)) || activeMember || {}
  const [form, setForm] = useState({ nickname: member.nickname || '', gender: member.gender || '', relationship: member.relationship || '', age: member.age || '', height: member.height || '', weight: member.weight || '', userType: member.userType || '普通人群', selectedAvoids: member.selectedAvoids || [], avatar: member.avatar || '' })
  const [avoidExpanded, setAvoidExpanded] = useState(false)
  const avatarInput = useRef(null)
  function update(field, value) { setForm(current => ({ ...current, [field]: value })) }
  async function changeAvatar(event) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    try { update('avatar', await makeAvatarDataUrl(file)) } catch (error) { notify(error.message, 'danger') }
  }
  function save(event) {
    event.preventDefault()
    if (!form.nickname.trim()) { notify('请输入昵称', 'danger'); return }
    const result = isNew ? createMember({ ...form, nickname: form.nickname.trim() }) : editMember(member.memberId, { ...form, nickname: form.nickname.trim() })
    if (isNew && !result.ok) { notify(result.message, 'danger'); return }
    notify(isNew ? '成员已添加' : '成员资料已更新', 'success'); navigate('/family')
  }
  async function deleteCurrent() {
    if (isNew) return
    const yes = await confirm({ title: '确认删除', message: `确定要移除「${member.nickname || '该成员'}」吗？`, confirmLabel: '移除成员', danger: true })
    if (yes) { const result = removeMember(member.memberId); notify(result.ok ? '成员已移除' : result.message, result.ok ? 'success' : 'danger'); if (result.ok) navigate('/family') }
  }
  return <Page title={isNew ? '添加成员' : '编辑成员'} subtitle="为不同家人保存人群类型和忌口信息，识别食品时自动给出更贴近个人的提醒" back className="member-edit-page"><form onSubmit={save}>
    <input ref={avatarInput} className="visually-hidden" type="file" accept="image/*" onChange={changeAvatar} />
    <Card className="member-profile-card"><button className="member-avatar-button" type="button" onClick={() => avatarInput.current?.click()}><Avatar src={form.avatar} name={form.nickname || '成'} /></button><span><strong>{form.nickname || '未命名成员'}</strong><small>从相册选择头像，可留空</small></span></Card>
    <Section title="基本信息"><Card className="native-form-card">
      <label className="native-form-row"><span>昵称</span><input value={form.nickname} onChange={event => update('nickname', event.target.value)} placeholder="输入昵称" maxLength={10} /></label>
      <label className="native-form-row"><span>性别</span><span className="native-select-wrap"><select value={form.gender} onChange={event => update('gender', event.target.value)}><option value="">请选择</option>{GENDERS.map(item => <option key={item}>{item}</option>)}</select><OriginalIcon name="arrow-right" /></span></label>
      <label className="native-form-row"><span>关系</span><span className="native-select-wrap"><select value={form.relationship} onChange={event => update('relationship', event.target.value)}><option value="">请选择</option>{RELATIONSHIPS.map(item => <option key={item}>{item}</option>)}</select><OriginalIcon name="arrow-right" /></span></label>
      <div className="native-metric-row"><label><span>年龄</span><input type="number" value={form.age} onChange={event => update('age', event.target.value)} placeholder="岁" /></label><label><span>身高</span><input type="number" value={form.height} onChange={event => update('height', event.target.value)} placeholder="cm" /></label><label><span>体重</span><input type="number" value={form.weight} onChange={event => update('weight', event.target.value)} placeholder="kg" /></label></div>
    </Card></Section>
    <Section title="健康偏好"><Card className="native-form-card">
      <label className="native-form-row"><span>人群类型</span><span className="native-select-wrap"><select value={form.userType} onChange={event => update('userType', event.target.value)}>{USER_TYPES.map(item => <option key={item}>{item}</option>)}</select><OriginalIcon name="arrow-right" /></span></label>
      <button className="native-form-row avoid-trigger-row" type="button" onClick={() => setAvoidExpanded(value => !value)}><span><strong>忌口设置</strong><small>过敏、不耐受和主动回避项</small></span><span className="native-select-wrap"><em>{form.selectedAvoids.length ? `已选 ${form.selectedAvoids.length} 项` : '未设置'}</em><OriginalIcon name="arrow-right" className={avoidExpanded ? 'open' : ''} /></span></button>
      {avoidExpanded && <div className="native-avoid-panel"><AvoidSelector value={form.selectedAvoids} onChange={value => update('selectedAvoids', value)} /></div>}
    </Card></Section>
    <div className="member-edit-actions"><button className="button primary full" type="submit">{isNew ? '添加成员' : '保存修改'}</button>{!isNew && <button className="member-delete-button" type="button" onClick={deleteCurrent}>删除成员</button>}</div>
  </form></Page>
}

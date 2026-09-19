import { useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Avatar } from '../components/Avatar'
import { OriginalIcon } from '../components/OriginalIcon'
import { Card, Page, Section } from '../components/Page'
import { useApp } from '../context/AppContext'
import { makeAvatarDataUrl } from '../utils/image'

const avoidNames = { peanut: '花生过敏', lactose: '乳糖不耐受', caffeine: '咖啡因敏感', preservative: '防腐剂' }

export function MinePage() {
  const { activeMember, members, memberHistory, editMember, selectMember, clearRecords, confirm, notify } = useApp()
  const navigate = useNavigate()
  const avatarInput = useRef(null)
  const history = memberHistory.filter(record => record.type !== 'pk')
  const avg = history.length ? Math.round(history.reduce((sum, record) => sum + Number(record.score || 0), 0) / history.length) : null
  const bmi = activeMember?.height && activeMember?.weight ? Number((Number(activeMember.weight) / ((Number(activeMember.height) / 100) ** 2)).toFixed(1)) : null
  const bmiText = bmi === null ? '' : bmi < 18.5 ? '偏瘦' : bmi < 24 ? '正常' : bmi < 28 ? '偏重' : '肥胖'
  const tags = (activeMember?.selectedAvoids || []).slice(0, 3).map(id => avoidNames[id] || id)
  const aiTags = [activeMember?.userType || '普通人群', bmi ? `BMI ${bmiText}` : '身体信息待完善', history.length ? `已分析 ${history.length} 次` : '等待扫描记录']

  async function changeAvatar(event) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file || !activeMember) return
    try { const url = await makeAvatarDataUrl(file); editMember(activeMember.memberId, { avatar: url }); notify('头像已更新', 'success') } catch (error) { notify(error.message, 'danger') }
  }

  async function clearAll() {
    const yes = await confirm({ title: '清除缓存', message: '确定清除所有扫描记录吗？此操作不可恢复。', confirmLabel: '清除记录', danger: true })
    if (yes) { await clearRecords(); notify('扫描记录已清除', 'success') }
  }

  const editPath = activeMember ? `/family/edit/${activeMember.memberId}` : '/profile'

  return (
    <Page title="我的" subtitle="个人与家庭设置中心" className="mine-page">
      <input ref={avatarInput} className="visually-hidden" type="file" accept="image/*" onChange={changeAvatar} />
      <Card className="guardian-card"><div className="guardian-left"><small>当前守护对象</small><div className="guardian-person"><button type="button" onClick={() => avatarInput.current?.click()} aria-label="更换头像"><Avatar src={activeMember?.avatar} name={activeMember?.nickname || '我'} /></button><span><strong>{activeMember?.nickname || '当前成员'}</strong><em>{activeMember?.userType || '普通人群'}</em></span></div>{tags.length > 0 && <div className="tag-row">{tags.map(tag => <span className="tag warning" key={tag}>{tag}</span>)}</div>}</div><div className="health-index"><strong>{avg ?? '--'}</strong><span>健康指数</span></div></Card>

      <Section title="家庭成员" action={<button className="section-action" type="button" onClick={() => navigate('/family')}>管理</button>}><Card className="member-card"><div className="member-chips">{members.slice(0, 6).map(member => <button type="button" className={`member-chip ${member.memberId === activeMember?.memberId ? 'active' : ''}`} key={member.memberId} onClick={() => selectMember(member.memberId)}><Avatar src={member.avatar} name={member.nickname || '成'} /><span>{member.nickname || member.relationship || '成员'}</span></button>)}<button type="button" className="member-chip add" onClick={() => navigate('/family/new')}><span className="member-add-icon"><img src="/images/feature-icons/family.png" alt="" /></span><span>添加</span></button></div></Card></Section>

      <Section><Card className="body-card"><header><h2>身体指标</h2><button type="button" onClick={() => navigate(editPath)}>编辑</button></header><div className="body-group"><small>基础信息</small><strong>{activeMember?.age || '-'}岁 · {activeMember?.gender || '未设置'}</strong></div><div className="body-group"><small>体型指标</small><strong>{activeMember?.height || '-'}cm · {activeMember?.weight || '-'}kg</strong>{bmi !== null && <span className={`tag ${bmiText === '正常' ? 'success' : 'warning'}`}>BMI {bmi} {bmiText}</span>}</div></Card></Section>

      <Section><Card className="ai-profile-card"><h2>AI 健康画像</h2><div className="tag-row">{aiTags.map(tag => <span className="tag ai" key={tag}>{tag}</span>)}</div><p>根据当前人群类型、忌口与扫描记录生成</p></Card></Section>

      <Section title="设置"><Card className="settings-card"><Setting label="编辑个人信息" onClick={() => navigate(editPath)} /><Setting label="人群类型" value={activeMember?.userType || '普通人群'} onClick={() => navigate(editPath)} /><Setting label="忌口设置" value={`${activeMember?.selectedAvoids?.length || 0} 项`} onClick={() => navigate('/avoid')} /><Setting label="家庭管理" onClick={() => navigate('/family')} /><Setting label="清除缓存" onClick={clearAll} /><div className="setting-row"><span>关于食安雷达</span><span>1.0</span></div></Card></Section>
    </Page>
  )
}

function Setting({ label, value, onClick }) {
  return <button className="setting-row" type="button" onClick={onClick}><span>{label}</span><span className="setting-value">{value && <em>{value}</em>}<OriginalIcon name="arrow-right" /></span></button>
}

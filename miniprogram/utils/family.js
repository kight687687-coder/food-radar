const FAMILY_KEY = 'familyMembers'
const ACTIVE_KEY = 'activeMemberId'
const HISTORY_KEY = 'scanHistory'

function generateId() {
  return 'm_' + Date.now() + '_' + Math.random().toString(36).slice(2, 7)
}

function getMembers() {
  return wx.getStorageSync(FAMILY_KEY) || []
}

function getActiveMemberId() {
  return wx.getStorageSync(ACTIVE_KEY) || ''
}

function getActiveMember() {
  const members = getMembers()
  const activeId = getActiveMemberId()
  return members.find(m => m.memberId === activeId) || members[0] || null
}

function setActiveMember(id) {
  wx.setStorageSync(ACTIVE_KEY, id)
}

function addMember(info) {
  const members = getMembers()
  if (members.length >= 6) {
    return { ok: false, msg: '最多添加6位家庭成员' }
  }
  const member = {
    memberId: generateId(),
    nickname: info.nickname || '',
    gender: info.gender || '',
    age: info.age || '',
    height: info.height || '',
    weight: info.weight || '',
    relationship: info.relationship || '',
    userType: info.userType || '普通人群',
    selectedAvoids: info.selectedAvoids || [],
    avatar: info.avatar || '',
    createTime: Date.now()
  }
  members.push(member)
  // 家庭成员资料保存在本地缓存，供首页、报告页和扫描页共享
  wx.setStorageSync(FAMILY_KEY, members)
  return { ok: true, member }
}

function updateMember(id, info) {
  const members = getMembers()
  const idx = members.findIndex(m => m.memberId === id)
  if (idx === -1) return false
  if (info.nickname !== undefined) members[idx].nickname = info.nickname
  if (info.gender !== undefined) members[idx].gender = info.gender
  if (info.age !== undefined) members[idx].age = info.age
  if (info.height !== undefined) members[idx].height = info.height
  if (info.weight !== undefined) members[idx].weight = info.weight
  if (info.relationship !== undefined) members[idx].relationship = info.relationship
  if (info.userType !== undefined) members[idx].userType = info.userType
  if (info.selectedAvoids !== undefined) members[idx].selectedAvoids = info.selectedAvoids
  if (info.avatar !== undefined) members[idx].avatar = info.avatar
  wx.setStorageSync(FAMILY_KEY, members)
  return true
}

function deleteMember(id) {
  const members = getMembers()
  if (members.length <= 1) {
    return { ok: false, msg: '至少保留一位家庭成员' }
  }
  const filtered = members.filter(m => m.memberId !== id)
  if (filtered.length === members.length) {
    return { ok: false, msg: '成员不存在' }
  }
  wx.setStorageSync(FAMILY_KEY, filtered)
  if (getActiveMemberId() === id) {
    // 删除当前成员后自动切换到剩余列表第一位
    setActiveMember(filtered[0].memberId)
  }
  return { ok: true }
}

function getFilteredHistory() {
  const history = wx.getStorageSync(HISTORY_KEY) || []
  const activeId = getActiveMemberId()
  if (!activeId) return history
  return history.filter(r => !r.memberId || r.memberId === activeId)
}

function addScanRecord(record) {
  const activeId = getActiveMemberId()
  const fullRecord = Object.assign({}, record, { memberId: activeId })
  const history = wx.getStorageSync(HISTORY_KEY) || []
  history.unshift(fullRecord)
  // 只保留最近50条记录，控制本地缓存体积
  if (history.length > 50) history.length = 50
  wx.setStorageSync(HISTORY_KEY, history)
  return fullRecord
}

function initFamily() {
  const members = getMembers()
  if (members.length > 0) {
    if (!getActiveMemberId()) {
      // 已有成员但未设置当前成员时，默认选中第一位
      setActiveMember(members[0].memberId)
    }
    return false
  }

  // 首次启用家庭功能时，以旧版用户画像创建“我自己”成员
  const profile = wx.getStorageSync('userProfile') || {}
  const memberId = generateId()
  const firstMember = {
    memberId: memberId,
    nickname: profile.nickname || '我自己',
    gender: profile.gender || '',
    age: profile.age || '',
    height: profile.height || '',
    weight: profile.weight || '',
    relationship: '我自己',
    userType: profile.userType || '普通人群',
    selectedAvoids: profile.selectedAvoids || [],
    avatar: profile.avatar || '',
    createTime: Date.now()
  }
  wx.setStorageSync(FAMILY_KEY, [firstMember])
  wx.setStorageSync(ACTIVE_KEY, memberId)

  const history = wx.getStorageSync(HISTORY_KEY) || []
  if (history.length > 0) {
    // 旧历史记录没有memberId，迁移时统一归属到默认成员
    history.forEach(function (r) {
      if (!r.memberId) r.memberId = memberId
    })
    wx.setStorageSync(HISTORY_KEY, history)
  }
  return true
}

module.exports = {
  getMembers: getMembers,
  getActiveMemberId: getActiveMemberId,
  getActiveMember: getActiveMember,
  setActiveMember: setActiveMember,
  addMember: addMember,
  updateMember: updateMember,
  deleteMember: deleteMember,
  getFilteredHistory: getFilteredHistory,
  addScanRecord: addScanRecord,
  initFamily: initFamily
}

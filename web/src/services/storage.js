import { DEFAULT_AVATAR, DEFAULT_NICKNAME, DEFAULT_RELATIONSHIP } from '../data/profileDefaults'

const KEYS = {
  profile: 'userProfile',
  members: 'familyMembers',
  activeMember: 'activeMemberId',
  history: 'scanHistory',
  lastResult: 'lastResult',
  comparePreset: 'resultForCompare',
}

export function readStorage(key, fallback = null) {
  try {
    const raw = localStorage.getItem(key)
    return raw === null ? fallback : JSON.parse(raw)
  } catch {
    return fallback
  }
}

export function writeStorage(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value))
    return true
  } catch (error) {
    console.error(`Unable to persist ${key}`, error)
    return false
  }
}

export function removeStorage(key) {
  localStorage.removeItem(key)
}

export function getProfile() {
  return readStorage(KEYS.profile, null)
}

export function saveProfile(profile) {
  writeStorage(KEYS.profile, profile)
  return profile
}

export function getMembers() {
  return readStorage(KEYS.members, [])
}

export function getActiveMemberId() {
  return readStorage(KEYS.activeMember, '')
}

export function setActiveMemberId(memberId) {
  writeStorage(KEYS.activeMember, memberId)
}

export function initializeFamily(profile = getProfile()) {
  if (profile?.userId) {
    const migratedProfile = {
      ...profile,
      nickname: profile.nickname === '我自己' ? DEFAULT_NICKNAME : (profile.nickname || DEFAULT_NICKNAME),
      avatar: profile.avatar || DEFAULT_AVATAR,
    }
    if (JSON.stringify(migratedProfile) !== JSON.stringify(profile)) writeStorage(KEYS.profile, migratedProfile)
    profile = migratedProfile
  }
  const members = getMembers()
  if (members.length) {
    const migrated = members.map(member => ({
      ...member,
      nickname: member.nickname === '我自己' ? DEFAULT_NICKNAME : (member.nickname || DEFAULT_NICKNAME),
      relationship: member.relationship === '我自己' ? DEFAULT_RELATIONSHIP : member.relationship,
      avatar: member.avatar || profile?.avatar || DEFAULT_AVATAR,
    }))
    if (JSON.stringify(migrated) !== JSON.stringify(members)) writeStorage(KEYS.members, migrated)
    if (!getActiveMemberId()) setActiveMemberId(members[0].memberId)
    return migrated
  }
  if (!profile?.userId) return []
  const memberId = createId('m')
  const member = {
    memberId,
    nickname: profile.nickname || DEFAULT_NICKNAME,
    gender: profile.gender || '',
    age: profile.age || '',
    height: profile.height || '',
    weight: profile.weight || '',
    relationship: DEFAULT_RELATIONSHIP,
    userType: profile.userType || '普通人群',
    selectedAvoids: profile.selectedAvoids || [],
    avatar: profile.avatar || DEFAULT_AVATAR,
    createTime: Date.now(),
  }
  writeStorage(KEYS.members, [member])
  setActiveMemberId(memberId)

  const history = getHistory()
  if (history.some(record => !record.memberId)) {
    writeStorage(KEYS.history, history.map(record => ({ ...record, memberId: record.memberId || memberId })))
  }
  return [member]
}

export function addMember(info) {
  const members = getMembers()
  if (members.length >= 6) return { ok: false, message: '最多添加 6 位家庭成员' }
  const member = {
    memberId: createId('m'),
    nickname: info.nickname || DEFAULT_NICKNAME,
    gender: info.gender || '',
    age: info.age || '',
    height: info.height || '',
    weight: info.weight || '',
    relationship: info.relationship || '',
    userType: info.userType || '普通人群',
    selectedAvoids: info.selectedAvoids || [],
    avatar: info.avatar || DEFAULT_AVATAR,
    createTime: Date.now(),
  }
  const next = [...members, member]
  writeStorage(KEYS.members, next)
  if (!getActiveMemberId()) setActiveMemberId(member.memberId)
  return { ok: true, member }
}

export function updateMember(memberId, patch) {
  const members = getMembers()
  const index = members.findIndex(member => member.memberId === memberId)
  if (index < 0) return false
  members[index] = { ...members[index], ...patch, memberId }
  writeStorage(KEYS.members, members)
  return true
}

export function deleteMember(memberId) {
  const members = getMembers()
  if (members.length <= 1) return { ok: false, message: '至少保留一位家庭成员' }
  const next = members.filter(member => member.memberId !== memberId)
  if (next.length === members.length) return { ok: false, message: '成员不存在' }
  writeStorage(KEYS.members, next)
  if (getActiveMemberId() === memberId) setActiveMemberId(next[0].memberId)
  return { ok: true }
}

export function getHistory() {
  return readStorage(KEYS.history, [])
}

export function addHistoryRecord(record, memberId = getActiveMemberId()) {
  const item = { ...record, memberId, recordId: record.recordId || createId('r') }
  const history = [item, ...getHistory()].slice(0, 50)
  writeStorage(KEYS.history, history)
  return item
}

export function updateHistoryRecord(recordId, patch) {
  const history = getHistory().map(record => record.recordId === recordId ? { ...record, ...patch } : record)
  writeStorage(KEYS.history, history)
  return history
}

export function clearHistory() {
  removeStorage(KEYS.history)
  removeStorage(KEYS.lastResult)
}

export function getLastResult() {
  return readStorage(KEYS.lastResult, null)
}

export function setLastResult(result) {
  writeStorage(KEYS.lastResult, result)
}

export function getComparePreset() {
  return readStorage(KEYS.comparePreset, null)
}

export function setComparePreset(result) {
  if (result) writeStorage(KEYS.comparePreset, result)
  else removeStorage(KEYS.comparePreset)
}

export function setCompareData(recordId, value) {
  writeStorage(`pkFullData_${recordId}`, value)
}

export function getCompareData(recordId) {
  return readStorage(`pkFullData_${recordId}`, null)
}

export function getWikiCache(name) {
  return readStorage(`wiki_cache_${name}`, null)
}

export function setWikiCache(name, value) {
  writeStorage(`wiki_cache_${name}`, { savedAt: Date.now(), value })
}

export function createId(prefix = 'id') {
  if (globalThis.crypto?.randomUUID) return `${prefix}_${crypto.randomUUID()}`
  return `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
}

export { KEYS }

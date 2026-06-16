
const family = require('../../utils/family')

const AVOID_NAMES = {
  peanut: '花生过敏', nuts: '坚果过敏', milk_allergy: '牛奶过敏', egg: '鸡蛋过敏',
  wheat: '小麦过敏', soy: '大豆过敏', seafood: '海鲜过敏', sesame: '芝麻过敏',
  lactose: '乳糖不耐受', fructose: '果糖不耐受', caffeine: '咖啡因敏感', alcohol: '酒精不耐受',
  msg: '味精敏感', trans_fat: '反式脂肪', artificial_color: '人工色素', artificial_sweet: '人工甜味剂',
  preservative: '防腐剂', hfcs: '高果糖浆', nitrite: '亚硝酸盐', flavor: '香精香料'
}

function shortAvatar(member) {
  const name = member.nickname || member.relationship || '家'
  return name.slice(0, 1)
}

Page({
  data: {
    member: null,
    members: [],
    avatar: '',
    avatarText: '我',
    nickname: '',
    userType: '',
    healthScore: null,
    age: '-',
    gender: '-',
    height: '-',
    weight: '-',
    bmi: null,
    bmiLevel: '',
    aiTags: [],
    selectedAvoidNames: [],
  },

  onShow() {
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({ selected: 4 })
    }
    this.loadData()
  },

  loadData() {
    const member = family.getActiveMember()
    const members = family.getMembers()
    const history = family.getFilteredHistory().filter(r => r.type !== 'pk')
    let healthScore = null
    if (history.length > 0) {
      const total = history.reduce((s, r) => s + (r.score ?? r.fullResult?.health_score ?? 0), 0)
      healthScore = Math.round(total / history.length)
    }

    let bmi = null
    let bmiLevel = ''
    if (member && member.height && member.weight) {
      const h = Number(member.height) / 100
      bmi = Math.round(Number(member.weight) / (h * h) * 10) / 10
      if (bmi < 18.5) bmiLevel = '偏瘦'
      else if (bmi < 24) bmiLevel = '正常'
      else if (bmi < 28) bmiLevel = '偏重'
      else bmiLevel = '肥胖'
    }

    const selectedAvoidNames = ((member && member.selectedAvoids) || [])
      .map(id => AVOID_NAMES[id]).filter(Boolean).slice(0, 4)
    const memberViews = members.map(m => ({
      memberId: m.memberId,
      nickname: m.nickname || m.relationship || '成员',
      avatar: m.avatar || '',
      avatarText: shortAvatar(m),
      active: member && m.memberId === member.memberId,
    })).slice(0, 5)

    this.setData({
      member,
      members: memberViews,
      avatar: member?.avatar || '',
      avatarText: member ? shortAvatar(member) : '我',
      nickname: member?.nickname || member?.relationship || '当前成员',
      userType: member?.userType || '普通人群',
      healthScore,
      age: member?.age || '-',
      gender: member?.gender || '-',
      height: member?.height || '-',
      weight: member?.weight || '-',
      bmi,
      bmiLevel,
      selectedAvoidNames,
      aiTags: this.genAiTags(history, selectedAvoidNames),
    })
  },

  genAiTags(history, avoids) {
    const tags = []
    if (avoids.length) tags.push(...avoids.slice(0, 2))
    if (!history.length) return tags.length ? tags : ['等待扫描记录']
    const avg = history.reduce((s, r) => s + (r.score ?? r.fullResult?.health_score ?? 0), 0) / history.length
    const riskTotal = history.reduce((s, r) => s + ((r.fullResult?.risk_additives || []).length), 0)
    if (avg >= 80) tags.push('饮食表现稳定')
    if (riskTotal / history.length > 2) tags.push('关注添加剂')
    if (avg < 60) tags.push('需要重点改善')
    if (!tags.length) tags.push('持续观察')
    return tags.slice(0, 4)
  },

  switchMember(e) {
    const id = e.currentTarget.dataset.id
    if (!id) return
    family.setActiveMember(id)
    this.loadData()
  },

  addMember() { wx.navigateTo({ url: '/pages/family-edit/family-edit' }) },
  goFamilyManage() { wx.navigateTo({ url: '/pages/family-manage/family-manage' }) },
  editProfile() { const m = family.getActiveMember(); if (m) wx.navigateTo({ url: '/pages/family-edit/family-edit?memberId=' + m.memberId }) },
  editUserType() { this.editProfile() },
  editAvoid() { this.editProfile() },

  chooseAvatar() {
    const member = family.getActiveMember()
    if (!member) return
    wx.chooseMedia({
      count: 1,
      mediaType: ['image'],
      sourceType: ['album'],
      success: (res) => {
        const tempPath = res.tempFiles[0].tempFilePath
        wx.saveFile({
          tempFilePath: tempPath,
          success: (saveRes) => {
            family.updateMember(member.memberId, { avatar: saveRes.savedFilePath })
            this.loadData()
            wx.showToast({ title: '头像已更新', icon: 'success' })
          },
          fail: () => {
            family.updateMember(member.memberId, { avatar: tempPath })
            this.loadData()
            wx.showToast({ title: '头像已更新', icon: 'success' })
          }
        })
      }
    })
  },

  clearCache() {
    wx.showModal({
      title: '清除缓存',
      content: '确定清除所有扫描记录吗？此操作不可恢复。',
      success: (res) => {
        if (res.confirm) {
          wx.removeStorageSync('scanHistory')
          wx.removeStorageSync('lastResult')
          this.loadData()
          wx.showToast({ title: '已清除', icon: 'success' })
        }
      }
    })
  },
})

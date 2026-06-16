const family = require('../../utils/family')

Page({
  data: {
    members: [],
    activeMemberId: ''
  },

  onShow() {
    this.loadData()
  },

  loadData() {
    const members = family.getMembers().map(member => ({
      ...member,
      avatarLetter: (member.nickname || '成').slice(0, 1),
      relationText: member.relationship ? member.relationship + ' · ' + member.userType : member.userType,
      avoidText: member.selectedAvoids && member.selectedAvoids.length ? '已设置 ' + member.selectedAvoids.length + ' 项忌口' : '未设置忌口',
    }))
    const activeMemberId = family.getActiveMemberId()
    this.setData({ members, activeMemberId })
  },

  switchMember(e) {
    const id = e.currentTarget.dataset.id
    family.setActiveMember(id)
    wx.showToast({ title: '已切换', icon: 'success', duration: 1000 })
    this.loadData()
  },

  editMember(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({ url: '/pages/family-edit/family-edit?memberId=' + id })
  },

  addMember() {
    const members = family.getMembers()
    if (members.length >= 6) {
      wx.showToast({ title: '最多添加6位家庭成员', icon: 'none' })
      return
    }
    wx.navigateTo({ url: '/pages/family-edit/family-edit' })
  },

  deleteMember(e) {
    const id = e.currentTarget.dataset.id
    const member = this.data.members.find(m => m.memberId === id)
    if (!member) return

    wx.showModal({
      title: '确认删除',
      content: '确定要移除「' + member.nickname + '」吗？该成员的扫描记录将不再显示。',
      confirmColor: '#DC2626',
      success: (res) => {
        if (res.confirm) {
          const result = family.deleteMember(id)
          if (result.ok) {
            wx.showToast({ title: '已移除', icon: 'success' })
            this.loadData()
          } else {
            wx.showToast({ title: result.msg, icon: 'none' })
          }
        }
      }
    })
  }
})

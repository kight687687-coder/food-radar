const family = require('../../utils/family')

var AVOID_GROUPS = [
  { key: 'red', name: '过敏类', ids: ['peanut','nuts','milk_allergy','egg','wheat','soy','seafood','sesame'] },
  { key: 'orange', name: '不耐受类', ids: ['lactose','fructose','caffeine','alcohol','msg'] },
  { key: 'green', name: '主动回避类', ids: ['trans_fat','artificial_color','artificial_sweet','preservative','hfcs','nitrite','flavor'] },
]

var AVOID_NAMES = {
  peanut: '花生过敏', nuts: '坚果过敏', milk_allergy: '牛奶过敏',
  egg: '鸡蛋过敏', wheat: '小麦/麸质过敏', soy: '大豆过敏',
  seafood: '海鲜过敏', sesame: '芝麻过敏',
  lactose: '乳糖不耐受', fructose: '果糖不耐受', caffeine: '咖啡因敏感',
  alcohol: '酒精不耐受', msg: '味精敏感',
  trans_fat: '反式脂肪', artificial_color: '人工色素', artificial_sweet: '人工甜味剂',
  preservative: '防腐剂', hfcs: '高果糖浆', nitrite: '亚硝酸盐', flavor: '香精香料',
}

var USER_TYPES = ['普通人群', '减肥', '健身', '儿童', '老人', '孕妇', '糖尿病', '心血管']
var GENDERS = ['男', '女', '保密']
var RELATIONS = ['爸爸', '妈妈', '爷爷', '奶奶', '外公', '外婆', '儿子', '女儿', '老公', '老婆', '哥哥', '姐姐', '弟弟', '妹妹', '我自己']

Page({
  data: {
    isEdit: false,
    memberId: '',
    nickname: '',
    gender: '',
    genderIndex: 0,
    age: '',
    height: '',
    weight: '',
    userType: '普通人群',
    typeIndex: 0,
    avoidGroups: [],
    selectedAvoids: [],
    avoidExpanded: false,
    avoidSummary: '点击设置',
    avatar: '',
    avatarLetter: '+',
    genders: ['男', '女', '保密'],
    relations: ['爸爸', '妈妈', '爷爷', '奶奶', '外公', '外婆', '儿子', '女儿', '老公', '老婆', '哥哥', '姐姐', '弟弟', '妹妹', '我自己'],
    relationship: ''
  },

  onLoad: function (options) {
    var memberId = options.memberId || ''
    var isEdit = !!memberId
    var self = this

    if (isEdit) {
      var members = family.getMembers()
      var member = members.find(function (m) { return m.memberId === memberId })
      if (member) {
        var avoids = member.selectedAvoids || []
        var typeIdx = USER_TYPES.indexOf(member.userType || '普通人群')
        var genderIdx = GENDERS.indexOf(member.gender || '')
        self.setData({
          isEdit: true,
          memberId: memberId,
          nickname: member.nickname || '',
          gender: member.gender || '',
          genderIndex: genderIdx > -1 ? genderIdx : 0,
          age: member.age || '',
          height: member.height || '',
          weight: member.weight || '',
          userType: member.userType || '普通人群',
          typeIndex: typeIdx > -1 ? typeIdx : 0,
          selectedAvoids: avoids,
          avoidSummary: avoids.length > 0 ? '已选' + avoids.length + '项' : '点击设置',
          avatar: member.avatar || '',
          avatarLetter: (member.nickname || '成').slice(0, 1),
          relationship: member.relationship || ''
        })
        wx.setNavigationBarTitle({ title: '编辑成员' })
      }
    }

    self._buildAvoidGroups(self.data.selectedAvoids)
  },

  _buildAvoidGroups: function (saved) {
    saved = saved || []
    var groups = AVOID_GROUPS.map(function (g) {
      var items = g.ids.map(function (id) {
        return { id: id, name: AVOID_NAMES[id], checked: saved.indexOf(id) !== -1 }
      })
      return { name: g.name, key: g.key, expanded: false, items: items }
    })
    this.setData({ avoidGroups: groups })
  },

  // ─── 昵称 ───
  onNicknameInput: function (e) {
    var nickname = e.detail.value || ''
    this.setData({
      nickname: nickname,
      avatarLetter: nickname ? nickname.slice(0, 1) : '+'
    })
  },

  // ─── 性别 ───
  confirmGender: function (e) {
    var idx = e.detail.value
    this.setData({ gender: GENDERS[idx], genderIndex: idx })
  },

  // ─── 数字输入 ───
  onAgeInput: function (e) { this.setData({ age: e.detail.value }) },
  onHeightInput: function (e) { this.setData({ height: e.detail.value }) },
  onWeightInput: function (e) { this.setData({ weight: e.detail.value }) },

  // ─── 人群类型 ───
  confirmType: function (e) {
    var idx = e.detail.value
    this.setData({ userType: USER_TYPES[idx], typeIndex: idx })
  },

  // ─── 家庭关系 ───
  confirmRelation: function (e) {
    var idx = e.detail.value
    this.setData({ relationship: RELATIONS[idx] })
  },

  // ─── 忌口设置 ───
  toggleAvoidSection: function () {
    this.setData({ avoidExpanded: !this.data.avoidExpanded })
  },

  toggleGroup: function (e) {
    var key = e.currentTarget.dataset.key
    var groups = this.data.avoidGroups
    for (var i = 0; i < groups.length; i++) {
      if (groups[i].key === key) {
        groups[i].expanded = !groups[i].expanded
        break
      }
    }
    this.setData({ avoidGroups: groups })
  },

  toggleAvoidItem: function (e) {
    var id = e.currentTarget.dataset.id
    var saved = this.data.selectedAvoids.slice()
    var idx = saved.indexOf(id)
    if (idx === -1) {
      saved.push(id)
    } else {
      saved.splice(idx, 1)
    }
    var groups = this.data.avoidGroups
    for (var i = 0; i < groups.length; i++) {
      for (var j = 0; j < groups[i].items.length; j++) {
        if (groups[i].items[j].id === id) {
          groups[i].items[j].checked = !groups[i].items[j].checked
          break
        }
      }
    }
    this.setData({
      selectedAvoids: saved,
      avoidGroups: groups,
      avoidSummary: saved.length > 0 ? '已选' + saved.length + '项' : '点击设置'
    })
  },

  // ─── 头像 ───
  chooseAvatar: function () {
    var self = this
    wx.chooseMedia({
      count: 1,
      mediaType: ['image'],
      sourceType: ['album'],
      success: function (res) {
        var tempPath = res.tempFiles[0].tempFilePath
        wx.saveFile({
          tempFilePath: tempPath,
          success: function (saveRes) {
            self.setData({ avatar: saveRes.savedFilePath })
          },
          fail: function () {
            self.setData({ avatar: tempPath })
          }
        })
      }
    })
  },

  // ─── 保存 ───
  saveMember: function () {
    var nickname = (this.data.nickname || '').trim()
    if (!nickname) {
      wx.showToast({ title: '请输入昵称', icon: 'none' })
      return
    }

    var form = {
      nickname: nickname,
      gender: this.data.gender,
      age: this.data.age,
      height: this.data.height,
      weight: this.data.weight,
      relationship: this.data.relationship,
      userType: this.data.userType,
      selectedAvoids: this.data.selectedAvoids,
      avatar: this.data.avatar
    }

    if (this.data.isEdit) {
      family.updateMember(this.data.memberId, form)
      wx.showToast({ title: '已更新', icon: 'success' })
    } else {
      var result = family.addMember(form)
      if (!result.ok) {
        wx.showToast({ title: result.msg, icon: 'none' })
        return
      }
      wx.showToast({ title: '已添加', icon: 'success' })
    }

    setTimeout(function () { wx.navigateBack() }, 800)
  },

  // ─── 删除成员 ───
  deleteMember: function () {
    var self = this
    var members = family.getMembers()
    var member = members.find(function (m) { return m.memberId === self.data.memberId })
    var name = member ? member.nickname : '该成员'

    wx.showModal({
      title: '确认删除',
      content: '确定要移除「' + name + '」吗？',
      confirmColor: '#DC2626',
      success: function (res) {
        if (res.confirm) {
          var result = family.deleteMember(self.data.memberId)
          if (result.ok) {
            wx.showToast({ title: '已移除', icon: 'success' })
            setTimeout(function () { wx.navigateBack() }, 800)
          } else {
            wx.showToast({ title: result.msg, icon: 'none' })
          }
        }
      }
    })
  }
})

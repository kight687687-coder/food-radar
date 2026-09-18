const app = getApp()

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

Page({
  data: {
    nickname: '',
    gender: '',
    age: '',
    height: '',
    weight: '',
    userType: '普通人群',
    showGenderPicker: false,
    showTypePicker: false,
    genderIndex: 0,
    typeIndex: 0,
    mode: '',
    genderList: ['男', '女', '保密'],
    typeList: [
      '普通人群', '减肥', '健身',
      '儿童', '老人', '孕妇',
      '糖尿病', '心血管',
    ],
    avoidGroups: [],
    selectedAvoids: [],
    avoidExpanded: false,
    avoidSummary: '点击设置',
  },

  onLoad: function(options) {
    this.setData({
      mode: (options && options.mode) || '',
    })

    this.loadAvoids()

    var profile = wx.getStorageSync('userProfile')
    if (profile && profile.userId && this.data.mode !== 'edit' && this.data.mode !== 'edit_type') {
      wx.reLaunch({ url: '/pages/index/index' })
      return
    }
    if (profile) {
      var typeIdx = this.data.typeList.indexOf(profile.userType)
      var genderIdx = this.data.genderList.indexOf(profile.gender)
      this.setData({
        nickname: profile.nickname || '',
        gender: profile.gender || '',
        age: profile.age || '',
        height: profile.height || '',
        weight: profile.weight || '',
        userType: profile.userType || '普通人群',
        typeIndex: typeIdx > -1 ? typeIdx : 0,
        genderIndex: genderIdx > -1 ? genderIdx : 0,
      })
    }
  },

  onShow: function() {
    this.loadAvoids()
  },

  loadAvoids: function() {
    var profile = wx.getStorageSync('userProfile') || {}
    var saved = profile.selectedAvoids || []
    var groups = AVOID_GROUPS.map(function(g) {
      var items = g.ids.map(function(id) {
        return { id: id, name: AVOID_NAMES[id], checked: saved.indexOf(id) !== -1 }
      })
      return { name: g.name, key: g.key, expanded: false, items: items }
    })
    var total = saved.length
    this.setData({
      selectedAvoids: saved,
      avoidGroups: groups,
      avoidSummary: total > 0 ? '已选' + total + '项' : '点击设置',
    })
  },

  toggleAvoidSection: function() {
    this.setData({ avoidExpanded: !this.data.avoidExpanded })
  },

  toggleGroup: function(e) {
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

  toggleAvoidItem: function(e) {
    var id = e.currentTarget.dataset.id
    var saved = this.data.selectedAvoids.slice()
    var idx = saved.indexOf(id)
    if (idx === -1) {
      // 未选择时加入忌口列表
      saved.push(id)
    } else {
      // 已选择时从忌口列表移除
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
      avoidSummary: saved.length > 0 ? '已选' + saved.length + '项' : '点击设置',
    })
  },

  onNicknameInput(e) {
    this.setData({ nickname: e.detail.value })
  },

  onAgeInput(e) {
    this.setData({ age: e.detail.value })
  },

  onHeightInput(e) {
    this.setData({ height: e.detail.value })
  },

  onWeightInput(e) {
    this.setData({ weight: e.detail.value })
  },

  showGenderPicker() {
    this.setData({ showGenderPicker: true })
  },

  confirmGender(e) {
    const idx = e.detail.value[0]
    this.setData({
      gender: this.data.genderList[idx],
      genderIndex: idx,
      showGenderPicker: false,
    })
  },

  cancelGender() {
    this.setData({ showGenderPicker: false })
  },

  showTypePicker() {
    this.setData({ showTypePicker: true })
  },

  confirmType(e) {
    const idx = e.detail.value
    const type = this.data.typeList[idx]
    this.setData({
      userType: type,
      typeIndex: idx,
      showTypePicker: false,
    })
  },

  cancelType() {
    this.setData({ showTypePicker: false })
  },

  saveProfile() {
    if (!this.data.nickname) {
      wx.showToast({ title: '请输入昵称', icon: 'none' })
      return
    }

    const existing = wx.getStorageSync('userProfile') || {}
    // 没有历史用户ID时使用当前时间生成本地用户ID
    const userId = existing.userId || Date.now()

    wx.setStorageSync('userProfile', {
      ...existing,
      userId: userId,
      nickname: this.data.nickname,
      gender: this.data.gender,
      age: this.data.age,
      height: this.data.height,
      weight: this.data.weight,
      userType: this.data.userType,
      selectedAvoids: this.data.selectedAvoids,
    })
    wx.setStorageSync('hasProfile', true)

    const g = app.globalData
    g.userId = userId
    g.userType = this.data.userType
    g.hasProfile = true

    wx.showToast({ title: this.data.mode ? '修改成功' : '保存成功' })

    if (this.data.mode === 'edit' || this.data.mode === 'edit_type') {
      setTimeout(function () { wx.navigateBack() }, 1200)
    } else {
      wx.switchTab({ url: '/pages/index/index' })
    }
  },

  skipProfile() {
    const existing = wx.getStorageSync('userProfile') || {}
    const userId = existing.userId || Date.now()

    wx.setStorageSync('userProfile', {
      userId: userId,
      userType: '普通人群',
    })
    wx.setStorageSync('hasProfile', true)

    const g = app.globalData
    g.userId = userId
    g.userType = '普通人群'
    g.hasProfile = true

    wx.switchTab({ url: '/pages/index/index' })
  },
})

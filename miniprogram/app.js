App({
  globalData: {
    baseUrl: 'http://154.8.193.154:5000',
    userId: null,
    userType: null,
    hasProfile: false,
  },
  onLaunch() {
    const profile = wx.getStorageSync('userProfile')
    if (profile && profile.userId) {
      this.globalData.userId = profile.userId
      this.globalData.userType = profile.userType
      this.globalData.hasProfile = true
    }
    // 初始化家庭模式
    const family = require('./utils/family')
    family.initFamily()
  },
})

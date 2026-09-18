Page({
  goScan() {
    wx.switchTab({
      url: '/pages/scan/scan'
    })
  },

  goHome() {
    wx.switchTab({
      url: '/pages/index/index'
    })
  }
})

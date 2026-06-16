
Page({
  data: {},

  onShow() {
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({ selected: 3 })
    }
  },

  goPage(e) {
    const path = e.currentTarget.dataset.path
    if (path) wx.navigateTo({ url: path })
  },

  goTab(e) {
    const path = e.currentTarget.dataset.path
    if (path) wx.switchTab({ url: path })
  },

  goAiChat() {
    wx.navigateTo({ url: '/pages/ai-chat/ai-chat' })
  },

  showComing() {
    wx.showToast({ title: '即将上线', icon: 'none' })
  }
})

Page({
  data: {
    keyword: '',
    examples: ['山梨酸钾', '阿斯巴甜', '柠檬黄', '黄原胶'],
  },

  onInput(e) {
    this.setData({ keyword: e.detail.value })
  },

  useExample(e) {
    this.setData({ keyword: e.currentTarget.dataset.text })
  },

  search() {
    const keyword = (this.data.keyword || '').trim()
    if (!keyword) {
      wx.showToast({ title: '请输入成分名称', icon: 'none' })
      return
    }
    wx.navigateTo({ url: `/pages/wiki/wiki?keyword=${encodeURIComponent(keyword)}` })
  },

  goWiki() {
    wx.navigateTo({ url: '/pages/wiki/wiki' })
  },
})

const api = require('../../utils/request')
const family = require('../../utils/family')

Page({
  data: {
    analyzing: false,
    recentRecord: null,
  },

  onShow() {
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({ selected: 2 })
    }
    this.loadRecent()
  },

  loadRecent() {
    const history = family.getFilteredHistory().filter(r => r.type !== 'pk')
    const latest = history[0]
    if (!latest) {
      // 没有历史记录时清空最近记录展示
      this.setData({ recentRecord: null })
      return
    }
    const d = new Date(latest.createTime)
    const time = latest.createTime ? `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}` : ''
    this.setData({
      recentRecord: {
        foodName: latest.foodName || latest.food_category || '未命名食品',
        category: latest.food_category || latest.fullResult?.food_category || '食品',
        score: latest.score || latest.fullResult?.health_score || 0,
        imagePath: latest.imagePath || latest.fullResult?.imagePath || '',
        time,
        createTime: latest.createTime,
      }
    })
  },

  chooseImage() {
    if (this.data.analyzing) return
    wx.chooseMedia({
      count: 1,
      mediaType: ['image'],
      sourceType: ['album'],
      success: (res) => this.uploadImage(res.tempFiles[0].tempFilePath),
    })
  },

  uploadImage(filePath) {
    this.setData({ analyzing: true })
    wx.showLoading({ title: '分析中', mask: true })

    wx.getFileSystemManager().readFile({
      filePath,
      encoding: 'base64',
      success: (fileRes) => {
        // 将图片base64提交给后端，后端完成OCR、分类、评分和AI分析
        api.analyze(fileRes.data).then((data) => {
          wx.hideLoading()
          data.imagePath = filePath
          wx.setStorageSync('lastResult', data)
          // 提取前三个风险添加剂作为历史列表标签
          const tags = (data.risk_additives || []).slice(0, 3).map(a => a.name)
          const record = family.addScanRecord({
            foodName: data.food_category || '未命名食品',
            food_category: data.food_category || '',
            score: data.health_score,
            tags,
            createTime: new Date().toISOString(),
            imagePath: '',
            fullResult: data,
          })
          // 保存图片到本地持久路径，避免临时文件失效后历史图片无法展示
          wx.saveFile({
            tempFilePath: filePath,
            success: (saveRes) => {
              const history = wx.getStorageSync('scanHistory') || []
              const idx = history.findIndex(r => r.createTime === record.createTime)
              if (idx !== -1) {
                // 回写历史记录中的图片路径，并同步完整结果中的图片路径
                history[idx].imagePath = saveRes.savedFilePath
                if (history[idx].fullResult) history[idx].fullResult.imagePath = saveRes.savedFilePath
                wx.setStorageSync('scanHistory', history)
              }
              const lastResult = wx.getStorageSync('lastResult') || {}
              lastResult.imagePath = saveRes.savedFilePath
              wx.setStorageSync('lastResult', lastResult)
            },
          })
          this.setData({ analyzing: false })
          wx.navigateTo({ url: '/pages/result/result' })
        }).catch((err) => {
          // 后端识别失败或网络失败时，恢复按钮状态并提示用户重新选择清晰图片
          wx.hideLoading()
          wx.showToast({ title: err.msg || '分析失败，请重新选择清晰图片', icon: 'none', duration: 3000 })
          this.setData({ analyzing: false })
        })
      },
      fail: () => {
        wx.hideLoading()
        wx.showToast({ title: '读取图片失败', icon: 'none' })
        this.setData({ analyzing: false })
      },
    })
  },

  goCompare() {
    wx.navigateTo({ url: '/pages/compare/compare' })
  },

  goRecentDetail() {
    const record = this.data.recentRecord
    if (!record) return
    const scanHistory = wx.getStorageSync('scanHistory') || []
    const fullRecord = scanHistory.find(r => r.createTime === record.createTime)
    if (fullRecord && fullRecord.fullResult) {
      // 结果页统一读取lastResult，因此进入前同步缓存中的完整记录
      const fullResult = fullRecord.fullResult
      fullResult.imagePath = fullRecord.imagePath || fullResult.imagePath || ''
      wx.setStorageSync('lastResult', fullResult)
      wx.navigateTo({ url: '/pages/result/result' })
    }
  },

  goHistory() {
    wx.navigateTo({ url: '/pages/history/history' })
  },
})

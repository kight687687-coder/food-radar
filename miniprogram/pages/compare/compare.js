const api = require('../../utils/request')
const family = require('../../utils/family')
const app = getApp()

Page({
  data: {
    foodA: null,
    foodB: null,
    ready: false,
    analyzing: false,
    winner: null,
    winnerName: '',
    cmpRows: [],
    riskListA: [],
    riskListB: [],
    aiAdvice: '',
    aiLoading: false,
  },

  onLoad(options) {
    // 从历史PK记录进入时，直接加载已保存的完整对比数据
    if (options && options.mode === 'history') {
      this.loadFromHistory()
      return
    }
    const preset = wx.getStorageSync('resultForCompare')
    if (preset && preset.food_category) {
      wx.removeStorageSync('resultForCompare')
      this.setData({ foodA: preset })
    }
  },

  loadFromHistory() {
    const pkResult = wx.getStorageSync('pkResult')
    if (!pkResult) {
      wx.showToast({ title: 'PK 数据已过期', icon: 'none' })
      wx.navigateBack()
      return
    }
    const pkData = wx.getStorageSync('pkFullData_' + pkResult.createTime)
    if (!pkData || !pkData.foodA || !pkData.foodB) {
      wx.showToast({ title: 'PK 数据已过期', icon: 'none' })
      wx.navigateBack()
      return
    }
    // 标记当前页面为历史查看模式，避免重复保存PK记录
    this._isHistoryView = true
    this.setData({ foodA: pkData.foodA, foodB: pkData.foodB })
    this.computeComparison()
    this.loadAiAdvice()
    this.setData({ ready: true })
  },

  selectFood(e) {
    const side = e.currentTarget.dataset.side
    // 分析中不允许重新选图，避免并发状态错乱
    if (!side || this.data.analyzing) return
    wx.chooseMedia({
      count: 1,
      mediaType: ['image'],
      sourceType: ['album'],
      success: (res) => {
        const path = res.tempFiles[0].tempFilePath
        const key = side === 'A' ? 'foodA' : 'foodB'
        this.setData({ [key]: { imagePath: path, status: 'pending' }, ready: false })
      }
    })
  },

  startCompare() {
    const { foodA, foodB } = this.data
    if (!foodA || !foodB || this.data.analyzing) return
    const tasks = []
    // 已分析过的食品直接复用结果，待分析图片才调用后端接口
    tasks.push(foodA.status === 'pending' ? this.analyzeImage(foodA.imagePath) : Promise.resolve(foodA))
    tasks.push(foodB.status === 'pending' ? this.analyzeImage(foodB.imagePath) : Promise.resolve(foodB))
    this.setData({ analyzing: true })
    wx.showLoading({ title: '分析中', mask: true })
    Promise.all(tasks).then(([resultA, resultB]) => {
      wx.hideLoading()
      this.setData({ foodA: resultA, foodB: resultB, analyzing: false })
      this.computeComparison()
      this.loadAiAdvice()
      this.setData({ ready: true })
    }).catch((err) => {
      wx.hideLoading()
      wx.showToast({ title: err.msg || '分析失败', icon: 'none' })
      this.setData({ analyzing: false })
    })
  },

  analyzeImage(filePath) {
    return new Promise((resolve, reject) => {
      wx.getFileSystemManager().readFile({
        filePath,
        encoding: 'base64',
        success: (fileRes) => {
          // 提交后端执行OCR、分类、评分和AI分析
          api.analyze(fileRes.data).then((data) => {
            data.imagePath = filePath
            resolve(data)
          }).catch(reject)
        },
        fail: () => reject({ msg: '读取图片失败' })
      })
    })
  },

  computeComparison() {
    const { foodA, foodB } = this.data
    if (!foodA || !foodB) return
    const scoreA = foodA.health_score || 0
    const scoreB = foodB.health_score || 0
    const riskA = foodA.risk_additives || []
    const riskB = foodB.risk_additives || []
    const benefitA = foodA.beneficial_ingredients || []
    const benefitB = foodB.beneficial_ingredients || []
    const warnA = (foodA.group_warnings || []).length + (foodA.avoid_warnings || []).length
    const warnB = (foodB.group_warnings || []).length + (foodB.avoid_warnings || []).length
    // 评分不同优先按评分判断；评分相同时选择风险项更少的一方
    const winner = scoreA === scoreB ? (riskA.length <= riskB.length ? 'A' : 'B') : (scoreA > scoreB ? 'A' : 'B')
    const winnerFood = winner === 'A' ? foodA : foodB
    const winnerName = winnerFood.food_category || (winner === 'A' ? '食品 A' : '食品 B')
    const cmpRows = [
      { label: '健康评分', valA: scoreA + '分', valB: scoreB + '分', aWins: scoreA > scoreB, bWins: scoreB > scoreA },
      { label: '风险成分', valA: riskA.length + '项', valB: riskB.length + '项', aWins: riskA.length < riskB.length, bWins: riskB.length < riskA.length },
      { label: '有益成分', valA: benefitA.length + '项', valB: benefitB.length + '项', aWins: benefitA.length > benefitB.length, bWins: benefitB.length > benefitA.length },
      { label: '人群提醒', valA: warnA + '条', valB: warnB + '条', aWins: warnA < warnB, bWins: warnB < warnA },
    ]
    const riskListA = riskA.map(r => ({ name: r.name || '风险成分', level: this.riskLevelClass(r) }))
    const riskListB = riskB.map(r => ({ name: r.name || '风险成分', level: this.riskLevelClass(r) }))
    this.setData({ winner, winnerName, cmpRows, riskListA, riskListB })
    // 非历史模式下保存本次PK记录，供历史页回看
    if (!this._isHistoryView) this.savePkRecord(winner, scoreA, scoreB)
  },

  riskLevelClass(item) {
    const level = String(item.risk_level || '')
    const deduct = Number(item.deduct_score || item.deduct || 0)
    if (level.indexOf('高') !== -1 || deduct >= 20) return 'high'
    if (level.indexOf('中') !== -1 || deduct >= 10) return 'mid'
    return 'low'
  },

  savePkRecord(winner, scoreA, scoreB) {
    const { foodA, foodB } = this.data
    const createTime = new Date().toISOString()
    const pkRecord = {
      type: 'pk',
      foodName: (foodA.food_category || '食品A') + ' VS ' + (foodB.food_category || '食品B'),
      scoreA,
      scoreB,
      categoryA: foodA.food_category || '食品A',
      categoryB: foodB.food_category || '食品B',
      winner,
      imagePathA: foodA.imagePath || '',
      imagePathB: foodB.imagePath || '',
      tags: [],
      score: Math.max(scoreA, scoreB),
      riskCount: 0,
      winnerScore: Math.max(scoreA, scoreB),
      winnerRiskCount: winner === 'A' ? (foodA.risk_additives || []).length : (foodB.risk_additives || []).length,
      winnerImage: winner === 'A' ? (foodA.imagePath || '') : (foodB.imagePath || ''),
      createTime,
    }
    family.addScanRecord(pkRecord)
    // 完整分析结果单独缓存，避免历史列表记录过大
    wx.setStorageSync('pkFullData_' + createTime, { foodA, foodB })
  },

  loadAiAdvice() {
    const { foodA, foodB } = this.data
    if (!foodA || !foodB) return
    this.setData({ aiAdvice: '', aiLoading: true })
    wx.request({
      url: app.globalData.baseUrl + '/api/ai-compare',
      method: 'POST',
      data: {
        food_a: {
          food_category: foodA.food_category,
          health_score: foodA.health_score,
          risk_additives: foodA.risk_additives || [],
          group_warnings: foodA.group_warnings || [],
        },
        food_b: {
          food_category: foodB.food_category,
          health_score: foodB.health_score,
          risk_additives: foodB.risk_additives || [],
          group_warnings: foodB.group_warnings || [],
        },
      },
      timeout: 30000,
      header: { 'Content-Type': 'application/json' },
      success: (res) => {
        // AI失败时使用兜底文案，保证页面始终可展示建议
        const advice = res.data && res.data.code === 200 ? (res.data.data.advice || '') : ''
        this.setData({ aiAdvice: advice || '结合个人忌口和食用频率选择更适合的一款。', aiLoading: false })
      },
      fail: () => this.setData({ aiAdvice: '结合个人忌口和食用频率选择更适合的一款。', aiLoading: false })
    })
  },

  resetAll() {
    this.setData({
      foodA: null,
      foodB: null,
      ready: false,
      analyzing: false,
      winner: null,
      winnerName: '',
      cmpRows: [],
      riskListA: [],
      riskListB: [],
      aiAdvice: '',
    })
  }
})

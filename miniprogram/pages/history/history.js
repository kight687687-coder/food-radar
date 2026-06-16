const app = getApp()
const { BENEFICIAL_KEYWORDS } = require('../../utils/constants')
const { genParticles } = require('../../utils/helpers')
const family = require('../../utils/family')

Page({
  data: {
    records: [],
    loading: false,
    loaded: false,
    groupedRecords: [],
    totalCount: 0,
    highRiskCount: 0,
    avgScore: 0,
    renameInfo: { g: -1, index: -1, value: '' },
    pageParticles: [],
  },

  _genParticles() {
    return genParticles(14)
  },

  onShow() {
    // 清空记录，触发飞入动画重播
    this.setData({
      pageParticles: this._genParticles(),
      records: [],
      groupedRecords: [],
    })
    if (app.globalData.hasProfile) {
      setTimeout(() => this.loadHistory(), 50)
    }
  },

  loadHistory() {
    this.setData({ loading: true })

    const scanHistory = family.getFilteredHistory()

    const totalCount = scanHistory.length
    const highRiskCount = scanHistory.filter(r => (r.score ?? 100) < 60).length
    const avgScore = totalCount > 0
      ? Math.round(scanHistory.reduce((s, r) => s + (r.score ?? 0), 0) / totalCount)
      : 0

    // 按日期分组
    const today = new Date()
    const fmtDate = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
    const todayStr = fmtDate(today)
    const yesterday = new Date(today)
    yesterday.setDate(yesterday.getDate() - 1)
    const yesterdayStr = fmtDate(yesterday)

    const groupMap = new Map()
    const groupOrder = []

    scanHistory.forEach((rec, idx) => {
      const d = new Date(rec.createTime)
      const ds = fmtDate(d)

      let label
      if (ds === todayStr) label = '今天'
      else if (ds === yesterdayStr) label = '昨天'
      else label = `${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`

      let time = ''
      try {
        time = `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
      } catch (e) { time = '' }

      // PK记录特殊处理
      if (rec.type === 'pk') {
        const item = {
          id: rec.createTime + '_' + idx,
          type: 'pk',
          createTime: rec.createTime,
          foodName: rec.foodName,
          categoryA: rec.categoryA,
          categoryB: rec.categoryB,
          scoreA: rec.scoreA,
          scoreB: rec.scoreB,
          winner: rec.winner,
          score: rec.score,
          time,
          imagePath: '',
          riskCount: 0,
          winnerScore: rec.winnerScore,
          winnerRiskCount: rec.winnerRiskCount,
          winnerImage: rec.winnerImage,
        }
        if (!groupMap.has(ds)) {
          groupMap.set(ds, { dateLabel: label, records: [] })
          groupOrder.push(groupMap.get(ds))
        }
        groupMap.get(ds).records.push(item)
        return
      }

      const score = rec.score ?? 0
      const scoreLevel = score >= 80 ? '优秀' : score >= 60 ? '良好' : '高风险'

      // 从该记录的 fullResult 提取添加剂风险等级
      const fullResult = rec.fullResult || {}
      const riskMap = {}
      ;(fullResult.risk_additives || []).forEach(a => {
        riskMap[a.name] = a.risk_level === '高' ? 'high' : a.risk_level === '中' ? 'mid' : a.risk_level === '低' ? 'low' : 'safe'
      })

      const name = rec.foodName || rec.food_category || '未知食品'
      const origCategory = rec.food_category || (rec.fullResult && rec.fullResult.food_category) || ''

      // 有益成分标签：优先从 fullResult 提取，没有时从配料表关键词匹配
      let beneficialTags = []
      const beneficialFromResult = (fullResult.beneficial_ingredients || []).map(b => b.nutrient)
      if (beneficialFromResult.length > 0) {
        beneficialTags = beneficialFromResult
      } else if (fullResult.ingredients) {
        const ingText = '' + fullResult.ingredients
        for (const kw of BENEFICIAL_KEYWORDS) {
          if (ingText.indexOf(kw) !== -1 && beneficialTags.indexOf(kw) === -1) {
            beneficialTags.push(kw)
          }
        }
      }

      const item = {
        id: rec.createTime + '_' + idx,
        createTime: rec.createTime,
        foodName: name,
        category: origCategory.replace('类', ''),
        score,
        scoreLevel,
        riskCount: rec.tags ? rec.tags.length : 0,
        tags: (rec.tags || []).map(name => ({ name, level: riskMap[name] || 'safe' })),
        beneficialTags,
        time,
        imagePath: rec.imagePath || (rec.fullResult && rec.fullResult.imagePath) || '',
      }

      if (!groupMap.has(ds)) {
        groupMap.set(ds, { dateLabel: label, records: [] })
        groupOrder.push(groupMap.get(ds))
      }
      groupMap.get(ds).records.push(item)
    })

    this.setData({
      records: scanHistory,
      groupedRecords: groupOrder,
      totalCount, highRiskCount, avgScore,
      loading: false, loaded: true,
    })
  },

  goDetail(e) {
    const { g, index } = e.currentTarget.dataset
    const group = this.data.groupedRecords[g]
    const record = group?.records?.[index]
    if (!record) return

    // PK记录：保存完整数据跳转到对比页
    if (record.type === 'pk') {
      wx.setStorageSync('pkResult', record)
      wx.navigateTo({ url: '/pages/compare/compare?mode=history' })
      return
    }

    // 尝试从 scanHistory 中找回完整结果
    const scanHistory = wx.getStorageSync('scanHistory') || []
    const fullRecord = scanHistory.find(r => r.createTime && r.createTime === record.createTime)

    if (fullRecord && fullRecord.fullResult) {
      const fullResult = fullRecord.fullResult
      // 确保使用原始的 food_category（未改名前的模型结果）
      fullResult.food_category = fullRecord.food_category || fullResult.food_category
      fullResult.imagePath = fullRecord.imagePath || fullResult.imagePath || ''
      wx.setStorageSync('lastResult', fullResult)
    } else {
      wx.setStorageSync('lastResult', {
        health_score: record.score,
        food_category: record.foodName,
        imagePath: record.imagePath || '',
        risk_additives: [],
        group_warnings: [],
        avoid_warnings: [],
        ai_report: { summary: '', detail: '', suggestion: '', long_term_risk: '' },
      })
    }
    wx.navigateTo({ url: '/pages/result/result' })
  },

  startRename(e) {
    const { g, index } = e.currentTarget.dataset
    const group = this.data.groupedRecords[g]
    const record = group?.records?.[index]
    if (!record) return
    this.setData({
      renameInfo: { g, index, value: record.foodName },
    })
  },

  confirmRename(e) {
    if (this._renaming) return
    this._renaming = true

    const { g, index } = e.currentTarget.dataset
    const value = (e.detail.value || '').trim()
    if (value) {
      const scanHistory = wx.getStorageSync('scanHistory') || []
      const group = this.data.groupedRecords[g]
      const oldRecord = group?.records?.[index]
      if (oldRecord) {
        const historyRecord = scanHistory.find(r => r.createTime && r.createTime === oldRecord.createTime)
        if (historyRecord) {
          historyRecord.foodName = value
          wx.setStorageSync('scanHistory', scanHistory)
        }
      }
    }
    this.setData({ renameInfo: { g: -1, index: -1, value: '' } })
    this.loadHistory()

    setTimeout(() => { this._renaming = false }, 300)
  },

  goScan() {
    wx.switchTab({ url: '/pages/scan/scan' })
  },
})

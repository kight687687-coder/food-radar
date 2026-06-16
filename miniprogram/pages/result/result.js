
const { BENEFICIAL_MAP } = require('../../utils/constants')
const { animateScore } = require('../../utils/helpers')

Page({
  data: {
    result: null,
    scoreLevel: '',
    animatedScore: 0,
    myWarnings: [],
    userType: '',
    riskItems: [],
    benefitItems: [],
    hitAvoids: [],
    showAvoidAlert: false,
    aiTags: [],
  },

  onLoad() { this.loadData() },
  onShow() { this.loadData() },

  animate(target) { animateScore(this.setData.bind(this), 'animatedScore', target || 0) },

  loadData() {
    const result = wx.getStorageSync('lastResult')
    if (!result) {
      wx.showToast({ title: '暂无分析数据', icon: 'none' })
      wx.switchTab({ url: '/pages/scan/scan' })
      return
    }
    const score = result.health_score || 0
    const scoreLevel = score >= 80 ? '可以放心食用' : score >= 60 ? '建议适量食用' : '需要谨慎选择'
    const rawRisks = result.risk_additives || []
    const riskItems = rawRisks.slice(0, 6).map(a => {
      const deduct = Number(a.deduct_score) || Number(a.deduct) || 0
      const cls = deduct >= 20 ? 'bad' : deduct >= 10 ? 'mid' : 'low'
      return {
        name: a.name || '风险成分',
        level: a.risk_level || (cls === 'bad' ? '高风险' : cls === 'mid' ? '中风险' : '低风险'),
        deduct,
        cls,
        desc: a.reason || a.description || '建议关注摄入频率。'
      }
    })
    if (result.ingredients_count_penalty > 0) {
      riskItems.push({ name: '配料较多', level: '中风险', deduct: result.ingredients_count_penalty, cls: 'mid', desc: '配料项目较多，建议优先选择配料更短的同类食品。' })
    }

    let rawBenefits = result.beneficial_ingredients || []
    if (rawBenefits.length === 0 && result.ingredients && BENEFICIAL_MAP) {
      const ingCombined = '' + result.ingredients
      const seen = new Set()
      Object.keys(BENEFICIAL_MAP).forEach(keyword => {
        if (ingCombined.indexOf(keyword) !== -1 && !seen.has(keyword)) {
          seen.add(keyword)
          rawBenefits.push({ nutrient: keyword, benefit_category: BENEFICIAL_MAP[keyword].cat })
        }
      })
    }
    const benefitItems = rawBenefits.slice(0, 6).map(b => ({ name: b.nutrient || b.name, cat: b.benefit_category || '' }))
    const profile = wx.getStorageSync('userProfile') || {}
    const hitAvoids = (result.avoid_warnings || []).map(a => a.name || a.avoid_name || a).filter(Boolean)
    const myWarnings = result.group_warnings || []
    const aiReport = result.ai_report || {}
    const aiTags = []
    if (score >= 80) aiTags.push('整体风险较低')
    if (riskItems.length) aiTags.push('存在风险成分')
    if (myWarnings.length) aiTags.push('人群需注意')

    this.setData({
      result,
      scoreLevel,
      myWarnings,
      userType: profile.userType || '',
      riskItems,
      benefitItems,
      hitAvoids,
      showAvoidAlert: hitAvoids.length > 0,
      aiTags,
      aiSummary: aiReport.summary || '',
      aiDetail: aiReport.detail || '',
      aiSuggestion: aiReport.suggestion || '',
      longTermRisk: aiReport.long_term_risk || '',
    })
    this.animate(score)
  },

  closeAvoidAlert() { this.setData({ showAvoidAlert: false }) },
  goBack() { wx.switchTab({ url: '/pages/index/index' }) },
  goScan() { wx.switchTab({ url: '/pages/scan/scan' }) },
  goCompare() { wx.setStorageSync('resultForCompare', this.data.result); wx.navigateTo({ url: '/pages/compare/compare' }) },
  goCardReport() { wx.navigateTo({ url: '/pages/card-report/card-report' }) },
  goWiki(e) {
    const name = e.currentTarget.dataset.name
    if (!name) return
    wx.navigateTo({ url: `/pages/wiki-detail/wiki-detail?name=${encodeURIComponent(name)}` })
  },
})

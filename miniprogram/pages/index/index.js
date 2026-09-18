const { BENEFICIAL_KEYWORDS, BENEFICIAL_ADDITIVE_NAMES } = require('../../utils/constants')
const family = require('../../utils/family')
const app = getApp()

function formatDateKey(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function formatTime(value) {
  if (!value) return ''
  const d = new Date(value)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

function scoreLevel(score) {
  if (score >= 80) return { text: '安全', cls: 'good' }
  if (score >= 60) return { text: '注意', cls: 'mid' }
  return { text: '高风险', cls: 'bad' }
}

Page({
  data: {
    safetyScore: 0,
    safetyLevelClass: 'empty',
    safetyStatusText: '等待记录',
    scoreRingDeg: 0,
    scoreRingColor: '#C9CDD4',
    scoreDeltaText: '暂无对比',
    guardDays: 0,
    todayScanCount: 0,
    homeSummary: '选择一张配料表图片，先看看这个食品适不适合你。',
    homeSuggestion: '从常吃的零食、饮料、儿童食品开始记录，会更快形成家庭档案。',
    riskEvent: null,
    recentRecords: [],
    trendBars: [],
    trendSummary: '扫描 3 次以上后生成趋势',
    nickname: '',
    userType: '',
   animateIn: false,
    enginePanelShow: false,
  },

  onShow() {
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({ selected: 0 })
    }
    this.replayEntryAnimation()
    const saved = wx.getStorageSync('userProfile')
    if (saved && saved.userId) {
      app.globalData.userId = saved.userId
      app.globalData.userType = saved.userType || ''
      app.globalData.hasProfile = true
      this.loadDashboard()
    } else {
      wx.reLaunch({ url: '/pages/profile/profile' })
    }
  },

  replayEntryAnimation() {
    this.setData({ animateIn: false })
    wx.nextTick(() => {
      this.setData({ animateIn: true })
    })
  },

  loadDashboard() {
    const activeMember = family.getActiveMember()
    const history = family.getFilteredHistory().filter(r => r.type !== 'pk')
    const safetyScore = this.computeSafetyScore(history)
    const safetyView = this.getSafetyView(safetyScore)
    const scoreDeltaText = this.computeDelta(history)
    const guardDays = this.computeGuardDays(history)
    const todayScanCount = this.computeTodayScanCount(history)
    const recentRecords = this.buildRecent(history.slice(0, 2))
    const trendBars = this.buildTrend(history)
    const trendSummary = this.buildTrendSummary(trendBars)
    const riskEvent = this.buildRiskEvent(history)
    const homeCopy = this.buildHomeCopy(history, safetyScore, riskEvent)

    this.setData({
      safetyScore,
      safetyLevelClass: safetyView.cls,
      safetyStatusText: safetyView.text,
      scoreRingDeg: Math.round(Math.max(0, Math.min(safetyScore, 100)) * 3.6),
      scoreRingColor: this.getScoreRingColor(safetyView.cls),
      scoreDeltaText,
      guardDays,
      todayScanCount,
      recentRecords,
      trendBars,
      trendSummary,
      riskEvent,
      homeSummary: homeCopy.summary,
      homeSuggestion: homeCopy.suggestion,
      nickname: activeMember ? (activeMember.nickname || activeMember.relationship || '当前成员') : '当前成员',
      userType: activeMember ? activeMember.userType || '' : '',
    })
  },

  computeSafetyScore(history) {
    const scores = history.map(r => r.score ?? r.fullResult?.health_score ?? 0).filter(Boolean)
    if (!scores.length) return 0
    return Math.round(scores.slice(0, 10).reduce((s, v) => s + v, 0) / Math.min(scores.length, 10))
  },

  getSafetyView(score) {
    if (score >= 80) return { text: '状态良好', cls: 'good' }
    if (score >= 60) return { text: '需要关注', cls: 'mid' }
    if (score > 0) return { text: '风险偏高', cls: 'bad' }
    return { text: '等待记录', cls: 'empty' }
  },

  computeDelta(history) {
    const now = new Date()
    const weekStart = new Date(now)
    weekStart.setDate(now.getDate() - 6)
    const prevStart = new Date(now)
    prevStart.setDate(now.getDate() - 13)
    const current = []
    const prev = []
    history.forEach(r => {
      if (!r.createTime) return
      const d = new Date(r.createTime)
      const score = r.score ?? r.fullResult?.health_score ?? 0
      if (!score) return
      if (d >= weekStart && d <= now) current.push(score)
      else if (d >= prevStart && d < weekStart) prev.push(score)
    })
    if (!current.length || !prev.length) return '继续积累记录'
    const avg = arr => Math.round(arr.reduce((s, v) => s + v, 0) / arr.length)
    const diff = avg(current) - avg(prev)
    if (diff === 0) return '与上周持平'
    return diff > 0 ? `较上周提升 ${diff} 分` : `较上周下降 ${Math.abs(diff)} 分`
  },

  computeGuardDays(history) {
    const days = new Set()
    history.forEach(r => {
      if (r.createTime) days.add(formatDateKey(new Date(r.createTime)))
    })
    return days.size
  },

  computeTodayScanCount(history) {
    const todayKey = formatDateKey(new Date())
    return history.filter(r => r.createTime && formatDateKey(new Date(r.createTime)) === todayKey).length
  },

  getScoreRingColor(level) {
    if (level === 'good') return '#07C160'
    if (level === 'mid') return '#FF7D00'
    if (level === 'bad') return '#F53F3F'
    return '#C9CDD4'
  },

  buildRecent(records) {
    return records.map(r => {
      const score = r.score ?? r.fullResult?.health_score ?? 0
      const level = scoreLevel(score)
      return {
        foodName: r.foodName || r.food_category || r.fullResult?.food_category || '未命名食品',
        category: r.food_category || r.fullResult?.food_category || '食品',
        score,
        levelText: level.text,
        levelCls: level.cls,
        imagePath: r.imagePath || r.fullResult?.imagePath || '',
        time: formatTime(r.createTime),
        createTime: r.createTime,
      }
    })
  },

  buildTrend(history) {
    const result = []
    const today = new Date()
    const labels = ['一', '二', '三', '四', '五', '六', '日']
    for (let i = 6; i >= 0; i--) {
      const d = new Date(today)
      d.setDate(today.getDate() - i)
      const key = formatDateKey(d)
      const scores = history.filter(r => r.createTime && formatDateKey(new Date(r.createTime)) === key)
        .map(r => r.score ?? r.fullResult?.health_score ?? 0).filter(Boolean)
      // 同一天有多次扫描时取平均分，避免单次记录过度影响趋势
      const score = scores.length ? Math.round(scores.reduce((s, v) => s + v, 0) / scores.length) : 0
      const day = d.getDay()
      const label = labels[day === 0 ? 6 : day - 1]
      result.push({
        label,
        score,
        height: score ? Math.max(28, Math.round(score * 1.15)) : 22,
        cls: score >= 80 ? 'good' : score >= 60 ? 'mid' : score > 0 ? 'bad' : 'empty',
      })
    }
    return result
  },

  buildTrendSummary(bars) {
    const scores = bars.map(b => b.score).filter(Boolean)
    if (scores.length < 3) return '扫描 3 次以上后生成趋势'
    const avg = Math.round(scores.reduce((s, v) => s + v, 0) / scores.length)
    return `本周平均 ${avg} 分，持续记录更容易发现变化`
  },

  buildRiskEvent(history) {
    const riskMap = {}
    history.forEach(r => {
      const risks = r.fullResult?.risk_additives || []
      // 已知有益添加剂不计入风险事件，避免首页误报
      risks.filter(a => !BENEFICIAL_ADDITIVE_NAMES.includes(a.name)).forEach(a => {
        const key = a.name || '风险成分'
        if (!riskMap[key]) riskMap[key] = { name: key, count: 0, sources: [] }
        riskMap[key].count++
        const source = r.foodName || r.food_category || r.fullResult?.food_category
        if (source && riskMap[key].sources.indexOf(source) === -1) riskMap[key].sources.push(source)
      })
    })
    const top = Object.values(riskMap).sort((a, b) => b.count - a.count)[0]
    if (!top) return null
    return {
      title: `${top.name} 出现 ${top.count} 次`,
      source: top.sources.slice(0, 3).join('、') || '近期扫描食品',
    }
  },

  buildHomeCopy(history, score, riskEvent) {
    if (!history.length) {
      return {
        summary: '还没有识别记录，先选一张配料表图片看看。',
        suggestion: '从家里常吃的食品开始，几次之后就能看出更清楚的饮食变化。',
      }
    }
    if (riskEvent) {
      return {
        summary: `近期 ${riskEvent.title}，主要来自 ${riskEvent.source}。`,
        suggestion: '同类食品可以先少买几次，换一款配料更短的会更稳妥。',
      }
    }
    if (score >= 80) {
      return {
        summary: '最近识别的食品整体比较安心。',
        suggestion: '继续保持看配料表的习惯，给家里常吃食品留个底。',
      }
    }
    if (score >= 60) {
      return {
        summary: '最近有一些成分需要留意，但整体还算可控。',
        suggestion: '买之前多比较一下配料表，优先选成分更简单的。',
      }
    }
    return {
      summary: '最近食品风险偏高，需要更谨慎一点。',
      suggestion: '先减少同类食品频率，再用配料表 PK 找更合适的替代品。',
    }
  },

 goScan() { wx.switchTab({ url: '/pages/scan/scan' }) },
  showEnginePanel() { this.setData({ enginePanelShow: true }) },
  closeEnginePanel() { this.setData({ enginePanelShow: false }) },
  noop() {},
 goWiki() { wx.navigateTo({ url: '/pages/wiki/wiki' }) },
  goCompare() { wx.navigateTo({ url: '/pages/compare/compare' }) },
  goAiChat() { wx.navigateTo({ url: '/pages/ai-chat/ai-chat' }) },
  goReport() { wx.switchTab({ url: '/pages/report/report' }) },
  goHistory() { wx.navigateTo({ url: '/pages/history/history' }) },

  goDetailFromIndex(e) {
    const record = this.data.recentRecords[e.currentTarget.dataset.index]
    if (!record) return
    const scanHistory = wx.getStorageSync('scanHistory') || []
    const fullRecord = scanHistory.find(r => r.createTime === record.createTime)
    if (fullRecord && fullRecord.fullResult) {
      const fullResult = fullRecord.fullResult
      fullResult.imagePath = fullRecord.imagePath || fullResult.imagePath || ''
      wx.setStorageSync('lastResult', fullResult)
      wx.navigateTo({ url: '/pages/result/result' })
    }
  },
})

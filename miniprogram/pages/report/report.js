const { BENEFICIAL_ADDITIVE_NAMES } = require('../../utils/constants')
const family = require('../../utils/family')

function fmtShort(d) {
  return `${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function formatTime(value) {
  if (!value) return ''
  const d = new Date(value)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

function scoreCls(score) {
  if (score >= 80) return 'good'
  if (score >= 60) return 'mid'
  if (score > 0) return 'bad'
  return 'empty'
}

function scoreOf(record) {
  return record.score ?? record.fullResult?.health_score ?? 0
}

Page({
  data: {
    nickname: '当前成员',
    memberLine: '普通人群',
    avatar: '',
    avatarText: '家',
    statusText: '等待记录',
    statusTone: 'empty',
    archiveScore: 0,
    trendText: '继续记录后生成周趋势',
    trendTone: 'empty',
    mainReason: '识别几次常吃食品后，系统会解释分数变化的主要原因。',
    suggestion: '先记录本周常吃食品，系统会给出更稳定的家庭食品安全建议。',
    nextActions: [],
    concernRows: [],
    recentRecords: [],
    latestRecord: null,
    weekScanCount: 0,
    weekAttentionCount: 0,
    riskProfiles: [],
    showRiskProfiles: false,
    profileBasis: '',
    manageActions: [
      { title: '食品记录', desc: '查看识别历史', iconClass: 'icon-file-text', tone: 'green', type: 'history' },
      { title: '饮食趋势', desc: '看长期变化', iconClass: 'icon-chart-line', tone: 'blue', type: 'trend' },
      { title: '风险偏好', desc: '管理忌口限制', iconClass: 'icon-shield-warning', tone: 'orange', type: 'avoid' },
      { title: '家庭成员', desc: '切换家庭档案', iconClass: 'icon-user-group', tone: 'purple', type: 'family' },
    ],
  },

  onShow() {
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({ selected: 1 })
    }
    this.loadHealthArchive()
  },

  loadHealthArchive() {
    const member = family.getActiveMember() || {}
    const history = family.getFilteredHistory()
      .filter(r => r.type !== 'pk')
      .sort((a, b) => new Date(b.createTime || 0) - new Date(a.createTime || 0))
    const weekRecords = this.getRecentDays(history, 7)
    const previousWeekRecords = this.getPreviousDays(history, 7, 7)
    const riskThemes = this.buildRiskThemes(weekRecords.length ? weekRecords : history)
    const categoryThemes = this.buildCategoryThemes(weekRecords.length ? weekRecords : history)
    const state = this.buildState(history, weekRecords, previousWeekRecords, riskThemes, categoryThemes)
    const recentRecords = history.slice(0, 3).map(record => this.buildRecord(record))

    this.setData({
      nickname: member.nickname || member.relationship || '当前成员',
      memberLine: member.userType || '普通人群',
      avatar: member.avatar || '',
      avatarText: (member.nickname || member.relationship || '家').slice(0, 1),
      statusText: state.statusText,
      statusTone: state.statusTone,
      archiveScore: state.score,
      trendText: state.trendText,
      trendTone: state.trendTone,
      mainReason: state.mainReason,
      suggestion: state.suggestion,
      nextActions: this.buildNextActions(state, riskThemes, weekRecords),
      concernRows: this.buildConcernRows(riskThemes, categoryThemes, weekRecords),
      latestRecord: recentRecords[0] || null,
      recentRecords,
      weekScanCount: weekRecords.length,
      weekAttentionCount: weekRecords.filter(r => scoreOf(r) < 70).length,
      riskProfiles: this.buildRiskProfiles(history, riskThemes, categoryThemes),
      showRiskProfiles: history.length >= 6,
      profileBasis: `基于近 ${Math.min(history.length, 30)} 条识别记录生成`,
    })
  },

  getRecentDays(history, days) {
    const start = new Date()
    start.setDate(start.getDate() - (days - 1))
    start.setHours(0, 0, 0, 0)
    return history.filter(r => r.createTime && new Date(r.createTime) >= start)
  },

  getPreviousDays(history, days, offsetDays) {
    const end = new Date()
    end.setDate(end.getDate() - offsetDays)
    end.setHours(0, 0, 0, 0)
    const start = new Date(end)
    start.setDate(start.getDate() - (days - 1))
    return history.filter(r => {
      if (!r.createTime) return false
      const t = new Date(r.createTime)
      return t >= start && t < end
    })
  },

  averageScore(records) {
    const scores = records.map(scoreOf).filter(Boolean)
    return scores.length ? Math.round(scores.reduce((sum, score) => sum + score, 0) / scores.length) : 0
  },

  buildState(history, weekRecords, previousWeekRecords, risks, categories) {
    if (!history.length) {
      return {
        statusText: '等待记录',
        statusTone: 'empty',
        score: 0,
        trendText: '完成几次识别后生成周趋势',
        trendTone: 'empty',
        mainReason: '识别几次常吃食品后，系统会解释分数变化的主要原因。',
        suggestion: '先记录本周常吃食品，系统会给出更稳定的家庭食品安全建议。',
      }
    }

    const recentBase = weekRecords.length ? weekRecords : history.slice(0, 10)
    const score = this.averageScore(recentBase)
    const previousScore = this.averageScore(previousWeekRecords)
    const attentionCount = weekRecords.filter(r => scoreOf(r) < 70).length
    const topRisk = risks[0]
    const topCategory = categories[0]
    const trend = this.buildTrendText(score, previousScore, weekRecords.length)

    let statusText = '整体稳定'
    let statusTone = 'good'
    if (score < 60 || attentionCount >= 3) {
      statusText = '需要关注'
      statusTone = 'bad'
    } else if (score < 80 || topRisk) {
      statusText = '轻度关注'
      statusTone = 'mid'
    }

    let mainReason = '近 7 天未发现明显高频风险，整体选择相对稳定。'
    if (topRisk) {
      mainReason = `${topRisk.name} 近 7 天出现 ${topRisk.count} 次，频率偏高。`
    } else if (topCategory) {
      mainReason = `${topCategory.name} 占近期记录 ${topCategory.pct}%，建议继续观察品类结构。`
    }

    let suggestion = '保持记录常吃食品，优先选择配料表更短、添加剂更少的产品。'
    if (topRisk) {
      suggestion = `减少含 ${topRisk.name} 的高添加剂食品，购买前多看配料表。`
    } else if (topCategory && topCategory.pct >= 40) {
      suggestion = `适当分散 ${topCategory.name} 摄入，搭配更简单的日常食品。`
    }

    return {
      statusText,
      statusTone,
      score,
      trendText: trend.text,
      trendTone: trend.tone,
      mainReason,
      suggestion,
    }
  },

  buildTrendText(score, previousScore, hasWeekRecord) {
    if (!hasWeekRecord) {
      return { text: '本周记录不足，先展示最近记录均值', tone: 'empty' }
    }
    if (!previousScore) {
      return { text: '继续记录后可对比上周变化', tone: 'empty' }
    }
    const diff = score - previousScore
    if (Math.abs(diff) <= 1) {
      return { text: '与上周基本持平', tone: 'flat' }
    }
    if (diff > 0) {
      return { text: `较上周上升 ${diff} 分`, tone: 'up' }
    }
    return { text: `较上周下降 ${Math.abs(diff)} 分`, tone: 'down' }
  },

  buildNextActions(state, risks, weekRecords) {
    const actions = []
    if (risks[0]) {
      actions.push({
        title: '查看高频添加剂说明',
        desc: risks[0].name,
        iconClass: 'icon-book',
        tone: 'orange',
        type: 'wiki',
      })
    } else {
      actions.push({
        title: '选择配料表更短的产品',
        desc: '优先看前 5 位成分',
        iconClass: 'icon-list',
        tone: 'green',
        type: 'wiki',
      })
    }

    const remain = Math.max(0, 3 - weekRecords.length)
    actions.push({
      title: remain ? `本周继续识别 ${remain} 次` : '保持本周记录节奏',
      desc: remain ? '让趋势判断更稳定' : '已具备基础趋势样本',
      iconClass: 'icon-file-text',
      tone: 'blue',
      type: 'scan',
    })
    actions.push({
      title: '更新忌口与偏好',
      desc: '让建议更贴合家庭成员',
      iconClass: 'icon-shield-warning',
      tone: 'purple',
      type: 'avoid',
    })
    return actions
  },

  buildRiskThemes(history) {
    const map = {}
    history.forEach(record => {
      const risks = record.fullResult?.risk_additives || []
      risks.filter(item => !BENEFICIAL_ADDITIVE_NAMES.includes(item.name)).forEach(item => {
        const name = item.name || '风险成分'
        if (!map[name]) map[name] = { name, count: 0 }
        map[name].count += 1
      })
    })
    return Object.values(map).sort((a, b) => b.count - a.count).slice(0, 3)
  },

  buildCategoryThemes(history) {
    const map = {}
    history.forEach(record => {
      const name = record.food_category || record.fullResult?.food_category || record.foodName || '常见食品'
      map[name] = (map[name] || 0) + 1
    })
    const total = history.length || 1
    return Object.entries(map).sort((a, b) => b[1] - a[1]).slice(0, 3).map(([name, count]) => ({
      name,
      count,
      pct: Math.round(count / total * 100),
    }))
  },

  buildConcernRows(risks, categories, weekRecords) {
    const rows = []
    if (risks[0]) {
      rows.push({
        title: '高频添加剂',
        desc: risks[0].name,
        meta: `近 7 天出现 ${risks[0].count} 次`,
        tone: 'warn',
        iconTone: 'orange',
        iconClass: 'icon-shield-warning',
      })
    }

    const attentionCount = weekRecords.filter(r => scoreOf(r) < 70).length
    rows.push({
      title: '近期风险',
      desc: attentionCount ? '存在需留意记录' : '暂无明显低分记录',
      meta: attentionCount ? `本周 ${attentionCount} 次低于 70 分` : '继续保持观察',
      tone: attentionCount ? 'warn' : 'info',
      iconTone: attentionCount ? 'orange' : 'green',
      iconClass: attentionCount ? 'icon-shield-warning' : 'icon-shield-check',
    })

    if (categories[0]) {
      rows.push({
        title: '重点品类',
        desc: categories[0].name,
        meta: `占近期记录 ${categories[0].pct}%`,
        tone: 'info',
        iconTone: 'blue',
        iconClass: 'icon-chart-line',
      })
    }

    while (rows.length < 3) {
      rows.push({
        title: '记录样本',
        desc: '继续识别常吃食品',
        meta: '生成更稳定判断',
        tone: 'muted',
        iconTone: 'green',
        iconClass: 'icon-file-text',
      })
    }

    return rows.slice(0, 3)
  },

  buildRiskProfiles(history, risks, categories) {
    if (history.length < 6) return []

    const profiles = []
    if (risks.length >= 2) {
      profiles.push({ name: '添加剂敏感', desc: '多种风险成分反复出现' })
    }
    if (categories.some(item => /饮料|糖|甜|零食/.test(item.name) && item.pct >= 30)) {
      profiles.push({ name: '甜食倾向', desc: '甜食或饮料类占比较高' })
    }
    if (!profiles.length) {
      profiles.push({ name: '整体稳定', desc: '近期食品选择相对均衡' })
    }
    return profiles.slice(0, 2)
  },

  buildRecord(record) {
    const score = scoreOf(record)
    const d = record.createTime ? new Date(record.createTime) : null
    return {
      foodName: record.foodName || record.food_category || record.fullResult?.food_category || '未命名食品',
      category: record.food_category || record.fullResult?.food_category || '食品',
      score,
      cls: scoreCls(score),
      levelText: score >= 80 ? '安心' : score >= 60 ? '需留意' : score > 0 ? '谨慎' : '待分析',
      dateLabel: d ? fmtShort(d) : '',
      time: formatTime(record.createTime),
      createTime: record.createTime,
    }
  },

  goManage(e) {
    const type = e.currentTarget.dataset.type
    if (type === 'history') wx.navigateTo({ url: '/pages/history/history' })
    else if (type === 'trend') wx.navigateTo({ url: '/pages/card-report/card-report' })
    else if (type === 'avoid') wx.navigateTo({ url: '/pages/avoid/avoid' })
    else if (type === 'family') wx.navigateTo({ url: '/pages/family-manage/family-manage' })
  },

  goNextAction(e) {
    const type = e.currentTarget.dataset.type
    if (type === 'scan') wx.switchTab({ url: '/pages/scan/scan' })
    else if (type === 'avoid') wx.navigateTo({ url: '/pages/avoid/avoid' })
    else wx.navigateTo({ url: '/pages/wiki/wiki' })
  },

  goScan() { wx.switchTab({ url: '/pages/scan/scan' }) },

  goRecordDetail(e) {
    const createTime = e.currentTarget.dataset.time
    const scanHistory = wx.getStorageSync('scanHistory') || []
    const fullRecord = scanHistory.find(r => r.createTime === createTime)
    if (fullRecord && fullRecord.fullResult) {
      const fullResult = fullRecord.fullResult
      fullResult.imagePath = fullRecord.imagePath || fullResult.imagePath || ''
      wx.setStorageSync('lastResult', fullResult)
      wx.navigateTo({ url: '/pages/result/result' })
    }
  },
})

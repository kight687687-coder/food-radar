const { additives } = require('../../data/additives')
const app = getApp()

function getRiskView(level) {
  const num = Number(level)
  if (num === 1) return { text: '低风险', tone: 'low', width: '33%' }
  if (num === 2) return { text: '中风险', tone: 'mid', width: '66%' }
  if (num === 3) return { text: '高风险', tone: 'high', width: '100%' }
  return { text: '待确认', tone: 'unknown', width: '18%' }
}

function normalizeEntry(entry, fromApi) {
  const risk = getRiskView(entry.risk_level)
  const alias = (entry.alias || []).filter(item => item && item !== entry.name)
  return {
    ...entry,
    fromApi,
    riskText: risk.text,
    riskTone: risk.tone,
    riskWidth: risk.width,
    aliasText: alias.join(' / '),
    specialGroupsText: (entry.special_groups || []).join('、'),
    infoRows: [
      { label: '主要用途', value: entry.usage || '暂无数据' },
      { label: '常见食品', value: entry.common_in || '暂无数据' },
      { label: 'ADI 值', value: entry.adi || '暂无数据' },
      { label: '类别', value: entry.category || '未分类' },
    ],
  }
}

Page({
  data: {
    additive: null,
    loading: true,
    errorText: '',
  },

  onLoad(options) {
    const name = decodeURIComponent(options.name || '').trim()
    if (!name) {
      wx.showToast({ title: '缺少参数', icon: 'none' })
      wx.navigateBack()
      return
    }

    const found = additives.find(item =>
      item.name === name ||
      (item.alias || []).some(alias => alias === name)
    )

    if (found) {
      wx.setNavigationBarTitle({ title: found.name })
      this.setData({
        additive: normalizeEntry(found, false),
        loading: false,
        errorText: '',
      })
      return
    }

    const cacheKey = 'wiki_cache_' + name
    const cached = wx.getStorageSync(cacheKey)
    if (cached) {
      try {
        // 命中本地缓存时直接展示，减少重复调用后端AI百科接口
        const parsed = typeof cached === 'string' ? JSON.parse(cached) : cached
        wx.setNavigationBarTitle({ title: parsed.name || name })
        this.setData({
          additive: normalizeEntry(parsed, true),
          loading: false,
          errorText: '',
        })
        return
      } catch (err) {
        // 缓存结构异常时清理缓存，避免后续继续读取坏数据
        wx.removeStorageSync(cacheKey)
      }
    }

    this.fetchFromApi(name, cacheKey)
  },

  fetchFromApi(name, cacheKey) {
    this.setData({ loading: true, errorText: '' })

    wx.request({
      url: app.globalData.baseUrl + '/api/wiki-query',
      method: 'POST',
      data: { name },
      timeout: 30000,
      header: { 'Content-Type': 'application/json' },
      success: (res) => {
        if (res.data && res.data.success && res.data.data) {
          const entry = res.data.data
          // AI结果写入本地缓存，后续再次查看同一添加剂可直接使用
          wx.setStorageSync(cacheKey, entry)
          wx.setNavigationBarTitle({ title: entry.name || name })
          this.setData({
            additive: normalizeEntry(entry, true),
            loading: false,
            errorText: '',
          })
        } else {
          // 接口返回不完整时展示兜底百科结构
          this.showFallback(name)
        }
      },
      fail: () => {
        this.showFallback(name)
      },
    })
  },

  showFallback(name) {
    const fallback = {
      name,
      usage: '暂无详细数据',
      common_in: '暂无数据',
      adi: '暂无数据',
      risk_level: 0,
      warning: '该添加剂暂未收录，请结合配料表上下文和可靠来源判断。',
      special_groups: [],
      intro: '',
      alias: [],
      category: '未分类',
    }

    this.setData({
      additive: normalizeEntry(fallback, true),
      loading: false,
      errorText: '百科库未命中，已展示临时信息',
    })
  },

  goBack() {
    wx.navigateBack()
  },
})

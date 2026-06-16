const { additives } = require('../../data/additives')

const PAGE_SIZE = 30
const CATEGORIES = ['全部', ...new Set(additives.map(item => item.category))]

function getRiskMeta(level) {
  if (level === 1) return { text: '低风险', tone: 'low' }
  if (level === 2) return { text: '中风险', tone: 'mid' }
  if (level === 3) return { text: '高风险', tone: 'high' }
  return { text: '待确认', tone: 'unknown' }
}

function normalizeItem(item) {
  const risk = getRiskMeta(Number(item.risk_level))
  return {
    ...item,
    riskText: risk.text,
    riskTone: risk.tone,
    aliasText: (item.alias || []).filter(alias => alias && alias !== item.name).slice(0, 2).join(' / '),
  }
}

Page({
  data: {
    searchWord: '',
    currentCat: '全部',
    categories: CATEGORIES,
    filteredAdditives: [],
    displayList: [],
    pageIndex: 1,
    totalCount: additives.length,
    highRiskCount: additives.filter(item => Number(item.risk_level) === 3).length,
  },

  onLoad(options) {
    const keyword = options.keyword || ''
    if (keyword) {
      this.setData({ searchWord: keyword })
    }
    this.resetAndFilter()
  },

  onSearch(e) {
    this.setData({ searchWord: (e.detail.value || '').trim() })
    this.resetAndFilter()
  },

  clearSearch() {
    this.setData({ searchWord: '' })
    this.resetAndFilter()
  },

  switchCategory(e) {
    const cat = e.currentTarget.dataset.cat
    if (!cat || cat === this.data.currentCat) return
    this.setData({ currentCat: cat })
    this.resetAndFilter()
  },

  resetAndFilter() {
    const { searchWord, currentCat } = this.data
    let list = additives

    if (currentCat !== '全部') {
      list = list.filter(item => item.category === currentCat)
    }

    if (searchWord) {
      const kw = searchWord.toLowerCase()
      list = list.filter(item =>
        item.name.toLowerCase().includes(kw) ||
        item.id.toLowerCase().includes(kw) ||
        (item.alias || []).some(alias => alias.toLowerCase().includes(kw))
      )
    }

    this.setData({
      filteredAdditives: list.map(normalizeItem),
      displayList: [],
      pageIndex: 1,
    })
    this.appendPage()
  },

  appendPage() {
    const { filteredAdditives, pageIndex, displayList } = this.data
    const start = (pageIndex - 1) * PAGE_SIZE
    const end = start + PAGE_SIZE
    const nextItems = filteredAdditives.slice(start, end)
    if (!nextItems.length) return

    this.setData({
      displayList: displayList.concat(nextItems),
      pageIndex: pageIndex + 1,
    })
  },

  loadMore() {
    this.appendPage()
  },

  goDetail(e) {
    const name = e.currentTarget.dataset.name
    if (!name) return
    wx.navigateTo({ url: `/pages/wiki-detail/wiki-detail?name=${encodeURIComponent(name)}` })
  },
})

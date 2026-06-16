const { drawQRCode } = require('../../utils/qrcode')
const family = require('../../utils/family')

const CARD_W = 500
const CARD_H = 800

Page({
  data: {
    historyList: [],
    period: 'day',
    periodStats: null,
    canvasW: 0,
    canvasH: 0,
    shareImage: '',
  },

  onLoad() {
    this.calcCanvasSize()
    this.loadHistory()
  },

  calcCanvasSize() {
    const sys = wx.getWindowInfo()
    const rpx2px = sys.windowWidth / 750
    const pad = 30 * rpx2px
    const dw = sys.windowWidth - pad * 2
    this.setData({ canvasW: dw, canvasH: dw * (CARD_H / CARD_W) })
  },

  loadHistory() {
    const raw = family.getFilteredHistory()
    const list = raw.map(r => ({
      ...r,
      foodName: r.foodName || r.food_name || '未知食品',
      score: r.score || 0,
      createTime: r.createTime || r.time || Date.now(),
    }))
    this.setData({ historyList: list }, () => {
      // Default to "今日"
      this.selectPeriod({ currentTarget: { dataset: { period: 'day' } } })
    })
  },

  // ═══ 选择时间维度 ═══
  selectPeriod(e) {
    const period = e.currentTarget.dataset.period
    this.setData({ period }, () => {
      const stats = this.calcStats(period)
      this.setData({ periodStats: stats }, () => {
        if (stats) setTimeout(() => this.renderCard(), 120)
      })
    })
  },

  calcStats(period) {
    const now = new Date()
    const list = this.data.historyList

    const inRange = (t) => {
      const d = new Date(t)
      if (isNaN(d.getTime())) return false
      if (period === 'day') {
        return d.getFullYear() === now.getFullYear() &&
               d.getMonth() === now.getMonth() &&
               d.getDate() === now.getDate()
      }
      if (period === 'week') {
        const start = new Date(now)
        start.setDate(now.getDate() - now.getDay())
        start.setHours(0, 0, 0, 0)
        return d.getTime() >= start.getTime()
      }
      return d.getFullYear() === now.getFullYear()
    }

    const filtered = list.filter(r => inRange(r.createTime))
    if (filtered.length === 0) return null

    const count = filtered.length
    const scores = filtered.map(r => r.score)
    const avg = (scores.reduce((a, b) => a + b, 0) / count).toFixed(1)
    const maxScore = Math.max(...scores)
    const best = filtered.find(r => r.score === maxScore)

    const labels = { day: '今日', week: '本周', year: '本年' }
    return {
      label: `你的${labels[period]}饮食图鉴`,
      count,
      avgScore: avg,
      bestName: best ? best.foodName : '',
      bestScore: maxScore,
      bestTags: best ? best.tags || [] : [],
      bestBeneficial: best ? best.beneficialTags || [] : [],
    }
  },

  // ═══ 渲染 Canvas ═══
  renderCard() {
    const query = wx.createSelectorQuery()
    query.select('#reportCanvas').fields({ node: true, size: true })
      .exec((res) => {
        if (!res || !res[0]) return
        const canvas = res[0].node
        const ctx = canvas.getContext('2d')
        const dpr = wx.getWindowInfo().pixelRatio
        canvas.width = CARD_W * dpr
        canvas.height = CARD_H * dpr
        ctx.scale(dpr, dpr)
        this.data.canvasNode = canvas
        this.drawCard(ctx, this.data.periodStats)

        wx.canvasToTempFilePath({
          canvas, fileType: 'png',
          success: (r) => { this.data.shareImage = r.tempFilePath }
        })
      })
  },

  // ─── 绘制卡片 ───
  drawCard(ctx, stats) {
    const W = CARD_W, H = CARD_H
    const periods = { day: '今日', week: '本周', year: '本年' }
    const periodLabel = periods[this.data.period] || '今日'

    // 圆角矩形
    const rr = (x, y, w, h, r) => {
      ctx.beginPath()
      ctx.moveTo(x + r, y); ctx.lineTo(x + w - r, y)
      ctx.arcTo(x + w, y, x + w, y + r, r)
      ctx.lineTo(x + w, y + h - r); ctx.arcTo(x + w, y + h, x + w - r, y + h, r)
      ctx.lineTo(x + r, y + h); ctx.arcTo(x, y + h, x, y + h - r, r)
      ctx.lineTo(x, y + r); ctx.arcTo(x, y, x + r, y, r)
      ctx.closePath()
    }

    // ─── 1. 背景渐变 ───
    ctx.save()
    const grad = ctx.createLinearGradient(0, 0, 0, H)
    grad.addColorStop(0, '#1a3d2b')
    grad.addColorStop(1, '#4a9e6f')
    ctx.fillStyle = grad
    ctx.fillRect(0, 0, W, H)

    // ─── 2. 装饰圆点 ───
    ctx.fillStyle = 'rgba(255,255,255,0.04)'
    for (let i = 0; i < 30; i++) {
      ctx.beginPath()
      ctx.arc(Math.random() * W, Math.random() * H, 3 + Math.random() * 12, 0, Math.PI * 2)
      ctx.fill()
    }

    // ─── 3. Header ───
    ctx.fillStyle = 'rgba(255,255,255,0.9)'
    ctx.font = 'bold 20px sans-serif'
    ctx.textAlign = 'left'; ctx.textBaseline = 'top'
    ctx.fillText('食安雷达 · 饮食健康报告', 24, 28)

    ctx.fillStyle = 'rgba(255,255,255,0.6)'
    ctx.font = '18px sans-serif'
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle'
    ctx.fillText(`「你的${periodLabel}饮食图鉴」`, W / 2, 94)

    // ─── 4. 三格数据区 ───
    const sY = 150, sW = 140, sH = 110, sGap = (W - 140 * 3) / 4

    const drawStat = (x, label, val, unit) => {
      ctx.fillStyle = 'rgba(255,255,255,0.12)'
      rr(x, sY, sW, sH, 12); ctx.fill()

      ctx.fillStyle = 'rgba(255,255,255,0.5)'
      ctx.font = '13px sans-serif'
      ctx.textAlign = 'center'; ctx.textBaseline = 'top'
      ctx.fillText(label, x + sW / 2, sY + 12)

      ctx.fillStyle = '#FFFFFF'
      ctx.font = 'bold 38px sans-serif'
      ctx.textBaseline = 'middle'
      ctx.fillText(String(val), x + sW / 2, sY + sH / 2 + 4)

      ctx.fillStyle = 'rgba(255,255,255,0.45)'
      ctx.font = '11px sans-serif'
      ctx.textBaseline = 'bottom'
      ctx.fillText(unit, x + sW / 2, sY + sH - 8)
    }

    drawStat(sGap, '扫描次数', stats.count, '次')
    drawStat(sGap * 2 + sW, '平均评分', stats.avgScore, '分')
    drawStat(sGap * 3 + sW * 2, '最高分', stats.bestScore, '分')

    // ─── 5. 最佳食品展示 ───
    const bestY = 320
    ctx.fillStyle = 'rgba(255,255,255,0.5)'
    ctx.font = '14px sans-serif'
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle'
    const unit = periodLabel === '今日' ? '日' : periodLabel === '本周' ? '周' : '年'
    ctx.fillText(`本${unit}最佳`, W / 2, bestY)

    ctx.fillStyle = '#FFFFFF'
    ctx.font = 'bold 34px sans-serif'
    ctx.textBaseline = 'middle'
    const bName = (stats.bestName || '').length > 8 ? stats.bestName.slice(0, 8) + '...' : stats.bestName
    ctx.fillText(bName, W / 2, bestY + 54)

    // 评分圆环
    const cx = W / 2, cy = bestY + 160, r = 52
    ctx.beginPath()
    ctx.arc(cx, cy, r, 0, Math.PI * 2)
    ctx.strokeStyle = '#4FC3A1'
    ctx.lineWidth = 4
    ctx.stroke()

    ctx.fillStyle = '#FFFFFF'
    ctx.font = 'bold 46px sans-serif'
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle'
    ctx.fillText(String(stats.bestScore), cx, cy - 4)

    ctx.fillStyle = 'rgba(255,255,255,0.5)'
    ctx.font = '14px sans-serif'
    ctx.textBaseline = 'top'
    ctx.fillText('分', cx + 42, cy + 6)

    // 最佳食品标签
    const tags = [...(stats.bestBeneficial || []).slice(0, 1), ...(stats.bestTags || []).filter(t => t.level !== 'safe').slice(0, 1).map(t => t.name || t)]
    if (tags.length > 0) {
      const tagY = cy + r + 20
      ctx.fillStyle = 'rgba(255,255,255,0.15)'
      rr(cx - 80, tagY, 160, 28, 14); ctx.fill()

      ctx.fillStyle = 'rgba(255,255,255,0.6)'
      ctx.font = '13px sans-serif'
      ctx.textAlign = 'center'; ctx.textBaseline = 'middle'
      ctx.fillText(tags.join(' · '), cx, tagY + 14)
    }

    // ─── 6. Footer ───
    const footerY = H - 70
    ctx.fillStyle = 'rgba(255,255,255,0.4)'
    ctx.font = '13px sans-serif'
    ctx.textAlign = 'left'; ctx.textBaseline = 'middle'
    ctx.fillText('AI守护每一餐的健康', 24, footerY + 45)

    const qrSize = 72
    const qrX = W - qrSize - 24
    const qrY = footerY

    ctx.fillStyle = 'rgba(255,255,255,0.9)'
    rr(qrX - 4, qrY - 4, qrSize + 8, qrSize + 8, 6); ctx.fill()

    try {
      drawQRCode(ctx, `食安雷达:${periodLabel}健康报告`, qrX, qrY, 1.9, '#1a3d2b')
    } catch (_) {
      ctx.strokeStyle = 'rgba(0,0,0,0.15)'; ctx.lineWidth = 1
      ctx.strokeRect(qrX, qrY, qrSize, qrSize)
    }

    ctx.restore()
  },

  // ═══ 保存 & 分享 ═══
  saveToAlbum() {
    const canvas = this.data.canvasNode
    if (!canvas) { wx.showToast({ title: '暂无数据', icon: 'none' }); return }

    wx.canvasToTempFilePath({
      canvas,
      success: (res) => {
        wx.saveImageToPhotosAlbum({
          filePath: res.tempFilePath,
          success: () => wx.showToast({ title: '已保存到相册', icon: 'success' }),
          fail: (err) => {
            if (err.errMsg && (err.errMsg.includes('auth deny') || err.errMsg.includes('fail auth'))) {
              wx.showModal({
                title: '需要权限',
                content: '保存图片需要相册权限',
                success: (r) => { if (r.confirm) wx.openSetting() }
              })
            } else {
              wx.showToast({ title: '保存失败', icon: 'none' })
            }
          }
        })
      },
      fail: () => wx.showToast({ title: '生成图片失败', icon: 'none' })
    })
  },

  onShareAppMessage() {
    return {
      title: '食安雷达 - 饮食健康报告',
      path: '/pages/card-report/card-report',
      imageUrl: this.data.shareImage || ''
    }
  }
})

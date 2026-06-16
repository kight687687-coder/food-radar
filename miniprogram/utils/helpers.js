/**
 * 通用工具函数
 */

/** 日期格式化为 YYYY-MM-DD */
function fmtDate(d) {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

/** 日期格式化为 MM-DD */
function fmtShort(d) {
  return `${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

/** 日期加减 */
function addDays(d, n) {
  const r = new Date(d)
  r.setDate(r.getDate() + n)
  return r
}

/** 计算周期起始日期 */
function startOfPeriod(navDate, type) {
  const d = new Date(navDate)
  if (type === 'weekly') {
    const day = d.getDay()
    d.setDate(d.getDate() - (day === 0 ? 6 : day - 1))
  } else if (type === 'monthly') {
    d.setDate(1)
  } else if (type === 'yearly') {
    d.setMonth(0, 1)
  }
  return d
}

/**
 * 生成背景漂浮粒子
 * @param {number} count - 粒子数量
 * @param {object} opts - 可选参数 { colors, sizeRange, durRange }
 */
function genParticles(count, opts) {
  const arr = []
  const colors = opts?.colors || ['rgba(45,106,79,0.35)', 'rgba(200,148,58,0.3)']
  for (let i = 0; i < count; i++) {
    arr.push({
      left: (5 + Math.random() * 85).toFixed(1) + '%',
      size: (8 + Math.random() * 10).toFixed(0) + 'rpx',
      duration: (12 + Math.random() * 12).toFixed(1) + 's',
      delay: (Math.random() * 14).toFixed(1) + 's',
      color: colors[i % colors.length],
    })
  }
  return arr
}

/**
 * 数字滚动动画
 * @param {function} setDataFn - this.setData 的引用
 * @param {string} key - data 中的字段名
 * @param {number} target - 目标值
 * @param {number} [steps=25] - 步数
 * @param {number} [interval=30] - 间隔毫秒
 */
function animateScore(setDataFn, key, target, steps, interval) {
  steps = steps || 25
  interval = interval || 30
  let current = 0
  const inc = target / steps
  let count = 0
  const timer = setInterval(() => {
    count++
    current = Math.min(Math.round(inc * count), target)
    setDataFn({ [key]: current })
    if (count >= steps) {
      clearInterval(timer)
      setDataFn({ [key]: target })
    }
  }, interval)
}

module.exports = {
  fmtDate,
  fmtShort,
  addDays,
  startOfPeriod,
  genParticles,
  animateScore,
}

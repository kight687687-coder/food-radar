const app = getApp()

const BASE_URL = app.globalData.baseUrl

function _request(url, method, data) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: BASE_URL + url,
      method: method,
      data: data,
      timeout: 30000,
      header: { 'Content-Type': 'application/json' },
      success(res) {
        if (res.data.code === 200) {
          resolve(res.data.data)
        } else {
          reject({ msg: res.data.msg || '请求失败', code: res.data.code })
        }
      },
      fail(err) {
        reject({ msg: '网络错误: ' + err.errMsg, code: -1 })
      },
    })
  })
}

/** 扫描分析食品配料表 */
function analyze(image, userType, avoidIds) {
  return _request('/analyze', 'POST', {
    image,
    user_type: userType || app.globalData.userType,
    avoid_ids: avoidIds ? avoidIds.join(',') : undefined,
    user_id: app.globalData.userId,
  })
}

/** PK对比两款食品 */
function compare(image1, image2, userType) {
  return _request('/compare', 'POST', {
    image1,
    image2,
    user_type: userType || app.globalData.userType,
  })
}

/** 获取历史记录 */
function getHistory() {
  return _request('/history?user_id=' + app.globalData.userId, 'GET')
}

/** 获取健康报告 (type: daily|monthly|yearly) */
function getReport(type, date) {
  if (type === 'daily') {
    return _request('/daily?user_id=' + app.globalData.userId, 'GET')
  }
  return _request('/history?user_id=' + app.globalData.userId + '&type=' + type + '&date=' + date, 'GET')
}

/** 对比两份报告 */
function compareReport(type, date1, date2) {
  return Promise.all([
    getReport(type, date1),
    getReport(type, date2),
  ]).then(([r1, r2]) => ({ report1: r1, report2: r2 }))
}

/** AI 营养师问答 */
function aiChat(question, history) {
  return _request('/api/ai-chat', 'POST', {
    question,
    history: history || [],
    user_type: app.globalData.userType,
    user_id: app.globalData.userId,
  })
}

/** 保存用户画像 */
function saveProfile(profile) {
  wx.setStorageSync('userProfile', profile)
  const g = app.globalData
  g.userId = profile.userId
  g.userType = profile.userType
  g.hasProfile = true
  return Promise.resolve({ success: true })
}

module.exports = {
  analyze,
  compare,
  getHistory,
  getReport,
  compareReport,
  aiChat,
  saveProfile,
}

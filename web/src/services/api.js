const configuredBase = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')
const devProxyEnabled = Boolean(import.meta.env.VITE_DEV_API_TARGET)
const API_BASE = configuredBase || (import.meta.env.DEV && devProxyEnabled ? '/backend-api' : '')

export class ApiError extends Error {
  constructor(message, code = -1) {
    super(message)
    this.name = 'ApiError'
    this.code = code
  }
}

async function request(path, options = {}) {
  if (!API_BASE) {
    throw new ApiError('在线识别服务尚未配置。请设置 VITE_API_BASE_URL 后重试。', 'NOT_CONFIGURED')
  }
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), options.timeout || 45000)
  try {
    const response = await fetch(`${API_BASE}${path}`, {
      method: options.method || 'GET',
      headers: { 'Content-Type': 'application/json', ...options.headers },
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      signal: controller.signal,
    })
    const payload = await response.json().catch(() => null)
    if (!response.ok) throw new ApiError(payload?.msg || payload?.error || `请求失败 (${response.status})`, response.status)
    if (payload?.code !== undefined) {
      if (payload.code !== 200) throw new ApiError(payload.msg || '请求失败', payload.code)
      return payload.data
    }
    return payload
  } catch (error) {
    if (error.name === 'AbortError') throw new ApiError('请求超时，请检查网络后重试。', 'TIMEOUT')
    if (error instanceof ApiError) throw error
    throw new ApiError('无法连接食品分析服务，请检查网络或服务地址。', 'NETWORK')
  } finally {
    clearTimeout(timeout)
  }
}

export function analyzeImage(base64, { userType, userId, avoidIds = [] } = {}) {
  const numericAvoidIds = avoidIds.filter(value => /^\d+$/.test(String(value)))
  return request('/analyze', {
    method: 'POST',
    body: {
      image: base64,
      user_type: userType || '普通人群',
      user_id: userId,
      avoid_ids: numericAvoidIds.length ? numericAvoidIds.join(',') : undefined,
    },
    timeout: 60000,
  })
}

export function getAiComparison(foodA, foodB) {
  return request('/api/ai-compare', {
    method: 'POST',
    body: {
      food_a: compactFood(foodA),
      food_b: compactFood(foodB),
    },
  })
}

export function askNutritionist(question, history, userType, userId) {
  return request('/api/ai-chat', {
    method: 'POST',
    body: { question, history, user_type: userType, user_id: userId },
  })
}

export function queryWiki(name) {
  return request('/api/wiki-query', { method: 'POST', body: { name } }).then(payload => payload?.data || payload)
}

function compactFood(food = {}) {
  return {
    food_category: food.food_category,
    health_score: food.health_score,
    risk_additives: food.risk_additives || [],
    group_warnings: food.group_warnings || [],
  }
}

export function getApiConfiguration() {
  return { configured: Boolean(API_BASE), baseUrl: API_BASE }
}

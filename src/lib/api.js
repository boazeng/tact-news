// קריאות לשרת. כל שגיאה נזרקת עם ההודעה (detail) שהשרת החזיר.
async function request(url, options = {}) {
  const res = await fetch(url, { credentials: 'same-origin', ...options })
  const isJson = (res.headers.get('content-type') || '').includes('application/json')
  const body = isJson ? await res.json() : null
  if (!res.ok) {
    const err = new Error((body && body.detail) || `שגיאה ${res.status}`)
    err.status = res.status
    throw err
  }
  return body
}

const json = (method, data) => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(data),
})
const q = (topic) => `topic=${encodeURIComponent(topic)}`

// בלי app → התחומים של האתר. '*' → כולל תחומי Longeviora (דף הניהול)
export const getTopics = (app = '') => request(`/api/topics${app ? `?app=${encodeURIComponent(app)}` : ''}`)
export const addTopic = (topic) => request('/api/topics', json('POST', topic))
export const editTopic = (id, fields) => request(`/api/topics/${encodeURIComponent(id)}`, json('PATCH', fields))
export const orderTopics = (ids) => request('/api/topics-order', json('PUT', { ids }))
export const deleteTopic = (id) => request(`/api/topics/${encodeURIComponent(id)}`, { method: 'DELETE' })
// all → גם ימים שעוד לא אושרו (מנהל)
export const getIssues = (topic, all = false) => request(`/api/issues?${q(topic)}${all ? '&all=1' : ''}`)
export const getIssue = (topic, day) => request(`/api/issues/${day}?${q(topic)}`)
export const getAgent = () => request('/api/agent')
export const runAgent = (topic = '') => request(`/api/agent/run?${q(topic)}`, { method: 'POST' })
export const getMe = () => request('/auth/me').catch(() => ({}))
export const paste = (topic, day, kind, text, title = '') =>
  request(`/api/issues/${day}/paste?${q(topic)}`, json('POST', { kind, text, title }))
export const deleteDay = (topic, day) => request(`/api/issues/${day}?${q(topic)}`, { method: 'DELETE' })
export const deleteFile = (topic, day, kind, name) =>
  request(`/api/issues/${day}/${kind}/${encodeURIComponent(name)}?${q(topic)}`, { method: 'DELETE' })
export const getReview = () => request('/api/review')
export const previewDay = (topic, day) => request(`/api/review/${day}?${q(topic)}`)
export const approveDay = (topic, day) => request(`/api/review/${day}?${q(topic)}`, { method: 'POST' })
export const revokeDay = (topic, day) => request(`/api/review/${day}?${q(topic)}`, { method: 'DELETE' })

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

export const getTopics = () => request('/api/topics')
export const addTopic = (topic) => request('/api/topics', json('POST', topic))
export const deleteTopic = (id) => request(`/api/topics/${encodeURIComponent(id)}`, { method: 'DELETE' })
export const getIssues = (topic) => request(`/api/issues?${q(topic)}`)
export const getIssue = (topic, day) => request(`/api/issues/${day}?${q(topic)}`)
export const getMe = () => request('/auth/me').catch(() => ({}))
export const paste = (topic, day, kind, text, title = '') =>
  request(`/api/issues/${day}/paste?${q(topic)}`, json('POST', { kind, text, title }))
export const deleteDay = (topic, day) => request(`/api/issues/${day}?${q(topic)}`, { method: 'DELETE' })
export const deleteFile = (topic, day, kind, name) =>
  request(`/api/issues/${day}/${kind}/${encodeURIComponent(name)}?${q(topic)}`, { method: 'DELETE' })

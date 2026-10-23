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

export const getIssues = () => request('/api/issues')
export const getIssue = (day) => request(`/api/issues/${day}`)
export const getMe = () => request('/auth/me').catch(() => ({}))
export const paste = (day, kind, text, title = '') =>
  request(`/api/issues/${day}/paste`, json('POST', { kind, text, title }))
export const deleteDay = (day) => request(`/api/issues/${day}`, { method: 'DELETE' })
export const deleteFile = (day, kind, name) =>
  request(`/api/issues/${day}/${kind}/${encodeURIComponent(name)}`, { method: 'DELETE' })

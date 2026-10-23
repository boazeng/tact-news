// תאריכים בעברית. התאריך מגיע כ-YYYY-MM-DD; בונים אותו בצהריים כדי שאזור זמן לא יזיז יום.
const parse = (day) => new Date(`${day}T12:00:00`)

export const longDate = (day) =>
  parse(day).toLocaleDateString('he-IL', { day: 'numeric', month: 'long', year: 'numeric' })

export const weekday = (day) => parse(day).toLocaleDateString('he-IL', { weekday: 'long' })

export const shortWeekday = (day) =>
  parse(day).toLocaleDateString('he-IL', { weekday: 'short' }).replace('יום ', '')

export const dayMonth = (day) => {
  const [, m, d] = day.split('-')
  return `${Number(d)}.${Number(m)}`
}

export function todayIL() {
  // en-CA נותן YYYY-MM-DD
  return new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Jerusalem' })
}

export function formatDuration(sec) {
  if (!sec || !isFinite(sec)) return ''
  const s = Math.round(sec)
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const r = String(s % 60).padStart(2, '0')
  return h ? `${h}:${String(m).padStart(2, '0')}:${r}` : `${m}:${r}`
}

export const minutes = (sec) => Math.round((sec || 0) / 60)

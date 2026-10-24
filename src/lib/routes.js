// כתובות: /  → תחום ברירת המחדל, היום, ניוזלטר
//          /<topic>[/<date>[/<tab>]]  ·  /d/<date> (כתובות ישנות)  ·  /admin
export const TABS = [
  { id: 'newsletter', label: 'ניוזלטר' },
  { id: 'podcasts', label: 'פודקאסטים' },
  { id: 'youtube', label: 'YouTube' },
  { id: 'guides', label: 'מדריכים' },
]
const TAB_IDS = TABS.map((t) => t.id)
const DATE = /^\d{4}-\d{2}-\d{2}$/

export function parse(path) {
  const seg = path.split('/').filter(Boolean).map(decodeURIComponent)
  if (seg[0] === 'admin') return { page: 'admin' }
  if (seg[0] === 'd' && DATE.test(seg[1] || '')) return { page: 'day', date: seg[1] }
  if (!seg.length) return { page: 'day' }
  const [topic, date, tab] = seg
  return {
    page: 'day',
    topic,
    date: DATE.test(date || '') ? date : undefined,
    tab: TAB_IDS.includes(tab) ? tab : undefined,
  }
}

export const dayPath = (topic, date, tab = 'newsletter') =>
  `/${topic}/${date}${tab && tab !== 'newsletter' ? `/${tab}` : ''}`

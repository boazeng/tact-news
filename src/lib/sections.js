// צבע לכל קטגוריה — לפי מילות מפתח בשם, כמו בניוזלטר. אפשר לעקוף עם "color" ב-JSON.
const RULES = [
  ['ai', ['בינה', 'AI', 'מלאכותית']],
  ['cyber', ['סייבר', 'אבטחה']],
  ['biz', ['ביג טק', 'עסקים', 'כלכלה']],
  ['chips', ['שבבים', 'חומרה']],
  ['startup', ['סטארטאפ', 'הייטק', 'ישראל']],
]
const SPARE = ['teal', 'rose', 'slate']

export function sectionTone(name = '', index = 0) {
  for (const [tone, words] of RULES) {
    if (words.some((w) => name.includes(w))) return tone
  }
  return SPARE[index % SPARE.length]
}

export function sourceLabel(item) {
  if (item.source_name) return item.source_name
  try {
    return new URL(item.source_url).hostname.replace(/^www\./, '')
  } catch {
    return 'למקור'
  }
}

export const slug = (si, ii) => `s${si}-${ii}`

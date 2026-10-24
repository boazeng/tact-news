// הדגשות בטקסט פשוט: **מודגש** ו-==מסומן==. נשמר כטקסט (גרוק קורא אותו כך), ומוצג באתר מעוצב.
// אין כאן HTML — רק פיצול לחלקים, כך שאין סכנת הזרקה.
const MARK = /(\*\*[^*\n]+\*\*|==[^=\n]+==)/g

export function renderMarks(text) {
  return String(text || '').split(MARK).map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**') && part.length > 4) {
      return <strong key={i}>{part.slice(2, -2)}</strong>
    }
    if (part.startsWith('==') && part.endsWith('==') && part.length > 4) {
      return <mark key={i}>{part.slice(2, -2)}</mark>
    }
    return part
  })
}

// עוטף את הטקסט המסומן בתיבה בסימן (או מסיר אם כבר עטוף). מחזיר [טקסט חדש, תחילת בחירה, סוף בחירה].
export function toggleWrap(value, start, end, mark) {
  const sel = value.slice(start, end)
  const before = value.slice(0, start)
  const after = value.slice(end)
  if (before.endsWith(mark) && after.startsWith(mark)) {
    return [before.slice(0, -mark.length) + sel + after.slice(mark.length), start - mark.length, end - mark.length]
  }
  const text = sel || 'טקסט'
  return [before + mark + text + mark + after, start + mark.length, start + mark.length + text.length]
}

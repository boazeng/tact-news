import { useState } from 'react'
import { deleteDay } from '../../lib/api.js'
import { dayMonth, shortWeekday } from '../../lib/dates.js'
import { dayPath } from '../../lib/routes.js'

// כל הימים שבאתר. מחיקה בשתי לחיצות (בלי חלון אישור של הדפדפן).
export default function DaysTable({ topic, issues, onChanged, navigate, onPick }) {
  const [arming, setArming] = useState(null)

  const del = async (day) => {
    if (arming !== day) return setArming(day)
    setArming(null)
    await deleteDay(topic, day).catch(() => {})
    onChanged()
  }

  return (
    <section className="card">
      <h2 className="card-title">הימים באתר</h2>
      <p className="kind-hint">כל יום נמחק אוטומטית שבועיים אחרי התאריך שלו.</p>
      {issues.length === 0 ? (
        <p className="empty">עוד אין גיליונות.</p>
      ) : (
        <table className="days-table">
          <thead>
            <tr><th>יום</th><th>ידיעות</th><th>פודקאסטים</th><th>YouTube</th><th>נמחק ב-</th><th /></tr>
          </thead>
          <tbody>
            {issues.map((it) => (
              <tr key={it.date}>
                <td>
                  <a href={dayPath(topic, it.date)} onClick={(e) => { e.preventDefault(); navigate(dayPath(topic, it.date)) }}>
                    {shortWeekday(it.date)} {dayMonth(it.date)}
                  </a>
                  {!it.newsletter && <span className="tag-warn">אין ניוזלטר</span>}
                  {it.newsletter && it.newsletter !== 'json' && <span className="tag">{it.newsletter}</span>}
                </td>
                <td>{it.items || '–'}</td>
                <td>{it.podcasts || '–'}</td>
                <td>{it.youtube || '–'}</td>
                <td>{dayMonth(it.expires)}</td>
                <td className="row-actions">
                  <button className="link-btn" onClick={() => onPick(it.date)}>עריכה</button>
                  <button className={`link-btn danger${arming === it.date ? ' armed' : ''}`}
                    onClick={() => del(it.date)} onBlur={() => setArming(null)}>
                    {arming === it.date ? 'בטוח? למחוק' : 'מחיקה'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}

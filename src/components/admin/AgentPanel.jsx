import { useCallback, useEffect, useState } from 'react'
import { getAgent, runAgent } from '../../lib/api.js'

const fmtTime = (iso) => (iso ? iso.slice(11, 16) : '')
const fmtDay = (iso) => (iso ? `${iso.slice(8, 10)}.${iso.slice(5, 7)}` : '')

// הניוזלטר של Claude — גיליון הבוקר ועדכון הערב (backend/evening_agent.py)
export default function AgentPanel({ topics, onChanged }) {
  const [info, setInfo] = useState(null)
  const [topic, setTopic] = useState('')
  const [msg, setMsg] = useState('')
  const names = Object.fromEntries(topics.map((t) => [t.id, t.name]))

  const load = useCallback(() => getAgent().then(setInfo).catch((e) => setMsg(e.message)), [])
  useEffect(() => { load() }, [load])
  // בזמן ריצה — רענון כל 10 שניות, ובסוף רענון הגיליונות
  useEffect(() => {
    if (!info?.running) return undefined
    const id = setInterval(() => getAgent().then((d) => {
      setInfo(d)
      if (!d.running) onChanged()
    }), 10000)
    return () => clearInterval(id)
  }, [info?.running, onChanged])

  const start = async () => {
    setMsg('')
    try {
      await runAgent(topic)
      setMsg('הריצה התחילה — לוקח כמה דקות לכל תחום. לפני 14:00 = גיליון בוקר מלא, אחרי = עדכון ערב')
      load()
    } catch (e) {
      setMsg(e.message)
    }
  }

  if (!info) return null
  return (
    <section className="card">
      <h2 className="card-title">הניוזלטר של Claude</h2>
      <p className="kind-hint">
        כל יום ב-{info.run_times.join(' וב-')} נאספות מהפידים של המקורות (שדה המקורות בכל תחום) הידיעות האחרונות, ו-Claude בוחר את החשובות וכותב אותן בעברית.
        בבוקר הוא בונה את הגיליון המלא, ובערב מוסיף לראש הקטגוריות עם הסימון 🆕. את "מעקב פייסבוק" מוסיף גרוק. מודל: {info.model}.
        {!info.enabled && <strong> כבוי — אין ANTHROPIC_API_KEY בשרת.</strong>}
      </p>

      <div className="paste-row">
        <select value={topic} onChange={(e) => setTopic(e.target.value)} disabled={info.running}>
          <option value="">כל התחומים</option>
          {topics.filter((t) => t.tabs.includes('newsletter')).map((t) => (
            <option key={t.id} value={t.id}>{t.name}</option>
          ))}
        </select>
        <button className="btn primary" onClick={start} disabled={info.running || !info.enabled}>
          {info.running ? 'רץ עכשיו…' : 'הרץ עכשיו'}
        </button>
        {msg && <span className="paste-msg">{msg}</span>}
      </div>

      {info.runs.length > 0 && (
        <table className="days-table">
          <thead>
            <tr><th>מתי</th><th>הפעלה</th><th>נוספו</th><th>עלות (הערכה)</th></tr>
          </thead>
          <tbody>
            {info.runs.map((r) => (
              <tr key={r.id}>
                <td>{fmtDay(r.started)} <span dir="ltr">{fmtTime(r.started)}</span>{!r.finished && ' · רץ'}</td>
                <td>{r.trigger === 'schedule' ? 'מתוזמן' : 'ידני'}{r.kind === 'base' ? ' · בוקר' : r.kind === 'update' ? ' · ערב' : ''}</td>
                <td>
                  {r.topics.map((t) => (
                    <div key={t.topic} title={t.error || t.skipped || t.note || ''}>
                      {names[t.topic] || t.topic}: {t.error ? `שגיאה — ${t.error}` : t.skipped ? 'דולג' : `+${t.added}${t.candidates != null ? ` מתוך ${t.candidates} בפידים` : ''}`}
                    </div>
                  ))}
                </td>
                <td dir="ltr">{r.cost_usd != null ? `$${r.cost_usd}` : ''}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}

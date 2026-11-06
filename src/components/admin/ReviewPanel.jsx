import { useCallback, useEffect, useState } from 'react'
import { approveDay, getReview, previewDay, revokeDay } from '../../lib/api.js'
import { dayMonth, shortWeekday } from '../../lib/dates.js'

const STATUS = {
  pending: 'ממתין לאישור',
  changed: 'אושר · יש שינויים שממתינים',
  approved: 'מאושר',
  empty: 'ריק',
}

// תחומים עם אישור לפני פרסום (Longeviora — backend/review.py). הציבור רואה רק את הגרסה שאושרה.
export default function ReviewPanel({ onChanged }) {
  const [data, setData] = useState(null)
  const [open, setOpen] = useState(null)   // {topic, day, info}
  const [msg, setMsg] = useState('')

  const load = useCallback(() => getReview().then(setData).catch((e) => setMsg(e.message)), [])
  useEffect(() => { load() }, [load])

  const preview = async (topic, day) => {
    if (open?.topic === topic && open?.day === day) return setOpen(null)
    setMsg('')
    try {
      setOpen({ topic, day, info: await previewDay(topic, day) })
    } catch (e) {
      setMsg(e.message)
    }
  }

  const act = async (fn, topic, day) => {
    setMsg('')
    try {
      await fn(topic, day)
      setOpen(null)
      load()
      onChanged()
    } catch (e) {
      setMsg(e.message)
    }
  }

  if (!data?.topics?.length) return null
  return (
    <section className="card">
      <h2 className="card-title">אישור לפני פרסום — Longeviora</h2>
      <p className="kind-hint">
        התחומים האלה לא מופיעים באתר. מה ש-Claude וגרוק כותבים בהם מגיע לאפליקציה רק אחרי אישור של היום.
        שינוי אחרי האישור (עדכון ערב, תיקון של גרוק) ממתין לאישור חוזר — עד אז האפליקציה מציגה את הגרסה שאושרה.
      </p>
      {msg && <p className="paste-msg">{msg}</p>}
      <table className="days-table">
        <thead>
          <tr><th>תחום</th><th>יום</th><th>מצב</th><th>ידיעות</th><th>מאמרים</th><th /></tr>
        </thead>
        <tbody>
          {data.topics.flatMap((t) => t.days.filter((d) => d.status !== 'empty').map((d) => (
            <ReviewRow key={`${t.id}/${d.date}`} topic={t} d={d} open={open} onPreview={preview}
              onApprove={() => act(approveDay, t.id, d.date)} onRevoke={() => act(revokeDay, t.id, d.date)} />
          )))}
        </tbody>
      </table>
    </section>
  )
}

function ReviewRow({ topic, d, open, onPreview, onApprove, onRevoke }) {
  const isOpen = open?.topic === topic.id && open?.day === d.date
  return (
    <>
      <tr>
        <td>{topic.name} <span className="tag">{topic.lang}</span></td>
        <td>{shortWeekday(d.date)} {dayMonth(d.date)}</td>
        <td>{d.status === 'approved' ? STATUS.approved : <span className="tag-warn">{STATUS[d.status]}</span>}</td>
        <td>{d.live.items || '–'}</td>
        <td>{d.live.papers || '–'}</td>
        <td className="row-actions">
          <button className="link-btn" onClick={() => onPreview(topic.id, d.date)}>{isOpen ? 'סגירה' : 'תצוגה'}</button>
          {d.status !== 'approved' && <button className="link-btn" onClick={onApprove}>אישור</button>}
          {d.status !== 'pending' && <button className="link-btn danger" onClick={onRevoke}>ביטול אישור</button>}
        </td>
      </tr>
      {isOpen && (
        <tr>
          <td colSpan={6}><Preview info={open.info} /></td>
        </tr>
      )}
    </>
  )
}

function Preview({ info }) {
  const sections = info.newsletter?.data?.sections || []
  const lists = [['מאמרים', info.papers], ['פודקאסטים', info.links], ['YouTube', info.youtube]]
  return (
    <div dir="auto">
      {sections.map((s) => (
        <div key={s.name}>
          <strong>{s.name}</strong>
          <ul>
            {s.items.map((it, i) => (
              <li key={i}>
                <a href={it.source_url} target="_blank" rel="noreferrer">{it.title}</a>
                {it.source_name && ` · ${it.source_name}`}
                {it.summary && <div className="kind-hint">{it.summary}</div>}
              </li>
            ))}
          </ul>
        </div>
      ))}
      {lists.filter(([, items]) => items?.length).map(([name, items]) => (
        <div key={name}>
          <strong>{name}</strong>
          <ul>
            {items.map((it, i) => <li key={i}><a href={it.url} target="_blank" rel="noreferrer">{it.title}</a></li>)}
          </ul>
        </div>
      ))}
      {info.podcasts?.length > 0 && <p>קבצי אודיו: {info.podcasts.map((p) => p.title).join(' · ')}</p>}
    </div>
  )
}

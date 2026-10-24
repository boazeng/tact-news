import { useRef, useState } from 'react'
import { renderMarks, toggleWrap } from '../../lib/marks.jsx'

export const SWATCHES = ['#6d28d9', '#0b72b9', '#15803d', '#c62828', '#a8500a', '#0f766e', '#be185d', '#475569']

// טופס תחום — להוספה (עם מזהה) ולעריכה (המזהה קבוע). התיאור תומך בהדגשה ובסימון.
export default function TopicForm({ initial, isNew, onSubmit, onCancel, submitLabel }) {
  const [form, setForm] = useState(() => ({
    id: '', name: '', color: SWATCHES[2], description: '', ...initial,
  }))
  const [msg, setMsg] = useState('')
  const [busy, setBusy] = useState(false)
  const area = useRef(null)
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  const wrap = (mark) => {
    const el = area.current
    const [value, s, e] = toggleWrap(form.description, el.selectionStart, el.selectionEnd, mark)
    setForm({ ...form, description: value })
    requestAnimationFrame(() => { el.focus(); el.setSelectionRange(s, e) })
  }

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setMsg('')
    try {
      await onSubmit(form)
      if (isNew) setForm({ id: '', name: '', color: SWATCHES[2], description: '' })
    } catch (err) {
      setMsg(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="topic-form" onSubmit={submit}>
      <div className="topic-fields">
        <label>
          <span>שם</span>
          <input value={form.name} onChange={set('name')} placeholder="ספורט" maxLength={40} required />
        </label>
        {isNew ? (
          <label>
            <span>מזהה (באנגלית, מופיע בכתובת)</span>
            <input value={form.id} onChange={(e) => setForm({ ...form, id: e.target.value.toLowerCase() })}
              placeholder="sport" dir="ltr" pattern="[a-z][a-z0-9-]{1,23}" required />
          </label>
        ) : (
          <label>
            <span>מזהה (לא ניתן לשינוי)</span>
            <input value={form.id} dir="ltr" disabled />
          </label>
        )}
      </div>

      <div className="topic-desc-field">
        <div className="rich-head">
          <span>מה לכסות (ההוראה לגרוק)</span>
          <span className="rich-tools">
            <button type="button" className="rich-btn" onClick={() => wrap('**')} title="הדגשה — חשוב">
              <strong>B</strong> הדגשה
            </button>
            <button type="button" className="rich-btn" onClick={() => wrap('==')} title="סימון — עדיפות עליונה">
              <mark>סימון</mark>
            </button>
          </span>
        </div>
        <textarea ref={area} value={form.description} onChange={set('description')} rows={3} maxLength={1500}
          placeholder="כדורגל וכדורסל בארץ ובעולם, ליגת האלופות, NBA, אולימפיאדה" />
        {/[*=]{2}/.test(form.description) && (
          <p className="rich-preview">{renderMarks(form.description)}</p>
        )}
      </div>

      <div className="swatches" role="radiogroup" aria-label="צבע">
        {SWATCHES.map((c) => (
          <button type="button" key={c} role="radio" aria-checked={form.color === c} aria-label={c}
            className={`swatch${form.color === c ? ' is-on' : ''}`} style={{ background: c }}
            onClick={() => setForm({ ...form, color: c })} />
        ))}
        <label className="swatch-custom" title="צבע אחר">
          <input type="color" value={form.color} onChange={set('color')} aria-label="צבע אחר" />
        </label>
      </div>

      <div className="paste-row">
        <button className="btn primary" type="submit" disabled={busy}>{submitLabel}</button>
        {onCancel && <button className="btn" type="button" onClick={onCancel}>ביטול</button>}
        {msg && <span className="paste-msg">{msg}</span>}
      </div>
    </form>
  )
}

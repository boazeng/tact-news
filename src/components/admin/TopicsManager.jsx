import { useState } from 'react'
import { addTopic, deleteTopic } from '../../lib/api.js'

const SWATCHES = ['#6d28d9', '#0b72b9', '#15803d', '#c62828', '#a8500a', '#0f766e', '#be185d', '#475569']

// תחומי על: הוספה ומחיקה. תחום חדש מופיע מיד באתר ובאפליקציה, וגרוק מפיק לו תוכן לפי התיאור.
export default function TopicsManager({ topics, onChanged }) {
  const [form, setForm] = useState({ id: '', name: '', color: SWATCHES[2], description: '' })
  const [msg, setMsg] = useState('')
  const [arming, setArming] = useState(null)
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  const add = async (e) => {
    e.preventDefault()
    setMsg('')
    try {
      await addTopic(form)
      setMsg(`התחום "${form.name}" נוסף ✓`)
      setForm({ id: '', name: '', color: SWATCHES[2], description: '' })
      onChanged()
    } catch (err) {
      setMsg(err.message)
    }
  }

  const remove = async (t) => {
    if (arming !== t.id) return setArming(t.id)
    setArming(null)
    try {
      await deleteTopic(t.id)
      setMsg(`התחום "${t.name}" נמחק`)
      onChanged()
    } catch (err) {
      setMsg(err.message)
    }
  }

  return (
    <section className="card">
      <h2 className="card-title">תחומי על</h2>
      <p className="kind-hint">
        הראשון ברשימה הוא ברירת המחדל. גרוק קורא את הרשימה כל בוקר ומפיק לכל תחום יום מלא לפי התיאור שלו.
      </p>

      <ul className="topics-list">
        {topics.map((t) => (
          <li key={t.id} className="topic-row">
            <span className="topic-dot" style={{ background: t.color }} aria-hidden="true" />
            <div className="topic-info">
              <div className="topic-line">
                <span className="topic-name">{t.name}</span>
                <code className="topic-id" dir="ltr">/{t.id}</code>
                {t.default && <span className="tag">ברירת מחדל</span>}
              </div>
              {t.description && <p className="topic-desc">{t.description}</p>}
            </div>
            {topics.length > 1 && (
              <button
                className={`link-btn danger${arming === t.id ? ' armed' : ''}`}
                onClick={() => remove(t)} onBlur={() => setArming(null)}
              >
                {arming === t.id ? 'למחוק את התחום וכל הימים שלו?' : 'מחיקה'}
              </button>
            )}
          </li>
        ))}
      </ul>

      <form className="topic-form" onSubmit={add}>
        <h3 className="kind-title">תחום חדש</h3>
        <div className="topic-fields">
          <label>
            <span>שם</span>
            <input value={form.name} onChange={set('name')} placeholder="ספורט" maxLength={40} required />
          </label>
          <label>
            <span>מזהה (באנגלית, מופיע בכתובת)</span>
            <input value={form.id} onChange={(e) => setForm({ ...form, id: e.target.value.toLowerCase() })}
              placeholder="sport" dir="ltr" pattern="[a-z][a-z0-9-]{1,23}" required />
          </label>
        </div>
        <label className="topic-desc-field">
          <span>מה לכסות (ההוראה לגרוק)</span>
          <textarea value={form.description} onChange={set('description')} rows={2} maxLength={600}
            placeholder="כדורגל וכדורסל בארץ ובעולם, ליגת האלופות, NBA, אולימפיאדה" />
        </label>
        <div className="swatches" role="radiogroup" aria-label="צבע">
          {SWATCHES.map((c) => (
            <button type="button" key={c} role="radio" aria-checked={form.color === c} aria-label={c}
              className={`swatch${form.color === c ? ' is-on' : ''}`} style={{ background: c }}
              onClick={() => setForm({ ...form, color: c })} />
          ))}
        </div>
        <div className="paste-row">
          <button className="btn primary" type="submit">הוספת תחום</button>
          {msg && <span className="paste-msg">{msg}</span>}
        </div>
      </form>
    </section>
  )
}

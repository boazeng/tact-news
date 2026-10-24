import { useState } from 'react'
import { addTopic, deleteTopic, editTopic, orderTopics } from '../../lib/api.js'
import { renderMarks } from '../../lib/marks.jsx'
import TopicForm from './TopicForm.jsx'

// תחומי על: סדר, עריכה, הוספה ומחיקה. כל שינוי מופיע מיד באתר ובאפליקציה,
// וגרוק מפיק לכל תחום תוכן לפי התיאור שלו.
export default function TopicsManager({ topics, onChanged }) {
  const [editing, setEditing] = useState(null)
  const [arming, setArming] = useState(null)
  const [msg, setMsg] = useState('')

  const run = async (fn, done) => {
    setMsg('')
    try {
      await fn()
      if (done) setMsg(done)
      onChanged()
    } catch (err) {
      setMsg(err.message)
    }
  }

  const move = (i, delta) => {
    const ids = topics.map((t) => t.id)
    const j = i + delta
    ;[ids[i], ids[j]] = [ids[j], ids[i]]
    run(() => orderTopics(ids))
  }

  const remove = (t) => {
    if (arming !== t.id) return setArming(t.id)
    setArming(null)
    run(() => deleteTopic(t.id), `התחום "${t.name}" נמחק`)
  }

  return (
    <section className="card">
      <h2 className="card-title">תחומי על</h2>
      <p className="kind-hint">
        הראשון ברשימה הוא ברירת המחדל — האתר נפתח עליו. גרוק קורא את הרשימה כל בוקר ומפיק לכל תחום יום מלא לפי התיאור.
      </p>

      <ul className="topics-list">
        {topics.map((t, i) => (
          <li key={t.id} className={`topic-row${editing === t.id ? ' is-editing' : ''}`}>
            {editing === t.id ? (
              <TopicForm
                initial={{ id: t.id, name: t.name, color: t.color, description: t.description || '' }}
                submitLabel="שמירה"
                onCancel={() => setEditing(null)}
                onSubmit={async (f) => {
                  await editTopic(t.id, { name: f.name, color: f.color, description: f.description })
                  setEditing(null)
                  setMsg(`התחום "${f.name}" עודכן ✓`)
                  onChanged()
                }}
              />
            ) : (
              <>
                <span className="order-btns">
                  <button className="x-btn" disabled={i === 0} onClick={() => move(i, -1)}
                    aria-label={`העבר את ${t.name} למעלה`} title="למעלה">▲</button>
                  <button className="x-btn" disabled={i === topics.length - 1} onClick={() => move(i, 1)}
                    aria-label={`העבר את ${t.name} למטה`} title="למטה">▼</button>
                </span>
                <span className="topic-dot" style={{ background: t.color }} aria-hidden="true" />
                <div className="topic-info">
                  <div className="topic-line">
                    <span className="topic-name">{t.name}</span>
                    <code className="topic-id" dir="ltr">/{t.id}</code>
                    {t.default && <span className="tag">ברירת מחדל</span>}
                  </div>
                  {t.description && <p className="topic-desc">{renderMarks(t.description)}</p>}
                </div>
                <span className="row-actions">
                  <button className="link-btn" onClick={() => { setEditing(t.id); setArming(null) }}>עריכה</button>
                  {topics.length > 1 && (
                    <button className={`link-btn danger${arming === t.id ? ' armed' : ''}`}
                      onClick={() => remove(t)} onBlur={() => setArming(null)}>
                      {arming === t.id ? 'למחוק את התחום וכל הימים שלו?' : 'מחיקה'}
                    </button>
                  )}
                </span>
              </>
            )}
          </li>
        ))}
      </ul>
      {msg && <p className="paste-msg topics-msg">{msg}</p>}

      <div className="topic-new">
        <h3 className="kind-title">תחום חדש</h3>
        <TopicForm
          isNew submitLabel="הוספת תחום"
          onSubmit={async (f) => {
            await addTopic(f)
            setMsg(`התחום "${f.name}" נוסף ✓`)
            onChanged()
          }}
        />
      </div>
    </section>
  )
}

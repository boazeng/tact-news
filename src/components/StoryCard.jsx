import { useState } from 'react'
import { sourceLabel } from '../lib/sections.js'

// ידיעה: כותרת + תקציר; "הרחבה" פותחת את הפירוט במקום (בלי לקפוץ לסוף הדף כמו ב-PDF)
export default function StoryCard({ item, id, lead }) {
  const [open, setOpen] = useState(false)
  const paragraphs = String(item.details || '').split(/\n+/).filter(Boolean)

  return (
    <article id={id} className={`story${lead ? ' story-lead' : ''}${open ? ' is-open' : ''}`}>
      <h3 className="story-title">{item.title}</h3>
      {item.summary && <p className="story-summary">{item.summary}</p>}
      {open && (
        <div className="story-details">
          {paragraphs.map((p, i) => <p key={i}>{p}</p>)}
        </div>
      )}
      <footer className="story-foot">
        {paragraphs.length > 0 && (
          <button className="story-more" onClick={() => setOpen(!open)} aria-expanded={open}>
            {open ? 'סגירה' : 'לקריאה המורחבת'}
            <span className="chev" aria-hidden="true">⌄</span>
          </button>
        )}
        {item.source_url && (
          <a className="story-src" href={item.source_url} target="_blank" rel="noopener noreferrer">
            {sourceLabel(item)} <span aria-hidden="true">↗</span>
          </a>
        )}
      </footer>
    </article>
  )
}

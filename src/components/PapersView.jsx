import { useState } from 'react'

const hostOf = (url) => {
  try { return new URL(url).hostname.replace(/^www\./, '') } catch { return '' }
}

// לשונית "מאמרים": מאמרים אקדמיים עדכניים — כותרת במקור, תקציר והרחבה בעברית, קישור למאמר ול-PDF
export default function PapersView({ papers }) {
  if (!papers.length) return <p className="empty">אין מאמרים ליום הזה.</p>
  return (
    <div className="papers">
      {papers.map((p) => <Paper key={p.url} p={p} />)}
    </div>
  )
}

function Paper({ p }) {
  const [open, setOpen] = useState(false)
  const paragraphs = String(p.details || '').split(/\n+/).filter(Boolean)
  const meta = [p.venue || hostOf(p.url), p.published].filter(Boolean)

  return (
    <article className={`paper${open ? ' is-open' : ''}`}>
      <div className="paper-meta">
        {meta.map((m, i) => <span key={i}>{m}</span>)}
      </div>
      <h3 className="paper-title" dir="auto">
        <a href={p.url} target="_blank" rel="noopener noreferrer">{p.title}</a>
      </h3>
      {p.authors && <p className="paper-authors" dir="auto">{p.authors}</p>}
      {p.summary && <p className="paper-summary">{p.summary}</p>}
      {open && (
        <div className="paper-details">
          {paragraphs.map((t, i) => <p key={i}>{t}</p>)}
        </div>
      )}
      <footer className="paper-foot">
        {paragraphs.length > 0 && (
          <button className="story-more" onClick={() => setOpen(!open)} aria-expanded={open}>
            {open ? 'סגירה' : 'למה זה חשוב'}
            <span className="chev" aria-hidden="true">⌄</span>
          </button>
        )}
        <span className="paper-links">
          <a href={p.url} target="_blank" rel="noopener noreferrer">למאמר ↗</a>
          {p.pdf_url && <a href={p.pdf_url} target="_blank" rel="noopener noreferrer">PDF ↗</a>}
        </span>
      </footer>
    </article>
  )
}

import { useMemo, useState } from 'react'
import { sectionTone, slug } from '../lib/sections.js'
import StoryCard from './StoryCard.jsx'

const match = (item, q) =>
  [item.title, item.summary, item.details, item.source_name]
    .some((t) => String(t || '').toLowerCase().includes(q))

// לשונית "ניוזלטר": קטגוריות + חיפוש + ידיעות. HTML/PDF מוצגים כמו שהם.
export default function NewsletterView({ issue }) {
  const [query, setQuery] = useState('')
  const data = issue.newsletter?.kind === 'json' ? issue.newsletter.data : null

  const sections = useMemo(() => {
    const q = query.trim().toLowerCase()
    return (data?.sections || []).map((s, si) => ({
      ...s,
      si,
      tone: sectionTone(s.name, si),
      shown: s.items.map((item, ii) => ({ item, ii })).filter(({ item }) => !q || match(item, q)),
    }))
  }, [data, query])

  if (!issue.newsletter) return <p className="empty">הניוזלטר של היום עוד לא עלה.</p>
  if (!data) return <RawNewsletter nl={issue.newsletter} />

  const found = sections.reduce((n, s) => n + s.shown.length, 0)
  return (
    <>
      <div className="sectnav">
        <div className="chips">
          {sections.map((s) => (
            <a key={s.si} href={`#sec-${s.si}`} className={`chip tone-${s.tone}`}
              style={s.color ? { '--tone': s.color } : undefined}>
              {s.name} <span className="chip-n">{query ? s.shown.length : s.items.length}</span>
            </a>
          ))}
        </div>
        <input
          className="search" type="search" value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="חיפוש בגיליון…" aria-label="חיפוש בגיליון"
        />
      </div>

      {query && <p className="search-note">{found ? `${found} תוצאות` : 'אין תוצאות'}</p>}

      {sections.filter((s) => s.shown.length).map((s) => (
        <section key={s.si} id={`sec-${s.si}`} className={`section tone-${s.tone}`}
          style={s.color ? { '--tone': s.color } : undefined}>
          <h2 className="section-title">
            {s.name}
            <span className="section-n">{s.shown.length}</span>
          </h2>
          <div className="stories">
            {s.shown.map(({ item, ii }) => (
              <StoryCard key={ii} item={item} id={slug(s.si, ii)} lead={!query && s.si === 0 && ii === 0} />
            ))}
          </div>
        </section>
      ))}

      {data.closing && <p className="closing">{data.closing}</p>}
    </>
  )
}

// ניוזלטר שהועלה כ-HTML או PDF — מוצג כמו שהוא
function RawNewsletter({ nl }) {
  if (nl.kind === 'json') return <p className="empty">קובץ ה-JSON של היום פגום.</p>
  return (
    <div className="raw">
      <div className="raw-bar">
        <span>הניוזלטר המקורי ({nl.kind.toUpperCase()})</span>
        <a className="link-btn" href={nl.url} target="_blank" rel="noopener noreferrer">פתיחה בחלון ↗</a>
      </div>
      <iframe
        className="raw-frame" src={nl.url} title="ניוזלטר"
        sandbox={nl.kind === 'html' ? 'allow-popups allow-popups-to-escape-sandbox' : undefined}
      />
    </div>
  )
}

import { useEffect, useMemo, useState } from 'react'
import { getIssue } from '../lib/api.js'
import { dayMonth, longDate, weekday } from '../lib/dates.js'
import { sectionTone, slug } from '../lib/sections.js'
import Listen from '../components/Listen.jsx'
import Materials from '../components/Materials.jsx'
import StoryCard from '../components/StoryCard.jsx'

const match = (item, q) =>
  [item.title, item.summary, item.details, item.source_name]
    .some((t) => String(t || '').toLowerCase().includes(q))

export default function DayPage({ date, today, latest, navigate }) {
  const [issue, setIssue] = useState(null)
  const [error, setError] = useState('')
  const [query, setQuery] = useState('')

  useEffect(() => {
    let alive = true
    setIssue(null)
    setError('')
    setQuery('')
    getIssue(date)
      .then((d) => alive && setIssue(d))
      .catch((e) => alive && setError(e.status === 404 ? 'missing' : e.message))
    window.scrollTo(0, 0)
    return () => { alive = false }
  }, [date])

  // הגיליון של היום עוד לא עלה → בודקים שוב כל 3 דקות, והוא מופיע בלי רענון
  useEffect(() => {
    if (error !== 'missing' || date !== today) return
    const t = setInterval(() => {
      getIssue(date).then((d) => { setIssue(d); setError('') }).catch(() => {})
    }, 3 * 60 * 1000)
    return () => clearInterval(t)
  }, [error, date, today])

  const data = issue?.newsletter?.kind === 'json' ? issue.newsletter.data : null
  const sections = useMemo(() => {
    const q = query.trim().toLowerCase()
    return (data?.sections || []).map((s, si) => ({
      ...s,
      si,
      tone: sectionTone(s.name, si),
      shown: s.items.map((item, ii) => ({ item, ii })).filter(({ item }) => !q || match(item, q)),
    }))
  }, [data, query])

  if (error === 'missing') {
    return <Missing date={date} isToday={date === today} latest={latest} navigate={navigate} />
  }
  if (error) return <div className="page"><p className="empty">{error}</p></div>
  if (!issue) return <div className="page"><div className="loading" aria-label="טוען" /></div>

  const count = sections.reduce((n, s) => n + s.items.length, 0)
  const found = sections.reduce((n, s) => n + s.shown.length, 0)

  return (
    <div className="page">
      <header className="masthead">
        <span className="kicker">{weekday(date)} · גיליון יומי</span>
        <h1 className="mast-date">{longDate(date)}</h1>
        <p className="mast-meta">
          {data?.title && <span>{data.title}</span>}
          {count > 0 && <span>{count} ידיעות</span>}
          {sections.length > 0 && <span>{sections.length} קטגוריות</span>}
          <span className="mast-exp">נשמר עד {dayMonth(issue.expires)}</span>
        </p>
      </header>

      {(issue.podcasts.length > 0 || issue.links?.length > 0) && (
        <Listen date={date} podcasts={issue.podcasts} links={issue.links || []} />
      )}

      {data && (
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
                  <StoryCard key={ii} item={item} id={slug(s.si, ii)}
                    lead={!query && s.si === 0 && ii === 0} />
                ))}
              </div>
            </section>
          ))}

          {data.closing && <p className="closing">{data.closing}</p>}
        </>
      )}

      {issue.newsletter && !data && <RawNewsletter nl={issue.newsletter} />}
      {!issue.newsletter && <p className="empty">הניוזלטר של היום עוד לא עלה.</p>}

      {issue.materials.length > 0 && <Materials materials={issue.materials} />}
    </div>
  )
}

// אין גיליון לתאריך — בדרך כלל היום, לפני שגרוק פרסם
function Missing({ date, isToday, latest, navigate }) {
  const other = latest && latest !== date
  return (
    <div className="page">
      <header className="masthead">
        <span className="kicker">{weekday(date)} · גיליון יומי</span>
        <h1 className="mast-date">{longDate(date)}</h1>
      </header>
      <div className="pending">
        <p className="pending-title">{isToday ? 'הגיליון של היום עוד לא פורסם' : 'אין גיליון לתאריך הזה'}</p>
        {isToday && <p className="pending-sub">הוא יופיע כאן אוטומטית ברגע שיעלה.</p>}
        {other && (
          <button className="btn primary" onClick={() => navigate(`/d/${latest}`)}>
            לגיליון האחרון · {weekday(latest)} {dayMonth(latest)}
          </button>
        )}
        {!latest && <p className="pending-sub">עוד אין גיליונות באתר.</p>}
      </div>
    </div>
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

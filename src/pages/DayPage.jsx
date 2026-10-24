import { useEffect, useState } from 'react'
import { getIssue } from '../lib/api.js'
import { dayMonth, longDate, weekday } from '../lib/dates.js'
import { dayPath, TABS } from '../lib/routes.js'
import Listen from '../components/Listen.jsx'
import Materials from '../components/Materials.jsx'
import NewsletterView from '../components/NewsletterView.jsx'
import YoutubeView from '../components/YoutubeView.jsx'

// יום אחד בתחום אחד: כותרת התאריך + לשוניות (ניוזלטר · פודקאסטים · YouTube · מדריכים)
export default function DayPage({ topic, topicName, date, tab, today, latest, navigate }) {
  const [issue, setIssue] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let alive = true
    setIssue(null)
    setError('')
    getIssue(topic, date)
      .then((d) => alive && setIssue(d))
      .catch((e) => alive && setError(e.status === 404 ? 'missing' : e.message))
    return () => { alive = false }
  }, [topic, date])

  // הגיליון של היום עוד לא עלה → בודקים שוב כל 3 דקות, והוא מופיע בלי רענון
  useEffect(() => {
    if (error !== 'missing' || date !== today) return
    const t = setInterval(() => {
      getIssue(topic, date).then((d) => { setIssue(d); setError('') }).catch(() => {})
    }, 3 * 60 * 1000)
    return () => clearInterval(t)
  }, [error, topic, date, today])

  const head = (
    <header className="masthead">
      <span className="kicker">{weekday(date)} · {topicName}</span>
      <h1 className="mast-date">{longDate(date)}</h1>
      {issue && <MastMeta issue={issue} />}
    </header>
  )

  if (error === 'missing') {
    return (
      <div className="page">
        {head}
        <Missing topic={topic} date={date} isToday={date === today} latest={latest} navigate={navigate} />
      </div>
    )
  }
  if (error) return <div className="page"><p className="empty">{error}</p></div>
  if (!issue) return <div className="page"><div className="loading" aria-label="טוען" /></div>

  const counts = {
    newsletter: itemCount(issue),
    podcasts: issue.podcasts.length + issue.links.length,
    youtube: issue.youtube.length,
    guides: (issue.guides || []).length,
  }

  return (
    <div className="page">
      {head}
      <nav className="tabs" aria-label="לשוניות">
        {TABS.map((t) => (
          <a
            key={t.id}
            href={dayPath(topic, date, t.id)}
            className={`tab${tab === t.id ? ' is-on' : ''}`}
            aria-current={tab === t.id ? 'page' : undefined}
            onClick={(e) => {
              if (e.metaKey || e.ctrlKey) return
              e.preventDefault()
              navigate(dayPath(topic, date, t.id), { keepScroll: true })
            }}
          >
            {t.label}
            {counts[t.id] > 0 && <span className="tab-n">{counts[t.id]}</span>}
          </a>
        ))}
      </nav>

      {tab === 'newsletter' && <NewsletterView issue={issue} />}
      {tab === 'podcasts' && <PodcastsView issue={issue} date={date} />}
      {tab === 'youtube' && <YoutubeView videos={issue.youtube} empty="אין סרטונים ליום הזה." />}
      {tab === 'guides' && <YoutubeView videos={issue.guides || []} empty="אין מדריכים ליום הזה." />}
    </div>
  )
}

const itemCount = (issue) =>
  (issue.newsletter?.data?.sections || []).reduce((n, s) => n + s.items.length, 0)

function MastMeta({ issue }) {
  const data = issue.newsletter?.data
  const count = itemCount(issue)
  return (
    <p className="mast-meta">
      {data?.title && <span>{data.title}</span>}
      {count > 0 && <span>{count} ידיעות</span>}
      <span className="mast-exp">נשמר עד {dayMonth(issue.expires)}</span>
    </p>
  )
}

// לשונית "פודקאסטים": תקציר קולי + פרקים שהועלו + קישורים, וחומר הרקע
function PodcastsView({ issue, date }) {
  const any = issue.podcasts.length + issue.links.length > 0
  return (
    <>
      {any ? <Listen date={date} podcasts={issue.podcasts} links={issue.links} />
        : <p className="empty">אין פודקאסטים ליום הזה.</p>}
      {issue.materials.length > 0 && <Materials materials={issue.materials} />}
    </>
  )
}

// אין שום תוכן לתאריך — בדרך כלל היום, לפני שגרוק פרסם
function Missing({ topic, date, isToday, latest, navigate }) {
  const other = latest && latest !== date
  return (
    <div className="pending">
      <p className="pending-title">{isToday ? 'הגיליון של היום עוד לא פורסם' : 'אין גיליון לתאריך הזה'}</p>
      {isToday && <p className="pending-sub">הוא יופיע כאן אוטומטית ברגע שיעלה.</p>}
      {other && (
        <button className="btn primary" onClick={() => navigate(dayPath(topic, latest))}>
          לגיליון האחרון · {weekday(latest)} {dayMonth(latest)}
        </button>
      )}
      {!latest && <p className="pending-sub">עוד אין גיליונות בתחום הזה.</p>}
    </div>
  )
}

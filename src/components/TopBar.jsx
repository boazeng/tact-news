import { useEffect, useRef, useState } from 'react'
import { SITE_NAME, SITE_TAGLINE } from '../config.js'
import { dayMonth, shortWeekday } from '../lib/dates.js'
import { dayPath } from '../lib/routes.js'

// סרגל עליון: שם האתר · תחום העל · רצועת הימים (עד שבועיים אחורה)
export default function TopBar({ topics, topic, issues, active, tab, navigate }) {
  const strip = useRef(null)

  useEffect(() => {
    const el = strip.current?.querySelector('.is-current')
    el?.scrollIntoView({ block: 'nearest', inline: 'center' })
  }, [active])

  const go = (e, to, opts) => {
    if (e.metaKey || e.ctrlKey) return
    e.preventDefault()
    navigate(to, opts)
  }

  return (
    <header className="topbar">
      <div className="topbar-inner">
        <a className="brand" href="/" onClick={(e) => go(e, '/')}>
          <span className="brand-mark" aria-hidden="true">N</span>
          <span className="brand-text">
            <span className="brand-name">{SITE_NAME}</span>
            <span className="brand-tag">{SITE_TAGLINE}</span>
          </span>
        </a>
        <TopicPicker topics={topics} topic={topic} onPick={(id) => navigate(`/${id}`)} />
        <nav className="days" ref={strip} aria-label="ימים">
          {issues.map((it) => (
            <a
              key={it.date}
              href={dayPath(topic, it.date, tab)}
              onClick={(e) => go(e, dayPath(topic, it.date, tab))}
              className={`day${it.date === active ? ' is-current' : ''}${it.empty ? ' is-empty' : ''}`}
              aria-current={it.date === active ? 'page' : undefined}
              title={it.empty ? 'עוד לא פורסם' : it.title || it.date}
            >
              <span className="day-wd">{shortWeekday(it.date)}</span>
              <span className="day-dm">{dayMonth(it.date)}</span>
              {it.podcasts > 0 && <span className="day-dot" aria-label="יש פודקאסט" />}
            </a>
          ))}
        </nav>
      </div>
    </header>
  )
}

// תחום על. כשיש תחום אחד — תווית בלבד; כשיש כמה — תפריט בחירה.
function TopicPicker({ topics, topic, onPick }) {
  const [open, setOpen] = useState(false)
  const current = topics.find((t) => t.id === topic)
  const many = topics.length > 1

  useEffect(() => {
    if (!open) return
    const close = () => setOpen(false)
    window.addEventListener('click', close)
    return () => window.removeEventListener('click', close)
  }, [open])

  return (
    <div className="topic">
      <button
        className={`topic-btn${many ? ' is-menu' : ''}`}
        onClick={(e) => { if (!many) return; e.stopPropagation(); setOpen(!open) }}
        aria-haspopup={many ? 'listbox' : undefined}
        aria-expanded={many ? open : undefined}
        title="תחום"
      >
        <span className="topic-dot" aria-hidden="true" style={current?.color ? { background: current.color } : undefined} />
        {current?.name || topic}
        {many && <span className="topic-chev" aria-hidden="true">⌄</span>}
      </button>
      {open && (
        <ul className="topic-menu" role="listbox">
          {topics.map((t) => (
            <li key={t.id}>
              <button
                role="option" aria-selected={t.id === topic}
                className={t.id === topic ? 'is-on' : ''}
                onClick={() => { setOpen(false); onPick(t.id) }}
              >
                <span className="topic-dot" aria-hidden="true" style={t.color ? { background: t.color } : undefined} />
                {t.name}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

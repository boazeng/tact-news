import { useEffect, useRef } from 'react'
import { SITE_NAME, SITE_TAGLINE } from '../config.js'
import { dayMonth, shortWeekday } from '../lib/dates.js'

// סרגל עליון: שם האתר + רצועת הימים (עד שבועיים אחורה)
export default function TopBar({ issues, active, navigate }) {
  const strip = useRef(null)

  useEffect(() => {
    const el = strip.current?.querySelector('.is-current')
    el?.scrollIntoView({ block: 'nearest', inline: 'center' })
  }, [active])

  const go = (e, to) => {
    if (e.metaKey || e.ctrlKey) return
    e.preventDefault()
    navigate(to)
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
        <nav className="days" ref={strip} aria-label="ימים">
          {issues.map((it) => (
            <a
              key={it.date}
              href={`/d/${it.date}`}
              onClick={(e) => go(e, `/d/${it.date}`)}
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

import { useEffect, useState } from 'react'
import { formatDuration, minutes } from '../lib/dates.js'
import { isDone, PauseIcon, PlayIcon, savedPosition, usePlayer } from './Player.jsx'

// משך כל פרק שמתנגן כאן — נקרא מה-metadata של הקובץ (בלי להוריד אותו כולו)
function useDurations(urls) {
  const [durations, setDurations] = useState({})
  const key = urls.join('|')
  useEffect(() => {
    const probes = urls.map((url) => {
      const a = new Audio()
      a.preload = 'metadata'
      a.onloadedmetadata = () => setDurations((d) => ({ ...d, [url]: a.duration }))
      a.src = url
      return a
    })
    return () => probes.forEach((a) => { a.onloadedmetadata = null; a.src = '' })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key])
  return durations
}

const host = (url) => {
  try { return new URL(url).hostname.replace(/^(www|open|podcasts)\./, '') } catch { return '' }
}

// פרקים: קבצים שהועלו + קישורים שגרוק בחר. קובץ אודיו ישיר מתנגן כאן; השאר נפתחים בלשונית חדשה.
export default function Listen({ date, podcasts, links = [] }) {
  const player = usePlayer()
  const rows = [
    ...podcasts.map((p) => ({ url: p.url, title: p.title, playable: true })),
    ...links.map((l) => ({
      url: l.url, title: l.title, show: l.show, description: l.description,
      playable: l.audio, minutes: l.duration_minutes,
    })),
  ]
  const queue = rows.filter((r) => r.playable).map((r) => ({ url: r.url, title: r.title, date }))
  const durations = useDurations(queue.map((q) => q.url))
  const total = rows.reduce((sum, r) => sum + (durations[r.url] || (r.minutes || 0) * 60), 0)

  return (
    <section className="listen" aria-label="פודקאסטים">
      <div className="listen-head">
        <div>
          <span className="listen-kicker">להאזנה</span>
          <h2 className="listen-title">הפודקאסטים של היום</h2>
        </div>
        <span className="listen-total">
          {rows.length} פרקים{total ? ` · ${minutes(total)} דקות` : ''}
        </span>
      </div>
      <ol className="episodes">
        {rows.map((r, i) => (r.playable
          ? <PlayableRow key={r.url} r={r} i={i} queue={queue} player={player} dur={durations[r.url] || (r.minutes || 0) * 60} />
          : <LinkRow key={r.url} r={r} i={i} />))}
      </ol>
    </section>
  )
}

function Meta({ r, i }) {
  return (
    <>
      <div className="ep-line">
        <span className="ep-num">פרק {i + 1}</span>
        <span className="ep-title">{r.title}</span>
      </div>
      {(r.show || r.description) && (
        <div className="ep-desc">
          {r.show && <span className="ep-show">{r.show}</span>}
          {r.description && <span>{r.description}</span>}
        </div>
      )}
    </>
  )
}

function PlayableRow({ r, i, queue, player, dur }) {
  const qi = queue.findIndex((q) => q.url === r.url)
  const active = player.current?.url === r.url
  const isPlaying = active && player.playing
  const pos = active ? player.time : savedPosition(r.url)
  const done = !active && isDone(r.url)
  const pct = dur ? Math.min(100, (pos / dur) * 100) : 0
  return (
    <li className={`episode${active ? ' is-active' : ''}${done ? ' is-done' : ''}`}>
      <button className="ep-play" onClick={() => player.play(queue, qi)}
        aria-label={isPlaying ? `השהה: ${r.title}` : `נגן: ${r.title}`}>
        {isPlaying ? <PauseIcon /> : <PlayIcon />}
      </button>
      <div className="ep-body">
        <Meta r={r} i={i} />
        <div className="ep-track" aria-hidden="true"><span style={{ width: `${done ? 100 : pct}%` }} /></div>
      </div>
      <span className="ep-dur" dir="ltr">
        {done ? 'הושמע ✓' : pos > 5 && dur ? `-${formatDuration(dur - pos)}` : formatDuration(dur)}
      </span>
    </li>
  )
}

function LinkRow({ r, i }) {
  return (
    <li className="episode is-link">
      <a className="ep-play ep-out" href={r.url} target="_blank" rel="noopener noreferrer"
        aria-label={`האזנה ב-${host(r.url)}: ${r.title}`}>
        <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
          <path d="M9 6h9v9M18 6 6 18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </a>
      <a className="ep-body ep-link" href={r.url} target="_blank" rel="noopener noreferrer">
        <Meta r={r} i={i} />
      </a>
      <span className="ep-dur">
        {r.minutes ? `${Math.round(r.minutes)} דק׳` : ''}
        <span className="ep-host">{host(r.url)}</span>
      </span>
    </li>
  )
}

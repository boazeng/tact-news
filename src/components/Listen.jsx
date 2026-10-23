import { useEffect, useState } from 'react'
import { formatDuration, minutes } from '../lib/dates.js'
import { isDone, PauseIcon, PlayIcon, savedPosition, usePlayer } from './Player.jsx'

// משך כל פרק — נקרא מה-metadata של הקובץ (בלי להוריד אותו כולו)
function useDurations(podcasts) {
  const [durations, setDurations] = useState({})
  useEffect(() => {
    const probes = podcasts.map((p) => {
      const a = new Audio()
      a.preload = 'metadata'
      a.onloadedmetadata = () => setDurations((d) => ({ ...d, [p.url]: a.duration }))
      a.src = p.url
      return a
    })
    return () => probes.forEach((a) => { a.onloadedmetadata = null; a.src = '' })
  }, [podcasts])
  return durations
}

export default function Listen({ date, podcasts }) {
  const player = usePlayer()
  const durations = useDurations(podcasts)
  const episodes = podcasts.map((p) => ({ url: p.url, title: p.title, date }))
  const total = Object.values(durations).reduce((a, b) => a + (b || 0), 0)

  return (
    <section className="listen" aria-label="פודקאסטים">
      <div className="listen-head">
        <div>
          <span className="listen-kicker">להאזנה</span>
          <h2 className="listen-title">הפודקאסט של היום</h2>
        </div>
        <span className="listen-total">
          {podcasts.length} פרקים{total ? ` · ${minutes(total)} דקות` : ''}
        </span>
      </div>
      <ol className="episodes">
        {episodes.map((ep, i) => {
          const active = player.current?.url === ep.url
          const isPlaying = active && player.playing
          const dur = durations[ep.url]
          const pos = active ? player.time : savedPosition(ep.url)
          const done = !active && isDone(ep.url)
          const pct = dur ? Math.min(100, (pos / dur) * 100) : 0
          return (
            <li key={ep.url} className={`episode${active ? ' is-active' : ''}${done ? ' is-done' : ''}`}>
              <button
                className="ep-play"
                onClick={() => player.play(episodes, i)}
                aria-label={isPlaying ? `השהה: ${ep.title}` : `נגן: ${ep.title}`}
              >
                {isPlaying ? <PauseIcon /> : <PlayIcon />}
              </button>
              <div className="ep-body">
                <div className="ep-line">
                  <span className="ep-num">פרק {i + 1}</span>
                  <span className="ep-title">{ep.title}</span>
                </div>
                <div className="ep-track" aria-hidden="true">
                  <span style={{ width: `${done ? 100 : pct}%` }} />
                </div>
              </div>
              <span className="ep-dur">
                {done ? 'הושמע ✓' : pos > 5 && dur ? `נותרו ${formatDuration(dur - pos)}` : formatDuration(dur)}
              </span>
            </li>
          )
        })}
      </ol>
    </section>
  )
}

import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import { SITE_NAME } from '../config.js'
import { formatDuration, longDate } from '../lib/dates.js'
import { load, save } from '../lib/store.js'

// נגן אחד לכל האתר: ממשיך לנגן גם כשעוברים בין ימים.
// זוכר מהירות, ואת המקום בכל פרק (חוזרים בדיוק לאן שהפסקתם).
const PlayerCtx = createContext(null)
export const usePlayer = () => useContext(PlayerCtx)

const RATES = [1, 1.25, 1.5, 1.75, 2]
const posKey = (url) => `pos:${url}`
const doneKey = (url) => `done:${url}`

export function PlayerProvider({ children }) {
  const audio = useRef(null)
  const [queue, setQueue] = useState([])      // [{url, title, date}]
  const [index, setIndex] = useState(-1)
  const [playing, setPlaying] = useState(false)
  const [time, setTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [rate, setRate] = useState(() => load('rate', 1))
  const lastSave = useRef(0)

  const current = index >= 0 ? queue[index] : null

  const play = useCallback((episodes, i) => {
    const same = current && episodes[i] && current.url === episodes[i].url
    if (same) {
      audio.current.paused ? audio.current.play() : audio.current.pause()
      return
    }
    setQueue(episodes)
    setIndex(i)
  }, [current])

  // החלפת פרק → טעינה, חזרה למקום השמור, ניגון
  useEffect(() => {
    const el = audio.current
    if (!el || !current) return
    el.src = current.url
    el.playbackRate = rate
    const resume = () => {
      const pos = load(posKey(current.url), 0)
      if (pos > 5 && pos < el.duration - 10) el.currentTime = pos
      el.play().catch(() => setPlaying(false))
    }
    el.addEventListener('loadedmetadata', resume, { once: true })
    el.load()
    setMediaSession(current, el)
    return () => el.removeEventListener('loadedmetadata', resume)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [current?.url])

  useEffect(() => {
    if (audio.current) audio.current.playbackRate = rate
    save('rate', rate)
  }, [rate])

  const onTime = () => {
    const el = audio.current
    setTime(el.currentTime)
    if (Math.abs(el.currentTime - lastSave.current) > 5) {
      lastSave.current = el.currentTime
      save(posKey(current.url), Math.floor(el.currentTime))
    }
  }

  const onEnded = () => {
    save(posKey(current.url), undefined)
    save(doneKey(current.url), true)
    if (index < queue.length - 1) setIndex(index + 1)
    else setPlaying(false)
  }

  const seek = (sec) => {
    const el = audio.current
    if (el && isFinite(el.duration)) el.currentTime = Math.max(0, Math.min(el.duration, sec))
  }
  const skip = (delta) => seek((audio.current?.currentTime || 0) + delta)
  const toggle = () => {
    const el = audio.current
    if (el) el.paused ? el.play() : el.pause()
  }
  const cycleRate = () => setRate(RATES[(RATES.indexOf(rate) + 1) % RATES.length])
  const close = () => {
    audio.current?.pause()
    setIndex(-1)
  }

  // כפתורי מסך הנעילה / אוזניות
  useEffect(() => {
    if (!('mediaSession' in navigator)) return
    const ms = navigator.mediaSession
    const handlers = {
      play: toggle, pause: toggle,
      seekbackward: () => skip(-15), seekforward: () => skip(30),
      previoustrack: index > 0 ? () => setIndex(index - 1) : null,
      nexttrack: index < queue.length - 1 ? () => setIndex(index + 1) : null,
    }
    for (const [action, fn] of Object.entries(handlers)) {
      try { ms.setActionHandler(action, fn) } catch { /* unsupported */ }
    }
  })

  const value = { current, queue, index, playing, time, duration, rate,
    play, toggle, seek, skip, cycleRate, close, setIndex }

  return (
    <PlayerCtx.Provider value={value}>
      {children}
      <audio
        ref={audio}
        preload="metadata"
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
        onTimeUpdate={onTime}
        onDurationChange={(e) => setDuration(e.currentTarget.duration)}
        onEnded={onEnded}
      />
      {current && <MiniPlayer />}
    </PlayerCtx.Provider>
  )
}

function setMediaSession(ep, el) {
  if (!('mediaSession' in navigator) || !window.MediaMetadata) return
  navigator.mediaSession.metadata = new window.MediaMetadata({
    title: ep.title,
    artist: SITE_NAME,
    album: longDate(ep.date),
    artwork: [{ src: '/favicon.svg', sizes: 'any', type: 'image/svg+xml' }],
  })
  el.title = ep.title
}

export const savedPosition = (url) => load(posKey(url), 0)
export const isDone = (url) => load(doneKey(url), false)

function MiniPlayer() {
  const p = usePlayer()
  const pct = p.duration ? (p.time / p.duration) * 100 : 0
  return (
    <div className="mini" role="region" aria-label="נגן">
      <input
        className="mini-bar"
        type="range" min="0" max={p.duration || 0} step="1" value={p.time}
        onChange={(e) => p.seek(Number(e.target.value))}
        style={{ '--pct': `${pct}%` }}
        aria-label="מיקום בפרק"
      />
      <div className="mini-row">
        <div className="mini-info">
          <span className="mini-title">{p.current.title}</span>
          <span className="mini-sub">
            {longDate(p.current.date)} · פרק {p.index + 1} מתוך {p.queue.length}
          </span>
        </div>
        <div className="mini-controls">
          <button className="mini-btn" onClick={() => p.skip(-15)} aria-label="15 שניות אחורה">
            <SkipIcon back />
          </button>
          <button className="mini-play" onClick={p.toggle} aria-label={p.playing ? 'השהה' : 'נגן'}>
            {p.playing ? <PauseIcon /> : <PlayIcon />}
          </button>
          <button className="mini-btn" onClick={() => p.skip(30)} aria-label="30 שניות קדימה">
            <SkipIcon />
          </button>
        </div>
        <div className="mini-side">
          <span className="mini-time" dir="ltr">{formatDuration(p.time)} / {formatDuration(p.duration)}</span>
          <button className="mini-rate" dir="ltr" onClick={p.cycleRate} aria-label="מהירות">{p.rate}×</button>
          <button className="mini-close" onClick={p.close} aria-label="סגור נגן">✕</button>
        </div>
      </div>
    </div>
  )
}

export const PlayIcon = () => (
  <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
    <path d="M8 5.5v13l11-6.5z" fill="currentColor" />
  </svg>
)
export const PauseIcon = () => (
  <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
    <path d="M7 5h4v14H7zM13 5h4v14h-4z" fill="currentColor" />
  </svg>
)
function SkipIcon({ back }) {
  return (
    <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true"
      style={back ? undefined : { transform: 'scaleX(-1)' }}>
      <path d="M12 5a7 7 0 1 1-6.6 4.7" fill="none" stroke="currentColor" strokeWidth="1.8"
        strokeLinecap="round" />
      <path d="M5 4.5v5h5" fill="none" stroke="currentColor" strokeWidth="1.8"
        strokeLinecap="round" strokeLinejoin="round" />
      <text x="12" y="15.5" textAnchor="middle" fontSize="7" fontWeight="700"
        fill="currentColor" style={back ? undefined : { transform: 'scaleX(-1)', transformOrigin: '12px 12px' }}>
        {back ? '15' : '30'}
      </text>
    </svg>
  )
}

import { useState } from 'react'
import { usePlayer } from './Player.jsx'

// לשוניות "YouTube" ו"מדריכים": כרטיס לכל סרטון. לחיצה מנגנת בתוך האתר (youtube-nocookie) ועוצרת את נגן האודיו.
export default function YoutubeView({ videos, empty }) {
  const [playing, setPlaying] = useState(null)
  const player = usePlayer()

  if (!videos.length) return <p className="empty">{empty}</p>

  const play = (v) => {
    if (player.playing) player.toggle()
    setPlaying(v.url)
  }

  return (
    <div className="videos">
      {videos.map((v) => (
        <article key={v.url} className="video">
          {v.video_id ? (
            <div className="video-frame">
              {playing === v.url ? (
                <iframe
                  src={`https://www.youtube-nocookie.com/embed/${v.video_id}?autoplay=1&rel=0`}
                  title={v.title}
                  allow="autoplay; encrypted-media; picture-in-picture; fullscreen"
                  allowFullScreen
                />
              ) : (
                <button className="video-thumb" onClick={() => play(v)} aria-label={`נגן: ${v.title}`}>
                  <img src={`https://i.ytimg.com/vi/${v.video_id}/hqdefault.jpg`} alt="" loading="lazy" />
                  <span className="video-play" aria-hidden="true">
                    <svg viewBox="0 0 24 24" width="26" height="26"><path d="M8 5.5v13l11-6.5z" fill="currentColor" /></svg>
                  </span>
                  {v.duration_minutes && <span className="video-dur">{Math.round(v.duration_minutes)} דק׳</span>}
                </button>
              )}
            </div>
          ) : null}
          <div className="video-body">
            <h3 className="video-title">
              <a href={v.url} target="_blank" rel="noopener noreferrer">{v.title}</a>
            </h3>
            <div className="video-meta">
              {v.channel && <span className="video-channel">{v.channel}</span>}
              {!v.video_id && <a className="link-btn" href={v.url} target="_blank" rel="noopener noreferrer">ל-YouTube ↗</a>}
            </div>
            {v.description && <p className="video-desc">{v.description}</p>}
          </div>
        </article>
      ))}
    </div>
  )
}

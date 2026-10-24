import { useCallback, useEffect, useRef, useState } from 'react'
import { deleteFile, getIssue, paste } from '../../lib/api.js'
import { longDate } from '../../lib/dates.js'
import { dayPath } from '../../lib/routes.js'
import { uploadFile } from '../../lib/upload.js'

// שלושה סוגי תוכן לכל יום: ניוזלטר, פרקי פודקאסט, חומר ל-NotebookLM
const KINDS = {
  newsletter: { label: 'הניוזלטר', hint: 'JSON מגרוק (מומלץ), או HTML / PDF', accept: '.json,.html,.htm,.pdf', paste: true },
  podcasts: { label: 'פרקי הפודקאסט', hint: 'קבצי האודיו מ-NotebookLM. WAV נדחס אוטומטית', accept: 'audio/*,.m4a,.wav', multiple: true },
  materials: { label: 'חומר ל-NotebookLM', hint: 'הטקסט שגרוק הכין, או קבצים', accept: '.md,.txt,.pdf,.html,.docx,.json', multiple: true, paste: true },
}

export default function UploadPanel({ topic, day, setDay, onChanged, navigate }) {
  const [info, setInfo] = useState(null)
  const [jobs, setJobs] = useState([])   // [{id, name, kind, progress, error, done}]

  const load = useCallback(() => {
    getIssue(topic, day).then(setInfo).catch(() => setInfo({ newsletter: null, podcasts: [], materials: [] }))
  }, [topic, day])
  useEffect(load, [load])

  const changed = () => { load(); onChanged() }
  const patch = (id, p) => setJobs((js) => js.map((j) => (j.id === id ? { ...j, ...p } : j)))

  const upload = async (kind, files) => {
    for (const file of files) {
      const id = `${Date.now()}-${Math.random()}`
      setJobs((js) => [{ id, name: file.name, kind, progress: 0 }, ...js])
      try {
        await uploadFile(topic, day, kind, file, (progress) => patch(id, { progress }))
        patch(id, { done: true, progress: 1 })
      } catch (e) {
        patch(id, { error: e.message })
      }
      changed()
    }
  }

  const remove = async (kind, name) => {
    await deleteFile(topic, day, kind, name).catch(() => {})
    changed()
  }

  const files = info ? {
    newsletter: info.newsletter ? [{ name: info.newsletter.name, title: info.newsletter.name }] : [],
    podcasts: info.podcasts,
    materials: info.materials,
  } : {}

  return (
    <section className="card">
      <div className="upload-head">
        <h2 className="card-title">העלאה ליום</h2>
        <label className="date-pick">
          <input type="date" value={day} onChange={(e) => e.target.value && setDay(e.target.value)} />
          <span>{longDate(day)}</span>
        </label>
        {(info?.newsletter || info?.podcasts?.length > 0) && (
          <button className="link-btn" onClick={() => navigate(dayPath(topic, day))}>לצפייה בדף ←</button>
        )}
      </div>

      <div className="kinds">
        {Object.entries(KINDS).map(([kind, cfg]) => (
          <KindBox key={kind} kind={kind} cfg={cfg} topic={topic} day={day} files={files[kind] || []}
            onFiles={(fs) => upload(kind, fs)} onRemove={(name) => remove(kind, name)}
            onPasted={changed} />
        ))}
      </div>

      {jobs.length > 0 && (
        <ul className="jobs">
          {jobs.map((j) => (
            <li key={j.id} className={`job${j.error ? ' is-err' : ''}${j.done ? ' is-done' : ''}`}>
              <span className="job-name">{j.name}</span>
              <span className="job-bar"><span style={{ width: `${Math.round(j.progress * 100)}%` }} /></span>
              <span className="job-state">
                {j.error || (j.done ? 'הועלה ✓' : j.progress >= 1 ? 'מעבד…' : `${Math.round(j.progress * 100)}%`)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

function KindBox({ kind, cfg, topic, day, files, onFiles, onRemove, onPasted }) {
  const input = useRef(null)
  const [over, setOver] = useState(false)
  const [text, setText] = useState('')
  const [title, setTitle] = useState('')
  const [msg, setMsg] = useState('')

  const drop = (e) => {
    e.preventDefault()
    setOver(false)
    const fs = [...e.dataTransfer.files]
    if (fs.length) onFiles(cfg.multiple ? fs : fs.slice(0, 1))
  }

  const submitText = async () => {
    setMsg('שומר…')
    try {
      await paste(topic, day, kind, text, title)
      setText('')
      setTitle('')
      setMsg('נשמר ✓')
      onPasted()
    } catch (e) {
      setMsg(e.message)
    }
  }

  return (
    <div className="kind">
      <h3 className="kind-title">{cfg.label}</h3>
      <p className="kind-hint">{cfg.hint}</p>
      <div
        className={`drop${over ? ' is-over' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setOver(true) }}
        onDragLeave={() => setOver(false)}
        onDrop={drop}
        onClick={() => input.current.click()}
        role="button" tabIndex={0}
        onKeyDown={(e) => e.key === 'Enter' && input.current.click()}
      >
        גוררים לכאן קבצים, או <u>בוחרים</u>
        <input ref={input} type="file" hidden accept={cfg.accept} multiple={!!cfg.multiple}
          onChange={(e) => { onFiles([...e.target.files]); e.target.value = '' }} />
      </div>

      {cfg.paste && (
        <div className="paste">
          {kind === 'materials' && (
            <input className="paste-title" value={title} onChange={(e) => setTitle(e.target.value)}
              placeholder="כותרת (לא חובה)" />
          )}
          <textarea dir="auto" value={text} onChange={(e) => setText(e.target.value)} rows={4}
            placeholder={kind === 'newsletter' ? 'או מדביקים כאן את ה-JSON מגרוק' : 'או מדביקים כאן את הטקסט'} />
          <div className="paste-row">
            <button className="btn" disabled={!text.trim()} onClick={submitText}>שמירה</button>
            {msg && <span className="paste-msg">{msg}</span>}
          </div>
        </div>
      )}

      {files.length > 0 && (
        <ul className="have">
          {files.map((f) => (
            <li key={f.name}>
              <span>{f.title || f.name}</span>
              <button className="x-btn" onClick={() => onRemove(f.name)} aria-label={`מחיקת ${f.name}`}>✕</button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

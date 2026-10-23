import { useState } from 'react'

const fmtSize = (b) => (b > 1e6 ? `${(b / 1e6).toFixed(1)}MB` : `${Math.max(1, Math.round(b / 1e3))}KB`)
const isText = (m) => ['md', 'txt'].includes(m.ext)

// חומר הרקע ש-Grok הכין ל-NotebookLM: צפייה, העתקה והורדה
export default function Materials({ materials }) {
  const [openName, setOpenName] = useState(null)
  const [text, setText] = useState('')
  const [copied, setCopied] = useState(false)

  const toggle = async (m) => {
    if (openName === m.name) return setOpenName(null)
    setOpenName(m.name)
    setText('טוען…')
    setText(await fetch(m.url).then((r) => r.text()).catch(() => 'הטעינה נכשלה'))
  }

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 1600)
    } catch { /* clipboard blocked */ }
  }

  return (
    <section className="materials" aria-label="חומר ל-NotebookLM">
      <h2 className="block-title">חומר הרקע לפודקאסט</h2>
      <p className="block-sub">מה שגרוק הכין ל-NotebookLM — המקור שממנו נוצרו הפרקים.</p>
      <ul className="mat-list">
        {materials.map((m) => (
          <li key={m.name} className="mat">
            <div className="mat-row">
              <span className="mat-ext">{m.ext}</span>
              <span className="mat-name">{m.title}</span>
              <span className="mat-size">{fmtSize(m.size)}</span>
              {isText(m) && (
                <button className="link-btn" onClick={() => toggle(m)}>
                  {openName === m.name ? 'הסתר' : 'הצג'}
                </button>
              )}
              <a className="link-btn" href={m.url} download={m.name}>הורדה</a>
            </div>
            {openName === m.name && (
              <div className="mat-text">
                <button className="copy-btn" onClick={copy}>{copied ? 'הועתק ✓' : 'העתקה'}</button>
                <pre>{text}</pre>
              </div>
            )}
          </li>
        ))}
      </ul>
    </section>
  )
}

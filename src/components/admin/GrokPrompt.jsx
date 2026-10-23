import { useState } from 'react'
import prompt from '../../../docs/GROK-PROMPT.md?raw'

// ההוראה לגרוק — מאז הוא מפרסם לאתר לבד דרך /mcp
export default function GrokPrompt() {
  const [copied, setCopied] = useState(false)
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(prompt)
      setCopied(true)
      setTimeout(() => setCopied(false), 1600)
    } catch { /* clipboard blocked */ }
  }
  return (
    <details className="card grok">
      <summary className="card-title">ההוראה לגרוק</summary>
      <p className="kind-hint">
        ההוראה לבוט של גרוק. הוא מפרסם לבד דרך החיבור (connector) ל-/mcp — ההעלאה כאן
        היא רק לתיקונים ידניים.
      </p>
      <div className="mat-text">
        <button className="copy-btn" onClick={copy}>{copied ? 'הועתק ✓' : 'העתקה'}</button>
        <pre>{prompt}</pre>
      </div>
    </details>
  )
}

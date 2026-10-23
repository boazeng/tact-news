import { useState } from 'react'
import prompt from '../../../docs/GROK-PROMPT.md?raw'

// ההוראה לגרוק — מעתיקים פעם אחת לבוט, ומאז הוא מחזיר JSON שהאתר מבין
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
      <summary className="card-title">ההוראה לגרוק (להעתקה חד-פעמית)</summary>
      <p className="kind-hint">
        מדביקים את זה לבוט של גרוק. מאז הוא מוסיף לכל ניוזלטר בלוק JSON — מעתיקים אותו
        לתיבה "הניוזלטר" למעלה. אם יש בו גם notebooklm, החומר נשמר אוטומטית.
      </p>
      <div className="mat-text">
        <button className="copy-btn" onClick={copy}>{copied ? 'הועתק ✓' : 'העתקה'}</button>
        <pre>{prompt}</pre>
      </div>
    </details>
  )
}

import { useCallback, useEffect, useState } from 'react'
import { getIssues, getMe } from '../lib/api.js'
import { todayIL } from '../lib/dates.js'
import UploadPanel from '../components/admin/UploadPanel.jsx'
import DaysTable from '../components/admin/DaysTable.jsx'
import GrokPrompt from '../components/admin/GrokPrompt.jsx'

export default function AdminPage({ topics, navigate, onChanged }) {
  const [me, setMe] = useState(null)
  const [issues, setIssues] = useState([])
  const [day, setDay] = useState(todayIL())
  const [topic, setTopic] = useState(topics[0].id)

  const refresh = useCallback(() => {
    getIssues(topic).then((d) => setIssues(d.issues)).catch(() => {})
    onChanged()
  }, [topic, onChanged])

  useEffect(() => { getMe().then(setMe) }, [])
  useEffect(() => { if (me?.role === 'admin') refresh() }, [me, refresh])

  if (!me) return <div className="page"><div className="loading" aria-label="טוען" /></div>

  if (me.role !== 'admin') {
    return (
      <div className="page admin">
        <div className="card gate">
          <h1 className="admin-h1">ניהול הגיליונות</h1>
          {me.email ? (
            <p>החשבון {me.email} לא מורשה לנהל את האתר.</p>
          ) : (
            <p>ההעלאה והמחיקה פתוחות רק למנהל. הקריאה פתוחה לכולם.</p>
          )}
          <a className="btn primary" href="/login">כניסה עם Google</a>
        </div>
      </div>
    )
  }

  return (
    <div className="page admin">
      <div className="admin-head">
        <h1 className="admin-h1">ניהול הגיליונות</h1>
        {topics.length > 1 && (
          <label className="date-pick">
            תחום
            <select value={topic} onChange={(e) => setTopic(e.target.value)}>
              {topics.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
            </select>
          </label>
        )}
        <span className="admin-who">
          {me.email} · <a href="/logout">יציאה</a>
        </span>
      </div>
      <UploadPanel topic={topic} day={day} setDay={setDay} onChanged={refresh} navigate={navigate} />
      <DaysTable topic={topic} issues={issues} onChanged={refresh} navigate={navigate} onPick={setDay} />
      <GrokPrompt />
    </div>
  )
}

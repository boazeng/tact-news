import { useCallback, useEffect, useState } from 'react'
import { getIssues, getMe, getTopics } from '../lib/api.js'
import { todayIL } from '../lib/dates.js'
import UploadPanel from '../components/admin/UploadPanel.jsx'
import DaysTable from '../components/admin/DaysTable.jsx'
import GrokPrompt from '../components/admin/GrokPrompt.jsx'
import TopicsManager from '../components/admin/TopicsManager.jsx'
import AgentPanel from '../components/admin/AgentPanel.jsx'
import ReviewPanel from '../components/admin/ReviewPanel.jsx'

export default function AdminPage({ topics: siteTopics, navigate, onChanged, onTopicsChanged }) {
  const [me, setMe] = useState(null)
  // בניהול — כל התחומים, גם של Longeviora (באתר עצמו הם לא מופיעים)
  const [allTopics, setAllTopics] = useState(null)
  const topics = allTopics || siteTopics
  const [issues, setIssues] = useState([])
  const [day, setDay] = useState(todayIL())
  const [picked, setTopic] = useState(topics[0].id)
  // תחום שנמחק → חוזרים לברירת המחדל
  const topic = topics.some((t) => t.id === picked) ? picked : topics[0].id

  const refresh = useCallback(() => {
    getIssues(topic, true).then((d) => setIssues(d.issues)).catch(() => {})
    onChanged()
  }, [topic, onChanged])

  const loadTopics = useCallback(() => {
    getTopics('*').then((d) => d.topics?.length && setAllTopics(d.topics)).catch(() => {})
  }, [])
  const topicsChanged = useCallback(() => { loadTopics(); onTopicsChanged() }, [loadTopics, onTopicsChanged])

  useEffect(() => { getMe().then(setMe) }, [])
  useEffect(() => { if (me?.role === 'admin') loadTopics() }, [me, loadTopics])
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
      <ReviewPanel onChanged={refresh} />
      <AgentPanel topics={topics} onChanged={refresh} />
      <TopicsManager topics={topics} onChanged={topicsChanged} />
      <GrokPrompt />
    </div>
  )
}

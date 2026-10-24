import { useCallback, useEffect, useState } from 'react'
import { getIssues, getTopics } from './lib/api.js'
import { todayIL } from './lib/dates.js'
import { parse } from './lib/routes.js'
import { PlayerProvider } from './components/Player.jsx'
import TopBar from './components/TopBar.jsx'
import DayPage from './pages/DayPage.jsx'
import AdminPage from './pages/AdminPage.jsx'

const FALLBACK_TOPICS = [{ id: 'ai', name: 'בינה מלאכותית', default: true }]

export default function App() {
  const [route, setRoute] = useState(() => parse(location.pathname))
  const [topics, setTopics] = useState(FALLBACK_TOPICS)
  const [issues, setIssues] = useState(null)
  const [today, setToday] = useState(todayIL)

  useEffect(() => { getTopics().then((d) => d.topics?.length && setTopics(d.topics)).catch(() => {}) }, [])

  const defaultTopic = (topics.find((t) => t.default) || topics[0]).id
  const topic = route.topic || defaultTopic
  const topicInfo = topics.find((t) => t.id === topic)

  const loadIssues = useCallback(() => {
    if (!topicInfo) return
    getIssues(topic)
      .then((d) => { setIssues(d.issues); if (d.today) setToday(d.today) })
      .catch(() => setIssues([]))
  }, [topic, topicInfo])
  useEffect(() => { setIssues(null); loadIssues() }, [loadIssues])

  useEffect(() => {
    const onPop = () => setRoute(parse(location.pathname))
    window.addEventListener('popstate', onPop)
    return () => window.removeEventListener('popstate', onPop)
  }, [])

  const navigate = useCallback((to, { keepScroll = false } = {}) => {
    if (to !== location.pathname) history.pushState(null, '', to)
    setRoute(parse(to))
    if (!keepScroll) window.scrollTo(0, 0)
  }, [])

  const date = route.date || today
  const tab = route.tab || 'newsletter'
  const latest = issues?.[0]?.date
  // היום הנוכחי תמיד ברצועה — גם לפני שהגיליון שלו עלה
  const strip = issues && !issues.some((it) => it.date === today)
    ? [{ date: today, empty: true }, ...issues] : issues || []

  return (
    <PlayerProvider>
      <TopBar
        topics={topics} topic={topic} issues={route.page === 'admin' ? [] : strip}
        active={date} tab={tab} navigate={navigate}
      />
      <main>
        {route.page === 'admin' && <AdminPage topics={topics} navigate={navigate} onChanged={loadIssues} />}
        {route.page === 'day' && !topicInfo && (
          <div className="page"><p className="empty">אין תחום כזה באתר.</p></div>
        )}
        {route.page === 'day' && topicInfo && issues === null && (
          <div className="page"><div className="loading" aria-label="טוען" /></div>
        )}
        {route.page === 'day' && topicInfo && issues !== null && (
          <DayPage
            key={`${topic}/${date}`} topic={topic} topicName={topicInfo.name}
            date={date} tab={tab} today={today} latest={latest} navigate={navigate}
          />
        )}
      </main>
      <footer className="site-foot">
        <span>הגיליונות נשמרים שבועיים ונמחקים אוטומטית</span>
        <a href="/admin" onClick={(e) => { e.preventDefault(); navigate('/admin') }}>ניהול</a>
      </footer>
    </PlayerProvider>
  )
}

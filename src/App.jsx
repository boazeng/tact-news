import { useCallback, useEffect, useState } from 'react'
import { getIssues } from './lib/api.js'
import { todayIL } from './lib/dates.js'
import { PlayerProvider } from './components/Player.jsx'
import TopBar from './components/TopBar.jsx'
import DayPage from './pages/DayPage.jsx'
import AdminPage from './pages/AdminPage.jsx'

// ניתוב פשוט: /  → היום הנוכחי (גם אם הגיליון עוד לא עלה) · /d/YYYY-MM-DD → יום · /admin → ניהול
function parse(path) {
  const m = path.match(/^\/d\/(\d{4}-\d{2}-\d{2})\/?$/)
  if (m) return { page: 'day', date: m[1] }
  if (path.startsWith('/admin')) return { page: 'admin' }
  return { page: 'home' }
}

export default function App() {
  const [route, setRoute] = useState(() => parse(location.pathname))
  const [issues, setIssues] = useState(null)
  const [today, setToday] = useState(todayIL)

  const loadIssues = useCallback(() => {
    getIssues()
      .then((d) => { setIssues(d.issues); if (d.today) setToday(d.today) })
      .catch(() => setIssues([]))
  }, [])
  useEffect(loadIssues, [loadIssues])

  useEffect(() => {
    const onPop = () => setRoute(parse(location.pathname))
    window.addEventListener('popstate', onPop)
    return () => window.removeEventListener('popstate', onPop)
  }, [])

  const navigate = useCallback((to) => {
    if (to !== location.pathname) history.pushState(null, '', to)
    setRoute(parse(to))
    window.scrollTo(0, 0)
  }, [])

  const latest = issues?.[0]?.date
  const date = route.page === 'day' ? route.date : route.page === 'home' ? today : null
  // היום הנוכחי תמיד ברצועה — גם לפני שהגיליון שלו עלה
  const strip = issues && !issues.some((it) => it.date === today)
    ? [{ date: today, empty: true }, ...issues] : issues || []

  return (
    <PlayerProvider>
      <TopBar issues={strip} active={date} navigate={navigate} />
      <main>
        {route.page === 'admin' && <AdminPage navigate={navigate} onChanged={loadIssues} />}
        {route.page !== 'admin' && issues === null && (
          <div className="page"><div className="loading" aria-label="טוען" /></div>
        )}
        {date && issues !== null && (
          <DayPage key={date} date={date} today={today} latest={latest} navigate={navigate} />
        )}
      </main>
      <footer className="site-foot">
        <span>הגיליונות נשמרים שבועיים ונמחקים אוטומטית</span>
        <a href="/admin" onClick={(e) => { e.preventDefault(); navigate('/admin') }}>ניהול</a>
      </footer>
    </PlayerProvider>
  )
}

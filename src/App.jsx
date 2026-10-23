import { useCallback, useEffect, useState } from 'react'
import { getIssues } from './lib/api.js'
import { PlayerProvider } from './components/Player.jsx'
import TopBar from './components/TopBar.jsx'
import DayPage from './pages/DayPage.jsx'
import AdminPage from './pages/AdminPage.jsx'

// ניתוב פשוט: /  → היום האחרון · /d/YYYY-MM-DD → יום · /admin → ניהול
function parse(path) {
  const m = path.match(/^\/d\/(\d{4}-\d{2}-\d{2})\/?$/)
  if (m) return { page: 'day', date: m[1] }
  if (path.startsWith('/admin')) return { page: 'admin' }
  return { page: 'home' }
}

export default function App() {
  const [route, setRoute] = useState(() => parse(location.pathname))
  const [issues, setIssues] = useState(null)

  const loadIssues = useCallback(() => {
    getIssues().then((d) => setIssues(d.issues)).catch(() => setIssues([]))
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
  const date = route.page === 'day' ? route.date : route.page === 'home' ? latest : null

  return (
    <PlayerProvider>
      <TopBar issues={issues || []} active={date} navigate={navigate} />
      <main>
        {route.page === 'admin' && <AdminPage navigate={navigate} onChanged={loadIssues} />}
        {route.page !== 'admin' && issues === null && (
          <div className="page"><div className="loading" aria-label="טוען" /></div>
        )}
        {route.page !== 'admin' && issues !== null && !date && (
          <div className="page">
            <p className="empty">עוד אין גיליונות. הראשון יופיע כאן ברגע שיעלה.</p>
          </div>
        )}
        {date && <DayPage key={date} date={date} />}
      </main>
      <footer className="site-foot">
        <span>הגיליונות נשמרים שבועיים ונמחקים אוטומטית</span>
        <a href="/admin" onClick={(e) => { e.preventDefault(); navigate('/admin') }}>ניהול</a>
      </footer>
    </PlayerProvider>
  )
}

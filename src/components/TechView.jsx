import StoryCard from './StoryCard.jsx'

// לשונית "טכנולוגיה": פיתוחים חדשים — כרטיסים כמו בניוזלטר, עם החברה מעל הכותרת
export default function TechView({ items }) {
  if (!items.length) return <p className="empty">אין פיתוחים ליום הזה.</p>
  return (
    <div className="stories tech-list tone-biz">
      {items.map((t, i) => (
        <StoryCard key={t.source_url + i} item={t} id={`tech-${i}`} kicker={t.company} />
      ))}
    </div>
  )
}

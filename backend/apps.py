"""תחומים של אפליקציות אחרות שמתארחות בשרת — כרגע Longeviora (אפליקציית תוחלת חיים לקהל, ריפו boazeng/longeviora-app).

- לא מופיעים באתר ובאפליקציה של TACT News: /api/topics מחזיר רק תחומים בלי app; ‏/api/topics?app=longeviora — רק אותם.
- review=True: מה שנכתב (Claude או גרוק) לא ציבורי עד אישור יומי בדף הניהול (review.py).
- kind=news: Claude כותב ניוזלטר מהפידים (evening_agent), גרוק מוסיף מאמרים, פודקאסטים ווידאו.
- kind=promote: פוסטים ממומנים — רק גרוק, דרך set_promoted. Claude לא רץ עליהם.
- lang: שפת התוכן (he / en) — Claude כותב בשפה הזו.

נוספים בעלייה אם חסרים (Topics.ensure). שם, תיאור ומקורות אפשר לערוך בדף הניהול — העריכה נשמרת.
"""
from urllib.parse import quote

from .topics import Topics

APP = "longeviora"
TABS = ["newsletter", "podcasts", "youtube", "papers"]

_GN_EN = "&hl=en-US&gl=US&ceid=US:en"
_GN_HE = "&hl=he&gl=IL&ceid=IL:he"


def _gnews(query: str, tail: str) -> str:
    return "https://news.google.com/rss/search?q=" + quote(query) + tail


_SOURCES_EN = [
    ("ScienceDaily — Healthy Aging", "https://www.sciencedaily.com/rss/health_medicine/healthy_aging.xml"),
    ("ScienceDaily — Nutrition", "https://www.sciencedaily.com/rss/health_medicine/nutrition.xml"),
    ("ScienceDaily — Fitness", "https://www.sciencedaily.com/rss/health_medicine/fitness.xml"),
    ("ScienceDaily — Sleep", "https://www.sciencedaily.com/rss/health_medicine/sleep_disorders.xml"),
    ("ScienceDaily — Alzheimer's", "https://www.sciencedaily.com/rss/health_medicine/alzheimer's.xml"),
    ("Nature Aging", "https://www.nature.com/nataging.rss"),
    ("Nature — Ageing", "https://www.nature.com/subjects/ageing.rss"),
    ("Lifespan.io", "https://www.lifespan.io/feed/"),
    ("Fight Aging!", "https://www.fightaging.org/feed/"),
    ("Medical Xpress — Gerontology", "https://medicalxpress.com/rss-feed/gerontology-geriatrics-news/"),
    ("WHO", "https://www.who.int/rss-feeds/news-english.xml"),
    ("NIH", _gnews("site:nih.gov when:3d", _GN_EN)),
    ("Harvard Health", _gnews("site:health.harvard.edu when:7d", _GN_EN)),
    ("Google News — longevity research", _gnews("healthspan OR longevity research when:2d", _GN_EN)),
    ("Google News — aging studies", _gnews("aging study OR ageing study when:2d", _GN_EN)),
]

_SOURCES_HE = [
    ("מעריב — בריאות", "https://www.maariv.co.il/Rss/RssFeedsBriut"),
    ("ynet — בריאות", _gnews("site:ynet.co.il/health when:2d", _GN_HE)),
    ("חדשות — הזדקנות", _gnews("הזדקנות מחקר when:3d", _GN_HE)),
    ("חדשות — אריכות ימים", _gnews("אריכות ימים when:3d", _GN_HE)),
    ("חדשות — שינה", _gnews("שינה מחקר when:3d", _GN_HE)),
    ("חדשות — תזונה", _gnews("תזונה מחקר when:3d", _GN_HE)),
    ("חדשות — פעילות גופנית", _gnews("פעילות גופנית מחקר when:3d", _GN_HE)),
]


def _lines(sources) -> str:
    return "\n".join(f"{name} | {url}" for name, url in sources)


_TONE_EN = (
    "Tone: consumer wellness — clear, calm, evidence-first, for a general audience. "
    "**No medical advice**, no dosing, no drug or supplement or brand recommendations; "
    "report what a study found and its limits (mice vs humans, sample size). No sensational claims."
)
_TONE_HE = (
    "טון: בריאות לצרכן — ברור, רגוע, מבוסס ראיות, לקהל הרחב. "
    "**בלי ייעוץ רפואי**, בלי מינונים, בלי המלצה על תרופות, תוספים או מותגים; "
    "מה המחקר מצא ומה המגבלות שלו (עכברים מול בני אדם, גודל המדגם). בלי כותרות מבהילות."
)

SPECS = [
    {"id": "longevity", "name": "אריכות ימים", "color": "#0f766e", "tabs": TABS,
     "app": APP, "lang": "he", "kind": "news", "review": True,
     "description": "==מחקר על הזדקנות ואריכות ימים בריאה (healthspan)==: ביולוגיה של ההזדקנות, "
                    "**פעילות גופנית, שינה ותזונה — מה המדע אומר**, בריאות המוח, מחלות של גיל מבוגר, "
                    "ונתוני בריאות הציבור (תוחלת חיים, מגמות). " + _TONE_HE,
     "sources": _lines(_SOURCES_HE + _SOURCES_EN)},
    {"id": "longevity-en", "name": "Longevity", "color": "#0f766e", "tabs": TABS,
     "app": APP, "lang": "en", "kind": "news", "review": True,
     "description": "==Aging research and healthy lifespan (healthspan)==: the biology of aging, "
                    "**exercise, sleep and nutrition science**, brain health, age-related disease, "
                    "and public-health data (life expectancy, trends). " + _TONE_EN,
     "sources": _lines(_SOURCES_EN)},
    {"id": "longeviora-promote", "name": "מקודם", "color": "#b45309", "tabs": ["newsletter"],
     "app": APP, "lang": "he", "kind": "promote", "review": True,
     "description": "פוסטים ממומנים של ארגונים בתחום הבריאות ואריכות הימים. גרוק מעלה עם set_promoted. " + _TONE_HE,
     "sources": ""},
    {"id": "longeviora-promote-en", "name": "Promoted", "color": "#b45309", "tabs": ["newsletter"],
     "app": APP, "lang": "en", "kind": "promote", "review": True,
     "description": "Sponsored posts by health and longevity organizations. Grok uploads them with set_promoted. "
                    + _TONE_EN,
     "sources": ""},
]


def ensure(topics: Topics) -> None:
    for spec in SPECS:
        topics.ensure(spec)

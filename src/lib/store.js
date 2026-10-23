// localStorage עטוף — בגלישה פרטית הוא יכול לזרוק; האתר עובד גם בלעדיו.
export function load(key, fallback) {
  try {
    const v = localStorage.getItem(key)
    return v === null ? fallback : JSON.parse(v)
  } catch {
    return fallback
  }
}

export function save(key, value) {
  try {
    if (value === undefined) localStorage.removeItem(key)
    else localStorage.setItem(key, JSON.stringify(value))
  } catch { /* ignore */ }
}

// העלאה בחתיכות של 25MB — Cloudflare חוסם בקשה מעל 100MB, ופרק WAV יכול לעבור את זה.
const CHUNK = 25 * 1024 * 1024

function sendChunk(url, form, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('POST', url)
    xhr.upload.onprogress = (e) => e.lengthComputable && onProgress(e.loaded)
    xhr.onload = () => {
      let body = {}
      try { body = JSON.parse(xhr.responseText) } catch { /* not json */ }
      if (xhr.status >= 200 && xhr.status < 300) resolve(body)
      else reject(new Error(body.detail || `שגיאה ${xhr.status}`))
    }
    xhr.onerror = () => reject(new Error('החיבור נכשל'))
    xhr.send(form)
  })
}

export async function uploadFile(day, kind, file, onProgress = () => {}) {
  const total = Math.max(1, Math.ceil(file.size / CHUNK))
  let result = null
  for (let index = 0; index < total; index++) {
    const start = index * CHUNK
    const form = new FormData()
    form.append('kind', kind)
    form.append('name', file.name)
    form.append('index', String(index))
    form.append('total', String(total))
    form.append('chunk', file.slice(start, start + CHUNK), file.name)
    result = await sendChunk(`/api/issues/${day}/upload`, form,
      (loaded) => onProgress(Math.min(1, (start + loaded) / file.size)))
  }
  onProgress(1)
  return result
}

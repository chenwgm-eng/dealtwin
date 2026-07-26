// 转义引号和反斜杠：用于 G6 label、JS 字符串字面量、CSV 字段等场景，避免拼接时破坏宿主语法
export const escapeText = (str) => String(str ?? '').replace(/['"\\]/g, '\\$&')

export function formatStructuredText(text, emptyPlaceholder = '— 双击添加 —') {
  if (!text || !String(text).trim()) return `<span class="fmt-empty">${emptyPlaceholder}</span>`
  let s = String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
  const lines = s.split(/\r?\n/)
  const out = []
  let inList = false
  const closeList = () => { if (inList) { out.push('</ul>'); inList = false } }
  for (let raw of lines) {
    const line = raw.trim()
    if (!line) { closeList(); continue }
    const titleMatch = line.match(/^【([^】]+)】(.*)$/)
    if (titleMatch) {
      closeList()
      out.push(`<h5 class="fmt-title">【${titleMatch[1]}】</h5>`)
      if (titleMatch[2]) out.push(`<p class="fmt-text">${titleMatch[2]}</p>`)
      continue
    }
    const bulletMatch = line.match(/^[•·\-\*]\s*(.*)$/)
    if (bulletMatch) {
      if (!inList) { out.push('<ul class="fmt-list">'); inList = true }
      out.push(`<li>${bulletMatch[1]}</li>`)
      continue
    }
    closeList()
    out.push(`<p class="fmt-text">${line}</p>`)
  }
  closeList()
  return out.join('')
}

export function formatDate(d) {
  if (!d) return ''
  const dt = new Date(d)
  return `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, '0')}-${String(dt.getDate()).padStart(2, '0')}`
}

export function formatDateTime(d) {
  if (!d) return ''
  try {
    const date = new Date(d)
    return date.toLocaleString(undefined, {
      month: 'long', day: 'numeric', year: 'numeric',
      hour: 'numeric', minute: '2-digit', hour12: false
    })
  } catch {
    return d
  }
}

export function formatCurrency(n) {
  if (!n) return ''
  return Number(n).toLocaleString()
}

export function truncateText(text, maxLen = 80) {
  if (!text) return ''
  return text.length > maxLen ? text.substring(0, maxLen) + '…' : text
}

export function formatFileSize(bytes) {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

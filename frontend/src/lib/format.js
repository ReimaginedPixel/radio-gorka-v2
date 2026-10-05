// Simpleton (font wyświetlaczy) ma tylko ASCII, więc zdejmujemy polskie znaki.
export function ledText(value) {
  return (value || '')
    .replace(/ł/g, 'l')
    .replace(/Ł/g, 'L')
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toUpperCase()
}

export function clock(seconds) {
  if (seconds == null || !Number.isFinite(seconds)) return '--:--'
  const s = Math.max(0, Math.floor(seconds))
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const rest = String(s % 60).padStart(2, '0')
  return h ? `${h}:${String(m).padStart(2, '0')}:${rest}` : `${m}:${rest}`
}

export function timeAgo(iso, now = Date.now()) {
  if (!iso) return ''
  const diff = Math.max(0, (now - new Date(iso).getTime()) / 1000)
  if (diff < 45) return 'przed chwilą'
  if (diff < 3600) return `${Math.round(diff / 60)} min temu`
  if (diff < 86400) return `${Math.round(diff / 3600)} godz. temu`
  return new Date(iso).toLocaleDateString('pl-PL', { day: 'numeric', month: 'short' })
}

export function pad2(n) {
  return String(Math.max(0, n | 0)).padStart(2, '0')
}

export function plural(n, one, few, many) {
  if (n === 1) return one
  const d = n % 10
  const dd = n % 100
  return d >= 2 && d <= 4 && (dd < 12 || dd > 14) ? few : many
}

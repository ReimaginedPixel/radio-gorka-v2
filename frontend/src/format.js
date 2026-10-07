export const formatDuration = (seconds) => {
  if (!seconds && seconds !== 0) return ''
  const m = Math.floor(seconds / 60)
  const s = String(seconds % 60).padStart(2, '0')
  return `${m}:${s}`
}

export const formatTime = (iso) => {
  if (!iso) return ''
  const date = new Date(iso)
  const now = new Date()
  const time = date.toLocaleTimeString('pl-PL', { hour: '2-digit', minute: '2-digit' })
  if (date.toDateString() === now.toDateString()) return time
  return `${date.toLocaleDateString('pl-PL', { day: 'numeric', month: 'short' })} ${time}`
}

export const votesWord = (n) => {
  if (n === 1) return 'głos'
  const lastTwo = n % 100
  const last = n % 10
  if (last >= 2 && last <= 4 && (lastTwo < 12 || lastTwo > 14)) return 'głosy'
  return 'głosów'
}

export const thumbnailUrl = (videoId) => `https://img.youtube.com/vi/${videoId}/default.jpg`

export const youtubeUrl = (videoId) => `https://music.youtube.com/watch?v=${videoId}`

// Odświeżanie co interval ms, tylko gdy karta jest widoczna.
export const startPolling = (fn, interval) => {
  const tick = () => {
    if (document.visibilityState === 'visible') fn()
  }
  const id = setInterval(tick, interval)
  document.addEventListener('visibilitychange', tick)
  return () => {
    clearInterval(id)
    document.removeEventListener('visibilitychange', tick)
  }
}

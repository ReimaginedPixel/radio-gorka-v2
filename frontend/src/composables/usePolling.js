import { onBeforeUnmount, onMounted } from 'vue'

// Odpytuje serwer co `ms`, ale tylko gdy karta jest widoczna.
export function usePolling(fn, ms) {
  let timer = 0
  let running = false
  let stopped = false

  async function tick() {
    if (running || stopped) return
    running = true
    try {
      await fn()
    } finally {
      running = false
    }
  }

  function start() {
    clearInterval(timer)
    timer = setInterval(() => {
      if (document.visibilityState === 'visible') tick()
    }, ms)
  }

  function onVisibility() {
    if (document.visibilityState === 'visible') tick()
  }

  onMounted(() => {
    tick()
    start()
    document.addEventListener('visibilitychange', onVisibility)
  })

  onBeforeUnmount(() => {
    stopped = true
    clearInterval(timer)
    document.removeEventListener('visibilitychange', onVisibility)
  })

  return { refresh: tick }
}

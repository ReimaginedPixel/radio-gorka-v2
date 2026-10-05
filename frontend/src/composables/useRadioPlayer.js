import { computed, ref, shallowRef } from 'vue'

let apiPromise = null

export function loadYouTubeApi() {
  if (window.YT?.Player) return Promise.resolve(window.YT)
  if (apiPromise) return apiPromise
  apiPromise = new Promise((resolve, reject) => {
    const previous = window.onYouTubeIframeAPIReady
    window.onYouTubeIframeAPIReady = () => {
      previous?.()
      resolve(window.YT)
    }
    const script = document.createElement('script')
    script.src = 'https://www.youtube.com/iframe_api'
    script.async = true
    script.onerror = () => {
      apiPromise = null
      script.remove()
      reject(new Error('Nie udało się załadować odtwarzacza YouTube'))
    }
    document.head.appendChild(script)
  })
  return apiPromise
}

const YT_STATE = { UNSTARTED: -1, ENDED: 0, PLAYING: 1, PAUSED: 2, BUFFERING: 3, CUED: 5 }

function readVolume() {
  try {
    const v = Number(localStorage.getItem('rg-volume'))
    return Number.isFinite(v) && localStorage.getItem('rg-volume') !== null ? Math.min(100, Math.max(0, v)) : 80
  } catch {
    return 80
  }
}

/**
 * Odtwarzacz YouTube (IFrame API) z własnymi kontrolkami.
 * status: idle (brak utworu) | loading | playing | paused | stopped
 */
export function useRadioPlayer() {
  const status = ref('idle')
  const current = shallowRef(null)
  const position = ref(0)
  const duration = ref(0)
  const volume = ref(readVolume())
  const muted = ref(false)
  const ready = ref(false)
  const failed = ref(false)

  let player = null
  let pending = null
  let ticker = 0
  let stallTimer = 0
  const listeners = { ended: () => {}, error: () => {} }

  const isActive = computed(() => ['playing', 'paused', 'loading'].includes(status.value))

  function on(event, fn) {
    listeners[event] = fn
  }

  async function attach(container) {
    try {
      const YT = await loadYouTubeApi()
      // YT podmienia element na iframe, więc dajemy mu własny węzeł poza kontrolą Vue.
      const host = document.createElement('div')
      container.appendChild(host)
      player = new YT.Player(host, {
        width: '100%',
        height: '100%',
        playerVars: {
          autoplay: 0,
          controls: 0,
          disablekb: 1,
          fs: 0,
          iv_load_policy: 3,
          playsinline: 1,
          rel: 0,
          origin: window.location.origin,
        },
        events: {
          onReady: () => {
            ready.value = true
            player.setVolume(volume.value)
            if (pending) {
              const { item, autoplay } = pending
              pending = null
              start(item, autoplay)
            }
          },
          onStateChange: (event) => handleState(event.data),
          onError: (event) => {
            stopTicker()
            clearTimeout(stallTimer)
            listeners.error(event.data, current.value)
          },
        },
      })
    } catch {
      failed.value = true
    }
  }

  function handleState(state) {
    if (state === YT_STATE.PLAYING) {
      clearTimeout(stallTimer)
      status.value = 'playing'
      syncDuration()
      startTicker()
    } else if (state === YT_STATE.PAUSED) {
      stopTicker()
      sample()
      if (status.value !== 'stopped') status.value = 'paused'
    } else if (state === YT_STATE.BUFFERING) {
      if (status.value === 'playing') status.value = 'loading'
    } else if (state === YT_STATE.ENDED) {
      stopTicker()
      position.value = duration.value
      listeners.ended(current.value)
    }
  }

  function sample() {
    if (!player?.getCurrentTime) return
    position.value = player.getCurrentTime() || 0
    syncDuration()
  }

  function syncDuration() {
    const d = player?.getDuration?.()
    if (d && d > 1) duration.value = d
  }

  function startTicker() {
    stopTicker()
    ticker = setInterval(sample, 250)
  }

  function stopTicker() {
    clearInterval(ticker)
  }

  // Gdy przeglądarka zablokuje autoodtwarzanie, utwór wisi w "loading". Wtedy pokazujemy pauzę.
  function armStallGuard() {
    clearTimeout(stallTimer)
    stallTimer = setTimeout(() => {
      const state = player?.getPlayerState?.()
      if (status.value === 'loading' && state !== YT_STATE.PLAYING && state !== YT_STATE.BUFFERING) {
        status.value = 'paused'
      }
    }, 6000)
  }

  function start(item, autoplay = true) {
    current.value = item
    position.value = 0
    duration.value = item.durationSeconds || 0
    if (!player || !ready.value) {
      pending = { item, autoplay }
      status.value = autoplay ? 'loading' : 'stopped'
      return
    }
    if (autoplay) {
      status.value = 'loading'
      player.loadVideoById(item.videoId)
      armStallGuard()
    } else {
      status.value = 'stopped'
      player.cueVideoById(item.videoId)
    }
  }

  function play() {
    if (!player || !ready.value || !current.value) return
    if (status.value !== 'playing') status.value = 'loading'
    player.playVideo()
    armStallGuard()
  }

  function pause() {
    if (!player || !ready.value) return
    player.pauseVideo()
    stopTicker()
    status.value = 'paused'
  }

  function stop() {
    if (!player || !ready.value) return
    player.stopVideo()
    stopTicker()
    clearTimeout(stallTimer)
    position.value = 0
    status.value = current.value ? 'stopped' : 'idle'
  }

  function eject() {
    if (player && ready.value) player.stopVideo()
    stopTicker()
    clearTimeout(stallTimer)
    pending = null
    current.value = null
    position.value = 0
    duration.value = 0
    status.value = 'idle'
  }

  function seek(seconds) {
    if (!player || !ready.value || !current.value) return
    const s = Math.max(0, Math.min(seconds, duration.value || seconds))
    player.seekTo(s, true)
    position.value = s
  }

  function setVolume(value) {
    volume.value = Math.min(100, Math.max(0, Math.round(value)))
    player?.setVolume?.(volume.value)
    if (muted.value && volume.value > 0) toggleMute(false)
    try {
      localStorage.setItem('rg-volume', String(volume.value))
    } catch {
      // głośność nie przetrwa odświeżenia
    }
  }

  function toggleMute(force) {
    muted.value = typeof force === 'boolean' ? force : !muted.value
    if (!player?.mute) return
    if (muted.value) player.mute()
    else player.unMute()
  }

  function destroy() {
    stopTicker()
    clearTimeout(stallTimer)
    try {
      player?.destroy?.()
    } catch {
      // iframe mógł już zniknąć razem z komponentem
    }
    player = null
  }

  return {
    status,
    current,
    position,
    duration,
    volume,
    muted,
    ready,
    failed,
    isActive,
    on,
    attach,
    start,
    play,
    pause,
    stop,
    eject,
    seek,
    setVolume,
    toggleMute,
    destroy,
  }
}

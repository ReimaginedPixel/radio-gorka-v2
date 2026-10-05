<template>
  <section class="np-slab slab" :class="{ 'is-live': state === 'playing' }" aria-label="Teraz gra">
    <img :src="mic" alt="Mikrofon Radio Górka" class="np-mic floaty" width="202" height="374" />
    <div class="screen">
      <div class="screen-head np-head">
        <span class="dot" :class="{ 'is-live': state === 'playing', 'is-paused': state === 'paused' }" />
        <LedText class="screen-label" :text="label" />
      </div>
      <div class="np">
        <span class="np-cover">
          <Transition name="cover">
            <img v-if="track" :key="track.videoId" :src="track.thumbnail" alt="" />
            <img v-else key="off" :src="logo" alt="" class="is-logo" />
          </Transition>
        </span>
        <div class="np-body">
          <Transition name="meta" mode="out-in">
            <div :key="track?.videoId || 'off'" class="np-meta">
              <div class="np-title ellipsis">{{ track ? track.title : 'Teraz nic nie gra' }}</div>
              <div class="np-artist ellipsis">{{ track ? track.artist : 'Zgłoś utwór, który ma polecieć' }}</div>
            </div>
          </Transition>
          <div class="np-bar" role="progressbar" :aria-valuenow="Math.round(progress * 100)" aria-valuemin="0" aria-valuemax="100">
            <div class="np-fill" :style="{ transform: `scaleX(${progress})` }" />
          </div>
          <div class="np-time led">
            <span class="np-elapsed tabular">{{ track ? clock(elapsed) : '0:00' }}</span>
            <span class="np-total tabular">{{ track ? clock(total) : '--:--' }}</span>
            <EqBars :playing="state === 'playing'" class="np-eq" />
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import logo from '../assets/img/logo.png'
import mic from '../assets/img/mic.png'
import { clock } from '../lib/format'
import EqBars from './EqBars.vue'
import LedText from './LedText.vue'

const props = defineProps({
  nowPlaying: { type: Object, default: null },
  receivedAt: { type: Number, default: 0 },
})

const state = computed(() => props.nowPlaying?.state || 'stopped')
const track = computed(() => (['playing', 'paused'].includes(state.value) ? props.nowPlaying?.track : null))
const total = computed(() => props.nowPlaying?.duration || track.value?.durationSeconds || 0)

const label = computed(() => {
  if (state.value === 'playing') return 'Radio Górka / Live'
  if (state.value === 'paused') return 'Radio Górka / Pauza'
  return 'Radio Górka / Off air'
})

// Serwer podaje pozycję w chwili odpowiedzi, dalej liczymy sami między odpytaniami.
const now = ref(Date.now())
let timer = 0
watch(
  state,
  (s) => {
    clearInterval(timer)
    now.value = Date.now()
    if (s === 'playing') timer = setInterval(() => (now.value = Date.now()), 500)
  },
  { immediate: true },
)
onBeforeUnmount(() => clearInterval(timer))

const elapsed = computed(() => {
  const base = props.nowPlaying?.position || 0
  const extra = state.value === 'playing' ? Math.max(0, (now.value - props.receivedAt) / 1000) : 0
  return total.value ? Math.min(total.value, base + extra) : base + extra
})

const progress = computed(() => (track.value && total.value ? Math.min(1, elapsed.value / total.value) : 0))
</script>

<style scoped>
.np-slab {
  margin-top: 80px;
}

.np-slab.is-live {
  box-shadow: 0 28px 64px -24px var(--acc);
}

.np-mic {
  position: absolute;
  right: 14px;
  top: -86px;
  height: 116px;
  width: auto;
  z-index: 2;
  pointer-events: none;
  filter: drop-shadow(0 14px 18px rgba(20, 16, 33, 0.55));
}

.np-head {
  padding-right: 74px;
}

.np {
  display: flex;
  gap: 13px;
  align-items: center;
}

.np-cover {
  position: relative;
  width: 74px;
  height: 74px;
  border-radius: 16px;
  flex: none;
  overflow: hidden;
  background: linear-gradient(140deg, #2f2946, #141120);
}

.np-cover img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.np-cover img.is-logo {
  object-fit: contain;
  padding: 14px;
  opacity: 0.85;
}

.np-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 9px;
}

.np-meta {
  min-width: 0;
}

.np-title {
  font-size: 15px;
  font-weight: 600;
  color: #f6f4ff;
}

.np-artist {
  font-size: 13px;
  color: #9691a9;
}

.np-bar {
  height: 6px;
  border-radius: 99px;
  background: rgba(255, 255, 255, 0.12);
  overflow: hidden;
}

.np-fill {
  height: 100%;
  border-radius: 99px;
  background: var(--acc);
  transform-origin: left;
  transition: transform 0.5s linear;
}

.np-time {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.np-elapsed {
  font-size: 24px;
  color: #f6f4ff;
  letter-spacing: 1px;
}

.np-total {
  font-size: 14px;
  color: #8f8aa6;
  letter-spacing: 1px;
}

.np-eq {
  margin-left: auto;
  align-self: center;
  color: var(--acc);
}

.cover-enter-active,
.cover-leave-active {
  transition: opacity 0.5s ease, transform 0.6s var(--ease-out);
}

.cover-enter-from {
  opacity: 0;
  transform: scale(1.12);
}

.cover-leave-to {
  opacity: 0;
}

.meta-enter-active,
.meta-leave-active {
  transition: opacity 0.2s ease, transform 0.25s var(--ease-out);
}

.meta-enter-from {
  opacity: 0;
  transform: translateY(6px);
}

.meta-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}
</style>

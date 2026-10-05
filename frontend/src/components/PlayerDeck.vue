<template>
  <section ref="root" class="deck" aria-label="Odtwarzacz">
    <img :src="headphones" alt="" class="deck-hp" width="413" height="379" />
    <div class="slab deck-slab" :class="{ 'is-live': isPlaying }">
      <div class="screen deck-screen">
        <div class="screen-head">
          <span class="dot" :class="{ 'is-live': status === 'playing', 'is-paused': status === 'paused' || status === 'loading' }" />
          <LedText class="screen-label" :text="label" />
          <span class="deck-count led tabular">KOLEJKA {{ pad2(queueCount) }}</span>
        </div>

        <div class="deck-video">
          <div ref="mount" class="deck-mount" />
          <Transition name="fade">
            <div v-if="!current" class="deck-empty">
              <img :src="logo" alt="" />
              <span>{{ emptyText }}</span>
            </div>
          </Transition>
        </div>

        <Transition name="meta" mode="out-in">
          <div :key="current?.id ?? 'none'" class="deck-meta">
            <div class="deck-title ellipsis">{{ current ? current.title : 'Nic nie gra' }}</div>
            <div class="deck-artist ellipsis">{{ subline }}</div>
          </div>
        </Transition>

        <div class="deck-scrub">
          <input
            class="range"
            type="range"
            min="0"
            :max="Math.max(1, duration)"
            step="0.5"
            :value="shownPosition"
            :disabled="!current"
            :style="{ '--pct': `${pct}%` }"
            aria-label="Pozycja w utworze"
            @input="onScrub"
            @change="onSeek"
          />
          <div class="deck-times led tabular">
            <span>{{ current ? clock(shownPosition) : '-:--' }}</span>
            <span>{{ current ? `-${clock(Math.max(0, duration - shownPosition))}` : '-:--' }}</span>
          </div>
        </div>

        <div class="deck-controls">
          <button type="button" class="deck-btn" :disabled="!current" aria-label="Od początku" title="Od początku" @click="$emit('restart')">
            <Icon name="restart" :size="18" />
          </button>
          <button type="button" class="deck-btn" :disabled="!current || status === 'stopped'" aria-label="Stop" title="Stop" @click="$emit('stop')">
            <Icon name="stop" :size="16" />
          </button>
          <button
            type="button"
            class="deck-play"
            :class="{ 'is-loading': status === 'loading' }"
            :disabled="!current && !queueCount"
            :aria-label="isPlaying ? 'Pauza' : 'Odtwórz'"
            :title="isPlaying ? 'Pauza (spacja)' : 'Odtwórz (spacja)'"
            @click="$emit('toggle')"
          >
            <Transition name="swap" mode="out-in">
              <Icon :key="isPlaying ? 'pause' : 'play'" :name="isPlaying ? 'pause' : 'play'" :size="24" />
            </Transition>
          </button>
          <button type="button" class="deck-btn" :disabled="!current" aria-label="Następny" title="Następny (N)" @click="$emit('next')">
            <Icon name="next" :size="18" />
          </button>
          <div class="deck-vol">
            <button type="button" class="deck-btn is-small" :aria-label="muted ? 'Włącz dźwięk' : 'Wycisz'" @click="player.toggleMute()">
              <Icon :name="muted || volume === 0 ? 'mute' : 'volume'" :size="17" />
            </button>
            <input
              class="range is-vol"
              type="range"
              min="0"
              max="100"
              :value="muted ? 0 : volume"
              :style="{ '--pct': `${muted ? 0 : volume}%` }"
              aria-label="Głośność"
              @input="(e) => player.setVolume(Number(e.target.value))"
            />
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import headphones from '../assets/img/headphones.png'
import logo from '../assets/img/logo.png'
import { clock, pad2 } from '../lib/format'
import Icon from './Icon.vue'
import LedText from './LedText.vue'

const props = defineProps({
  player: { type: Object, required: true },
  queueCount: { type: Number, default: 0 },
  nextUp: { type: Object, default: null },
})

const emit = defineEmits(['toggle', 'stop', 'next', 'restart', 'seek'])

const { status, current, position, duration, volume, muted, failed } = props.player

const root = ref(null)
const mount = ref(null)
const scrubbing = ref(false)
const scrubValue = ref(0)

const isPlaying = computed(() => status.value === 'playing' || status.value === 'loading')
const shownPosition = computed(() => (scrubbing.value ? scrubValue.value : position.value))
const pct = computed(() => (duration.value ? Math.min(100, (shownPosition.value / duration.value) * 100) : 0))

const label = computed(() => {
  switch (status.value) {
    case 'playing':
      return 'Na antenie'
    case 'loading':
      return 'Ładuję'
    case 'paused':
      return 'Pauza'
    case 'stopped':
      return 'Stop'
    default:
      return props.queueCount ? 'Gotowy' : 'Cisza'
  }
})

const emptyText = computed(() => {
  if (failed.value) return 'Nie udało się załadować odtwarzacza YouTube. Odśwież stronę.'
  return props.queueCount ? 'Wciśnij play, żeby zacząć od pierwszego utworu w kolejce' : 'Zaakceptuj zgłoszenie, żeby coś zagrało'
})

const subline = computed(() => {
  if (current.value) return current.value.artist
  return props.nextUp ? `Następny: ${props.nextUp.title}` : 'Kolejka jest pusta'
})

function onScrub(e) {
  scrubbing.value = true
  scrubValue.value = Number(e.target.value)
}

function onSeek(e) {
  const value = Number(e.target.value)
  scrubbing.value = false
  emit('seek', value)
}

onMounted(() => props.player.attach(mount.value))

defineExpose({ root })
</script>

<style scoped>
.deck {
  position: relative;
  padding-top: 84px;
}

/* słuchawki leżą za urządzeniem, dolną część zasłania obudowa */
.deck-hp {
  position: absolute;
  top: 0;
  left: 26px;
  height: 114px;
  width: auto;
  z-index: 0;
  pointer-events: none;
  filter: drop-shadow(0 10px 16px rgba(0, 0, 0, 0.45));
  animation: hp-bob 7s ease-in-out infinite;
}

@keyframes hp-bob {
  0%,
  100% {
    transform: translateY(0) rotate(-2deg);
  }
  50% {
    transform: translateY(6px) rotate(1deg);
  }
}

.deck-slab {
  z-index: 1;
}

.deck-slab.is-live {
  box-shadow: 0 28px 64px -24px var(--acc);
}

.deck-count {
  font-size: 11px;
  color: #8f8aa6;
  flex: none;
}

.deck-video {
  position: relative;
  aspect-ratio: 16 / 9;
  border-radius: 12px;
  overflow: hidden;
  background: #07060b;
}

.deck-mount {
  position: absolute;
  inset: 0;
}

.deck-mount :deep(iframe) {
  width: 100%;
  height: 100%;
  display: block;
  border: 0;
}

.deck-empty {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 16px;
  text-align: center;
  font-size: 13px;
  color: #9691a9;
  background: radial-gradient(ellipse at 50% 40%, #1c1828, #07060b 75%);
  text-wrap: pretty;
}

.deck-empty img {
  width: 64px;
  opacity: 0.8;
}

.deck-meta {
  min-width: 0;
}

.deck-title {
  font-size: 16px;
  font-weight: 650;
  color: #f6f4ff;
}

.deck-artist {
  font-size: 13px;
  color: #9691a9;
}

.deck-scrub {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.deck-times {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  color: #cfc6ff;
}

.range {
  -webkit-appearance: none;
  appearance: none;
  width: 100%;
  height: 18px;
  background: transparent;
  cursor: pointer;
  margin: 0;
  --track: rgba(255, 255, 255, 0.12);
}

.range:disabled {
  cursor: default;
  opacity: 0.5;
}

.range::-webkit-slider-runnable-track {
  height: 6px;
  border-radius: 99px;
  background: linear-gradient(to right, var(--acc) var(--pct), var(--track) var(--pct));
}

.range::-moz-range-track {
  height: 6px;
  border-radius: 99px;
  background: linear-gradient(to right, var(--acc) var(--pct), var(--track) var(--pct));
}

.range::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 16px;
  height: 16px;
  margin-top: -5px;
  border-radius: 50%;
  background: #f6f4ff;
  border: 0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.5);
  transition: transform 0.15s var(--ease-out);
}

.range::-moz-range-thumb {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #f6f4ff;
  border: 0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.5);
}

.range:active::-webkit-slider-thumb {
  transform: scale(1.2);
}

.deck-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.deck-btn {
  width: 42px;
  height: 42px;
  flex: none;
  border-radius: 13px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.05);
  color: #f6f4ff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  cursor: pointer;
  transition: background-color 0.15s, transform 0.18s var(--ease-out), opacity 0.2s;
}

.deck-btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.11);
}

.deck-btn:active:not(:disabled) {
  transform: scale(0.92);
}

.deck-btn:disabled {
  opacity: 0.35;
  cursor: default;
}

.deck-btn.is-small {
  width: 36px;
  height: 36px;
  border-color: transparent;
  background: transparent;
}

.deck-play {
  position: relative;
  width: 58px;
  height: 58px;
  flex: none;
  border-radius: 50%;
  border: 0;
  background: var(--acc);
  color: #141021;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  cursor: pointer;
  box-shadow: 0 10px 24px -10px var(--acc);
  transition: filter 0.15s, transform 0.2s var(--ease-spring), opacity 0.2s;
}

.deck-play:hover:not(:disabled) {
  filter: brightness(1.12);
}

.deck-play:active:not(:disabled) {
  transform: scale(0.9);
}

.deck-play:disabled {
  opacity: 0.4;
  cursor: default;
}

/* obracający się pierścień podczas buforowania */
.deck-play.is-loading::after {
  content: '';
  position: absolute;
  inset: -5px;
  border-radius: 50%;
  border: 2px solid transparent;
  border-top-color: var(--acc);
  animation: rg-spin 0.9s linear infinite;
}

.deck-vol {
  margin-left: auto;
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 2px;
  min-width: 0;
}

.range.is-vol {
  flex: 1;
  min-width: 40px;
  max-width: 110px;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.35s ease;
}

.fade-enter-from,
.fade-leave-to {
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

.swap-enter-active,
.swap-leave-active {
  transition: transform 0.18s var(--ease-out), opacity 0.15s;
}

.swap-enter-from,
.swap-leave-to {
  transform: scale(0.5);
  opacity: 0;
}

@media (max-width: 380px) {
  .deck-controls {
    gap: 6px;
  }

  .deck-btn {
    width: 38px;
    height: 38px;
  }
}
</style>

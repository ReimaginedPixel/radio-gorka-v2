<template>
  <Transition name="mini">
    <div v-if="visible && current" class="mini" role="region" aria-label="Mini odtwarzacz">
      <button type="button" class="mini-jump" aria-label="Przewiń do odtwarzacza" @click="$emit('jump')">
        <span class="thumb mini-thumb"><img :src="current.thumbnail" alt="" /></span>
        <span class="t-body">
          <span class="t-title">{{ current.title }}</span>
          <span class="t-sub">{{ current.artist }}</span>
        </span>
      </button>
      <EqBars :playing="status === 'playing'" class="mini-eq" />
      <button type="button" class="icon-btn mini-play" :aria-label="isPlaying ? 'Pauza' : 'Odtwórz'" @click="$emit('toggle')">
        <Icon :name="isPlaying ? 'pause' : 'play'" :size="16" />
      </button>
      <button type="button" class="icon-btn" aria-label="Następny" @click="$emit('next')">
        <Icon name="next" :size="15" />
      </button>
      <div class="mini-progress" :style="{ transform: `scaleX(${progress})` }" aria-hidden="true" />
    </div>
  </Transition>
</template>

<script setup>
import { computed } from 'vue'
import EqBars from './EqBars.vue'
import Icon from './Icon.vue'

const props = defineProps({
  player: { type: Object, required: true },
  visible: { type: Boolean, default: false },
})

defineEmits(['toggle', 'next', 'jump'])

const { status, current, position, duration } = props.player
const isPlaying = computed(() => status.value === 'playing' || status.value === 'loading')
const progress = computed(() => (duration.value ? Math.min(1, position.value / duration.value) : 0))
</script>

<style scoped>
.mini {
  position: fixed;
  left: 50%;
  bottom: 16px;
  translate: -50% 0;
  width: min(520px, calc(100% - 32px));
  z-index: 650;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 18px;
  padding: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
  box-shadow: 0 20px 44px -18px rgba(0, 0, 0, 0.8);
  overflow: hidden;
}

.mini-jump {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 10px;
  border: 0;
  background: transparent;
  padding: 0;
  cursor: pointer;
  text-align: left;
}

.mini-thumb {
  width: 42px;
  height: 42px;
  border-radius: 11px;
}

.mini-eq {
  color: var(--acc);
}

.mini-play {
  background: var(--acc);
  border-color: transparent;
  color: var(--accInk);
}

.mini-play:hover:not(:disabled) {
  background: var(--acc);
  color: var(--accInk);
  filter: brightness(1.12);
}

.mini-progress {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 2px;
  background: var(--acc);
  transform-origin: left;
  transition: transform 0.25s linear;
}

.mini-enter-active,
.mini-leave-active {
  transition: transform 0.38s var(--ease-out), opacity 0.25s ease;
}

.mini-enter-from,
.mini-leave-to {
  transform: translateY(24px);
  opacity: 0;
}
</style>

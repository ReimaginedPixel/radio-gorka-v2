<template>
  <div class="swipe" :data-leave="leave || undefined">
    <div class="swipe-under" :class="dx > 0 ? 'is-accept' : dx < 0 ? 'is-reject' : ''" :style="{ opacity: underOpacity }" aria-hidden="true">
      <span class="under-label is-accept"><Icon name="check" :size="16" :stroke="2.4" /> Akceptuj</span>
      <span class="under-label is-reject">Odrzuć <Icon name="x" :size="16" :stroke="2.4" /></span>
    </div>
    <div
      ref="row"
      class="track-row inbox-row"
      :class="{ 'is-selected': selected, 'is-dragging': dragging }"
      :style="{ transform: dx ? `translateX(${dx}px) rotate(${dx / 60}deg)` : undefined }"
      @pointerdown="onDown"
      @pointermove="onMove"
      @pointerup="onUp"
      @pointercancel="onCancel"
    >
      <button
        type="button"
        class="check"
        role="checkbox"
        :aria-checked="selected"
        :aria-label="`Zaznacz ${item.title}`"
        @click="$emit('toggle')"
      >
        <Icon name="check" :size="13" :stroke="2.6" />
      </button>
      <span class="thumb" :data-inbox-thumb="item.id">
        <img :src="item.thumbnail" alt="" draggable="false" @error="(e) => (e.target.style.visibility = 'hidden')" />
      </span>
      <span class="t-body">
        <a class="t-title t-link" :href="youtubeUrl" target="_blank" rel="noopener noreferrer" draggable="false">{{ item.title }}</a>
        <span class="t-sub">{{ [item.artist, ago].filter(Boolean).join(' · ') }}</span>
      </span>
      <span class="t-dur hide-sm">{{ clock(item.durationSeconds) }}</span>
      <a class="icon-btn hide-sm" :href="youtubeUrl" target="_blank" rel="noopener noreferrer" aria-label="Posłuchaj na YouTube" title="Posłuchaj na YouTube">
        <Icon name="youtube" :size="15" />
      </a>
      <button type="button" class="icon-btn is-reject" aria-label="Odrzuć" title="Odrzuć" @click="$emit('reject')">
        <Icon name="x" :size="14" :stroke="2.2" />
      </button>
      <button type="button" class="icon-btn is-accept" aria-label="Akceptuj" title="Akceptuj" @click="$emit('accept')">
        <Icon name="check" :size="15" :stroke="2.4" />
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { clock, timeAgo } from '../lib/format'
import Icon from './Icon.vue'

const props = defineProps({
  item: { type: Object, required: true },
  selected: { type: Boolean, default: false },
  leave: { type: String, default: null },
  now: { type: Number, default: () => Date.now() },
})

const emit = defineEmits(['toggle', 'accept', 'reject'])

const youtubeUrl = computed(() => `https://www.youtube.com/watch?v=${props.item.videoId}`)
const ago = computed(() => timeAgo(props.item.createdAt, props.now))

// Przesunięcie w prawo akceptuje, w lewo odrzuca. Przyciski robią to samo, gest to tylko skrót.
const row = ref(null)
const dx = ref(0)
const dragging = ref(false)
let gesture = null

const threshold = () => Math.min(110, (row.value?.offsetWidth || 300) * 0.28)
const underOpacity = computed(() => Math.min(1, Math.abs(dx.value) / threshold()))

function onDown(e) {
  if (e.button !== 0 || e.target.closest('button, a, input')) return
  gesture = { id: e.pointerId, x: e.clientX, y: e.clientY, decided: false }
}

function onMove(e) {
  if (!gesture || gesture.id !== e.pointerId) return
  const x = e.clientX - gesture.x
  const y = e.clientY - gesture.y
  if (!gesture.decided) {
    if (Math.abs(x) < 8 && Math.abs(y) < 8) return
    gesture.decided = true
    if (Math.abs(x) < Math.abs(y) * 1.2) {
      gesture = null
      return
    }
    dragging.value = true
    row.value.setPointerCapture(e.pointerId)
  }
  dx.value = x
}

function onUp(e) {
  if (!gesture || gesture.id !== e.pointerId) return
  gesture = null
  if (!dragging.value) return
  dragging.value = false
  const limit = threshold()
  if (dx.value > limit) commit('accept')
  else if (dx.value < -limit) commit('reject')
  else dx.value = 0
}

function onCancel() {
  gesture = null
  dragging.value = false
  dx.value = 0
}

function commit(kind) {
  const width = row.value?.offsetWidth || 400
  dx.value = kind === 'accept' ? width * 1.15 : -width * 1.15
  setTimeout(() => emit(kind, { swiped: true }), 200)
}
</script>

<style scoped>
.swipe {
  position: relative;
}

.swipe-under {
  position: absolute;
  inset: 0;
  border-radius: 18px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 18px;
  font-size: 13px;
  font-weight: 600;
  pointer-events: none;
}

.swipe-under.is-accept {
  background: color-mix(in srgb, var(--acc) 22%, transparent);
  color: var(--acc);
}

.swipe-under.is-reject {
  background: color-mix(in srgb, var(--danger) 18%, transparent);
  color: var(--danger);
}

.under-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  opacity: 0;
}

.swipe-under.is-accept .under-label.is-accept,
.swipe-under.is-reject .under-label.is-reject {
  opacity: 1;
}

.inbox-row {
  touch-action: pan-y;
  -webkit-user-select: none;
  user-select: none;
  transition: transform 0.32s var(--ease-out), border-color 0.2s, background-color 0.2s;
}

.inbox-row.is-dragging {
  transition: none;
  cursor: grabbing;
}

.inbox-row.is-selected {
  border-color: var(--acc);
}

.check {
  width: 24px;
  height: 24px;
  flex: none;
  border-radius: 8px;
  border: 1.5px solid var(--line);
  background: transparent;
  color: var(--accInk);
  cursor: pointer;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  transition: background-color 0.15s, border-color 0.15s;
}

/* większe pole kliknięcia niż sam kwadrat */
.check::after {
  content: '';
  position: absolute;
  inset: -10px;
}

.check :deep(svg) {
  transform: scale(0);
  transition: transform 0.22s var(--ease-spring);
}

.inbox-row.is-selected .check {
  background: var(--acc);
  border-color: var(--acc);
}

.inbox-row.is-selected .check :deep(svg) {
  transform: scale(1);
}

.t-link:hover {
  text-decoration: underline;
}

/* wyjście z listy: akceptacja w prawo, odrzucenie w lewo */
.swipe.row-leave-active[data-leave='accept'] .thumb img {
  opacity: 0;
}

.swipe.row-leave-to[data-leave='accept'] {
  transform: translateX(36px) scale(0.98);
}

.swipe.row-leave-to[data-leave='reject'] {
  transform: translateX(-36px) scale(0.98);
}

.swipe.row-leave-active[data-leave='reject'] .inbox-row {
  border-color: color-mix(in srgb, var(--danger) 60%, transparent);
}

@media (max-width: 520px) {
  .hide-sm {
    display: none;
  }
}
</style>

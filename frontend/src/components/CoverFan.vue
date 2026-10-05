<template>
  <div ref="root" class="fan" :style="{ height: `${geom.size + 82}px` }" @pointerleave="hoverId = null">
    <button
      v-for="(item, i) in items"
      :key="item.videoId"
      :ref="(el) => setCard(item.videoId, el)"
      type="button"
      class="card"
      :class="{
        'is-busy': busyId === item.videoId,
        'is-shake': shakeId === item.videoId,
        'is-flying': flyingId === item.videoId,
      }"
      :style="cardStyle(item, i)"
      :aria-label="`${item.title}, ${item.artist}. Dodaj do kolejki`"
      @pointerenter="(e) => e.pointerType === 'mouse' && (hoverId = item.videoId)"
      @pointerdown="(e) => onPointerDown(e, item)"
      @focus="focusId = item.videoId"
      @click="onClick(item)"
    >
      <img :src="item.thumbnail" alt="" draggable="false" @error="(e) => onImgError(e, item)" />
      <span class="card-label" :style="{ opacity: !flyingId && !leaving && activeId === item.videoId ? 1 : 0 }">
        <span class="card-title">{{ item.title }}</span>
        <span class="card-artist">{{ item.artist }}</span>
      </span>
      <span v-if="busyId === item.videoId" class="card-busy">
        <svg class="spinner" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6">
          <path d="M12 3a9 9 0 1 0 9 9" stroke-linecap="round" />
        </svg>
      </span>
    </button>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { rectOf } from '../lib/motion'

const props = defineProps({
  items: { type: Array, default: () => [] },
  busyId: { type: String, default: null },
  shakeId: { type: String, default: null },
  flyingId: { type: String, default: null },
  leaving: { type: Boolean, default: false },
})

const emit = defineEmits(['pick', 'focus'])

const root = ref(null)
const width = ref(360)
const hoverId = ref(null)
const focusId = ref(null)
const dealt = ref(false)
const dealing = ref(false)
const cards = {}

function setCard(id, el) {
  if (el) cards[id] = el
  else delete cards[id]
}

// Rozmiar i odstęp liczone z szerokości, żeby żadna okładka nie chowała się prawie cała za sąsiadką.
const geom = computed(() => {
  const w = Math.max(240, width.value)
  const tight = 0.66
  const size = Math.round(Math.max(74, Math.min(136, (w - 10) / (1 + 4 * tight))))
  return { size, step: Math.round(size * tight) }
})

function slot(i, n) {
  const k = i - (n - 1) / 2
  return {
    x: k * geom.value.step,
    y: k === 0 ? 0 : k * k * 4.5 + 1.5,
    r: k * 4.5,
    z: 30 - Math.round(Math.abs(k) * 10),
  }
}

const centerId = computed(() => props.items[Math.floor((props.items.length - 1) / 2)]?.videoId || null)
const activeId = computed(() => {
  const ids = props.items.map((i) => i.videoId)
  if (hoverId.value && ids.includes(hoverId.value)) return hoverId.value
  if (focusId.value && ids.includes(focusId.value)) return focusId.value
  return centerId.value
})

watch(
  activeId,
  (id) => emit('focus', props.items.find((i) => i.videoId === id) || null),
  { immediate: true },
)

function cardStyle(item, i) {
  const b = slot(i, props.items.length)
  let { x, y, r, z } = b
  let s = 1
  let o = 1
  if (!dealt.value) {
    x = 0
    y = -70
    r = 0
    s = 0.5
    o = 0
  } else if (props.flyingId === item.videoId) {
    o = 0
  } else if (props.leaving) {
    o = 0
    s = 0.88
    y = b.y + 16
  } else if (activeId.value === item.videoId) {
    y = b.y - 14
    r = 0
    s = 1.06
    z = 90
  }
  return {
    width: `${geom.value.size}px`,
    height: `${geom.value.size}px`,
    transform: `translate(calc(-50% + ${x}px), calc(-50% + ${y}px)) rotate(${r}deg) scale(${s})`,
    opacity: o,
    zIndex: z,
    transitionDelay: dealing.value ? `${i * 55}ms` : '0ms',
  }
}

// Nowe wyniki "rozdają się" spod paska wyszukiwania jak karty.
function deal() {
  dealt.value = false
  dealing.value = true
  hoverId.value = null
  focusId.value = null
  requestAnimationFrame(() =>
    requestAnimationFrame(() => {
      dealt.value = true
      setTimeout(() => (dealing.value = false), 700)
    }),
  )
}

watch(
  () => props.items.map((i) => i.videoId).join(','),
  () => nextTick(deal),
)

// Na dotyku pierwsze stuknięcie wybiera okładkę, drugie dodaje. Mysz i klawiatura dodają od razu.
let tap = null
function onPointerDown(e, item) {
  tap = { id: item.videoId, touch: e.pointerType !== 'mouse', wasActive: activeId.value === item.videoId }
}

function onClick(item) {
  const t = tap
  tap = null
  if (props.busyId || props.flyingId || props.leaving) return
  if (t && t.id === item.videoId && t.touch && !t.wasActive) {
    focusId.value = item.videoId
    return
  }
  emit('pick', item)
}

function onImgError(e, item) {
  const fallback = `https://i.ytimg.com/vi/${item.videoId}/hqdefault.jpg`
  if (e.target.src !== fallback) e.target.src = fallback
  else e.target.style.visibility = 'hidden'
}

let observer = null
onMounted(() => {
  width.value = root.value.getBoundingClientRect().width || 360
  observer = new ResizeObserver(([entry]) => {
    width.value = entry.contentRect.width
  })
  observer.observe(root.value)
  deal()
})
onBeforeUnmount(() => observer?.disconnect())

defineExpose({
  rectFor: (id) => rectOf(cards[id]),
  focusNext: (dir) => {
    const ids = props.items.map((i) => i.videoId)
    const idx = ids.indexOf(activeId.value)
    const next = ids[(idx + dir + ids.length) % ids.length]
    focusId.value = next
    hoverId.value = null
    cards[next]?.focus()
  },
})
</script>

<style scoped>
.fan {
  position: relative;
  touch-action: manipulation;
}

.card {
  position: absolute;
  left: 50%;
  top: 50%;
  padding: 0;
  border: 1px solid rgba(255, 255, 255, 0.16);
  border-radius: 20px;
  cursor: pointer;
  overflow: hidden;
  background: linear-gradient(140deg, var(--deep), #141120);
  box-shadow: 0 16px 34px -14px rgba(0, 0, 0, 0.8);
  transition:
    transform 0.5s cubic-bezier(0.22, 0.9, 0.24, 1),
    opacity 0.45s ease,
    box-shadow 0.2s;
}

.card:hover {
  box-shadow: 0 22px 40px -12px rgba(0, 0, 0, 0.9);
}

.card:focus-visible {
  outline: 2px solid var(--acc);
  outline-offset: 3px;
}

.card.is-flying {
  transition: none;
}

.card.is-shake {
  animation: rg-shake 0.45s ease;
}

.card img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  pointer-events: none;
}

.card-label {
  position: absolute;
  inset: auto 0 0 0;
  padding: 24px 10px 10px;
  background: linear-gradient(to top, rgba(8, 6, 14, 0.94), transparent);
  display: block;
  text-align: left;
  transition: opacity 0.2s ease;
  pointer-events: none;
}

.card-title {
  display: block;
  font-size: 11.5px;
  font-weight: 600;
  color: #fff;
  line-height: 1.25;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-artist {
  display: block;
  font-size: 10.5px;
  color: rgba(255, 255, 255, 0.72);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-busy {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(8, 6, 14, 0.55);
  color: #fff;
}

.card-busy .spinner {
  width: 26px;
  height: 26px;
}
</style>

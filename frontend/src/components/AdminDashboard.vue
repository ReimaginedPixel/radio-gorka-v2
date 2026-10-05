<template>
  <div class="admin">
    <div class="admin-head">
      <div class="admin-title-wrap">
        <h1 class="admin-title">Panel administratora</h1>
        <p class="admin-sub">Odtwarzaj kolejkę i rozpatruj zgłoszenia</p>
      </div>
      <button type="button" class="btn btn-ghost btn-sm logout" @click="logout()">
        <Icon name="logout" :size="15" :stroke="1.9" />
        Wyloguj
      </button>
    </div>

    <div class="dash">
      <div class="area-deck">
        <PlayerDeck
          ref="deck"
          :player="player"
          :queue-count="queue.length"
          :next-up="queue[0] || null"
          @toggle="togglePlay"
          @stop="stop"
          @next="skip"
          @restart="restart"
          @seek="seek"
        />
      </div>

      <section class="area-inbox" aria-label="Zgłoszenia">
        <div class="section-head">
          <span class="eyebrow">ZGLOSZENIA</span>
          <CountBadge :value="inbox.length" />
        </div>

        <div v-if="inbox.length" class="toolbar panel">
          <button type="button" class="btn btn-ghost btn-sm" @click="toggleAll">{{ allSelected ? 'Odznacz wszystkie' : 'Zaznacz wszystkie' }}</button>
          <span class="toolbar-count tabular">Zaznaczono {{ selected.size }} z {{ inbox.length }}</span>
          <button type="button" class="btn btn-quiet btn-sm" :disabled="!selected.size" @click="reject([...selected])">Odrzuć</button>
          <button type="button" class="btn btn-primary btn-sm" :disabled="!selected.size" @click="accept([...selected])">Akceptuj</button>
        </div>

        <TransitionGroup name="row" tag="div" class="rows">
          <InboxRow
            v-for="item in inbox"
            :key="item.id"
            :item="item"
            :now="now"
            :selected="selected.has(item.id)"
            :leave="leaving[item.id] || null"
            @toggle="toggleSelect(item.id)"
            @accept="(opts) => accept([item.id], { fly: !opts?.swiped })"
            @reject="reject([item.id])"
          />
        </TransitionGroup>

        <div v-if="loaded && !inbox.length" class="empty inbox-empty">
          <img :src="speaker" alt="" class="empty-speaker floaty" width="233" height="311" />
          <strong>Brak nowych propozycji</strong>
          <span>Nowe zgłoszenia pojawią się tutaj same.</span>
        </div>
        <div v-else-if="!loaded" class="empty">Ładuję zgłoszenia…</div>
      </section>

      <section class="area-queue" aria-label="Kolejka">
        <div class="section-head">
          <span class="eyebrow">KOLEJKA</span>
          <button v-if="queue.length" type="button" class="btn btn-quiet btn-sm clear-btn" @click="clearAll">Wyczyść</button>
          <CountBadge :value="queue.length" />
        </div>

        <TransitionGroup name="row" tag="div" class="rows">
          <div
            v-for="(q, i) in queue"
            :key="q.id"
            class="track-row queue-row"
            :class="{ 'is-current': q.id === currentId, 'is-landing': q.landing }"
          >
            <span class="q-num led tabular">
              <EqBars v-if="q.id === currentId" :playing="player.status.value === 'playing'" />
              <template v-else>{{ pad2(i + 1) }}</template>
            </span>
            <span class="thumb" :data-queue-thumb="q.id"><img :src="q.thumbnail" alt="" @error="(e) => (e.target.style.visibility = 'hidden')" /></span>
            <span class="t-body">
              <span class="t-title">{{ q.title }}</span>
              <span class="t-sub">{{ q.id === currentId ? statusText : q.artist }}</span>
            </span>
            <span class="t-dur hide-sm">{{ clock(q.durationSeconds) }}</span>
            <button
              v-if="q.id !== currentId"
              type="button"
              class="icon-btn"
              aria-label="Zagraj teraz"
              title="Zagraj teraz"
              @click="playNow(q)"
            >
              <Icon name="play" :size="13" />
            </button>
            <button
              v-if="q.id !== currentId && i > (currentId ? 1 : 0)"
              type="button"
              class="icon-btn hide-xs"
              aria-label="Zagraj jako następny"
              title="Zagraj jako następny"
              @click="playNext(q)"
            >
              <Icon name="up" :size="15" />
            </button>
            <button type="button" class="icon-btn is-reject" aria-label="Usuń z kolejki" title="Usuń z kolejki" @click="removeItem(q)">
              <Icon name="trash" :size="14" :stroke="1.9" />
            </button>
          </div>
        </TransitionGroup>

        <div v-if="loaded && !queue.length" class="empty">
          <strong>Kolejka jest pusta</strong>
          <span>Zaakceptuj zgłoszenie, a trafi tutaj.</span>
        </div>
      </section>
    </div>

    <MiniPlayer :player="player" :visible="!deckVisible" @toggle="togglePlay" @next="skip" @jump="jumpToDeck" />
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'
import speaker from '../assets/img/speaker.png'
import { confirmDialog } from '../composables/useConfirm'
import { usePolling } from '../composables/usePolling'
import { useRadioPlayer } from '../composables/useRadioPlayer'
import { toast } from '../composables/useToast'
import { api, errorMessage, isUnauthorized, reportPlayerOnExit } from '../lib/api'
import { clock, pad2, plural } from '../lib/format'
import { flyImage, inViewport, rectOf } from '../lib/motion'
import CountBadge from './CountBadge.vue'
import EqBars from './EqBars.vue'
import Icon from './Icon.vue'
import InboxRow from './InboxRow.vue'
import MiniPlayer from './MiniPlayer.vue'
import PlayerDeck from './PlayerDeck.vue'

const emit = defineEmits(['logout'])

const player = useRadioPlayer()
const queue = ref([])
const inbox = ref([])
const selected = ref(new Set())
const leaving = reactive({})
const loaded = ref(false)
const now = ref(Date.now())
const deck = ref(null)
const deckVisible = ref(true)

const currentId = computed(() => player.current.value?.id ?? null)
const allSelected = computed(() => inbox.value.length > 0 && selected.value.size === inbox.value.length)

const statusText = computed(() => {
  const s = player.status.value
  if (s === 'playing') return 'Teraz gra'
  if (s === 'loading') return 'Ładuję…'
  if (s === 'paused') return 'Pauza'
  return 'Zatrzymany'
})

// ---------- synchronizacja z serwerem ----------

let version = 0
let inflight = 0

async function refresh() {
  const started = version
  try {
    const [s, q] = await Promise.all([api.submissions('pending'), api.queue()])
    // lokalna zmiana w trakcie zapytania: te dane mogą być starsze, poczekamy na kolejne
    if (started !== version || inflight > 0) return
    inbox.value = s.submissions
    queue.value = q.queue.map((item) => ({ ...item, landing: false }))
    const ids = new Set(inbox.value.map((i) => i.id))
    selected.value = new Set([...selected.value].filter((id) => ids.has(id)))
    loaded.value = true
  } catch (err) {
    handleError(err)
  }
}

const polling = usePolling(refresh, 4000)

async function mutate(fn) {
  version++
  inflight++
  try {
    return await fn()
  } catch (err) {
    handleError(err)
    throw err
  } finally {
    inflight--
    version++
    if (!inflight) setTimeout(() => polling.refresh(), 150)
  }
}

let loggingOut = false
function handleError(err) {
  if (isUnauthorized(err)) {
    if (!loggingOut) {
      toast('Sesja wygasła, zaloguj się ponownie', 'error')
      finishLogout()
    }
    return
  }
  toast(errorMessage(err), 'error')
}

// ---------- zgłoszenia ----------

function toggleSelect(id) {
  const next = new Set(selected.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  selected.value = next
}

function toggleAll() {
  selected.value = allSelected.value ? new Set() : new Set(inbox.value.map((i) => i.id))
}

async function accept(ids, { fly = false } = {}) {
  const items = inbox.value.filter((s) => ids.includes(s.id))
  if (!items.length) return
  const sources = fly && items.length === 1 ? [{ item: items[0], rect: rectOf(document.querySelector(`[data-inbox-thumb="${items[0].id}"]`)) }] : []

  for (const it of items) leaving[it.id] = 'accept'
  await nextTick()
  inbox.value = inbox.value.filter((s) => !ids.includes(s.id))
  queue.value = [...queue.value, ...items.map((it) => ({ ...it, status: 'accepted', landing: sources.length > 0 }))]
  selected.value = new Set([...selected.value].filter((id) => !ids.includes(id)))

  const request = mutate(() => api.accept(items.map((i) => i.id)))

  if (sources.length) {
    await nextTick()
    const { item, rect } = sources[0]
    const to = rectOf(document.querySelector(`[data-queue-thumb="${item.id}"]`))
    if (inViewport(to) && inViewport(rect)) await flyImage({ src: item.thumbnail, from: rect, to, fromRadius: 14, toRadius: 14, duration: 620 })
    queue.value = queue.value.map((q) => (q.id === item.id ? { ...q, landing: false } : q))
  }

  try {
    await request
    toast(items.length === 1 ? `Zaakceptowano: ${items[0].title}` : `Zaakceptowano ${items.length} ${plural(items.length, 'utwór', 'utwory', 'utworów')}`)
  } catch {
    // stan wróci z serwera przy najbliższym odświeżeniu
  } finally {
    for (const it of items) delete leaving[it.id]
  }
}

async function reject(ids) {
  const items = inbox.value.filter((s) => ids.includes(s.id))
  if (!items.length) return
  for (const it of items) leaving[it.id] = 'reject'
  await nextTick()
  inbox.value = inbox.value.filter((s) => !ids.includes(s.id))
  selected.value = new Set([...selected.value].filter((id) => !ids.includes(id)))
  try {
    await mutate(() => api.reject(items.map((i) => i.id)))
    toast(items.length === 1 ? `Odrzucono: ${items[0].title}` : `Odrzucono ${items.length} ${plural(items.length, 'zgłoszenie', 'zgłoszenia', 'zgłoszeń')}`)
  } catch {
    // jw.
  } finally {
    for (const it of items) delete leaving[it.id]
  }
}

// ---------- kolejka i odtwarzanie ----------

function saveOrder() {
  const ids = queue.value.map((q) => q.id)
  if (ids.length) mutate(() => api.reorder(ids)).catch(() => {})
}

// Utwór skończył się albo został pominięty: znika z kolejki, startuje następny.
function advance(how = 'played', autoplay = true) {
  const cur = player.current.value
  if (cur) {
    queue.value = queue.value.filter((q) => q.id !== cur.id)
    mutate(() => (how === 'played' ? api.played(cur.id) : api.remove(cur.id))).catch(() => {})
  }
  const next = queue.value[0]
  if (next) {
    player.start(next, autoplay)
  } else {
    player.eject()
    if (cur && how === 'played') toast('Kolejka się skończyła')
  }
}

player.on('ended', () => advance('played'))
player.on('error', (code, item) => {
  toast(`Nie da się odtworzyć „${item?.title || 'utworu'}”, pomijam`, 'error', 3600)
  advance('removed')
})

function togglePlay() {
  const s = player.status.value
  if (s === 'playing' || s === 'loading') player.pause()
  else if (player.current.value) player.play()
  else if (queue.value[0]) player.start(queue.value[0])
  else toast('Kolejka jest pusta', 'error')
}

function stop() {
  player.stop()
}

function skip() {
  if (!player.current.value) return
  advance('played', true)
}

function restart() {
  player.seek(0)
  if (player.status.value !== 'playing') player.play()
  report(true)
}

function seek(seconds) {
  player.seek(seconds)
  report(true)
}

function playNow(item) {
  queue.value = [item, ...queue.value.filter((q) => q.id !== item.id)]
  saveOrder()
  player.start(item)
}

function playNext(item) {
  const cur = queue.value.find((q) => q.id === currentId.value)
  const rest = queue.value.filter((q) => q.id !== item.id && q.id !== cur?.id)
  queue.value = cur ? [cur, item, ...rest] : [item, ...rest]
  saveOrder()
}

function removeItem(item) {
  if (item.id === currentId.value) {
    advance('removed', player.status.value === 'playing' || player.status.value === 'loading')
    return
  }
  queue.value = queue.value.filter((q) => q.id !== item.id)
  mutate(() => api.remove(item.id)).catch(() => {})
}

async function clearAll() {
  const ok = await confirmDialog({
    title: 'Czy na pewno?',
    message: 'Ta operacja usunie wszystkie utwory z kolejki i z playlisty YouTube. Nie można jej cofnąć.',
    confirmLabel: 'Tak, wyczyść',
    danger: true,
  })
  if (!ok) return
  const count = queue.value.length
  queue.value = []
  player.eject()
  try {
    await mutate(() => api.clear())
    toast(`Usunięto ${count} ${plural(count, 'utwór', 'utwory', 'utworów')} z kolejki`)
  } catch {
    // jw.
  }
}

// ---------- raportowanie stanu dla strony głównej ----------

function payload() {
  const s = player.status.value
  const cur = player.current.value
  const state = !cur ? 'stopped' : s === 'playing' || s === 'loading' ? 'playing' : s === 'paused' ? 'paused' : 'stopped'
  return {
    state,
    submissionId: cur && state !== 'stopped' ? cur.id : null,
    position: Math.round(player.position.value * 10) / 10,
    duration: Math.round(player.duration.value) || 0,
  }
}

let lastKey = ''
function report(force = false) {
  const p = payload()
  const key = `${p.state}:${p.submissionId}`
  if (!force && key === lastKey) return
  lastKey = key
  api.player(p).catch((err) => isUnauthorized(err) && handleError(err))
}

watch([player.status, player.current], () => report())
const heartbeat = setInterval(() => {
  now.value = Date.now()
  if (player.isActive.value) report(true)
}, 5000)

// ---------- wyjście ----------

async function confirmStopMusic() {
  if (!(player.status.value === 'playing' || player.status.value === 'loading')) return true
  return confirmDialog({
    title: 'Muzyka przestanie grać',
    message: 'Odtwarzacz działa w tej karcie. Jeśli wyjdziesz, radio ucichnie.',
    confirmLabel: 'Wyjdź',
    cancelLabel: 'Zostań',
  })
}

async function logout() {
  if (!(await confirmStopMusic())) return
  finishLogout()
}

function finishLogout() {
  loggingOut = true
  player.eject()
  reportPlayerOnExit({ state: 'stopped' })
  emit('logout')
}

onBeforeRouteLeave(() => (loggingOut ? true : confirmStopMusic()))

function onBeforeUnload(e) {
  if (player.status.value === 'playing' || player.status.value === 'loading') {
    e.preventDefault()
    e.returnValue = ''
  }
}

function onPageHide() {
  if (player.current.value) reportPlayerOnExit({ state: 'stopped' })
}

// Spacja: play/pauza, N: następny. Tylko gdy nie piszesz w polu i nie klikasz przycisku.
function onKey(e) {
  if (e.defaultPrevented || e.metaKey || e.ctrlKey || e.altKey) return
  if (e.target.closest?.('input, textarea, select, button, a, [contenteditable]')) return
  if (document.querySelector('[role="alertdialog"]')) return
  if (e.code === 'Space') {
    e.preventDefault()
    togglePlay()
  } else if (e.key === 'n' || e.key === 'N') {
    skip()
  }
}

function jumpToDeck() {
  deck.value?.root?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

let observer = null
onMounted(() => {
  window.addEventListener('beforeunload', onBeforeUnload)
  window.addEventListener('pagehide', onPageHide)
  window.addEventListener('keydown', onKey)
  const el = deck.value?.root
  if (el && 'IntersectionObserver' in window) {
    observer = new IntersectionObserver(([entry]) => (deckVisible.value = entry.isIntersecting), { threshold: 0.15 })
    observer.observe(el)
  }
})

onBeforeUnmount(() => {
  clearInterval(heartbeat)
  observer?.disconnect()
  window.removeEventListener('beforeunload', onBeforeUnload)
  window.removeEventListener('pagehide', onPageHide)
  window.removeEventListener('keydown', onKey)
  if (player.current.value && !loggingOut) reportPlayerOnExit({ state: 'stopped' })
  player.destroy()
  document.body.style.removeProperty('--toast-offset')
})

watch(
  () => !deckVisible.value && !!player.current.value,
  (mini) => document.body.style.setProperty('--toast-offset', mini ? '78px' : '0px'),
)
</script>

<style scoped>
.admin {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.admin-head {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.admin-title-wrap {
  flex: 1;
  min-width: 180px;
}

.admin-title {
  margin: 0;
  font-size: clamp(17px, 2.4vw, 21px);
  font-weight: 700;
  letter-spacing: -0.3px;
}

.admin-sub {
  margin: 0;
  font-size: 13.5px;
  color: var(--dim);
}

.logout {
  height: 42px;
  border-radius: 14px;
  background: var(--panel);
}

.dash {
  display: grid;
  gap: 18px;
  grid-template-columns: minmax(0, 1fr);
  grid-template-areas:
    'deck'
    'inbox'
    'queue';
}

@media (min-width: 900px) {
  .dash {
    grid-template-columns: minmax(340px, 420px) minmax(0, 1fr);
    grid-template-rows: auto 1fr;
    grid-template-areas:
      'deck inbox'
      'queue inbox';
    align-items: start;
  }
}

.area-deck {
  grid-area: deck;
  min-width: 0;
}

.area-inbox {
  grid-area: inbox;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 9px;
}

.area-queue {
  grid-area: queue;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 9px;
}

@media (min-width: 900px) {
  .area-inbox {
    padding-top: 84px;
  }
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 9px;
  flex-wrap: wrap;
  border-radius: 18px;
  padding: 10px 12px;
}

.toolbar-count {
  flex: 1;
  font-size: 13px;
  font-weight: 500;
  color: var(--dim);
  min-width: 110px;
}

.rows {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 9px;
}

.rows > .row-leave-active {
  position: absolute;
  left: 0;
  right: 0;
}

.clear-btn {
  height: 30px;
  padding: 0 10px;
  font-size: 12px;
}

.q-num {
  width: 22px;
  flex: none;
  text-align: center;
  font-size: 12px;
  color: var(--dim);
  display: flex;
  justify-content: center;
}

.queue-row.is-current {
  border-color: var(--acc);
  background: color-mix(in srgb, var(--acc) 8%, var(--panel));
}

.queue-row.is-current .q-num {
  color: var(--acc);
}

.queue-row.is-landing .thumb img {
  opacity: 0;
}

.queue-row.is-landing.row-enter-from {
  opacity: 1;
  transform: none;
}

.inbox-empty {
  gap: 10px;
}

.empty-speaker {
  width: 132px;
  height: auto;
  animation-duration: 7s;
  filter: drop-shadow(0 18px 22px rgba(0, 0, 0, 0.45));
}

@media (max-width: 520px) {
  .hide-sm {
    display: none;
  }

  .toolbar .btn-quiet,
  .toolbar .btn-primary {
    flex: 1;
  }
}

@media (max-width: 430px) {
  .hide-xs {
    display: none;
  }
}
</style>

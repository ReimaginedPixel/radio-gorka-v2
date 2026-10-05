<template>
  <div class="home">
    <div class="col-left">
      <NowPlaying :now-playing="live.nowPlaying" :received-at="live.receivedAt" />
      <div class="readouts">
        <div class="readout panel">
          <span class="eyebrow">W KOLEJCE</span>
          <span class="readout-num led tabular">{{ pad2(live.queue.length) }}</span>
        </div>
        <div class="readout panel">
          <span class="eyebrow">CZEKA NA DJ-A</span>
          <span class="readout-num led tabular">{{ pad2(live.pendingCount) }}</span>
        </div>
      </div>
    </div>

    <div class="col-right">
      <form class="search panel" role="search" @submit.prevent="doSearch">
        <Icon name="search" class="search-icon" />
        <label for="q" class="sr-only">Szukaj utworu</label>
        <input
          id="q"
          ref="searchInput"
          v-model="query"
          class="search-input"
          type="text"
          inputmode="search"
          enterkeyhint="search"
          autocomplete="off"
          maxlength="150"
          placeholder="Szukaj utworu na YT Music…"
        />
        <button class="btn btn-primary search-btn" type="submit" :disabled="searching || !query.trim()">
          <svg v-if="searching" class="spinner" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6">
            <path d="M12 3a9 9 0 1 0 9 9" stroke-linecap="round" />
          </svg>
          <span>{{ searching ? 'Szukam' : 'Szukaj' }}</span>
        </button>
      </form>

      <Transition name="block">
        <section v-if="pageItems.length" class="results" aria-label="Wyniki wyszukiwania" @keydown="onFanKey">
          <div class="results-inner">
          <div class="section-head">
            <span class="eyebrow">STUKNIJ OKLADKE</span>
            <span class="results-count">{{ results.length }} {{ plural(results.length, 'wynik', 'wyniki', 'wyników') }}</span>
            <button v-if="pages > 1" type="button" class="btn btn-quiet btn-sm" :disabled="!!adding" @click="nextPage">
              <Icon name="shuffle" :size="15" />
              Inne
            </button>
          </div>
          <CoverFan
            ref="fan"
            :items="pageItems"
            :busy-id="adding"
            :shake-id="shakeId"
            :flying-id="flyingId"
            :leaving="leaving"
            @pick="pick"
            @focus="focused = $event"
          />
          <div class="caption panel" :class="{ 'is-hidden': leaving }">
            <Transition name="meta" mode="out-in">
              <div v-if="focused" :key="focused.videoId" class="caption-text">
                <span class="t-title">{{ focused.title }}</span>
                <span class="t-sub">{{ [focused.artist, clock(focused.durationSeconds)].filter((x) => x && x !== '--:--').join(' · ') }}</span>
              </div>
            </Transition>
            <button type="button" class="btn btn-primary btn-sm" :disabled="!focused || !!adding" @click="pick(focused)">
              <Icon name="plus" :size="15" :stroke="2.2" />
              Dodaj
            </button>
          </div>
          </div>
        </section>
      </Transition>

      <div v-if="noResults" class="empty">
        <strong>Nic nie znaleźliśmy dla „{{ lastQuery }}”</strong>
        <span>Wpisz wykonawcę i tytuł, na przykład „Alan Walker Faded”.</span>
      </div>

      <section class="queue" aria-label="Kolejka">
        <div class="section-head">
          <span class="eyebrow">KOLEJKA</span>
          <CountBadge :value="live.queue.length" />
        </div>

        <p v-if="offline" class="notice">Brak połączenia z serwerem, próbuję ponownie…</p>

        <TransitionGroup name="row" tag="div" class="rows">
          <div
            v-for="row in rows"
            :key="row.key"
            class="track-row"
            :class="{ 'is-mine': row.mine, 'is-landing': row.item.landing, 'is-rejected': row.item.status === 'rejected' }"
          >
            <span class="q-num led tabular" aria-hidden="true">{{ row.position ? pad2(row.position) : '--' }}</span>
            <span class="thumb" :data-thumb="row.position ? null : `req-${row.item.id}`">
              <img :src="row.thumbnail" alt="" @error="hideImg" />
            </span>
            <span class="t-body">
              <span class="t-title">{{ row.item.title }}</span>
              <span class="t-sub">{{ row.item.artist }}</span>
            </span>
            <span v-if="row.chip" class="chip" :class="row.chipClass">{{ row.chip }}</span>
            <span v-if="row.position" class="t-dur hide-xs">{{ clock(row.item.durationSeconds) }}</span>
            <button
              v-if="row.dismissable"
              type="button"
              class="icon-btn"
              :aria-label="row.item.status === 'pending' ? 'Wycofaj zgłoszenie' : 'Ukryj'"
              :title="row.item.status === 'pending' ? 'Wycofaj zgłoszenie' : 'Ukryj'"
              @click="dropMine(row.item)"
            >
              <Icon name="x" :size="14" :stroke="2" />
            </button>
          </div>
        </TransitionGroup>

        <div v-if="!mineOpen.length && !live.queue.length" class="empty">
          <strong>Kolejka jest pusta</strong>
          <span>Wyszukaj utwór i stuknij okładkę, żeby go zgłosić.</span>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, reactive, ref } from 'vue'
import CountBadge from '../components/CountBadge.vue'
import CoverFan from '../components/CoverFan.vue'
import Icon from '../components/Icon.vue'
import NowPlaying from '../components/NowPlaying.vue'
import { useMyRequests } from '../composables/useMyRequests'
import { usePolling } from '../composables/usePolling'
import { toast } from '../composables/useToast'
import { api, errorMessage } from '../lib/api'
import { clock, pad2, plural } from '../lib/format'
import { flyImage, rectOf } from '../lib/motion'

const PAGE = 5

const query = ref('')
const lastQuery = ref('')
const searching = ref(false)
const searched = ref(false)
const results = ref([])
const page = ref(0)
const focused = ref(null)

const adding = ref(null)
const shakeId = ref(null)
const flyingId = ref(null)
const leaving = ref(false)

const fan = ref(null)
const searchInput = ref(null)

const live = reactive({ nowPlaying: null, queue: [], pendingCount: 0, receivedAt: 0 })
const offline = ref(false)

const mine = useMyRequests()
const myIds = mine.ids

const pages = computed(() => Math.ceil(results.value.length / PAGE))
const pageItems = computed(() => results.value.slice(page.value * PAGE, page.value * PAGE + PAGE))
const noResults = computed(() => searched.value && !searching.value && !results.value.length && lastQuery.value)

const queueIds = computed(() => new Set(live.queue.map((q) => q.id)))
const playingId = computed(() => live.nowPlaying?.submissionId ?? null)

// Własne zgłoszenia zostają na górze, dopóki nie pojawią się w publicznej kolejce albo nie zagrają.
const mineOpen = computed(() =>
  mine.requests.value.filter(
    (r) => !queueIds.value.has(r.id) && r.id !== playingId.value && !r.nowPlaying && ['pending', 'accepted', 'rejected'].includes(r.status),
  ),
)

const localThumbs = computed(() => new Map(mine.requests.value.map((r) => [r.id, r.thumbnail])))
const thumbFor = (q) => localThumbs.value.get(q.id) || q.thumbnail

function mineLabel(r) {
  if (r.status === 'pending') return 'Czeka na DJ-a'
  if (r.status === 'accepted') return 'W kolejce'
  return 'Odrzucone'
}

// Jedna lista z jednym szablonem wiersza: zaakceptowane zgłoszenie płynnie zjeżdża na swoje miejsce w kolejce.
const rows = computed(() => [
  ...mineOpen.value.map((r) => ({
    key: `r${r.id}`,
    item: r,
    mine: true,
    position: 0,
    thumbnail: r.thumbnail,
    chip: mineLabel(r),
    chipClass: `is-${r.status}`,
    dismissable: r.status !== 'accepted',
  })),
  ...live.queue.map((q, i) => ({
    key: `r${q.id}`,
    item: q,
    mine: myIds.value.has(q.id),
    position: i + 1,
    thumbnail: thumbFor(q),
    chip: myIds.value.has(q.id) ? 'Twoje' : '',
    chipClass: 'is-accepted',
    dismissable: false,
  })),
])

async function refreshLive() {
  try {
    const [data] = await Promise.all([api.live(), mine.refresh().catch(() => {})])
    Object.assign(live, data, { receivedAt: Date.now() })
    offline.value = false
  } catch {
    offline.value = true
  }
}

usePolling(refreshLive, 5000)

async function doSearch() {
  const q = query.value.trim()
  if (!q || searching.value || adding.value) return
  searching.value = true
  searchInput.value?.blur()
  try {
    const data = await api.search(q)
    results.value = data.results || []
    page.value = 0
    lastQuery.value = q
    searched.value = true
  } catch (err) {
    toast(errorMessage(err, 'Błąd podczas wyszukiwania'), 'error')
  } finally {
    searching.value = false
  }
}

function nextPage() {
  page.value = (page.value + 1) % pages.value
}

function onFanKey(e) {
  if (e.key === 'ArrowRight') fan.value?.focusNext(1)
  else if (e.key === 'ArrowLeft') fan.value?.focusNext(-1)
  else return
  e.preventDefault()
}

const wait = (ms) => new Promise((r) => setTimeout(r, ms))

async function pick(item) {
  if (!item || adding.value || leaving.value) return
  adding.value = item.videoId
  try {
    const res = await api.submit(item.videoId)
    const request = {
      id: res.id,
      ticket: res.ticket,
      videoId: res.videoId,
      title: res.title || item.title,
      artist: item.artist || res.artist,
      thumbnail: item.thumbnail || res.thumbnail,
      durationSeconds: res.durationSeconds ?? item.durationSeconds,
      status: res.status,
      createdAt: res.createdAt,
    }
    mine.add(request)
    await nextTick()

    // Okładka leci do swojego miejsca w kolejce. Jeśli to miejsce jest pod ekranem, najpierw przewijamy.
    const thumbEl = document.querySelector(`[data-thumb="req-${request.id}"]`)
    let to = rectOf(thumbEl)
    if (to && to.top + to.height > window.innerHeight - 12) {
      window.scrollBy({ top: to.top + to.height - window.innerHeight + 40, behavior: 'smooth' })
      await wait(380)
      to = rectOf(thumbEl)
    }
    const from = fan.value?.rectFor(item.videoId)
    adding.value = null
    flyingId.value = item.videoId
    leaving.value = true
    await flyImage({ src: item.thumbnail, from, to })
    mine.land(request.id)
    toast(`Zgłoszono: ${request.title}`)
    results.value = []
    searched.value = false
  } catch (err) {
    shakeId.value = item.videoId
    setTimeout(() => (shakeId.value = null), 500)
    toast(errorMessage(err, 'Nie udało się zgłosić utworu'), 'error')
  } finally {
    adding.value = null
    flyingId.value = null
    leaving.value = false
  }
}

async function dropMine(r) {
  if (r.status !== 'pending') {
    mine.forget(r.id)
    return
  }
  try {
    await mine.cancel(r)
    toast('Zgłoszenie wycofane')
  } catch (err) {
    toast(errorMessage(err, 'Nie udało się wycofać zgłoszenia'), 'error')
    mine.refresh().catch(() => {})
  }
}

function hideImg(e) {
  e.target.style.visibility = 'hidden'
}
</script>

<style scoped>
.home {
  display: flex;
  flex-wrap: wrap;
  gap: 18px;
  align-items: flex-start;
}

.col-left {
  flex: 1 1 320px;
  min-width: 290px;
  max-width: 440px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.col-right {
  flex: 2 1 380px;
  min-width: 290px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

@media (min-width: 760px) {
  .col-left {
    position: sticky;
    top: 20px;
  }
}

.readouts {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.readout {
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  border-radius: 18px;
}

.readout .eyebrow {
  font-size: 11px;
}

.readout-num {
  font-size: 26px;
  line-height: 1;
  color: var(--ink);
}

.search {
  padding: 9px;
  display: flex;
  gap: 8px;
  align-items: center;
  transition: border-color 0.2s;
}

.search:focus-within {
  border-color: color-mix(in srgb, var(--acc) 60%, transparent);
}

.search-icon {
  color: var(--dim);
  margin-left: 7px;
  flex: none;
}

.search-input {
  flex: 1;
  min-width: 0;
  border: 0;
  outline: none;
  background: transparent;
  color: var(--ink);
  font-size: 15px;
  padding: 9px 0;
}

.search-input::placeholder {
  color: var(--dim);
}

.search-btn {
  min-width: 98px;
}

/* blok wyników rozwija się i zwija wysokością, więc kolejka pod nim nie skacze */
.results {
  display: grid;
  grid-template-rows: 1fr;
}

.results-inner {
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.results .section-head .eyebrow {
  flex: 1;
}

.results-count {
  font-size: 13px;
  color: var(--dim);
}

.caption {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 8px 8px 14px;
  border-radius: 16px;
  transition: opacity 0.3s ease, transform 0.3s var(--ease-out);
}

.caption.is-hidden {
  opacity: 0;
  transform: translateY(8px);
}

.caption-text {
  flex: 1;
  min-width: 0;
}

.queue {
  display: flex;
  flex-direction: column;
  gap: 9px;
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

.q-num {
  width: 22px;
  flex: none;
  text-align: center;
  font-size: 12px;
  color: var(--dim);
}

.track-row.is-mine {
  border-color: color-mix(in srgb, var(--acc) 38%, var(--line));
}

.track-row.is-rejected {
  opacity: 0.6;
}

.track-row.is-landing .thumb img {
  opacity: 0;
}

/* wiersz, do którego leci okładka, stoi od razu na miejscu, żeby trafić w niego dokładnie */
.track-row.is-landing.row-enter-from {
  opacity: 1;
  transform: none;
}

.track-row:not(.is-landing) .thumb img {
  transition: opacity 0.15s;
}

.notice {
  margin: 0;
  padding: 0 5px;
  font-size: 13px;
  color: var(--warn);
}

.block-enter-active,
.block-leave-active {
  transition: grid-template-rows 0.42s var(--ease-out), opacity 0.3s ease, margin 0.42s var(--ease-out);
}

.block-enter-active .results-inner,
.block-leave-active .results-inner {
  overflow: hidden;
}

.block-enter-from,
.block-leave-to {
  grid-template-rows: 0fr;
  opacity: 0;
  margin-bottom: -14px;
}

.meta-enter-active,
.meta-leave-active {
  transition: opacity 0.16s ease, transform 0.2s var(--ease-out);
}

.meta-enter-from {
  opacity: 0;
  transform: translateY(4px);
}

.meta-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

@media (max-width: 420px) {
  .hide-xs {
    display: none;
  }
}
</style>

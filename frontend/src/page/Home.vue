<template>
  <div class="min-h-screen flex flex-col items-center py-10 px-4 relative overflow-hidden bg-retro-bg">
    <header class="relative z-10 text-center mb-8">
      <div class="inline-flex items-center justify-center w-28 h-28 mb-4" style="box-shadow: 1px 1px 75px 15px #39FF14; border-radius: 50%; overflow: hidden;">
        <img v-if="!imageError" src="/logo.png" alt="Radio Górka" class="w-full h-full object-cover" @error="imageError = true" />
        <span v-else class="text-6xl">📻</span>
      </div>
      <h1 class="text-4xl md:text-5xl font-bold neon-text mb-2">Radio Górka</h1>
      <p class="text-xl text-retro-pink max-w-xl">Zaproponuj utwór albo zagłosuj na kolejkę. Najpopularniejsze prośby trafiają prosto do DJ-ów.</p>
    </header>

    <div class="relative z-10 w-full max-w-2xl flex flex-col gap-5">
      <!-- Status: cel dnia, limit, konto -->
      <div class="neon-box rounded-lg p-4 flex flex-col sm:flex-row gap-4 sm:items-center sm:justify-between">
        <GoalMeter :played="board?.goal.played_today || 0" :goal="board?.goal.daily_goal || 0" />
        <div v-if="me" class="sm:text-right text-lg leading-tight">
          <p class="text-retro-green">
            Propozycje na dziś: <span class="font-orbitron">{{ me.remaining_today }}</span> / {{ me.daily_limit }}
          </p>
          <p v-if="me.account" class="text-retro-cyan">
            {{ me.account.name }}
            <button type="button" class="underline ml-1 text-retro-pink" @click="logoutGorka">Wyloguj</button>
          </p>
          <button v-else-if="me.gorka_enabled" type="button" class="underline text-retro-cyan" @click="showGorka = true">
            Zaloguj przez Górkę i proponuj więcej
          </button>
        </div>
      </div>

      <div v-if="me && !me.requests_open" class="neon-box rounded-lg p-4 text-center text-xl text-retro-gold">
        Prośby są teraz zamknięte. Kolejkę możesz dalej przeglądać i głosować.
      </div>

      <!-- Wyszukiwarka -->
      <div class="neon-box rounded-lg p-5">
        <form class="flex flex-col sm:flex-row gap-3" @submit.prevent="search">
          <input
            v-model="query"
            type="search"
            enterkeyhint="search"
            placeholder="Szukaj utworu na YT Music..."
            aria-label="Szukaj utworu"
            class="retro-input rounded-lg px-4 py-3 text-lg focus:outline-none focus:ring-2 focus:ring-pink-500"
            style="width: 100%;"
          />
          <button
            type="submit"
            :disabled="loading"
            class="retro-button rounded-lg px-6 py-3 shadow-lg flex items-center justify-center gap-2 min-w-[140px]"
          >
            <svg v-if="loading" class="animate-spin h-5 w-5" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"/>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
            </svg>
            <span>{{ loading ? 'Szukam...' : 'Wyszukaj' }}</span>
          </button>
        </form>
      </div>

      <ul v-if="results.length > 0" class="flex flex-col gap-3">
        <SongRow
          v-for="item in results"
          :key="item.videoId"
          :video-id="item.videoId"
          :title="item.title"
          :artist="item.artist"
          :duration="item.duration_seconds"
        >
          <template v-if="item.state === 'queued'" #meta>
            <p class="text-sm text-retro-cyan">
              {{ item.status === 'approved' ? 'Zatwierdzone, leci wkrótce' : 'Już w kolejce, dorzuć swój głos' }}
            </p>
          </template>
          <template #actions>
            <VoteButton
              v-if="item.state === 'queued'"
              :votes="item.votes"
              :voted="item.voted_by_me"
              :busy="!!busy[item.videoId]"
              @toggle="toggleVoteOnResult(item)"
            />
            <button
              v-else-if="item.state === 'new'"
              type="button"
              :disabled="!canSuggest || !!busy[item.videoId]"
              class="retro-button-green rounded-lg px-4 py-2 shadow-lg flex items-center gap-2 whitespace-nowrap disabled:opacity-50 disabled:cursor-not-allowed"
              @click="suggest(item)"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
              </svg>
              {{ suggestLabel }}
            </button>
            <span v-else class="rounded-lg px-3 py-2 border border-retro-silver text-retro-silver whitespace-nowrap">
              {{ STATE_LABELS[item.state] || 'Niedostępne' }}
            </span>
          </template>
        </SongRow>
      </ul>

      <p v-else-if="searched && !loading" class="text-center text-retro-pink">Brak wyników. Spróbuj wpisać inną frazę.</p>

      <!-- Kolejka / Moje prośby / Zagrane dziś -->
      <div class="neon-box rounded-lg p-4 sm:p-5">
        <div role="tablist" class="flex flex-wrap gap-2 mb-5">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            role="tab"
            type="button"
            :aria-selected="activeTab === tab.key"
            class="rounded-lg px-3 py-2 font-orbitron text-sm border transition"
            :class="activeTab === tab.key
              ? 'bg-retro-pink text-white border-retro-pink'
              : 'border-retro-pink text-retro-pink hover:bg-retro-pink/20'"
            @click="activeTab = tab.key"
          >
            {{ tab.label }} <span class="opacity-80">({{ tab.count }})</span>
          </button>
        </div>

        <section v-if="activeTab === 'queue'">
          <p v-if="queue.length === 0" class="text-center text-retro-green text-xl py-6">
            Kolejka jest pusta. Wyszukaj utwór i bądź pierwszy!
          </p>
          <template v-if="approvedQueue.length">
            <h3 class="text-lg font-orbitron text-retro-green mb-3">Zatwierdzone, lecą wkrótce</h3>
            <ul class="flex flex-col gap-3 mb-6">
              <SongRow
                v-for="item in approvedQueue"
                :key="item.id"
                :video-id="item.video_id"
                :title="item.title"
                :artist="item.artist"
                :duration="item.duration_seconds"
                highlight
              >
                <template #meta>
                  <p class="text-sm"><StatusChip status="approved" /> <span v-if="item.mine" class="text-retro-gold ml-1">twoja prośba</span></p>
                </template>
                <template #actions>
                  <VoteButton :votes="item.votes" :voted="item.voted_by_me" :busy="!!busy['q' + item.id]" @toggle="toggleVoteOnQueue(item)" />
                </template>
              </SongRow>
            </ul>
          </template>
          <template v-if="pendingQueue.length">
            <h3 class="text-lg font-orbitron text-retro-cyan mb-1">Czekają na DJ-a</h3>
            <p class="text-retro-pink mb-3">Im więcej głosów, tym wyżej na liście DJ-ów.</p>
            <ol class="flex flex-col gap-3">
              <SongRow
                v-for="(item, index) in pendingQueue"
                :key="item.id"
                :video-id="item.video_id"
                :title="item.title"
                :artist="item.artist"
                :duration="item.duration_seconds"
              >
                <template #before>
                  <span class="font-orbitron text-2xl text-retro-cyan w-8 text-center shrink-0">{{ index + 1 }}</span>
                </template>
                <template v-if="item.mine" #meta>
                  <p class="text-sm text-retro-gold">twoja prośba</p>
                </template>
                <template #actions>
                  <VoteButton :votes="item.votes" :voted="item.voted_by_me" :busy="!!busy['q' + item.id]" @toggle="toggleVoteOnQueue(item)" />
                </template>
              </SongRow>
            </ol>
          </template>
        </section>

        <section v-else-if="activeTab === 'mine'">
          <p v-if="!me || me.suggestions.length === 0" class="text-center text-retro-green text-xl py-6">
            Nie masz jeszcze żadnych próśb. Wyszukaj coś powyżej.
          </p>
          <ul v-else class="flex flex-col gap-3">
            <SongRow
              v-for="item in me.suggestions"
              :key="item.id"
              :video-id="item.video_id"
              :title="item.title"
              :artist="item.artist"
              :duration="item.duration_seconds"
            >
              <template #meta>
                <div class="text-sm flex flex-wrap items-center gap-2 mt-1">
                  <StatusChip :status="item.status" />
                  <span class="text-retro-silver">{{ item.votes }} {{ votesWord(item.votes) }}</span>
                  <span v-if="item.status === 'played'" class="text-retro-gold">zagrane {{ formatTime(item.played_at) }}</span>
                  <span v-if="item.status === 'rejected' && item.reject_reason" class="text-retro-pink">powód: {{ item.reject_reason }}</span>
                </div>
              </template>
            </SongRow>
          </ul>
        </section>

        <section v-else>
          <p v-if="!board || board.played.length === 0" class="text-center text-retro-green text-xl py-6">
            Dziś jeszcze nic z próśb nie poleciało.
          </p>
          <ul v-else class="flex flex-col gap-3">
            <SongRow
              v-for="item in board.played"
              :key="item.id"
              :video-id="item.video_id"
              :title="item.title"
              :artist="item.artist"
            >
              <template #meta>
                <p class="text-sm text-retro-gold">zagrane {{ formatTime(item.played_at) }} · {{ item.votes }} {{ votesWord(item.votes) }}</p>
              </template>
            </SongRow>
          </ul>
        </section>
      </div>
    </div>

    <!-- Logowanie przez Górkę -->
    <div
      v-if="showGorka"
      class="fixed inset-0 z-50 flex items-center justify-center px-4"
      style="background: rgba(0,0,0,0.75);"
      @click.self="showGorka = false"
    >
      <form class="neon-box rounded-lg p-6 w-full max-w-sm flex flex-col gap-4" @submit.prevent="loginGorka">
        <h2 class="text-xl font-bold neon-text">Zaloguj przez Górkę</h2>
        <p class="text-retro-pink">Masz więcej propozycji dziennie, a twoje głosy działają na każdym urządzeniu.</p>
        <input v-model="gorkaForm.username" class="retro-input rounded-lg px-4 py-3" style="width: 100%;" placeholder="Login" autocomplete="username" required />
        <input v-model="gorkaForm.password" type="password" class="retro-input rounded-lg px-4 py-3" style="width: 100%;" placeholder="Hasło" autocomplete="current-password" required />
        <p v-if="gorkaError" class="text-retro-pink">{{ gorkaError }}</p>
        <div class="flex gap-3 justify-end">
          <button type="button" class="retro-button rounded-lg" @click="showGorka = false">Anuluj</button>
          <button type="submit" class="retro-button-green rounded-lg" :disabled="gorkaLoading">
            {{ gorkaLoading ? 'Loguję...' : 'Zaloguj' }}
          </button>
        </div>
      </form>
    </div>

    <div v-if="notification" class="fixed bottom-6 right-6 left-6 sm:left-auto z-50" role="status">
      <div
        class="neon-box rounded-lg px-6 py-4 flex items-center gap-3"
        :style="notification.type === 'success' ? 'border-color: #39FF14;' : ''"
      >
        <span :class="notification.type === 'success' ? 'text-retro-green' : 'text-retro-pink'">
          {{ notification.type === 'success' ? '✓' : '✕' }}
        </span>
        <p class="text-retro-pink">{{ notification.message }}</p>
      </div>
    </div>

    <p class="mt-8 text-retro-pink">© Radio Górka</p>
    <GitHubButton href="https://github.com/ReimaginedPixel/radio-gorka-v2" />
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import api, { errorMessage, leaveAccount, switchToAccount } from '../api'
import { formatTime, startPolling, votesWord } from '../format'
import GitHubButton from './GitHubButton.vue'
import GoalMeter from '../components/GoalMeter.vue'
import SongRow from '../components/SongRow.vue'
import StatusChip from '../components/StatusChip.vue'
import VoteButton from '../components/VoteButton.vue'

const STATE_LABELS = {
  played_recently: 'Grane niedawno',
  rejected_recently: 'Odrzucone niedawno',
  blocked: 'Niedostępne',
  too_long: 'Za długie',
}

// Na wspólnym komputerze w pokoju konto wylogowuje się samo po chwili bezczynności.
const STATION_LOGOUT_MS = 3 * 60 * 1000
const STATION_FLAG = 'voter_prev_station'

const query = ref('')
const results = ref([])
const loading = ref(false)
const searched = ref(false)
const notification = ref(null)
const imageError = ref(false)

const me = ref(null)
const queue = ref([])
const board = ref(null)
const activeTab = ref('queue')
const busy = reactive({})

const showGorka = ref(false)
const gorkaForm = reactive({ username: '', password: '' })
const gorkaLoading = ref(false)
const gorkaError = ref('')

const approvedQueue = computed(() => queue.value.filter((q) => q.status === 'approved'))
const pendingQueue = computed(() => queue.value.filter((q) => q.status === 'pending'))

const tabs = computed(() => [
  { key: 'queue', label: 'Kolejka', count: queue.value.length },
  { key: 'mine', label: 'Moje prośby', count: me.value?.suggestions.length || 0 },
  { key: 'played', label: 'Zagrane dziś', count: board.value?.goal.played_today || 0 },
])

const canSuggest = computed(() => !!me.value && me.value.requests_open && me.value.remaining_today > 0)

const suggestLabel = computed(() => {
  if (me.value && !me.value.requests_open) return 'Zamknięte'
  if (me.value && me.value.remaining_today <= 0) return 'Limit na dziś'
  return 'Zaproponuj'
})

let notificationTimer = null
const showNotification = (message, type = 'success') => {
  notification.value = { message, type }
  clearTimeout(notificationTimer)
  notificationTimer = setTimeout(() => {
    notification.value = null
  }, 3500)
}

const refresh = async () => {
  const [meRes, queueRes, boardRes] = await Promise.allSettled([
    api.get('/me'),
    api.get('/queue'),
    api.get('/board'),
  ])
  if (meRes.status === 'fulfilled') me.value = meRes.value.data
  if (queueRes.status === 'fulfilled') queue.value = queueRes.value.data.queue
  if (boardRes.status === 'fulfilled') board.value = boardRes.value.data
}

const search = async () => {
  if (!query.value.trim()) return
  loading.value = true
  searched.value = true
  results.value = []
  try {
    const response = await api.get('/search', { params: { query: query.value } })
    results.value = response.data.results
  } catch (error) {
    showNotification(errorMessage(error, 'Błąd podczas wyszukiwania'), 'error')
  } finally {
    loading.value = false
  }
}

const applySuggestion = (item, suggestion) => {
  Object.assign(item, {
    state: 'queued',
    suggestion_id: suggestion.id,
    status: suggestion.status,
    votes: suggestion.votes,
    voted_by_me: suggestion.voted_by_me,
  })
}

const suggest = async (item) => {
  busy[item.videoId] = true
  try {
    const response = await api.post('/suggestions', { videoId: item.videoId })
    applySuggestion(item, response.data.suggestion)
    showNotification(
      response.data.action === 'created'
        ? `Dodano do kolejki: ${item.title}`
        : 'Ktoś już to zaproponował, dodano twój głos',
    )
    refresh()
  } catch (error) {
    showNotification(errorMessage(error, 'Błąd podczas dodawania'), 'error')
  } finally {
    busy[item.videoId] = false
  }
}

const toggleVote = async (suggestionId, voted) => {
  const url = `/suggestions/${suggestionId}/vote`
  const response = voted ? await api.delete(url) : await api.post(url)
  return response.data.suggestion
}

const toggleVoteOnResult = async (item) => {
  busy[item.videoId] = true
  try {
    applySuggestion(item, await toggleVote(item.suggestion_id, item.voted_by_me))
    refresh()
  } catch (error) {
    showNotification(errorMessage(error, 'Nie udało się zagłosować'), 'error')
  } finally {
    busy[item.videoId] = false
  }
}

const toggleVoteOnQueue = async (item) => {
  const key = 'q' + item.id
  busy[key] = true
  try {
    const suggestion = await toggleVote(item.id, item.voted_by_me)
    item.votes = suggestion.votes
    item.voted_by_me = suggestion.voted_by_me
    await refresh()
  } catch (error) {
    showNotification(errorMessage(error, 'Nie udało się zagłosować'), 'error')
  } finally {
    busy[key] = false
  }
}

const loggedInFromStation = () => {
  try {
    return localStorage.getItem(STATION_FLAG) === '1'
  } catch {
    return false
  }
}

let stationTimer = null
const armStationLogout = () => {
  clearTimeout(stationTimer)
  if (!me.value?.account || !loggedInFromStation()) return
  stationTimer = setTimeout(() => {
    logoutGorka()
  }, STATION_LOGOUT_MS)
}

const loginGorka = async () => {
  gorkaLoading.value = true
  gorkaError.value = ''
  const fromStation = !!me.value?.is_station
  try {
    const response = await api.post('/gorka/login', { ...gorkaForm })
    switchToAccount(response.data.token)
    try {
      localStorage.setItem(STATION_FLAG, fromStation ? '1' : '0')
    } catch {
      // brak storage: bez automatycznego wylogowania
    }
    showGorka.value = false
    gorkaForm.password = ''
    showNotification(
      fromStation
        ? `Cześć ${response.data.account.name}! Wylogujemy cię za 3 minuty bezczynności.`
        : `Zalogowano: ${response.data.account.name}`,
    )
    await refresh()
    armStationLogout()
  } catch (error) {
    gorkaError.value = errorMessage(error, 'Nie udało się zalogować')
  } finally {
    gorkaLoading.value = false
  }
}

const logoutGorka = async () => {
  clearTimeout(stationTimer)
  leaveAccount()
  try {
    localStorage.removeItem(STATION_FLAG)
  } catch {
    // nic
  }
  showNotification('Wylogowano')
  await refresh()
}

let stopPolling = null
onMounted(async () => {
  await refresh()
  armStationLogout()
  stopPolling = startPolling(refresh, 15000)
  window.addEventListener('pointerdown', armStationLogout)
})

onUnmounted(() => {
  stopPolling?.()
  clearTimeout(stationTimer)
  clearTimeout(notificationTimer)
  window.removeEventListener('pointerdown', armStationLogout)
})
</script>

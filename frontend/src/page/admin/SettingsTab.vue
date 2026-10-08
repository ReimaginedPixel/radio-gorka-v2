<template>
  <div class="flex flex-col gap-8">
    <section v-if="form">
      <h3 class="text-xl font-orbitron text-retro-green mb-3">Zasady próśb</h3>
      <form class="grid sm:grid-cols-2 gap-4" @submit.prevent="save">
        <label v-for="field in NUMBER_FIELDS" :key="field.key" class="flex flex-col gap-1 text-retro-pink">
          {{ field.label }}
          <input
            v-model.number="form[field.key]"
            type="number"
            :min="field.min"
            :max="field.max"
            class="retro-input rounded px-3 py-2"
            style="width: 100%;"
          />
        </label>
        <label v-for="field in TOGGLE_FIELDS" :key="field.key" class="flex items-start gap-2 text-retro-pink sm:col-span-2">
          <input v-model="form[field.key]" type="checkbox" class="accent-[#39FF14] w-5 h-5 mt-0.5" />
          <span>{{ field.label }}<br /><span class="text-retro-silver text-base">{{ field.hint }}</span></span>
        </label>
        <div class="sm:col-span-2">
          <button type="submit" class="retro-button-green rounded-lg" :disabled="saving">
            {{ saving ? 'Zapisuję...' : 'Zapisz ustawienia' }}
          </button>
        </div>
      </form>
    </section>

    <section>
      <h3 class="text-xl font-orbitron text-retro-green mb-2">Ta przeglądarka</h3>
      <p class="text-retro-pink mb-3">
        Na komputerze w pokoju radia oznacz przeglądarkę jako stanowisko. Dostaje wtedy wyższy dzienny limit,
        bo korzysta z niej wiele osób, a logowanie przez Górkę wylogowuje się tam samo.
      </p>
      <button type="button" class="retro-button rounded-lg" :disabled="isStation === null" @click="toggleStation">
        {{ isStation ? 'Stanowisko w pokoju (kliknij, żeby wyłączyć)' : 'Oznacz jako stanowisko w pokoju' }}
      </button>
    </section>

    <section>
      <h3 class="text-xl font-orbitron text-retro-green mb-2">Zablokowane</h3>
      <p class="text-retro-pink mb-3">Utwory blokujesz przy odrzucaniu. Tu możesz zablokować całego wykonawcę.</p>
      <form class="flex flex-wrap gap-2 mb-4" @submit.prevent="addArtist">
        <input
          v-model="artist"
          maxlength="255"
          placeholder="Nazwa wykonawcy"
          class="retro-input rounded px-3 py-2"
          style="width: auto; flex: 1 1 14rem;"
        />
        <button type="submit" class="retro-button rounded-lg">Zablokuj wykonawcę</button>
      </form>
      <p v-if="blocklist.length === 0" class="text-retro-silver">Nic nie jest zablokowane.</p>
      <ul v-else class="flex flex-col gap-2">
        <li v-for="item in blocklist" :key="item.id" class="flex items-center gap-3 border-b border-retro-pink/30 pb-2">
          <span class="text-retro-cyan text-sm w-24 shrink-0">{{ item.kind === 'artist' ? 'wykonawca' : 'utwór' }}</span>
          <span class="flex-1 truncate text-retro-pink">{{ item.label || item.value }}</span>
          <button type="button" class="text-retro-silver underline text-sm" @click="removeBlock(item)">Odblokuj</button>
        </li>
      </ul>
    </section>

    <section>
      <h3 class="text-xl font-orbitron text-retro-pink mb-2">Strefa niebezpieczna</h3>
      <p class="text-retro-pink mb-3">Usuwa wszystkie utwory z playlisty YouTube. Statusy próśb się nie zmieniają.</p>
      <button type="button" class="retro-button rounded-lg" :disabled="clearing" @click="showConfirm = true">
        {{ clearing ? 'Czyszczę...' : 'Wyczyść playlistę YouTube' }}
      </button>
    </section>

    <div
      v-if="showConfirm"
      class="fixed inset-0 z-50 flex items-center justify-center px-4"
      style="background: rgba(0,0,0,0.75);"
      @click.self="showConfirm = false"
    >
      <div class="neon-box rounded-lg p-8 max-w-sm w-full text-center">
        <h3 class="text-xl font-bold mb-2 neon-text">Czy na pewno?</h3>
        <p class="mb-6 text-retro-pink">Wszystkie utwory znikną z playlisty YouTube. Nie można tego cofnąć.</p>
        <div class="flex gap-3 justify-center">
          <button type="button" class="retro-button rounded-lg px-5 py-2" @click="showConfirm = false">Anuluj</button>
          <button type="button" class="retro-button rounded-lg px-5 py-2" @click="clearPlaylist">Tak, wyczyść</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { inject, onMounted, ref } from 'vue'
import api, { ensureVoterToken } from '../../api'

const NUMBER_FIELDS = [
  { key: 'daily_goal', label: 'Cel: zagranych próśb dziennie', min: 0, max: 100 },
  { key: 'max_per_day_anon', label: 'Limit propozycji dziennie (bez konta)', min: 0, max: 100 },
  { key: 'max_per_day_account', label: 'Limit propozycji dziennie (konto Górka)', min: 0, max: 100 },
  { key: 'max_per_day_station', label: 'Limit propozycji dziennie (komputer w pokoju)', min: 0, max: 1000 },
  { key: 'max_duration_s', label: 'Maksymalna długość utworu (sekundy)', min: 60, max: 3600 },
  { key: 'replay_cooldown_days', label: 'Ile dni po zagraniu nie można prosić ponownie', min: 0, max: 365 },
]

// requests_open ma tylko przełącznik w nagłówku panelu, żeby zapis formularza go nie nadpisał.
const TOGGLE_FIELDS = [
  {
    key: 'remove_when_played',
    label: 'Usuwaj zagrane utwory z playlisty YouTube',
    hint: 'Playlista zawiera wtedy tylko to, co jeszcze trzeba zagrać.',
  },
  {
    key: 'auto_mark_played',
    label: 'Automatycznie oznaczaj zagrane na podstawie historii YouTube',
    hint: 'Działa tylko, jeśli muzyka leci z tego samego konta YouTube, co backend (browser.json).',
  },
]

const { notify, onError, refreshSummary } = inject('admin')

const form = ref(null)
const saving = ref(false)
const isStation = ref(null)
const blocklist = ref([])
const artist = ref('')
const showConfirm = ref(false)
const clearing = ref(false)

const save = async () => {
  saving.value = true
  try {
    const changes = { ...form.value }
    delete changes.requests_open
    form.value = (await api.put('/admin/settings', changes)).data
    notify('Zapisano ustawienia')
    refreshSummary()
  } catch (error) {
    onError(error, 'Nie udało się zapisać')
  } finally {
    saving.value = false
  }
}

const toggleStation = async () => {
  try {
    const voterToken = await ensureVoterToken()
    const response = await api.post('/admin/station', { voter_token: voterToken, is_station: !isStation.value })
    isStation.value = response.data.is_station
    notify(isStation.value ? 'Ta przeglądarka to teraz stanowisko w pokoju' : 'To już zwykła przeglądarka')
  } catch (error) {
    onError(error, 'Nie udało się zmienić')
  }
}

const addArtist = async () => {
  if (!artist.value.trim()) return
  try {
    blocklist.value = (await api.post('/admin/blocklist', { kind: 'artist', value: artist.value.trim() })).data.items
    artist.value = ''
  } catch (error) {
    onError(error, 'Nie udało się zablokować')
  }
}

const removeBlock = async (item) => {
  try {
    blocklist.value = (await api.delete(`/admin/blocklist/${item.id}`)).data.items
  } catch (error) {
    onError(error, 'Nie udało się odblokować')
  }
}

const clearPlaylist = async () => {
  showConfirm.value = false
  clearing.value = true
  try {
    notify((await api.delete('/clear-playlist')).data.message)
  } catch (error) {
    onError(error, 'Nie udało się wyczyścić playlisty')
  } finally {
    clearing.value = false
  }
}

onMounted(async () => {
  const [settings, blocks, me] = await Promise.allSettled([
    api.get('/admin/settings'),
    api.get('/admin/blocklist'),
    api.get('/me'),
  ])
  if (settings.status === 'fulfilled') form.value = settings.value.data
  else onError(settings.reason, 'Nie udało się pobrać ustawień')
  if (blocks.status === 'fulfilled') blocklist.value = blocks.value.data.items
  if (me.status === 'fulfilled') isStation.value = me.value.data.is_station
})
</script>

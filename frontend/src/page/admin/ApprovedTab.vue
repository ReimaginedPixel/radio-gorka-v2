<template>
  <div>
    <div class="flex flex-wrap items-center gap-3 mb-4">
      <p class="text-retro-pink flex-1 min-w-[16rem]">
        Te utwory są na playliście YouTube. Gdy poleci, kliknij „Zagrane”, żeby uczniowie to zobaczyli.
      </p>
      <button type="button" class="retro-button rounded-lg text-sm" :disabled="syncing" @click="syncHistory">
        {{ syncing ? 'Sprawdzam...' : 'Sprawdź historię YouTube' }}
      </button>
    </div>

    <div v-if="loading && !items.length" class="flex justify-center py-12">
      <div class="animate-spin w-10 h-10 border-4 border-[#39FF14] border-t-transparent rounded-full"></div>
    </div>

    <p v-else-if="items.length === 0" class="text-center py-12 text-retro-green text-2xl">
      Nic nie czeka na zagranie. Zatwierdź coś w Inboxie.
    </p>

    <ul v-else class="flex flex-col gap-3">
      <SongRow
        v-for="item in items"
        :key="item.id"
        :video-id="item.video_id"
        :title="item.title"
        :artist="item.artist"
        :duration="item.duration_seconds"
      >
        <template #meta>
          <p class="text-sm text-retro-silver">
            <span class="font-orbitron text-retro-green">▲ {{ item.votes }}</span>
            · zatwierdził(a) {{ item.decided_by }} {{ formatTime(item.decided_at) }}
          </p>
        </template>
        <template #actions>
          <button
            type="button"
            class="rounded-lg px-4 py-2 font-orbitron text-sm border border-retro-gold text-retro-gold hover:bg-retro-gold hover:text-retro-bg"
            :disabled="busy.has(item.id)"
            @click="markPlayed(item)"
          >
            Zagrane
          </button>
          <button type="button" class="retro-button rounded-lg text-sm" :disabled="busy.has(item.id)" @click="withdraw(item)">
            Wycofaj
          </button>
        </template>
      </SongRow>
    </ul>
  </div>
</template>

<script setup>
import { inject, onMounted, onUnmounted, ref } from 'vue'
import api from '../../api'
import { formatTime, startPolling } from '../../format'
import SongRow from '../../components/SongRow.vue'

const { notify, onError, refreshSummary } = inject('admin')

const items = ref([])
const loading = ref(false)
const busy = ref(new Set())
const syncing = ref(false)

const load = async () => {
  loading.value = true
  try {
    const response = await api.get('/admin/suggestions', { params: { status: 'approved' } })
    items.value = response.data.suggestions
  } catch (error) {
    onError(error, 'Nie udało się pobrać listy')
  } finally {
    loading.value = false
  }
}

const act = async (item, path, body, message) => {
  busy.value = new Set(busy.value).add(item.id)
  try {
    const response = await api.post(`/admin/suggestions/${item.id}/${path}`, body)
    items.value = items.value.filter((i) => i.id !== item.id)
    notify(response.data.warning || message, response.data.warning ? 'error' : 'success')
  } catch (error) {
    onError(error, 'Operacja się nie udała')
  } finally {
    const updated = new Set(busy.value)
    updated.delete(item.id)
    busy.value = updated
    refreshSummary()
  }
}

const markPlayed = (item) => act(item, 'played', undefined, `Zagrane: ${item.title}`)

const withdraw = (item) => act(item, 'reject', { reason: 'Wycofane przez DJ-a' }, `Wycofano: ${item.title}`)

const syncHistory = async () => {
  syncing.value = true
  try {
    const response = await api.post('/admin/sync-history')
    notify(`Oznaczono jako zagrane: ${response.data.marked}`)
    await load()
    refreshSummary()
  } catch (error) {
    onError(error, 'Nie udało się sprawdzić historii')
  } finally {
    syncing.value = false
  }
}

let stopPolling = null
onMounted(() => {
  load()
  stopPolling = startPolling(load, 30000)
})
onUnmounted(() => stopPolling?.())
</script>

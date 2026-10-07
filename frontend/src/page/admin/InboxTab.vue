<template>
  <div>
    <div class="flex flex-wrap items-center gap-3 mb-4">
      <label v-if="items.length" class="flex items-center gap-2 cursor-pointer text-retro-green">
        <input type="checkbox" :checked="allSelected" class="accent-[#39FF14] w-4 h-4" @change="toggleSelectAll" />
        Zaznacz wszystkie
      </label>
      <template v-if="selected.size > 0">
        <button type="button" class="retro-button-green rounded-lg text-sm" :disabled="bulkBusy" @click="bulk('approve')">
          Zatwierdź zaznaczone ({{ selected.size }})
        </button>
        <button type="button" class="retro-button rounded-lg text-sm" :disabled="bulkBusy" @click="bulk('reject')">
          Odrzuć zaznaczone
        </button>
      </template>
      <button type="button" class="retro-button rounded-lg text-sm ml-auto" @click="load">Odśwież</button>
    </div>

    <div v-if="loading && !items.length" class="flex justify-center py-12">
      <div class="animate-spin w-10 h-10 border-4 border-[#39FF14] border-t-transparent rounded-full"></div>
    </div>

    <p v-else-if="items.length === 0" class="text-center py-12 text-retro-green text-2xl">Brak nowych propozycji</p>

    <template v-else>
      <p v-if="items[0].votes > 1" class="mb-4 text-lg text-retro-gold">
        Najczęściej proszone: „{{ items[0].title }}” ({{ items[0].votes }} {{ votesWord(items[0].votes) }}). Zagraj je, a cała szkoła zobaczy to na ekranie.
      </p>
      <ul class="flex flex-col gap-3">
        <SongRow
          v-for="(item, index) in items"
          :key="item.id"
          :video-id="item.video_id"
          :title="item.title"
          :artist="item.artist"
          :duration="item.duration_seconds"
          :highlight="selected.has(item.id) || (index < 3 && item.votes > 1)"
        >
          <template #before>
            <input
              type="checkbox"
              :checked="selected.has(item.id)"
              :aria-label="'Zaznacz ' + item.title"
              class="accent-[#39FF14] w-5 h-5 shrink-0 cursor-pointer"
              @change="toggleSelect(item.id)"
            />
          </template>
          <template #meta>
            <div class="text-sm flex flex-wrap items-center gap-x-3 gap-y-1 mt-1">
              <span class="font-orbitron text-retro-green">▲ {{ item.votes }}</span>
              <span class="text-retro-silver">{{ submitterLabel(item) }} · {{ formatTime(item.created_at) }}</span>
            </div>
            <div v-if="rejecting === item.id" class="mt-3 flex flex-col gap-2">
              <div class="flex flex-wrap gap-2">
                <button
                  v-for="reason in REASONS"
                  :key="reason"
                  type="button"
                  class="rounded px-2 py-1 text-sm border border-retro-pink text-retro-pink hover:bg-retro-pink hover:text-white"
                  @click="reject(item, reason)"
                >{{ reason }}</button>
              </div>
              <form class="flex flex-wrap gap-2 items-center" @submit.prevent="reject(item, customReason)">
                <input
                  v-model="customReason"
                  maxlength="120"
                  placeholder="Inny powód (widzi go uczeń)"
                  class="retro-input rounded px-2 py-1 text-base"
                  style="width: auto; flex: 1 1 12rem;"
                />
                <button type="submit" class="retro-button rounded text-sm">Odrzuć</button>
                <button type="button" class="text-retro-silver underline text-sm" @click="rejecting = null">Anuluj</button>
              </form>
              <label class="flex items-center gap-2 text-sm text-retro-pink">
                <input v-model="blockToo" type="checkbox" class="accent-[#FF1493]" />
                zablokuj ten utwór na stałe
              </label>
            </div>
          </template>
          <template #actions>
            <button type="button" class="retro-button-green rounded-lg text-sm" :disabled="busy.has(item.id)" @click="approve(item)">
              Zatwierdź
            </button>
            <button type="button" class="retro-button rounded-lg text-sm" :disabled="busy.has(item.id)" @click="startReject(item)">
              Odrzuć
            </button>
            <button
              v-if="!item.submitter_is_station"
              type="button"
              class="text-retro-silver underline text-sm px-1"
              title="Odrzuca wszystkie czekające prośby tej osoby i blokuje jej przeglądarkę"
              @click="banSubmitter(item)"
            >
              Zablokuj autora
            </button>
          </template>
        </SongRow>
      </ul>
    </template>
  </div>
</template>

<script setup>
import { computed, inject, onMounted, onUnmounted, ref } from 'vue'
import api from '../../api'
import { formatTime, startPolling, votesWord } from '../../format'
import SongRow from '../../components/SongRow.vue'

const REASONS = ['Nie pasuje do radia', 'Wulgarny tekst', 'Było niedawno', 'Za długie', 'Nie teraz']

const { notify, onError, refreshSummary } = inject('admin')

const items = ref([])
const loading = ref(false)
const selected = ref(new Set())
const busy = ref(new Set())
const bulkBusy = ref(false)
const rejecting = ref(null)
const customReason = ref('')
const blockToo = ref(false)

const allSelected = computed(() => items.value.length > 0 && items.value.every((i) => selected.value.has(i.id)))

const submitterLabel = (item) => {
  if (item.submitter_is_station) return 'z komputera w pokoju'
  return item.submitter_name ? `od: ${item.submitter_name}` : 'anonim'
}

const load = async () => {
  loading.value = true
  try {
    const response = await api.get('/admin/suggestions', { params: { status: 'pending' } })
    items.value = response.data.suggestions
    const ids = new Set(items.value.map((i) => i.id))
    selected.value = new Set([...selected.value].filter((id) => ids.has(id)))
  } catch (error) {
    onError(error, 'Nie udało się pobrać propozycji')
  } finally {
    loading.value = false
  }
}

const toggleSelect = (id) => {
  const updated = new Set(selected.value)
  if (updated.has(id)) updated.delete(id)
  else updated.add(id)
  selected.value = updated
}

const toggleSelectAll = () => {
  selected.value = allSelected.value ? new Set() : new Set(items.value.map((i) => i.id))
}

const removeLocally = (ids) => {
  items.value = items.value.filter((i) => !ids.has(i.id))
  selected.value = new Set([...selected.value].filter((id) => !ids.has(id)))
}

const act = async (item, path, body) => {
  busy.value = new Set(busy.value).add(item.id)
  try {
    await api.post(`/admin/suggestions/${item.id}/${path}`, body)
    removeLocally(new Set([item.id]))
    return true
  } finally {
    const updated = new Set(busy.value)
    updated.delete(item.id)
    busy.value = updated
  }
}

const approve = async (item) => {
  try {
    await act(item, 'approve')
    notify(`Zatwierdzono: ${item.title}`)
  } catch (error) {
    onError(error, 'Nie udało się zatwierdzić')
  }
  refreshSummary()
}

const startReject = (item) => {
  rejecting.value = rejecting.value === item.id ? null : item.id
  customReason.value = ''
  blockToo.value = false
}

const reject = async (item, reason) => {
  try {
    await act(item, 'reject', { reason: (reason || '').trim() || null, block: blockToo.value })
    rejecting.value = null
    notify(`Odrzucono: ${item.title}`)
  } catch (error) {
    onError(error, 'Nie udało się odrzucić')
  }
  refreshSummary()
}

const banSubmitter = async (item) => {
  if (!window.confirm('Zablokować autora tej prośby? Jego czekające prośby zostaną odrzucone.')) return
  try {
    const response = await api.post(`/admin/suggestions/${item.id}/ban-submitter`)
    notify(`Zablokowano autora, odrzucono ${response.data.rejected} próśb`)
    await load()
  } catch (error) {
    onError(error, 'Nie udało się zablokować autora')
  }
  refreshSummary()
}

const bulk = async (action) => {
  bulkBusy.value = true
  const chosen = items.value.filter((i) => selected.value.has(i.id))
  const body = action === 'reject' ? { reason: null } : undefined
  const outcomes = await Promise.allSettled(chosen.map((item) => api.post(`/admin/suggestions/${item.id}/${action}`, body)))
  const done = new Set(chosen.filter((_, i) => outcomes[i].status === 'fulfilled').map((item) => item.id))
  removeLocally(done)
  const failed = outcomes.find((o) => o.status === 'rejected')
  if (failed) onError(failed.reason, 'Część operacji się nie udała')
  else notify(action === 'approve' ? `Zatwierdzono ${done.size}` : `Odrzucono ${done.size}`)
  bulkBusy.value = false
  refreshSummary()
}

let stopPolling = null
onMounted(() => {
  load()
  stopPolling = startPolling(() => {
    if (rejecting.value === null && !bulkBusy.value) load()
  }, 20000)
})
onUnmounted(() => stopPolling?.())
</script>

<template>
  <div>
    <div class="flex flex-wrap gap-2 mb-4">
      <button
        v-for="f in FILTERS"
        :key="f.key"
        type="button"
        class="rounded-lg px-3 py-1 text-sm border transition"
        :class="filter === f.key ? 'bg-retro-cyan text-retro-bg border-retro-cyan' : 'border-retro-cyan text-retro-cyan'"
        @click="setFilter(f.key)"
      >{{ f.label }}</button>
    </div>

    <div v-if="loading" class="flex justify-center py-12">
      <div class="animate-spin w-10 h-10 border-4 border-[#39FF14] border-t-transparent rounded-full"></div>
    </div>

    <p v-else-if="items.length === 0" class="text-center py-12 text-retro-green text-2xl">Pusto</p>

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
          <div class="text-sm flex flex-wrap gap-2 items-center mt-1">
            <StatusChip :status="item.status" />
            <span class="text-retro-silver">
              {{ item.status === 'played' ? formatTime(item.played_at) : formatTime(item.decided_at) }}
              <template v-if="item.decided_by"> · {{ item.decided_by }}</template>
              · ▲ {{ item.votes }}
            </span>
            <span v-if="item.reject_reason" class="text-retro-pink">{{ item.reject_reason }}</span>
          </div>
        </template>
        <template #actions>
          <button type="button" class="retro-button rounded-lg text-sm" @click="requeue(item)">Przywróć do kolejki</button>
        </template>
      </SongRow>
    </ul>
  </div>
</template>

<script setup>
import { inject, onMounted, ref } from 'vue'
import api from '../../api'
import { formatTime } from '../../format'
import SongRow from '../../components/SongRow.vue'
import StatusChip from '../../components/StatusChip.vue'

const FILTERS = [
  { key: 'played', label: 'Zagrane' },
  { key: 'rejected', label: 'Odrzucone' },
]

const { notify, onError, refreshSummary } = inject('admin')

const filter = ref('played')
const items = ref([])
const loading = ref(false)

const load = async () => {
  loading.value = true
  try {
    const response = await api.get('/admin/suggestions', { params: { status: filter.value } })
    items.value = response.data.suggestions
  } catch (error) {
    onError(error, 'Nie udało się pobrać historii')
  } finally {
    loading.value = false
  }
}

const setFilter = (key) => {
  filter.value = key
  load()
}

const requeue = async (item) => {
  try {
    await api.post(`/admin/suggestions/${item.id}/requeue`)
    items.value = items.value.filter((i) => i.id !== item.id)
    notify(`Przywrócono do kolejki: ${item.title}`)
    refreshSummary()
  } catch (error) {
    onError(error, 'Nie udało się przywrócić')
  }
}

onMounted(load)
</script>

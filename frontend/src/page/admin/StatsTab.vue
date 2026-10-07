<template>
  <div v-if="stats">
    <div class="grid grid-cols-2 md:grid-cols-3 gap-3 mb-6">
      <div v-for="card in cards" :key="card.label" class="neon-box-accent rounded-lg p-4">
        <p class="text-retro-pink">{{ card.label }}</p>
        <p class="text-3xl font-orbitron text-retro-green">{{ card.value }}</p>
      </div>
    </div>

    <div class="grid md:grid-cols-2 gap-6">
      <section>
        <h3 class="text-lg font-orbitron text-retro-green mb-2">Najbardziej chciane (30 dni)</h3>
        <p v-if="!stats.top_songs.length" class="text-retro-pink">Brak danych</p>
        <ol class="flex flex-col gap-1">
          <li v-for="(song, i) in stats.top_songs" :key="song.video_id" class="flex gap-2 text-lg">
            <span class="text-retro-cyan w-6">{{ i + 1 }}.</span>
            <span class="flex-1 truncate text-retro-pink">{{ song.artist ? song.artist + ' - ' : '' }}{{ song.title }}</span>
            <span class="font-orbitron text-retro-green">▲ {{ song.votes }}</span>
          </li>
        </ol>
      </section>
      <section>
        <h3 class="text-lg font-orbitron text-retro-green mb-2">Najczęstsi wykonawcy (30 dni)</h3>
        <p v-if="!stats.top_artists.length" class="text-retro-pink">Brak danych</p>
        <ol class="flex flex-col gap-1">
          <li v-for="(artist, i) in stats.top_artists" :key="artist.artist" class="flex gap-2 text-lg">
            <span class="text-retro-cyan w-6">{{ i + 1 }}.</span>
            <span class="flex-1 truncate text-retro-pink">{{ artist.artist }}</span>
            <span class="font-orbitron text-retro-green">{{ artist.suggestions }}</span>
          </li>
        </ol>
      </section>
    </div>
  </div>
  <div v-else class="flex justify-center py-12">
    <div class="animate-spin w-10 h-10 border-4 border-[#39FF14] border-t-transparent rounded-full"></div>
  </div>
</template>

<script setup>
import { computed, inject, onMounted, ref } from 'vue'
import api from '../../api'

const { onError } = inject('admin')

const stats = ref(null)

const cards = computed(() => [
  { label: 'Zagrane prośby dziś', value: `${stats.value.played_today} / ${stats.value.daily_goal}` },
  { label: 'Zagrane prośby (7 dni)', value: stats.value.played_week },
  { label: 'Nowe prośby (7 dni)', value: stats.value.submitted_week },
  { label: 'Głosujący (7 dni)', value: stats.value.active_voters_week },
  {
    label: 'Zaakceptowane (30 dni)',
    value: stats.value.approval_rate === null ? '-' : `${Math.round(stats.value.approval_rate * 100)}%`,
  },
])

onMounted(async () => {
  try {
    stats.value = (await api.get('/admin/stats')).data
  } catch (error) {
    onError(error, 'Nie udało się pobrać statystyk')
  }
})
</script>

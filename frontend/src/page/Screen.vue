<template>
  <div class="fixed inset-0 overflow-auto lg:overflow-hidden bg-retro-bg">
    <div class="min-h-full grid grid-cols-1 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)] gap-8 lg:gap-12 p-6 lg:p-10">
      <aside class="flex flex-col items-center justify-between text-center gap-6">
        <div>
          <h1 class="neon-text text-5xl xl:text-6xl font-bold">Radio Górka</h1>
          <p class="text-3xl xl:text-4xl text-retro-pink mt-3">Zeskanuj i zaproponuj utwór</p>
        </div>
        <div
          class="bg-white p-4 rounded-2xl w-[min(80vw,26rem)] lg:w-[min(28vw,46vh)] [&_svg]:w-full [&_svg]:h-auto"
          style="box-shadow: 0 0 40px 8px #39FF14;"
          role="img"
          :aria-label="'Kod QR do ' + displayUrl"
          v-html="qrSvg"
        />
        <p class="text-3xl xl:text-4xl text-retro-green font-orbitron break-all">{{ displayUrl }}</p>
        <GoalMeter
          big
          :played="board?.goal.played_today || 0"
          :goal="board?.goal.daily_goal || 0"
          label="Dziś zagrane prośby"
        />
      </aside>

      <main class="flex flex-col gap-6 min-h-0">
        <div
          v-if="board && !board.requests_open"
          class="neon-box rounded-xl px-6 py-4 text-3xl text-retro-gold text-center"
        >
          Prośby są teraz zamknięte
        </div>

        <section class="flex-1 min-h-0 flex flex-col">
          <h2 class="text-4xl font-orbitron text-retro-green mb-4">Top prośby</h2>
          <p v-if="board && board.queue.length === 0" class="text-4xl text-retro-pink mt-8">
            Kolejka jest pusta. Bądź pierwszy!
          </p>
          <transition-group v-else tag="ol" name="rank" class="flex flex-col gap-3 overflow-hidden">
            <li
              v-for="(item, index) in board?.queue || []"
              :key="item.id"
              class="neon-box rounded-xl px-5 py-3 flex items-center gap-5"
              :style="item.status === 'approved' ? 'border-color: #39FF14; box-shadow: 0 0 12px #39FF14;' : ''"
            >
              <span class="font-orbitron text-4xl w-12 text-center shrink-0" :class="index === 0 ? 'text-retro-gold' : 'text-retro-cyan'">
                {{ index + 1 }}
              </span>
              <img :src="thumbnailUrl(item.video_id)" alt="" class="w-16 h-16 rounded-lg object-cover shrink-0" />
              <div class="flex-1 min-w-0">
                <p class="text-3xl text-retro-green truncate font-orbitron">{{ item.title }}</p>
                <p class="text-2xl text-retro-pink truncate">
                  {{ item.artist }}
                  <span v-if="item.status === 'approved'" class="text-retro-green"> · leci wkrótce</span>
                </p>
              </div>
              <span class="font-orbitron text-4xl text-retro-green shrink-0">▲ {{ item.votes }}</span>
            </li>
          </transition-group>
        </section>

        <section v-if="board && board.played.length">
          <h2 class="text-3xl font-orbitron text-retro-gold mb-3">Zagrane dziś na prośbę</h2>
          <ul class="flex flex-wrap gap-3">
            <li
              v-for="item in board.played.slice(0, 6)"
              :key="item.id"
              class="rounded-lg border border-retro-gold px-4 py-2 text-2xl text-retro-gold max-w-full truncate"
            >
              {{ item.artist ? item.artist + ' - ' : '' }}{{ item.title }}
            </li>
          </ul>
        </section>
      </main>
    </div>

    <p v-if="offline" class="fixed bottom-3 right-4 text-xl text-retro-silver">Brak połączenia, ponawiam...</p>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import QRCode from 'qrcode'
import api from '../api'
import { thumbnailUrl } from '../format'
import GoalMeter from '../components/GoalMeter.vue'

const REFRESH_MS = 10000

const board = ref(null)
const offline = ref(false)
const qrSvg = ref('')

const siteUrl = computed(() => board.value?.site_url || window.location.origin)
const displayUrl = computed(() => siteUrl.value.replace(/^https?:\/\//, '').replace(/\/$/, ''))

watch(siteUrl, async (url) => {
  qrSvg.value = await QRCode.toString(url, {
    type: 'svg',
    margin: 1,
    errorCorrectionLevel: 'M',
    color: { dark: '#0d0d2b', light: '#ffffff' },
  })
}, { immediate: true })

const load = async () => {
  try {
    board.value = (await api.get('/board')).data
    offline.value = false
  } catch {
    offline.value = true
  }
}

let timer = null
onMounted(() => {
  document.title = 'Radio Górka: ekran'
  load()
  timer = setInterval(load, REFRESH_MS)
})

onUnmounted(() => {
  clearInterval(timer)
  document.title = 'Radio Górka'
})
</script>

<style scoped>
.rank-move,
.rank-enter-active,
.rank-leave-active {
  transition: all 0.6s ease;
}
.rank-enter-from,
.rank-leave-to {
  opacity: 0;
  transform: translateX(40px);
}
.rank-leave-active {
  position: absolute;
}
</style>

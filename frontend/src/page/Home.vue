<template>
  <div class="min-h-screen flex flex-col items-center py-12 px-4 relative overflow-hidden" style="background-color: #0d0d2b;">
    <header class="relative z-10 text-center mb-12">
      <div class="inline-flex items-center justify-center w-32 h-32 mb-4" style="box-shadow: 1px 1px 75px 15px #39FF14; border-radius: 50%; overflow: hidden;">
        <img v-if="!imageError" src="/logo.png" alt="Radio Górka" class="w-full h-full object-cover" @error="handleImageError" />
        <span v-else class="text-6xl">📻</span>
      </div>
      <h1 class="text-4xl md:text-5xl font-bold neon-text mb-2" style="font-family: 'Orbitron', sans-serif;">Radio Górka</h1>
      <p class="text-xl" style="color: #FF1493;">Podaj utwór do wyszukania na YT Music</p>
    </header>

    <div class="relative z-10 w-full max-w-2xl">
      <div class="neon-box rounded-lg p-6">
        <div class="flex flex-col sm:flex-row gap-3">
          <input
            type="text"
            v-model="query"
            placeholder="Szukaj utworu..."
            class="retro-input rounded-lg px-4 py-3 text-lg focus:outline-none focus:ring-2 focus:ring-pink-500"
            style="width: 100%;"
            @keyup.enter="search()"
          />
          <button
            @click="search()"
            :disabled="loading"
            class="retro-button rounded-lg px-6 py-3 shadow-lg flex items-center justify-center gap-2 min-w-[140px]"
          >
            <svg v-if="loading" class="animate-spin h-5 w-5" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"/>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
            </svg>
            <span>{{ loading ? 'Szukam...' : 'Wyszukaj' }}</span>
          </button>
        </div>
      </div>
    </div>

    <div v-if="results.length > 0" class="relative z-10 w-full max-w-2xl mt-8 space-y-4">
      <transition-group name="list" tag="ul" class="flex flex-col gap-4">
        <li
          v-for="(item, index) in results"
          :key="item.videoId"
          class="neon-box rounded-lg p-4 flex flex-col sm:flex-row items-center gap-4 hover:scale-[1.02] transition-transform cursor-pointer"
        >
          <a :href="'https://www.youtube.com/watch?v=' + item.videoId" target="_blank" class="shrink-0">
            <img
              :src="'https://img.youtube.com/vi/' + item.videoId + '/default.jpg'"
              :alt="item.title"
              class="w-24 h-24 sm:w-16 sm:h-16 rounded-lg object-cover"
              style="box-shadow: 0px 0px 10px 2px #39FF14;"
            />
          </a>
          <div class="flex-1 min-w-0 text-center sm:text-left">
            <a :href="'https://www.youtube.com/watch?v=' + item.videoId" target="_blank" class="font-semibold truncate hover:underline block" style="color: #39FF14; font-family: 'Orbitron', sans-serif;">{{ item.title }}</a>
            <p class="text-sm" style="color: #FF1493;">{{ item.artist }}</p>
          </div>
          <button
            @click="add(item)"
            class="retro-button-green rounded-lg px-4 py-2 shadow-lg flex items-center gap-2 whitespace-nowrap w-full sm:w-auto justify-center"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
            </svg>
            Dodaj
          </button>
        </li>
      </transition-group>
    </div>

    <div v-else-if="searched && !loading" class="relative z-10 mt-8 text-center" style="color: #FF1493;">
      <p>Brak wyników. Spróbuj wpisać inną frazę.</p>
    </div>

    <div v-if="notification" class="fixed bottom-6 right-6 z-50">
      <div :class="[
        'neon-box rounded-lg px-6 py-4 flex items-center gap-3',
        notification.type === 'success' ? 'border-[#39FF14]' : 'border-[#FF1493]'
      ]">
        <span :class="notification.type === 'success' ? 'text-[#39FF14]' : 'text-[#FF1493]'">
          {{ notification.type === 'success' ? '✓' : '✕' }}
        </span>
        <p style="color: #FF1493;">{{ notification.message }}</p>
      </div>
    </div>

    <p class="mt-6" style="color: #FF1493;">© Radio Górka</p>
    <GitHubButton href="https://github.com/daniel-kub/radio-gorka-v2" />
  </div>
</template>

<script setup>
import { ref } from "vue";
import api from "../api";
import GitHubButton from "./GitHubButton.vue";

const query = ref("");
const results = ref([]);
const loading = ref(false);
const searched = ref(false);
const notification = ref(null);
const imageError = ref(false);

const handleImageError = (e) => {
  imageError.value = true;
  e.target.style.display = 'none';
};

const showNotification = (message, type = 'success') => {
  notification.value = { message, type };
  setTimeout(() => {
    notification.value = null;
  }, 3000);
};

const search = async () => {
  if (!query.value.trim()) return;
  
  loading.value = true;
  searched.value = true;
  results.value = [];
  
  try {
    const response = await api.get("/search", { params: { query: query.value } });
    results.value = response.data.results.filter(item => item.videoId != null);
  } catch (error) {
    console.error(error);
    showNotification('Błąd podczas wyszukiwania', 'error');
  } finally {
    loading.value = false;
  }
};

const add = async (item) => {
  try {
    await api.get("/add", { params: { videoID: item.videoId } });
    showNotification(`Dodano: ${item.title}`, 'success');
    results.value = results.value.filter(r => r.videoId !== item.videoId);
  } catch (error) {
    showNotification(error.response?.data?.detail || 'Błąd podczas dodawania', 'error');
  }
};
</script>

<style scoped>
.list-enter-active,
.list-leave-active {
  transition: all 0.4s ease;
}
.list-enter-from,
.list-leave-to {
  opacity: 0;
  transform: translateX(-30px);
}
.list-move {
  transition: transform 0.4s ease;
}
</style>

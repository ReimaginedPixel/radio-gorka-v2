<template>
  <div class="min-h-screen flex items-center justify-center p-4 relative overflow-hidden" style="background-color: #0d0d2b;">
    
    <!-- ZALOGOWANY PANEL -->
    <div v-if="logged" class="relative z-10 w-full max-w-4xl">
      <div class="neon-box rounded-lg p-6">
        
        <div class="flex items-center justify-between mb-6">
          <div>
            <h2 class="text-2xl font-bold neon-text">Propozycje utworów</h2>
            <p style="color: #FF1493;">Zarządzaj zgłoszeniami użytkowników</p>
          </div>
          <button
            @click="handleLogout"
            class="retro-button rounded-lg px-4 py-2 flex items-center gap-2"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/>
            </svg>
            Wyloguj
          </button>
        </div>

        <div v-if="loading" class="flex justify-center py-12">
          <div class="animate-spin w-10 h-10 border-4 border-[#39FF14] border-t-transparent rounded-full"></div>
        </div>

        <div v-else-if="results.length === 0" class="text-center py-12">
          <p style="color: #39FF14; font-size: 1.5em;">Brak nowych propozycji</p>
        </div>

        <div v-else>

          <!-- Pasek akcji zbiorczych -->
          <div class="flex flex-wrap gap-3 mb-6">
            <button
              v-if="selectedItems.size > 0"
              @click="deleteSelected"
              :disabled="deleteSelectedLoading"
              class="retro-button rounded-lg px-4 py-2 flex items-center gap-2 text-sm"
            >
              <svg v-if="deleteSelectedLoading" class="animate-spin h-4 w-4" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"/>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
              </svg>
              <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
              </svg>
              Usuń zaznaczone ({{ selectedItems.size }})
            </button>

            <button
              @click="confirmClearAll"
              :disabled="clearAllLoading"
              class="retro-button rounded-lg px-4 py-2 flex items-center gap-2 text-sm"
              style="border-color: #FF1493; color: #FF1493;"
            >
              <svg v-if="clearAllLoading" class="animate-spin h-4 w-4" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"/>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
              </svg>
              <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
              </svg>
              Wyczyść wszystko
            </button>
          </div>

          <!-- Modal potwierdzenia -->
          <div
            v-if="showConfirmModal"
            class="fixed inset-0 z-50 flex items-center justify-center"
            style="background: rgba(0,0,0,0.75);"
          >
            <div class="neon-box rounded-lg p-8 max-w-sm w-full mx-4 text-center">
              <svg class="w-12 h-12 mx-auto mb-4" style="color: #FF1493;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
              </svg>
              <h3 class="text-xl font-bold mb-2 neon-text">Czy na pewno?</h3>
              <p class="mb-6" style="color: #FF1493;">Ta operacja usunie wszystkie propozycje z playlisty. Nie można jej cofnąć.</p>
              <div class="flex gap-3 justify-center">
                <button
                  @click="showConfirmModal = false"
                  class="retro-button rounded-lg px-5 py-2"
                >
                  Anuluj
                </button>
                <button
                  @click="clearAll"
                  class="retro-button rounded-lg px-5 py-2"
                  style="border-color: #FF1493; color: #FF1493;"
                >
                  Tak, wyczyść
                </button>
              </div>
            </div>
          </div>

          <!-- Zwykłe propozycje -->
          <div v-if="results.length > 0">
            <div class="flex items-center gap-3 mb-4">
              <h3 class="text-xl font-bold" style="color: #39FF14; font-family: 'Orbitron', sans-serif;">
                Propozycje zwykłe
              </h3>
              <label class="flex items-center gap-2 cursor-pointer text-sm" style="color: #39FF14;">
                <input
                  type="checkbox"
                  :checked="allNormalSelected"
                  @change="toggleSelectAll('normal')"
                  class="accent-[#39FF14] w-4 h-4"
                />
                Zaznacz wszystkie
              </label>
            </div>
            <ul class="flex flex-col gap-4 mb-8">
              <li
                v-for="(item, index) in results"
                :key="item.videoID"
                class="neon-box rounded-lg p-4 flex flex-col sm:flex-row items-center gap-4 hover:scale-[1.02] transition-transform"
                :style="selectedItems.has('normal:' + item.videoID) ? 'border: 2px solid #39FF14; background: rgba(57,255,20,0.06);' : ''"
              >
                <!-- Checkbox -->
                <input
                  type="checkbox"
                  :checked="selectedItems.has('normal:' + item.videoID)"
                  @change="toggleSelect(item, 'normal')"
                  class="accent-[#39FF14] w-5 h-5 shrink-0 cursor-pointer"
                />

                <!-- Miniaturka -->
                <a :href="`https://www.youtube.com/watch?v=${item.videoID}`" target="_blank" class="shrink-0">
                  <img
                    :src="`https://img.youtube.com/vi/${item.videoID}/default.jpg`"
                    :alt="item.title"
                    class="w-24 h-24 sm:w-16 sm:h-16 rounded-lg object-cover"
                    style="box-shadow: 0px 0px 10px 2px #39FF14;"
                  />
                </a>

                <div class="flex-1 min-w-0 text-center sm:text-left">
                  <a 
                    :href="`https://www.youtube.com/watch?v=${item.videoID}`" 
                    target="_blank" 
                    class="font-semibold truncate hover:underline block" 
                    style="color: #39FF14; font-family: 'Orbitron', sans-serif;"
                  >
                    {{ item.title }}
                  </a>
                  <p style="color: #FF1493;">{{ item.author }}</p>
                </div>

                <div class="flex gap-2 w-full sm:w-auto">
                  <a 
                    :href="`https://www.youtube.com/watch?v=${item.videoID}`"
                    target="_blank"
                    class="retro-button-green rounded-lg px-3 py-2 shadow-lg flex items-center justify-center gap-1 flex-1 sm:flex-none text-sm"
                  >
                    <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M19.615 3.184c-3.604-.246-11.631-.245-15.23 0-3.897.266-4.356 2.62-4.385 8.816.029 6.185.484 8.549 4.385 8.816 3.6.245 11.626.246 15.23 0 3.897-.266 4.356-2.62 4.385-8.816-.029-6.185-.484-8.549-4.385-8.816zm-10.615 12.816v-8l8 3.993-8 4.007z"/>
                    </svg>
                    Wyświetl na Youtube
                  </a>
                  <button
                    @click="deleteItem(item, 'normal')"
                    class="retro-button rounded-lg px-3 py-2 shadow-lg flex items-center justify-center gap-1 flex-1 sm:flex-none text-sm"
                  >
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                    </svg>
                    Usuń
                  </button>
                </div>
              </li>
            </ul>
          </div>

        </div>
      </div>
    </div>

    <!-- PANEL LOGOWANIA -->
    <div v-else class="relative z-10 w-full max-w-md">
      <div class="neon-box rounded-lg p-8">
        <div class="text-center mb-8">
          <div class="inline-flex items-center justify-center w-16 h-16 mb-4 neon-box-accent rounded-lg">
            <svg class="w-8 h-8" style="color: #39FF14;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/>
            </svg>
          </div>
          <h2 class="text-2xl font-bold neon-text">Panel Administratora</h2>
          <p style="color: #FF1493;">Zaloguj się aby zarządzać</p>
        </div>

        <form @submit.prevent="handleLogin" class="space-y-5">
          <div>
            <label class="block text-sm font-medium mb-2" style="color: #FF1493;">Login</label>
            <input
              type="text"
              v-model="username"
              class="retro-input rounded-lg px-4 py-3 w-full"
              placeholder="Wpisz login"
              required
            />
          </div>

          <div>
            <label class="block text-sm font-medium mb-2" style="color: #FF1493;">Hasło</label>
            <input
              type="password"
              v-model="password"
              class="retro-input rounded-lg px-4 py-3 w-full"
              placeholder="Wpisz hasło"
              required
            />
          </div>

          <button
            type="submit"
            :disabled="loginLoading"
            class="retro-button rounded-lg px-6 py-3 shadow-lg w-full flex items-center justify-center gap-2"
          >
            <svg v-if="loginLoading" class="animate-spin h-5 w-5" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"/>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
            </svg>
            <span>{{ loginLoading ? 'Logowanie...' : 'Zaloguj się' }}</span>
          </button>
        </form>

        <p v-if="loginError" class="mt-4 text-center" style="color: #FF1493;">
          {{ loginError }}
        </p>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import api from '../api';

const logged = ref(!!localStorage.getItem('token'));
const username = ref('');
const password = ref('');
const results = ref([]);
const loading = ref(false);
const loginLoading = ref(false);
const loginError = ref('');

// Nowe stany
const selectedItems = ref(new Set());
const deleteSelectedLoading = ref(false);
const clearAllLoading = ref(false);
const showConfirmModal = ref(false);

// Computed: czy wszystkie normalne zaznaczone
const allNormalSelected = computed(() =>
  results.value.length > 0 &&
  results.value.every(item => selectedItems.value.has('normal:' + item.videoID))
);

const toggleSelect = (item, type) => {
  const key = `${type}:${item.videoID}`;
  const updated = new Set(selectedItems.value);
  if (updated.has(key)) {
    updated.delete(key);
  } else {
    updated.add(key);
  }
  selectedItems.value = updated;
};

const toggleSelectAll = (type) => {
  const updated = new Set(selectedItems.value);
  const list = results.value;
  const allSelected = list.every(item => updated.has(`${type}:${item.videoID}`));
  if (allSelected) {
    list.forEach(item => updated.delete(`${type}:${item.videoID}`));
  } else {
    list.forEach(item => updated.add(`${type}:${item.videoID}`));
  }
  selectedItems.value = updated;
};

const deleteSelected = async () => {
  deleteSelectedLoading.value = true;
  try {
    const keys = [...selectedItems.value];
    const outcomes = await Promise.allSettled(
      keys.map(key => {
        const videoID = key.split(':')[1];
        return api.delete('/delete', { params: { videoID } }).then(() => ({ key, videoID }));
      })
    );

    const deletedVideoIds = new Set();
    const remainingKeys = new Set(selectedItems.value);
    for (let i = 0; i < outcomes.length; i++) {
      const outcome = outcomes[i];
      if (outcome.status === 'fulfilled') {
        deletedVideoIds.add(outcome.value.videoID);
        remainingKeys.delete(keys[i]);
      } else {
        console.error(outcome.reason);
      }
    }

    results.value = results.value.filter(r => !deletedVideoIds.has(r.videoID));
    selectedItems.value = remainingKeys;
  } catch (error) {
    console.error(error);
  } finally {
    deleteSelectedLoading.value = false;
  }
};

const confirmClearAll = () => {
  showConfirmModal.value = true;
};

const clearAll = async () => {
  showConfirmModal.value = false;
  clearAllLoading.value = true;
  try {
    await api.delete('/clear-playlist');
    results.value = [];
    selectedItems.value = new Set();
  } catch (error) {
    console.error(error);
  } finally {
    clearAllLoading.value = false;
  }
};

onMounted(async () => {
  if (logged.value) {
    await fetchResults();
  }
});

const fetchResults = async () => {
  loading.value = true;
  try {
    const normalRes = await api.get("/list");
    results.value = normalRes.data;
  } catch (error) {
    console.error(error);
    handleLogout();
  } finally {
    loading.value = false;
  }
};

const handleLogin = async () => {
  loginLoading.value = true;
  loginError.value = '';
  try {
    const response = await api.post("/login", {
      username: username.value,
      password: password.value
    });
    const token = response.data.token;
    localStorage.setItem('token', token);
    logged.value = true;
    await fetchResults();
  } catch (error) {
    loginError.value = error.response?.data?.detail || 'Błąd logowania';
  } finally {
    loginLoading.value = false;
  }
};

const handleLogout = () => {
  localStorage.removeItem('token');
  logged.value = false;
  results.value = [];
  selectedItems.value = new Set();
};

const deleteItem = async (item, type) => {
  try {
    await api.delete('/delete', { params: { videoID: item.videoID } });
    const updated = new Set(selectedItems.value);
    updated.delete(`${type}:${item.videoID}`);
    selectedItems.value = updated;
    results.value = results.value.filter(r => r !== item);
  } catch (error) {
    console.error(error);
  }
};
</script>
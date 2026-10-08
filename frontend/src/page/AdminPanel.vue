<template>
  <div class="min-h-screen flex justify-center p-2 sm:p-4 relative bg-retro-bg">

    <!-- ZALOGOWANY PANEL -->
    <div v-if="logged" class="relative z-10 w-full max-w-5xl py-4">
      <div class="neon-box rounded-lg p-5 mb-4 flex flex-col lg:flex-row lg:items-center gap-4 lg:justify-between">
        <div>
          <h2 class="text-2xl font-bold neon-text">Panel DJ-a</h2>
          <p class="text-retro-pink">Prośby uczniów posortowane według głosów</p>
        </div>
        <GoalMeter :played="summary.played_today" :goal="summary.daily_goal" />
        <div class="flex flex-wrap gap-2">
          <button
            type="button"
            class="rounded-lg px-4 py-2 font-orbitron text-sm border"
            :class="summary.requests_open ? 'border-retro-green text-retro-green' : 'border-retro-gold text-retro-gold'"
            :title="summary.requests_open
              ? 'Kliknij, żeby zamknąć prośby (np. w czasie lekcji albo eventu)'
              : 'Kliknij, żeby otworzyć prośby'"
            @click="toggleRequestsOpen"
          >
            {{ summary.requests_open ? 'Prośby otwarte' : 'Prośby zamknięte' }}
          </button>
          <a href="/ekran" target="_blank" class="retro-button rounded-lg px-4 py-2 text-sm">Ekran w pokoju</a>
          <button type="button" class="retro-button rounded-lg px-4 py-2 text-sm" @click="handleLogout">Wyloguj</button>
        </div>
      </div>

      <div role="tablist" class="flex flex-wrap gap-2 mb-4">
        <button
          v-for="t in tabs"
          :key="t.key"
          role="tab"
          type="button"
          :aria-selected="tab === t.key"
          class="rounded-lg px-4 py-2 font-orbitron text-sm border transition"
          :class="tab === t.key
            ? 'bg-retro-pink text-white border-retro-pink'
            : 'border-retro-pink text-retro-pink hover:bg-retro-pink/20'"
          @click="tab = t.key"
        >
          {{ t.label }}<span v-if="t.count !== undefined" class="opacity-80"> ({{ t.count }})</span>
        </button>
      </div>

      <div class="neon-box rounded-lg p-3 sm:p-5">
        <InboxTab v-if="tab === 'inbox'" />
        <ApprovedTab v-else-if="tab === 'approved'" />
        <HistoryTab v-else-if="tab === 'history'" />
        <StatsTab v-else-if="tab === 'stats'" />
        <SettingsTab v-else />
      </div>
    </div>

    <!-- PANEL LOGOWANIA -->
    <div v-else class="relative z-10 w-full max-w-md self-center">
      <div class="neon-box rounded-lg p-8">
        <div class="text-center mb-8">
          <div class="inline-flex items-center justify-center w-16 h-16 mb-4 neon-box-accent rounded-lg">
            <svg class="w-8 h-8 text-retro-green" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/>
            </svg>
          </div>
          <h2 class="text-2xl font-bold neon-text">Panel Administratora</h2>
          <p class="text-retro-pink">Zaloguj się aby zarządzać</p>
        </div>

        <form @submit.prevent="handleLogin" class="space-y-5">
          <div>
            <label class="block text-sm font-medium mb-2 text-retro-pink" for="login">Login</label>
            <input
              id="login"
              type="text"
              v-model="username"
              class="retro-input rounded-lg px-4 py-3 w-full"
              placeholder="Wpisz login"
              autocomplete="username"
              required
            />
          </div>

          <div>
            <label class="block text-sm font-medium mb-2 text-retro-pink" for="password">Hasło</label>
            <input
              id="password"
              type="password"
              v-model="password"
              class="retro-input rounded-lg px-4 py-3 w-full"
              placeholder="Wpisz hasło"
              autocomplete="current-password"
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

        <p v-if="loginError" class="mt-4 text-center text-retro-pink">
          {{ loginError }}
        </p>
      </div>
    </div>

    <div v-if="notification" class="fixed bottom-6 right-6 left-6 sm:left-auto z-50" role="status">
      <div class="neon-box rounded-lg px-6 py-4" :style="notification.type === 'success' ? 'border-color: #39FF14;' : ''">
        <p :class="notification.type === 'success' ? 'text-retro-green' : 'text-retro-pink'">{{ notification.message }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, provide, reactive, ref } from 'vue'
import api, { errorMessage } from '../api'
import { startPolling } from '../format'
import GoalMeter from '../components/GoalMeter.vue'
import InboxTab from './admin/InboxTab.vue'
import ApprovedTab from './admin/ApprovedTab.vue'
import HistoryTab from './admin/HistoryTab.vue'
import StatsTab from './admin/StatsTab.vue'
import SettingsTab from './admin/SettingsTab.vue'

const readToken = () => {
  try {
    return localStorage.getItem('token')
  } catch {
    return null
  }
}

const logged = ref(!!readToken())
const username = ref('')
const password = ref('')
const loginLoading = ref(false)
const loginError = ref('')
const tab = ref('inbox')
const notification = ref(null)
const summary = reactive({
  counts: { pending: 0, approved: 0 },
  played_today: 0,
  daily_goal: 0,
  requests_open: true,
})

const tabs = computed(() => [
  { key: 'inbox', label: 'Inbox', count: summary.counts.pending },
  { key: 'approved', label: 'Do zagrania', count: summary.counts.approved },
  { key: 'history', label: 'Historia' },
  { key: 'stats', label: 'Statystyki' },
  { key: 'settings', label: 'Ustawienia' },
])

let notificationTimer = null
const notify = (message, type = 'success') => {
  notification.value = { message, type }
  clearTimeout(notificationTimer)
  notificationTimer = setTimeout(() => {
    notification.value = null
  }, 3500)
}

const handleLogout = () => {
  try {
    localStorage.removeItem('token')
  } catch {
    // nic
  }
  logged.value = false
}

const onError = (error, fallback) => {
  if (error.response?.status === 401) {
    handleLogout()
    return
  }
  notify(errorMessage(error, fallback), 'error')
}

const loadSummary = async () => {
  if (!logged.value) return
  try {
    const response = await api.get('/admin/summary')
    Object.assign(summary, response.data)
  } catch (error) {
    onError(error, 'Nie udało się pobrać podsumowania')
  }
}

provide('admin', { notify, onError, refreshSummary: loadSummary })

const toggleRequestsOpen = async () => {
  try {
    const response = await api.put('/admin/settings', { requests_open: !summary.requests_open })
    summary.requests_open = response.data.requests_open
    notify(summary.requests_open ? 'Prośby otwarte' : 'Prośby zamknięte')
  } catch (error) {
    onError(error, 'Nie udało się zmienić ustawienia')
  }
}

const handleLogin = async () => {
  loginLoading.value = true
  loginError.value = ''
  try {
    const response = await api.post('/login', {
      username: username.value,
      password: password.value,
    })
    localStorage.setItem('token', response.data.token)
    password.value = ''
    logged.value = true
    await loadSummary()
  } catch (error) {
    loginError.value = errorMessage(error, 'Błąd logowania')
  } finally {
    loginLoading.value = false
  }
}

let stopPolling = null
onMounted(() => {
  loadSummary()
  stopPolling = startPolling(loadSummary, 20000)
})

onUnmounted(() => {
  stopPolling?.()
  clearTimeout(notificationTimer)
})
</script>

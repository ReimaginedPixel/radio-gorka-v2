<template>
  <div class="login-wrap">
    <form class="login panel" :class="{ 'is-shake': shake }" novalidate @submit.prevent="submit">
      <div class="login-head">
        <div class="login-art">
          <span class="login-glow" aria-hidden="true" />
          <img :src="headphones" alt="" class="login-hp floaty" width="413" height="379" />
        </div>
        <h1 class="login-title">Panel administratora</h1>
        <p class="login-sub">Zaloguj się aby zarządzać zgłoszeniami</p>
      </div>

      <div class="login-fields">
        <label class="field">
          <span class="field-label">Login</span>
          <input
            ref="userInput"
            v-model="username"
            class="input"
            type="text"
            name="username"
            autocomplete="username"
            placeholder="admin"
            :aria-invalid="!!error"
            required
          />
        </label>
        <label class="field">
          <span class="field-label">Hasło</span>
          <input
            v-model="password"
            class="input"
            type="password"
            name="password"
            autocomplete="current-password"
            placeholder="••••••••"
            :aria-invalid="!!error"
            required
          />
        </label>
        <Transition name="err">
          <p v-if="error" class="login-error" role="alert">{{ error }}</p>
        </Transition>
      </div>

      <button class="btn btn-primary login-btn" type="submit" :disabled="loading">
        <svg v-if="loading" class="spinner" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6">
          <path d="M12 3a9 9 0 1 0 9 9" stroke-linecap="round" />
        </svg>
        <span>{{ loading ? 'Logowanie…' : 'Zaloguj się' }}</span>
      </button>
      <RouterLink to="/" class="login-back">← Wróć na stronę główną</RouterLink>
    </form>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import headphones from '../assets/img/headphones.png'
import { api, errorMessage } from '../lib/api'
import { setToken } from '../lib/session'

const emit = defineEmits(['success'])

const username = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')
const shake = ref(false)
const userInput = ref(null)

onMounted(() => userInput.value?.focus())

async function submit() {
  if (loading.value) return
  if (!username.value.trim() || !password.value) {
    fail('Wpisz login i hasło')
    return
  }
  loading.value = true
  error.value = ''
  try {
    const { token } = await api.login(username.value.trim(), password.value)
    setToken(token)
    password.value = ''
    emit('success', username.value.trim())
  } catch (err) {
    fail(errorMessage(err, 'Błąd logowania'))
  } finally {
    loading.value = false
  }
}

function fail(message) {
  error.value = message
  shake.value = false
  requestAnimationFrame(() => (shake.value = true))
  setTimeout(() => (shake.value = false), 500)
}
</script>

<style scoped>
.login-wrap {
  display: flex;
  justify-content: center;
  padding: clamp(10px, 5vw, 50px) 0;
}

.login {
  width: 100%;
  max-width: 420px;
  border-radius: 26px;
  padding: clamp(20px, 4vw, 30px);
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.login.is-shake {
  animation: rg-shake 0.45s ease;
}

.login-head {
  display: flex;
  flex-direction: column;
  gap: 6px;
  align-items: center;
  text-align: center;
}

.login-art {
  position: relative;
  height: 158px;
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.login-glow {
  position: absolute;
  width: 180px;
  height: 130px;
  border-radius: 50%;
  background: radial-gradient(circle, var(--acc), transparent 70%);
  opacity: 0.4;
  filter: blur(24px);
}

.login-hp {
  position: relative;
  height: 100%;
  width: auto;
  object-fit: contain;
  filter: drop-shadow(0 20px 24px rgba(0, 0, 0, 0.5));
}

.login-title {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  letter-spacing: -0.3px;
}

.login-sub {
  margin: 0;
  font-size: 13.5px;
  color: var(--dim);
}

.login-fields {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.field-label {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--dim);
}

.login-error {
  margin: 0;
  font-size: 13px;
  font-weight: 500;
  color: var(--danger);
}

.login-btn {
  height: 50px;
  border-radius: 15px;
  font-size: 15px;
}

.login-back {
  text-align: center;
  font-size: 13px;
  color: var(--dim);
}

.err-enter-active,
.err-leave-active {
  transition: opacity 0.2s ease, transform 0.25s var(--ease-out);
}

.err-enter-from,
.err-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>

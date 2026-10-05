<template>
  <Transition name="view" mode="out-in">
    <AdminLogin v-if="!token" key="login" @success="onLogin" />
    <AdminDashboard v-else key="dashboard" @logout="onLogout" />
  </Transition>
</template>

<script setup>
import { onMounted } from 'vue'
import AdminDashboard from '../components/AdminDashboard.vue'
import AdminLogin from '../components/AdminLogin.vue'
import { toast } from '../composables/useToast'
import { api, isUnauthorized } from '../lib/api'
import { setToken, token } from '../lib/session'

// Stary token (np. z poprzedniej wersji panelu) od razu odsyła do logowania.
onMounted(() => {
  if (token.value) api.me().catch((err) => isUnauthorized(err) && setToken(''))
})

function onLogin() {
  toast('Zalogowano')
}

function onLogout() {
  setToken('')
}
</script>

<style scoped>
.view-enter-active,
.view-leave-active {
  transition: opacity 0.25s ease, transform 0.35s var(--ease-out);
}

.view-enter-from {
  opacity: 0;
  transform: scale(0.98) translateY(8px);
}

.view-leave-to {
  opacity: 0;
  transform: scale(0.98);
}
</style>

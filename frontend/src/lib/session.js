import { ref } from 'vue'

const KEY = 'token'

function read() {
  try {
    return localStorage.getItem(KEY) || ''
  } catch {
    return ''
  }
}

export const token = ref(read())

export function setToken(value) {
  token.value = value || ''
  try {
    if (value) localStorage.setItem(KEY, value)
    else localStorage.removeItem(KEY)
  } catch {
    // tryb prywatny: sesja zostaje tylko w pamięci
  }
}

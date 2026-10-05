import { ref } from 'vue'

const toasts = ref([])
let seq = 0

export function dismiss(id) {
  toasts.value = toasts.value.filter((t) => t.id !== id)
}

export function toast(message, type = 'success', ms = 2800) {
  const id = ++seq
  toasts.value = [...toasts.value.slice(-2), { id, message, type }]
  setTimeout(() => dismiss(id), ms)
  return id
}

export function useToasts() {
  return { toasts, dismiss }
}

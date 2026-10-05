import { ref } from 'vue'

const dialog = ref(null)

export function confirmDialog({ title, message, confirmLabel = 'Tak', cancelLabel = 'Anuluj', danger = false }) {
  return new Promise((resolve) => {
    dialog.value?.resolve(false)
    dialog.value = {
      title,
      message,
      confirmLabel,
      cancelLabel,
      danger,
      resolve: (value) => {
        dialog.value = null
        resolve(value)
      },
    }
  })
}

export function useConfirmState() {
  return dialog
}

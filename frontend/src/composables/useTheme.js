import { ref, watch } from 'vue'

const root = document.documentElement
const theme = ref(root.getAttribute('data-theme') === 'light' ? 'light' : 'dark')

function apply(value) {
  root.setAttribute('data-theme', value)
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content', value === 'light' ? '#e9e7ef' : '#0a0910')
}

apply(theme.value)

watch(theme, (value) => {
  apply(value)
  try {
    localStorage.setItem('rg-theme', value)
  } catch {
    // bez zapisu, motyw wróci do domyślnego po odświeżeniu
  }
})

export function useTheme() {
  const toggle = () => {
    theme.value = theme.value === 'dark' ? 'light' : 'dark'
  }
  return { theme, toggle }
}

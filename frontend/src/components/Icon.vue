<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    :fill="filled ? 'currentColor' : 'none'"
    :stroke="filled ? 'none' : 'currentColor'"
    :stroke-width="stroke"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
    focusable="false"
  >
    <path v-for="(d, i) in paths" :key="i" :d="d" />
    <circle v-for="(c, i) in circles" :key="'c' + i" :cx="c[0]" :cy="c[1]" :r="c[2]" />
  </svg>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  name: { type: String, required: true },
  size: { type: [Number, String], default: 18 },
  stroke: { type: [Number, String], default: 1.8 },
})

// Jeden zestaw: obrys 1.8px, zaokrąglone końce. Wypełnione tylko ikony transportu.
const ICONS = {
  search: { c: [[11, 11, 7]], p: ['M16.5 16.5L21 21'] },
  sun: { c: [[12, 12, 4]], p: ['M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M19.1 4.9l-1.4 1.4M6.3 17.7l-1.4 1.4'] },
  moon: { p: ['M20 14.5A8.5 8.5 0 1 1 9.5 4a6.8 6.8 0 0 0 10.5 10.5z'] },
  x: { p: ['M6 6l12 12M18 6L6 18'] },
  check: { p: ['M5 12.5l4.5 4.5L19 7.5'] },
  trash: { p: ['M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13'] },
  logout: { p: ['M15 17l4-5-4-5M19 12H9M11 4H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h4'] },
  restart: { p: ['M4 12a8 8 0 1 0 2.3-5.6', 'M4 4v4h4'] },
  up: { p: ['M12 19V6M6.5 11.5L12 6l5.5 5.5', 'M6 3h12'] },
  plus: { p: ['M12 5v14M5 12h14'] },
  shuffle: { p: ['M4 7h3.5c4.5 0 4.5 10 9 10H20M4 17h3.5c1.6 0 2.6-1.3 3.4-3M14 10c.9-1.8 1.9-3 3.5-3H20M17.5 4.5L20 7l-2.5 2.5M17.5 14.5L20 17l-2.5 2.5'] },
  volume: { p: ['M4 9.5h3.5L12 5.5v13l-4.5-4H4z', 'M15.5 9a4 4 0 0 1 0 6M18 6.5a7.5 7.5 0 0 1 0 11'] },
  mute: { p: ['M4 9.5h3.5L12 5.5v13l-4.5-4H4z', 'M16 9.5l5 5M21 9.5l-5 5'] },
  external: { p: ['M14 4h6v6M20 4l-9 9M18 14v4a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4'] },
  play: { fill: true, p: ['M8 5.6v12.8a1 1 0 0 0 1.5.86l10.2-6.4a1 1 0 0 0 0-1.72L9.5 4.74A1 1 0 0 0 8 5.6z'] },
  pause: { fill: true, p: ['M7 5h3.2v14H7zM13.8 5H17v14h-3.2z'] },
  stop: { fill: true, p: ['M6.5 6.5h11v11h-11z'] },
  next: { fill: true, p: ['M5.5 6.2v11.6a.8.8 0 0 0 1.25.66L15 12.66a.8.8 0 0 0 0-1.32L6.75 5.54a.8.8 0 0 0-1.25.66zM16.5 5.5h2.2v13h-2.2z'] },
  youtube: {
    fill: true,
    p: [
      'M10 15.5v-7l6 3.5-6 3.5z',
      'M21.6 7.2c-.2-1.1-.9-1.9-2-2.1C17.8 4.8 15 4.7 12 4.7s-5.8.1-7.6.4c-1.1.2-1.8 1-2 2.1C2.1 8.5 2 10.1 2 12s.1 3.5.4 4.8c.2 1.1.9 1.9 2 2.1 1.8.3 4.6.4 7.6.4s5.8-.1 7.6-.4c1.1-.2 1.8-1 2-2.1.3-1.3.4-2.9.4-4.8s-.1-3.5-.4-4.8zm-1.9 9.2c-.1.5-.3.7-.7.8-1.5.2-4.2.4-7 .4s-5.5-.1-7-.4c-.4-.1-.6-.3-.7-.8C4.1 15.3 4 13.8 4 12s.1-3.3.3-4.4c.1-.5.3-.7.7-.8 1.5-.2 4.2-.4 7-.4s5.5.1 7 .4c.4.1.6.3.7.8.2 1.1.3 2.6.3 4.4s-.1 3.3-.3 4.4z',
    ],
  },
  github: {
    fill: true,
    p: ['M12 2C6.48 2 2 6.58 2 12.23c0 4.52 2.87 8.35 6.84 9.7.5.1.68-.22.68-.49l-.01-1.7c-2.78.62-3.37-1.38-3.37-1.38-.46-1.19-1.11-1.5-1.11-1.5-.9-.64.07-.63.07-.63 1 .07 1.53 1.06 1.53 1.06.9 1.57 2.34 1.12 2.91.86.09-.67.35-1.12.63-1.38-2.22-.26-4.56-1.14-4.56-5.07 0-1.12.39-2.04 1.03-2.76-.1-.26-.45-1.3.1-2.71 0 0 .84-.28 2.75 1.05a9.3 9.3 0 0 1 5 0c1.91-1.33 2.75-1.05 2.75-1.05.55 1.41.2 2.45.1 2.71.64.72 1.03 1.64 1.03 2.76 0 3.94-2.34 4.8-4.57 5.06.36.32.68.94.68 1.9l-.01 2.82c0 .27.18.6.69.49A10.1 10.1 0 0 0 22 12.23C22 6.58 17.52 2 12 2z'],
  },
}

const icon = computed(() => ICONS[props.name] || ICONS.x)
const paths = computed(() => icon.value.p || [])
const circles = computed(() => icon.value.c || [])
const filled = computed(() => !!icon.value.fill)
</script>

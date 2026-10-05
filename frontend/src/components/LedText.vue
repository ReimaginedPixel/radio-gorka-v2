<template>
  <span :aria-label="target">{{ display }}</span>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { ledText } from '../lib/format'
import { prefersReducedMotion } from '../lib/motion'

const props = defineProps({ text: { type: String, default: '' } })

const GLYPHS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/#+*'
const target = computed(() => ledText(props.text))
const display = ref(target.value)
let frame = 0

// Przy zmianie tekstu znaki "przestrajają się" jak na wyświetlaczu, od lewej do prawej.
watch(target, (next) => {
  cancelAnimationFrame(frame)
  if (prefersReducedMotion()) {
    display.value = next
    return
  }
  const begin = performance.now()
  const total = 320 + next.length * 14
  const step = (now) => {
    const p = Math.min(1, (now - begin) / total)
    let out = ''
    for (let i = 0; i < next.length; i++) {
      const settle = 0.2 + (i / Math.max(1, next.length)) * 0.75
      const ch = next[i]
      out += p >= settle || ch === ' ' ? ch : GLYPHS[(Math.random() * GLYPHS.length) | 0]
    }
    display.value = out
    if (p < 1) frame = requestAnimationFrame(step)
  }
  frame = requestAnimationFrame(step)
})

onBeforeUnmount(() => cancelAnimationFrame(frame))
</script>

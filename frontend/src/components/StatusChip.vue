<template>
  <span
    class="inline-block rounded px-2 py-0.5 text-sm border whitespace-nowrap"
    :style="{ color: info.color, borderColor: info.color }"
  >{{ info.label }}</span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  status: { type: String, required: true },
})

const STATUSES = {
  pending: { label: 'Czeka na DJ-a', color: '#00FFFF' },
  approved: { label: 'Zatwierdzone', color: '#39FF14' },
  played: { label: 'Zagrane', color: '#FFD700' },
  rejected: { label: 'Odrzucone', color: '#FF1493' },
}

const info = computed(() => STATUSES[props.status] || { label: props.status, color: '#C0C0C0' })
</script>

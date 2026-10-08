<template>
  <div :class="big ? 'w-full' : 'w-full max-w-xs'">
    <div class="flex items-baseline justify-between gap-3 mb-1" :class="big ? 'text-3xl' : 'text-lg'">
      <span class="text-retro-pink">{{ label }}</span>
      <span class="font-orbitron" :class="reached ? 'text-retro-gold' : 'text-retro-green'">
        {{ played }} / {{ goal }}
      </span>
    </div>
    <div
      class="w-full rounded-full overflow-hidden border border-retro-green bg-retro-bg"
      :class="big ? 'h-6' : 'h-3'"
      role="progressbar"
      :aria-valuenow="played"
      aria-valuemin="0"
      :aria-valuemax="goal"
    >
      <div
        class="h-full transition-all duration-700"
        :class="reached ? 'bg-retro-gold' : 'bg-retro-green'"
        :style="{ width: percent + '%' }"
      />
    </div>
    <p v-if="reached && big" class="mt-2 text-2xl text-retro-gold">Cel na dziś osiągnięty, dzięki DJ-e!</p>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  played: { type: Number, default: 0 },
  goal: { type: Number, default: 0 },
  big: { type: Boolean, default: false },
  label: { type: String, default: 'Dziś zagrane prośby' },
})

const reached = computed(() => props.goal > 0 && props.played >= props.goal)
const percent = computed(() => (props.goal > 0 ? Math.min(100, (props.played / props.goal) * 100) : 0))
</script>

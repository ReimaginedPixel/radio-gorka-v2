<template>
  <span class="count-pill tabular" :aria-label="String(value)">
    <Transition name="roll" mode="out-in">
      <span :key="text" class="roll">{{ text }}</span>
    </Transition>
  </span>
</template>

<script setup>
import { computed } from 'vue'
import { pad2 } from '../lib/format'

const props = defineProps({ value: { type: Number, default: 0 } })
const text = computed(() => pad2(props.value))
</script>

<style scoped>
.count-pill {
  display: inline-flex;
  justify-content: center;
  overflow: hidden;
}

.roll {
  display: inline-block;
}

.roll-enter-active,
.roll-leave-active {
  transition: transform 0.16s var(--ease-out), opacity 0.16s ease;
}

.roll-enter-from {
  transform: translateY(70%);
  opacity: 0;
}

.roll-leave-to {
  transform: translateY(-70%);
  opacity: 0;
}
</style>

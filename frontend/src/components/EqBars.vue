<template>
  <span class="eq" :class="{ 'is-on': playing }" aria-hidden="true">
    <i v-for="n in 4" :key="n" :style="{ '--d': `${0.62 + n * 0.13}s`, '--o': `${-n * 0.21}s` }" />
  </span>
</template>

<script setup>
defineProps({ playing: { type: Boolean, default: false } })
</script>

<style scoped>
.eq {
  display: inline-flex;
  align-items: flex-end;
  gap: 2px;
  height: 14px;
  flex: none;
}

.eq i {
  width: 3px;
  height: 100%;
  border-radius: 2px;
  background: currentColor;
  transform-origin: bottom;
  transform: scaleY(0.25);
  transition: transform 0.4s var(--ease-out);
  animation: eq var(--d) ease-in-out var(--o) infinite alternate;
  animation-play-state: paused;
}

.eq.is-on i {
  animation-play-state: running;
}

.eq:not(.is-on) i {
  animation: none;
}

@keyframes eq {
  0% {
    transform: scaleY(0.2);
  }
  50% {
    transform: scaleY(1);
  }
  100% {
    transform: scaleY(0.45);
  }
}
</style>

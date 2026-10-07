<template>
  <button
    type="button"
    :disabled="disabled || busy"
    :aria-pressed="voted"
    :title="voted ? 'Cofnij głos' : 'Zagłosuj'"
    class="rounded-lg px-3 py-2 flex items-center gap-2 font-orbitron text-sm transition border min-w-[84px] justify-center disabled:opacity-50"
    :class="voted
      ? 'bg-retro-green text-retro-bg border-retro-green'
      : 'bg-retro-bg-secondary text-retro-green border-retro-green hover:bg-retro-green hover:text-retro-bg'"
    @click="$emit('toggle')"
  >
    <svg class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M12 4l8 10h-5v6H9v-6H4z" />
    </svg>
    <span>{{ votes }}</span>
  </button>
</template>

<script setup>
defineProps({
  votes: { type: Number, default: 0 },
  voted: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  busy: { type: Boolean, default: false },
})

defineEmits(['toggle'])
</script>

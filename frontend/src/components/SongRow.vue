<template>
  <li
    class="neon-box rounded-lg p-3 sm:p-4 flex flex-wrap items-center gap-3 sm:gap-4"
    :class="highlight ? 'border-retro-green!' : ''"
  >
    <slot name="before" />
    <a :href="youtubeUrl(videoId)" target="_blank" rel="noopener noreferrer" class="shrink-0">
      <img
        :src="thumbnailUrl(videoId)"
        :alt="title"
        loading="lazy"
        class="w-12 h-12 sm:w-16 sm:h-16 rounded-lg object-cover"
        style="box-shadow: 0px 0px 10px 2px #39FF14;"
      />
    </a>
    <div class="flex-1 min-w-[9rem]">
      <a
        :href="youtubeUrl(videoId)"
        target="_blank"
        rel="noopener noreferrer"
        class="font-semibold truncate hover:underline block text-retro-green font-orbitron"
      >{{ title }}</a>
      <p class="text-retro-pink truncate">
        {{ artist || 'Nieznany wykonawca' }}<span v-if="duration" class="opacity-70"> · {{ formatDuration(duration) }}</span>
      </p>
      <slot name="meta" />
    </div>
    <div v-if="$slots.actions" class="flex flex-wrap items-center justify-end gap-2 ml-auto">
      <slot name="actions" />
    </div>
  </li>
</template>

<script setup>
import { formatDuration, thumbnailUrl, youtubeUrl } from '../format'

defineProps({
  videoId: { type: String, required: true },
  title: { type: String, default: '' },
  artist: { type: String, default: '' },
  duration: { type: Number, default: null },
  highlight: { type: Boolean, default: false },
})
</script>

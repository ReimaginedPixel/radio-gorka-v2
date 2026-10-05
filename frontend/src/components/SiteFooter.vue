<template>
  <footer class="site-footer">
    <span>© Radio Górka</span>
    <span aria-hidden="true">·</span>
    <RouterLink to="/admin-panel">panel admina</RouterLink>
    <span aria-hidden="true">·</span>
    <a href="https://github.com/daniel-kub/radio-gorka-v2" target="_blank" rel="noopener noreferrer" class="gh">
      <Icon name="github" :size="13" />
      GitHub
    </a>
  </footer>
</template>

<script setup>
import Icon from './Icon.vue'
</script>

<style scoped>
.site-footer {
  display: flex;
  justify-content: center;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  font-size: 12.5px;
  color: var(--dim);
  padding-top: 8px;
}

.gh {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}
</style>

<template>
  <header class="site-header">
    <RouterLink to="/" class="brand" aria-label="Radio Górka, strona główna">
      <img :src="logo" alt="" class="brand-logo" width="46" height="46" />
      <span class="brand-text">
        <span class="brand-name">Radio Górka</span>
        <span class="brand-sub">{{ subtitle }}</span>
      </span>
    </RouterLink>

    <nav ref="navEl" class="nav" aria-label="Nawigacja">
      <span class="nav-ind" :style="indicator" aria-hidden="true" />
      <RouterLink
        v-for="item in items"
        :key="item.to"
        :ref="(el) => (links[item.to] = el?.$el)"
        :to="item.to"
        class="nav-item led"
        :class="{ 'is-active': active === item.to }"
        :aria-current="active === item.to ? 'page' : undefined"
      >
        {{ item.label }}
      </RouterLink>
    </nav>

    <button class="theme-btn" type="button" :aria-label="theme === 'dark' ? 'Włącz jasny motyw' : 'Włącz ciemny motyw'" @click="toggle">
      <Transition name="swap" mode="out-in">
        <Icon :key="theme" :name="theme === 'dark' ? 'sun' : 'moon'" :size="19" :stroke="1.7" />
      </Transition>
    </button>
  </header>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import logo from '../assets/img/logo.png'
import { useTheme } from '../composables/useTheme'
import Icon from './Icon.vue'

const { theme, toggle } = useTheme()
const route = useRoute()

const items = [
  { to: '/', label: 'SZUKAJ' },
  { to: '/admin-panel', label: 'ADMIN' },
]

const active = computed(() => items.find((i) => i.to === route.path)?.to || null)
const subtitle = computed(() => (active.value === '/admin-panel' ? 'Panel DJ-a' : 'Zgłoś utwór do playlisty'))

const navEl = ref(null)
const links = reactive({})
const box = ref({ left: 0, width: 0, visible: false })

// Podświetlenie przesuwa się pod aktywną zakładkę zamiast skakać.
function measure() {
  const el = active.value && links[active.value]
  if (!el) {
    box.value = { ...box.value, visible: false }
    return
  }
  box.value = { left: el.offsetLeft, width: el.offsetWidth, visible: true }
}

const indicator = computed(() => ({
  transform: `translateX(${box.value.left}px)`,
  width: `${box.value.width}px`,
  opacity: box.value.visible ? 1 : 0,
}))

watch(active, () => nextTick(measure))
onMounted(() => {
  nextTick(measure)
  document.fonts?.ready.then(measure)
  window.addEventListener('resize', measure)
})
onBeforeUnmount(() => window.removeEventListener('resize', measure))
</script>

<style scoped>
.site-header {
  display: flex;
  align-items: center;
  gap: 11px;
  flex-wrap: wrap;
}

.brand {
  display: flex;
  align-items: center;
  gap: 11px;
  flex: 1;
  min-width: 0;
  color: var(--ink);
}

.brand:hover {
  text-decoration: none;
  color: var(--ink);
}

.brand-logo {
  width: 46px;
  height: 46px;
  object-fit: contain;
  flex: none;
  filter: drop-shadow(0 5px 14px color-mix(in srgb, var(--acc) 50%, transparent));
  transition: transform 0.4s var(--ease-spring);
}

.brand:hover .brand-logo {
  transform: rotate(-6deg) scale(1.05);
}

.brand-text {
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.brand-name {
  font-size: clamp(16px, 2.1vw, 19px);
  font-weight: 700;
  letter-spacing: -0.3px;
  line-height: 1.15;
}

.brand-sub {
  font-size: 13px;
  color: var(--dim);
  line-height: 1.3;
}

.nav {
  position: relative;
  display: flex;
  gap: 4px;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 99px;
  padding: 4px;
  order: 3;
  flex: none;
}

.nav-ind {
  position: absolute;
  top: 4px;
  left: 0;
  height: 32px;
  border-radius: 99px;
  background: var(--acc);
  transition: transform 0.38s var(--ease-out), width 0.38s var(--ease-out), opacity 0.2s;
}

.nav-item {
  position: relative;
  z-index: 1;
  border-radius: 99px;
  font-size: 12px;
  letter-spacing: 1px;
  height: 32px;
  padding: 0 14px;
  display: inline-flex;
  align-items: center;
  color: var(--dim);
  transition: color 0.25s;
}

.nav-item:hover {
  color: var(--ink);
  text-decoration: none;
}

.nav-item.is-active {
  color: var(--accInk);
}

.theme-btn {
  width: 44px;
  height: 44px;
  border-radius: 14px;
  border: 1px solid var(--line);
  background: var(--panel);
  color: var(--ink);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex: none;
  padding: 0;
  order: 2;
  transition: background-color 0.15s, transform 0.18s var(--ease-out);
}

.theme-btn:hover {
  background: var(--panel2);
}

.theme-btn:active {
  transform: scale(0.94);
}

.swap-enter-active,
.swap-leave-active {
  transition: transform 0.25s var(--ease-out), opacity 0.2s;
}

.swap-enter-from {
  transform: rotate(-90deg) scale(0.6);
  opacity: 0;
}

.swap-leave-to {
  transform: rotate(90deg) scale(0.6);
  opacity: 0;
}

.brand-name,
.brand-sub {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* na telefonie zakładki zajmują własny rząd pod logo */
@media (max-width: 559px) {
  .nav {
    flex: 1 1 100%;
  }

  .nav-item {
    flex: 1;
    justify-content: center;
  }
}

@media (min-width: 560px) {
  .nav {
    order: 1;
  }
}
</style>

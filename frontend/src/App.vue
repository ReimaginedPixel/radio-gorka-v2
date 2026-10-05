<template>
  <div class="app">
    <div class="grid-bg" aria-hidden="true" />
    <div class="shell">
      <SiteHeader />
      <main class="main">
        <RouterView v-slot="{ Component, route }">
          <Transition name="page" mode="out-in">
            <component :is="Component" :key="route.path" />
          </Transition>
        </RouterView>
      </main>
      <SiteFooter />
    </div>
    <ToastHost />
    <ConfirmDialog />
  </div>
</template>

<script setup>
import ConfirmDialog from './components/ConfirmDialog.vue'
import SiteFooter from './components/SiteFooter.vue'
import SiteHeader from './components/SiteHeader.vue'
import ToastHost from './components/ToastHost.vue'
</script>

<style scoped>
.app {
  position: relative;
  min-height: 100vh;
  overflow-x: clip;
}

.grid-bg {
  position: absolute;
  inset: 0 0 auto 0;
  height: 720px;
  pointer-events: none;
  background-image:
    linear-gradient(to right, var(--line) 1px, transparent 1px),
    linear-gradient(to bottom, var(--line) 1px, transparent 1px);
  background-size: 46px 46px;
  mask-image: radial-gradient(ellipse 70% 55% at 50% 0%, #000 55%, transparent 100%);
  -webkit-mask-image: radial-gradient(ellipse 70% 55% at 50% 0%, #000 55%, transparent 100%);
}

.shell {
  position: relative;
  max-width: 1080px;
  margin: 0 auto;
  padding: 20px 16px 48px;
  display: flex;
  flex-direction: column;
  gap: 18px;
  min-height: 100vh;
}

.main {
  flex: 1;
}
</style>

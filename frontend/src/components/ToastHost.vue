<template>
  <div class="toasts" role="status" aria-live="polite">
    <TransitionGroup name="toast">
      <button
        v-for="t in toasts"
        :key="t.id"
        type="button"
        class="toast"
        :class="`is-${t.type}`"
        @click="dismiss(t.id)"
      >
        <span class="toast-icon"><Icon :name="t.type === 'error' ? 'x' : 'check'" :size="12" :stroke="2.6" /></span>
        <span class="toast-text">{{ t.message }}</span>
      </button>
    </TransitionGroup>
  </div>
</template>

<script setup>
import { useToasts } from '../composables/useToast'
import Icon from './Icon.vue'

const { toasts, dismiss } = useToasts()
</script>

<style scoped>
.toasts {
  position: fixed;
  left: 16px;
  right: 16px;
  bottom: calc(20px + var(--toast-offset, 0px));
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  pointer-events: none;
  z-index: 700;
  transition: bottom 0.3s var(--ease-out);
}

.toast {
  pointer-events: auto;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 11px 16px;
  display: flex;
  align-items: center;
  gap: 10px;
  box-shadow: 0 18px 38px -16px rgba(0, 0, 0, 0.75);
  max-width: 100%;
  cursor: pointer;
  text-align: left;
}

.toast-icon {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--acc);
  color: var(--accInk);
  display: flex;
  align-items: center;
  justify-content: center;
  flex: none;
}

.toast.is-error .toast-icon {
  background: var(--danger);
  color: #fff;
}

.toast-text {
  font-size: 13px;
  font-weight: 500;
  color: var(--ink);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.toast-enter-active,
.toast-leave-active {
  transition: opacity 0.3s ease, transform 0.35s var(--ease-out);
}

.toast-enter-from {
  opacity: 0;
  transform: translateY(14px) scale(0.96);
}

.toast-leave-to {
  opacity: 0;
  transform: translateY(8px);
}

.toast-move {
  transition: transform 0.3s var(--ease-out);
}

.toast-leave-active {
  position: absolute;
}
</style>

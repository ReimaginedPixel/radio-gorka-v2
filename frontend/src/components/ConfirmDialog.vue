<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="dialog" class="backdrop" @click.self="close(false)">
        <div class="dialog" role="alertdialog" aria-modal="true" :aria-labelledby="'dlg-title'" :aria-describedby="'dlg-msg'">
          <div id="dlg-title" class="dlg-title">{{ dialog.title }}</div>
          <div id="dlg-msg" class="dlg-msg">{{ dialog.message }}</div>
          <div class="dlg-actions">
            <button ref="cancelBtn" type="button" class="btn btn-ghost" @click="close(false)">{{ dialog.cancelLabel }}</button>
            <button type="button" class="btn" :class="dialog.danger ? 'btn-danger' : 'btn-primary'" @click="close(true)">
              {{ dialog.confirmLabel }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useConfirmState } from '../composables/useConfirm'

const dialog = useConfirmState()
const cancelBtn = ref(null)

function close(value) {
  dialog.value?.resolve(value)
}

function onKey(e) {
  if (dialog.value && e.key === 'Escape') close(false)
}

watch(dialog, (d) => {
  if (d) nextTick(() => cancelBtn.value?.focus())
})

onMounted(() => window.addEventListener('keydown', onKey))
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<style scoped>
.backdrop {
  position: fixed;
  inset: 0;
  z-index: 800;
  background: rgba(6, 5, 11, 0.72);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 18px;
}

.dialog {
  width: 100%;
  max-width: 360px;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 24px;
  padding: 24px;
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 12px;
  box-shadow: 0 30px 60px -20px rgba(0, 0, 0, 0.7);
}

.dlg-title {
  font-size: 18px;
  font-weight: 700;
}

.dlg-msg {
  font-size: 13.5px;
  color: var(--dim);
  text-wrap: pretty;
}

.dlg-actions {
  display: flex;
  gap: 9px;
  margin-top: 6px;
}

.dlg-actions .btn {
  flex: 1;
  height: 46px;
  border-radius: 14px;
}

.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.22s ease;
}

.modal-enter-active .dialog,
.modal-leave-active .dialog {
  transition: transform 0.32s var(--ease-spring), opacity 0.22s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-from .dialog,
.modal-leave-to .dialog {
  transform: scale(0.94) translateY(8px);
  opacity: 0;
}
</style>

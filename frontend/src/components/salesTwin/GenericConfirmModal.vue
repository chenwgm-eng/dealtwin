<template>
  <div v-if="state.show" class="modal-overlay" tabindex="-1" role="dialog" aria-modal="true"
    :aria-label="state.title" @click.self="handleCancel" @keydown.esc="handleCancel">
    <div class="modal modal-sm">
      <div class="modal-header">
        <h3 class="modal-title">{{ state.title }}</h3>
        <button type="button" class="modal-close" @click="handleCancel" :aria-label="t('common.close')">×</button>
      </div>
      <div class="modal-body">
        <p class="modal-confirm-text">{{ state.message }}</p>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn-secondary" :disabled="state.loading" @click="handleCancel">
          {{ state.cancelText }}
        </button>
        <button type="button" :class="state.danger ? 'btn-danger' : 'btn-primary'" :disabled="state.loading" @click="handleConfirm">
          {{ state.loading ? t('common.processing') : state.confirmText }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useI18n } from 'vue-i18n'
import { useConfirmToast } from '../../composables/salesTwin/useConfirmToast'

const { t } = useI18n()
const { confirmState: state, resolveConfirm, cancelConfirm } = useConfirmToast()

function handleConfirm() {
  resolveConfirm()
}

function handleCancel() {
  if (state.loading) return
  cancelConfirm()
}
</script>

<style scoped>
.modal-sm {
  max-width: 440px;
  width: 90%;
}

.modal-confirm-text {
  font-size: 14px;
  color: var(--text-primary, #15171D);
  margin: 0;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

.btn-danger {
  background: var(--red, #C4391C);
  color: #fff;
  border: 1px solid var(--red, #C4391C);
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  transition: background 0.15s;
}

.btn-danger:hover:not(:disabled) {
  background: #A02E15;
  border-color: #A02E15;
}

.btn-danger:disabled {
  background: var(--border, #E8E8E0);
  border-color: var(--border, #E8E8E0);
  color: var(--text-muted, #93959D);
  cursor: not-allowed;
}

.btn-primary {
  background: var(--accent, #E67E22);
  color: #fff;
  border: 1px solid var(--accent, #E67E22);
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  transition: background 0.15s;
}

.btn-primary:hover:not(:disabled) {
  background: #D35400;
  border-color: #D35400;
}

.btn-primary:disabled {
  background: var(--border, #E8E8E0);
  border-color: var(--border, #E8E8E0);
  color: var(--text-muted, #93959D);
  cursor: not-allowed;
}

.btn-secondary {
  background: transparent;
  color: var(--text-secondary, #494A4D);
  border: 1px solid var(--border, #E8E8E0);
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  transition: background 0.15s;
}

.btn-secondary:hover:not(:disabled) {
  background: var(--bg-base, #F5F5F0);
}

.btn-secondary:disabled {
  color: var(--text-muted, #93959D);
  cursor: not-allowed;
}
</style>

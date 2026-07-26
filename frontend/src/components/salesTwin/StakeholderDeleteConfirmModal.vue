<template>
  <div v-if="show" class="modal-overlay" tabindex="-1" role="dialog" aria-modal="true" :aria-label="t('stakeholder.removeStakeholder')"
    @click.self="emit('close')" @keydown.esc="emit('close')">
    <div class="modal modal-sm">
      <div class="modal-header">
        <h3 class="modal-title">{{ t('stakeholder.removeStakeholder') }}</h3>
        <button type="button" class="modal-close" @click="emit('close')" :aria-label="t('common.close')">×</button>
      </div>
      <div class="modal-body">
        <p class="modal-confirm-text">
          {{ t('stakeholder.removeConfirmPrefix') }}<strong>{{ stakeholder?.name }}</strong>{{ t('stakeholder.removeConfirmSuffix') }}
        </p>
        <p class="modal-confirm-hint">
          {{ t('stakeholder.removeHintPrefix') }}<strong>{{ t('stakeholder.removeHintEmphasis') }}</strong>{{ t('stakeholder.removeHintSuffix') }}
        </p>
        <ul class="modal-confirm-list">
          <li>{{ t('stakeholder.removeHintItem1') }}</li>
          <li>{{ t('stakeholder.removeHintItem2') }}</li>
        </ul>
        <p class="modal-confirm-warn">{{ t('stakeholder.removeWarn') }}</p>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn-secondary" @click="emit('close')">{{ t('common.cancel') }}</button>
        <button type="button" class="btn-danger" :disabled="deleting" @click="emit('confirm')">
          {{ deleting ? t('stakeholder.removing') : t('stakeholder.confirmRemove') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

defineProps({
  show: { type: Boolean, default: false },
  stakeholder: { type: Object, default: null },
  deleting: { type: Boolean, default: false }
})

const emit = defineEmits(['close', 'confirm'])
</script>

<style scoped>
.modal-sm {
  max-width: 440px;
  width: 90%;
}

.modal-confirm-text {
  font-size: 14px;
  color: var(--text-primary, #15171D);
  margin: 0 0 12px;
  line-height: 1.6;
}

.modal-confirm-hint {
  font-size: 13px;
  color: var(--text-secondary, #494A4D);
  margin: 0 0 6px;
}

.modal-confirm-list {
  margin: 0 0 12px;
  padding-left: 20px;
  color: var(--text-secondary, #494A4D);
  font-size: 13px;
}

.modal-confirm-list li {
  margin-bottom: 2px;
}

.modal-confirm-warn {
  font-size: 12px;
  color: var(--red, #C4391C);
  margin: 0;
  font-weight: 600;
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
</style>

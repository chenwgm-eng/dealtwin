<template>
  <div v-if="show" class="modal-overlay" tabindex="-1" role="dialog" aria-modal="true" :aria-label="t('project.createProject')"
    @click.self="emit('close')" @keydown.esc="emit('close')">
    <div class="modal modal-lg">
      <div class="modal-header">
        <h3 class="modal-title">{{ t('project.createProject') }}</h3>
        <button type="button" class="modal-close" @click="emit('close')" :aria-label="t('common.close')">×</button>
      </div>
      <div class="modal-body">
        <div class="form-row">
          <div class="form-group">
            <label class="field-label" for="new-project-name">{{ t('project.projectName') }} *</label>
            <input id="new-project-name" type="text" :value="form.name"
              @input="emit('update:form', { ...form, name: $event.target.value })"
              :placeholder="t('project.projectNamePlaceholder')" class="form-input" autocomplete="off">
          </div>
          <div class="form-group">
            <label class="field-label" for="new-project-customer">{{ t('project.customerName') }}</label>
            <input id="new-project-customer" type="text" :value="form.customer_name"
              @input="emit('update:form', { ...form, customer_name: $event.target.value })"
              :placeholder="t('project.customerNamePlaceholder')" class="form-input" autocomplete="off">
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label class="field-label" for="new-project-stage">{{ t('project.salesStage') }}</label>
            <select id="new-project-stage" :value="form.sales_stage"
              @change="emit('update:form', { ...form, sales_stage: $event.target.value })" class="form-input">
              <option v-for="s in activeStages" :key="s.value" :value="s.value">{{ s.label }}</option>
            </select>
          </div>
          <div class="form-group">
            <label class="field-label" for="new-project-budget">{{ t('project.budget') }}{{ t('project.budgetUnit') }}</label>
            <input id="new-project-budget" type="number" :value="form.budget"
              @input="emit('update:form', { ...form, budget: Number($event.target.value) || null })"
              :placeholder="t('project.budgetPlaceholder')" class="form-input" autocomplete="off">
          </div>
        </div>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn-secondary" @click="emit('close')">{{ t('common.cancel') }}</button>
        <button type="button" class="btn-primary" @click="emit('create')" :disabled="!form.name.trim()">{{ t('project.createProject') }}</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

defineProps({
  show: { type: Boolean, default: false },
  form: { type: Object, required: true },
  activeStages: { type: Array, default: () => [] }
})

const emit = defineEmits(['close', 'create', 'update:form'])
</script>

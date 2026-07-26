<template>
  <div v-if="show" class="modal-overlay" tabindex="-1"
    role="dialog" aria-modal="true" :aria-label="t('workspace.createTask')"
    @click.self="emit('close')"
    @keydown.esc="emit('close')">
    <div class="modal" style="max-width:520px;">
      <div class="modal-header">
        <h3 class="modal-title">{{ t('workspace.createTask') }}</h3>
        <button type="button" class="modal-close" @click="emit('close')" :aria-label="t('common.close')">×</button>
      </div>
      <div class="modal-body">
        <div class="form-group">
          <label class="field-label" for="new-task-title">{{ t('workspace.taskTitle') }} *</label>
          <input id="new-task-title" type="text" :value="form.title"
            @input="emit('update:form', { ...form, title: $event.target.value })"
            :placeholder="t('workspace.taskTitlePlaceholder')" class="form-input" autocomplete="off">
        </div>
        <div class="form-group">
          <label class="field-label" for="new-task-desc">{{ t('workspace.taskDescription') }}</label>
          <textarea id="new-task-desc" :value="form.description"
            @input="emit('update:form', { ...form, description: $event.target.value })"
            rows="3" :placeholder="t('workspace.taskDescriptionPlaceholder')" class="form-input"></textarea>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label class="field-label" for="new-task-priority">{{ t('common.priority') }}</label>
            <select id="new-task-priority" :value="form.priority"
              @change="emit('update:form', { ...form, priority: $event.target.value })" class="form-input">
              <option value="high">{{ t('workspace.priorityLabels.high') }}</option>
              <option value="medium">{{ t('workspace.priorityLabels.medium') }}</option>
              <option value="low">{{ t('workspace.priorityLabels.low') }}</option>
            </select>
          </div>
          <div class="form-group">
            <label class="field-label" for="new-task-type">{{ t('workspace.taskType') }}</label>
            <select id="new-task-type" :value="form.task_type"
              @change="emit('update:form', { ...form, task_type: $event.target.value })" class="form-input">
              <option value="follow_up">{{ t('workspace.taskTypes.follow_up') }}</option>
              <option value="meeting">{{ t('workspace.taskTypes.meeting') }}</option>
              <option value="blind_spot">{{ t('workspace.taskTypes.blind_spot') }}</option>
              <option value="address_concerns">{{ t('workspace.taskTypes.address_concerns') }}</option>
              <option value="build_alliance">{{ t('workspace.taskTypes.build_alliance') }}</option>
              <option value="provide_material">{{ t('workspace.taskTypes.provide_material') }}</option>
            </select>
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label class="field-label" for="new-task-stakeholder">{{ t('workspace.relatedStakeholder') }}</label>
            <select id="new-task-stakeholder" :value="form.stakeholder_id"
              @change="emit('update:form', { ...form, stakeholder_id: Number($event.target.value) || null })" class="form-input">
              <option :value="null">{{ t('workspace.notLinked') }}</option>
              <option v-for="s in stakeholders" :key="s.id" :value="s.id">{{ s.name }}{{ s.role ? ' (' + s.role + ')' : '' }}</option>
            </select>
          </div>
          <div class="form-group">
            <label class="field-label" for="new-task-due">{{ t('workspace.dueDate') }}</label>
            <input id="new-task-due" type="date" :value="form.due_date"
              @input="emit('update:form', { ...form, due_date: $event.target.value })" class="form-input">
          </div>
        </div>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn-secondary" @click="emit('close')">{{ t('common.cancel') }}</button>
        <button type="button" class="btn-primary" @click="emit('create')" :disabled="!form.title.trim()">{{ t('workspace.createTask') }}</button>
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
  stakeholders: { type: Array, default: () => [] }
})

const emit = defineEmits(['close', 'create', 'update:form'])
</script>

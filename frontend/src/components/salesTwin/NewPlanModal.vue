<template>
  <div v-if="show" class="modal-overlay" tabindex="-1"
    role="dialog" aria-modal="true" :aria-label="t('workspace.generatePlan')"
    @click.self="emit('close')"
    @keydown.esc="emit('close')">
    <div class="modal" style="max-width:560px;">
      <div class="modal-header">
        <h3 class="modal-title">{{ t('workspace.generatePlan') }}</h3>
        <button type="button" class="modal-close" @click="emit('close')" :aria-label="t('common.close')">×</button>
      </div>
      <div class="modal-body">
        <div class="form-group">
          <label class="field-label" for="new-plan-name">{{ t('workspace.planNameOptional') }}</label>
          <input id="new-plan-name" type="text" :value="form.name"
            @input="emit('update:form', { ...form, name: $event.target.value })"
            :placeholder="t('workspace.planNamePlaceholder')" class="form-input" autocomplete="off">
        </div>
        <div class="form-row">
          <div class="form-group">
            <label class="field-label" for="new-plan-stakeholder">{{ t('workspace.targetStakeholder') }} *</label>
            <select id="new-plan-stakeholder" :value="form.stakeholder_id"
              @change="emit('update:form', { ...form, stakeholder_id: Number($event.target.value) || null })" class="form-input">
              <option :value="null">{{ t('common.pleaseSelect') }}</option>
              <option v-for="s in stakeholders" :key="s.id" :value="s.id">{{ s.name }}{{ s.role ? ' (' + s.role + ')' : '' }}</option>
            </select>
          </div>
          <div class="form-group">
            <label class="field-label" for="new-plan-type">{{ t('workspace.meetingType') }}</label>
            <select id="new-plan-type" :value="form.meeting_type"
              @change="emit('update:form', { ...form, meeting_type: $event.target.value })" class="form-input">
              <option value="初次拜访">{{ t('workspace.meetingTypes.first_visit') }}</option>
              <option value="技术交流">{{ t('workspace.meetingTypes.tech_exchange') }}</option>
              <option value="商务谈判">{{ t('workspace.meetingTypes.business_negotiation') }}</option>
              <option value="方案演示">{{ t('workspace.meetingTypes.proposal_demo') }}</option>
              <option value="回访跟进">{{ t('workspace.meetingTypes.follow_up_visit') }}</option>
            </select>
          </div>
        </div>
        <div class="form-group">
          <label class="field-label" for="new-plan-purpose">{{ t('workspace.meetingPurpose') }}</label>
          <textarea id="new-plan-purpose" :value="form.meeting_purpose"
            @input="emit('update:form', { ...form, meeting_purpose: $event.target.value })"
            rows="3" :placeholder="t('workspace.meetingPurposePlaceholder')" class="form-input"></textarea>
        </div>
        <div v-if="tasks.length > 0" class="form-group">
          <label class="field-label">{{ t('workspace.relatedTasksOptional') }}</label>
          <div class="checkbox-list" style="max-height:140px;overflow-y:auto;border:1px solid var(--border-color, #e5e7eb);border-radius:6px;padding:8px;">
            <label v-for="task in tasks" :key="task.id" class="checkbox-item" style="display:flex;align-items:center;gap:8px;padding:4px 0;">
              <input
                type="checkbox"
                :value="task.id"
                :checked="form.related_task_ids.includes(task.id)"
                @change="toggleTask(task.id, $event.target.checked)"
              >
              <span>{{ task.title }}</span>
              <span v-if="task.status === 'completed'" style="font-size:12px;color:#10b981;">{{ t('workspace.taskStatus.completed') }}</span>
            </label>
          </div>
        </div>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn-secondary" @click="emit('close')" :disabled="generating">{{ t('common.cancel') }}</button>
        <button type="button" class="btn-primary" @click="emit('create')" :disabled="!form.stakeholder_id || generating">
          {{ generating ? t('workspace.generatingPlan') : t('workspace.generatePlan') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const props = defineProps({
  show: { type: Boolean, default: false },
  form: { type: Object, required: true },
  stakeholders: { type: Array, default: () => [] },
  tasks: { type: Array, default: () => [] },
  generating: { type: Boolean, default: false }
})

const emit = defineEmits(['close', 'create', 'update:form'])

function toggleTask(taskId, checked) {
  const ids = props.form.related_task_ids || []
  const nextIds = checked
    ? [...ids, taskId]
    : ids.filter(id => id !== taskId)
  emit('update:form', { ...props.form, related_task_ids: nextIds })
}
</script>

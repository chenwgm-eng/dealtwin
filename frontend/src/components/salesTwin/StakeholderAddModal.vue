<template>
  <div v-if="show" class="modal-overlay" tabindex="-1" role="dialog" aria-modal="true" :aria-label="t('stakeholder.addStakeholder')"
    @click.self="emit('close')" @keydown.esc="emit('close')">
    <div class="modal modal-lg">
      <div class="modal-header">
        <h3 class="modal-title">{{ t('stakeholder.addStakeholder') }}</h3>
        <button type="button" class="modal-close" @click="emit('close')" :aria-label="t('common.close')">×</button>
      </div>
      <div class="modal-body">
        <!-- 姓名 typeahead：模糊匹配客户联系人，无匹配则作为第三方人员 -->
        <div class="form-row">
          <div class="form-group form-group-full">
            <label class="form-label">
              {{ t('stakeholder.stakeholderName') }} <span class="required">*</span>
              <span v-if="form.contact_id" class="sk-name-linked-tag">🔗 {{ t('stakeholder.linkedContact') }}</span>
              <span v-else-if="form.name" class="sk-name-linked-tag muted">{{ t('stakeholder.thirdParty') }}</span>
            </label>
            <div class="sk-name-typeahead">
              <input
                ref="nameInputEl"
                :value="form.name"
                @input="emit('name-input', $event)"
                @keydown.enter.prevent="emit('name-enter', $event)"
                @keydown.esc.prevent="emit('name-blur', $event)"
                @blur="emit('name-blur', $event)"
                type="text"
                class="form-input"
                :placeholder="t('stakeholder.namePlaceholder')"
                autocomplete="off"
              >
              <ul v-if="showSuggestions && suggestions.length" class="sk-name-suggestions" role="listbox" @mousedown.prevent>
                <li
                  v-for="(ct, idx) in suggestions"
                  :key="ct.id"
                  :class="['sk-name-option', { active: idx === suggestionActiveIdx }]"
                  role="option"
                  :aria-selected="idx === suggestionActiveIdx"
                  @mouseenter="emit('hover-suggestion', idx)"
                  @mousedown.prevent="emit('select-suggestion', ct)"
                >
                  <span class="sk-name-option-name">{{ ct.name }}</span>
                  <span v-if="ct.department" class="sk-name-option-dept">{{ ct.department }}</span>
                  <span v-if="ct.position" class="sk-name-option-pos">{{ ct.position }}</span>
                  <span v-if="ct.linked" class="sk-name-option-linked">{{ t('stakeholder.linked') }}</span>
                </li>
                <li class="sk-name-option sk-name-option-new" @mousedown.prevent="emit('select-as-third-party')">
                  <span class="sk-name-option-name">{{ t('stakeholder.addAsThirdParty', { name: form.name }) }}</span>
                </li>
              </ul>
            </div>
            <p v-if="linkContacts.length === 0 && !linkLoading" class="sk-name-hint">
              {{ t('stakeholder.noCustomerHint') }}
            </p>
          </div>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label class="form-label">{{ t('stakeholder.position') }}</label>
            <input :value="form.position" @input="emit('update:form', { ...form, position: $event.target.value })"
              type="text" class="form-input" :placeholder="t('stakeholder.positionPlaceholder')">
          </div>
          <div class="form-group">
            <label class="form-label">{{ t('stakeholder.level') }}</label>
            <input :value="form.level" @input="emit('update:form', { ...form, level: $event.target.value })"
              type="text" class="form-input" :placeholder="t('common.optional')">
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">{{ t('stakeholder.buyerRole') }}</label>
            <select :value="form.buyer_role" @change="emit('update:form', { ...form, buyer_role: $event.target.value })" class="form-input">
              <option value="">{{ t('stakeholder.uncategorized') }}</option>
              <option value="champion">{{ t('stakeholder.buyerRoleOptions.champion') }}</option>
              <option value="blocker">{{ t('stakeholder.buyerRoleOptions.blocker') }}</option>
              <option value="mobilizer">{{ t('stakeholder.buyerRoleOptions.mobilizer') }}</option>
              <option value="guide">{{ t('stakeholder.buyerRoleOptions.guide') }}</option>
              <option value="skeptic">{{ t('stakeholder.buyerRoleOptions.skeptic') }}</option>
              <option value="coach">{{ t('stakeholder.buyerRoleOptions.coach') }}</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">{{ t('stakeholder.projectRole') }}</label>
            <select :value="form.project_role" @change="emit('update:form', { ...form, project_role: $event.target.value })" class="form-input">
              <option value="">{{ t('stakeholder.uncategorized') }}</option>
              <option value="technical_buyer">{{ t('stakeholder.projectRoleOptions.technical_buyer') }}</option>
              <option value="business_buyer">{{ t('stakeholder.projectRoleOptions.business_buyer') }}</option>
              <option value="financial_buyer">{{ t('stakeholder.projectRoleOptions.financial_buyer') }}</option>
              <option value="influencer">{{ t('stakeholder.projectRoleOptions.influencer') }}</option>
              <option value="decision_maker">{{ t('stakeholder.projectRoleOptions.decision_maker') }}</option>
              <option value="user">{{ t('stakeholder.projectRoleOptions.user') }}</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">{{ t('stakeholder.socialStyle') }}</label>
            <select :value="form.social_style" @change="emit('update:form', { ...form, social_style: $event.target.value })" class="form-input">
              <option value="">{{ t('stakeholder.socialStyleOptions.unknown') }}</option>
              <option value="analytical" :title="t('stakeholder.socialStyleTooltips.analytical')">{{ t('stakeholder.socialStyleOptions.analytical') }}</option>
              <option value="driver" :title="t('stakeholder.socialStyleTooltips.driver')">{{ t('stakeholder.socialStyleOptions.driver') }}</option>
              <option value="amiable" :title="t('stakeholder.socialStyleTooltips.amiable')">{{ t('stakeholder.socialStyleOptions.amiable') }}</option>
              <option value="expressive" :title="t('stakeholder.socialStyleTooltips.expressive')">{{ t('stakeholder.socialStyleOptions.expressive') }}</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">{{ t('stakeholder.identificationStatus') }}</label>
            <select :value="form.status" @change="emit('update:form', { ...form, status: $event.target.value })" class="form-input">
              <option value="confirmed">{{ t('stakeholder.confirmed') }}</option>
              <option value="pending">{{ t('stakeholder.pending') }}</option>
            </select>
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">{{ t('stakeholder.decisionPower') }}</label>
            <input :value="form.decision_power" @input="emit('update:form', { ...form, decision_power: Number($event.target.value) || null })"
              type="number" min="0" max="10" class="form-input">
          </div>
          <div class="form-group">
            <label class="form-label">{{ t('stakeholder.supportLevel') }}</label>
            <input :value="form.support_level" @input="emit('update:form', { ...form, support_level: Number($event.target.value) || null })"
              type="number" min="0" max="10" class="form-input">
          </div>
          <div class="form-group">
            <label class="form-label">{{ t('stakeholder.urgency') }}</label>
            <input :value="form.urgency" @input="emit('update:form', { ...form, urgency: Number($event.target.value) || null })"
              type="number" min="0" max="10" class="form-input">
          </div>
        </div>
        <div class="form-row">
          <div class="form-group form-group-full">
            <label class="form-label">{{ t('stakeholder.responsibilities') }}</label>
            <textarea :value="form.responsibilities" @input="emit('update:form', { ...form, responsibilities: $event.target.value })"
              class="form-input" rows="2" :placeholder="t('common.optional')"></textarea>
          </div>
        </div>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn-secondary" @click="emit('close')">{{ t('common.cancel') }}</button>
        <button type="button" class="btn-primary" :disabled="saving" @click="emit('save')">
          {{ saving ? t('common.saving') : t('common.save') }}
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
  form: { type: Object, required: true },
  saving: { type: Boolean, default: false },
  suggestions: { type: Array, default: () => [] },
  suggestionActiveIdx: { type: Number, default: -1 },
  showSuggestions: { type: Boolean, default: false },
  linkContacts: { type: Array, default: () => [] },
  linkLoading: { type: Boolean, default: false }
})

defineEmits([
  'close', 'save',
  'name-input', 'name-enter', 'name-blur',
  'select-suggestion', 'select-as-third-party', 'hover-suggestion',
  'update:form'
])
</script>

<style scoped>
.sk-name-typeahead {
  position: relative;
  width: 100%;
}

.sk-name-linked-tag {
  display: inline-block;
  margin-left: 6px;
  padding: 1px 6px;
  font-size: 10px;
  font-weight: 600;
  border-radius: 3px;
  background: rgba(16, 185, 129, 0.12);
  color: #047857;
  border: 1px solid rgba(16, 185, 129, 0.3);
  vertical-align: middle;
}

.sk-name-linked-tag.muted {
  background: rgba(107, 114, 128, 0.1);
  color: #4B5563;
  border-color: rgba(107, 114, 128, 0.25);
  font-weight: 500;
}

.sk-name-hint {
  margin: 6px 0 0;
  font-size: 11px;
  color: var(--text-muted, #93959D);
}

.sk-name-suggestions {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  z-index: 50;
  list-style: none;
  margin: 2px 0 0;
  padding: 0;
  background: var(--bg-base, #FFFFFF);
  border: 1px solid var(--border, #E8E8E0);
  border-radius: 4px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  max-height: 240px;
  overflow-y: auto;
}

.sk-name-option {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 10px;
  cursor: pointer;
  font-size: 13px;
  border-bottom: 1px solid var(--border, #F0EEE6);
  transition: background 0.1s;
}

.sk-name-option:last-child {
  border-bottom: none;
}

.sk-name-option:hover,
.sk-name-option.active {
  background: rgba(205, 80, 54, 0.06);
}

.sk-name-option-name {
  font-weight: 600;
  color: var(--text-primary, #15171D);
  white-space: nowrap;
}

.sk-name-option-dept,
.sk-name-option-pos {
  color: var(--text-muted, #93959D);
  font-size: 11px;
  white-space: nowrap;
}

.sk-name-option-linked {
  margin-left: auto;
  font-size: 10px;
  padding: 1px 5px;
  border-radius: 3px;
  background: rgba(203, 184, 140, 0.2);
  color: #8B6F35;
}

.sk-name-option-new {
  color: var(--accent, #CD5036);
  font-weight: 600;
  justify-content: center;
  border-top: 1px dashed var(--border, #E8E8E0);
}

.sk-name-option-new .sk-name-option-name {
  color: var(--accent, #CD5036);
}

.form-group-full {
  flex: 1 1 100% !important;
}

.required {
  color: var(--red, #C4391C);
}
</style>

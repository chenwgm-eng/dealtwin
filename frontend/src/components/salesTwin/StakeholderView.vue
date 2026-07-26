<template>
  <!-- Tab 4: Stakeholders -->
  <div class="tab-pane">
    <div class="section-header">
      <span class="section-deco">◇</span>
      <h3 class="section-title">{{ t('stakeholder.title') }}</h3>
      <button type="button" class="btn-primary btn-sm" @click="emit('open-add-modal')">
        <span class="btn-plus">+</span> {{ t('stakeholder.addStakeholder') }}
      </button>
    </div>

    <div v-if="stakeholders.length === 0" class="empty-state">
      <div class="empty-icon">❖</div>
      <p class="empty-text">{{ t('stakeholder.noStakeholders') }}</p>
      <p class="empty-hint">{{ t('stakeholder.clickToAddHint') }}</p>
    </div>

    <div v-else class="sk-master-detail">
      <!-- 左侧：干系人列表 -->
      <div class="sk-list-pane">
        <!-- 合并模式提示栏 -->
        <div v-if="mergeMode" class="merge-banner">
          <span class="merge-banner-text">
            {{ t('stakeholder.mergePrimaryHint', { name: mergePrimary?.name }) }}
          </span>
          <button type="button" class="btn-link" @click="emit('cancel-merge')">{{ t('stakeholder.exitMerge') }}</button>
        </div>

        <div
          v-for="sh in stakeholders"
          :key="sh.id"
          class="sk-list-item"
          :class="{
            active: !mergeMode && selectedStakeholderId === sh.id,
            'merge-target': mergeMode && mergePrimary && mergePrimary.id === sh.id,
            'merge-selectable': mergeMode && mergePrimary && mergePrimary.id !== sh.id,
            'is-pending': sh.status === 'pending'
          }"
          role="button"
          :tabindex="0"
          :aria-label="stakeholderAriaLabel(sh)"
          @click="handleStakeholderActivate(sh)"
          @keydown.enter="handleStakeholderActivate(sh)"
          @keydown.space.prevent="handleStakeholderActivate(sh)"
        >
          <div class="sk-li-top">
            <h4 class="sk-li-name">
              {{ sh.name }}
              <span v-if="sh.contact_id" class="sk-li-linked-icon" :title="t('stakeholder.linkedContact')" :aria-label="t('stakeholder.linkedContact')">🔗</span>
            </h4>
            <span class="role-badge" :class="sh.buyer_role" :title="buyerRoleTooltips[sh.buyer_role] || ''">
              {{ buyerRoleLabels[sh.buyer_role] || sh.buyer_role || t('stakeholder.uncategorized') }}
            </span>
          </div>
          <p class="sk-li-position">{{ sh.position }}<span v-if="sh.level"> · {{ sh.level }}</span></p>
          <div class="sk-li-stats">
            <span class="sk-li-stat" :title="t('stakeholder.supportLevel')"><span class="sk-li-dot support"></span>{{ sh.support_level }}</span>
            <span class="sk-li-stat" :title="t('stakeholder.decisionPower')"><span class="sk-li-dot power"></span>{{ sh.decision_power }}</span>
            <span class="sk-li-stat" :title="t('stakeholder.urgency')"><span class="sk-li-dot urgency"></span>{{ sh.urgency }}</span>
            <span v-if="sh.status === 'pending'" class="sk-li-status-tag pending" :title="t('stakeholder.pending')">{{ t('stakeholder.pending') }}</span>
            <span v-else class="sk-li-status-tag confirmed" :title="t('stakeholder.confirmed')">{{ t('stakeholder.confirmed') }}</span>
          </div>
          <div v-if="mergeMode && mergePrimary && mergePrimary.id === sh.id" class="sk-li-merge-tag">{{ t('stakeholder.primaryRecord') }}</div>
        </div>
      </div>

      <!-- 右侧：详情面板 -->
      <div class="sk-detail-pane">
        <StakeholderDetailPanel
          :stakeholder="selectedStakeholder"
          :state-logs="stateLogsArray"
          :fermentation-result="fermentationResult"
          :meeting-plans="meetingPlans"
          :role-labels="buyerRoleLabels"
          :role-tooltips="buyerRoleTooltips"
          :project-role-labels="projectRoleLabels"
          :project-role-tooltips="projectRoleTooltips"
          :stakeholders="stakeholders"
          :customer-contacts="customerContacts"
          @edit="emit('open-edit-modal', $event)"
          @merge="emit('start-merge', $event)"
          @updated="emit('stakeholder-updated', $event)"
          @delete="emit('delete-stakeholder', $event)"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import StakeholderDetailPanel from '../StakeholderDetailPanel.vue'

const { t } = useI18n()

const props = defineProps({
  stakeholders: {
    type: Array,
    default: () => []
  },
  selectedStakeholderId: {
    type: [String, Number, null],
    default: null
  },
  mergeMode: {
    type: Boolean,
    default: false
  },
  mergePrimary: {
    type: Object,
    default: null
  },
  stateLogsArray: {
    type: Array,
    default: () => []
  },
  fermentationResult: {
    type: Object,
    default: null
  },
  meetingPlans: {
    type: Array,
    default: () => []
  },
  buyerRoleLabels: {
    type: Object,
    default: () => ({})
  },
  buyerRoleTooltips: {
    type: Object,
    default: () => ({})
  },
  projectRoleLabels: {
    type: Object,
    default: () => ({})
  },
  projectRoleTooltips: {
    type: Object,
    default: () => ({})
  },
  customerContacts: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits([
  'select-stakeholder',
  'open-edit-modal',
  'start-merge',
  'cancel-merge',
  'execute-merge',
  'open-add-modal',
  'stakeholder-updated',
  'delete-stakeholder'
])

const selectedStakeholder = computed(() => {
  if (!props.selectedStakeholderId) return null
  return props.stakeholders.find(s => s.id === props.selectedStakeholderId) || null
})

function isMergeTarget(sh) {
  return props.mergeMode && props.mergePrimary && props.mergePrimary.id !== sh.id
}

function stakeholderAriaLabel(sh) {
  if (isMergeTarget(sh)) {
    return t('stakeholder.mergeInto', { sourceName: sh.name, targetName: props.mergePrimary.name })
  }
  return t('stakeholder.viewDetails', { name: sh.name })
}

function handleStakeholderActivate(sh) {
  if (props.mergeMode) {
    if (isMergeTarget(sh)) emit('execute-merge', sh)
    return
  }
  emit('select-stakeholder', sh.id)
}
</script>

<style scoped>
.sk-list-item.is-pending {
  border-left: 2px solid #CBB88C;
}

.sk-li-linked-icon {
  font-size: 11px;
  margin-left: 4px;
  opacity: 0.7;
}

.sk-li-status-tag {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 8px;
  font-weight: 600;
  margin-left: auto;
  border: 1px solid transparent;
}

.sk-li-status-tag.pending {
  background: rgba(203, 184, 140, 0.2);
  color: #8B6F35;
  border-color: rgba(203, 184, 140, 0.4);
}

.sk-li-status-tag.confirmed {
  background: rgba(17, 138, 88, 0.1);
  color: var(--green, #118A58);
  border-color: rgba(17, 138, 88, 0.2);
}
</style>

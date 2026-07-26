<template>
  <div class="sdp-container">
    <!-- 空状态 -->
    <div v-if="!stakeholder" class="sdp-empty">
      <div class="sdp-empty-icon" aria-hidden="true">❖</div>
      <p class="sdp-empty-text">{{ t('stakeholder.selectPrompt') }}</p>
    </div>

    <template v-else>
      <!-- 基本信息区 -->
      <section class="sdp-section sdp-section-info">
        <h4 class="sdp-section-label">{{ t('project.basicInfo') }}</h4>

        <div class="sdp-info-grid">
          <!-- 第一行：姓名 + 汇报对象（并排） -->
          <div class="sdp-info-cell">
            <span class="sdp-info-label">
              {{ t('stakeholder.stakeholderName') }}
              <span v-if="stakeholder.contact_id" class="sdp-link-tag" :title="t('stakeholder.linkedContactTooltip')">{{ t('stakeholder.linkedTag') }}</span>
              <span v-else-if="stakeholder.name" class="sdp-link-tag sdp-link-tag-muted" :title="t('stakeholder.thirdPartyTooltip')">{{ t('stakeholder.thirdParty') }}</span>
            </span>
            <div v-if="editing.field === 'name'" class="sdp-name-edit-wrapper">
              <input
                ref="nameInputRef"
                v-model="editing.value"
                class="sdp-input sdp-name-input"
                :placeholder="t('stakeholder.nameInputPlaceholder')"
                @input="onNameInput"
                @keydown.enter.prevent="onNameEnter"
                @keydown.esc.prevent="cancelEdit"
                @blur="onNameBlur"
                autocomplete="off"
              >
              <ul v-if="showNameSuggestions && nameSuggestions.length" class="sdp-name-suggestions" role="listbox" @mousedown.prevent>
                <li
                  v-for="(ct, idx) in nameSuggestions"
                  :key="ct.id"
                  :class="['sdp-name-option', { active: idx === activeSuggestionIdx }]"
                  role="option"
                  :aria-selected="idx === activeSuggestionIdx"
                  @mouseenter="activeSuggestionIdx = idx"
                  @mousedown.prevent="selectNameSuggestion(ct)"
                >
                  <span class="sdp-name-option-name">{{ ct.name }}</span>
                  <span v-if="ct.department" class="sdp-name-option-dept">{{ ct.department }}</span>
                  <span v-if="ct.position" class="sdp-name-option-pos">{{ ct.position }}</span>
                  <span v-if="ct.linked" class="sdp-name-option-linked">{{ t('stakeholder.linkedTag') }}</span>
                </li>
                <li class="sdp-name-option sdp-name-option-new" @mousedown.prevent="selectNameAsThirdParty">
                  <span class="sdp-name-option-name">{{ t('stakeholder.addAsThirdParty', { name: editing.value }) }}</span>
                </li>
              </ul>
            </div>
            <span v-else class="sdp-info-value sdp-info-editable" @dblclick="startEditName" :title="t('stakeholder.dblclickToEditHint')" tabindex="0" role="button" @keydown.enter="startEditName">{{ stakeholder.name }}</span>
          </div>

          <!-- 汇报对象（与姓名同一行） -->
          <div class="sdp-info-cell">
            <span class="sdp-info-label">{{ t('customer.reportsTo') }}</span>
            <select v-if="editing.field === 'reports_to_id'" v-focus v-model="editing.value" class="sdp-select" @change="saveEdit" @blur="saveEdit" @keydown.enter.prevent="saveEdit" @keydown.esc.prevent="cancelEdit">
              <option value="">{{ t('stakeholder.noneOrUnfilled') }}</option>
              <option v-for="s in reportableStakeholders" :key="s.id" :value="s.id">{{ s.name }}<template v-if="s.position"> · {{ s.position }}</template></option>
            </select>
            <span v-else class="sdp-info-value sdp-info-editable" @dblclick="startEditReportsTo" :title="t('stakeholder.dblclickToEdit')" tabindex="0" role="button" @keydown.enter="startEditReportsTo">
              {{ stakeholder.reports_to_name || t('stakeholder.unfilled') }}
              <span v-if="stakeholder.contact_info && stakeholder.contact_info.reports_to_name && !stakeholder.reports_to_name" class="sdp-link-tag sdp-link-tag-muted" :title="t('stakeholder.originalReportsToTooltip')">{{ t('stakeholder.originalReportsTo') }}: {{ stakeholder.contact_info.reports_to_name }}</span>
            </span>
          </div>

          <!-- 职务 -->
          <div class="sdp-info-cell">
            <span class="sdp-info-label">{{ t('customer.position') }}</span>
            <input v-if="editing.field === 'position'" v-focus v-model="editing.value" class="sdp-input" @blur="saveEdit" @keydown.enter.prevent="saveEdit" @keydown.esc.prevent="cancelEdit">
            <span v-else class="sdp-info-value sdp-info-editable" @dblclick="startEdit('position', stakeholder.position)" :title="t('stakeholder.dblclickToEdit')" tabindex="0" role="button" @keydown.enter="startEdit('position', stakeholder.position)">{{ stakeholder.position || t('stakeholder.unfilled') }}</span>
          </div>

          <!-- 级别 -->
          <div class="sdp-info-cell">
            <span class="sdp-info-label">{{ t('stakeholder.level') }}</span>
            <select v-if="editing.field === 'level'" v-focus v-model="editing.value" class="sdp-select" @change="saveEdit" @blur="saveEdit" @keydown.enter.prevent="saveEdit" @keydown.esc.prevent="cancelEdit">
              <option value="">{{ t('stakeholder.levelOptions.unknown') }}</option>
              <option value="高管">{{ t('stakeholder.levelOptions.executive') }}</option>
              <option value="中层">{{ t('stakeholder.levelOptions.middle') }}</option>
              <option value="基层">{{ t('stakeholder.levelOptions.base') }}</option>
            </select>
            <span v-else class="sdp-info-value sdp-info-editable" @dblclick="startEdit('level', stakeholder.level)" :title="t('stakeholder.dblclickToEdit')" tabindex="0" role="button" @keydown.enter="startEdit('level', stakeholder.level)">{{ stakeholder.level || t('stakeholder.levelOptions.unknown') }}</span>
          </div>

          <!-- 角色类型（原"买家角色"） -->
          <div class="sdp-info-cell">
            <span class="sdp-info-label">{{ t('stakeholder.buyerRole') }}</span>
            <select v-if="editing.field === 'buyer_role'" v-focus v-model="editing.value" class="sdp-select" @blur="saveEdit" @keydown.enter.prevent="saveEdit" @keydown.esc.prevent="cancelEdit">
              <option value="">{{ t('stakeholder.uncategorized') }}</option>
              <option value="champion">{{ t('stakeholder.buyerRoleOptions.champion') }}</option>
              <option value="blocker">{{ t('stakeholder.buyerRoleOptions.blocker') }}</option>
              <option value="mobilizer">{{ t('stakeholder.buyerRoleOptions.mobilizer') }}</option>
              <option value="guide">{{ t('stakeholder.buyerRoleOptions.guide') }}</option>
              <option value="skeptic">{{ t('stakeholder.buyerRoleOptions.skeptic') }}</option>
              <option value="coach">{{ t('stakeholder.buyerRoleOptions.coach') }}</option>
            </select>
            <span v-else class="sdp-info-value" @dblclick="startEdit('buyer_role', stakeholder.buyer_role || '')" :title="t('stakeholder.dblclickToEdit')" tabindex="0" role="button" @keydown.enter="startEdit('buyer_role', stakeholder.buyer_role || '')">
              <span class="role-badge" :class="stakeholder.buyer_role" :title="roleTooltips[stakeholder.buyer_role] || ''">
                {{ roleLabels[stakeholder.buyer_role] || stakeholder.buyer_role || t('stakeholder.uncategorized') }}
              </span>
            </span>
          </div>

          <!-- 项目角色（采购决策职能） -->
          <div class="sdp-info-cell">
            <span class="sdp-info-label">{{ t('stakeholder.projectRole') }}</span>
            <select v-if="editing.field === 'project_role'" v-focus v-model="editing.value" class="sdp-select" @blur="saveEdit" @keydown.enter.prevent="saveEdit" @keydown.esc.prevent="cancelEdit">
              <option value="">{{ t('stakeholder.uncategorized') }}</option>
              <option value="technical_buyer">{{ t('stakeholder.projectRoleOptions.technical_buyer') }}</option>
              <option value="business_buyer">{{ t('stakeholder.projectRoleOptions.business_buyer') }}</option>
              <option value="financial_buyer">{{ t('stakeholder.projectRoleOptions.financial_buyer') }}</option>
              <option value="influencer">{{ t('stakeholder.projectRoleOptions.influencer') }}</option>
              <option value="decision_maker">{{ t('stakeholder.projectRoleOptions.decision_maker') }}</option>
              <option value="user">{{ t('stakeholder.projectRoleOptions.user') }}</option>
            </select>
            <span v-else class="sdp-info-value" @dblclick="startEdit('project_role', stakeholder.project_role || '')" :title="t('stakeholder.dblclickToEdit')" tabindex="0" role="button" @keydown.enter="startEdit('project_role', stakeholder.project_role || '')">
              <span class="project-role-badge" :class="stakeholder.project_role" :title="projectRoleTooltips[stakeholder.project_role] || ''">
                {{ projectRoleLabels[stakeholder.project_role] || stakeholder.project_role || t('stakeholder.uncategorized') }}
              </span>
            </span>
          </div>

          <!-- 社交风格 -->
          <div class="sdp-info-cell">
            <span class="sdp-info-label">{{ t('stakeholder.socialStyle') }}</span>
            <select v-if="editing.field === 'social_style'" v-focus v-model="editing.value" class="sdp-select" @change="saveEdit" @blur="saveEdit" @keydown.enter.prevent="saveEdit" @keydown.esc.prevent="cancelEdit">
              <option value="">{{ t('stakeholder.socialStyleOptions.unknown') }}</option>
              <option value="analytical">{{ t('stakeholder.socialStyleOptions.analytical') }}</option>
              <option value="driver">{{ t('stakeholder.socialStyleOptions.driver') }}</option>
              <option value="amiable">{{ t('stakeholder.socialStyleOptions.amiable') }}</option>
              <option value="expressive">{{ t('stakeholder.socialStyleOptions.expressive') }}</option>
            </select>
            <span v-else class="sdp-info-value" @dblclick="startEdit('social_style', stakeholder.social_style || '')" :title="t('stakeholder.dblclickToEdit')" tabindex="0" role="button" @keydown.enter="startEdit('social_style', stakeholder.social_style || '')">
              <span class="social-style-badge" :class="stakeholder.social_style" :title="socialStyleTooltips[stakeholder.social_style] || ''">
                {{ socialStyleLabels[stakeholder.social_style] || t('stakeholder.socialStyleOptions.unknown') }}
              </span>
            </span>
          </div>

          <!-- 识别状态 -->
          <div class="sdp-info-cell">
            <span class="sdp-info-label">{{ t('common.status') }}</span>
            <select v-if="editing.field === 'status'" v-focus v-model="editing.value" class="sdp-select" @blur="saveEdit" @keydown.enter.prevent="saveEdit" @keydown.esc.prevent="cancelEdit">
              <option value="confirmed">{{ t('stakeholder.confirmed') }}</option>
              <option value="pending">{{ t('stakeholder.pending') }}</option>
            </select>
            <span v-else class="sdp-info-value" @dblclick="startEdit('status', stakeholder.status || 'pending')" :title="t('stakeholder.dblclickToEdit')" tabindex="0" role="button" @keydown.enter="startEdit('status', stakeholder.status || 'pending')">
              <span class="status-badge" :class="stakeholder.status" :title="stakeholder.status === 'confirmed' ? t('stakeholder.confirmedTooltip') : t('stakeholder.pendingTooltip')">
                {{ stakeholder.status === 'confirmed' ? t('stakeholder.confirmed') : t('stakeholder.pending') }}
              </span>
            </span>
          </div>

          <!-- 联系电话（自动同步自客户联系人） -->
          <div class="sdp-info-cell">
            <span class="sdp-info-label">
              {{ t('stakeholder.contactPhone') }}
              <span v-if="!stakeholder.contact_id" class="sdp-link-tag sdp-link-tag-muted" :title="t('stakeholder.noPhoneForThirdParty')">{{ t('stakeholder.none') }}</span>
            </span>
            <span class="sdp-info-value" :class="{ 'sdp-info-readonly': stakeholder.contact_id }" :title="stakeholder.contact_id ? t('stakeholder.autoSyncedFromContact') : ''">
              {{ stakeholder.contact_info?.phone || '—' }}
            </span>
          </div>

          <!-- 邮箱地址（自动同步自客户联系人） -->
          <div class="sdp-info-cell">
            <span class="sdp-info-label">
              {{ t('stakeholder.emailAddress') }}
              <span v-if="!stakeholder.contact_id" class="sdp-link-tag sdp-link-tag-muted" :title="t('stakeholder.noEmailForThirdParty')">{{ t('stakeholder.none') }}</span>
            </span>
            <span class="sdp-info-value" :class="{ 'sdp-info-readonly': stakeholder.contact_id }" :title="stakeholder.contact_id ? t('stakeholder.autoSyncedFromContact') : ''">
              {{ stakeholder.contact_info?.email || '—' }}
            </span>
          </div>
        </div>
      </section>

      <!-- 数值信号格 -->
      <section class="sdp-section">
        <h4 class="sdp-section-label">{{ t('stakeholder.keyMetrics') }}</h4>
        <div class="sdp-stats-row">
          <div class="sdp-stat-card" @mouseenter="showTrend('support_level')" @mouseleave="hideTrend()">
            <span class="sdp-stat-label">{{ t('stakeholder.supportLevel') }}</span>
            <div class="sdp-stat-track">
              <span v-for="i in 10" :key="i" class="sdp-stat-cell" :class="{ filled: i <= stakeholder.support_level, support: i <= stakeholder.support_level }"></span>
            </div>
            <div class="sdp-stat-bottom">
              <span class="sdp-stat-num">{{ stakeholder.support_level }}</span>
              <span v-if="projectedSupport !== null" class="sdp-projected-pill" :class="projectedSupport >= stakeholder.support_level ? 'up' : 'down'">
                → {{ projectedSupport }}
              </span>
            </div>
            <div v-if="hoveredMetric === 'support_level'" class="sdp-trend-pop" role="tooltip">
              <div :ref="el => trendRefs.support_level = el" class="sdp-trend-canvas"></div>
              <p v-if="!hasMetricHistory('support_level')" class="sdp-trend-empty">{{ t('stakeholder.noChangeRecords') }}</p>
            </div>
          </div>
          <div class="sdp-stat-card" @mouseenter="showTrend('decision_power')" @mouseleave="hideTrend()">
            <span class="sdp-stat-label">{{ t('stakeholder.decisionPower') }}</span>
            <div class="sdp-stat-track">
              <span v-for="i in 10" :key="i" class="sdp-stat-cell" :class="{ filled: i <= stakeholder.decision_power, power: i <= stakeholder.decision_power }"></span>
            </div>
            <span class="sdp-stat-num">{{ stakeholder.decision_power }}</span>
            <div v-if="hoveredMetric === 'decision_power'" class="sdp-trend-pop" role="tooltip">
              <div :ref="el => trendRefs.decision_power = el" class="sdp-trend-canvas"></div>
              <p v-if="!hasMetricHistory('decision_power')" class="sdp-trend-empty">{{ t('stakeholder.noChangeRecords') }}</p>
            </div>
          </div>
          <div class="sdp-stat-card" @mouseenter="showTrend('urgency')" @mouseleave="hideTrend()">
            <span class="sdp-stat-label">{{ t('stakeholder.urgency') }}</span>
            <div class="sdp-stat-track">
              <span v-for="i in 10" :key="i" class="sdp-stat-cell" :class="{ filled: i <= stakeholder.urgency, urgency: i <= stakeholder.urgency }"></span>
            </div>
            <div class="sdp-stat-bottom">
              <span class="sdp-stat-num">{{ stakeholder.urgency }}</span>
              <span v-if="projectedUrgency !== null" class="sdp-projected-pill" :class="projectedUrgency >= stakeholder.urgency ? 'up' : 'down'">
                → {{ projectedUrgency }}
              </span>
            </div>
            <div v-if="hoveredMetric === 'urgency'" class="sdp-trend-pop" role="tooltip">
              <div :ref="el => trendRefs.urgency = el" class="sdp-trend-canvas"></div>
              <p v-if="!hasMetricHistory('urgency')" class="sdp-trend-empty">{{ t('stakeholder.noChangeRecords') }}</p>
            </div>
          </div>
        </div>
      </section>

      <!-- 描述信息 -->
      <section class="sdp-section">
        <h4 class="sdp-section-label">{{ t('stakeholder.descriptionInfo') }}</h4>

        <div class="sdp-desc-block">
          <span class="sdp-info-label">{{ t('stakeholder.responsibilities') }}</span>
          <textarea v-if="editing.field === 'responsibilities'" v-focus v-model="editing.value" class="sdp-textarea" rows="3" @blur="saveEdit" @keydown.ctrl.enter.prevent="saveEdit" @keydown.esc.prevent="cancelEdit"></textarea>
          <p v-else class="sdp-desc-text sdp-desc-editable" @dblclick="startEdit('responsibilities', stakeholder.responsibilities)" :title="t('stakeholder.dblclickToEdit')" tabindex="0" role="button" @keydown.enter="startEdit('responsibilities', stakeholder.responsibilities)">{{ stakeholder.responsibilities || t('stakeholder.dblclickToAdd') }}</p>
        </div>

        <div class="sdp-desc-block">
          <span class="sdp-info-label">{{ t('stakeholder.personalAgenda') }}</span>
          <textarea v-if="editing.field === 'personal_agenda'" v-focus v-model="editing.value" class="sdp-textarea" rows="3" @blur="saveEdit" @keydown.ctrl.enter.prevent="saveEdit" @keydown.esc.prevent="cancelEdit"></textarea>
          <p v-else class="sdp-desc-text sdp-desc-editable" @dblclick="startEdit('personal_agenda', stakeholder.personal_agenda)" :title="t('stakeholder.dblclickToEdit')" tabindex="0" role="button" @keydown.enter="startEdit('personal_agenda', stakeholder.personal_agenda)">{{ stakeholder.personal_agenda || t('stakeholder.dblclickToAdd') }}</p>
        </div>
      </section>

      <!-- 交流/接触历史 -->
      <section class="sdp-section sdp-section-history" v-if="sortedHistory.length">
        <div class="sdp-section-header">
          <h4 class="sdp-section-label">{{ t('stakeholder.contactHistory', { count: sortedHistory.length }) }}</h4>
        </div>
        <div class="sdp-history-list">
          <div v-for="(item, idx) in sortedHistory" :key="idx" class="sdp-history-item">
            <span class="sdp-history-dot" :class="item.type" aria-hidden="true"></span>
            <div class="sdp-history-body">
              <div class="sdp-history-top">
                <span class="sdp-history-type" :class="item.type">{{ item.typeLabel }}</span>
                <span class="sdp-history-date">{{ item.date }}</span>
              </div>
              <p class="sdp-history-desc">{{ item.description }}</p>
            </div>
          </div>
        </div>
      </section>

      <!-- 操作区 -->
      <section class="sdp-section sdp-section-actions">
        <button type="button" class="btn-merge" @click="$emit('merge', stakeholder)">{{ t('stakeholder.mergeIntoOther') }}</button>
        <button type="button" class="btn-delete" @click="$emit('delete', stakeholder)" :aria-label="t('stakeholder.removeStakeholderAria', { name: stakeholder.name })">
          <span class="btn-delete-icon" aria-hidden="true">
            <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M3 4h10M6 4V2.5a1 1 0 011-1h2a1 1 0 011 1V4M5 4l.5 9a1 1 0 001 1h3a1 1 0 001-1L11 4"/>
            </svg>
          </span>
          {{ t('stakeholder.removeStakeholder') }}
        </button>
      </section>
    </template>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import * as d3 from 'd3'
import * as salesTwinApi from '../api/salesTwin'

const { t } = useI18n()

const props = defineProps({
  stakeholder: { type: Object, default: null },
  stateLogs: { type: Array, default: () => [] },
  fermentationResult: { type: Object, default: null },
  meetingPlans: { type: Array, default: () => [] },
  roleLabels: { type: Object, default: () => ({}) },
  roleTooltips: { type: Object, default: () => ({}) },
  projectRoleLabels: { type: Object, default: () => ({}) },
  projectRoleTooltips: { type: Object, default: () => ({}) },
  // 项目内所有干系人，用于"汇报对象"下拉选择
  stakeholders: { type: Array, default: () => [] },
  // 项目关联客户的联系人列表，用于姓名模糊匹配
  customerContacts: { type: Array, default: () => [] },
})

const emit = defineEmits(['edit', 'merge', 'updated', 'delete'])

// v-focus 指令：渲染时自动聚焦
const vFocus = { mounted: (el) => el.focus() }

// 双击内联编辑状态
const editing = reactive({ field: null, value: '' })
let originalValue = ''

// 姓名 typeahead 状态
const nameInputRef = ref(null)
const showNameSuggestions = ref(false)
const nameSuggestions = ref([])
const activeSuggestionIdx = ref(-1)
// 在姓名编辑过程中暂存"待提交的 contact_id"，selectNameSuggestion 时设置
let pendingContactId = null

// 趋势悬浮状态
const hoveredMetric = ref(null)
const trendRefs = reactive({ support_level: null, decision_power: null, urgency: null })

function showTrend(metric) { hoveredMetric.value = metric }
function hideTrend() { hoveredMetric.value = null }

function hasMetricHistory(metricKey) {
  if (!props.stakeholder) return false
  const actual = actualHistory.value[metricKey] || []
  return actual.length > 1
}

function drawMiniChart(metricKey, color, hasProj) {
  const container = trendRefs[metricKey]
  if (!container) return
  container.innerHTML = ''
  const containerW = container.clientWidth || 260
  const containerH = 100
  const margin = { top: 8, right: 12, bottom: 18, left: 24 }
  const width = Math.max(containerW - margin.left - margin.right, 100)
  const height = containerH - margin.top - margin.bottom

  const svg = d3.select(container).append('svg')
    .attr('width', containerW).attr('height', containerH).attr('role', 'img')
  const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`)

  const actualPts = (actualHistory.value[metricKey] || []).map(p => ({ ...p, kind: 'actual' }))
  const projPts = (projectionData.value[metricKey] || []).map(p => ({ ...p, kind: 'proj' }))
  const allPts = [...actualPts, ...projPts]
  if (allPts.length < 2) return

  const xScale = d3.scaleTime().domain(d3.extent(allPts, d => d.t)).range([0, width])
  const yScale = d3.scaleLinear().domain([0, 10]).range([height, 0])

  g.append('g').attr('transform', `translate(0,${height})`)
    .call(d3.axisBottom(xScale).ticks(Math.min(allPts.length, 4)).tickFormat(d3.timeFormat('%m/%d')))
    .selectAll('text').style('font-size', '9px').style('fill', 'var(--text-muted)')

  g.append('g').call(d3.axisLeft(yScale).ticks(4))
    .selectAll('text').style('font-size', '9px').style('fill', 'var(--text-muted)')

  const line = d3.line().x(d => xScale(d.t)).y(d => yScale(d.v)).curve(d3.curveMonotoneX)

  if (actualPts.length >= 2) {
    g.append('path').datum(actualPts).attr('fill', 'none').attr('stroke', color)
      .attr('stroke-width', 1.8).attr('d', line)
    g.selectAll('.dot-actual').data(actualPts).enter().append('circle')
      .attr('class', 'dot-actual').attr('cx', d => xScale(d.t)).attr('cy', d => yScale(d.v))
      .attr('r', 2.5).attr('fill', color)
  }

  if (hasProj && projPts.length >= 2) {
    g.append('path').datum(projPts).attr('fill', 'none').attr('stroke', color)
      .attr('stroke-width', 1.5).attr('stroke-dasharray', '4,3').attr('d', line)
    g.selectAll('.dot-proj').data(projPts.slice(1)).enter().append('circle')
      .attr('class', 'dot-proj').attr('cx', d => xScale(d.t)).attr('cy', d => yScale(d.v))
      .attr('r', 2).attr('fill', '#fff').attr('stroke', color).attr('stroke-width', 1.2)
  }
}

function startEdit(field, value) {
  editing.field = field
  editing.value = value || ''
  originalValue = value || ''
}

function cancelEdit() {
  editing.field = null
  editing.value = ''
  showNameSuggestions.value = false
  pendingContactId = null
}

// ===== 姓名 typeahead =====
function startEditName() {
  if (!props.stakeholder) return
  editing.field = 'name'
  editing.value = props.stakeholder.name || ''
  originalValue = props.stakeholder.name || ''
  // 初始 pendingContactId 为当前 contact_id，输入清空时变 null
  pendingContactId = props.stakeholder.contact_id || null
  showNameSuggestions.value = false
  activeSuggestionIdx.value = -1
  nextTick(() => {
    nameInputRef.value?.focus()
    nameInputRef.value?.select()
  })
}

function onNameInput() {
  const q = (editing.value || '').trim().toLowerCase()
  // 输入发生变化：默认视为第三方人员（contact_id=null），除非再次选中建议
  pendingContactId = null
  if (!q) {
    nameSuggestions.value = []
    showNameSuggestions.value = false
    activeSuggestionIdx.value = -1
    return
  }
  const matched = (props.customerContacts || []).filter(ct =>
    (ct.name || '').toLowerCase().includes(q) ||
    (ct.department || '').toLowerCase().includes(q) ||
    (ct.position || '').toLowerCase().includes(q)
  ).slice(0, 8)
  nameSuggestions.value = matched
  showNameSuggestions.value = matched.length > 0
  activeSuggestionIdx.value = matched.length > 0 ? 0 : -1
}

function onNameBlur() {
  // 延迟以允许 mousedown 事件先触发选择
  setTimeout(() => {
    showNameSuggestions.value = false
    saveNameEdit()
  }, 150)
}

function onNameEnter() {
  if (showNameSuggestions.value && activeSuggestionIdx.value >= 0) {
    const ct = nameSuggestions.value[activeSuggestionIdx.value]
    if (ct) {
      selectNameSuggestion(ct)
      return
    }
  }
  // 无选中建议：作为第三方人员保存
  saveNameEdit()
}

function selectNameSuggestion(ct) {
  editing.value = ct.name
  pendingContactId = ct.id
  showNameSuggestions.value = false
  activeSuggestionIdx.value = -1
  saveNameEdit()
}

function selectNameAsThirdParty() {
  pendingContactId = null
  showNameSuggestions.value = false
  saveNameEdit()
}

async function saveNameEdit() {
  if (!editing.field || !props.stakeholder) return
  const newName = (editing.value || '').trim()
  const oldName = props.stakeholder.name || ''
  const oldContactId = props.stakeholder.contact_id || null
  const newContactId = pendingContactId

  // 名字和 contact_id 都没变化：直接取消
  if (newName === oldName && newContactId === oldContactId) {
    cancelEdit()
    return
  }

  const payload = { name: newName }
  // 若 contact_id 有变化，一并发送；后端会自动带出 reports_to_id
  if (newContactId !== oldContactId) {
    payload.contact_id = newContactId
  }
  try {
    const res = await salesTwinApi.updateStakeholder(props.stakeholder.id, payload)
    emit('updated', res)
  } catch (e) {
    console.warn('Update name failed:', e)
  } finally {
    cancelEdit()
  }
}

// ===== 汇报对象 =====
const reportableStakeholders = computed(() => {
  if (!props.stakeholder || !props.stakeholders) return []
  // 排除自身
  return props.stakeholders
    .filter(s => s.id !== props.stakeholder.id)
    .map(s => ({ id: s.id, name: s.name, position: s.position }))
})

function startEditReportsTo() {
  if (!props.stakeholder) return
  editing.field = 'reports_to_id'
  editing.value = props.stakeholder.reports_to_id || ''
  // originalValue 统一为 null 或整数，与 saveEdit 中的 newValue 类型对齐
  originalValue = props.stakeholder.reports_to_id || null
}

async function saveEdit() {
  if (!editing.field || !props.stakeholder) return
  let newValue = typeof editing.value === 'string' ? editing.value.trim() : editing.value
  // ID 类字段（reports_to_id / contact_id）：空字符串/0 统一为 null，数字字符串转整数
  // 避免后端 "5" == 5 被判为相等而跳过更新
  if (editing.field === 'reports_to_id' || editing.field === 'contact_id') {
    if (newValue === '' || newValue === 0 || newValue === '0' || newValue === null) {
      newValue = null
    } else if (typeof newValue === 'string' && /^\d+$/.test(newValue)) {
      newValue = parseInt(newValue, 10)
    }
  }
  // 比较：ID 类字段已统一为 null 或整数，可直接与 originalValue 比较
  if (newValue === originalValue) {
    cancelEdit()
    return
  }
  const payload = { [editing.field]: newValue }
  try {
    const res = await salesTwinApi.updateStakeholder(props.stakeholder.id, payload)
    emit('updated', res)
  } catch (e) {
    console.warn('Update failed:', e)
  } finally {
    cancelEdit()
  }
}

// 颜色配置
const COLORS = {
  support: '#10B981',
  power: '#3B82F6',
  urgency: '#F59E0B'
}

// 社交风格标签与沟通建议 tooltip
const socialStyleLabels = computed(() => ({
  analytical: t('stakeholder.socialStyleOptions.analytical'),
  driver: t('stakeholder.socialStyleOptions.driver'),
  amiable: t('stakeholder.socialStyleOptions.amiable'),
  expressive: t('stakeholder.socialStyleOptions.expressive'),
}))
const socialStyleTooltips = computed(() => ({
  analytical: t('stakeholder.socialStyleTooltips.analytical'),
  driver: t('stakeholder.socialStyleTooltips.driver'),
  amiable: t('stakeholder.socialStyleTooltips.amiable'),
  expressive: t('stakeholder.socialStyleTooltips.expressive'),
}))
const METRICS = computed(() => [
  { key: 'support_level', label: t('stakeholder.supportLevel'), color: COLORS.support },
  { key: 'decision_power', label: t('stakeholder.decisionPower'), color: COLORS.power },
  { key: 'urgency', label: t('stakeholder.urgency'), color: COLORS.urgency }
])

// ===== 实际值历史（来自StateChangeLog，实线） =====
const actualHistory = computed(() => {
  if (!props.stakeholder) return {}
  const sid = props.stakeholder.id
  const result = {}
  for (const m of METRICS.value) {
    const logs = props.stateLogs
      .filter(l => l.stakeholder_id === sid && l.attribute_name === m.key)
      .sort((a, b) => new Date(a.created_at) - new Date(b.created_at))
    const points = []
    if (logs.length > 0) {
      points.push({ t: new Date(logs[0].created_at), v: parseFloat(logs[0].old_value) || 0, isStart: true })
      for (const l of logs) {
        points.push({ t: new Date(l.created_at), v: parseFloat(l.new_value) || 0 })
      }
    } else {
      points.push({ t: new Date(props.stakeholder.created_at || Date.now()), v: props.stakeholder[m.key], isStart: true })
      points.push({ t: new Date(props.stakeholder.updated_at || Date.now()), v: props.stakeholder[m.key] })
    }
    result[m.key] = points
  }
  return result
})

// ===== 推演预测值（来自fermentationResult，虚线） =====
const projectionData = computed(() => {
  if (!props.stakeholder || !props.fermentationResult?.narrative_history) return {}
  const sid = props.stakeholder.id
  const result = { support_level: [], urgency: [] }

  const now = new Date()
  result.support_level.push({ t: now, v: props.stakeholder.support_level })
  result.urgency.push({ t: now, v: props.stakeholder.urgency })

  let curSupport = props.stakeholder.support_level
  let curUrgency = props.stakeholder.urgency
  const dayOffset = 24 * 60 * 60 * 1000

  for (let i = 0; i < props.fermentationResult.narrative_history.length; i++) {
    const nh = props.fermentationResult.narrative_history[i]
    const changes = nh.state_changes || []
    const dayTime = new Date(now.getTime() + dayOffset * (i + 1))
    let supportChanged = false
    let urgencyChanged = false
    for (const c of changes) {
      if (c.stakeholder_id === sid || c.stakeholder_name === props.stakeholder.name) {
        if (c.new_support_level !== undefined && c.new_support_level !== null) {
          curSupport = parseFloat(c.new_support_level)
          supportChanged = true
        }
        if (c.new_urgency !== undefined && c.new_urgency !== null) {
          curUrgency = parseFloat(c.new_urgency)
          urgencyChanged = true
        }
      }
    }
    if (supportChanged) result.support_level.push({ t: dayTime, v: curSupport })
    if (urgencyChanged) result.urgency.push({ t: dayTime, v: curUrgency })
  }
  return result
})

const projectedSupport = computed(() => {
  const pts = projectionData.value.support_level
  if (!pts || pts.length <= 1) return null
  return pts[pts.length - 1].v
})

const projectedUrgency = computed(() => {
  const pts = projectionData.value.urgency
  if (!pts || pts.length <= 1) return null
  return pts[pts.length - 1].v
})

// ===== 交流历史 =====
const sortedHistory = computed(() => {
  if (!props.stakeholder) return []
  const sid = props.stakeholder.id
  const items = []

  for (const p of props.meetingPlans) {
    if (p.stakeholder_id === sid) {
      items.push({
        type: 'meeting',
        typeLabel: t('stakeholder.visitPlan'),
        date: formatDate(p.created_at),
        timestamp: new Date(p.created_at || Date.now()).getTime(),
        description: t('stakeholder.meetingDesc', { type: p.meeting_type || t('stakeholder.visit'), name: p.name || p.meeting_purpose || '' })
      })
    }
  }

  for (const l of props.stateLogs) {
    if (l.stakeholder_id === sid) {
      const fieldLabelMap = { support_level: t('stakeholder.supportLevel'), decision_power: t('stakeholder.decisionPower'), urgency: t('stakeholder.urgency') }
      const fieldLabel = fieldLabelMap[l.attribute_name] || l.attribute_name
      const sourceLabel = l.change_source === 'manual_edit' ? t('stakeholder.manualEdit') : (l.change_source === 'feedback_parser' ? t('stakeholder.feedbackParse') : l.change_source)
      const desc = l.reasoning
        ? t('stakeholder.changeDescWithReason', { field: fieldLabel, old: l.old_value || t('stakeholder.empty'), new: l.new_value, reasoning: l.reasoning })
        : t('stakeholder.changeDesc', { field: fieldLabel, old: l.old_value || t('stakeholder.empty'), new: l.new_value })
      items.push({
        type: 'change',
        typeLabel: sourceLabel,
        date: formatDate(l.created_at),
        timestamp: new Date(l.created_at || Date.now()).getTime(),
        description: desc
      })
    }
  }

  return items.sort((a, b) => b.timestamp - a.timestamp)
})

function formatDate(d) {
  if (!d) return ''
  const dt = new Date(d)
  return `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, '0')}-${String(dt.getDate()).padStart(2, '0')} ${String(dt.getHours()).padStart(2, '0')}:${String(dt.getMinutes()).padStart(2, '0')}`
}

// 监听悬浮指标变化 → 绘制迷你趋势图
watch(hoveredMetric, (metric) => {
  if (!metric) return
  nextTick(() => {
    const color = COLORS[metric === 'support_level' ? 'support' : metric === 'decision_power' ? 'power' : 'urgency']
    const hasProj = metric !== 'decision_power' && (projectionData.value[metric] || []).length > 1
    drawMiniChart(metric, color, hasProj)
  })
})

// 数据变化时重绘当前悬浮的迷你图
watch(() => props.stateLogs, () => {
  if (hoveredMetric.value) {
    const m = hoveredMetric.value
    const color = COLORS[m === 'support_level' ? 'support' : m === 'decision_power' ? 'power' : 'urgency']
    const hasProj = m !== 'decision_power' && (projectionData.value[m] || []).length > 1
    nextTick(() => drawMiniChart(m, color, hasProj))
  }
}, { deep: true })

watch(() => props.fermentationResult, () => {
  if (hoveredMetric.value) {
    const m = hoveredMetric.value
    const color = COLORS[m === 'support_level' ? 'support' : m === 'decision_power' ? 'power' : 'urgency']
    nextTick(() => drawMiniChart(m, color, true))
  }
})
</script>

<style scoped>
.sdp-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow-y: auto;
  overflow-x: hidden;
  min-width: 0;
}

.sdp-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  min-height: 300px;
  color: var(--text-muted);
}

.sdp-empty-icon {
  font-size: 2.5rem;
  opacity: 0.4;
}

.sdp-empty-text {
  font-size: var(--fs-sm);
  margin: 0;
}

/* ===== 区块通用 ===== */
.sdp-section {
  padding: 16px 0;
  border-bottom: 1px solid var(--border);
}

.sdp-section:last-child {
  border-bottom: none;
}

.sdp-section-label {
  font-size: var(--fs-xs);
  font-weight: 700;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin: 0 0 12px 0;
}

.sdp-section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.sdp-section-header .sdp-section-label {
  margin-bottom: 0;
}

/* ===== 基本信息网格 ===== */
.sdp-info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px 24px;
}

.sdp-info-cell {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}

.sdp-info-cell-full {
  grid-column: 1 / -1;
}

/* 只读字段（如联系电话、邮箱，由客户联系人自动同步） */
.sdp-info-readonly {
  color: var(--text-secondary, #494A4D);
  font-style: italic;
  cursor: default;
}

/* ===== 关联标签 ===== */
.sdp-link-tag {
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

.sdp-link-tag-muted {
  background: rgba(107, 114, 128, 0.1);
  color: #4B5563;
  border-color: rgba(107, 114, 128, 0.25);
  font-weight: 500;
}

/* ===== 姓名 typeahead ===== */
.sdp-name-edit-wrapper {
  position: relative;
  width: 100%;
}

.sdp-name-input {
  width: 100%;
}

.sdp-name-suggestions {
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

.sdp-name-option {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 10px;
  cursor: pointer;
  font-size: var(--fs-sm);
  border-bottom: 1px solid var(--border, #F0EEE6);
  transition: background 0.1s;
}

.sdp-name-option:last-child {
  border-bottom: none;
}

.sdp-name-option:hover,
.sdp-name-option.active {
  background: rgba(205, 80, 54, 0.06);
}

.sdp-name-option-name {
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
}

.sdp-name-option-dept,
.sdp-name-option-pos {
  color: var(--text-muted);
  font-size: var(--fs-xs);
  white-space: nowrap;
}

.sdp-name-option-linked {
  margin-left: auto;
  font-size: 10px;
  padding: 1px 5px;
  border-radius: 3px;
  background: rgba(203, 184, 140, 0.2);
  color: #8B6F35;
}

.sdp-name-option-new {
  color: var(--accent, #CD5036);
  font-weight: 600;
  justify-content: center;
  border-top: 1px dashed var(--border, #E8E8E0);
}

.sdp-name-option-new .sdp-name-option-name {
  color: var(--accent, #CD5036);
  font-weight: 600;
}

.sdp-info-label {
  font-size: var(--fs-xs);
  font-weight: 600;
  color: var(--text-muted);
}

.sdp-info-value {
  font-size: var(--fs-sm);
  color: var(--text-primary);
  line-height: 1.4;
  min-height: 20px;
}

.sdp-info-editable {
  cursor: pointer;
  padding: 2px 4px;
  margin: -2px -4px;
  border-radius: 3px;
  transition: background-color 0.1s;
}

.sdp-info-editable:hover {
  background-color: rgba(205, 80, 54, 0.06);
}

.sdp-info-editable:focus-visible {
  outline: 2px solid var(--focus-ring);
  outline-offset: 1px;
}

/* ===== 输入控件 ===== */
.sdp-input,
.sdp-select {
  padding: 6px 10px;
  border: 1px solid var(--border);
  border-radius: 4px;
  font-size: var(--fs-sm);
  font-family: inherit;
  background: var(--bg-base);
  color: var(--text-primary);
}

.sdp-input:focus,
.sdp-select:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 2px rgba(205, 80, 54, 0.12);
}

.sdp-textarea {
  width: 100%;
  padding: 6px 10px;
  border: 1px solid var(--border);
  border-radius: 4px;
  font-size: var(--fs-sm);
  font-family: inherit;
  background: var(--bg-base);
  color: var(--text-primary);
  resize: vertical;
  min-height: 48px;
}

.sdp-textarea:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 2px rgba(205, 80, 54, 0.12);
}

/* ===== 数值信号格 - 卡片式 ===== */
.sdp-stats-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.sdp-stat-card {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 10px 12px;
  background: var(--bg-base);
  border-radius: 6px;
  border: 1px solid var(--border);
}

.sdp-stat-label {
  font-size: var(--fs-xs);
  font-weight: 600;
  color: var(--text-muted);
}

.sdp-stat-track {
  display: flex;
  gap: 2px;
}

.sdp-stat-cell {
  flex: 1;
  height: 8px;
  border-radius: 2px;
  background: var(--border);
}

.sdp-stat-cell.support { background: var(--green); }
.sdp-stat-cell.power { background: var(--blue); }
.sdp-stat-cell.urgency { background: var(--yellow); }

.sdp-stat-bottom {
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.sdp-stat-num {
  font-size: var(--fs-md);
  font-weight: 700;
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
}

.sdp-projected-pill {
  font-size: var(--fs-xs);
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 8px;
}

.sdp-projected-pill.up { background: rgba(16, 185, 129, 0.1); color: var(--green); }
.sdp-projected-pill.down { background: rgba(196, 57, 28, 0.1); color: var(--red); }

.role-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: var(--fs-xs);
  font-weight: 600;
  background: var(--bg-surface);
  color: var(--text-secondary);
}
.role-badge.champion { background: rgba(16, 185, 129, 0.12); color: var(--green); }
.role-badge.blocker { background: rgba(196, 57, 28, 0.1); color: var(--red); }
.role-badge.mobilizer { background: rgba(144, 176, 200, 0.12); color: var(--blue); }
.role-badge.guide { background: rgba(205, 80, 54, 0.1); color: var(--accent); }
.role-badge.skeptic { background: rgba(205, 80, 54, 0.1); color: var(--accent); }
.role-badge.coach { background: rgba(144, 176, 200, 0.12); color: var(--blue); }

/* 项目角色徽章 */
.project-role-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: var(--fs-xs);
  font-weight: 600;
  line-height: 1.6;
  cursor: help;
  border: 1px solid transparent;
}
.project-role-badge.technical_buyer { background: rgba(144, 176, 200, 0.12); color: var(--blue); border-color: rgba(144, 176, 200, 0.2); }
.project-role-badge.business_buyer { background: rgba(205, 80, 54, 0.1); color: var(--accent); border-color: rgba(205, 80, 54, 0.2); }
.project-role-badge.financial_buyer { background: rgba(203, 184, 140, 0.18); color: #8B6F35; border-color: rgba(203, 184, 140, 0.3); }
.project-role-badge.influencer { background: rgba(17, 138, 88, 0.1); color: var(--green); border-color: rgba(17, 138, 88, 0.2); }
.project-role-badge.decision_maker { background: rgba(196, 57, 28, 0.1); color: var(--red); border-color: rgba(196, 57, 28, 0.2); }
.project-role-badge.user { background: rgba(147, 149, 157, 0.15); color: var(--text-secondary); border-color: rgba(147, 149, 157, 0.2); }

/* 社交风格徽章 */
.social-style-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: var(--fs-xs);
  font-weight: 600;
  line-height: 1.6;
  cursor: help;
  border: 1px solid transparent;
  background: rgba(147, 149, 157, 0.12);
  color: var(--text-secondary);
  border-color: rgba(147, 149, 157, 0.2);
}
.social-style-badge.analytical { background: rgba(144, 176, 200, 0.12); color: var(--blue); border-color: rgba(144, 176, 200, 0.2); }
.social-style-badge.driver { background: rgba(205, 80, 54, 0.1); color: var(--accent); border-color: rgba(205, 80, 54, 0.2); }
.social-style-badge.amiable { background: rgba(17, 138, 88, 0.1); color: var(--green); border-color: rgba(17, 138, 88, 0.2); }
.social-style-badge.expressive { background: rgba(203, 184, 140, 0.18); color: #8B6F35; border-color: rgba(203, 184, 140, 0.3); }

/* 识别状态徽章 */
.status-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: var(--fs-xs);
  font-weight: 600;
  line-height: 1.6;
  cursor: help;
  border: 1px solid transparent;
}
.status-badge.confirmed {
  background: rgba(17, 138, 88, 0.12);
  color: var(--green);
  border-color: rgba(17, 138, 88, 0.2);
}
.status-badge.pending {
  background: rgba(203, 184, 140, 0.2);
  color: #8B6F35;
  border-color: rgba(203, 184, 140, 0.4);
  position: relative;
}
.status-badge.pending::before {
  content: '';
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #CBB88C;
  margin-right: 4px;
  vertical-align: middle;
}

/* ===== 描述信息 ===== */
.sdp-desc-block {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 12px;
}

.sdp-desc-block:last-child {
  margin-bottom: 0;
}

.sdp-desc-text {
  font-size: var(--fs-sm);
  color: var(--text-primary);
  line-height: 1.5;
  margin: 0;
  cursor: pointer;
  padding: 4px 6px;
  margin: -4px -6px;
  border-radius: 3px;
  transition: background-color 0.1s;
}

.sdp-desc-text:hover {
  background-color: rgba(205, 80, 54, 0.06);
}



/* ===== 趋势悬浮弹出层 ===== */
.sdp-stat-card {
  position: relative;
}

.sdp-trend-pop {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  margin-top: 6px;
  padding: 8px 10px;
  background: var(--bg-card);
  border: 1px solid var(--border-strong);
  border-radius: 6px;
  box-shadow: 0 4px 16px rgba(21, 23, 29, 0.1);
  z-index: 20;
}

.sdp-trend-canvas {
  width: 100%;
  height: 100px;
}

.sdp-trend-canvas :deep(svg) {
  display: block;
}

.sdp-trend-empty {
  font-size: var(--fs-xs);
  color: var(--text-muted);
  text-align: center;
  padding: 12px 0;
  margin: 0;
}

/* ===== 历史记录 ===== */
.sdp-history-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.sdp-history-item {
  display: flex;
  gap: 8px;
}

.sdp-history-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-top: 5px;
  flex-shrink: 0;
}

.sdp-history-dot.meeting { background: var(--blue); }
.sdp-history-dot.change { background: var(--yellow); }
.sdp-history-dot.feedback { background: var(--green); }

.sdp-history-body {
  flex: 1;
  min-width: 0;
}

.sdp-history-top {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 2px;
}

.sdp-history-type {
  font-size: var(--fs-xs);
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 3px;
  background: var(--bg-surface);
  color: var(--text-secondary);
}

.sdp-history-type.meeting { background: rgba(144, 176, 200, 0.12); color: var(--blue); }
.sdp-history-type.change { background: rgba(205, 80, 54, 0.1); color: var(--accent); }
.sdp-history-type.feedback { background: rgba(16, 185, 129, 0.1); color: var(--green); }

.sdp-history-date {
  font-size: var(--fs-xs);
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}

.sdp-history-desc {
  font-size: var(--fs-xs);
  color: var(--text-secondary);
  line-height: 1.5;
  margin: 0;
  word-break: break-word;
}

/* ===== 操作区 ===== */
.sdp-section-actions {
  padding: 12px 0;
  display: flex;
  justify-content: space-between;
  gap: 8px;
  flex-wrap: wrap;
}

.btn-merge {
  background: transparent;
  border: 1px dashed var(--border-strong);
  color: var(--text-secondary);
  font-size: var(--fs-xs);
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-merge:hover {
  border-color: var(--accent);
  color: var(--accent);
  background: rgba(205, 80, 54, 0.04);
}

.btn-merge:focus-visible {
  outline: 2px solid var(--focus-ring);
  outline-offset: 2px;
}

.btn-delete {
  background: transparent;
  border: 1px dashed var(--red, #C4391C);
  color: var(--red, #C4391C);
  font-size: var(--fs-xs);
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.15s;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.btn-delete:hover {
  background: rgba(196, 57, 28, 0.06);
  border-style: solid;
}

.btn-delete:focus-visible {
  outline: 2px solid var(--focus-ring);
  outline-offset: 2px;
}

.btn-delete-icon {
  display: inline-flex;
  width: 12px;
  height: 12px;
}

.btn-delete-icon svg {
  width: 100%;
  height: 100%;
}

@media (prefers-reduced-motion: reduce) {
  * {
    transition: none !important;
    animation: none !important;
  }
}
</style>
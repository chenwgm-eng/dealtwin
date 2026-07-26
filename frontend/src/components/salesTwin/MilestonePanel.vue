<template>
  <div class="milestone-panel">
    <div class="mp-header">
      <span class="section-deco">◇</span>
      <h3 class="mp-title">{{ t('milestone.title') }}</h3>

      <!-- 销售模式选择（紧凑选项卡） -->
      <div class="mp-salesmode" role="group" :aria-label="t('milestone.salesMode')">
        <span v-if="!currentMode" class="mp-salesmode-hint">{{ t('milestone.selectSalesMode') }}</span>
        <button
          v-for="opt in SALES_MODES"
          :key="opt"
          type="button"
          :class="['mp-mode-tab', { active: currentMode === opt }]"
          :disabled="modeSaving"
          @click="changeSalesMode(opt)"
        >{{ t('milestone.salesModes.' + opt) }}</button>
      </div>
    </div>

    <!-- 加载 / 错误 / 空状态 -->
    <div v-if="loading" class="mp-state">{{ t('common.loading') }}</div>
    <div v-else-if="loadError" class="mp-state mp-state-error">
      {{ t('milestone.loadFailed') }}
      <button type="button" class="mp-link" @click="loadMilestones">{{ t('common.retry') }}</button>
    </div>
    <div v-else-if="!orderedMilestones.length" class="mp-state">{{ t('milestone.empty') }}</div>

    <!-- 横向 5 节点里程碑条 -->
    <div v-else class="mp-track" role="list">
      <button
        v-for="(m, idx) in orderedMilestones"
        :key="m.milestone"
        type="button"
        role="listitem"
        :class="['mp-node', m.decision || 'pending']"
        :aria-label="`${m.milestone.toUpperCase()} ${milestoneLabel(m)}`"
        @click="openEditor(m)"
      >
        <span class="mp-node-dot" aria-hidden="true">
          <span v-if="m.decision === 'go'">✓</span>
          <span v-else-if="m.decision === 'no_go'">×</span>
        </span>
        <span class="mp-node-code">{{ m.milestone.toUpperCase() }}</span>
        <span class="mp-node-label">{{ milestoneLabel(m) }}</span>
        <span class="mp-node-decision">{{ decisionLabel(m.decision) }}</span>
        <span v-if="idx < orderedMilestones.length - 1" class="mp-node-line" aria-hidden="true"></span>
      </button>
    </div>

    <!-- 里程碑评估弹窗 -->
    <div v-if="editing" class="modal-overlay" tabindex="-1" role="dialog" aria-modal="true"
      :aria-label="t('milestone.evaluateTitle')"
      @click.self="closeEditor" @keydown.esc="closeEditor">
      <div class="modal mp-modal">
        <div class="modal-header">
          <h3 class="modal-title">
            {{ editing.milestone.toUpperCase() }} · {{ milestoneLabel(editing) }}
          </h3>
          <button type="button" class="modal-close" @click="closeEditor" :aria-label="t('common.close')">×</button>
        </div>
        <div class="modal-body">
          <!-- 五维评分（1-5 分段按钮） -->
          <div v-for="dim in DIMENSIONS" :key="dim" class="mp-dim-row">
            <span class="mp-dim-label">{{ t('milestone.dimensions.' + dim) }}</span>
            <div class="mp-dim-btns" role="group" :aria-label="t('milestone.dimensions.' + dim)">
              <button
                v-for="n in 5"
                :key="n"
                type="button"
                :class="['mp-dim-btn', { active: editForm[dim] === n }]"
                @click="editForm[dim] = n"
              >{{ n }}</button>
            </div>
          </div>

          <!-- 决策三选一 -->
          <div class="mp-dim-row">
            <span class="mp-dim-label">{{ t('milestone.decision') }}</span>
            <div class="mp-decision-btns" role="group" :aria-label="t('milestone.decision')">
              <button
                v-for="d in ['go', 'no_go', 'pending']"
                :key="d"
                type="button"
                :class="['mp-decision-btn', d, { active: editForm.decision === d }]"
                @click="editForm.decision = d"
              >{{ decisionLabel(d) }}</button>
            </div>
          </div>

          <!-- 决策依据 + 决策人 -->
          <div class="form-group">
            <label class="field-label" for="mp-rationale">{{ t('milestone.rationale') }}</label>
            <textarea id="mp-rationale" v-model="editForm.rationale" rows="3" class="form-input"
              :placeholder="t('milestone.rationalePlaceholder')"></textarea>
          </div>
          <div class="form-group">
            <label class="field-label" for="mp-decided-by">{{ t('milestone.decidedBy') }}</label>
            <input id="mp-decided-by" v-model="editForm.decided_by" type="text" class="form-input"
              :placeholder="t('common.optional')" autocomplete="off">
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn-secondary" :disabled="saving" @click="closeEditor">{{ t('common.cancel') }}</button>
          <button type="button" class="btn-primary" :disabled="saving" @click="saveMilestone">
            {{ saving ? t('common.saving') : t('common.save') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { getMilestones, updateMilestone, updateSalesMode } from '../../api/salesTwin'
import { showToast } from '../../composables/salesTwin/useConfirmToast'

const { t } = useI18n()

const props = defineProps({
  projectId: { type: [Number, String], default: null },
  salesMode: { type: String, default: null },
})

const emit = defineEmits(['sales-mode-changed'])

const MILESTONE_ORDER = ['om10', 'om20', 'om30', 'om40', 'om70']
const SALES_MODES = ['inside_sales', 'prescriptive_pursuit', 'value_solution_selling']
const DIMENSIONS = ['strategic_fit', 'revenue_scale', 'competitive_intensity', 'resource_requirement', 'success_probability']

const milestones = ref([])
const loading = ref(false)
const loadError = ref(false)
const saving = ref(false)
const modeSaving = ref(false)
const editing = ref(null)
const editForm = ref({})

const currentMode = computed(() => props.salesMode || null)

const orderedMilestones = computed(() => {
  const list = milestones.value || []
  return [...list].sort((a, b) => MILESTONE_ORDER.indexOf(a.milestone) - MILESTONE_ORDER.indexOf(b.milestone))
})

function milestoneLabel(m) {
  return m.milestone_label || t(`milestone.labels.${m.milestone}`, m.milestone.toUpperCase())
}

function decisionLabel(decision) {
  return t('milestone.decisions.' + (decision || 'pending'))
}

async function loadMilestones() {
  if (!props.projectId) return
  loading.value = true
  loadError.value = false
  try {
    const res = await getMilestones(props.projectId)
    milestones.value = res.milestones || []
  } catch (e) {
    console.error('加载里程碑失败:', e)
    loadError.value = true
  } finally {
    loading.value = false
  }
}

function openEditor(m) {
  editing.value = m
  editForm.value = {
    decision: m.decision || 'pending',
    strategic_fit: m.strategic_fit ?? null,
    revenue_scale: m.revenue_scale ?? null,
    competitive_intensity: m.competitive_intensity ?? null,
    resource_requirement: m.resource_requirement ?? null,
    success_probability: m.success_probability ?? null,
    rationale: m.rationale || '',
    decided_by: m.decided_by || '',
  }
}

function closeEditor() {
  if (saving.value) return
  editing.value = null
}

async function saveMilestone() {
  if (!editing.value || saving.value) return
  saving.value = true
  try {
    const res = await updateMilestone(props.projectId, editing.value.milestone, { ...editForm.value })
    const updated = res.milestone || res
    const idx = milestones.value.findIndex(x => x.milestone === editing.value.milestone)
    if (idx !== -1) milestones.value[idx] = { ...milestones.value[idx], ...updated }
    editing.value = null
  } catch (e) {
    console.error('保存里程碑失败:', e)
    showToast(t('milestone.saveFailed', { reason: e?.message || e }), 'error')
  } finally {
    saving.value = false
  }
}

async function changeSalesMode(mode) {
  if (modeSaving.value || mode === currentMode.value) return
  modeSaving.value = true
  try {
    await updateSalesMode(props.projectId, mode)
    emit('sales-mode-changed', mode)
  } catch (e) {
    console.error('更新销售模式失败:', e)
    showToast(t('milestone.salesModeFailed', { reason: e?.message || e }), 'error')
  } finally {
    modeSaving.value = false
  }
}

watch(() => props.projectId, (pid) => {
  if (pid) loadMilestones()
}, { immediate: true })
</script>

<style scoped>
.milestone-panel {
  margin-bottom: 16px;
  padding: 12px 16px;
  background: var(--bg-card, #FCFBF5);
  border: 1px solid var(--border, #E8E8E0);
  border-radius: 8px;
}

.mp-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.section-deco {
  color: var(--accent, #CD5036);
  font-size: 14px;
  font-weight: 300;
}

.mp-title {
  font-size: 14px;
  font-weight: 600;
  margin: 0;
  color: var(--text-primary, #15171D);
}

/* ============ 销售模式选项卡 ============ */
.mp-salesmode {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.mp-salesmode-hint {
  font-size: 11px;
  color: var(--accent, #CD5036);
  margin-right: 6px;
}

.mp-mode-tab {
  padding: 4px 10px;
  border: 1px solid rgba(21, 23, 29, 0.12);
  border-radius: 4px;
  background: transparent;
  cursor: pointer;
  font-size: 11px;
  font-family: inherit;
  color: rgba(21, 23, 29, 0.6);
  transition: background 0.15s, border-color 0.15s, color 0.15s;
  white-space: nowrap;
}

.mp-mode-tab:hover:not(:disabled) {
  border-color: var(--accent, #CD5036);
  color: var(--accent, #CD5036);
}

.mp-mode-tab.active {
  background: var(--text-primary, #15171D);
  color: var(--bg-card, #FCFBF5);
  border-color: var(--text-primary, #15171D);
}

.mp-mode-tab:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

/* ============ 状态 ============ */
.mp-state {
  padding: 16px;
  text-align: center;
  color: var(--text-muted, #93959D);
  font-size: 12px;
}

.mp-state-error {
  color: var(--red, #C4391C);
}

.mp-link {
  background: none;
  border: none;
  color: var(--accent, #CD5036);
  cursor: pointer;
  font-size: 12px;
  text-decoration: underline;
  padding: 0 4px;
}

/* ============ 横向里程碑条 ============ */
.mp-track {
  display: flex;
  align-items: stretch;
  gap: 0;
}

.mp-node {
  position: relative;
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  padding: 8px 4px 6px;
  border: none;
  background: transparent;
  cursor: pointer;
  font-family: inherit;
  border-radius: 6px;
  transition: background 0.15s;
}

.mp-node:hover {
  background: rgba(21, 23, 29, 0.03);
}

.mp-node-dot {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  border: 2px solid var(--border-strong, #D7D4CD);
  color: transparent;
  background: var(--bg-card, #FCFBF5);
}

.mp-node.pending .mp-node-dot {
  border-color: var(--border-strong, #D7D4CD);
  background: rgba(21, 23, 29, 0.06);
}

.mp-node.go .mp-node-dot {
  border-color: var(--green, #118A58);
  background: var(--green, #118A58);
  color: #fff;
}

.mp-node.no_go .mp-node-dot {
  border-color: var(--red, #C4391C);
  background: var(--red, #C4391C);
  color: #fff;
}

.mp-node-code {
  font-family: var(--font-mono, 'JetBrains Mono', monospace);
  font-size: 11px;
  font-weight: 700;
  color: var(--text-primary, #15171D);
  letter-spacing: 0.02em;
}

.mp-node-label {
  font-size: 11px;
  color: rgba(21, 23, 29, 0.6);
  line-height: 1.3;
  text-align: center;
}

.mp-node-decision {
  font-size: 10px;
  font-family: var(--font-mono, 'JetBrains Mono', monospace);
  padding: 1px 6px;
  border-radius: 3px;
  background: rgba(21, 23, 29, 0.06);
  color: rgba(21, 23, 29, 0.5);
}

.mp-node.go .mp-node-decision {
  background: var(--green-light, rgba(17, 138, 88, 0.08));
  color: var(--green, #118A58);
}

.mp-node.no_go .mp-node-decision {
  background: var(--red-light, rgba(196, 57, 28, 0.08));
  color: var(--red, #C4391C);
}

/* 节点间连接线 */
.mp-node-line {
  position: absolute;
  top: 19px;
  left: calc(50% + 14px);
  width: calc(100% - 28px);
  height: 2px;
  background: var(--border, #E8E8E0);
}

/* ============ 评估弹窗 ============ */
.mp-modal {
  max-width: 560px;
  width: 92%;
}

.mp-dim-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.mp-dim-label {
  flex-shrink: 0;
  width: 96px;
  font-size: 12px;
  color: rgba(21, 23, 29, 0.6);
}

.mp-dim-btns {
  display: inline-flex;
  gap: 4px;
}

.mp-dim-btn {
  width: 30px;
  height: 26px;
  border: 1px solid rgba(21, 23, 29, 0.15);
  border-radius: 4px;
  background: var(--bg-card, #FCFBF5);
  cursor: pointer;
  font-size: 12px;
  font-family: var(--font-mono, 'JetBrains Mono', monospace);
  color: rgba(21, 23, 29, 0.6);
  transition: background 0.12s, border-color 0.12s, color 0.12s;
}

.mp-dim-btn:hover {
  border-color: var(--accent, #CD5036);
  color: var(--accent, #CD5036);
}

.mp-dim-btn.active {
  background: var(--accent, #CD5036);
  border-color: var(--accent, #CD5036);
  color: #fff;
}

.mp-decision-btns {
  display: inline-flex;
  gap: 6px;
}

.mp-decision-btn {
  padding: 5px 16px;
  border: 1px solid rgba(21, 23, 29, 0.15);
  border-radius: 4px;
  background: var(--bg-card, #FCFBF5);
  cursor: pointer;
  font-size: 12px;
  font-family: inherit;
  font-weight: 600;
  color: rgba(21, 23, 29, 0.6);
  transition: background 0.12s, border-color 0.12s, color 0.12s;
}

.mp-decision-btn.go.active {
  background: var(--green, #118A58);
  border-color: var(--green, #118A58);
  color: #fff;
}

.mp-decision-btn.no_go.active {
  background: var(--red, #C4391C);
  border-color: var(--red, #C4391C);
  color: #fff;
}

.mp-decision-btn.pending.active {
  background: var(--text-primary, #15171D);
  border-color: var(--text-primary, #15171D);
  color: var(--bg-card, #FCFBF5);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 10px;
}

.field-label {
  font-size: 11px;
  color: rgba(21, 23, 29, 0.5);
  font-family: var(--font-mono, 'JetBrains Mono', monospace);
}

.form-input {
  padding: 6px 8px;
  border: 1px solid rgba(21, 23, 29, 0.15);
  border-radius: 2px;
  font-size: 12px;
  font-family: inherit;
  background: var(--bg-card, #FCFBF5);
}

.form-input:focus {
  outline: 2px solid transparent;
  border-color: var(--accent, #CD5036);
}

/* 弹窗基础样式（与现有 modal 风格一致的最小子集） */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(21, 23, 29, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: var(--bg-card, #FCFBF5);
  border-radius: 8px;
  box-shadow: 0 12px 40px rgba(21, 23, 29, 0.18);
  display: flex;
  flex-direction: column;
  max-height: 88vh;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  border-bottom: 1px solid var(--border, #E8E8E0);
}

.modal-title {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary, #15171D);
}

.modal-close {
  background: none;
  border: none;
  font-size: 20px;
  line-height: 1;
  cursor: pointer;
  color: rgba(21, 23, 29, 0.5);
  padding: 2px 6px;
}

.modal-close:hover {
  color: var(--text-primary, #15171D);
}

.modal-body {
  padding: 16px 18px;
  overflow-y: auto;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 12px 18px;
  border-top: 1px solid var(--border, #E8E8E0);
}

.btn-primary {
  background: var(--green, #118A58);
  color: #fff;
  border: 1px solid var(--green, #118A58);
  padding: 7px 16px;
  font-size: 12px;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  border-radius: 6px;
}

.btn-primary:disabled {
  background: #93BFA3;
  border-color: #93BFA3;
  cursor: not-allowed;
}

.btn-secondary {
  background: var(--bg-card, #FCFBF5);
  color: var(--text-secondary, #494A4D);
  border: 1px solid var(--border-strong, #D7D4CD);
  padding: 7px 16px;
  font-size: 12px;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  border-radius: 6px;
}

@media (max-width: 720px) {
  .mp-track {
    flex-wrap: wrap;
  }
  .mp-node {
    flex-basis: 33%;
  }
  .mp-node-line {
    display: none;
  }
}
</style>

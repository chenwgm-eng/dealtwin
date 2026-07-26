<template>
  <div class="ct-panel">
    <!-- Challenger 检查清单条 -->
    <div v-if="checklistItems.length" class="ct-checklist" role="list" :aria-label="t('challenger.checklist')">
      <span class="ct-checklist-title">{{ t('challenger.checklist') }} {{ passedCount }}/5</span>
      <button
        v-for="item in checklistItems"
        :key="item.key"
        type="button"
        role="listitem"
        :class="['ct-check-item', { passed: item.passed }]"
        @click="toggleSuggestion(item)"
      >
        <span class="ct-check-icon" aria-hidden="true">{{ item.passed ? '✓' : '×' }}</span>
        {{ item.label }}
      </button>
    </div>
    <p v-if="activeSuggestion" class="ct-suggestion">{{ activeSuggestion }}</p>

    <div class="ct-split">
      <!-- 左栏：话术列表 -->
      <aside class="ct-list-pane">
        <button type="button" class="ct-generate-btn" :disabled="generating" @click="showGenerateModal = true">
          <span class="ct-plus">+</span> {{ t('challenger.generate') }}
        </button>

        <div v-if="loading" class="ct-state">{{ t('common.loading') }}</div>
        <div v-else-if="loadError" class="ct-state ct-state-error">
          {{ t('challenger.loadFailed') }}
          <button type="button" class="ct-link" @click="loadAll">{{ t('common.retry') }}</button>
        </div>
        <div v-else-if="!teachings.length" class="ct-state">{{ t('challenger.emptyHint') }}</div>

        <div
          v-for="item in teachings"
          :key="item.id"
          :class="['ct-list-item', { selected: selected && selected.id === item.id }]"
          role="button"
          tabindex="0"
          @click="selectTeaching(item)"
          @keydown.enter="selectTeaching(item)"
        >
          <h4 class="ct-list-name">{{ item.name || t('challenger.untitled') }}</h4>
          <div class="ct-list-meta">
            <span v-if="item.stakeholder_name" class="ct-meta-item">▤ {{ item.stakeholder_name }}</span>
            <span v-else class="ct-meta-item">▤ {{ t('challenger.generic') }}</span>
            <span class="ct-meta-item">◷ {{ formatDate(item.created_at) }}</span>
          </div>
        </div>
      </aside>

      <!-- 右栏：话术详情 -->
      <section class="ct-detail-pane">
        <div v-if="!selected" class="ct-state">{{ t('challenger.selectHint') }}</div>

        <template v-else>
          <div class="ct-detail-header">
            <div class="ct-detail-title-row">
              <h3 class="ct-detail-title">{{ selected.name || t('challenger.untitled') }}</h3>
              <div class="ct-detail-actions">
                <button v-if="!editingMode" type="button" class="ct-link" @click="startEdit">{{ t('common.edit') }}</button>
                <button type="button" class="ct-link ct-link-danger" @click="removeTeaching">{{ t('common.delete') }}</button>
              </div>
            </div>
            <div class="ct-list-meta">
              <span class="ct-meta-item">▤ {{ selected.stakeholder_name || t('challenger.generic') }}</span>
              <span class="ct-meta-item">◷ {{ formatDate(selected.created_at) }}</span>
            </div>
          </div>

          <!-- 编辑模式 -->
          <div v-if="editingMode" class="ct-edit-form">
            <div class="ct-form-group">
              <label class="ct-field-label" for="ct-edit-name">{{ t('challenger.nameLabel') }}</label>
              <input id="ct-edit-name" v-model="editForm.name" type="text" class="ct-input" autocomplete="off">
            </div>
            <div v-for="(step, i) in STEPS" :key="step" class="ct-form-group">
              <label class="ct-field-label" :for="'ct-edit-' + step">{{ String(i + 1).padStart(2, '0') }} {{ t('challenger.steps.' + step) }}</label>
              <textarea :id="'ct-edit-' + step" v-model="editForm.content[step]" rows="2" class="ct-input"></textarea>
            </div>
            <div class="ct-form-group">
              <span class="ct-field-label">{{ t('challenger.powerfulAsk') }}</span>
              <div v-for="k in ASK_KEYS" :key="k" class="ct-ask-edit-row">
                <label class="ct-ask-edit-label" :for="'ct-edit-ask-' + k">{{ t('challenger.ask.' + k) }}</label>
                <input :id="'ct-edit-ask-' + k" v-model="editForm.content.powerful_ask[k]" type="text" class="ct-input" autocomplete="off">
              </div>
            </div>
            <div class="ct-form-group">
              <label class="ct-field-label" for="ct-edit-validation">{{ t('challenger.validationFactors') }}</label>
              <textarea id="ct-edit-validation" v-model="editForm.validationText" rows="3" class="ct-input"
                :placeholder="t('challenger.validationPlaceholder')"></textarea>
            </div>
            <div class="ct-form-group">
              <label class="ct-field-label" for="ct-edit-tailoring">{{ t('challenger.tailoringNote') }}</label>
              <textarea id="ct-edit-tailoring" v-model="editForm.content.tailoring_note" rows="2" class="ct-input"></textarea>
            </div>
            <div class="ct-edit-actions">
              <button type="button" class="ct-btn-primary" :disabled="saving" @click="saveEdit">
                {{ saving ? t('common.saving') : t('common.save') }}
              </button>
              <button type="button" class="ct-link" :disabled="saving" @click="editingMode = false">{{ t('common.cancel') }}</button>
            </div>
          </div>

          <!-- 展示模式 -->
          <div v-else class="ct-detail-body">
            <div v-for="(step, i) in STEPS" :key="step" class="ct-step">
              <span class="ct-step-num" aria-hidden="true">{{ String(i + 1).padStart(2, '0') }}</span>
              <div class="ct-step-body">
                <h4 class="ct-step-title">{{ t('challenger.steps.' + step) }}</h4>
                <p class="ct-step-text">{{ selectedContent[step] || '—' }}</p>
              </div>
            </div>

            <!-- 有力的请求 -->
            <div v-if="selectedContent.powerful_ask" class="ct-ask-card">
              <h4 class="ct-block-title">{{ t('challenger.powerfulAsk') }}</h4>
              <div class="ct-ask-grid">
                <div v-for="k in ASK_KEYS" :key="k" class="ct-ask-cell">
                  <span class="ct-ask-label">{{ t('challenger.ask.' + k) }}</span>
                  <p class="ct-ask-value">{{ selectedContent.powerful_ask[k] || '—' }}</p>
                </div>
              </div>
            </div>

            <!-- 认可要素 -->
            <div v-if="validationFactors.length" class="ct-block">
              <h4 class="ct-block-title">{{ t('challenger.validationFactors') }}</h4>
              <ul class="ct-validation-list">
                <li v-for="(v, i) in validationFactors" :key="i">{{ v }}</li>
              </ul>
            </div>

            <!-- 定制沟通建议 -->
            <div v-if="selectedContent.tailoring_note" class="ct-block ct-tailoring">
              <h4 class="ct-block-title">{{ t('challenger.tailoringNote') }}</h4>
              <p class="ct-step-text">{{ selectedContent.tailoring_note }}</p>
            </div>
          </div>
        </template>
      </section>
    </div>

    <!-- 生成弹窗 -->
    <div v-if="showGenerateModal" class="modal-overlay" tabindex="-1" role="dialog" aria-modal="true"
      :aria-label="t('challenger.generate')"
      @click.self="closeGenerateModal" @keydown.esc="closeGenerateModal">
      <div class="modal ct-modal">
        <div class="modal-header">
          <h3 class="modal-title">{{ t('challenger.generate') }}</h3>
          <button type="button" class="modal-close" :disabled="generating" @click="closeGenerateModal" :aria-label="t('common.close')">×</button>
        </div>
        <div class="modal-body">
          <p class="ct-generate-hint">{{ t('challenger.generateHint') }}</p>
          <div class="ct-form-group">
            <label class="ct-field-label" for="ct-gen-stakeholder">{{ t('challenger.targetStakeholder') }}</label>
            <select id="ct-gen-stakeholder" v-model="generateStakeholderId" class="ct-input" :disabled="generating">
              <option :value="null">{{ t('challenger.generic') }}</option>
              <option v-for="s in stakeholders" :key="s.id" :value="s.id">
                {{ s.name }}{{ s.position ? ' - ' + s.position : '' }}
              </option>
            </select>
          </div>
          <p v-if="generating" class="ct-generating-hint">
            <span class="ct-spinner" aria-hidden="true"></span>
            {{ t('challenger.generatingHint') }}
          </p>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn-secondary" :disabled="generating" @click="closeGenerateModal">{{ t('common.cancel') }}</button>
          <button type="button" class="btn-primary" :disabled="generating" @click="generate">
            {{ generating ? t('common.generating') : t('challenger.generate') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  generateChallengerTeaching,
  getChallengerTeachings,
  updateChallengerTeaching,
  deleteChallengerTeaching,
  getChallengerChecklist,
} from '../../api/salesTwin'
import { formatDate } from '../../composables/salesTwin/formatters.js'
import { requestConfirm, showToast } from '../../composables/salesTwin/useConfirmToast'

const { t } = useI18n()

const props = defineProps({
  projectId: { type: [Number, String], default: null },
  stakeholders: { type: Array, default: () => [] },
})

const STEPS = ['warmer', 'reframe', 'rational_drowning', 'emotional_impact', 'new_way', 'our_solution', 'call_to_action']
const ASK_KEYS = ['why', 'when', 'who', 'what']

const teachings = ref([])
const checklistItems = ref([])
const passedCount = ref(0)
const loading = ref(false)
const loadError = ref(false)
const selected = ref(null)
const editingMode = ref(false)
const saving = ref(false)
const editForm = ref({ name: '', content: {}, validationText: '' })
const showGenerateModal = ref(false)
const generateStakeholderId = ref(null)
const generating = ref(false)
const activeSuggestionItem = ref(null)

const activeSuggestion = computed(() => activeSuggestionItem.value?.suggestion || '')

// teaching_content 兼容 JSON 字符串与对象
function parseContent(raw) {
  if (!raw) return {}
  if (typeof raw === 'object') return raw
  try {
    return JSON.parse(raw) || {}
  } catch {
    return {}
  }
}

const selectedContent = computed(() => parseContent(selected.value?.teaching_content))

const validationFactors = computed(() => {
  const v = selectedContent.value.validation_factors
  return Array.isArray(v) ? v : []
})

function toggleSuggestion(item) {
  if (item.passed) {
    activeSuggestionItem.value = null
    return
  }
  activeSuggestionItem.value = activeSuggestionItem.value?.key === item.key ? null : item
}

async function loadAll() {
  if (!props.projectId) return
  loading.value = true
  loadError.value = false
  try {
    const [teachingsRes, checklistRes] = await Promise.all([
      getChallengerTeachings(props.projectId),
      getChallengerChecklist(props.projectId),
    ])
    teachings.value = teachingsRes.teachings || []
    checklistItems.value = checklistRes.items || []
    passedCount.value = checklistRes.passed_count ?? checklistItems.value.filter(i => i.passed).length
    // 保持选中项与最新数据同步
    if (selected.value) {
      const fresh = teachings.value.find(x => x.id === selected.value.id)
      selected.value = fresh || null
      if (!selected.value) editingMode.value = false
    }
  } catch (e) {
    console.error('加载商业指导话术失败:', e)
    loadError.value = true
  } finally {
    loading.value = false
  }
}

function selectTeaching(item) {
  if (saving.value) return
  selected.value = item
  editingMode.value = false
}

function closeGenerateModal() {
  if (generating.value) return
  showGenerateModal.value = false
}

async function generate() {
  if (generating.value || !props.projectId) return
  generating.value = true
  try {
    const res = await generateChallengerTeaching(props.projectId, {
      stakeholderId: generateStakeholderId.value,
    })
    const created = res.teaching || res
    teachings.value.unshift(created)
    selected.value = created
    editingMode.value = false
    showGenerateModal.value = false
    showToast(t('challenger.generateSuccess'), 'success')
    // 生成可能影响检查清单状态，静默刷新
    refreshChecklist()
  } catch (e) {
    console.error('生成商业指导话术失败:', e)
    showToast(t('challenger.generateFailed', { reason: e?.message || e }), 'error')
  } finally {
    generating.value = false
  }
}

async function refreshChecklist() {
  try {
    const res = await getChallengerChecklist(props.projectId)
    checklistItems.value = res.items || []
    passedCount.value = res.passed_count ?? checklistItems.value.filter(i => i.passed).length
  } catch (e) {
    console.warn('刷新检查清单失败:', e)
  }
}

function startEdit() {
  const content = parseContent(selected.value?.teaching_content)
  editForm.value = {
    name: selected.value?.name || '',
    content: {
      ...STEPS.reduce((acc, s) => ({ ...acc, [s]: content[s] || '' }), {}),
      powerful_ask: ASK_KEYS.reduce((acc, k) => ({ ...acc, [k]: content.powerful_ask?.[k] || '' }), {}),
      tailoring_note: content.tailoring_note || '',
    },
    validationText: (Array.isArray(content.validation_factors) ? content.validation_factors : []).join('\n'),
  }
  editingMode.value = true
}

async function saveEdit() {
  if (!selected.value || saving.value) return
  saving.value = true
  try {
    const content = {
      ...editForm.value.content,
      validation_factors: editForm.value.validationText
        .split('\n')
        .map(s => s.trim())
        .filter(Boolean),
    }
    const res = await updateChallengerTeaching(selected.value.id, {
      name: editForm.value.name,
      teaching_content: content,
    })
    const updated = res.teaching || res
    const idx = teachings.value.findIndex(x => x.id === selected.value.id)
    if (idx !== -1) teachings.value[idx] = { ...teachings.value[idx], ...updated }
    selected.value = teachings.value[idx] || { ...selected.value, ...updated }
    editingMode.value = false
    showToast(t('challenger.saveSuccess'), 'success')
  } catch (e) {
    console.error('保存话术失败:', e)
    showToast(t('challenger.saveFailed', { reason: e?.message || e }), 'error')
  } finally {
    saving.value = false
  }
}

async function removeTeaching() {
  if (!selected.value) return
  const ok = await requestConfirm({
    title: t('challenger.deleteTitle'),
    message: t('challenger.deleteConfirm', { name: selected.value.name || t('challenger.untitled') }),
    danger: true,
  })
  if (!ok) return
  try {
    await deleteChallengerTeaching(selected.value.id)
    teachings.value = teachings.value.filter(x => x.id !== selected.value.id)
    selected.value = null
    editingMode.value = false
    showToast(t('challenger.deleteSuccess'), 'success')
  } catch (e) {
    console.error('删除话术失败:', e)
    showToast(t('challenger.deleteFailed', { reason: e?.message || e }), 'error')
  }
}

watch(() => props.projectId, (pid) => {
  selected.value = null
  editingMode.value = false
  if (pid) loadAll()
}, { immediate: true })
</script>

<style scoped>
.ct-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* ============ 检查清单条 ============ */
.ct-checklist {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  padding: 8px 12px;
  background: rgba(21, 23, 29, 0.03);
  border: 1px solid var(--border, #E8E8E0);
  border-radius: 6px;
}

.ct-checklist-title {
  font-size: 11px;
  font-weight: 700;
  font-family: var(--font-mono, 'JetBrains Mono', monospace);
  color: rgba(21, 23, 29, 0.55);
  margin-right: 6px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.ct-check-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 10px;
  border: 1px solid rgba(21, 23, 29, 0.12);
  border-radius: 14px;
  background: var(--bg-card, #FCFBF5);
  cursor: pointer;
  font-size: 11px;
  font-family: inherit;
  color: rgba(21, 23, 29, 0.6);
  transition: border-color 0.15s, color 0.15s;
}

.ct-check-item .ct-check-icon {
  color: var(--text-muted, #93959D);
  font-weight: 700;
}

.ct-check-item.passed {
  border-color: rgba(17, 138, 88, 0.35);
  color: var(--green, #118A58);
}

.ct-check-item.passed .ct-check-icon {
  color: var(--green, #118A58);
}

.ct-check-item:not(.passed):hover {
  border-color: var(--accent, #CD5036);
  color: var(--accent, #CD5036);
}

.ct-suggestion {
  margin: 0;
  font-size: 11px;
  color: rgba(21, 23, 29, 0.7);
  background: rgba(205, 80, 54, 0.06);
  border-left: 2px solid var(--accent, #CD5036);
  padding: 8px 12px;
  border-radius: 0 4px 4px 0;
  line-height: 1.6;
}

/* ============ 左右栏布局 ============ */
.ct-split {
  display: grid;
  grid-template-columns: 300px 1fr;
  gap: 16px;
  min-height: 420px;
}

.ct-list-pane {
  border-right: 1px solid rgba(21, 23, 29, 0.08);
  padding-right: 12px;
  overflow-y: auto;
  max-height: 70vh;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.ct-generate-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 8px;
  border: 1px dashed rgba(21, 23, 29, 0.25);
  border-radius: 6px;
  background: transparent;
  cursor: pointer;
  font-size: 12px;
  font-family: inherit;
  font-weight: 600;
  color: var(--accent, #CD5036);
  transition: border-color 0.15s, background 0.15s;
}

.ct-generate-btn:hover:not(:disabled) {
  border-color: var(--accent, #CD5036);
  background: rgba(205, 80, 54, 0.05);
}

.ct-generate-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.ct-plus {
  font-size: 14px;
  line-height: 1;
}

.ct-list-item {
  padding: 10px 12px;
  border: 1px solid rgba(21, 23, 29, 0.08);
  border-radius: 4px;
  background: var(--bg-card, #FCFBF5);
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}

.ct-list-item:hover {
  border-color: rgba(21, 23, 29, 0.2);
}

.ct-list-item.selected {
  border-color: var(--accent, #CD5036);
  background: rgba(205, 80, 54, 0.05);
}

.ct-list-name {
  font-size: 13px;
  font-weight: 600;
  margin: 0 0 4px;
  color: var(--text-primary, #15171D);
  line-height: 1.4;
}

.ct-list-meta {
  display: flex;
  gap: 10px;
  font-size: 11px;
  color: rgba(21, 23, 29, 0.5);
  font-family: var(--font-mono, 'JetBrains Mono', monospace);
}

.ct-meta-item {
  white-space: nowrap;
}

.ct-state {
  padding: 20px 8px;
  text-align: center;
  color: var(--text-muted, #93959D);
  font-size: 12px;
  line-height: 1.6;
}

.ct-state-error {
  color: var(--red, #C4391C);
}

.ct-link {
  background: none;
  border: none;
  color: rgba(21, 23, 29, 0.6);
  cursor: pointer;
  font-size: 11px;
  padding: 4px 8px;
  text-decoration: underline;
  font-family: inherit;
}

.ct-link:hover {
  color: var(--accent, #CD5036);
}

.ct-link-danger {
  color: var(--red, #C4391C);
}

/* ============ 右栏详情 ============ */
.ct-detail-pane {
  padding-left: 12px;
  overflow-y: auto;
  max-height: 70vh;
}

.ct-detail-header {
  border-bottom: 1px solid rgba(21, 23, 29, 0.08);
  padding-bottom: 10px;
  margin-bottom: 14px;
}

.ct-detail-title-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 6px;
}

.ct-detail-title {
  font-size: 16px;
  font-weight: 600;
  margin: 0;
  flex: 1;
  color: var(--text-primary, #15171D);
}

.ct-detail-actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}

.ct-detail-body {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

/* 七步话术 */
.ct-step {
  display: flex;
  gap: 12px;
  padding: 10px 12px;
  border: 1px solid var(--border, #E8E8E0);
  border-radius: 6px;
  background: var(--bg-card, #FCFBF5);
}

.ct-step-num {
  flex-shrink: 0;
  font-family: var(--font-mono, 'JetBrains Mono', monospace);
  font-size: 15px;
  font-weight: 700;
  color: var(--accent, #CD5036);
  line-height: 1.4;
}

.ct-step-body {
  flex: 1;
  min-width: 0;
}

.ct-step-title {
  margin: 0 0 4px;
  font-size: 12px;
  font-weight: 700;
  color: var(--text-primary, #15171D);
}

.ct-step-text {
  margin: 0;
  font-size: 12px;
  color: rgba(21, 23, 29, 0.75);
  line-height: 1.65;
  white-space: pre-wrap;
}

/* 有力的请求 */
.ct-ask-card {
  padding: 12px;
  border: 1px solid rgba(205, 80, 54, 0.25);
  border-left: 3px solid var(--accent, #CD5036);
  border-radius: 0 6px 6px 0;
  background: rgba(205, 80, 54, 0.04);
}

.ct-block-title {
  margin: 0 0 8px;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--accent, #CD5036);
  font-family: var(--font-mono, 'JetBrains Mono', monospace);
}

.ct-ask-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.ct-ask-cell {
  padding: 8px;
  background: var(--bg-card, #FCFBF5);
  border: 1px solid rgba(21, 23, 29, 0.06);
  border-radius: 4px;
}

.ct-ask-label {
  display: block;
  font-size: 10px;
  font-weight: 700;
  color: rgba(21, 23, 29, 0.45);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: 3px;
}

.ct-ask-value {
  margin: 0;
  font-size: 12px;
  color: rgba(21, 23, 29, 0.78);
  line-height: 1.5;
}

/* 认可要素 / 定制建议 */
.ct-block {
  padding: 12px;
  border-left: 3px solid var(--border-strong, #D7D4CD);
  background: rgba(21, 23, 29, 0.02);
  border-radius: 0 6px 6px 0;
}

.ct-block .ct-block-title {
  color: rgba(21, 23, 29, 0.55);
}

.ct-validation-list {
  margin: 0;
  padding-left: 18px;
}

.ct-validation-list li {
  font-size: 12px;
  color: rgba(21, 23, 29, 0.75);
  line-height: 1.7;
}

.ct-tailoring {
  border-left-color: var(--accent, #CD5036);
}

/* ============ 编辑表单 ============ */
.ct-edit-form {
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: rgba(21, 23, 29, 0.02);
  padding: 14px;
  border-radius: 6px;
}

.ct-form-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.ct-field-label {
  font-size: 11px;
  color: rgba(21, 23, 29, 0.5);
  font-family: var(--font-mono, 'JetBrains Mono', monospace);
}

.ct-input {
  padding: 6px 8px;
  border: 1px solid rgba(21, 23, 29, 0.15);
  border-radius: 2px;
  font-size: 12px;
  font-family: inherit;
  background: var(--bg-card, #FCFBF5);
}

.ct-input:focus {
  outline: 2px solid transparent;
  border-color: var(--accent, #CD5036);
}

.ct-ask-edit-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.ct-ask-edit-label {
  flex-shrink: 0;
  width: 72px;
  font-size: 11px;
  color: rgba(21, 23, 29, 0.55);
}

.ct-ask-edit-row .ct-input {
  flex: 1;
}

.ct-edit-actions {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-top: 4px;
}

.ct-btn-primary {
  background: var(--green, #118A58);
  color: #fff;
  border: 1px solid var(--green, #118A58);
  padding: 6px 14px;
  font-size: 12px;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  border-radius: 6px;
}

.ct-btn-primary:disabled {
  background: #93BFA3;
  border-color: #93BFA3;
  cursor: not-allowed;
}

/* ============ 生成弹窗 ============ */
.ct-modal {
  max-width: 440px;
  width: 92%;
}

.ct-generate-hint {
  margin: 0 0 12px;
  font-size: 12px;
  color: rgba(21, 23, 29, 0.62);
  background: rgba(205, 80, 54, 0.06);
  border-left: 2px solid var(--accent, #CD5036);
  padding: 8px 12px;
  border-radius: 0 4px 4px 0;
  line-height: 1.6;
}

.ct-generating-hint {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 12px 0 0;
  font-size: 12px;
  color: var(--accent, #CD5036);
  font-weight: 500;
}

.ct-spinner {
  display: inline-block;
  width: 13px;
  height: 13px;
  border: 2px solid currentColor;
  border-top-color: transparent;
  border-radius: 50%;
  animation: ct-spin 0.7s linear infinite;
}

@keyframes ct-spin {
  to { transform: rotate(360deg); }
}

@media (prefers-reduced-motion: reduce) {
  .ct-spinner { animation: none; }
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

.modal-close:hover:not(:disabled) {
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

@media (max-width: 1024px) {
  .ct-split {
    grid-template-columns: 1fr;
  }
  .ct-list-pane {
    border-right: none;
    border-bottom: 1px solid rgba(21, 23, 29, 0.08);
    padding-right: 0;
    padding-bottom: 12px;
    max-height: 280px;
  }
  .ct-detail-pane {
    padding-left: 0;
    max-height: none;
  }
  .ct-ask-grid {
    grid-template-columns: 1fr;
  }
}
</style>

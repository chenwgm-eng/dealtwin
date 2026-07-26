<template>
  <section class="info-field-tabs-section" aria-labelledby="biz-field-title">
    <!-- Section header：装饰符 + 标题 + 右侧动态 AI 生成按钮 -->
    <div class="section-header">
      <span class="section-deco" aria-hidden="true">◇</span>
      <h3 id="biz-field-title" class="section-title">{{ t('insight.title') }}</h3>

      <!-- Tab 1-3 激活时：AI 生成 3-3-3 -->
      <button
        v-if="isStrategyTab"
        type="button"
        class="ai-generate-btn"
        :disabled="aiGeneratingStrategy || loadingStrategy"
        @click="handleAIGenerateStrategy"
        :title="aiGeneratingStrategy ? t('common.generating') : t('insight.aiGenerateStrategyTooltip')"
      >
        <span class="ai-generate-icon" :class="{ spinning: aiGeneratingStrategy }" aria-hidden="true">✦</span>
        <span>{{ aiGeneratingStrategy ? t('insight.aiGenerating') : t('insight.aiDeepAnalysis') }}</span>
      </button>

      <!-- Tab 4 激活时：AI 生成 WHY -->
      <button
        v-else-if="activeTab === 'why'"
        type="button"
        class="ai-generate-btn"
        :disabled="aiGeneratingWhy || loadingWhy"
        @click="handleAIGenerateWhy"
        :title="aiGeneratingWhy ? t('common.generating') : t('insight.aiGenerateWhyTooltip')"
      >
        <span class="ai-generate-icon" :class="{ spinning: aiGeneratingWhy }" aria-hidden="true">✦</span>
        <span>{{ aiGeneratingWhy ? t('insight.aiGenerating') : t('insight.aiGenerate') }}</span>
      </button>

      <!-- Tab 5 激活时：AI 生成竞争分析 -->
      <button
        v-else-if="activeTab === 'competitive_analysis'"
        type="button"
        class="ai-generate-btn"
        :disabled="competitiveGenerating"
        @click="handleGenerateCompetitive"
        :title="competitiveGenerating ? t('common.generating') : t('insight.aiGenerateCompetitiveTooltip')"
      >
        <span class="ai-generate-icon" :class="{ spinning: competitiveGenerating }" aria-hidden="true">✦</span>
        <span>{{ competitiveGenerating ? t('insight.aiGenerating') : t('insight.aiGenerate') }}</span>
      </button>
    </div>

    <!-- Tab 列表 -->
    <div class="info-field-tabs" role="tablist" :aria-label="t('insight.ariaLabel')">
      <button type="button" role="tab" class="info-field-tab" :class="{active: activeTab==='industry_trend'}" :aria-selected="activeTab==='industry_trend'" aria-controls="biz-tab-industry" @click="activeTab='industry_trend'">{{ t('insight.tabs.industryTrend') }}</button>
      <button type="button" role="tab" class="info-field-tab" :class="{active: activeTab==='pain_point'}" :aria-selected="activeTab==='pain_point'" aria-controls="biz-tab-pain" @click="activeTab='pain_point'">{{ t('insight.tabs.painPoints') }}</button>
      <button type="button" role="tab" class="info-field-tab" :class="{active: activeTab==='current_measure'}" :aria-selected="activeTab==='current_measure'" aria-controls="biz-tab-measure" @click="activeTab='current_measure'">{{ t('insight.tabs.currentMeasures') }}</button>
      <button type="button" role="tab" class="info-field-tab" :class="{active: activeTab==='why'}" :aria-selected="activeTab==='why'" aria-controls="biz-tab-why" @click="activeTab='why'">{{ t('insight.tabs.valueProposition') }}</button>
      <button type="button" role="tab" class="info-field-tab" :class="{active: activeTab==='competitive_analysis'}" :aria-selected="activeTab==='competitive_analysis'" aria-controls="biz-tab-comp" @click="activeTab='competitive_analysis'">{{ t('insight.tabs.competitiveAnalysis') }}</button>
    </div>

    <!-- Tab body -->
    <div class="info-field-tab-body">
      <!-- Tab 1-3：战略项（行业趋势 / 痛点 / 当前措施） -->
      <div
        v-for="group in strategyGroups"
        :key="group.type"
        v-show="activeTab === group.type"
        :id="`biz-tab-${group.idSuffix}`"
        class="tab-panel"
        role="tabpanel"
      >
        <div v-if="loadingStrategy && !hasAnyStrategyData" class="strategy-skeleton">
          <div class="skel-line"></div>
          <div class="skel-block"></div>
          <div class="skel-line w70"></div>
          <div class="skel-block"></div>
        </div>
        <div v-else class="strategy-groups">
          <div class="strategy-group">
            <div class="group-header">
              <span class="group-title">{{ group.title }}</span>
              <span class="group-count">{{ itemsByType[group.type].length }}/3</span>
              <button
                type="button"
                class="add-btn"
                :disabled="itemsByType[group.type].length >= 3 || aiGeneratingStrategy"
                :title="itemsByType[group.type].length >= 3 ? t('insight.maxItemsPerType') : `${t('common.add')}${group.title}`"
                @click="openAddModal(group.type)"
              >
                <span aria-hidden="true">+</span>
              </button>
            </div>
            <div v-if="itemsByType[group.type].length === 0" class="group-empty">
              {{ t('insight.clickToAdd') }}
            </div>
            <div v-else class="group-items">
              <div
                v-for="item in itemsByType[group.type]"
                :key="item.id"
                class="strategy-card"
              >
                <div class="card-head">
                  <span class="card-name" :title="item.name">{{ item.name }}</span>
                  <div class="card-actions">
                    <button
                      type="button"
                      class="card-action-btn edit-btn"
                      :disabled="aiGeneratingStrategy"
                      @click="openEditModal(item)"
                    >{{ t('common.edit') }}</button>
                    <button
                      type="button"
                      class="card-action-btn delete-btn"
                      :disabled="aiGeneratingStrategy"
                      @click="handleDeleteStrategy(item)"
                    >{{ t('common.delete') }}</button>
                  </div>
                </div>
                <p v-if="item.description" class="card-desc">{{ item.description }}</p>
                <div v-if="showMetaRow(item)" class="card-meta">
                  <span class="meta-label">{{ getMetaLabel(item) }}</span>
                  <span class="meta-value" :class="getMetaClass(item)">{{ getMetaValue(item) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Tab 4：价值主张（三个WHY） -->
      <div v-show="activeTab === 'why'" id="biz-tab-why" class="tab-panel" role="tabpanel">
        <div v-if="loadingWhy && !hasAnyWhyData" class="strategy-skeleton">
          <div class="skel-line"></div>
          <div class="skel-block"></div>
          <div class="skel-line w70"></div>
          <div class="skel-block"></div>
        </div>
        <div v-else class="why-groups">
          <div v-for="group in whyGroups" :key="group.type" class="why-group">
            <div class="group-header">
              <span class="group-title">{{ group.title }}</span>
              <div class="group-actions">
                <template v-if="contextByType[group.type]">
                  <button
                    type="button"
                    class="card-action-btn edit-btn"
                    :disabled="aiGeneratingWhy"
                    @click="openEditWhyModal(group.type)"
                  >{{ t('common.edit') }}</button>
                  <button
                    type="button"
                    class="card-action-btn delete-btn"
                    :disabled="aiGeneratingWhy"
                    @click="handleDeleteWhy(group.type)"
                  >{{ t('common.delete') }}</button>
                </template>
                <button
                  v-else
                  type="button"
                  class="add-btn"
                  :disabled="aiGeneratingWhy"
                  @click="openAddWhyModal(group.type)"
                >{{ t('insight.clickToAdd') }}</button>
              </div>
            </div>
            <div v-if="contextByType[group.type]" class="why-card">
              <p class="card-text">{{ contextByType[group.type].context_text }}</p>
              <p v-if="contextByType[group.type].rationale" class="card-rationale">
                <span class="rationale-label">{{ t('insight.rationale') }}</span>{{ contextByType[group.type].rationale }}
              </p>
            </div>
            <div v-else class="group-empty">
              {{ t('insight.noContent') }}
            </div>
          </div>
        </div>
      </div>

      <!-- Tab 5：竞争分析（textarea 内联编辑） -->
      <div v-show="activeTab === 'competitive_analysis'" id="biz-tab-comp" class="tab-panel info-row-block" role="tabpanel">
        <p v-if="competitiveError" class="ai-generate-error" role="alert">{{ competitiveError }}</p>
        <textarea
          v-if="editing.field === 'competitive_analysis'"
          v-focus v-model="editing.value"
          class="inline-edit-textarea"
          rows="4"
          @blur="saveEditCompetitive"
          @keydown.ctrl.enter.prevent="saveEditCompetitive"
          @keydown.esc.prevent="cancelEditCompetitive"
          :disabled="editing.saving"
        ></textarea>
        <span v-else
          class="info-value info-value-text formatted-text info-value-editable"
          @dblclick="startEditCompetitive"
          :title="t('insight.dblclickToEdit')"
          tabindex="0"
          role="button"
          @keydown.enter="startEditCompetitive"
          v-html="formatStructuredText(currentProject?.competitive_analysis, t('insight.competitiveEmptyHint'))"
        ></span>
      </div>
    </div>

    <!-- Strategy Modal（Tab 1-3 共用） -->
    <div
      v-if="strategyModal.visible"
      class="modal-overlay"
      tabindex="-1"
      role="dialog"
      aria-modal="true"
      :aria-label="strategyModalTitle"
      @click.self="closeStrategyModal"
      @keydown.esc="closeStrategyModal"
    >
      <div class="modal">
        <div class="modal-header">
          <h3 class="modal-title">{{ strategyModalTitle }}</h3>
          <button type="button" class="modal-close" @click="closeStrategyModal" :aria-label="t('common.close')">×</button>
        </div>
        <div class="modal-body">
          <div class="form-row">
            <label class="form-label">{{ t('insight.itemName') }} <span class="required">*</span></label>
            <input
              ref="strategyNameInputRef"
              v-model="strategyModal.form.name"
              type="text"
              class="form-input"
              :placeholder="t('insight.itemNamePlaceholder')"
              maxlength="50"
            >
          </div>
          <div class="form-row">
            <label class="form-label">{{ t('insight.itemDescription') }}</label>
            <textarea
              v-model="strategyModal.form.description"
              class="form-textarea"
              rows="3"
              :placeholder="t('insight.itemDescriptionPlaceholder')"
              maxlength="500"
            ></textarea>
          </div>
          <!-- metadata 字段：按 item_type 动态显示 -->
          <div v-if="strategyModal.itemType === 'industry_trend'" class="form-row">
            <label class="form-label">{{ t('insight.impactArea') }}</label>
            <input
              v-model="strategyModal.form.metadata.impact_area"
              type="text"
              class="form-input"
              :placeholder="t('insight.impactAreaPlaceholder')"
              maxlength="50"
            >
          </div>
          <div v-else-if="strategyModal.itemType === 'pain_point'" class="form-row">
            <label class="form-label">{{ t('insight.severity') }}</label>
            <select v-model="strategyModal.form.metadata.severity" class="form-input">
              <option value="high">{{ t('insight.severityHigh') }}</option>
              <option value="medium">{{ t('insight.severityMedium') }}</option>
              <option value="low">{{ t('insight.severityLow') }}</option>
            </select>
          </div>
          <div v-else-if="strategyModal.itemType === 'current_measure'" class="form-row">
            <label class="form-label">{{ t('insight.effectiveness') }}</label>
            <select v-model="strategyModal.form.metadata.effectiveness" class="form-input">
              <option value="high">{{ t('insight.severityHigh') }}</option>
              <option value="medium">{{ t('insight.severityMedium') }}</option>
              <option value="low">{{ t('insight.severityLow') }}</option>
              <option value="none">{{ t('insight.effectivenessNone') }}</option>
            </select>
          </div>
          <p v-if="strategyModal.error" class="form-error" role="alert">{{ strategyModal.error }}</p>
        </div>
        <div class="modal-footer">
          <button
            type="button"
            class="btn-secondary"
            :disabled="strategyModal.saving"
            @click="closeStrategyModal"
          >{{ t('common.cancel') }}</button>
          <button
            type="button"
            class="btn-primary"
            :disabled="!canSaveStrategy || strategyModal.saving"
            @click="handleSaveStrategy"
          >
            <span v-if="strategyModal.saving" class="btn-spinner" aria-hidden="true"></span>
            {{ strategyModal.saving ? t('common.saving') : t('common.save') }}
          </button>
        </div>
      </div>
    </div>

    <!-- Why Modal（Tab 4） -->
    <div
      v-if="whyModal.visible"
      class="modal-overlay"
      tabindex="-1"
      role="dialog"
      aria-modal="true"
      :aria-label="whyModalTitle"
      @click.self="closeWhyModal"
      @keydown.esc="closeWhyModal"
    >
      <div class="modal">
        <div class="modal-header">
          <h3 class="modal-title">{{ whyModalTitle }}</h3>
          <button type="button" class="modal-close" @click="closeWhyModal" :aria-label="t('common.close')">×</button>
        </div>
        <div class="modal-body">
          <div class="form-row">
            <label class="form-label">{{ t('insight.contextText') }} <span class="required">*</span></label>
            <textarea
              ref="whyContextInputRef"
              v-model="whyModal.form.context_text"
              class="form-textarea"
              rows="5"
              :placeholder="t('insight.contextTextPlaceholder')"
              maxlength="1000"
            ></textarea>
          </div>
          <div class="form-row">
            <label class="form-label">{{ t('insight.rationaleLabel') }}</label>
            <textarea
              v-model="whyModal.form.rationale"
              class="form-textarea"
              rows="3"
              :placeholder="t('insight.rationalePlaceholder')"
              maxlength="500"
            ></textarea>
          </div>
          <p v-if="whyModal.error" class="form-error" role="alert">{{ whyModal.error }}</p>
        </div>
        <div class="modal-footer">
          <button
            type="button"
            class="btn-secondary"
            :disabled="whyModal.saving"
            @click="closeWhyModal"
          >{{ t('common.cancel') }}</button>
          <button
            type="button"
            class="btn-primary"
            :disabled="!canSaveWhy || whyModal.saving"
            @click="handleSaveWhy"
          >
            <span v-if="whyModal.saving" class="btn-spinner" aria-hidden="true"></span>
            {{ whyModal.saving ? t('common.saving') : t('common.save') }}
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  getStrategyItems,
  createStrategyItem,
  updateStrategyItem,
  deleteStrategyItem,
  aiGenerateStrategyItems,
  getWhyContexts,
  upsertWhyContext,
  deleteWhyContext,
  aiGenerateWhyContexts,
  generateCompetitiveAnalysis,
} from '../../api/salesTwin.js'
import { requestConfirm, showToast } from '../../composables/salesTwin/useConfirmToast'
import { formatStructuredText as defaultFormatStructuredText } from '../../composables/salesTwin/formatters.js'

const { t } = useI18n()

const props = defineProps({
  currentProject: { type: Object, default: () => ({}) },
  formatStructuredText: { type: Function, default: defaultFormatStructuredText },
})

const emit = defineEmits(['update-project', 'refresh-project'])

// v-focus 指令：渲染时自动聚焦（用于 Tab 5 textarea）
const vFocus = {
  mounted: (el) => {
    if (typeof el.focus === 'function') el.focus()
    if (el && typeof el.select === 'function' && el.tagName === 'INPUT') el.select()
  }
}

// ============ Tab 状态 ============
// 5 个 Tab：industry_trend / pain_point / current_measure / why / competitive_analysis
const STRATEGY_TAB_TYPES = ['industry_trend', 'pain_point', 'current_measure']
const activeTab = ref('industry_trend') // 默认激活 Tab 1（行业趋势）

const isStrategyTab = computed(() => STRATEGY_TAB_TYPES.includes(activeTab.value))

// Tab 1-3 分组配置
const strategyGroups = computed(() => [
  { type: 'industry_trend', title: t('insight.tabs.industryTrend'), idSuffix: 'industry' },
  { type: 'pain_point', title: t('insight.tabs.painPoints'), idSuffix: 'pain' },
  { type: 'current_measure', title: t('insight.tabs.currentMeasures'), idSuffix: 'measure' },
])

// Tab 4 分组配置
const whyGroups = computed(() => [
  { type: 'why', title: t('insight.whyChange') },
  { type: 'why_now', title: t('insight.whyNow') },
  { type: 'why_us', title: t('insight.whyUs') },
])

// ============ Tab 1-3：战略项状态 ============
const loadingStrategy = ref(false)
const aiGeneratingStrategy = ref(false)
let strategyLoadId = 0  // 防止快速切换项目时旧请求覆盖新数据
const itemsByType = reactive({
  industry_trend: [],
  pain_point: [],
  current_measure: [],
})

const hasAnyStrategyData = computed(() =>
  itemsByType.industry_trend.length > 0 ||
  itemsByType.pain_point.length > 0 ||
  itemsByType.current_measure.length > 0
)

const strategyModal = reactive({
  visible: false,
  mode: 'add', // 'add' | 'edit'
  itemType: 'industry_trend',
  editingId: null,
  saving: false,
  error: '',
  form: { name: '', description: '', metadata: {} },
})

const strategyNameInputRef = ref(null)

const strategyModalTitle = computed(() => {
  const title = strategyGroups.value.find(g => g.type === strategyModal.itemType)?.title || ''
  return strategyModal.mode === 'add' ? `${t('common.add')}${title}` : `${t('common.edit')}${title}`
})

const canSaveStrategy = computed(() => (strategyModal.form.name || '').trim().length > 0)

// ============ Tab 4：三个WHY 状态 ============
const loadingWhy = ref(false)
const aiGeneratingWhy = ref(false)
let whyLoadId = 0  // 防止快速切换项目时旧请求覆盖新数据
const contextByType = reactive({
  why: null,
  why_now: null,
  why_us: null,
})

const hasAnyWhyData = computed(() =>
  !!contextByType.why || !!contextByType.why_now || !!contextByType.why_us
)

const whyModal = reactive({
  visible: false,
  mode: 'add', // 'add' | 'edit'
  contextType: 'why',
  saving: false,
  error: '',
  form: { context_text: '', rationale: '' },
})

const whyContextInputRef = ref(null)

const whyModalTitle = computed(() => {
  const title = whyGroups.value.find(g => g.type === whyModal.contextType)?.title || ''
  return whyModal.mode === 'add' ? `${t('common.add')}${title}` : `${t('common.edit')}${title}`
})

const canSaveWhy = computed(() => (whyModal.form.context_text || '').trim().length > 0)

// ============ Tab 5：竞争分析状态 ============
const competitiveGenerating = ref(false)
const competitiveError = ref('')
const editing = reactive({ field: null, value: '', saving: false })

// ============ 数据加载 ============
async function loadStrategyItems() {
  const projectId = props.currentProject?.id
  if (!projectId) return
  const reqId = ++strategyLoadId
  loadingStrategy.value = true
  try {
    const res = await getStrategyItems(projectId)
    if (reqId !== strategyLoadId) return  // 旧请求，丢弃
    const grouped = res.strategy_items || {}
    itemsByType.industry_trend = grouped.industry_trend || []
    itemsByType.pain_point = grouped.pain_point || []
    itemsByType.current_measure = grouped.current_measure || []
  } catch (err) {
    if (reqId !== strategyLoadId) return  // 旧请求，丢弃
    // 404 表示项目不存在（可能已被删除），静默重置数据不弹 toast
    if (err?.response?.status === 404) {
      itemsByType.industry_trend = []
      itemsByType.pain_point = []
      itemsByType.current_measure = []
      return
    }
    const msg = err?.response?.data?.error || err?.message || t('toast.loadFailed')
    showToast(`${t('insight.loadStrategyFailed')}：${msg}`, 'error')
  } finally {
    if (reqId === strategyLoadId) loadingStrategy.value = false
  }
}

async function loadWhyContexts() {
  const projectId = props.currentProject?.id
  if (!projectId) return
  const reqId = ++whyLoadId
  loadingWhy.value = true
  try {
    const res = await getWhyContexts(projectId)
    if (reqId !== whyLoadId) return  // 旧请求，丢弃
    const grouped = res.why_contexts || {}
    contextByType.why = grouped.why || null
    contextByType.why_now = grouped.why_now || null
    contextByType.why_us = grouped.why_us || null
  } catch (err) {
    if (reqId !== whyLoadId) return  // 旧请求，丢弃
    // 404 表示项目不存在（可能已被删除），静默重置数据不弹 toast
    if (err?.response?.status === 404) {
      contextByType.why = null
      contextByType.why_now = null
      contextByType.why_us = null
      return
    }
    const msg = err?.response?.data?.error || err?.message || t('toast.loadFailed')
    showToast(`${t('insight.loadWhyFailed')}：${msg}`, 'error')
  } finally {
    if (reqId === whyLoadId) loadingWhy.value = false
  }
}

// 项目切换时自动加载
watch(() => props.currentProject?.id, (newId) => {
  if (newId) {
    loadStrategyItems()
    loadWhyContexts()
  }
})

onMounted(() => {
  if (props.currentProject?.id) {
    loadStrategyItems()
    loadWhyContexts()
  }
})

// ============ Strategy Modal 操作 ============
function initMetadata(itemType) {
  if (itemType === 'industry_trend') return { impact_area: '' }
  if (itemType === 'pain_point') return { severity: 'medium' }
  if (itemType === 'current_measure') return { effectiveness: 'medium' }
  return {}
}

function openAddModal(itemType) {
  if (itemsByType[itemType].length >= 3) return
  strategyModal.mode = 'add'
  strategyModal.itemType = itemType
  strategyModal.editingId = null
  strategyModal.error = ''
  strategyModal.form = {
    name: '',
    description: '',
    metadata: initMetadata(itemType),
  }
  strategyModal.visible = true
  nextTick(() => strategyNameInputRef.value?.focus())
}

function openEditModal(item) {
  strategyModal.mode = 'edit'
  strategyModal.itemType = item.item_type
  strategyModal.editingId = item.id
  strategyModal.error = ''
  strategyModal.form = {
    name: item.name || '',
    description: item.description || '',
    metadata: { ...(item.metadata || initMetadata(item.item_type)) },
  }
  strategyModal.visible = true
  nextTick(() => strategyNameInputRef.value?.focus())
}

function closeStrategyModal() {
  if (strategyModal.saving) return
  strategyModal.visible = false
  strategyModal.error = ''
}

// 清理 metadata：industry_trend 无值返回 null
function cleanMetadata(metadata, itemType) {
  if (itemType === 'industry_trend') {
    const v = (metadata?.impact_area || '').trim()
    return v ? { impact_area: v } : null
  }
  if (itemType === 'pain_point') {
    return { severity: metadata?.severity || 'medium' }
  }
  if (itemType === 'current_measure') {
    return { effectiveness: metadata?.effectiveness || 'medium' }
  }
  return null
}

async function handleSaveStrategy() {
  const projectId = props.currentProject?.id
  if (!projectId) return
  const name = (strategyModal.form.name || '').trim()
  if (!name) {
    strategyModal.error = t('insight.nameRequired')
    return
  }
  strategyModal.saving = true
  strategyModal.error = ''
  try {
    const payload = {
      item_type: strategyModal.itemType,
      name,
      description: strategyModal.form.description?.trim() || null,
      metadata: cleanMetadata(strategyModal.form.metadata, strategyModal.itemType),
    }
    if (strategyModal.mode === 'add') {
      await createStrategyItem(projectId, payload)
      showToast(t('toast.createSuccess'), 'success')
    } else {
      await updateStrategyItem(projectId, strategyModal.editingId, {
        name: payload.name,
        description: payload.description,
        metadata: payload.metadata,
      })
      showToast(t('toast.saveSuccess'), 'success')
    }
    strategyModal.visible = false
    await loadStrategyItems()
  } catch (err) {
    const msg = err?.response?.data?.error || err?.message || t('toast.saveFailed')
    strategyModal.error = `${t('toast.saveFailed')}：${msg}`
  } finally {
    strategyModal.saving = false
  }
}

async function handleDeleteStrategy(item) {
  const projectId = props.currentProject?.id
  if (!projectId || !item?.id) return
  const confirmed = await requestConfirm({
    title: t('insight.deleteStrategyTitle'),
    message: t('insight.deleteStrategyConfirm', { name: item.name }),
    confirmText: t('common.delete'),
    danger: true,
  })
  if (!confirmed) return
  try {
    await deleteStrategyItem(projectId, item.id)
    showToast(t('toast.deleteSuccess'), 'success')
    await loadStrategyItems()
  } catch (err) {
    const msg = err?.response?.data?.error || err?.message || t('toast.deleteFailed')
    showToast(`${t('toast.deleteFailed')}：${msg}`, 'error')
  }
}

// ============ Strategy AI 生成（覆盖式刷新 3 个 Tab） ============
async function handleAIGenerateStrategy() {
  const projectId = props.currentProject?.id
  if (!projectId) return
  const confirmed = await requestConfirm({
    title: t('insight.aiGenerateStrategyTitle'),
    message: t('insight.aiGenerateStrategyConfirm'),
    confirmText: t('common.confirm'),
    danger: true,
  })
  if (!confirmed) return
  aiGeneratingStrategy.value = true
  try {
    const res = await aiGenerateStrategyItems(projectId)
    const draft = res.draft || {}

    // 1. 先删除所有现有战略项（3 类 × 3 条 = 9 条）
    const allItems = [
      ...itemsByType.industry_trend,
      ...itemsByType.pain_point,
      ...itemsByType.current_measure,
    ]
    for (const it of allItems) {
      await deleteStrategyItem(projectId, it.id)
    }

    // 2. 逐条创建新战略项（顺序执行，避免触发每类 3 条上限校验）
    const creations = [
      ...mapDraftToPayload(draft.industry_trends, 'industry_trend'),
      ...mapDraftToPayload(draft.pain_points, 'pain_point'),
      ...mapDraftToPayload(draft.current_measures, 'current_measure'),
    ]
    for (const payload of creations) {
      await createStrategyItem(projectId, payload)
    }

    showToast(t('insight.aiGenerateSuccess'), 'success')
    await loadStrategyItems()
  } catch (err) {
    const msg = err?.response?.data?.error || err?.message || t('insight.aiGenerateFailed')
    showToast(`${t('insight.aiGenerateFailed')}：${msg}`, 'error')
  } finally {
    aiGeneratingStrategy.value = false
  }
}

// 将 AI 草稿条目映射为 createStrategyItem 请求体
function mapDraftToPayload(drafts, itemType) {
  if (!Array.isArray(drafts)) return []
  return drafts.map(d => {
    const name = (d.name || '').trim()
    if (!name) return null
    const description = (d.description || '').trim() || null
    let metadata = null
    if (itemType === 'industry_trend' && d.impact_area) {
      metadata = { impact_area: String(d.impact_area) }
    } else if (itemType === 'pain_point') {
      metadata = { severity: ['high', 'medium', 'low'].includes(d.severity) ? d.severity : 'medium' }
    } else if (itemType === 'current_measure') {
      metadata = { effectiveness: ['high', 'medium', 'low', 'none'].includes(d.effectiveness) ? d.effectiveness : 'medium' }
    }
    return { item_type: itemType, name, description, metadata }
  }).filter(Boolean)
}

// ============ Strategy metadata 字段展示 ============
function showMetaRow(item) {
  if (item.item_type === 'industry_trend') {
    return !!(item.metadata?.impact_area || '').trim()
  }
  // pain_point / current_measure 始终显示
  return true
}

function getMetaLabel(item) {
  if (item.item_type === 'industry_trend') return t('insight.impactArea')
  if (item.item_type === 'pain_point') return t('insight.severity')
  if (item.item_type === 'current_measure') return t('insight.effectiveness')
  return ''
}

function getMetaValue(item) {
  const meta = item.metadata || {}
  if (item.item_type === 'industry_trend') return meta.impact_area || '—'
  if (item.item_type === 'pain_point') return severityLabel(meta.severity)
  if (item.item_type === 'current_measure') return effectivenessLabel(meta.effectiveness)
  return '—'
}

function getMetaClass(item) {
  const meta = item.metadata || {}
  if (item.item_type === 'pain_point') return `meta-sev-${meta.severity || 'medium'}`
  if (item.item_type === 'current_measure') return `meta-eff-${meta.effectiveness || 'medium'}`
  return ''
}

function severityLabel(v) {
  return { high: t('insight.severityHigh'), medium: t('insight.severityMedium'), low: t('insight.severityLow') }[v] || '—'
}

function effectivenessLabel(v) {
  return { high: t('insight.severityHigh'), medium: t('insight.severityMedium'), low: t('insight.severityLow'), none: t('insight.effectivenessNone') }[v] || '—'
}

// ============ Why Modal 操作 ============
function openAddWhyModal(contextType) {
  whyModal.mode = 'add'
  whyModal.contextType = contextType
  whyModal.error = ''
  whyModal.form = { context_text: '', rationale: '' }
  whyModal.visible = true
  nextTick(() => whyContextInputRef.value?.focus())
}

function openEditWhyModal(contextType) {
  const existing = contextByType[contextType]
  if (!existing) return
  whyModal.mode = 'edit'
  whyModal.contextType = contextType
  whyModal.error = ''
  whyModal.form = {
    context_text: existing.context_text || '',
    rationale: existing.rationale || '',
  }
  whyModal.visible = true
  nextTick(() => whyContextInputRef.value?.focus())
}

function closeWhyModal() {
  if (whyModal.saving) return
  whyModal.visible = false
  whyModal.error = ''
}

async function handleSaveWhy() {
  const projectId = props.currentProject?.id
  if (!projectId) return
  const contextText = (whyModal.form.context_text || '').trim()
  if (!contextText) {
    whyModal.error = t('insight.contextRequired')
    return
  }
  whyModal.saving = true
  whyModal.error = ''
  try {
    const rationale = (whyModal.form.rationale || '').trim() || null
    // upsert 语义：同一 (project_id, context_type) 已有则更新，否则新建
    await upsertWhyContext(projectId, {
      context_type: whyModal.contextType,
      context_text: contextText,
      rationale,
    })
    showToast(whyModal.mode === 'add' ? t('toast.createSuccess') : t('toast.saveSuccess'), 'success')
    whyModal.visible = false
    await loadWhyContexts()
  } catch (err) {
    const msg = err?.response?.data?.error || err?.message || t('toast.saveFailed')
    whyModal.error = `${t('toast.saveFailed')}：${msg}`
  } finally {
    whyModal.saving = false
  }
}

async function handleDeleteWhy(contextType) {
  const projectId = props.currentProject?.id
  const existing = contextByType[contextType]
  if (!projectId || !existing?.id) return
  const title = whyGroups.value.find(g => g.type === contextType)?.title || ''
  const confirmed = await requestConfirm({
    title: `${t('common.delete')}${title}`,
    message: t('insight.deleteWhyConfirm', { title }),
    confirmText: t('common.delete'),
    danger: true,
  })
  if (!confirmed) return
  try {
    await deleteWhyContext(projectId, existing.id)
    showToast(t('toast.deleteSuccess'), 'success')
    await loadWhyContexts()
  } catch (err) {
    const msg = err?.response?.data?.error || err?.message || t('toast.deleteFailed')
    showToast(`${t('toast.deleteFailed')}：${msg}`, 'error')
  }
}

// ============ Why AI 生成（覆盖式） ============
async function handleAIGenerateWhy() {
  const projectId = props.currentProject?.id
  if (!projectId) return
  const confirmed = await requestConfirm({
    title: t('insight.aiGenerateWhyTitle'),
    message: t('insight.aiGenerateWhyConfirm'),
    confirmText: t('common.confirm'),
    danger: true,
  })
  if (!confirmed) return
  aiGeneratingWhy.value = true
  try {
    const res = await aiGenerateWhyContexts(projectId)
    const draft = res.draft || {}
    // 逐条 upsert 持久化（每类 1 条）
    for (const group of whyGroups.value) {
      const d = draft[group.type]
      if (!d) continue
      const contextText = (d.context_text || '').trim()
      if (!contextText) continue
      const rationale = (d.rationale || '').trim() || null
      await upsertWhyContext(projectId, {
        context_type: group.type,
        context_text: contextText,
        rationale,
      })
    }
    showToast(t('insight.aiGenerateSuccess'), 'success')
    await loadWhyContexts()
  } catch (err) {
    const msg = err?.response?.data?.error || err?.message || t('insight.aiGenerateFailed')
    showToast(`${t('insight.aiGenerateFailed')}：${msg}`, 'error')
  } finally {
    aiGeneratingWhy.value = false
  }
}

// ============ Tab 5：竞争分析 内联编辑 ============
function startEditCompetitive() {
  editing.field = 'competitive_analysis'
  editing.value = props.currentProject?.competitive_analysis ?? ''
}

function cancelEditCompetitive() {
  editing.field = null
  editing.value = ''
}

async function saveEditCompetitive() {
  if (editing.field !== 'competitive_analysis' || editing.saving) return
  const newVal = editing.value
  const oldVal = props.currentProject?.competitive_analysis ?? ''
  editing.field = null
  // 无变化直接退出
  const oldCmp = oldVal == null ? '' : oldVal
  const newCmp = newVal == null ? '' : newVal
  if (newCmp === oldCmp) return
  // 通过 emit 让父组件处理保存
  emit('update-project', { field: 'competitive_analysis', value: newVal })
}

// ============ Tab 5：竞争分析 AI 生成 ============
async function handleGenerateCompetitive() {
  const projectId = props.currentProject?.id
  if (!projectId) {
    competitiveError.value = t('insight.noProjectSelected')
    return
  }
  if (competitiveGenerating.value) return
  competitiveGenerating.value = true
  competitiveError.value = ''
  try {
    const res = await generateCompetitiveAnalysis(projectId, [])
    const content = res?.competitive_analysis || ''
    if (content) {
      // 后端已写库，通知父组件用返回的 project 数据刷新 currentProject
      if (res.project) {
        emit('refresh-project', res.project)
      } else {
        // 兜底：只更新单字段
        emit('update-project', { field: 'competitive_analysis', value: content, source: 'ai_generate' })
      }
    } else {
      competitiveError.value = t('insight.llmEmptyContent')
    }
  } catch (err) {
    const msg = err?.response?.data?.error || err?.message || t('insight.generateFailed')
    competitiveError.value = `${t('insight.tabs.competitiveAnalysis')}${msg}`
  } finally {
    competitiveGenerating.value = false
  }
}
</script>

<style scoped>
/* ============ 业务字段 Tab section ============ */
.info-field-tabs-section {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 18px 24px 20px;
  box-shadow: var(--shadow-sm);
}

.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 20px;
}

.section-deco {
  color: var(--accent);
  font-size: var(--fs-md);
  font-weight: 300;
}

.section-title {
  font-size: var(--fs-lg);
  font-weight: 600;
  margin: 0;
  color: var(--text-primary);
  flex: 1;
}

/* ============ Tab 切换 ============ */
.info-field-tabs {
  display: flex;
  align-items: center;
  gap: 4px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 12px;
  height: 32px;
}

.info-field-tab {
  appearance: none;
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  padding: 4px 14px;
  font-family: var(--font-sans);
  font-size: var(--fs-sm);
  font-weight: 600;
  color: var(--text-muted);
  cursor: pointer;
  white-space: nowrap;
  transition: color 0.15s, border-color 0.15s;
  margin-bottom: -1px;
  line-height: 1.4;
}

.info-field-tab:hover {
  color: var(--text-secondary);
}

.info-field-tab.active {
  color: var(--accent);
  border-bottom-color: var(--accent);
}

.info-field-tab:focus-visible {
  outline: 2px solid var(--focus-ring);
  outline-offset: 2px;
  border-radius: 2px;
}

.info-field-tab-body {
  min-height: 80px;
}

.tab-panel {
  padding: 8px 0 0;
}

/* ============ AI 生成按钮（共享） ============ */
.ai-generate-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 10px;
  font-size: 11px;
  font-family: var(--font-sans);
  line-height: 1.5;
  color: var(--accent);
  background: transparent;
  border: 1px solid var(--accent);
  border-radius: 12px;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s, color 0.15s;
}

.ai-generate-btn:hover:not(:disabled) {
  background: var(--accent);
  color: #fff;
}

.ai-generate-btn:focus-visible {
  outline: 2px solid var(--focus-ring);
  outline-offset: 2px;
}

.ai-generate-btn:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.ai-generate-icon {
  display: inline-block;
  font-size: 10px;
  line-height: 1;
}

.ai-generate-icon.spinning {
  animation: ai-spin 1s linear infinite;
  transform-origin: center;
}

@keyframes ai-spin {
  to { transform: rotate(360deg); }
}

.ai-generate-error {
  margin: 4px 0 6px;
  padding: 6px 10px;
  font-size: 12px;
  color: var(--red, #c4391c);
  background: rgba(196, 57, 28, 0.08);
  border-left: 2px solid var(--red, #c4391c);
  border-radius: 2px;
}

/* ============ 分组容器（Strategy / Why 共用基础） ============ */
.strategy-groups,
.why-groups {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.strategy-group,
.why-group {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 12px;
}

.group-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.group-title {
  font-size: var(--fs-sm);
  font-weight: 700;
  color: var(--text-secondary);
  font-family: var(--font-mono);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.group-count {
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}

/* Why 模块：title 占满左侧，actions 推到右边 */
.why-group .group-title {
  flex: 1;
}

.why-group .group-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

/* Strategy 中的 + 按钮：方形小按钮，靠 margin-left:auto 推到右边 */
.strategy-group .add-btn {
  appearance: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: 1px dashed var(--border-strong);
  border-radius: 6px;
  color: var(--text-muted);
  cursor: pointer;
  font-family: var(--font-mono);
  font-size: 14px;
  font-weight: 700;
  width: 20px;
  height: 18px;
  line-height: 1;
  padding: 0;
  margin-left: auto;
  transition: border-color 0.15s, color 0.15s, background 0.15s;
}

.strategy-group .add-btn:hover:not(:disabled) {
  border-color: var(--accent);
  color: var(--accent);
  background: rgba(205, 80, 54, 0.06);
  border-style: solid;
}

.strategy-group .add-btn:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.strategy-group .add-btn:focus-visible {
  outline: 2px solid var(--focus-ring);
  outline-offset: 2px;
}

/* Why 中的 "点击添加" 按钮：橙色描边文字按钮 */
.why-group .add-btn {
  appearance: none;
  font-family: var(--font-sans);
  font-size: 11px;
  padding: 2px 10px;
  border-radius: 8px;
  cursor: pointer;
  color: var(--accent);
  background: transparent;
  border: 1px dashed var(--accent);
  transition: border-color 0.15s, color 0.15s, background 0.15s;
}

.why-group .add-btn:hover:not(:disabled) {
  background: rgba(205, 80, 54, 0.06);
  border-style: solid;
}

.why-group .add-btn:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.why-group .add-btn:focus-visible {
  outline: 2px solid var(--focus-ring);
  outline-offset: 2px;
}

.group-empty {
  font-size: var(--fs-xs);
  color: var(--text-muted);
  font-style: italic;
  padding: 4px 0;
}

/* ============ Strategy 条目卡片 ============ */
.group-items {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.strategy-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 8px 10px;
  transition: border-color 0.15s, background 0.15s;
}

.strategy-card:hover {
  border-color: var(--border-strong);
}

.card-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.card-name {
  font-size: var(--fs-sm);
  font-weight: 700;
  color: var(--text-primary);
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.card-action-btn {
  appearance: none;
  font-family: var(--font-sans);
  font-size: 10px;
  padding: 2px 8px;
  border-radius: 8px;
  cursor: pointer;
  border: 1px solid transparent;
  transition: background 0.15s, color 0.15s, border-color 0.15s, opacity 0.15s;
}

.card-action-btn:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.edit-btn {
  color: var(--text-muted);
  background: transparent;
  border-color: var(--border);
}

.edit-btn:hover:not(:disabled) {
  color: var(--accent);
  background: rgba(205, 80, 54, 0.06);
  border-color: var(--accent);
}

.delete-btn {
  color: var(--text-muted);
  background: transparent;
  border-color: var(--border);
}

.delete-btn:hover:not(:disabled) {
  color: var(--red);
  background: var(--red-light);
  border-color: var(--red);
}

.card-action-btn:focus-visible {
  outline: 2px solid var(--focus-ring);
  outline-offset: 1px;
}

.card-desc {
  margin: 0 0 6px;
  font-size: var(--fs-xs);
  color: var(--text-secondary);
  line-height: 1.55;
  white-space: normal;
  word-break: break-word;
}

.card-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 10px;
}

.meta-label {
  color: var(--text-muted);
  font-weight: 600;
}

.meta-value {
  display: inline-block;
  padding: 1px 8px;
  border-radius: 8px;
  font-weight: 600;
  font-family: var(--font-mono);
  border: 1px solid transparent;
}

/* 痛点严重程度：high=红 / medium=黄 / low=绿 */
.meta-sev-high {
  color: var(--red);
  background: var(--red-light);
  border-color: rgba(196, 57, 28, 0.2);
}
.meta-sev-medium {
  color: #8B7434;
  background: var(--yellow-light);
  border-color: rgba(203, 184, 140, 0.3);
}
.meta-sev-low {
  color: var(--green);
  background: var(--green-light);
  border-color: rgba(17, 138, 88, 0.2);
}

/* 当前措施有效性：high=绿 / medium=黄 / low=红 / none=灰 */
.meta-eff-high {
  color: var(--green);
  background: var(--green-light);
  border-color: rgba(17, 138, 88, 0.2);
}
.meta-eff-medium {
  color: #8B7434;
  background: var(--yellow-light);
  border-color: rgba(203, 184, 140, 0.3);
}
.meta-eff-low {
  color: var(--red);
  background: var(--red-light);
  border-color: rgba(196, 57, 28, 0.2);
}
.meta-eff-none {
  color: var(--text-muted);
  background: var(--bg-surface);
  border-color: var(--border);
}

/* ============ Why 条目卡片 ============ */
.why-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 8px 10px;
  transition: border-color 0.15s, background 0.15s;
}

.why-card:hover {
  border-color: var(--border-strong);
}

.card-text {
  margin: 0 0 6px;
  font-size: var(--fs-sm);
  color: var(--text-primary);
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

.card-rationale {
  margin: 0;
  font-size: var(--fs-xs);
  color: var(--text-muted);
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}

.rationale-label {
  font-weight: 600;
  color: var(--text-secondary);
}

/* ============ Tab 5：竞争分析（内联编辑） ============ */
.info-row-block {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.info-value {
  font-size: var(--fs-base);
  color: var(--text-primary);
  font-weight: 500;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
}

.info-value-text {
  display: block;
  line-height: var(--lh-loose);
  color: var(--text-secondary);
  font-weight: 400;
  white-space: normal;
  overflow: visible;
  text-overflow: clip;
}

.info-value-editable {
  cursor: pointer;
  border-radius: 4px;
  transition: background 0.15s;
}

.info-value-editable:hover {
  background: var(--bg-surface);
  outline: 1px dashed var(--border-strong);
}

.info-value-editable:focus-visible {
  outline: 2px solid var(--focus-ring);
  outline-offset: 2px;
}

.inline-edit-textarea {
  width: 100%;
  font-family: var(--font-sans);
  font-size: var(--fs-base);
  line-height: var(--lh-loose);
  color: var(--text-secondary);
  background: var(--bg-surface);
  border: 1px solid var(--accent);
  border-radius: 6px;
  padding: 8px 10px;
  resize: vertical;
  min-height: 80px;
}

.inline-edit-textarea:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 2px rgba(205, 80, 54, 0.12);
}

.inline-edit-textarea:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 格式化文本（formatStructuredText 输出） */
.formatted-text {
  white-space: normal !important;
  overflow: visible !important;
  text-overflow: clip !important;
}

.formatted-text :deep(.fmt-empty) {
  color: var(--text-muted);
  font-style: italic;
}

.formatted-text :deep(.fmt-title) {
  font-size: var(--fs-sm);
  font-weight: 700;
  color: var(--text-primary);
  margin: 12px 0 6px 0;
  padding-bottom: 4px;
  border-bottom: 1px solid var(--border);
  letter-spacing: 0.02em;
}

.formatted-text :deep(.fmt-title:first-child) {
  margin-top: 0;
}

.formatted-text :deep(.fmt-text) {
  font-size: var(--fs-base);
  line-height: var(--lh-loose);
  color: var(--text-secondary);
  margin: 4px 0;
}

.formatted-text :deep(.fmt-list) {
  margin: 4px 0 8px 0;
  padding-left: 18px;
  list-style: none;
}

.formatted-text :deep(.fmt-list li) {
  font-size: var(--fs-base);
  line-height: var(--lh-loose);
  color: var(--text-secondary);
  margin: 3px 0;
  position: relative;
  padding-left: 4px;
}

.formatted-text :deep(.fmt-list li)::before {
  content: '•';
  color: var(--accent);
  font-weight: 700;
  position: absolute;
  left: -12px;
}

/* ============ 骨架屏 ============ */
.strategy-skeleton {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.skel-line {
  height: 12px;
  background: linear-gradient(90deg, var(--border) 25%, var(--bg-surface) 50%, var(--border) 75%);
  background-size: 200% 100%;
  border-radius: 4px;
  animation: skel-shimmer 1.4s ease-in-out infinite;
}

.skel-line.w70 { width: 70%; }

.skel-block {
  height: 50px;
  background: linear-gradient(90deg, var(--border) 25%, var(--bg-surface) 50%, var(--border) 75%);
  background-size: 200% 100%;
  border-radius: 6px;
  animation: skel-shimmer 1.4s ease-in-out infinite;
}

@keyframes skel-shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* ============ Modal（Strategy / Why 共用） ============ */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(21, 23, 29, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.modal {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 10px;
  width: 100%;
  max-width: 480px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 12px 40px rgba(21, 23, 29, 0.15);
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  border-bottom: 1px solid var(--border);
}

.modal-title {
  margin: 0;
  font-size: var(--fs-md);
  font-weight: 600;
  color: var(--text-primary);
  font-family: var(--font-sans);
}

.modal-close {
  appearance: none;
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 22px;
  line-height: 1;
  padding: 0 4px;
  font-family: var(--font-sans);
}

.modal-close:hover {
  color: var(--text-primary);
}

.modal-close:focus-visible {
  outline: 2px solid var(--focus-ring);
  outline-offset: 2px;
  border-radius: 2px;
}

.modal-body {
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow-y: auto;
}

.form-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-label {
  font-size: var(--fs-sm);
  font-weight: 600;
  color: var(--text-secondary);
}

.form-label .required {
  color: var(--accent);
  margin-left: 2px;
}

.form-input {
  appearance: auto;
  font-family: var(--font-sans);
  font-size: var(--fs-base);
  color: var(--text-primary);
  background: var(--bg-surface);
  border: 1px solid var(--border-strong);
  border-radius: 6px;
  padding: 7px 10px;
  cursor: text;
}

.form-input:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 2px rgba(205, 80, 54, 0.12);
}

.form-textarea {
  font-family: var(--font-sans);
  font-size: var(--fs-base);
  color: var(--text-primary);
  background: var(--bg-surface);
  border: 1px solid var(--border-strong);
  border-radius: 6px;
  padding: 7px 10px;
  resize: vertical;
  min-height: 60px;
  line-height: 1.5;
}

.form-textarea:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 2px rgba(205, 80, 54, 0.12);
}

.form-error {
  margin: 0;
  padding: 6px 10px;
  font-size: var(--fs-xs);
  color: var(--red);
  background: var(--red-light);
  border-left: 2px solid var(--red);
  border-radius: 2px;
}

.modal-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  padding: 12px 20px;
  border-top: 1px solid var(--border);
}

.btn-secondary,
.btn-primary {
  appearance: none;
  font-family: var(--font-sans);
  font-size: var(--fs-sm);
  font-weight: 600;
  padding: 6px 16px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s, color 0.15s, opacity 0.15s;
  border: 1px solid transparent;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.btn-secondary {
  background: transparent;
  border-color: var(--border-strong);
  color: var(--text-secondary);
}

.btn-secondary:hover:not(:disabled) {
  background: var(--bg-surface);
  border-color: var(--text-muted);
}

.btn-secondary:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.btn-primary {
  background: var(--accent);
  color: #fff;
  border-color: var(--accent);
}

.btn-primary:hover:not(:disabled) {
  background: var(--accent-hover);
  border-color: var(--accent-hover);
}

.btn-primary:disabled {
  cursor: not-allowed;
  opacity: 0.55;
  background: var(--text-muted);
  border-color: var(--text-muted);
}

.btn-secondary:focus-visible,
.btn-primary:focus-visible {
  outline: 2px solid var(--focus-ring);
  outline-offset: 2px;
}

.btn-spinner {
  display: inline-block;
  width: 10px;
  height: 10px;
  border: 1.5px solid rgba(255, 255, 255, 0.4);
  border-top-color: #fff;
  border-radius: 50%;
  animation: btn-spin 0.8s linear infinite;
}

@keyframes btn-spin {
  to { transform: rotate(360deg); }
}

@media (prefers-reduced-motion: reduce) {
  .ai-generate-icon.spinning,
  .btn-spinner,
  .skel-line,
  .skel-block {
    animation: none;
  }
}
</style>

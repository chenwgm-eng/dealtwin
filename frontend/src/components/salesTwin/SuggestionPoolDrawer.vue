<template>
  <Teleport to="body">
    <Transition name="sp-drawer">
      <div v-if="visible" class="sp-overlay" @click.self="$emit('close')">
        <div class="sp-drawer" role="dialog" :aria-label="t('workspace.suggestionPool')" aria-modal="true">
          <!-- 头部 -->
          <div class="sp-header">
            <div class="sp-header-left">
              <span class="sp-title">{{ t('workspace.suggestionPool') }}</span>
              <span class="sp-count" v-if="suggestions.length">{{ t('workspace.suggestionCount', { count: suggestions.length }) }}</span>
            </div>
            <div class="sp-header-right">
              <button
                type="button"
                class="sp-btn sp-btn-primary"
                @click="handleGenerateTasks"
                :disabled="generating || suggestions.length === 0"
                :aria-label="generating ? t('workspace.generatingTasks') : t('workspace.generateFromSuggestions')"
              >
                <span v-if="generating" class="sp-spinner" aria-hidden="true"></span>
                <svg v-else class="sp-btn-icon" viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
                  <path d="M8 1v14M1 8h14" stroke-linecap="round"/>
                </svg>
                <span>{{ generating ? t('common.generating') : t('workspace.generateTasks') }}</span>
              </button>
              <button
                type="button"
                class="sp-close"
                @click="$emit('close')"
                :aria-label="t('workspace.closeSuggestionPool')"
              >
                <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                  <line x1="18" y1="6" x2="6" y2="18"></line>
                  <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
              </button>
            </div>
          </div>

          <!-- 操作提示 -->
          <div class="sp-tip" v-if="suggestions.length === 0 && !loading">
            <div class="sp-tip-icon" aria-hidden="true">
              <svg viewBox="0 0 48 48" width="48" height="48" fill="none" stroke="currentColor" stroke-width="1.5">
                <rect x="8" y="12" width="32" height="28" rx="2"/>
                <line x1="8" y1="20" x2="40" y2="20"/>
                <line x1="14" y1="8" x2="14" y2="14"/>
                <line x1="34" y1="8" x2="34" y2="14"/>
              </svg>
            </div>
            <p class="sp-tip-title">{{ t('workspace.emptySuggestionPool') }}</p>
            <p class="sp-tip-sub">{{ t('workspace.emptySuggestionHint') }}</p>
          </div>

          <!-- 加载中 -->
          <div class="sp-tip" v-if="loading" aria-live="polite">
            <div class="sp-spinner sp-spinner-lg" aria-hidden="true"></div>
            <p>{{ t('common.loading') }}</p>
          </div>

          <!-- 建议列表 -->
          <div class="sp-list" v-if="!loading && suggestions.length > 0">
            <div
              v-for="item in suggestions"
              :key="item.id"
              class="sp-item"
              :class="{ consumed: item.is_consumed, editing: editingId === item.id }"
            >
              <!-- 查看模式 -->
              <template v-if="editingId !== item.id">
                <div class="sp-item-header">
                  <span class="sp-source-badge" :class="`sp-source-${item.source}`">
                    {{ sourceLabels[item.source] || item.source }}
                  </span>
                  <span class="sp-item-time" v-if="item.created_at">{{ formatDate(item.created_at) }}</span>
                  <span class="sp-consumed-tag" v-if="item.is_consumed">
                    <svg viewBox="0 0 16 16" width="10" height="10" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                      <polyline points="3,8 7,12 13,4"/>
                    </svg>
                    {{ t('workspace.consumedTag') }}
                  </span>
                </div>
                <div class="sp-item-content">{{ item.content }}</div>
                <!-- 删除确认 -->
                <div v-if="deletingId === item.id" class="sp-delete-confirm">
                  <span>{{ t('workspace.confirmDeleteSuggestion') }}</span>
                  <button type="button" class="sp-action-btn sp-action-danger" @click="handleDelete(item)">{{ t('workspace.confirmDelete') }}</button>
                  <button type="button" class="sp-action-btn" @click="cancelDelete">{{ t('common.cancel') }}</button>
                </div>
                <div v-else class="sp-item-actions">
                  <button type="button" class="sp-action-btn" @click="startEdit(item)">{{ t('common.edit') }}</button>
                  <button type="button" class="sp-action-btn sp-action-danger" @click="confirmDelete(item)">{{ t('common.delete') }}</button>
                </div>
              </template>

              <!-- 编辑模式 -->
              <template v-else>
                <textarea
                  ref="editTextarea"
                  class="sp-edit-textarea"
                  v-model="editContent"
                  rows="4"
                  autocomplete="off"
                  :aria-label="t('workspace.editSuggestionAria')"
                ></textarea>
                <div class="sp-item-actions">
                  <button type="button" class="sp-action-btn sp-action-primary" @click="saveEdit(item)">{{ t('common.save') }}</button>
                  <button type="button" class="sp-action-btn" @click="cancelEdit">{{ t('common.cancel') }}</button>
                </div>
              </template>
            </div>
          </div>

          <!-- 错误提示 -->
          <div v-if="errorMsg" class="sp-error" aria-live="polite" role="alert">
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="8" x2="12" y2="12"/>
              <line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            <span>{{ errorMsg }}</span>
            <button type="button" class="sp-error-close" @click="errorMsg = ''" :aria-label="t('workspace.closeError')">
              <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <line x1="18" y1="6" x2="6" y2="18"/>
                <line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
          </div>

          <!-- 生成结果 -->
          <div class="sp-result" v-if="generatedTasks.length > 0">
            <div class="sp-result-header">
              <span class="sp-result-title">{{ t('workspace.generatedTasksCount', { count: generatedTasks.length }) }}</span>
              <button type="button" class="sp-action-btn" @click="generatedTasks = []">{{ t('common.close') }}</button>
            </div>
            <div class="sp-result-list">
              <div v-for="(task, idx) in generatedTasks" :key="idx" class="sp-result-item">
                <div class="sp-result-item-header">
                  <span class="sp-result-priority" :class="`sp-priority-${task.priority}`">{{ priorityLabels[task.priority] }}</span>
                  <span class="sp-result-type">{{ taskTypeLabels[task.task_type] || task.task_type }}</span>
                  <span class="sp-result-target" v-if="task.target_stakeholder">→ {{ task.target_stakeholder }}</span>
                </div>
                <div class="sp-result-item-title">{{ task.title }}</div>
                <div class="sp-result-item-desc" v-if="task.description">{{ task.description }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import * as salesTwinApi from '../../api/salesTwin'

const { t } = useI18n()

const props = defineProps({
  visible: Boolean,
  projectId: [Number, String]
})

const emit = defineEmits(['close', 'tasks-generated'])

const suggestions = ref([])
const loading = ref(false)
const generating = ref(false)
const editingId = ref(null)
const editContent = ref('')
const editTextarea = ref(null)
const generatedTasks = ref([])
const deletingId = ref(null)
const errorMsg = ref('')

const _dateFmt = new Intl.DateTimeFormat('zh-CN', {
  month: 'numeric', day: 'numeric',
  hour: '2-digit', minute: '2-digit'
})

const sourceLabels = computed(() => ({
  interview: t('workspace.sourceInterview'),
  report: t('workspace.sourceReport'),
  manual: t('workspace.sourceManual')
}))

const priorityLabels = computed(() => ({
  high: t('workspace.priorityLabels.high'),
  medium: t('workspace.priorityLabels.medium'),
  low: t('workspace.priorityLabels.low')
}))

const taskTypeLabels = computed(() => ({
  build_alliance: t('workspace.taskTypes.build_alliance'),
  address_concerns: t('workspace.taskTypes.address_concerns'),
  provide_material: t('workspace.taskTypes.provide_material'),
  meeting: t('workspace.taskTypes.meeting'),
  follow_up: t('workspace.taskTypes.follow_up'),
  blind_spot: t('workspace.taskTypes.blind_spot')
}))

async function loadSuggestions() {
  if (!props.projectId) return
  loading.value = true
  try {
    const res = await salesTwinApi.getSuggestions(props.projectId)
    suggestions.value = res.suggestions || []
  } catch (e) {
    console.error('加载建议池失败:', e)
  } finally {
    loading.value = false
  }
}

function startEdit(item) {
  editingId.value = item.id
  editContent.value = item.content
  nextTick(() => {
    if (editTextarea.value && editTextarea.value[0]) {
      editTextarea.value[0].focus()
    }
  })
}

function cancelEdit() {
  editingId.value = null
  editContent.value = ''
}

async function saveEdit(item) {
  const content = editContent.value.trim()
  if (!content) return
  try {
    await salesTwinApi.updateSuggestion(item.id, { content })
    item.content = content
    editingId.value = null
    editContent.value = ''
  } catch (e) {
    console.error('保存建议失败:', e)
  }
}

function confirmDelete(item) {
  deletingId.value = item.id
}

function cancelDelete() {
  deletingId.value = null
}

async function handleDelete(item) {
  try {
    await salesTwinApi.deleteSuggestion(item.id)
    suggestions.value = suggestions.value.filter(s => s.id !== item.id)
    deletingId.value = null
  } catch (e) {
    console.error('删除建议失败:', e)
  }
}

async function handleGenerateTasks() {
  if (generating.value || suggestions.value.length === 0) return
  generating.value = true
  generatedTasks.value = []
  errorMsg.value = ''
  try {
    const res = await salesTwinApi.generateTasksFromSuggestions(props.projectId)
    if (res.success) {
      generatedTasks.value = res.generated_tasks || []
      const consumedIds = new Set(res.consumed_suggestion_ids || [])
      suggestions.value.forEach(s => {
        if (consumedIds.has(s.id)) {
          s.is_consumed = true
        }
      })
      emit('tasks-generated', res.generated_count || 0)
    } else {
      errorMsg.value = res.error || t('workspace.generateFailedRetry')
    }
  } catch (e) {
    console.error('生成待办失败:', e)
    errorMsg.value = t('workspace.generateTasksFailed')
  } finally {
    generating.value = false
  }
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  try {
    return _dateFmt.format(new Date(dateStr))
  } catch {
    return ''
  }
}

function handleKeydown(e) {
  if (e.key === 'Escape' && props.visible) {
    if (editingId.value !== null) {
      cancelEdit()
    } else if (deletingId.value !== null) {
      cancelDelete()
    } else {
      emit('close')
    }
  }
}

onMounted(() => {
  document.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown)
})

watch(() => props.visible, (val) => {
  if (val) {
    loadSuggestions()
  } else {
    editingId.value = null
    generatedTasks.value = []
    deletingId.value = null
    errorMsg.value = ''
  }
})
</script>

<style scoped>
/* ============ 系统变量 ============ */
.sp-overlay {
  --black: #000000;
  --white: #FFFFFF;
  --orange: #FF4500;
  --green: #4CAF50;
  --red: #F44336;
  --gray-bg: #F5F5F5;
  --gray-text: #666666;
  --gray-muted: #999999;
  --gray-faint: #CCCCCC;
  --border: #E5E5E5;
  --font-mono: 'JetBrains Mono', monospace;
  --font-sans: 'Space Grotesk', 'Noto Sans SC', system-ui, sans-serif;

  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
  z-index: 2000;
  display: flex;
  justify-content: flex-end;
  touch-action: manipulation;
  font-family: var(--font-sans);
}

.sp-drawer {
  width: 460px;
  max-width: 90vw;
  height: 100%;
  background: var(--gray-bg);
  display: flex;
  flex-direction: column;
  box-shadow: -4px 0 24px rgba(0, 0, 0, 0.12);
  overflow: hidden;
}

/* ============ 头部 ============ */
.sp-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  background: var(--black);
  color: var(--white);
  flex-shrink: 0;
}

.sp-header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.sp-title {
  font-family: var(--font-mono);
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 0.05em;
  color: var(--white);
}

.sp-count {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--gray-muted);
  background: rgba(255, 255, 255, 0.12);
  padding: 2px 8px;
  border-radius: 2px;
}

.sp-header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 主按钮：黑底白字，hover变橙——与系统 .btn-primary 一致 */
.sp-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border: 1px solid var(--white);
  border-radius: 2px;
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.05em;
  cursor: pointer;
  transition: background-color 0.2s, border-color 0.2s, color 0.2s;
  touch-action: manipulation;
}

.sp-btn-primary {
  background: var(--white);
  color: var(--black);
  border-color: var(--white);
}

.sp-btn-primary:hover:not(:disabled) {
  background: var(--orange);
  border-color: var(--orange);
  color: var(--white);
}

.sp-btn-primary:focus-visible {
  outline: 2px solid var(--orange);
  outline-offset: 2px;
}

.sp-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.sp-btn-icon {
  flex-shrink: 0;
}

/* 关闭按钮 */
.sp-close {
  display: flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: none;
  color: var(--gray-muted);
  cursor: pointer;
  padding: 4px;
  border-radius: 2px;
  transition: color 0.2s, background-color 0.2s;
  touch-action: manipulation;
}

.sp-close:hover {
  color: var(--white);
  background: rgba(255, 255, 255, 0.1);
}

.sp-close:focus-visible {
  outline: 2px solid var(--orange);
  outline-offset: 1px;
}

/* ============ 空状态/加载提示 ============ */
.sp-tip {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--gray-muted);
  text-align: center;
  padding: 40px 24px;
  gap: 6px;
}

.sp-tip-icon {
  color: var(--gray-faint);
  margin-bottom: 8px;
}

.sp-tip-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--gray-text);
}

.sp-tip-sub {
  font-size: 12px;
  color: var(--gray-muted);
  line-height: 1.6;
  max-width: 280px;
}

/* ============ 建议列表 ============ */
.sp-list {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  overscroll-behavior: contain;
}

.sp-item {
  background: var(--white);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 14px;
  margin-bottom: 8px;
  transition: border-color 0.2s;
}

.sp-item:hover {
  border-color: var(--gray-faint);
}

.sp-item.consumed {
  opacity: 0.55;
}

.sp-item.editing {
  border-color: var(--black);
}

.sp-item-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

/* 来源标签：rgba背景+边框+同色文字——与系统 stage-badge 一致 */
.sp-source-badge {
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 2px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border: 1px solid transparent;
}

.sp-source-interview {
  background: rgba(59, 130, 246, 0.1);
  border-color: rgba(59, 130, 246, 0.3);
  color: #1d4ed8;
}

.sp-source-report {
  background: rgba(139, 92, 246, 0.1);
  border-color: rgba(139, 92, 246, 0.3);
  color: #6d28d9;
}

.sp-source-manual {
  background: rgba(102, 102, 102, 0.1);
  border-color: rgba(102, 102, 102, 0.3);
  color: var(--gray-text);
}

.sp-item-time {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--gray-muted);
}

.sp-consumed-tag {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 600;
  color: var(--green);
  background: rgba(76, 175, 80, 0.1);
  border: 1px solid rgba(76, 175, 80, 0.3);
  padding: 2px 6px;
  border-radius: 2px;
  margin-left: auto;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.sp-item-content {
  font-size: 13px;
  line-height: 1.6;
  color: #333;
  white-space: pre-wrap;
  word-break: break-word;
}

.sp-item-actions {
  display: flex;
  gap: 6px;
  margin-top: 10px;
}

/* 次级按钮：透明底+边框——与系统 ghost 按钮一致 */
.sp-action-btn {
  background: none;
  border: 1px solid var(--border);
  border-radius: 2px;
  padding: 4px 12px;
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.05em;
  color: var(--gray-text);
  cursor: pointer;
  transition: background-color 0.2s, color 0.2s, border-color 0.2s;
  touch-action: manipulation;
  text-transform: uppercase;
}

.sp-action-btn:hover {
  background: var(--black);
  color: var(--white);
  border-color: var(--black);
}

.sp-action-btn:focus-visible {
  outline: 2px solid var(--orange);
  outline-offset: 1px;
}

.sp-action-primary {
  border-color: var(--black);
  color: var(--black);
}

.sp-action-primary:hover {
  background: var(--black);
  color: var(--white);
}

.sp-action-danger {
  color: var(--red);
  border-color: rgba(244, 67, 54, 0.4);
}

.sp-action-danger:hover {
  background: var(--red);
  color: var(--white);
  border-color: var(--red);
}

/* ============ 删除确认 ============ */
.sp-delete-confirm {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  padding: 8px 12px;
  background: rgba(244, 67, 54, 0.06);
  border: 1px solid rgba(244, 67, 54, 0.2);
  border-radius: 4px;
  flex-wrap: wrap;
}

.sp-delete-confirm > span {
  font-size: 12px;
  color: var(--red);
  flex: 1;
  min-width: 0;
}

/* ============ 编辑文本框 ============ */
.sp-edit-textarea {
  width: 100%;
  border: 1px solid var(--border);
  border-radius: 2px;
  padding: 10px;
  font-size: 13px;
  line-height: 1.6;
  resize: vertical;
  font-family: var(--font-sans);
  color: #333;
  background: var(--white);
}

.sp-edit-textarea:focus-visible {
  outline: 2px solid transparent;
  border-color: var(--black);
  box-shadow: 0 0 0 2px rgba(0, 0, 0, 0.08);
}

/* ============ 生成结果 ============ */
.sp-result {
  flex-shrink: 0;
  border-top: 2px solid var(--black);
  background: var(--white);
  max-height: 40%;
  overflow-y: auto;
  overscroll-behavior: contain;
}

.sp-result-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  background: var(--black);
  position: sticky;
  top: 0;
}

.sp-result-title {
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.05em;
  color: var(--white);
  text-transform: uppercase;
}

.sp-result-list {
  padding: 12px 16px 16px;
}

.sp-result-item {
  padding: 12px;
  background: var(--gray-bg);
  border: 1px solid var(--border);
  border-radius: 4px;
  margin-top: 8px;
}

.sp-result-item-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
}

.sp-result-priority {
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 2px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border: 1px solid transparent;
}

.sp-priority-high {
  background: rgba(244, 67, 54, 0.1);
  border-color: rgba(244, 67, 54, 0.3);
  color: #C62828;
}

.sp-priority-medium {
  background: rgba(255, 69, 0, 0.1);
  border-color: rgba(255, 69, 0, 0.3);
  color: var(--orange);
}

.sp-priority-low {
  background: rgba(102, 102, 102, 0.1);
  border-color: rgba(102, 102, 102, 0.3);
  color: var(--gray-text);
}

.sp-result-type {
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 600;
  color: var(--gray-text);
  background: rgba(102, 102, 102, 0.08);
  border: 1px solid var(--border);
  padding: 2px 6px;
  border-radius: 2px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.sp-result-target {
  font-size: 11px;
  color: var(--gray-text);
}

.sp-result-item-title {
  font-size: 13px;
  font-weight: 500;
  color: #333;
  margin-bottom: 4px;
}

.sp-result-item-desc {
  font-size: 12px;
  color: var(--gray-text);
  line-height: 1.5;
}

/* ============ 加载动画 ============ */
.sp-spinner {
  display: inline-block;
  width: 12px;
  height: 12px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: var(--white);
  border-radius: 50%;
  animation: sp-spin 0.8s linear infinite;
}

.sp-spinner-lg {
  width: 28px;
  height: 28px;
  border: 2px solid var(--border);
  border-top-color: var(--black);
  margin-bottom: 12px;
}

@keyframes sp-spin {
  to { transform: rotate(360deg); }
}

/* ============ 错误提示 ============ */
.sp-error {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  background: rgba(244, 67, 54, 0.08);
  border-top: 1px solid rgba(244, 67, 54, 0.2);
  font-size: 12px;
  color: #C62828;
  flex-shrink: 0;
}

.sp-error-close {
  margin-left: auto;
  display: flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: none;
  color: #C62828;
  cursor: pointer;
  padding: 2px;
  border-radius: 2px;
  transition: background-color 0.2s;
  touch-action: manipulation;
}

.sp-error-close:hover {
  background: rgba(198, 40, 40, 0.1);
}

.sp-error-close:focus-visible {
  outline: 2px solid #C62828;
  outline-offset: 1px;
}

/* ============ 抽屉过渡动画 ============ */
.sp-drawer-enter-active,
.sp-drawer-leave-active {
  transition: opacity 0.25s;
}

.sp-drawer-enter-active .sp-drawer,
.sp-drawer-leave-active .sp-drawer {
  transition: transform 0.25s ease-out;
}

.sp-drawer-enter-from,
.sp-drawer-leave-to {
  opacity: 0;
}

.sp-drawer-enter-from .sp-drawer,
.sp-drawer-leave-to .sp-drawer {
  transform: translateX(100%);
}

/* ============ 动效偏好 ============ */
@media (prefers-reduced-motion: reduce) {
  .sp-drawer-enter-active,
  .sp-drawer-leave-active,
  .sp-drawer-enter-active .sp-drawer,
  .sp-drawer-leave-active .sp-drawer {
    transition: none;
  }

  .sp-spinner,
  .sp-spinner-lg {
    animation: none;
  }

  .sp-btn,
  .sp-close,
  .sp-action-btn,
  .sp-item,
  .sp-error-close {
    transition: none;
  }
}
</style>

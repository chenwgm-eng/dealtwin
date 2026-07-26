<template>
  <div>
    <!-- 骨架屏（加载中） -->
    <div v-if="stageDeliverablesLoading" class="aside-skeleton">
      <div class="aside-skel-line"></div>
      <div class="aside-skel-line w70"></div>
      <div class="aside-skel-block"></div>
      <div class="aside-skel-line w40"></div>
      <div class="aside-skel-block"></div>
    </div>

    <!-- 空状态 -->
    <div v-else-if="!stageDeliverables" class="aside-empty">{{ t('deliverable.noDeliverables') }}</div>

    <!-- 正常渲染：四个区块 -->
    <div v-else class="aside-content">
      <!-- 区块1：阶段说明 -->
      <div class="aside-block stage-info-block">
        <div class="aside-block-title">{{ t('deliverable.stageDescription') }}</div>
        <div v-if="stageDeliverables.pm_milestone" class="stage-om-badge">{{ stageDeliverables.pm_milestone }}</div>
        <div class="stage-objective">{{ stageDeliverables.core_objective || '—' }}</div>
        <div class="stage-conditions">
          <div class="condition-group">
            <div class="condition-label">{{ t('deliverable.entryConditions') }}</div>
            <ul v-if="stageDeliverables.entry_conditions && stageDeliverables.entry_conditions.length">
              <li v-for="(c, i) in stageDeliverables.entry_conditions" :key="i">{{ c }}</li>
            </ul>
            <span v-else class="condition-empty">—</span>
          </div>
          <div class="condition-group">
            <div class="condition-label">{{ t('deliverable.exitConditions') }}</div>
            <ul v-if="stageDeliverables.exit_conditions && stageDeliverables.exit_conditions.length">
              <li v-for="(c, i) in stageDeliverables.exit_conditions" :key="i">{{ c }}</li>
            </ul>
            <span v-else class="condition-empty">—</span>
          </div>
        </div>
      </div>

      <!-- 区块2：交付物检查情况 -->
      <div class="aside-block deliverable-check-block">
        <div class="aside-block-title">
          {{ t('deliverable.deliverableCheck') }}
          <span class="completion-num">{{ completedCount }}/{{ totalCount }}</span>
          <button
            type="button"
            class="run-stage-check-btn"
            :disabled="stageDeliverablesLoading"
            :title="stageDeliverablesLoading ? t('common.loading') : t('deliverable.runStageCheckTooltip')"
            @click="emit('run-stage-check')"
          >
            <span class="run-check-icon" aria-hidden="true">▸</span>
            {{ t('deliverable.stageCheck') }}
          </button>
        </div>
        <div class="completion-bar">
          <div class="completion-fill" :class="progressClass" :style="{width: completionRate + '%'}"></div>
        </div>
        <div class="deliverable-mini-list">
          <div v-for="group in stageDeliverables.deliverables" :key="group.key" class="deliverable-mini-group">
            <div v-for="item in group.items" :key="item.key" class="deliverable-mini-item" :class="{ 'manual-completed': item.is_completed }">
              <label class="deliverable-checkbox" :title="item.is_completed ? t('deliverable.manuallyConfirmed') : t('deliverable.clickToConfirm')">
                <input
                  type="checkbox"
                  :checked="item.is_completed"
                  :disabled="deliverableToggling[item.key]"
                  @change="toggleDeliverableManual(item, $event.target.checked)"
                >
                <span class="checkbox-mark" :class="{
                  completed: item.effective_completed,
                  optional: item.is_optional,
                  manual: item.is_completed
                }" aria-hidden="true"></span>
              </label>
              <span class="item-name" :title="item.auto_reason">{{ item.name }}</span>
              <span v-if="(item.attachments?.length || 0) > 0" class="attach-count-badge" :title="t('deliverable.attachmentCount', { count: item.attachments.length })">
                <span class="attach-count-icon" aria-hidden="true">📎</span>
                <span class="attach-count-num">{{ item.attachments.length }}</span>
              </span>
              <button
                v-else
                type="button"
                class="attach-add-btn"
                :title="t('deliverable.uploadAttachmentFor', { name: item.name })"
                @click="openUploadModal(item)"
              >+</button>
            </div>
          </div>
        </div>
      </div>

      <!-- 区块3：阶段任务说明 -->
      <div class="aside-block stage-tasks-block">
        <div class="aside-block-title">{{ t('deliverable.stageTasks') }}</div>
        <div v-if="!stageDeliverables.tasks || !stageDeliverables.tasks.length" class="condition-empty">{{ t('deliverable.noTasks') }}</div>
        <details v-for="(task, i) in stageDeliverables.tasks" :key="i" class="stage-task-details">
          <summary class="stage-task-summary">{{ task.name }}</summary>
          <ul class="stage-task-sublist">
            <li v-for="(sub, j) in task.subtasks" :key="j">{{ sub }}</li>
          </ul>
        </details>
      </div>

      <!-- 区块4：交付物附件清单 -->
      <div class="aside-block attachment-block">
        <div class="aside-block-title">
          {{ t('workspace.attachments') }}
          <span class="attach-total-num">{{ totalAttachmentCount }}</span>
          <button type="button" class="upload-btn" @click="openUploadModal(null)">
            <span class="upload-icon" aria-hidden="true">↑</span>
            {{ t('deliverable.uploadAttachment') }}
          </button>
        </div>
        <div v-if="allAttachments.length === 0" class="attach-empty">
          {{ t('deliverable.noAttachmentsHint') }}
        </div>
        <ul v-else class="attach-list">
          <li v-for="att in allAttachments" :key="att.attach.filename" class="attach-item">
            <div class="attach-item-main">
              <span class="attach-item-name" :title="att.attach.original_filename">{{ att.attach.original_filename }}</span>
              <span class="attach-item-meta">
                <span class="attach-deliverable-tag" :title="att.deliverableName">{{ att.deliverableName }}</span>
                <span class="attach-size">{{ formatFileSize(att.attach.size) }}</span>
                <span class="attach-date">{{ formatDate(att.attach.uploaded_at) }}</span>
              </span>
            </div>
            <div class="attach-item-actions">
              <a
                :href="stageDeliverableAttachmentUrl(currentProject?.id, att.deliverableKey, att.stage, att.attach.filename)"
                :download="att.attach.original_filename"
                class="attach-action-btn attach-download-btn"
                :title="t('deliverable.downloadAttachment')"
              >{{ t('common.download') }}</a>
              <button
                type="button"
                class="attach-action-btn attach-delete-btn"
                :disabled="attachmentDeleting[att.attach.filename]"
                :title="attachmentDeleting[att.attach.filename] ? t('common.deleting') : t('common.delete')"
                @click="deleteAttachment(att)"
              >{{ attachmentDeleting[att.attach.filename] ? t('common.deleting') : t('common.delete') }}</button>
            </div>
          </li>
        </ul>
      </div>
    </div>

    <!-- 上传附件弹窗 -->
    <div v-if="uploadModal.visible" class="upload-modal-overlay" @click.self="closeUploadModal">
      <div class="upload-modal" role="dialog" aria-modal="true" aria-labelledby="upload-modal-title">
        <div class="upload-modal-header">
          <h3 id="upload-modal-title" class="upload-modal-title">{{ t('deliverable.uploadDeliverableAttachment') }}</h3>
          <button type="button" class="upload-modal-close" @click="closeUploadModal" :aria-label="t('common.close')">×</button>
        </div>
        <div class="upload-modal-body">
          <div class="upload-form-row">
            <label class="upload-form-label">{{ t('deliverable.deliverableType') }} <span class="required">*</span></label>
            <select v-model="uploadModal.deliverableKey" class="upload-form-select" :disabled="uploadModal.locked">
              <option value="">{{ t('deliverable.selectDeliverableType') }}</option>
              <optgroup v-for="group in stageDeliverables?.deliverables" :key="group.key" :label="group.name">
                <option v-for="item in group.items" :key="item.key" :value="item.key">{{ item.name }}</option>
              </optgroup>
            </select>
          </div>
          <div class="upload-form-row">
            <label class="upload-form-label">{{ t('deliverable.attachmentFile') }} <span class="required">*</span></label>
            <div class="upload-file-dropzone" @click="triggerFileInput">
              <input
                ref="uploadFileInput"
                type="file"
                multiple
                class="upload-file-input"
                :accept="ACCEPTED_EXTENSIONS"
                @change="onFileInputChange"
              >
              <div v-if="uploadModal.files.length === 0" class="upload-file-placeholder">
                <span class="upload-icon" aria-hidden="true">↑</span>
                <span>{{ t('deliverable.clickToSelectFiles') }}</span>
              </div>
              <ul v-else class="upload-file-list">
                <li v-for="(f, i) in uploadModal.files" :key="i" class="upload-file-item">
                  <span class="upload-file-name">{{ f.name }}</span>
                  <span class="upload-file-size">{{ formatFileSize(f.size) }}</span>
                  <button type="button" class="upload-file-remove" @click.stop="removeUploadFile(i)">×</button>
                </li>
              </ul>
            </div>
            <p class="upload-form-hint">{{ t('deliverable.supportedFormats') }}</p>
          </div>
          <p v-if="uploadModal.error" class="upload-form-error" role="alert">{{ uploadModal.error }}</p>
        </div>
        <div class="upload-modal-footer">
          <button type="button" class="upload-cancel-btn" @click="closeUploadModal" :disabled="uploadModal.uploading">{{ t('common.cancel') }}</button>
          <button
            type="button"
            class="upload-submit-btn"
            :disabled="!uploadModal.deliverableKey || uploadModal.files.length === 0 || uploadModal.uploading"
            @click="submitUpload"
          >
            <span v-if="uploadModal.uploading" class="upload-spinner" aria-hidden="true"></span>
            {{ uploadModal.uploading ? t('deliverable.uploading') : t('deliverable.confirmUpload') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { formatDate as defaultFormatDate, formatFileSize as defaultFormatFileSize } from '../../composables/salesTwin/formatters.js'
import {
  updateStageDeliverable,
  uploadStageDeliverableAttachments,
  deleteStageDeliverableAttachment,
  stageDeliverableAttachmentUrl
} from '../../api/salesTwin.js'
import { requestConfirm, showToast } from '../../composables/salesTwin/useConfirmToast'

const { t } = useI18n()

const props = defineProps({
  currentProject: { type: Object, default: () => ({}) },
  stageDeliverables: { type: Object, default: () => null },
  stageDeliverablesLoading: { type: Boolean, default: false },
  formatDate: { type: Function, default: defaultFormatDate },
  formatFileSize: { type: Function, default: defaultFormatFileSize },
})

const emit = defineEmits(['reload-stage-deliverables', 'run-stage-check'])

// 上传附件支持文件类型（与后端 ALLOWED_ATTACHMENT_EXTENSIONS 对齐）
const ACCEPTED_EXTENSIONS = '.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.md,.png,.jpg,.jpeg,.gif,.zip,.rar'

// ============ 完成度统计 ============
const completionRate = computed(() => props.stageDeliverables?.completion_rate || 0)

const completedCount = computed(() => {
  if (!props.stageDeliverables?.deliverables) return 0
  return props.stageDeliverables.deliverables.reduce((sum, g) =>
    sum + (g.items || []).filter(i => i.effective_completed && !i.is_optional).length, 0)
})

const totalCount = computed(() => {
  if (!props.stageDeliverables?.deliverables) return 0
  return props.stageDeliverables.deliverables.reduce((sum, g) =>
    sum + (g.items || []).filter(i => !i.is_optional).length, 0)
})

const progressClass = computed(() => {
  const r = completionRate.value
  if (r >= 80) return 'progress-ok'
  if (r >= 40) return 'progress-warn'
  return 'progress-danger'
})

// ============ 交付物手工勾选 ============
// 各交付物项的手工勾选进行中状态（key -> bool）
const deliverableToggling = reactive({})

// 手工勾选交付物完成状态（自动检查仍由后端判定，此处只更新手工 is_completed）
async function toggleDeliverableManual(item, isCompleted) {
  const projectId = props.currentProject?.id
  const stage = props.stageDeliverables?.stage
  if (!projectId || !stage || !item?.key) return
  if (deliverableToggling[item.key]) return
  deliverableToggling[item.key] = true
  try {
    await updateStageDeliverable(projectId, item.key, stage, {
      is_completed: isCompleted,
      notes: item.notes  // 保持原备注不变
    })
    emit('reload-stage-deliverables')
  } catch (err) {
    const msg = err?.response?.data?.error || err?.message || t('toast.updateFailed')
    showToast(`${t('deliverable.updateStatusFailed')}：${msg}`, 'error')
    // 失败时回滚 checkbox
    item.is_completed = !isCompleted
  } finally {
    deliverableToggling[item.key] = false
  }
}

// ============ 交付物附件 ============
// 汇总所有交付物的附件（带 deliverableKey / deliverableName / stage 元信息）
const allAttachments = computed(() => {
  const stage = props.stageDeliverables?.stage
  const groups = props.stageDeliverables?.deliverables || []
  const result = []
  for (const group of groups) {
    for (const item of (group.items || [])) {
      const attachments = item.attachments || []
      for (const attach of attachments) {
        result.push({
          attach,
          deliverableKey: item.key,
          deliverableName: item.name,
          groupName: group.name,
          stage,
        })
      }
    }
  }
  // 按上传时间倒序
  result.sort((a, b) => new Date(b.attach.uploaded_at || 0) - new Date(a.attach.uploaded_at || 0))
  return result
})

const totalAttachmentCount = computed(() => allAttachments.value.length)

// 附件删除进行中状态（filename -> bool）
const attachmentDeleting = reactive({})

async function deleteAttachment(att) {
  const projectId = props.currentProject?.id
  if (!projectId || !att?.deliverableKey || !att?.attach?.filename) return
  if (attachmentDeleting[att.attach.filename]) return
  const confirmed = await requestConfirm({
    title: t('deliverable.deleteAttachment'),
    message: t('deliverable.deleteAttachmentConfirm', { name: att.attach.original_filename }),
    confirmText: t('common.delete'),
    danger: true,
  })
  if (!confirmed) return
  attachmentDeleting[att.attach.filename] = true
  try {
    await deleteStageDeliverableAttachment(
      projectId,
      att.deliverableKey,
      att.stage,
      att.attach.filename
    )
    emit('reload-stage-deliverables')
  } catch (err) {
    const msg = err?.response?.data?.error || err?.message || t('toast.deleteFailed')
    showToast(`${t('deliverable.deleteAttachmentFailed')}：${msg}`, 'error')
  } finally {
    attachmentDeleting[att.attach.filename] = false
  }
}

// ============ 上传附件弹窗 ============
const uploadModal = reactive({
  visible: false,
  deliverableKey: '',
  files: [],
  uploading: false,
  error: '',
  locked: false,  // 当从 deliverable-mini-item + 按钮触发时，锁定交付物类型选择
})

const uploadFileInput = ref(null)

// 打开上传弹窗：传 item 时锁定为该交付物类型，传 null 时由用户选择
function openUploadModal(item) {
  uploadModal.visible = true
  uploadModal.uploading = false
  uploadModal.error = ''
  uploadModal.files = []
  if (item) {
    uploadModal.deliverableKey = item.key
    uploadModal.locked = true
  } else {
    uploadModal.deliverableKey = ''
    uploadModal.locked = false
  }
}

function closeUploadModal() {
  if (uploadModal.uploading) return
  uploadModal.visible = false
  uploadModal.files = []
  uploadModal.error = ''
  uploadModal.deliverableKey = ''
  uploadModal.locked = false
}

function triggerFileInput() {
  uploadFileInput.value?.click()
}

function onFileInputChange(e) {
  const fileList = e.target.files
  if (!fileList || !fileList.length) return
  const newFiles = Array.from(fileList)
  uploadModal.files = [...uploadModal.files, ...newFiles]
  // 清空 input 的 value，允许重复选择同一文件
  e.target.value = ''
}

function removeUploadFile(idx) {
  uploadModal.files.splice(idx, 1)
}

async function submitUpload() {
  const projectId = props.currentProject?.id
  const stage = props.stageDeliverables?.stage
  if (!projectId || !stage) {
    uploadModal.error = t('deliverable.noProjectOrStage')
    return
  }
  if (!uploadModal.deliverableKey) {
    uploadModal.error = t('deliverable.selectDeliverableType')
    return
  }
  if (uploadModal.files.length === 0) {
    uploadModal.error = t('deliverable.selectFilesToUpload')
    return
  }
  uploadModal.uploading = true
  uploadModal.error = ''
  try {
    await uploadStageDeliverableAttachments(
      projectId,
      uploadModal.deliverableKey,
      stage,
      uploadModal.files
    )
    emit('reload-stage-deliverables')
    closeUploadModal()
  } catch (err) {
    const msg = err?.response?.data?.error || err?.message || t('deliverable.uploadFailed')
    uploadModal.error = `${t('deliverable.uploadFailed')}：${msg}`
  } finally {
    uploadModal.uploading = false
  }
}
</script>

<style scoped>
/* ============ 右侧栏：当前阶段交付物 ============ */
.aside-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.aside-block {
  padding: 12px 0;
  border-bottom: 1px solid var(--border);
}

.aside-block:first-child {
  padding-top: 0;
}

.aside-block:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.aside-block-title {
  font-size: var(--fs-xs);
  font-weight: 700;
  color: var(--text-secondary);
  font-family: var(--font-mono);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 8px;
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.completion-num {
  font-family: 'JetBrains Mono', monospace;
  font-size: var(--fs-sm);
  color: var(--text-primary);
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  margin-left: auto;
}

/* 阶段检查按钮：描边风格，与实心"上传附件"按钮区分 */
.run-stage-check-btn {
  appearance: none;
  display: inline-flex;
  align-items: center;
  gap: 3px;
  background: transparent;
  border: 1px solid var(--accent);
  border-radius: 10px;
  color: var(--accent);
  cursor: pointer;
  font-family: var(--font-sans);
  font-size: 10px;
  font-weight: 600;
  padding: 2px 8px;
  letter-spacing: 0.02em;
  transition: background 0.15s, color 0.15s, transform 0.12s;
}

.run-stage-check-btn:hover:not(:disabled) {
  background: var(--accent);
  color: #fff;
}

.run-stage-check-btn:focus-visible {
  outline: 2px solid var(--focus-ring);
  outline-offset: 2px;
}

.run-stage-check-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.run-stage-check-btn .run-check-icon {
  font-size: 10px;
  font-weight: 700;
  line-height: 1;
}

/* 区块1：阶段说明 */
.stage-om-badge {
  display: inline-block;
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  padding: 2px 8px;
  border: 1px solid var(--accent);
  border-radius: 12px;
  color: var(--accent);
  background: rgba(205, 80, 54, 0.08);
  margin-bottom: 8px;
}

.stage-objective {
  font-size: var(--fs-sm);
  color: var(--text-primary);
  line-height: var(--lh-base);
  margin-bottom: 10px;
}

.stage-conditions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.condition-group {
  border-left: 2px solid var(--border-strong);
  padding-left: 8px;
}

.condition-label {
  font-size: var(--fs-xs);
  font-weight: 600;
  color: var(--text-muted);
  margin-bottom: 4px;
}

.condition-group ul {
  margin: 0;
  padding-left: 16px;
  font-size: var(--fs-xs);
  color: var(--text-secondary);
  line-height: 1.55;
}

.condition-empty {
  font-size: var(--fs-xs);
  color: var(--text-muted);
  font-style: italic;
}

/* 区块2：交付物检查情况 */
.completion-bar {
  height: 6px;
  background: var(--border);
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 10px;
}

.completion-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.4s ease-out;
}

.completion-fill.progress-ok { background: var(--green); }
.completion-fill.progress-warn { background: var(--yellow); }
.completion-fill.progress-danger { background: var(--red); }

.deliverable-mini-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.deliverable-mini-group {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.deliverable-mini-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--fs-xs);
  color: var(--text-primary);
  min-width: 0;
}

.deliverable-mini-item .status-dot {
  font-size: 10px;
  color: var(--text-muted);
  flex-shrink: 0;
  line-height: 1;
}

.deliverable-mini-item .status-dot.completed {
  color: var(--green);
}

.deliverable-mini-item .status-dot.optional {
  color: var(--yellow);
}

.deliverable-mini-item .item-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 区块3：阶段任务 */
.stage-task-details {
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg-surface);
  overflow: hidden;
  margin-bottom: 6px;
}

.stage-task-details:last-child {
  margin-bottom: 0;
}

.stage-task-summary {
  padding: 6px 10px;
  cursor: pointer;
  font-size: var(--fs-xs);
  font-weight: 600;
  color: var(--text-primary);
  list-style: none;
  user-select: none;
  transition: background 0.15s;
}

.stage-task-summary::-webkit-details-marker {
  display: none;
}

.stage-task-summary::before {
  content: '▸';
  display: inline-block;
  margin-right: 6px;
  color: var(--text-muted);
  transition: transform 0.2s;
}

.stage-task-details[open] .stage-task-summary::before {
  transform: rotate(90deg);
}

.stage-task-summary:hover {
  background: var(--bg-card);
}

.stage-task-sublist {
  margin: 0;
  padding: 2px 10px 8px 28px;
  font-size: var(--fs-xs);
  color: var(--text-secondary);
  line-height: 1.55;
}

.stage-task-sublist li {
  margin-bottom: 2px;
}

/* 右侧栏骨架屏与空状态 */
.aside-skeleton {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.aside-skel-line {
  height: 12px;
  background: linear-gradient(90deg, var(--border) 25%, var(--bg-surface) 50%, var(--border) 75%);
  background-size: 200% 100%;
  border-radius: 4px;
  animation: aside-shimmer 1.4s ease-in-out infinite;
}

.aside-skel-line.w70 { width: 70%; }
.aside-skel-line.w40 { width: 40%; }

.aside-skel-block {
  height: 50px;
  background: linear-gradient(90deg, var(--border) 25%, var(--bg-surface) 50%, var(--border) 75%);
  background-size: 200% 100%;
  border-radius: 6px;
  animation: aside-shimmer 1.4s ease-in-out infinite;
}

@keyframes aside-shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.aside-empty {
  text-align: center;
  padding: 24px 12px;
  color: var(--text-muted);
  font-size: var(--fs-sm);
  font-style: italic;
}

@media (prefers-reduced-motion: reduce) {
  .completion-fill,
  .aside-skel-line,
  .aside-skel-block {
    transition: none;
    animation: none;
  }
}

/* ============ 交付物手工勾选 checkbox ============ */
.deliverable-mini-item {
  padding: 2px 0;
  transition: background 0.12s;
  border-radius: 4px;
}

.deliverable-mini-item.manual-completed {
  background: rgba(17, 138, 88, 0.05);
}

.deliverable-checkbox {
  display: inline-flex;
  align-items: center;
  cursor: pointer;
  margin: 0;
  padding: 0;
  flex-shrink: 0;
}

.deliverable-checkbox input[type="checkbox"] {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
  margin: 0;
}

.checkbox-mark {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 1.5px solid var(--border-strong);
  border-radius: 50%;
  background: var(--bg-card);
  position: relative;
  transition: border-color 0.15s, background 0.15s, transform 0.12s;
}

.checkbox-mark.completed {
  border-color: var(--green);
  background: var(--green);
}

.checkbox-mark.optional {
  border-color: var(--yellow);
}

.checkbox-mark.manual {
  border-color: var(--accent);
  background: var(--accent);
}

.checkbox-mark.manual::after {
  content: '';
  position: absolute;
  left: 3.5px;
  top: 1px;
  width: 4px;
  height: 7px;
  border: solid #fff;
  border-width: 0 1.5px 1.5px 0;
  transform: rotate(45deg);
}

.checkbox-mark.completed::after {
  content: '';
  position: absolute;
  left: 3.5px;
  top: 1px;
  width: 4px;
  height: 7px;
  border: solid #fff;
  border-width: 0 1.5px 1.5px 0;
  transform: rotate(45deg);
}

.deliverable-checkbox:hover .checkbox-mark {
  transform: scale(1.15);
}

.deliverable-checkbox input[type="checkbox"]:focus-visible + .checkbox-mark {
  outline: 2px solid var(--focus-ring);
  outline-offset: 2px;
}

.deliverable-checkbox input[type="checkbox"]:disabled + .checkbox-mark {
  opacity: 0.55;
  cursor: not-allowed;
}

/* 附件计数徽章 / 上传 + 按钮 */
.attach-count-badge {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 1px 6px;
  font-size: 10px;
  color: var(--accent);
  background: rgba(205, 80, 54, 0.08);
  border: 1px solid rgba(205, 80, 54, 0.2);
  border-radius: 8px;
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  flex-shrink: 0;
  margin-left: auto;
  cursor: default;
}

.attach-count-icon {
  font-size: 9px;
  line-height: 1;
}

.attach-count-num {
  font-weight: 600;
}

.attach-add-btn {
  appearance: none;
  background: transparent;
  border: 1px dashed var(--border-strong);
  border-radius: 8px;
  color: var(--text-muted);
  cursor: pointer;
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 700;
  width: 18px;
  height: 16px;
  line-height: 1;
  padding: 0;
  margin-left: auto;
  flex-shrink: 0;
  transition: border-color 0.15s, color 0.15s, background 0.15s;
}

.attach-add-btn:hover {
  border-color: var(--accent);
  color: var(--accent);
  background: rgba(205, 80, 54, 0.06);
  border-style: solid;
}

.attach-add-btn:focus-visible {
  outline: 2px solid var(--focus-ring);
  outline-offset: 2px;
}

/* ============ 交付物附件清单 block ============ */
.attachment-block {
  padding-bottom: 0;
}

.attach-total-num {
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
  margin-left: auto;
  font-weight: 600;
}

.upload-btn {
  appearance: none;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: var(--accent);
  border: none;
  border-radius: 10px;
  color: #fff;
  cursor: pointer;
  font-family: var(--font-sans);
  font-size: 10px;
  font-weight: 600;
  padding: 3px 8px;
  letter-spacing: 0.02em;
  margin-left: 6px;
  transition: background 0.15s, transform 0.12s;
}

.upload-btn:hover {
  background: var(--accent-hover);
}

.upload-btn:focus-visible {
  outline: 2px solid var(--focus-ring);
  outline-offset: 2px;
}

.upload-btn .upload-icon {
  font-size: 11px;
  font-weight: 700;
  line-height: 1;
}

.attach-empty {
  font-size: var(--fs-xs);
  color: var(--text-muted);
  font-style: italic;
  line-height: 1.5;
  padding: 6px 0;
}

.attach-list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.attach-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 6px 8px;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 6px;
  transition: border-color 0.15s, background 0.15s;
}

.attach-item:hover {
  border-color: var(--border-strong);
}

.attach-item-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.attach-item-name {
  font-size: var(--fs-xs);
  color: var(--text-primary);
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.attach-item-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.attach-deliverable-tag {
  font-size: 10px;
  color: var(--accent);
  background: rgba(205, 80, 54, 0.08);
  border: 1px solid rgba(205, 80, 54, 0.15);
  border-radius: 8px;
  padding: 1px 6px;
  font-weight: 500;
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.attach-size {
  font-size: 10px;
  color: var(--text-muted);
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}

.attach-date {
  font-size: 10px;
  color: var(--text-muted);
  font-family: var(--font-mono);
}

.attach-item-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.attach-action-btn {
  appearance: none;
  font-family: var(--font-sans);
  font-size: 10px;
  padding: 2px 8px;
  border-radius: 8px;
  cursor: pointer;
  text-decoration: none;
  transition: background 0.15s, color 0.15s, border-color 0.15s;
  border: 1px solid transparent;
}

.attach-download-btn {
  color: var(--accent);
  background: rgba(205, 80, 54, 0.06);
  border-color: rgba(205, 80, 54, 0.2);
}

.attach-download-btn:hover {
  background: var(--accent);
  color: #fff;
  border-color: var(--accent);
}

.attach-delete-btn {
  color: var(--text-muted);
  background: transparent;
  border-color: var(--border);
}

.attach-delete-btn:hover:not(:disabled) {
  color: var(--red);
  background: var(--red-light);
  border-color: var(--red);
}

.attach-delete-btn:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.attach-action-btn:focus-visible {
  outline: 2px solid var(--focus-ring);
  outline-offset: 1px;
}

/* ============ 上传附件弹窗 ============ */
.upload-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(21, 23, 29, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.upload-modal {
  background: var(--bg-card, #FCFBF5);
  border: 1px solid var(--border, #E8E8E0);
  border-radius: 10px;
  width: 100%;
  max-width: 520px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 12px 40px rgba(21, 23, 29, 0.15);
}

.upload-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  border-bottom: 1px solid var(--border, #E8E8E0);
}

.upload-modal-title {
  margin: 0;
  font-size: var(--fs-md, 14px);
  font-weight: 600;
  color: var(--text-primary, #15171D);
  font-family: var(--font-sans);
}

.upload-modal-close {
  appearance: none;
  background: transparent;
  border: none;
  color: var(--text-muted, #93959D);
  cursor: pointer;
  font-size: 22px;
  line-height: 1;
  padding: 0 4px;
  font-family: var(--font-sans);
}

.upload-modal-close:hover {
  color: var(--text-primary, #15171D);
}

.upload-modal-close:focus-visible {
  outline: 2px solid var(--focus-ring, #15171D);
  outline-offset: 2px;
  border-radius: 2px;
}

.upload-modal-body {
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  overflow-y: auto;
}

.upload-form-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.upload-form-label {
  font-size: var(--fs-sm, 12px);
  font-weight: 600;
  color: var(--text-secondary, #494A4D);
}

.upload-form-label .required {
  color: var(--accent, #CD5036);
  margin-left: 2px;
}

.upload-form-select {
  appearance: auto;
  font-family: var(--font-sans);
  font-size: var(--fs-base, 13px);
  color: var(--text-primary, #15171D);
  background: var(--bg-surface, #F8F4EC);
  border: 1px solid var(--border-strong, #D7D4CD);
  border-radius: 6px;
  padding: 8px 10px;
  cursor: pointer;
}

.upload-form-select:focus {
  outline: none;
  border-color: var(--accent, #CD5036);
  box-shadow: 0 0 0 2px rgba(205, 80, 54, 0.12);
}

.upload-form-select:disabled {
  opacity: 0.65;
  cursor: not-allowed;
  background: var(--bg-base, #F4F0E7);
}

.upload-file-dropzone {
  position: relative;
  border: 1.5px dashed var(--border-strong, #D7D4CD);
  border-radius: 8px;
  padding: 14px 12px;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
  min-height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.upload-file-dropzone:hover {
  border-color: var(--accent, #CD5036);
  background: rgba(205, 80, 54, 0.04);
}

.upload-file-input {
  position: absolute;
  inset: 0;
  opacity: 0;
  cursor: pointer;
  width: 100%;
  height: 100%;
}

.upload-file-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  color: var(--text-muted, #93959D);
  font-size: var(--fs-sm, 12px);
  pointer-events: none;
}

.upload-file-placeholder .upload-icon {
  font-size: 22px;
  font-weight: 700;
  color: var(--accent, #CD5036);
  line-height: 1;
}

.upload-file-list {
  margin: 0;
  padding: 0;
  list-style: none;
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 4px;
  pointer-events: auto;
  position: relative;
  z-index: 1;
}

.upload-file-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  background: var(--bg-card, #FCFBF5);
  border: 1px solid var(--border, #E8E8E0);
  border-radius: 4px;
}

.upload-file-name {
  flex: 1;
  min-width: 0;
  font-size: var(--fs-xs, 11px);
  color: var(--text-primary, #15171D);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.upload-file-size {
  font-size: 10px;
  color: var(--text-muted, #93959D);
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}

.upload-file-remove {
  appearance: none;
  background: transparent;
  border: none;
  color: var(--text-muted, #93959D);
  cursor: pointer;
  font-size: 16px;
  line-height: 1;
  padding: 0 4px;
}

.upload-file-remove:hover {
  color: var(--red, #C4391C);
}

.upload-form-hint {
  margin: 2px 0 0;
  font-size: 10px;
  color: var(--text-muted, #93959D);
  font-style: italic;
}

.upload-form-error {
  margin: 0;
  padding: 6px 10px;
  font-size: var(--fs-xs, 11px);
  color: var(--red, #C4391C);
  background: rgba(196, 57, 28, 0.08);
  border-left: 2px solid var(--red, #C4391C);
  border-radius: 2px;
}

.upload-modal-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  padding: 12px 20px;
  border-top: 1px solid var(--border, #E8E8E0);
}

.upload-cancel-btn,
.upload-submit-btn {
  appearance: none;
  font-family: var(--font-sans);
  font-size: var(--fs-sm, 12px);
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

.upload-cancel-btn {
  background: transparent;
  border-color: var(--border-strong, #D7D4CD);
  color: var(--text-secondary, #494A4D);
}

.upload-cancel-btn:hover:not(:disabled) {
  background: var(--bg-surface, #F8F4EC);
  border-color: var(--text-muted, #93959D);
}

.upload-cancel-btn:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.upload-submit-btn {
  background: var(--accent, #CD5036);
  color: #fff;
  border-color: var(--accent, #CD5036);
}

.upload-submit-btn:hover:not(:disabled) {
  background: var(--accent-hover, #C4391C);
  border-color: var(--accent-hover, #C4391C);
}

.upload-submit-btn:disabled {
  cursor: not-allowed;
  opacity: 0.55;
  background: var(--text-muted, #93959D);
  border-color: var(--text-muted, #93959D);
}

.upload-submit-btn:focus-visible,
.upload-cancel-btn:focus-visible {
  outline: 2px solid var(--focus-ring, #15171D);
  outline-offset: 2px;
}

.upload-spinner {
  display: inline-block;
  width: 10px;
  height: 10px;
  border: 1.5px solid rgba(255, 255, 255, 0.4);
  border-top-color: #fff;
  border-radius: 50%;
  animation: upload-spin 0.8s linear infinite;
}

@keyframes upload-spin {
  to { transform: rotate(360deg); }
}

@media (prefers-reduced-motion: reduce) {
  .upload-spinner {
    animation: none;
  }
  .checkbox-mark,
  .attach-action-btn,
  .upload-btn,
  .attach-add-btn {
    transition: none;
  }
}
</style>

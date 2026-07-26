<template>
  <div class="settings-panel">
    <!-- 页面标题 -->
    <header class="page-header">
      <div class="header-left">
        <span class="section-deco" aria-hidden="true">◇</span>
        <h1 class="page-title">{{ t('settings.title') }}</h1>
      </div>
    </header>

    <!-- 加载状态 -->
    <div v-if="loading" class="settings-loading" role="status" aria-live="polite">
      <div class="skel-block"></div>
      <div class="skel-block"></div>
      <div class="skel-block"></div>
    </div>

    <template v-else>
      <!-- 分区 1：LLM 配置 -->
      <section class="settings-card">
        <div class="card-header">
          <span class="section-deco" aria-hidden="true">◇</span>
          <h2 class="card-title">{{ t('settings.llmConfig') }}</h2>
        </div>
        <div class="card-body">
          <div class="form-group">
            <label class="field-label" for="settings-llm-key">{{ t('settings.apiKey') }}</label>
            <input
              id="settings-llm-key"
              type="password"
              v-model="form.llm_api_key"
              :placeholder="apiKeyPlaceholder"
              class="form-input"
              autocomplete="off"
            >
          </div>
          <div class="form-group">
            <label class="field-label" for="settings-llm-url">{{ t('settings.baseUrl') }}</label>
            <input
              id="settings-llm-url"
              type="text"
              v-model="form.llm_base_url"
              placeholder="https://api.longcat.chat/openai"
              class="form-input"
              autocomplete="off"
            >
          </div>
          <div class="form-group">
            <label class="field-label" for="settings-llm-model">{{ t('settings.modelName') }}</label>
            <input
              id="settings-llm-model"
              type="text"
              v-model="form.llm_model_name"
              placeholder="LongCat-2.0"
              class="form-input"
              autocomplete="off"
            >
          </div>
          <p class="card-hint">{{ t('settings.llmConfigHint') }}</p>
        </div>
      </section>

      <!-- 分区 2：公司信息 -->
      <section class="settings-card">
        <div class="card-header">
          <span class="section-deco" aria-hidden="true">◇</span>
          <h2 class="card-title">{{ t('settings.companyInfo') }}</h2>
        </div>
        <div class="card-body">
          <div class="form-group">
            <label class="field-label" for="settings-company-name">{{ t('settings.companyName') }}</label>
            <input
              id="settings-company-name"
              type="text"
              v-model="form.company_name"
              :placeholder="t('settings.companyName')"
              class="form-input"
              autocomplete="off"
            >
          </div>
          <div class="form-group">
            <label class="field-label" for="settings-company-intro">{{ t('settings.companyIntro') }}</label>
            <textarea
              id="settings-company-intro"
              v-model="form.company_intro"
              rows="5"
              :placeholder="t('settings.companyIntro')"
              class="form-textarea"
            ></textarea>
          </div>
          <div class="form-group">
            <label class="field-label" for="settings-product-intro">{{ t('settings.productIntro') }}</label>
            <textarea
              id="settings-product-intro"
              v-model="form.product_intro"
              rows="5"
              :placeholder="t('settings.productIntro')"
              class="form-textarea"
            ></textarea>
          </div>
          <p class="card-hint">{{ t('settings.companyInfoHint') }}</p>
        </div>
      </section>

      <!-- 分区 3：产品资料附件 -->
      <section class="settings-card">
        <div class="card-header">
          <span class="section-deco" aria-hidden="true">◇</span>
          <h2 class="card-title">{{ t('settings.productDocs') }}</h2>
          <button
            type="button"
            class="btn-secondary btn-sm upload-btn"
            :disabled="uploading"
            @click="triggerFileInput"
          >
            <span v-if="uploading" class="btn-spinner" aria-hidden="true"></span>
            {{ uploading ? t('common.upload') + '…' : '+ ' + t('settings.uploadDoc') }}
          </button>
          <input
            ref="fileInputRef"
            type="file"
            accept=".pdf,.md,.txt"
            class="file-input-hidden"
            @change="handleFileSelect"
          >
        </div>
        <div class="card-body">
          <div v-if="attachments.length === 0" class="attachments-empty">
            {{ t('settings.noDocs') }}
          </div>
          <ul v-else class="attachments-list">
            <li
              v-for="item in attachments"
              :key="item.id"
              class="attachment-item"
            >
              <div class="attachment-info">
                <span class="attachment-name" :title="item.file_name">{{ item.file_name }}</span>
                <span class="attachment-meta">
                  <span class="meta-size">{{ formatFileSize(item.file_size) }}</span>
                  <span class="meta-dot">·</span>
                  <span class="meta-date">{{ formatDate(item.uploaded_at) }}</span>
                </span>
              </div>
              <div class="attachment-actions">
                <button
                  type="button"
                  class="card-action-btn edit-btn"
                  @click="handleDownload(item.id)"
                >{{ t('common.download') }}</button>
                <button
                  type="button"
                  class="card-action-btn delete-btn"
                  :disabled="deletingId === item.id"
                  @click="handleDeleteAttachment(item)"
                >
                  <span v-if="deletingId === item.id" class="btn-spinner" aria-hidden="true"></span>
                  {{ t('common.delete') }}
                </button>
              </div>
            </li>
          </ul>
          <p class="card-hint">{{ t('settings.docsHint') }}</p>
        </div>
      </section>

      <!-- 底部操作栏 -->
      <footer class="settings-footer">
        <button
          type="button"
          class="btn-primary"
          :disabled="saving"
          @click="handleSave"
        >
          <span v-if="saving" class="btn-spinner" aria-hidden="true"></span>
          {{ saving ? t('common.saving') : t('common.save') }}
        </button>
      </footer>
    </template>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  getSettings,
  updateSettings,
  uploadCompanyAttachment,
  deleteCompanyAttachment,
  getCompanyAttachmentDownloadUrl,
} from '../../api/salesTwin'
import { showToast, requestConfirm } from '../../composables/salesTwin/useConfirmToast'

const { t } = useI18n()

const loading = ref(false)
const saving = ref(false)
const uploading = ref(false)
const deletingId = ref(null)
const fileInputRef = ref(null)

const form = reactive({
  company_name: '',
  company_intro: '',
  product_intro: '',
  llm_api_key: '',
  llm_base_url: '',
  llm_model_name: '',
})

// 后端返回的脱敏 API Key 标志：'已配置' | null
const apiKeyMasked = ref(null)
const apiKeyPlaceholder = computed(() => {
  return apiKeyMasked.value === '已配置'
    ? t('settings.apiKeyConfigured')
    : t('settings.apiKey')
})

const attachments = ref([])

const formatFileSize = (bytes) => {
  if (!bytes) return '-'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

const formatDate = (iso) => {
  if (!iso) return '-'
  const d = new Date(iso)
  if (isNaN(d.getTime())) return '-'
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

async function loadSettings() {
  loading.value = true
  try {
    const res = await getSettings()
    const profile = res.profile || {}
    form.company_name = profile.company_name || ''
    form.company_intro = profile.company_intro || ''
    form.product_intro = profile.product_intro || ''
    form.llm_base_url = profile.llm_base_url || ''
    form.llm_model_name = profile.llm_model_name || ''
    // 脱敏 API Key 仅用于 placeholder 提示，input 始终留空
    apiKeyMasked.value = profile.llm_api_key || null
    form.llm_api_key = ''
    attachments.value = Array.isArray(res.attachments) ? res.attachments : []
  } catch (err) {
    const msg = err?.response?.data?.error || err?.message || t('toast.loadFailed')
    showToast(t('toast.loadFailed') + '：' + msg, 'error')
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  if (saving.value) return
  saving.value = true
  try {
    const payload = {
      company_name: form.company_name,
      company_intro: form.company_intro,
      product_intro: form.product_intro,
      llm_base_url: form.llm_base_url,
      llm_model_name: form.llm_model_name,
    }
    // API Key 留空时不覆盖（后端忽略空字符串/'已配置'）
    const key = (form.llm_api_key || '').trim()
    if (key) {
      payload.llm_api_key = key
    } else {
      payload.llm_api_key = ''
    }
    await updateSettings(payload)
    // 保存后重置脱敏标志：若用户输入了新 key，后端会返回 '已配置'
    await loadSettings()
    showToast(t('toast.saveSuccess'), 'success')
  } catch (err) {
    const msg = err?.response?.data?.error || err?.message || t('toast.saveFailed')
    showToast(t('toast.saveFailed') + '：' + msg, 'error')
  } finally {
    saving.value = false
  }
}

function triggerFileInput() {
  if (uploading.value) return
  fileInputRef.value?.click()
}

async function handleFileSelect(e) {
  const file = e.target.files?.[0]
  // 清空 input 的 value，允许重复上传同名文件
  e.target.value = ''
  if (!file) return
  // 简单类型校验：.pdf / .md / .txt
  const name = file.name.toLowerCase()
  if (!/\.(pdf|md|txt)$/.test(name)) {
    showToast(t('settings.docFormats'), 'warning')
    return
  }
  uploading.value = true
  try {
    await uploadCompanyAttachment(file)
    showToast(t('toast.operationSuccess'), 'success')
    await loadSettings()
  } catch (err) {
    const msg = err?.response?.data?.error || err?.message || t('toast.operationFailed')
    showToast(t('toast.operationFailed') + '：' + msg, 'error')
  } finally {
    uploading.value = false
  }
}

function handleDownload(id) {
  window.open(getCompanyAttachmentDownloadUrl(id), '_blank')
}

async function handleDeleteAttachment(item) {
  if (deletingId.value) return
  const confirmed = await requestConfirm({
    title: t('modal.deleteTitle'),
    message: t('modal.deleteMessage'),
    confirmText: t('modal.deleteButton'),
    danger: true,
  })
  if (!confirmed) return
  deletingId.value = item.id
  try {
    await deleteCompanyAttachment(item.id)
    showToast(t('toast.deleteSuccess'), 'success')
    await loadSettings()
  } catch (err) {
    const msg = err?.response?.data?.error || err?.message || t('toast.deleteFailed')
    showToast(t('toast.deleteFailed') + '：' + msg, 'error')
  } finally {
    deletingId.value = null
  }
}

onMounted(() => {
  loadSettings()
})
</script>

<style scoped>
.settings-panel {
  max-width: 820px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* 页面标题 */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--divider);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.section-deco {
  color: var(--accent);
  font-size: var(--fs-md);
  font-weight: 300;
}

.page-title {
  font-size: var(--fs-xl);
  font-weight: 700;
  margin: 0;
  letter-spacing: -0.01em;
  color: var(--text-primary);
}

/* 加载骨架 */
.settings-loading {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.skel-block {
  height: 120px;
  background: linear-gradient(90deg, var(--border) 25%, var(--bg-surface) 50%, var(--border) 75%);
  background-size: 200% 100%;
  border-radius: 10px;
  animation: skel-shimmer 1.4s ease-in-out infinite;
}

@keyframes skel-shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* 卡片分区 */
.settings-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 10px;
  box-shadow: var(--shadow-sm);
  overflow: hidden;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 20px;
  border-bottom: 1px solid var(--border);
  background: var(--bg-surface);
}

.card-title {
  flex: 1;
  margin: 0;
  font-size: var(--fs-md);
  font-weight: 600;
  color: var(--text-primary);
  font-family: var(--font-sans);
}

.card-body {
  padding: 18px 20px 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field-label {
  font-size: var(--fs-xs);
  font-weight: 600;
  color: var(--text-tertiary);
  font-family: var(--font-mono);
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.form-input {
  appearance: none;
  font-family: var(--font-sans);
  font-size: var(--fs-base);
  color: var(--text-primary);
  background: var(--bg-surface);
  border: 1px solid var(--border-strong);
  border-radius: 6px;
  padding: 8px 10px;
  transition: border-color 0.15s, box-shadow 0.15s;
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
  padding: 8px 10px;
  resize: vertical;
  min-height: 90px;
  line-height: 1.55;
  transition: border-color 0.15s, box-shadow 0.15s;
}

.form-textarea:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 2px rgba(205, 80, 54, 0.12);
}

.card-hint {
  margin: 4px 0 0;
  font-size: var(--fs-xs);
  color: var(--text-muted);
  line-height: 1.5;
}

/* 上传按钮 */
.upload-btn {
  flex-shrink: 0;
}

.btn-sm {
  padding: 5px 12px;
  font-size: var(--fs-xs);
}

.file-input-hidden {
  display: none;
}

/* 附件列表 */
.attachments-empty {
  font-size: var(--fs-xs);
  color: var(--text-muted);
  font-style: italic;
  padding: 8px 0;
}

.attachments-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.attachment-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 6px;
  transition: border-color 0.15s;
}

.attachment-item:hover {
  border-color: var(--border-strong);
}

.attachment-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.attachment-name {
  font-size: var(--fs-sm);
  font-weight: 600;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.attachment-meta {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: var(--fs-xs);
  color: var(--text-muted);
  font-family: var(--font-mono);
}

.meta-dot {
  opacity: 0.5;
}

.attachment-actions {
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
  display: inline-flex;
  align-items: center;
  gap: 3px;
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

/* 底部操作栏 */
.settings-footer {
  display: flex;
  justify-content: flex-end;
  padding-top: 4px;
}

.btn-primary {
  appearance: none;
  font-family: var(--font-sans);
  font-size: var(--fs-sm);
  font-weight: 600;
  padding: 8px 20px;
  border-radius: 6px;
  cursor: pointer;
  border: 1px solid transparent;
  background: var(--accent);
  color: #fff;
  border-color: var(--accent);
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: background 0.15s, border-color 0.15s, opacity 0.15s;
}

.btn-primary:hover:not(:disabled) {
  background: var(--accent-hover);
  border-color: var(--accent-hover);
}

.btn-primary:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.btn-primary:focus-visible {
  outline: 2px solid var(--focus-ring);
  outline-offset: 2px;
}

.btn-secondary {
  appearance: none;
  font-family: var(--font-sans);
  font-size: var(--fs-sm);
  font-weight: 600;
  padding: 6px 14px;
  border-radius: 6px;
  cursor: pointer;
  background: transparent;
  color: var(--text-secondary);
  border: 1px solid var(--border-strong);
  display: inline-flex;
  align-items: center;
  gap: 4px;
  transition: background 0.15s, border-color 0.15s, color 0.15s, opacity 0.15s;
}

.btn-secondary:hover:not(:disabled) {
  background: var(--bg-surface);
  border-color: var(--text-muted);
  color: var(--text-primary);
}

.btn-secondary:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.btn-secondary:focus-visible {
  outline: 2px solid var(--focus-ring);
  outline-offset: 2px;
}

.btn-spinner {
  display: inline-block;
  width: 10px;
  height: 10px;
  border: 1.5px solid rgba(255, 255, 255, 0.4);
  border-top-color: currentColor;
  border-radius: 50%;
  animation: btn-spin 0.8s linear infinite;
}

.btn-secondary .btn-spinner {
  border-color: rgba(73, 74, 77, 0.3);
  border-top-color: var(--text-secondary);
}

@keyframes btn-spin {
  to { transform: rotate(360deg); }
}

@media (prefers-reduced-motion: reduce) {
  .btn-spinner,
  .skel-block {
    animation: none;
  }
}
</style>

<template>
  <div class="report-overlay">
    <!-- 顶部导航栏 -->
    <header class="sr-header">
      <div class="sr-header-left">
        <button type="button" class="sr-back-btn" @click="$emit('close')" :aria-label="t('common.back')">
          <span aria-hidden="true">←</span>
          <span>{{ t('simulation.backToSimulation') }}</span>
        </button>
      </div>
      <div class="sr-header-center">
        <span class="sr-title">{{ t('simulation.report') }}</span>
      </div>
      <div class="sr-header-right">
        <button type="button" class="sr-suggestion-btn" @click="$emit('open-suggestions')" :aria-label="t('simulation.openSuggestionPool')">
          <svg viewBox="0 0 16 16" width="13" height="13" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
            <rect x="2" y="3" width="12" height="11" rx="1"/>
            <line x1="2" y1="6" x2="14" y2="6"/>
            <line x1="5" y1="1" x2="5" y2="4"/>
            <line x1="11" y1="1" x2="11" y2="4"/>
          </svg>
          <span>{{ t('simulation.suggestionPool') }}</span>
        </button>
        <span class="sr-step-indicator">Step 4/5</span>
      </div>
    </header>

    <main class="sr-main">
      <!-- 左面板：报告渲染 -->
      <div class="sr-left-panel" ref="leftPanel">
        <!-- 加载中 -->
        <div v-if="generating" class="sr-loading">
          <div class="sr-loading-rings">
            <div class="sr-ring"></div>
            <div class="sr-ring"></div>
            <div class="sr-ring"></div>
          </div>
          <p class="sr-loading-text">{{ t('simulation.generatingReport') }}</p>
        </div>

        <!-- 报告内容 -->
        <div v-else-if="report" class="sr-report-content" @mouseup="handleReportMouseUp">
          <!-- 报告头部 -->
          <div class="sr-report-header">
            <div class="sr-report-meta">
              <span class="sr-report-tag">Prediction Report</span>
              <span class="sr-report-id">ID: {{ report.id || 'REF-2024-X92' }}</span>
            </div>
            <h1 class="sr-main-title">{{ report.title }}</h1>
            <p class="sr-sub-title">{{ report.summary }}</p>
            <div class="sr-header-divider"></div>
          </div>

          <!-- 章节列表 -->
          <div class="sr-sections">
            <div
              v-for="(section, idx) in report.sections"
              :key="idx"
              class="sr-section"
              :class="{ collapsed: collapsedSections.has(idx) }"
            >
              <button type="button" class="sr-section-header" @click="toggleSection(idx)">
                <span class="sr-section-number">{{ String(idx + 1).padStart(2, '0') }}</span>
                <h3 class="sr-section-title">{{ section.title }}</h3>
                <span class="sr-collapse-icon" aria-hidden="true">{{ collapsedSections.has(idx) ? '▸' : '▾' }}</span>
              </button>
              <div v-show="!collapsedSections.has(idx)" class="sr-section-body">
                <p v-if="section.content" class="sr-section-text">{{ section.content }}</p>
                <ul v-if="section.bullets?.length" class="sr-section-bullets">
                  <li v-for="(b, i) in section.bullets" :key="i">{{ b }}</li>
                </ul>
              </div>
            </div>
          </div>
        </div>

        <!-- 错误态 -->
        <div v-else-if="errorMsg" class="sr-error">
          <p class="sr-error-text">{{ errorMsg }}</p>
          <button type="button" class="sr-retry-btn" @click="generateReport">{{ t('common.retry') }}</button>
        </div>
      </div>

      <!-- 右面板：推演摘要 -->
      <div class="sr-right-panel">
        <div class="sr-summary-header">
          <span class="sr-summary-title">{{ t('simulation.summary') }}</span>
        </div>

        <div v-if="fermentationResult" class="sr-summary-body">
          <!-- 趋势指标 -->
          <div class="sr-metrics">
            <div class="sr-metric">
              <span class="sr-metric-label">{{ t('simulation.initialSupport') }}</span>
              <span class="sr-metric-value">{{ fermentationResult.trend?.initial_avg?.toFixed(1) || '-' }}</span>
            </div>
            <div class="sr-metric">
              <span class="sr-metric-label">{{ t('simulation.finalSupport') }}</span>
              <span class="sr-metric-value">{{ fermentationResult.trend?.final_avg?.toFixed(1) || '-' }}</span>
            </div>
            <div class="sr-metric">
              <span class="sr-metric-label">{{ t('simulation.trend') }}</span>
              <span class="sr-metric-value" :class="fermentationResult.trend?.change > 0 ? 'up' : 'down'">
                {{ fermentationResult.trend?.change > 0 ? '+' : '' }}{{ fermentationResult.trend?.change?.toFixed(1) || '0' }}
              </span>
            </div>
            <div class="sr-metric">
              <span class="sr-metric-label">{{ t('simulation.diffusionRounds') }}</span>
              <span class="sr-metric-value">{{ t('simulation.roundsValue', { count: fermentationResult.rounds || fermentationResult.days || '-' }) }}</span>
            </div>
          </div>

          <!-- 结论 -->
          <div class="sr-conclusion-box">
            <span class="sr-conclusion-label">{{ t('simulation.conclusion') }}</span>
            <p class="sr-conclusion-text">{{ fermentationResult.conclusion }}</p>
          </div>

          <!-- 互动统计 -->
          <div v-if="fermentationResult.narrative_history?.length" class="sr-interactions-box">
            <span class="sr-box-label">{{ t('simulation.keyInteractions', { count: totalInteractions }) }}</span>
            <div class="sr-interaction-list">
              <div
                v-for="(nh, idx) in fermentationResult.narrative_history"
                :key="idx"
                class="sr-day-summary"
              >
                <span class="sr-day-label">{{ nh.label }}</span>
                <div v-if="nh.interactions?.length" class="sr-day-interactions">
                  <div v-for="(it, i) in nh.interactions.slice(0, 3)" :key="i" class="sr-int-item">
                    <span class="sr-int-actor">{{ it.actor }}</span>
                    <span class="sr-int-action">{{ it.action }}</span>
                  </div>
                  <span v-if="nh.interactions.length > 3" class="sr-int-more">{{ t('simulation.moreCount', { count: nh.interactions.length - 3 }) }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- 态度变化 -->
          <div v-if="allStateChanges.length" class="sr-changes-box">
            <span class="sr-box-label">{{ t('simulation.attitudeChange') }}</span>
            <div class="sr-changes-list">
              <div
                v-for="(c, i) in allStateChanges"
                :key="i"
                class="sr-change-row"
              >
                <span class="sr-change-name">{{ c.stakeholder_name }}</span>
                <span class="sr-change-val" :class="c.new_support_level > c.old_support_level ? 'up' : 'down'">
                  {{ c.old_support_level }} → {{ c.new_support_level }}
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- 操作按钮 -->
        <div class="sr-actions">
          <button type="button" class="sr-action-btn" @click="generateReport" :disabled="generating">
            <span v-if="generating" class="sr-btn-spinner" aria-hidden="true"></span>
            {{ generating ? t('common.generating') : (report ? t('simulation.regenerate') : t('simulation.generateReport')) }}
          </button>
          <button v-if="report" type="button" class="sr-action-btn primary" @click="$emit('go-interview')">
            <span>{{ t('simulation.enterInterview') }}</span>
            <span aria-hidden="true">→</span>
          </button>
        </div>
      </div>
    </main>

    <!-- 选中文字浮动采纳按钮 -->
    <Transition name="sr-popover">
      <button
        v-if="showAdoptPopover"
        type="button"
        class="sr-adopt-popover"
        :style="{ top: popoverY + 'px', left: popoverX + 'px' }"
        @click="adoptSelection"
        @mousedown.prevent
        :aria-label="t('simulation.adoptSuggestionAria')"
      >
        <span aria-hidden="true">💡</span>
        <span>{{ t('simulation.adoptSuggestion') }}</span>
      </button>
    </Transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import * as salesTwinApi from '../../api/salesTwin'

const { t } = useI18n()

const props = defineProps({
  projectId: { type: [Number, String], required: true },
  stakeholders: { type: Array, default: () => [] },
  fermentationResult: { type: Object, default: null },
  initialReport: { type: Object, default: null }
})

const emit = defineEmits(['close', 'go-interview', 'report-generated', 'open-suggestions'])

const report = ref(null)
const generating = ref(false)
const errorMsg = ref('')
const collapsedSections = ref(new Set())

// 选中文字采纳建议
const showAdoptPopover = ref(false)
const popoverX = ref(0)
const popoverY = ref(0)
const selectedText = ref('')

function handleReportMouseUp(e) {
  const selection = window.getSelection()
  const text = selection.toString().trim()
  if (text && text.length > 5 && e.target.closest('.sr-section-text, .sr-section-bullets, .sr-main-title, .sr-sub-title')) {
    selectedText.value = text
    popoverX.value = e.clientX
    popoverY.value = e.clientY - 45
    showAdoptPopover.value = true
  } else {
    showAdoptPopover.value = false
  }
}

function handleDocumentMouseDown(e) {
  if (!e.target.closest('.sr-adopt-popover')) {
    showAdoptPopover.value = false
  }
}

async function adoptSelection() {
  if (!selectedText.value || !props.projectId) return
  const text = selectedText.value
  showAdoptPopover.value = false
  window.getSelection()?.removeAllRanges()
  try {
    await salesTwinApi.addSuggestion(props.projectId, {
      content: text,
      source: 'report',
      source_context: null
    })
    const popover = document.createElement('div')
    popover.textContent = t('simulation.adoptedToPool')
    popover.style.cssText = 'position:fixed;top:20px;left:50%;transform:translateX(-50%);background:#4CAF50;color:#fff;padding:8px 20px;border-radius:6px;font-size:13px;z-index:3000;box-shadow:0 4px 12px rgba(0,0,0,0.15)'
    document.body.appendChild(popover)
    setTimeout(() => popover.remove(), 2000)
  } catch (e) {
    console.error('采纳建议失败:', e)
  }
}

const totalInteractions = computed(() => {
  if (!props.fermentationResult?.narrative_history) return 0
  return props.fermentationResult.narrative_history.reduce((sum, h) => sum + (h.interactions?.length || 0), 0)
})

const allStateChanges = computed(() => {
  if (!props.fermentationResult?.narrative_history) return []
  const changes = []
  for (const nh of props.fermentationResult.narrative_history) {
    if (nh.state_changes) changes.push(...nh.state_changes)
  }
  return changes
})

function toggleSection(idx) {
  const s = new Set(collapsedSections.value)
  if (s.has(idx)) s.delete(idx)
  else s.add(idx)
  collapsedSections.value = s
}

async function generateReport() {
  if (!props.fermentationResult) {
    errorMsg.value = t('simulation.noResultError')
    return
  }
  generating.value = true
  errorMsg.value = ''
  try {
    const res = await salesTwinApi.generateFermentationReport(
      props.projectId,
      props.fermentationResult
    )
    report.value = res
    // 通知父组件缓存报告，避免重复生成
    emit('report-generated', res)
  } catch (e) {
    errorMsg.value = t('simulation.generateFailed', { reason: e.message || t('simulation.unknownError') })
  } finally {
    generating.value = false
  }
}

onMounted(() => {
  // 若父组件已缓存报告，直接复用，避免重复调用API
  if (props.initialReport) {
    report.value = props.initialReport
  } else {
    generateReport()
  }
  document.addEventListener('mousedown', handleDocumentMouseDown)
})

onUnmounted(() => {
  document.removeEventListener('mousedown', handleDocumentMouseDown)
})
</script>

<style scoped>
.report-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  background: #fff;
  display: flex;
  flex-direction: column;
  font-family: 'Space Grotesk', 'Noto Sans SC', system-ui, sans-serif;
}

/* 顶部导航 */
.sr-header {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  border-bottom: 1px solid #EAEAEA;
  flex-shrink: 0;
}

.sr-back-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: transparent;
  border: 1px solid #EAEAEA;
  border-radius: 4px;
  font-size: 0.82rem;
  color: #333;
  cursor: pointer;
  transition: border-color 0.2s, color 0.2s;
}

.sr-back-btn:hover {
  border-color: #000;
  color: #000;
}

.sr-back-btn:focus-visible {
  outline: 2px solid #000;
  outline-offset: 1px;
}

.sr-title {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.9rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  color: #000;
}

.sr-step-indicator {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.78rem;
  color: #999;
}

/* 主体布局 */
.sr-main {
  flex: 1;
  display: flex;
  min-height: 0;
}

/* 左面板：报告渲染 */
.sr-left-panel {
  flex: 1;
  overflow-y: auto;
  padding: 40px 60px;
  border-right: 1px solid #EAEAEA;
  min-width: 0;
}

/* 加载态 */
.sr-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 24px;
  min-height: 400px;
}

.sr-loading-rings {
  position: relative;
  width: 60px;
  height: 60px;
}

.sr-ring {
  position: absolute;
  inset: 0;
  border: 2px solid #EAEAEA;
  border-top-color: #000;
  border-radius: 50%;
  animation: sr-spin 1s linear infinite;
}

.sr-ring:nth-child(2) {
  inset: 8px;
  animation-delay: 0.15s;
  border-top-color: #666;
}

.sr-ring:nth-child(3) {
  inset: 16px;
  animation-delay: 0.3s;
  border-top-color: #999;
}

@keyframes sr-spin {
  to { transform: rotate(360deg); }
}

.sr-loading-text {
  font-size: 0.85rem;
  color: #999;
  font-family: 'JetBrains Mono', monospace;
}

/* 报告头部 */
.sr-report-header {
  margin-bottom: 32px;
}

.sr-report-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.sr-report-tag {
  background: #000;
  color: #fff;
  font-size: 0.7rem;
  font-weight: 700;
  padding: 4px 8px;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  font-family: 'JetBrains Mono', monospace;
}

.sr-report-id {
  font-size: 0.7rem;
  color: #999;
  font-family: 'JetBrains Mono', monospace;
}

.sr-main-title {
  font-family: 'Times New Roman', Times, serif;
  font-size: 2.2rem;
  font-weight: 700;
  color: #111827;
  line-height: 1.2;
  letter-spacing: -0.02em;
  margin: 0 0 12px;
}

.sr-sub-title {
  font-family: 'Times New Roman', Times, serif;
  font-size: 1rem;
  color: #6B7280;
  font-style: italic;
  line-height: 1.6;
  margin: 0;
}

.sr-header-divider {
  height: 1px;
  background: #E5E7EB;
  margin-top: 24px;
}

/* 章节列表 */
.sr-sections {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.sr-section {
  border-bottom: 1px solid #F3F4F6;
}

.sr-section:last-child {
  border-bottom: none;
}

.sr-section-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px 0;
  cursor: pointer;
  transition: background-color 0.15s;
  border: none;
  background: transparent;
  font: inherit;
  text-align: left;
  width: 100%;
  color: inherit;
}

.sr-section-header:hover {
  background: #FAFAFA;
  margin: 0 -16px;
  padding: 20px 16px;
}

.sr-section-number {
  font-family: 'JetBrains Mono', monospace;
  font-size: 1rem;
  color: #9CA3AF;
  font-weight: 500;
  flex-shrink: 0;
}

.sr-section-title {
  font-family: 'Times New Roman', Times, serif;
  font-size: 1.4rem;
  font-weight: 600;
  color: #111827;
  margin: 0;
  flex: 1;
}

.sr-collapse-icon {
  font-size: 0.8rem;
  color: #9CA3AF;
  flex-shrink: 0;
}

.sr-section-body {
  padding: 0 0 20px 28px;
}

.sr-section-text {
  font-family: 'Inter', 'Noto Sans SC', system-ui, sans-serif;
  font-size: 0.88rem;
  line-height: 1.8;
  color: #374151;
  margin: 0 0 12px;
  white-space: pre-wrap;
}

.sr-section-bullets {
  margin: 8px 0 0;
  padding-left: 20px;
}

.sr-section-bullets li {
  font-size: 0.85rem;
  line-height: 1.7;
  color: #4B5563;
  margin-bottom: 4px;
}

/* 错误态 */
.sr-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  min-height: 300px;
}

.sr-error-text {
  font-size: 0.85rem;
  color: #EF4444;
  margin: 0;
}

.sr-retry-btn {
  padding: 8px 20px;
  background: #000;
  color: #fff;
  border: none;
  border-radius: 4px;
  font-size: 0.82rem;
  cursor: pointer;
}

.sr-retry-btn:focus-visible {
  outline: 2px solid #000;
  outline-offset: 2px;
}

/* 右面板：摘要 */
.sr-right-panel {
  width: 360px;
  border-left: 1px solid #EAEAEA;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.sr-summary-header {
  padding: 16px 20px;
  border-bottom: 1px solid #EAEAEA;
}

.sr-summary-title {
  font-size: 0.8rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #000;
}

.sr-summary-body {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* 指标 */
.sr-metrics {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.sr-metric {
  padding: 12px;
  background: #F9FAFB;
  border: 1px solid #F3F4F6;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.sr-metric-label {
  font-size: 0.68rem;
  color: #9CA3AF;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.sr-metric-value {
  font-size: 1.1rem;
  font-weight: 700;
  color: #111827;
  font-family: 'JetBrains Mono', monospace;
}

.sr-metric-value.up { color: #10B981; }
.sr-metric-value.down { color: #EF4444; }

/* 结论 */
.sr-conclusion-box {
  padding: 16px;
  background: #FAFAFA;
  border: 1px solid #EAEAEA;
  border-radius: 8px;
  border-left: 3px solid #000;
}

.sr-conclusion-label {
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #9CA3AF;
  font-family: 'JetBrains Mono', monospace;
}

.sr-conclusion-text {
  font-size: 0.82rem;
  line-height: 1.7;
  color: #374151;
  margin: 8px 0 0;
}

/* 互动统计 */
.sr-interactions-box {
  padding: 16px;
  background: #F9FAFB;
  border: 1px solid #F3F4F6;
  border-radius: 8px;
}

.sr-box-label {
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #9CA3AF;
  font-family: 'JetBrains Mono', monospace;
}

.sr-interaction-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 12px;
}

.sr-day-summary {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.sr-day-label {
  font-size: 0.78rem;
  font-weight: 600;
  color: #111827;
}

.sr-day-interactions {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding-left: 8px;
}

.sr-int-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.72rem;
}

.sr-int-actor {
  font-weight: 600;
  color: #374151;
}

.sr-int-action {
  color: #6B7280;
}

.sr-int-more {
  font-size: 0.68rem;
  color: #9CA3AF;
  padding-left: 8px;
}

/* 态度变化 */
.sr-changes-box {
  padding: 16px;
  background: #F9FAFB;
  border: 1px solid #F3F4F6;
  border-radius: 8px;
}

.sr-changes-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 12px;
}

.sr-change-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 8px;
  background: #fff;
  border-radius: 4px;
}

.sr-change-name {
  font-size: 0.78rem;
  font-weight: 600;
  color: #374151;
}

.sr-change-val {
  font-size: 0.75rem;
  font-family: 'JetBrains Mono', monospace;
  padding: 2px 8px;
  border-radius: 10px;
}

.sr-change-val.up {
  background: #ECFDF5;
  color: #047857;
}

.sr-change-val.down {
  background: #FEF2F2;
  color: #B91C1C;
}

/* 操作按钮 */
.sr-actions {
  padding: 16px 20px;
  border-top: 1px solid #EAEAEA;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.sr-action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 20px;
  font-size: 0.82rem;
  font-weight: 600;
  color: #111827;
  background: #F9FAFB;
  border: 1px solid #E5E7EB;
  border-radius: 8px;
  cursor: pointer;
  transition: background-color 0.2s, border-color 0.2s;
}

.sr-action-btn:hover:not(:disabled) {
  background: #F3F4F6;
  border-color: #9CA3AF;
}

.sr-action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.sr-action-btn.primary {
  background: #1F2937;
  color: #fff;
  border-color: #1F2937;
}

.sr-action-btn.primary:hover:not(:disabled) {
  background: #374151;
}

.sr-action-btn:focus-visible {
  outline: 2px solid #000;
  outline-offset: 2px;
}

.sr-btn-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(0, 0, 0, 0.2);
  border-top-color: #000;
  border-radius: 50%;
  animation: sr-spin 0.6s linear infinite;
}

/* 响应式 */
@media (max-width: 1024px) {
  .sr-left-panel {
    padding: 30px 40px;
  }
  .sr-main-title {
    font-size: 1.8rem;
  }
}

@media (max-width: 768px) {
  .sr-main {
    flex-direction: column;
  }
  .sr-right-panel {
    width: 100%;
    border-left: none;
    border-top: 1px solid #EAEAEA;
    max-height: 300px;
  }
  .sr-left-panel {
    padding: 20px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .sr-ring,
  .sr-btn-spinner {
    animation: none;
  }
}

/* 建议池入口按钮——与系统 btn-primary 风格一致 */
.sr-suggestion-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border: 1px solid #000;
  background: transparent;
  color: #000;
  border-radius: 2px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.05em;
  cursor: pointer;
  transition: background-color 0.2s, color 0.2s;
  touch-action: manipulation;
}

.sr-suggestion-btn:hover {
  background: #000;
  color: #fff;
}

.sr-suggestion-btn:focus-visible {
  outline: 2px solid #FF4500;
  outline-offset: 2px;
}

/* 选中文字浮动采纳按钮——黑底白字，hover变橙 */
.sr-adopt-popover {
  position: fixed;
  z-index: 2100;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  background: #000;
  color: #fff;
  border: none;
  border-radius: 2px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.05em;
  cursor: pointer;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25);
  transition: background-color 0.2s;
  touch-action: manipulation;
}

.sr-adopt-popover:hover {
  background: #FF4500;
}

.sr-adopt-popover:focus-visible {
  outline: 2px solid #FF4500;
  outline-offset: 2px;
}

.sr-popover-enter-active,
.sr-popover-leave-active {
  transition: opacity 0.15s, transform 0.15s;
}

.sr-popover-enter-from,
.sr-popover-leave-to {
  opacity: 0;
  transform: translateY(8px);
}

@media (prefers-reduced-motion: reduce) {
  .sr-suggestion-btn,
  .sr-adopt-popover,
  .sr-popover-enter-active,
  .sr-popover-leave-active {
    transition: none;
  }
}
</style>

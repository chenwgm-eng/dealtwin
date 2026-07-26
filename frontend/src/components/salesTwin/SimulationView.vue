<template>
  <div class="tab-pane sim-tab-pane">
    <!-- ============ 场景 A：未推演 / 重新推演中 ============ -->
    <div v-if="!fermentationResult || showInputPanel" class="sim-console-box">
      <!-- 01 / 会议纪要 -->
      <div class="sim-console-section">
        <div class="sim-console-header">
          <span class="sim-console-label">
            <span class="sim-section-num">01</span>
            <span class="sim-section-sep">/</span>
            <span class="sim-section-title">{{ t('simulation.meetingMinutes') }}</span>
          </span>
          <span class="sim-console-meta">{{ t('simulation.selectFeedbackHint') }}</span>
        </div>
        <div class="sim-seed-zone">
          <div v-if="feedbackRecords.length === 0" class="sim-seed-empty">
            {{ t('simulation.noFeedbackHint') }}
          </div>
          <div v-else class="sim-seed-list">
            <label
              v-for="record in feedbackRecords.slice(0, 8)"
              :key="record.id"
              class="sim-seed-item"
              :class="{ selected: fermentationInput.related_feedback_ids.includes(record.id) }"
            >
              <input
                type="checkbox"
                :value="record.id"
                :checked="fermentationInput.related_feedback_ids.includes(record.id)"
                :disabled="runningSim"
                @change="$emit('update:fermentationInput', {
                  ...fermentationInput,
                  related_feedback_ids: $event.target.checked
                    ? [...fermentationInput.related_feedback_ids, record.id]
                    : fermentationInput.related_feedback_ids.filter(id => id !== record.id)
                })"
              >
              <span class="sim-seed-date">{{ formatDate(record.created_at) }}</span>
              <span class="sim-seed-text">{{ record.feedback_text.substring(0, 40) }}…</span>
              <span v-if="record.total_changes" class="sim-seed-changes">{{ t('simulation.changesCount', { count: record.total_changes }) }}</span>
            </label>
          </div>
        </div>
      </div>

      <!-- 分割线 -->
      <div class="sim-console-divider"><span>{{ t('simulation.optionalBelow') }}</span></div>

      <!-- 02 / 关联任务 -->
      <div class="sim-console-section">
        <div class="sim-console-header">
          <span class="sim-console-label">
            <span class="sim-section-num">02</span>
            <span class="sim-section-sep">/</span>
            <span class="sim-section-title">{{ t('simulation.relatedTasks') }}</span>
          </span>
          <span class="sim-console-meta">{{ t('simulation.todoCount', { count: fermentationInput.related_task_ids.length }) }}</span>
        </div>

        <div v-if="tasks.length > 0" class="sim-trigger-group">
          <div class="sim-trigger-grid">
            <label v-for="task in tasks" :key="task.id" class="sim-trigger-item">
              <input
                type="checkbox"
                :value="task.id"
                :checked="fermentationInput.related_task_ids.includes(task.id)"
                :disabled="runningSim"
                @change="$emit('update:fermentationInput', {
                  ...fermentationInput,
                  related_task_ids: $event.target.checked
                    ? [...fermentationInput.related_task_ids, task.id]
                    : fermentationInput.related_task_ids.filter(id => id !== task.id)
                })"
              >
              <span class="sim-trigger-name">{{ task.title }}</span>
              <span v-if="task.status === 'completed'" class="sim-trigger-tag done">{{ t('workspace.taskStatus.completed') }}</span>
            </label>
          </div>
        </div>
      </div>

      <!-- 状态指示 + 启动按钮 -->
      <div class="sim-console-section sim-btn-section">
        <div class="sim-status-line">
          <span class="sim-status-dot" :class="{ idle: !fermentationResult && !runningSim, active: runningSim, completed: fermentationResult && !runningSim }" aria-hidden="true"></span>
          <span class="sim-status-text">{{ runningSim ? t('simulation.simulating') : (fermentationResult ? t('workspace.taskStatus.completed') : t('simulation.statusIdle')) }}</span>
          <span v-if="fermentationResult?.trend" class="sim-status-trend" :class="fermentationResult.trend.change > 0 ? 'up' : 'down'">
            {{ fermentationResult.trend.initial_avg?.toFixed(1) }} → {{ fermentationResult.trend.final_avg?.toFixed(1) }}
            ({{ fermentationResult.trend.change > 0 ? '+' : '' }}{{ fermentationResult.trend.change?.toFixed(1) }})
          </span>
        </div>
        <button
          type="button"
          class="sim-start-engine-btn"
          :class="{ pulsing: !fermentationResult && !runningSim }"
          @click="handleStartSimulation"
          :disabled="runningSim"
        >
          <span v-if="runningSim" class="sim-btn-spinner" aria-hidden="true"></span>
          <span>{{ runningSim ? t('simulation.simulating') : (fermentationResult ? t('simulation.resimulate') : t('simulation.startSimulation')) }}</span>
          <span v-if="!runningSim" class="sim-btn-arrow" aria-hidden="true">→</span>
        </button>
      </div>
    </div>

    <!-- ============ 场景 B：推演完成 ============ -->
    <template v-else>
      <!-- 顶部操作按钮组（替代 01/02） -->
      <section class="sim-actions-bar" :aria-label="t('simulation.resultActions')">
        <div class="sim-actions-info">
          <div class="sim-actions-status">
            <span class="sim-status-dot completed" aria-hidden="true"></span>
            <span class="sim-actions-text">{{ t('simulation.simulationCompleted') }}</span>
            <span v-if="fermentationResult?.trend" class="sim-actions-trend" :class="fermentationResult.trend.change > 0 ? 'up' : 'down'">
              {{ fermentationResult.trend.initial_avg?.toFixed(1) }} → {{ fermentationResult.trend.final_avg?.toFixed(1) }}
              ({{ fermentationResult.trend.change > 0 ? '+' : '' }}{{ fermentationResult.trend.change?.toFixed(1) }})
            </span>
          </div>
        </div>
        <div class="sim-actions-buttons">
          <button type="button" class="sim-action-btn primary" @click="$emit('update:showReportView', true)">
            <span class="sim-action-icon" aria-hidden="true">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
                <line x1="9" y1="13" x2="15" y2="13"/>
                <line x1="9" y1="17" x2="15" y2="17"/>
              </svg>
            </span>
            <span class="sim-action-text">{{ t('simulation.viewReport') }}</span>
          </button>
          <button type="button" class="sim-action-btn" @click="$emit('update:showInterviewView', true)">
            <span class="sim-action-icon" aria-hidden="true">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
              </svg>
            </span>
            <span class="sim-action-text">{{ t('simulation.virtualInterview') }}</span>
          </button>
          <button type="button" class="sim-action-btn ghost" @click="handleResetSimulation">
            <span class="sim-action-icon" aria-hidden="true">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
                <path d="M3 12a9 9 0 1 0 9-9"/>
                <polyline points="3 4 3 12 11 12"/>
              </svg>
            </span>
            <span class="sim-action-text">{{ t('simulation.resimulate') }}</span>
          </button>
        </div>
      </section>

      <!-- 推演时间线 -->
      <div v-if="fermentationResult?.narrative_history?.length" class="sim-timeline-section">
        <div class="sim-timeline-header">
          <span class="sim-timeline-title">{{ t('simulation.timeline') }}</span>
          <span class="sim-timeline-count">{{ t('simulation.nodeCount', { count: fermentationResult.narrative_history.length }) }}</span>
        </div>
        <div class="sim-timeline-feed">
          <div class="sim-timeline-axis" aria-hidden="true"></div>
          <TransitionGroup name="sim-timeline">
            <div
              v-for="(nh, idx) in fermentationResult.narrative_history"
              :key="idx"
              class="sim-timeline-item"
              :class="idx % 2 === 0 ? 'left' : 'right'"
            >
              <div class="sim-timeline-marker" aria-hidden="true">
                <span class="sim-marker-dot"></span>
              </div>
              <div class="sim-timeline-card">
                <div class="sim-card-header">
                  <span class="sim-card-day">{{ nh.label }}</span>
                  <span v-if="nh.states?.length" class="sim-card-avg">{{ t('simulation.supportLevel', { value: calcAvgSupport(nh.states).toFixed(1) }) }}</span>
                </div>
                <div class="sim-card-body">
                  <p v-if="nh.narrative" class="sim-card-narrative">{{ nh.narrative }}</p>
                  <div v-if="nh.interactions?.length" class="sim-card-interactions">
                    <div v-for="(it, i) in nh.interactions" :key="i" class="sim-interaction">
                      <div class="sim-interaction-head">
                        <span class="sim-actor">{{ it.actor }}</span>
                        <span class="sim-action-badge">{{ it.action }}</span>
                        <span v-if="it.target" class="sim-target">→ {{ it.target }}</span>
                      </div>
                      <p class="sim-interaction-text">{{ it.content }}</p>
                      <p v-if="it.effect" class="sim-interaction-effect">{{ it.effect }}</p>
                    </div>
                  </div>
                </div>
                <div v-if="nh.state_changes?.length" class="sim-card-footer">
                  <span v-for="(c, i) in nh.state_changes" :key="i" class="sim-change-chip" :class="c.new_support_level > c.old_support_level ? 'up' : 'down'">
                    {{ c.stakeholder_name }} {{ c.old_support_level }}→{{ c.new_support_level }}
                  </span>
                </div>
              </div>
            </div>
          </TransitionGroup>
        </div>
      </div>

      <!-- 结论 + 态度曲线 -->
      <div v-if="fermentationResult" class="sim-result-section">
        <div class="sim-conclusion-bar">
          <span class="sim-conclusion-label">{{ t('simulation.conclusion') }}</span>
          <p class="sim-conclusion-text">{{ fermentationResult.conclusion }}</p>
        </div>
        <div v-if="fermentationResult.narrative_history?.length || fermentationResult.history?.length" class="sim-chart-wrapper">
          <svg ref="chartSvgRef" class="chart-svg" :aria-label="t('simulation.attitudeCurve')" role="img"></svg>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { formatDate } from '../../composables/salesTwin/formatters.js'

const { t } = useI18n()

const props = defineProps({
  fermentationResult: { type: Object, default: null },
  fermentationInput: { type: Object, default: () => ({ related_task_ids: [], related_feedback_ids: [], related_materials: [], initial_events: [] }) },
  runningSim: { type: Boolean, default: false },
  feedbackRecords: { type: Array, default: () => [] },
  tasks: { type: Array, default: () => [] },
  stakeholders: { type: Array, default: () => [] },
  buyerRoleLabels: { type: Object, default: () => ({}) },
  interviewHistory: { type: Array, default: () => [] },
  interviewTargetId: { type: [Number, null], default: null },
  interviewQuestion: { type: String, default: '' },
  interviewResult: { type: Object, default: null },
  interviewing: { type: Boolean, default: false },
  presetQuestions: { type: Array, default: () => [] },
  showReportView: { type: Boolean, default: false },
  showInterviewView: { type: Boolean, default: false },
  showSuggestionPool: { type: Boolean, default: false },
  fermentationReport: { type: Object, default: null },
  chartSvg: { type: Object, default: null },
})

const emit = defineEmits([
  'run-simulation',
  'reset-simulation',
  'run-interview',
  'update:fermentationInput',
  'update:interviewTargetId',
  'update:interviewQuestion',
  'update:showReportView',
  'update:showInterviewView',
  'update:showSuggestionPool',
  'close-interview-result',
])

// 控制是否显示 01/02 输入面板（推演完成后隐藏，点"重新推演"再显示）
const showInputPanel = ref(true)
const chartSvgRef = ref(null)

// 推演结果变化时重置面板显示状态
watch(() => props.fermentationResult, (newVal) => {
  if (newVal) {
    // 有结果 → 隐藏输入面板
    showInputPanel.value = false
  } else {
    // 无结果 → 显示输入面板
    showInputPanel.value = true
  }
})

// 启动推演
function handleStartSimulation() {
  showInputPanel.value = false
  emit('run-simulation')
}

// 重新推演：通知父组件清空结果，并显示输入面板
function handleResetSimulation() {
  showInputPanel.value = true
  emit('reset-simulation')
}

onMounted(() => {
  if (props.chartSvg && chartSvgRef.value) {
    props.chartSvg.value = chartSvgRef.value
  }
})

watch(chartSvgRef, (el) => {
  if (props.chartSvg && el) {
    props.chartSvg.value = el
  }
})

function calcAvgSupport(states) {
  if (!states || !states.length) return 0
  const total = states.reduce((sum, s) => sum + (s.support_level || 0) * (s.decision_power || 1), 0)
  const totalPower = states.reduce((sum, s) => sum + (s.decision_power || 1), 0)
  return totalPower === 0 ? 0 : total / totalPower
}
</script>

<style scoped>
/* ============ CSS 变量 ============ */
.sim-tab-pane {
  --bg-base: #F4F0E7;
  --bg-surface: #F8F4EC;
  --bg-card: #FCFBF5;
  --sidebar-bg: #EBE7DC;
  --sidebar-border: #D7D4CD;
  --panel-bg: #EFEDE2;

  --text-primary: #15171D;
  --text-secondary: #494A4D;
  --text-tertiary: #807E7E;
  --text-muted: #93959D;

  --border: #E8E8E0;
  --border-strong: #D7D4CD;
  --divider: #D7D4CD;

  --accent: #CD5036;
  --accent-light: #D88573;
  --accent-hover: #C4391C;
  --green: #118A58;
  --green-light: rgba(17, 138, 88, 0.08);
  --red: #C4391C;
  --red-light: rgba(196, 57, 28, 0.08);
  --yellow: #CBB88C;
  --yellow-light: rgba(203, 184, 140, 0.12);
  --blue: #90B0C8;
  --blue-light: rgba(144, 176, 200, 0.12);

  --focus-ring: #15171D;
  --shadow-sm: 0 1px 2px rgba(21, 23, 29, 0.04);
  --shadow-md: 0 4px 12px rgba(21, 23, 29, 0.05);
  --shadow-lg: 0 8px 24px rgba(21, 23, 29, 0.06);

  --font-mono: 'JetBrains Mono', 'SF Mono', monospace;
  --font-sans: 'Noto Sans SC', 'PingFang SC', 'Microsoft YaHei', system-ui, sans-serif;

  --fs-xs: 11px;
  --fs-sm: 12px;
  --fs-base: 13px;
  --fs-md: 14px;
  --fs-lg: 16px;
  --fs-xl: 20px;
  --fs-2xl: 26px;

  --lh-tight: 1.3;
  --lh-base: 1.5;
  --lh-loose: 1.65;
}

/* ===== 推演与模拟（MiroFish原生风格） ===== */
.sim-tab-pane {
  display: flex;
  flex-direction: column;
  flex: 1;
  gap: 0;
  overflow-y: auto;
  overflow-x: hidden;
}

/* ============ 推演输入控制台（参照MiroFish首页 console-box） ============ */
.sim-console-box {
  border: 1px solid var(--border-strong);
  padding: 8px;
  margin-bottom: 20px;
  background: var(--bg-card);
}

.sim-console-section {
  padding: 18px 20px;
}

.sim-console-section.sim-btn-section {
  padding-top: 14px;
}

.sim-console-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
}

.sim-console-label {
  display: inline-flex;
  align-items: baseline;
  gap: 6px;
  color: var(--text-primary);
}

.sim-section-num {
  font-family: var(--font-mono);
  font-weight: 700;
  font-size: var(--fs-base);
  color: var(--text-primary);
  opacity: 0.3;
}

.sim-section-sep {
  color: var(--border-strong);
  font-weight: 400;
}

.sim-section-title {
  font-weight: 520;
  font-size: var(--fs-base);
  letter-spacing: 0.02em;
  color: var(--text-primary);
}

.sim-console-meta {
  color: var(--text-muted);
  font-size: var(--fs-xs);
}

/* 01 / 会议纪要 - 种子记录列表 */
.sim-seed-zone {
  border: 1px dashed var(--border);
  background: var(--bg-surface);
  min-height: 80px;
  max-height: 220px;
  overflow-y: auto;
  padding: 6px;
}

.sim-seed-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 80px;
  font-size: var(--fs-sm);
  color: var(--text-muted);
  font-family: var(--font-mono);
}

.sim-seed-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.sim-seed-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  cursor: pointer;
  font-size: var(--fs-sm);
  transition: border-color 0.15s, background 0.15s;
}

.sim-seed-item:hover {
  border-color: var(--text-muted);
}

.sim-seed-item.selected {
  border-color: var(--text-primary);
  background: rgba(21, 23, 29, 0.02);
}

.sim-seed-item input[type="checkbox"] {
  margin: 0;
  flex-shrink: 0;
  accent-color: var(--text-primary);
}

.sim-seed-item.selected input[type="checkbox"] {
  accent-color: var(--text-primary);
}

.sim-seed-date {
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  color: var(--text-muted);
  flex-shrink: 0;
  min-width: 80px;
}

.sim-seed-text {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: rgba(21, 23, 29, 0.78);
}

.sim-seed-changes {
  font-size: var(--fs-xs);
  font-family: var(--font-mono);
  color: var(--yellow);
  flex-shrink: 0;
}

/* 分割线（参照MiroFish console-divider） */
.sim-console-divider {
  display: flex;
  align-items: center;
  margin: 4px 0;
}

.sim-console-divider::before,
.sim-console-divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--border);
}

.sim-console-divider span {
  padding: 0 15px;
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  color: var(--text-muted);
  letter-spacing: 1px;
}

/* 02 / 关联任务 */
.sim-trigger-group {
  margin-bottom: 14px;
}

.sim-trigger-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.sim-trigger-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 10px;
  border: 1px solid var(--border);
  background: var(--bg-card);
  cursor: pointer;
  font-size: var(--fs-sm);
  transition: border-color 0.15s, background 0.15s;
}

.sim-trigger-item:hover {
  border-color: var(--text-muted);
}

.sim-trigger-item input[type="checkbox"] {
  margin: 0;
  accent-color: var(--text-primary);
}

.sim-trigger-name {
  color: rgba(21, 23, 29, 0.8);
}

.sim-trigger-tag.done {
  font-size: var(--fs-xs);
  font-family: var(--font-mono);
  color: var(--green);
  padding: 1px 5px;
  border: 1px solid var(--green);
}

/* 状态指示行 */
.sim-status-line {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  font-size: var(--fs-sm);
  font-family: var(--font-mono);
}

.sim-status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--border-strong);
  flex-shrink: 0;
}

.sim-status-dot.idle {
  background: var(--border-strong);
}

.sim-status-dot.active {
  background: var(--yellow);
  animation: sim-pulse 1s infinite;
}

.sim-status-dot.completed {
  background: var(--green);
}

@keyframes sim-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.4; transform: scale(1.3); }
}

.sim-status-text {
  color: rgba(21, 23, 29, 0.78);
}

.sim-status-trend {
  margin-left: auto;
  font-weight: 600;
}

.sim-status-trend.up {
  color: var(--green);
}

.sim-status-trend.down {
  color: var(--red);
}

/* 启动推演按钮 */
.sim-start-engine-btn {
  width: 100%;
  background: var(--text-primary);
  color: var(--bg-card);
  border: 1px solid var(--text-primary);
  padding: 16px 20px;
  font-family: var(--font-mono);
  font-weight: 700;
  font-size: var(--fs-md);
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  transition: background-color 0.25s, border-color 0.25s, transform 0.2s;
  letter-spacing: 1px;
  position: relative;
  overflow: hidden;
}

.sim-start-engine-btn:not(:disabled) {
  animation: sim-pulse-border 2s infinite;
}

.sim-start-engine-btn:hover:not(:disabled) {
  background: var(--yellow);
  border-color: var(--yellow);
  transform: translateY(-1px);
}

.sim-start-engine-btn:disabled {
  background: var(--border);
  color: var(--text-muted);
  cursor: not-allowed;
  transform: none;
  border-color: var(--border);
}

.sim-start-engine-btn.pulsing {
  animation: sim-pulse-border 2s infinite;
}

@keyframes sim-pulse-border {
  0% { box-shadow: 0 0 0 0 rgba(21, 23, 29, 0.2); }
  70% { box-shadow: 0 0 0 6px rgba(21, 23, 29, 0); }
  100% { box-shadow: 0 0 0 0 rgba(21, 23, 29, 0); }
}

.sim-btn-arrow {
  font-size: var(--fs-md);
}

.sim-btn-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: var(--bg-card);
  border-radius: 50%;
  animation: sim-spin 0.6s linear infinite;
}

.sim-btn-spinner.small {
  width: 12px;
  height: 12px;
  border-width: 1.5px;
}

@keyframes sim-spin {
  to { transform: rotate(360deg); }
}

/* ============ 顶部操作按钮组（推演完成后） ============ */
.sim-actions-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 18px;
  background: var(--bg-card);
  border: 1px solid var(--border-strong);
  border-left: 3px solid var(--green);
  border-radius: 6px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.sim-actions-info {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.sim-actions-status {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-family: var(--font-mono);
  font-size: var(--fs-sm);
}

.sim-actions-text {
  color: var(--text-primary);
  font-weight: 600;
}

.sim-actions-trend {
  font-weight: 600;
  padding-left: 8px;
  border-left: 1px solid var(--border);
  font-variant-numeric: tabular-nums;
}

.sim-actions-trend.up {
  color: var(--green);
}

.sim-actions-trend.down {
  color: var(--red);
}

.sim-actions-buttons {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.sim-action-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border: 1px solid var(--border-strong);
  background: var(--bg-card);
  color: var(--text-primary);
  font-size: var(--fs-sm);
  font-weight: 600;
  font-family: var(--font-mono);
  cursor: pointer;
  border-radius: 4px;
  transition: background-color 0.15s, border-color 0.15s, transform 0.15s;
  touch-action: manipulation;
}

.sim-action-btn:hover {
  border-color: var(--text-primary);
  background: var(--bg-surface);
  transform: translateY(-1px);
}

.sim-action-btn:focus-visible {
  outline: 2px solid var(--focus-ring);
  outline-offset: 2px;
}

.sim-action-btn:active {
  transform: translateY(0);
}

.sim-action-btn.primary {
  background: var(--text-primary);
  color: var(--bg-card);
  border-color: var(--text-primary);
}

.sim-action-btn.primary:hover {
  background: var(--accent);
  border-color: var(--accent);
}

.sim-action-btn.ghost {
  background: transparent;
  color: var(--text-secondary);
  border-color: var(--border);
}

.sim-action-btn.ghost:hover {
  color: var(--text-primary);
  border-color: var(--text-muted);
  background: var(--bg-surface);
}

.sim-action-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.sim-action-text {
  white-space: nowrap;
}

/* 中央轴时间线 */
.sim-timeline-section {
  margin-bottom: 16px;
}

.sim-timeline-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 0;
  border-bottom: 1px solid var(--border);
  margin-bottom: 20px;
}

.sim-timeline-title {
  font-size: var(--fs-base);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-primary);
}

.sim-timeline-count {
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}

.sim-timeline-feed {
  position: relative;
  padding: 0 0 20px;
}

.sim-timeline-axis {
  position: absolute;
  left: 50%;
  top: 0;
  bottom: 0;
  width: 1px;
  background: var(--border);
  transform: translateX(-50%);
}

.sim-timeline-item {
  position: relative;
  padding: 0 0 24px;
}

.sim-timeline-item.left {
  padding-right: 50%;
}

.sim-timeline-item.right {
  padding-left: 50%;
}

.sim-timeline-marker {
  position: absolute;
  top: 12px;
  left: 50%;
  transform: translateX(-50%);
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--bg-card);
  border: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1;
}

.sim-marker-dot {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--text-primary);
}

.sim-timeline-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 6px;
  overflow: hidden;
}

.sim-timeline-item.left .sim-timeline-card {
  margin-right: 32px;
}

.sim-timeline-item.right .sim-timeline-card {
  margin-left: 32px;
}

.sim-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border);
}

.sim-card-day {
  font-size: var(--fs-sm);
  font-weight: 600;
  color: var(--text-primary);
}

.sim-card-avg {
  font-size: var(--fs-xs);
  color: var(--text-secondary);
  font-family: 'JetBrains Mono', monospace;
  font-variant-numeric: tabular-nums;
}

.sim-card-body {
  padding: 12px;
}

.sim-card-narrative {
  font-size: var(--fs-sm);
  line-height: 1.6;
  color: rgba(21, 23, 29, 0.78);
  margin: 0 0 10px;
  padding: 8px 10px;
  background: var(--bg-surface);
  border-left: 2px solid var(--text-primary);
  border-radius: 0 4px 4px 0;
  text-wrap: pretty;
}

.sim-card-interactions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.sim-interaction {
  padding: 8px 10px;
  border: 1px solid var(--bg-surface);
  border-radius: 4px;
}

.sim-interaction-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
}

.sim-actor {
  font-size: var(--fs-sm);
  font-weight: 600;
  color: var(--text-primary);
}

.sim-action-badge {
  font-size: var(--fs-xs);
  padding: 1px 6px;
  background: var(--bg-surface);
  color: var(--text-secondary);
  border-radius: 3px;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.sim-target {
  font-size: var(--fs-xs);
  color: var(--text-muted);
}

.sim-interaction-text {
  font-size: var(--fs-sm);
  line-height: 1.5;
  color: rgba(21, 23, 29, 0.7);
  margin: 4px 0 0;
}

.sim-interaction-effect {
  font-size: var(--fs-xs);
  color: var(--yellow);
  margin: 2px 0 0;
  font-style: italic;
}

.sim-card-footer {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  padding: 8px 12px;
  background: var(--bg-surface);
  border-top: 1px solid var(--border);
}

.sim-change-chip {
  font-size: var(--fs-xs);
  padding: 2px 8px;
  border-radius: 10px;
  font-family: 'JetBrains Mono', monospace;
  font-variant-numeric: tabular-nums;
}

.sim-change-chip.up {
  background: var(--green-light);
  color: var(--green);
}

.sim-change-chip.down {
  background: var(--red-light);
  color: var(--red);
}

/* 时间线进入动画 */
.sim-timeline-enter-from {
  opacity: 0;
  transform: translateY(20px);
}

.sim-timeline-enter-active {
  transition: opacity 0.4s cubic-bezier(0.165, 0.84, 0.44, 1), transform 0.4s cubic-bezier(0.165, 0.84, 0.44, 1);
}

/* 结论 + 曲线 */
.sim-result-section {
  margin-bottom: 16px;
}

.sim-conclusion-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 6px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.sim-conclusion-label {
  font-size: var(--fs-xs);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
  font-family: var(--font-mono, 'JetBrains Mono', monospace);
}

.sim-conclusion-text {
  flex: 1;
  min-width: 200px;
  font-size: var(--fs-sm);
  color: rgba(21, 23, 29, 0.8);
  margin: 0;
  text-wrap: pretty;
}

.sim-chart-wrapper {
  margin-bottom: 20px;
}

.chart-svg {
  width: 100%;
  height: 250px;
  margin-top: 8px;
}

/* sr-only：屏幕阅读器可见，视觉隐藏 */
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

@media (max-width: 768px) {
  .sim-actions-bar {
    flex-direction: column;
    align-items: stretch;
  }

  .sim-actions-buttons {
    flex-direction: column;
  }

  .sim-action-btn {
    width: 100%;
    justify-content: center;
  }

  .sim-timeline-axis {
    left: 20px;
  }
  .sim-timeline-item.left,
  .sim-timeline-item.right {
    padding-left: 40px;
    padding-right: 0;
  }
  .sim-timeline-item.left .sim-timeline-card,
  .sim-timeline-item.right .sim-timeline-card {
    margin-left: 0;
    margin-right: 0;
  }
  .sim-timeline-marker {
    left: 20px;
  }
  .sim-seed-item {
    flex-wrap: wrap;
  }
}

@media (prefers-reduced-motion: reduce) {
  .sim-start-engine-btn.pulsing,
  .sim-start-engine-btn:not(:disabled),
  .sim-status-dot.active {
    animation: none;
  }
  .sim-timeline-enter-active {
    transition: none;
  }
  .sim-action-btn,
  .sim-action-btn:hover {
    transition: none;
    transform: none;
  }
}
</style>

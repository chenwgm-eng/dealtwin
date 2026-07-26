<template>
  <div class="tab-pane overview-pane">
    <!-- 顶部指标条：可访问的button元素，键盘可达 -->
    <div class="metrics-grid" role="group" :aria-label="t('overview.coreMetrics')">
      <button type="button" class="metric-card clickable" @click="$emit('open-win-rate')">
        <div class="metric-value" :class="winRateColor">
          {{ winRateData?.win_rate || 0 }}<span class="metric-unit">%</span>
        </div>
        <div class="metric-label">{{ t('overview.opportunityQuality') }}</div>
      </button>
      <button type="button" class="metric-card clickable" @click="$emit('navigate-to', 'stakeholders')">
        <div class="metric-value">{{ stakeholders.length }}</div>
        <div class="metric-label">{{ t('overview.stakeholders') }}</div>
      </button>
      <button type="button" class="metric-card clickable" @click="$emit('navigate-to', 'tasks')">
        <div class="metric-value">{{ tasks.length }}</div>
        <div class="metric-label">{{ t('workspace.todoItems') }}</div>
      </button>
      <button type="button" class="metric-card clickable" @click="$emit('navigate-to', 'blindspot')">
        <div class="metric-value" :class="{ 'text-error': sortedFindings.length > 0, 'text-success': sortedFindings.length === 0 }">
          {{ sortedFindings.length || 0 }}
        </div>
        <div class="metric-label">{{ t('overview.blindSpotWarning') }}</div>
      </button>
    </div>

    <!-- 主体两列：左项目信息+客户概览 / 右最近活动 -->
    <div class="overview-grid">
      <!-- 左列：项目信息 + 客户概览 -->
      <div class="overview-main">
        <!-- 项目信息卡片 -->
        <ProjectInfoSection
          :currentProject="currentProject"
          :allCustomers="allCustomers"
          :formatDate="formatDate"
          :formatCurrency="formatCurrency"
          @update-project="$emit('update-project', $event)"
        />

        <!-- 业务字段 Tab section（业务痛点/价值主张/竞争分析） -->
        <BusinessInsightSection
          :currentProject="currentProject"
          :formatStructuredText="formatStructuredText"
          @update-project="$emit('update-project', $event)"
          @refresh-project="$emit('refresh-project', $event)"
        />

        <!-- 最近活动（待办/反馈/变更 摘要，横向三列） -->
        <section class="recent-activity-section" aria-labelledby="recent-activity-title">
          <div class="section-header">
            <span class="section-deco" aria-hidden="true">◇</span>
            <h3 id="recent-activity-title" class="section-title">{{ t('overview.recentActivity') }}</h3>
          </div>
          <div class="recent-activity-row">
            <div class="activity-col">
              <div class="activity-col-title">
                {{ t('overview.todo') }}
                <span class="activity-count">{{ pendingTasks.length }}</span>
              </div>
              <ul v-if="pendingTasks.length" class="activity-list">
                <li v-for="t in pendingTasks.slice(0,5)" :key="t.id" class="activity-item">
                  <span class="activity-dot" :class="t.status" aria-hidden="true"></span>
                  <span class="activity-text">{{ t.title }}</span>
                </li>
              </ul>
              <div v-else class="activity-empty">{{ t('overview.noTodos') }}</div>
              <button type="button" class="view-all-btn" @click="emit('navigate-to', 'tasks')">{{ t('overview.viewAll') }}</button>
            </div>
            <div class="activity-col">
              <div class="activity-col-title">
                {{ t('overview.feedback') }}
                <span class="activity-count">{{ feedbackRecords.length }}</span>
              </div>
              <ul v-if="recentFeedback.length" class="activity-list">
                <li v-for="f in recentFeedback" :key="f.id" class="activity-item">
                  <span class="activity-dot feedback" aria-hidden="true"></span>
                  <span class="activity-text">{{ f.feedback_text }}</span>
                </li>
              </ul>
              <div v-else class="activity-empty">{{ t('overview.noFeedback') }}</div>
              <button type="button" class="view-all-btn" @click="emit('navigate-to', 'feedback')">{{ t('overview.viewAll') }}</button>
            </div>
            <div class="activity-col">
              <div class="activity-col-title">
                {{ t('overview.stakeholderChange') }}
                <span class="activity-count">{{ stakeholderChanges.length }}</span>
              </div>
              <ul v-if="stakeholderChanges.length" class="activity-list">
                <li v-for="log in stakeholderChanges" :key="log.id" class="activity-item">
                  <span class="activity-dot change" aria-hidden="true"></span>
                  <span class="activity-text">{{ log.change_object }} · {{ log.attribute_name }}：{{ log.old_value }} → {{ log.new_value }}</span>
                </li>
              </ul>
              <div v-else class="activity-empty">{{ t('overview.noChanges') }}</div>
              <button type="button" class="view-all-btn" @click="emit('navigate-to', 'stakeholders')">{{ t('overview.viewTimeline') }}</button>
            </div>
          </div>
        </section>
      </div>

      <!-- 右列：当前阶段交付物要求 -->
      <aside class="overview-aside" aria-labelledby="stage-aside-title">
        <div class="section-header">
          <span class="section-deco" aria-hidden="true">◇</span>
          <h3 id="stage-aside-title" class="section-title">{{ t('overview.currentStageDeliverables') }}</h3>
        </div>
        <StageDeliverablesPanel
          :currentProject="currentProject"
          :stageDeliverables="stageDeliverables"
          :stageDeliverablesLoading="stageDeliverablesLoading"
          :formatDate="formatDate"
          :formatFileSize="formatFileSize"
          @reload-stage-deliverables="$emit('reload-stage-deliverables')"
          @run-stage-check="$emit('run-stage-check')"
        />
      </aside>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { formatStructuredText, formatDate, formatCurrency, formatFileSize } from '../../composables/salesTwin/formatters.js'
import StageDeliverablesPanel from './StageDeliverablesPanel.vue'
import ProjectInfoSection from './ProjectInfoSection.vue'
import BusinessInsightSection from './BusinessInsightSection.vue'

const { t } = useI18n()

const props = defineProps({
  currentProject: { type: Object, default: () => ({}) },
  stakeholders: { type: Array, default: () => [] },
  tasks: { type: Array, default: () => [] },
  winRateData: { type: Object, default: () => ({}) },
  sortedFindings: { type: Array, default: () => [] },
  winRateColor: { type: String, default: '' },
  allCustomers: { type: Array, default: () => [] },
  formatStructuredText: { type: Function, default: formatStructuredText },
  formatDate: { type: Function, default: formatDate },
  formatCurrency: { type: Function, default: formatCurrency },
  formatFileSize: { type: Function, default: formatFileSize },
  stageDeliverables: { type: Object, default: () => null },
  stageDeliverablesLoading: { type: Boolean, default: false },
  feedbackRecords: { type: Array, default: () => [] },
  stateLogs: { type: Array, default: () => [] },
})

const emit = defineEmits(['navigate-to', 'open-win-rate', 'update-project', 'refresh-project', 'reload-stage-deliverables', 'run-stage-check'])

// 最近活动：待办（未完成）、反馈、干系人变更
const pendingTasks = computed(() => {
  // 只显示未完成任务（pending / in_progress），排除 completed / cancelled
  return (props.tasks || []).filter(t => t.status === 'pending' || t.status === 'in_progress')
})

const recentFeedback = computed(() => {
  // 按时间倒序，最多5条
  return [...(props.feedbackRecords || [])]
    .sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0))
    .slice(0, 5)
})

const stakeholderChanges = computed(() => {
  // 只看干系人相关的变更日志（stakeholder_id 非空）
  return (props.stateLogs || [])
    .filter(log => log.stakeholder_id)
    .sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0))
    .slice(0, 5)
})
</script>

<style scoped>
/* ============ CSS 变量 ============ */
.overview-pane {
  /* 覆盖 .tab-pane 的 overflow:hidden，让内容能正常扩展并由 .main-content 滚动 */
  overflow: visible;

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

.overview-pane,
.overview-pane * {
  letter-spacing: 0.01em;
}

/* ============ 指标网格 ============ */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.metric-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 20px 24px;
  text-align: left;
  display: flex;
  flex-direction: column;
  gap: 6px;
  position: relative;
}

.metric-value {
  font-family: var(--font-mono);
  font-size: 28px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  line-height: 1.2;
  color: var(--text-primary);
}

.metric-unit {
  font-size: 16px;
  font-weight: 500;
  margin-left: 2px;
}

.metric-label {
  font-size: var(--fs-sm);
  color: var(--text-tertiary);
  letter-spacing: 0.02em;
}

.text-error { color: var(--red); }
.text-success { color: var(--green); }

/* ============ 可点击指标卡 ============ */
.metric-card.clickable {
  cursor: pointer;
  transition: transform 0.15s, box-shadow 0.15s, border-color 0.15s;
  font: inherit;
  text-align: center;
  color: inherit;
  width: 100%;
  border: 1px solid var(--border);
  background: var(--bg-card);
  touch-action: manipulation;
  -webkit-tap-highlight-color: rgba(196, 154, 69, 0.12);
}

.metric-card.clickable:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(21, 23, 29, 0.08);
  border-color: var(--yellow);
}

.metric-card.clickable:focus-visible {
  outline: 2px solid var(--yellow);
  outline-offset: 2px;
}

.metric-card.clickable:active {
  transform: translateY(0);
}

@media (prefers-reduced-motion: reduce) {
  .metric-card.clickable {
    transition: border-color 0.15s, box-shadow 0.15s;
  }
  .metric-card.clickable:hover {
    transform: none;
  }
}

/* ============ 概览主网格 ============ */
.overview-grid {
  display: grid;
  grid-template-columns: minmax(0, 2fr) minmax(280px, 1fr);
  gap: 24px;
  margin-top: 24px;
  align-items: start;
}

.overview-main {
  display: flex;
  flex-direction: column;
  gap: 28px;
  min-width: 0;
}

.overview-aside {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 18px 20px;
  position: sticky;
  top: 12px;
}

@media (max-width: 1024px) {
  .overview-grid {
    grid-template-columns: 1fr;
  }
  .overview-aside {
    position: static;
  }
}

/* ============ 区块标题（aside/section 共享） ============ */
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

/* ============ 活动列表（最近活动复用） ============ */
.activity-count {
  font-size: var(--fs-xs);
  font-family: 'JetBrains Mono', monospace;
  color: rgba(21, 23, 29, 0.5);
  font-variant-numeric: tabular-nums;
}

.activity-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.activity-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: var(--fs-xs);
  color: rgba(21, 23, 29, 0.7);
}

.activity-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: rgba(21, 23, 29, 0.35);
  flex-shrink: 0;
}

.activity-dot.pending { background: var(--yellow); }
.activity-dot.in_progress { background: var(--blue); }
.activity-dot.completed { background: var(--green); }
.activity-dot.cancelled { background: rgba(21, 23, 29, 0.2); }
.activity-dot.feedback { background: var(--yellow); }
.activity-dot.change { background: var(--accent, #CD5036); }
.activity-dot.manual_edit { background: rgba(21, 23, 29, 0.5); }
.activity-dot.feedback_parser { background: var(--yellow); }

.activity-text {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.activity-empty {
  font-size: var(--fs-xs);
  color: rgba(21, 23, 29, 0.35);
  font-style: italic;
}

/* ============ 最近活动（横向三列） ============ */
.recent-activity-section {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 18px 24px 20px;
  box-shadow: var(--shadow-sm);
}

.recent-activity-row {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 20px;
}

.activity-col {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
  padding: 12px;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 6px;
}

.activity-col-title {
  display: flex;
  align-items: baseline;
  gap: 8px;
  font-size: var(--fs-sm);
  font-weight: 700;
  color: var(--text-primary);
}

.activity-col-title .activity-count {
  font-size: var(--fs-xs);
  color: var(--text-muted);
}

/* ul 重置：原 .activity-list 用于 div，这里复用为 ul 需清除默认样式 */
.recent-activity-section .activity-list {
  margin: 0;
  padding: 0;
  list-style: none;
  flex: 1;
}

.recent-activity-section .activity-item {
  margin: 0;
}

.view-all-btn {
  appearance: none;
  background: none;
  border: none;
  color: var(--accent);
  font-size: var(--fs-xs);
  font-family: var(--font-sans);
  cursor: pointer;
  padding: 4px 0;
  text-align: left;
  text-decoration: underline;
  align-self: flex-start;
}

.view-all-btn:hover {
  color: var(--accent-hover);
}

.view-all-btn:focus-visible {
  outline: 2px solid var(--focus-ring);
  outline-offset: 2px;
  border-radius: 2px;
}

@media (max-width: 720px) {
  .recent-activity-row {
    grid-template-columns: 1fr;
  }
}
</style>

<template>
  <div class="stage-timeline" role="region" :aria-label="t('timeline.title')">
    <!-- 加载骨架屏 -->
    <div v-if="loading" class="timeline-skeleton" role="status" aria-live="polite" aria-busy="true">
      <div v-for="i in 2" :key="i" class="skeleton-row">
        <div class="skeleton-node">
          <div class="skeleton-line w-70"></div>
          <div class="skeleton-line w-50"></div>
          <div class="skeleton-line w-40"></div>
        </div>
        <div class="skeleton-card">
          <div class="skeleton-line w-90"></div>
          <div class="skeleton-line w-60"></div>
          <div class="skeleton-line w-80"></div>
          <div class="skeleton-line w-50"></div>
        </div>
      </div>
      <span class="sr-only">{{ t('common.loading') }}</span>
    </div>

    <!-- 空状态 -->
    <div v-else-if="!timelineData || !timelineData.stages?.length" class="timeline-empty" role="status">
      <div class="empty-icon" aria-hidden="true">◇</div>
      <div class="empty-text">{{ t('timeline.noTimeline') }}</div>
    </div>

    <!-- 时间流瀑布 -->
    <div v-else class="timeline-content">
      <header class="timeline-header">
        <div class="header-title-group">
          <h2 class="timeline-title">{{ timelineData.project_name }}<span class="title-sub">&nbsp;{{ t('timeline.title') }}</span></h2>
          <div class="timeline-current" aria-live="polite">
            <span class="current-dot" aria-hidden="true"></span>
            {{ t('timeline.currentStage') }}：{{ currentStageLabel }}
          </div>
        </div>
        <div class="header-meta" v-if="stageStats.total > 0">
          <span class="meta-label">{{ t('timeline.recordedStages') }}</span>
          <span class="meta-value">{{ stageStats.total }}</span>
          <span class="meta-divider" aria-hidden="true">·</span>
          <span class="meta-label">{{ t('timeline.totalDeliverables') }}</span>
          <span class="meta-value">{{ stageStats.deliverableTotal }}</span>
          <span class="meta-divider" aria-hidden="true">·</span>
          <span class="meta-label">{{ t('timeline.completed') }}</span>
          <span class="meta-value meta-value-accent">{{ stageStats.deliverableDone }}</span>
        </div>
      </header>

      <ol class="timeline-waterfall" role="list">
        <li v-for="(stage, idx) in timelineData.stages" :key="idx"
            class="timeline-stage-row"
            :class="{ current: stage.is_current }"
            role="listitem">
          <!-- 左侧节点列：时间 + 标题 -->
          <div class="stage-node" :class="{ current: stage.is_current }">
            <div class="node-marker" aria-hidden="true">
              <div class="node-dot"></div>
              <div class="node-line" v-if="idx < timelineData.stages.length - 1"></div>
            </div>
            <div class="node-body">
              <time class="node-date" :datetime="stage.started_at">
                <span class="date-day">{{ formatShortDate(stage.started_at) }}</span>
                <span class="date-time">{{ formatTime(stage.started_at) }}</span>
              </time>
              <div class="node-title">
                <span class="node-label">{{ stage.label }}</span>
                <div class="node-badges">
                  <span v-if="stage.om_milestone" class="node-om" :aria-label="t('timeline.milestone', { name: stage.om_milestone })">
                    {{ stage.om_milestone }}
                  </span>
                  <span v-if="stage.is_current" class="node-current-tag" :aria-label="t('timeline.currentStage')">{{ t('timeline.currentTag') }}</span>
                </div>
              </div>
              <div class="node-duration" v-if="stage.duration_days !== null">
                <span class="duration-icon" aria-hidden="true">
                  <svg viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.4">
                    <circle cx="6" cy="6" r="5"/>
                    <path d="M6 3.5V6l1.8 1.1"/>
                  </svg>
                </span>
                {{ t('timeline.duration') }}&nbsp;{{ stage.duration_days }}&nbsp;{{ t('timeline.days') }}
              </div>
            </div>
          </div>

          <!-- 右侧内容列：活动记录 + 交付物 -->
          <article class="stage-content" :class="{ current: stage.is_current }">
            <!-- 卡片头部：核心目标 + 完成度 -->
            <header class="content-header">
              <div class="header-objective" v-if="stage.core_objective">
                <div class="objective-label" aria-hidden="true">{{ t('timeline.coreObjective') }}</div>
                <p class="objective-text">{{ stage.core_objective }}</p>
              </div>
              <div class="header-progress" v-if="stage.total_items > 0">
                <div class="progress-meta">
                  <span class="progress-label">{{ t('timeline.completion') }}</span>
                  <span class="progress-rate" :class="getProgressClass(stage.completion_rate)">
                    {{ formatPercent(stage.completion_rate) }}
                  </span>
                </div>
                <div class="progress-track" role="progressbar"
                     :aria-valuenow="Math.round(stage.completion_rate)"
                     aria-valuemin="0" aria-valuemax="100"
                     :aria-label="t('timeline.stageCompletion', { name: stage.label })">
                  <div class="progress-fill"
                       :class="getProgressClass(stage.completion_rate)"
                       :style="{ width: Math.max(stage.completion_rate, 2) + '%' }"></div>
                </div>
                <div class="progress-count" :aria-label="t('timeline.completedItems')">
                  {{ stage.completed_items }}/{{ stage.total_items }}
                </div>
              </div>
            </header>

            <!-- 交付物（主要活动记录） -->
            <section v-if="stage.deliverables?.length" class="content-section" :aria-label="t('deliverable.title')">
              <header class="section-header">
                <h3 class="section-title">
                  <span class="section-icon" aria-hidden="true">
                    <svg viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.4">
                      <path d="M3 2h6l2 2v8H3V2z"/>
                      <path d="M9 2v2h2"/>
                      <path d="M5.5 7h3M5.5 9.5h3"/>
                    </svg>
                  </span>
                  {{ t('deliverable.title') }}
                </h3>
                <span class="section-count">{{ stage.completed_items }}/{{ stage.total_items }}</span>
              </header>
              <div class="deliverable-grid">
                <div v-for="group in stage.deliverables" :key="group.key" class="deliverable-group">
                  <div class="deliverable-group-name">{{ group.name }}</div>
                  <ul class="deliverable-items" role="list">
                    <li v-for="item in group.items" :key="item.key" class="deliverable-item" role="listitem"
                        :title="item.auto_reason || ''">
                      <span class="status-indicator"
                            :class="{
                              manual: item.is_completed,
                              auto: !item.is_completed && item.auto_status === 'completed',
                              pending: !item.is_completed && item.auto_status !== 'completed'
                            }"
                            :aria-label="getStatusAriaLabel(item)">
                        <template v-if="item.is_completed">
                          <svg viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M2.5 6.5l2.5 2.5 4.5-5"/>
                          </svg>
                        </template>
                        <template v-else-if="item.auto_status === 'completed'">
                          <svg viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M2.5 6.5l2.5 2.5 4.5-5"/>
                          </svg>
                          <span class="auto-flag" aria-hidden="true">{{ t('deliverable.autoCompletedShort') }}</span>
                        </template>
                        <template v-else>
                          <svg viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.6">
                            <circle cx="6" cy="6" r="4"/>
                          </svg>
                        </template>
                      </span>
                      <span class="item-name">{{ item.name }}</span>
                      <span v-if="item.is_optional" class="optional-tag" :aria-label="t('deliverable.optional')">{{ t('deliverable.optional') }}</span>
                    </li>
                  </ul>
                </div>
              </div>
            </section>

            <!-- 阶段任务（折叠） -->
            <details v-if="stage.tasks?.length" class="content-details">
              <summary class="details-summary">
                <span class="summary-chevron" aria-hidden="true">
                  <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" stroke-width="1.6">
                    <path d="M3 2l4 3-4 3"/>
                  </svg>
                </span>
                <span class="summary-label">{{ t('timeline.stageTasks') }}</span>
                <span class="summary-count">{{ stage.tasks.length }}</span>
              </summary>
              <div class="details-body">
                <div v-for="(task, i) in stage.tasks" :key="i" class="task-group">
                  <div class="task-name">{{ task.name }}</div>
                  <ul class="task-sublist">
                    <li v-for="(sub, j) in task.subtasks" :key="j">{{ sub }}</li>
                  </ul>
                </div>
              </div>
            </details>

            <!-- 阶段说明（折叠） -->
            <details class="content-details">
              <summary class="details-summary">
                <span class="summary-chevron" aria-hidden="true">
                  <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" stroke-width="1.6">
                    <path d="M3 2l4 3-4 3"/>
                  </svg>
                </span>
                <span class="summary-label">{{ t('timeline.stageDescription') }}</span>
              </summary>
              <div class="details-body">
                <div class="condition-block">
                  <div class="condition-title">{{ t('timeline.entryConditions') }}</div>
                  <ul class="condition-list">
                    <li v-for="(c, i) in stage.entry_conditions" :key="i">{{ c }}</li>
                  </ul>
                </div>
                <div class="condition-block">
                  <div class="condition-title">{{ t('timeline.exitConditions') }}</div>
                  <ul class="condition-list">
                    <li v-for="(c, i) in stage.exit_conditions" :key="i">{{ c }}</li>
                  </ul>
                </div>
              </div>
            </details>
          </article>
        </li>
      </ol>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const props = defineProps({
  timelineData: { type: Object, default: null },
  loading: { type: Boolean, default: false },
  formatDate: { type: Function, default: (d) => d }
})

const currentStageLabel = computed(() => {
  if (!props.timelineData?.stages) return ''
  const current = props.timelineData.stages.find(s => s.is_current)
  return current?.label || props.timelineData.current_stage || ''
})

// 顶部统计
const stageStats = computed(() => {
  if (!props.timelineData?.stages) return { total: 0, deliverableTotal: 0, deliverableDone: 0 }
  const stages = props.timelineData.stages
  let deliverableTotal = 0
  let deliverableDone = 0
  stages.forEach(s => {
    deliverableTotal += s.total_items || 0
    deliverableDone += s.completed_items || 0
  })
  return { total: stages.length, deliverableTotal, deliverableDone }
})

function getProgressClass(rate) {
  if (rate >= 80) return 'green'
  if (rate >= 40) return 'yellow'
  return 'red'
}

// 紧凑日期：仅显示月-日
function formatShortDate(dateStr) {
  if (!dateStr) return ''
  try {
    const d = new Date(dateStr)
    if (isNaN(d.getTime())) return dateStr
    return new Intl.DateTimeFormat('zh-CN', { month: '2-digit', day: '2-digit' }).format(d)
  } catch (e) {
    return dateStr
  }
}

// 时间：仅显示时:分
function formatTime(dateStr) {
  if (!dateStr) return ''
  try {
    const d = new Date(dateStr)
    if (isNaN(d.getTime())) return ''
    return new Intl.DateTimeFormat('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false }).format(d)
  } catch (e) {
    return ''
  }
}

// 百分比格式化
function formatPercent(rate) {
  return new Intl.NumberFormat('zh-CN', { maximumFractionDigits: 1 }).format(rate) + '%'
}

// 状态徽章的无障碍标签
function getStatusAriaLabel(item) {
  if (item.is_completed) return t('timeline.manuallyCompleted')
  if (item.auto_status === 'completed') return t('timeline.autoCheckComplete', { reason: item.auto_reason || '' })
  return t('timeline.pendingCompletion', { reason: item.auto_reason || t('timeline.needManualConfirm') })
}
</script>

<style scoped>
.stage-timeline {
  font-family: var(--font-sans, 'Noto Sans SC', 'PingFang SC', 'Microsoft YaHei', system-ui, sans-serif);
  font-size: var(--fs-base, 13px);
  color: var(--text-primary, #15171D);
  line-height: 1.5;
}

/* 屏幕阅读器专用 */
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

/* ============ 骨架屏 ============ */
.timeline-skeleton {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.skeleton-row {
  display: grid;
  grid-template-columns: 180px 1fr;
  gap: 20px;
  align-items: stretch;
}

.skeleton-node {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-top: 14px;
}

.skeleton-card {
  border: 1px solid var(--border, #E8E8E0);
  border-radius: 10px;
  padding: 16px 18px;
  background: var(--bg-card, #FCFBF5);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.skeleton-line {
  height: 12px;
  background: linear-gradient(90deg, var(--border, #E8E8E0) 25%, var(--bg-surface, #F8F4EC) 50%, var(--border, #E8E8E0) 75%);
  background-size: 200% 100%;
  border-radius: 4px;
  animation: timeline-shimmer 1.4s ease-in-out infinite;
}

.skeleton-line.w-40 { width: 40%; }
.skeleton-line.w-50 { width: 50%; }
.skeleton-line.w-60 { width: 60%; }
.skeleton-line.w-70 { width: 70%; }
.skeleton-line.w-80 { width: 80%; }
.skeleton-line.w-90 { width: 90%; }

@keyframes timeline-shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* ============ 空状态 ============ */
.timeline-empty {
  text-align: center;
  padding: 60px 16px;
  color: var(--text-muted, #93959D);
}

.empty-icon {
  font-size: 36px;
  color: var(--accent, #CD5036);
  opacity: 0.5;
  margin-bottom: 10px;
  font-weight: 300;
}

.empty-text {
  font-size: var(--fs-sm, 12px);
}

/* ============ 时间线头部 ============ */
.timeline-content {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.timeline-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--border, #E8E8E0);
}

.header-title-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.timeline-title {
  margin: 0;
  font-size: var(--fs-lg, 16px);
  font-weight: 700;
  color: var(--text-primary, #15171D);
  letter-spacing: -0.015em;
  text-wrap: balance;
}

.title-sub {
  color: var(--text-muted, #93959D);
  font-weight: 500;
}

.timeline-current {
  font-size: var(--fs-sm, 12px);
  color: var(--text-secondary, #494A4D);
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.current-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--accent, #CD5036);
  box-shadow: 0 0 0 3px rgba(205, 80, 54, 0.15);
}

.header-meta {
  display: inline-flex;
  align-items: baseline;
  gap: 6px;
  font-size: var(--fs-sm, 12px);
  color: var(--text-muted, #93959D);
  font-variant-numeric: tabular-nums;
}

.meta-label {
  color: var(--text-muted, #93959D);
}

.meta-value {
  font-family: var(--font-mono, 'JetBrains Mono', monospace);
  font-weight: 700;
  color: var(--text-primary, #15171D);
}

.meta-value-accent {
  color: var(--accent, #CD5036);
}

.meta-divider {
  color: var(--border-strong, #D7D4CD);
  margin: 0 2px;
}

/* ============ 时间流瀑布（双列布局） ============ */
.timeline-waterfall {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
}

.timeline-stage-row {
  display: grid;
  grid-template-columns: 180px 1fr;
  gap: 20px;
  align-items: stretch;
  padding-bottom: 20px;
  position: relative;
}

.timeline-stage-row:last-child {
  padding-bottom: 0;
}

/* ============ 左侧节点列 ============ */
.stage-node {
  position: relative;
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding-top: 14px;
}

/* 节点标记：圆点 + 连接线 */
.node-marker {
  position: relative;
  flex-shrink: 0;
  width: 14px;
  height: 14px;
}

.node-dot {
  position: absolute;
  left: 0;
  top: 0;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: var(--bg-card, #FCFBF5);
  border: 2px solid var(--border-strong, #D7D4CD);
  box-sizing: border-box;
  z-index: 1;
  transition: background 0.2s, border-color 0.2s, box-shadow 0.2s, transform 0.2s;
}

.stage-node.current .node-dot {
  background: var(--accent, #CD5036);
  border-color: var(--accent, #CD5036);
  box-shadow: 0 0 0 4px rgba(205, 80, 54, 0.15);
}

.node-line {
  position: absolute;
  left: 5px;
  top: 14px;
  bottom: -34px;
  width: 2px;
  background: var(--border, #E8E8E0);
  z-index: 0;
}

.timeline-stage-row:last-child .node-line {
  display: none;
}

/* 节点主体 */
.node-body {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
  min-width: 0;
}

.node-date {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.date-day {
  font-family: var(--font-mono, 'JetBrains Mono', monospace);
  font-size: var(--fs-md, 14px);
  font-weight: 700;
  color: var(--text-primary, #15171D);
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.01em;
  line-height: 1.2;
}

.date-time {
  font-family: var(--font-mono, 'JetBrains Mono', monospace);
  font-size: var(--fs-xs, 11px);
  color: var(--text-muted, #93959D);
  font-variant-numeric: tabular-nums;
}

.node-title {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.node-label {
  font-size: var(--fs-md, 14px);
  font-weight: 700;
  color: var(--text-primary, #15171D);
  letter-spacing: -0.01em;
  line-height: 1.3;
}

.stage-node.current .node-label {
  color: var(--accent, #CD5036);
}

.node-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.node-om {
  display: inline-flex;
  align-items: center;
  font-family: var(--font-mono, 'JetBrains Mono', monospace);
  font-size: 11px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 4px;
  background: rgba(205, 80, 54, 0.08);
  color: var(--accent, #CD5036);
  white-space: nowrap;
  border: 1px solid rgba(205, 80, 54, 0.15);
}

.node-current-tag {
  display: inline-flex;
  align-items: center;
  font-size: 10px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 3px;
  background: var(--accent, #CD5036);
  color: #fff;
  letter-spacing: 0.02em;
  line-height: 1.2;
}

.node-duration {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: var(--fs-xs, 11px);
  color: var(--text-muted, #93959D);
  margin-top: 8px;
  font-variant-numeric: tabular-nums;
}

.duration-icon {
  display: inline-flex;
  width: 12px;
  height: 12px;
  color: var(--text-muted, #93959D);
}

.duration-icon svg {
  width: 100%;
  height: 100%;
}

/* ============ 右侧内容卡片 ============ */
.stage-content {
  padding: 16px 18px;
  border-radius: 10px;
  background: var(--bg-card, #FCFBF5);
  border: 1px solid var(--border, #E8E8E0);
  transition: background 0.15s, border-color 0.15s, box-shadow 0.15s, transform 0.15s;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.stage-content:hover {
  border-color: var(--border-strong, #D7D4CD);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.stage-content.current {
  border-left: 3px solid var(--accent, #CD5036);
  padding-left: 16px;
  background: linear-gradient(90deg, rgba(205, 80, 54, 0.03), var(--bg-card, #FCFBF5) 20%);
  box-shadow: 0 1px 3px rgba(205, 80, 54, 0.08);
}

/* 卡片头部：核心目标 + 完成度 */
.content-header {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border, #E8E8E0);
}

.header-objective {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.objective-label {
  font-size: var(--fs-xs, 11px);
  font-weight: 700;
  color: var(--text-muted, #93959D);
  font-family: var(--font-mono, 'JetBrains Mono', monospace);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.objective-text {
  margin: 0;
  font-size: var(--fs-sm, 12px);
  color: var(--text-primary, #15171D);
  line-height: 1.6;
  text-wrap: pretty;
}

.header-progress {
  display: flex;
  align-items: center;
  gap: 10px;
}

.progress-meta {
  display: flex;
  align-items: baseline;
  gap: 6px;
  flex-shrink: 0;
}

.progress-label {
  font-size: var(--fs-xs, 11px);
  font-weight: 600;
  color: var(--text-muted, #93959D);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.progress-rate {
  font-family: var(--font-mono, 'JetBrains Mono', monospace);
  font-size: var(--fs-md, 14px);
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.01em;
}

.progress-rate.green { color: var(--green, #118A58); }
.progress-rate.yellow { color: var(--yellow, #B8860B); }
.progress-rate.red { color: var(--red, #C4391C); }

.progress-track {
  flex: 1;
  height: 6px;
  background: var(--border, #E8E8E0);
  border-radius: 3px;
  overflow: hidden;
  min-width: 80px;
}

.progress-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.4s ease-out;
}

.progress-fill.green { background: var(--green, #118A58); }
.progress-fill.yellow { background: var(--yellow, #CBB88C); }
.progress-fill.red { background: var(--red, #C4391C); }

.progress-count {
  font-family: var(--font-mono, 'JetBrains Mono', monospace);
  font-size: var(--fs-xs, 11px);
  color: var(--text-muted, #93959D);
  font-variant-numeric: tabular-nums;
  flex-shrink: 0;
}

/* ============ 内容区块（交付物） ============ */
.content-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.section-title {
  margin: 0;
  font-size: var(--fs-xs, 11px);
  font-weight: 700;
  color: var(--text-secondary, #494A4D);
  font-family: var(--font-mono, 'JetBrains Mono', monospace);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.section-icon {
  display: inline-flex;
  width: 12px;
  height: 12px;
  color: var(--text-muted, #93959D);
}

.section-icon svg {
  width: 100%;
  height: 100%;
}

.section-count {
  font-family: var(--font-mono, 'JetBrains Mono', monospace);
  font-size: var(--fs-xs, 11px);
  color: var(--text-muted, #93959D);
  font-variant-numeric: tabular-nums;
  padding: 1px 6px;
  background: var(--bg-surface, #F8F4EC);
  border-radius: 3px;
  border: 1px solid var(--border, #E8E8E0);
}

/* ============ 交付物分组网格 ============ */
.deliverable-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
}

.deliverable-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 8px 10px;
  border-radius: 6px;
  background: var(--bg-surface, #F8F4EC);
  border: 1px solid var(--border, #E8E8E0);
  min-width: 0;
}

.deliverable-group-name {
  font-size: var(--fs-xs, 11px);
  font-weight: 700;
  color: var(--text-secondary, #494A4D);
  text-transform: uppercase;
  letter-spacing: 0.03em;
  padding: 0 2px 2px 2px;
  border-bottom: 1px dashed var(--border, #E8E8E0);
  margin-bottom: 2px;
}

.deliverable-items {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.deliverable-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 4px;
  border-radius: 4px;
  transition: background 0.15s;
  min-width: 0;
}

.deliverable-item:hover {
  background: var(--bg-card, #FCFBF5);
}

/* 状态徽章 */
.status-indicator {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border-radius: 9px;
  font-size: 11px;
  font-weight: 700;
  line-height: 1;
  flex-shrink: 0;
  position: relative;
}

.status-indicator svg {
  width: 12px;
  height: 12px;
}

.status-indicator.manual {
  color: var(--accent, #CD5036);
  background: rgba(205, 80, 54, 0.1);
}

.status-indicator.auto {
  color: var(--green, #118A58);
  background: var(--green-light, rgba(17, 138, 88, 0.08));
}

.status-indicator.pending {
  color: var(--text-muted, #93959D);
  background: transparent;
}

.auto-flag {
  position: absolute;
  top: -5px;
  right: -10px;
  font-size: 9px;
  font-weight: 700;
  line-height: 1;
  padding: 1px 3px;
  border-radius: 2px;
  background: var(--green, #118A58);
  color: #fff;
  font-family: var(--font-mono, 'JetBrains Mono', monospace);
}

.item-name {
  flex: 1;
  min-width: 0;
  color: var(--text-primary, #15171D);
  font-size: var(--fs-sm, 12px);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.optional-tag {
  font-family: var(--font-mono, 'JetBrains Mono', monospace);
  font-size: 10px;
  padding: 1px 5px;
  border: 1px solid var(--border, #E8E8E0);
  border-radius: 2px;
  color: var(--text-muted, #93959D);
  background: var(--bg-card, #FCFBF5);
  flex-shrink: 0;
}

/* ============ 折叠区块 ============ */
.content-details {
  border-top: 1px solid var(--border, #E8E8E0);
  padding-top: 6px;
  margin-top: 2px;
}

.content-details[open] {
  padding-bottom: 4px;
}

.details-summary {
  padding: 6px 0;
  cursor: pointer;
  font-size: var(--fs-xs, 11px);
  font-weight: 600;
  color: var(--text-secondary, #494A4D);
  list-style: none;
  user-select: none;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: color 0.15s;
  border-radius: 3px;
  outline: none;
  touch-action: manipulation;
}

.details-summary::-webkit-details-marker {
  display: none;
}

.summary-chevron {
  display: inline-flex;
  width: 10px;
  height: 10px;
  color: var(--text-muted, #93959D);
  transition: transform 0.2s;
}

.summary-chevron svg {
  width: 100%;
  height: 100%;
}

.content-details[open] .summary-chevron {
  transform: rotate(90deg);
}

.details-summary:hover {
  color: var(--text-primary, #15171D);
}

.details-summary:focus-visible {
  outline: 2px solid var(--focus-ring, #15171D);
  outline-offset: 2px;
  border-radius: 3px;
}

.summary-label {
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.summary-count {
  font-family: var(--font-mono, 'JetBrains Mono', monospace);
  color: var(--text-muted, #93959D);
  font-variant-numeric: tabular-nums;
  margin-left: auto;
  padding: 1px 6px;
  background: var(--bg-surface, #F8F4EC);
  border-radius: 3px;
  border: 1px solid var(--border, #E8E8E0);
}

.details-body {
  padding: 6px 0 8px 16px;
  font-size: var(--fs-sm, 12px);
  color: var(--text-secondary, #494A4D);
}

/* 阶段任务 */
.task-group + .task-group {
  margin-top: 8px;
}

.task-name {
  font-size: var(--fs-sm, 12px);
  font-weight: 600;
  color: var(--text-primary, #15171D);
  margin-bottom: 2px;
}

.task-sublist {
  margin: 0;
  padding-left: 18px;
  color: var(--text-secondary, #494A4D);
  line-height: 1.7;
}

.task-sublist li {
  margin-bottom: 2px;
}

/* 阶段说明 */
.condition-block {
  border-left: 2px solid var(--border, #E8E8E0);
  padding-left: 10px;
  margin-bottom: 8px;
}

.condition-block:last-child {
  margin-bottom: 0;
}

.stage-content.current .condition-block {
  border-left-color: var(--accent, #CD5036);
}

.condition-title {
  font-size: var(--fs-xs, 11px);
  font-weight: 700;
  color: var(--text-secondary, #494A4D);
  font-family: var(--font-mono, 'JetBrains Mono', monospace);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 4px;
}

.condition-list {
  margin: 0;
  padding-left: 18px;
  color: var(--text-secondary, #494A4D);
  line-height: 1.7;
}

.condition-list li {
  margin-bottom: 2px;
}

/* ============ 响应式 ============ */
@media (max-width: 720px) {
  .timeline-stage-row {
    grid-template-columns: 1fr;
    gap: 8px;
  }

  .stage-node {
    padding-top: 8px;
    flex-direction: row;
    align-items: flex-start;
    gap: 10px;
  }

  .node-body {
    flex-direction: row;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 6px 12px;
  }

  .node-date {
    flex-direction: row;
    gap: 6px;
    align-items: baseline;
  }

  .node-title {
    flex-direction: row;
    align-items: center;
    gap: 6px;
    flex: 1;
    min-width: 0;
  }

  .node-duration {
    flex-basis: 100%;
    margin-top: 4px;
    padding-left: 0;
  }

  .node-line {
    display: none;
  }

  .deliverable-grid {
    grid-template-columns: 1fr;
  }

  .header-progress {
    flex-wrap: wrap;
  }

  .progress-track {
    order: 3;
    width: 100%;
    flex-basis: 100%;
  }
}

/* ============ 动画无障碍 ============ */
@media (prefers-reduced-motion: reduce) {
  .skeleton-line,
  .progress-fill,
  .summary-chevron,
  .node-dot,
  .stage-content,
  .deliverable-item {
    transition: none;
    animation: none;
  }

  .skeleton-line {
    background: var(--border, #E8E8E0);
  }
}
</style>

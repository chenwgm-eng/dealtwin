<template>
  <div class="attention-items">
    <!-- 加载状态 -->
    <div v-if="loading" class="attention-loading" aria-live="polite">
      <span class="attention-spinner" aria-hidden="true"></span>
      <span>{{ t('common.loading') }}</span>
    </div>

    <template v-else>
      <!-- 空状态（全部为空时单独显示，避免堆叠空白区块） -->
      <div v-if="isAllEmpty" class="attention-empty" role="status">
        <span class="attention-empty-icon" aria-hidden="true">✓</span>
        <span>{{ t('dashboard.noAttentionItems') }}</span>
      </div>

      <template v-else>
        <!-- 统计卡片网格：4 列紧凑布局（纯展示，不可点击） -->
        <div class="attention-stats-grid" role="list">
          <div
            class="attention-stat-card"
            :class="{ 'has-alert': (items?.today_due_count || 0) > 0 }"
            role="listitem"
            :aria-label="t('dashboard.todayDueTasksCount', { count: items?.today_due_count || 0 })"
          >
            <span class="stat-value" :class="{ 'stat-warning': items?.today_due_count > 0 }">{{ items?.today_due_count || 0 }}</span>
            <span class="stat-label">{{ t('dashboard.todayDueTasks') }}</span>
          </div>

          <div
            class="attention-stat-card"
            :class="{ 'has-alert': (items?.pending_stakeholders_count || 0) > 0 }"
            role="listitem"
            :aria-label="t('dashboard.pendingStakeholdersCount', { count: items?.pending_stakeholders_count || 0 })"
          >
            <span class="stat-value" :class="{ 'stat-warning': items?.pending_stakeholders_count > 0 }">{{ items?.pending_stakeholders_count || 0 }}</span>
            <span class="stat-label">{{ t('dashboard.pendingStakeholders') }}</span>
          </div>

          <div
            class="attention-stat-card"
            :class="{ 'has-alert': (items?.red_contacts_count || 0) > 0 }"
            role="listitem"
            :aria-label="t('dashboard.redContactsCount', { count: items?.red_contacts_count || 0 })"
          >
            <span class="stat-value" :class="{ 'stat-danger': items?.red_contacts_count > 0 }">{{ items?.red_contacts_count || 0 }}</span>
            <span class="stat-label">{{ t('dashboard.redStatusContacts') }}</span>
          </div>

          <div
            class="attention-stat-card"
            :class="{ 'has-alert': (items?.pending_plans_count || 0) > 0 }"
            role="listitem"
            :aria-label="t('dashboard.unreviewedPlansCount', { count: items?.pending_plans_count || 0 })"
          >
            <span class="stat-value" :class="{ 'stat-warning': items?.pending_plans_count > 0 }">{{ items?.pending_plans_count || 0 }}</span>
            <span class="stat-label">{{ t('dashboard.unreviewedVisitPlans') }}</span>
          </div>
        </div>

        <!-- 逾期待办列表：紧凑单行布局 -->
        <section
          v-if="items?.overdue_tasks?.length > 0"
          class="attention-overdue-section"
          aria-labelledby="overdue-heading"
        >
          <h3 id="overdue-heading" class="attention-section-title">
            <span class="attention-deco" aria-hidden="true">⚠</span>
            {{ t('dashboard.overdueTasks') }}
            <span class="attention-overdue-count" :aria-label="t('dashboard.totalCount', { count: items?.overdue_count || 0 })">{{ items?.overdue_count || 0 }}</span>
          </h3>

          <ul class="overdue-list">
            <li v-for="task in items.overdue_tasks" :key="task.id">
              <button
                type="button"
                class="overdue-item"
                @click="goToTask(task)"
                :aria-label="t('dashboard.jumpToTask', { title: task.title, priority: priorityLabel(task.priority), date: formatDate(task.due_date) })"
              >
                <!-- 单行：优先级 + 标题 + 项目 + 日期 -->
                <span class="overdue-priority" :class="`priority-${task.priority}`" aria-hidden="true">{{ priorityLabel(task.priority) }}</span>
                <span class="overdue-title" :title="task.title">{{ task.title }}</span>
                <span class="overdue-project" :title="task.project_name">{{ task.project_name || t('project.unknownProject') }}</span>
                <span class="overdue-due-date">{{ formatDate(task.due_date) }}</span>
              </button>
            </li>
          </ul>
        </section>
      </template>
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

// Props：重点关注事项聚合
const props = defineProps({
  items: {
    type: Object,
    default: () => ({})
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const router = useRouter()

// 日期格式化：YYYY-MM-DD（紧凑形式 MM/DD）
const dateFormatter = new Intl.DateTimeFormat('zh-CN', {
  month: '2-digit',
  day: '2-digit'
})
function formatDate(dateStr) {
  if (!dateStr) return '—'
  const d = new Date(dateStr)
  if (isNaN(d.getTime())) return '—'
  return dateFormatter.format(d).replace(/\//g, '/')
}

// 优先级文案映射
function priorityLabel(priority) {
  return t(`workspace.priorityLabels.${priority}`) ?? priority
}

// 全部为空：所有计数为 0 且无逾期待办
const isAllEmpty = computed(() => {
  if (!props.items) return true
  const counts = [
    props.items.today_due_count,
    props.items.pending_stakeholders_count,
    props.items.red_contacts_count,
    props.items.pending_plans_count
  ]
  const allCountsZero = counts.every((c) => !c)
  const noOverdue = !props.items.overdue_tasks || props.items.overdue_tasks.length === 0
  return allCountsZero && noOverdue
})

// 跳转到具体项目的待办列表（仅逾期待办列表项使用）
function goToTask(task) {
  router.push({
    path: '/sales-twin',
    query: { project: task.project_id, menu: 'tasks' }
  })
}
</script>

<style scoped>
/* ============ 容器 ============ */
.attention-items {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

/* ============ 加载状态 ============ */
.attention-loading {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 24px;
  color: var(--text-secondary);
  font-size: 13px;
  justify-content: center;
}

.attention-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: attention-spin 0.8s linear infinite;
  transform-origin: center;
}

@keyframes attention-spin {
  to { transform: rotate(360deg); }
}

/* ============ 统计卡片 4 列网格（紧凑） ============ */
.attention-stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
}

.attention-stat-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 12px;
  text-align: left;
  font: inherit;
  color: inherit;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  min-height: 60px;
}

/* 告警态：左侧色条提示 */
.attention-stat-card.has-alert {
  position: relative;
}

.attention-stat-card.has-alert::before {
  content: '';
  position: absolute;
  left: 0;
  top: 8px;
  bottom: 8px;
  width: 2px;
  border-radius: 0 2px 2px 0;
  background: var(--yellow);
}

.stat-value {
  font-family: 'JetBrains Mono', 'SF Mono', monospace;
  font-size: 20px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  line-height: 1.1;
  color: var(--text-primary);
}

.stat-warning { color: var(--yellow); }
.stat-danger { color: var(--red); }

.stat-label {
  font-size: 11px;
  color: var(--text-tertiary);
  letter-spacing: 0.02em;
  line-height: 1.3;
  /* 允许换行，确保完整显示 */
  word-break: keep-all;
  white-space: normal;
  text-wrap: balance;
}

/* ============ 逾期待办区块 ============ */
.attention-overdue-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.attention-section-title {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 6px;
}

.attention-deco {
  color: var(--red);
  font-weight: 400;
}

.attention-overdue-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 18px;
  height: 16px;
  padding: 0 5px;
  font-size: 10px;
  font-family: 'JetBrains Mono', 'SF Mono', monospace;
  font-weight: 600;
  color: var(--red);
  background: rgba(196, 57, 28, 0.1);
  border-radius: 8px;
}

/* ============ 逾期待办列表：单行紧凑 ============ */
.overdue-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
  /* 最大高度限制（同步行高 1.5 倍调整），超出滚动，避免占据过多垂直空间 */
  max-height: 360px;
  overflow-y: auto;
  overscroll-behavior: contain;
}

.overdue-item {
  width: 100%;
  text-align: left;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 6px;
  /* 行高调整为原 1.5 倍：padding 8px→12px、gap 8px→12px、font-size 12px→13px、line-height 1.4→1.6 */
  padding: 12px 15px;
  cursor: pointer;
  font: inherit;
  color: inherit;
  /* 单行布局：优先级 | 标题 | 项目 | 日期 */
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 13px;
  line-height: 1.6;
  transition: border-color 0.15s, background 0.15s;
}

.overdue-item:hover {
  border-color: var(--accent);
  background: var(--bg-surface);
}

.overdue-item:focus-visible {
  outline: 2px solid var(--focus-ring, #15171D);
  outline-offset: 1px;
}

/* 优先级标签（固定宽度） */
.overdue-priority {
  flex-shrink: 0;
  padding: 2px 6px;
  border: 1px solid var(--border);
  border-radius: 2px;
  font-size: 11px;
  font-family: 'JetBrains Mono', 'SF Mono', monospace;
  font-weight: 600;
  line-height: 1.4;
}

.priority-high {
  border-color: var(--red);
  color: var(--red);
}
.priority-medium {
  border-color: var(--yellow);
  color: var(--yellow);
}
.priority-low {
  border-color: var(--text-muted);
  color: var(--text-muted);
}

/* 标题：flex 主项，可截断 */
.overdue-title {
  flex: 1 1 auto;
  min-width: 0;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 项目名：固定宽度，可截断 */
.overdue-project {
  flex: 0 1 140px;
  min-width: 0;
  color: var(--text-secondary);
  font-size: 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 日期：固定宽度，等宽数字 */
.overdue-due-date {
  flex-shrink: 0;
  color: var(--text-muted);
  font-size: 12px;
  font-family: 'JetBrains Mono', 'SF Mono', monospace;
  font-variant-numeric: tabular-nums;
}

/* ============ 空状态 ============ */
.attention-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 16px;
  color: var(--text-muted);
  font-size: 12px;
  background: var(--bg-card);
  border: 1px dashed var(--border);
  border-radius: 8px;
}

.attention-empty-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--green);
  color: #ffffff;
  font-size: 11px;
  font-weight: 700;
}

/* ============ 响应式 ============ */
@media (max-width: 768px) {
  .attention-stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .overdue-item {
    /* 窄屏：允许换行但保持紧凑 */
    flex-wrap: wrap;
  }

  .overdue-title {
    flex: 1 1 100%;
    order: 2;
    margin-top: 2px;
  }

  .overdue-project {
    flex: 1 1 auto;
    order: 3;
  }

  .overdue-priority {
    order: 1;
  }

  .overdue-due-date {
    order: 4;
  }
}

/* ============ 动画无障碍 ============ */
@media (prefers-reduced-motion: reduce) {
  .attention-spinner {
    animation: none;
  }
  .attention-stat-card,
  .overdue-item {
    transition: none;
  }
}
</style>

<template>
  <div class="dashboard-metrics">
    <!-- 加载状态 -->
    <div v-if="loading" class="metrics-loading">
      <span class="metrics-spinner"></span>
      <span>{{ t('common.loading') }}</span>
    </div>
    <div v-else class="metrics-row">
      <!-- 1. 线索金额 -->
      <button
        type="button"
        class="metric-card metric-card-lead"
        @click="goToProjects"
        :aria-label="t('dashboard.jumpToProjectsLead')"
      >
        <div class="metric-value">{{ formatCurrency(expectedClose?.lead_amount) }}</div>
        <div class="metric-label">{{ t('dashboard.leadAmount') }}</div>
        <div class="metric-sub">{{ t('dashboard.projectCount', { count: expectedClose?.lead_count || 0 }) }}</div>
      </button>

      <!-- 2. 商机金额（悬浮显示明细，点击跳转） -->
      <div
        class="metric-card metric-card-opportunity metric-card-popover"
        tabindex="0"
        role="button"
        :aria-label="t('dashboard.opportunityAmountAria')"
        :aria-describedby="showBreakdown ? 'opportunity-popover' : undefined"
        @click="goToProjects"
        @mouseenter="showBreakdown = true"
        @mouseleave="showBreakdown = false"
        @focus="showBreakdown = true"
        @blur="showBreakdown = false"
        @keydown.enter="goToProjects"
        @keydown.space.prevent="goToProjects"
        @keydown.esc="showBreakdown = false"
      >
        <div class="metric-value">{{ formatCurrency(expectedClose?.opportunity_amount) }}</div>
        <div class="metric-label">{{ t('dashboard.opportunityAmount') }}</div>
        <div class="metric-sub">{{ t('dashboard.projectCount', { count: expectedClose?.opportunity_count || 0 }) }} · {{ t('dashboard.hoverForDetails') }}</div>
        <!-- popover -->
        <div
          v-if="showBreakdown"
          id="opportunity-popover"
          class="metric-popover"
          role="tooltip"
        >
          <div class="popover-title">{{ t('dashboard.opportunityBreakdown') }}</div>
          <div class="popover-item popover-identity">
            <span class="popover-dot"></span>
            <span class="popover-label">{{ t('stages.identity') }}</span>
            <span class="popover-amount">{{ formatCurrency(expectedClose?.opportunity_breakdown?.identity?.amount) }}</span>
            <span class="popover-count">{{ t('dashboard.itemCount', { count: expectedClose?.opportunity_breakdown?.identity?.count || 0 }) }}</span>
          </div>
          <div class="popover-item popover-define">
            <span class="popover-dot"></span>
            <span class="popover-label">{{ t('stages.define') }}</span>
            <span class="popover-amount">{{ formatCurrency(expectedClose?.opportunity_breakdown?.define?.amount) }}</span>
            <span class="popover-count">{{ t('dashboard.itemCount', { count: expectedClose?.opportunity_breakdown?.define?.count || 0 }) }}</span>
          </div>
          <div class="popover-item popover-confirm">
            <span class="popover-dot"></span>
            <span class="popover-label">{{ t('stages.confirm') }}</span>
            <span class="popover-amount">{{ formatCurrency(expectedClose?.opportunity_breakdown?.confirm?.amount) }}</span>
            <span class="popover-count">{{ t('dashboard.itemCount', { count: expectedClose?.opportunity_breakdown?.confirm?.count || 0 }) }}</span>
          </div>
        </div>
      </div>

      <!-- 3. 赢单金额 -->
      <button
        type="button"
        class="metric-card metric-card-won"
        @click="goToProjects"
        :aria-label="t('dashboard.jumpToProjectsWon')"
      >
        <div class="metric-value metric-value-won">{{ formatCurrency(actualClose?.won_amount) }}</div>
        <div class="metric-label">{{ t('dashboard.wonAmount') }}</div>
        <div class="metric-sub">{{ t('dashboard.projectCount', { count: actualClose?.won_count || 0 }) }}</div>
      </button>

      <!-- 4. 丢单金额 -->
      <button
        type="button"
        class="metric-card metric-card-lost"
        @click="goToProjects"
        :aria-label="t('dashboard.jumpToProjectsLost')"
      >
        <div class="metric-value metric-value-lost">{{ formatCurrency(actualClose?.lost_amount) }}</div>
        <div class="metric-label">{{ t('dashboard.lostAmount') }}</div>
        <div class="metric-sub">{{ t('dashboard.projectCount', { count: actualClose?.lost_count || 0 }) }}</div>
      </button>

      <!-- 5. 赢单率 -->
      <button
        type="button"
        class="metric-card metric-card-winrate"
        @click="goToProjects"
        :aria-label="t('dashboard.jumpToProjectsClosed')"
      >
        <div class="metric-value metric-value-winrate">
          {{ actualClose?.win_rate != null ? Math.round(actualClose.win_rate) : '—' }}
          <span v-if="actualClose?.win_rate != null" class="metric-unit">%</span>
        </div>
        <div class="metric-label">{{ t('dashboard.winRate') }}</div>
        <div class="metric-sub">{{ t('dashboard.closedCount', { count: (actualClose?.won_count || 0) + (actualClose?.lost_count || 0) }) }}</div>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

// Props：预计关单 / 实际关单聚合数据
defineProps({
  expectedClose: {
    type: Object,
    default: () => ({})
  },
  actualClose: {
    type: Object,
    default: () => ({})
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const router = useRouter()

// 商机金额明细展开状态
const showBreakdown = ref(false)

// 跳转到商机台账
function goToProjects() {
  router.push({ path: '/sales-twin', query: { menu: 'projects' } })
}

// 金额格式化：≥10000 用紧凑表示法（万、亿），否则保留两位小数
const currencyFormatter = new Intl.NumberFormat('zh-CN', {
  style: 'currency',
  currency: 'CNY',
  maximumFractionDigits: 2
})
const currencyCompactFormatter = new Intl.NumberFormat('zh-CN', {
  style: 'currency',
  currency: 'CNY',
  notation: 'compact',
  maximumFractionDigits: 2
})
function formatCurrency(val) {
  if (val == null) return '¥0'
  const n = Number(val)
  if (isNaN(n)) return '¥0'
  return n >= 10000 ? currencyCompactFormatter.format(n) : currencyFormatter.format(n)
}
</script>

<style scoped>
/* 容器 */
.dashboard-metrics {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* 加载状态 */
.metrics-loading {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 32px;
  color: var(--text-secondary);
  font-size: 13px;
  justify-content: center;
}

.metrics-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: metrics-spin 0.8s linear infinite;
}

@keyframes metrics-spin {
  to { transform: rotate(360deg); }
}

/* 5 列网格 */
.metrics-row {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
}

/* 响应式断点 */
@media (max-width: 1279px) {
  .metrics-row {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 1023px) {
  .metrics-row {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 767px) {
  .metrics-row {
    grid-template-columns: 1fr;
  }
}

/* 指标卡片基础样式：左侧 3px 色条 + 可点击 */
.metric-card {
  position: relative;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 16px 18px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  overflow: hidden;
  min-height: 96px;
  transition: border-color 0.15s, box-shadow 0.15s, transform 0.1s;
  /* button 重置 */
  font: inherit;
  color: inherit;
  text-align: left;
  cursor: pointer;
  font-family: var(--font-sans, 'Noto Sans SC', system-ui, sans-serif);
}

.metric-card:hover {
  border-color: var(--accent);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  transform: translateY(-1px);
}

.metric-card:focus-visible {
  outline: 2px solid var(--focus-ring, #15171D);
  outline-offset: 2px;
}

.metric-card:active {
  transform: translateY(0);
}

.metric-card::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
}

/* 左色条颜色变体 */
.metric-card-lead::before { background: var(--yellow); }
.metric-card-opportunity::before { background: var(--blue); }
.metric-card-won::before { background: var(--green); }
.metric-card-lost::before { background: var(--red); }
.metric-card-winrate::before { background: var(--accent); }

/* 商机金额卡片：可聚焦，有指针手势 */
.metric-card-popover {
  position: relative;
}

/* 数值显示 */
.metric-value {
  font-family: 'JetBrains Mono', 'SF Mono', monospace;
  font-size: 22px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  line-height: 1.2;
  color: var(--text-primary);
}

.metric-value-won { color: var(--green); }
.metric-value-lost { color: var(--red); }
.metric-value-winrate { color: var(--green); }

.metric-unit {
  font-size: 16px;
  font-weight: 500;
  margin-left: 2px;
}

.metric-label {
  font-size: 12px;
  color: var(--text-tertiary);
  letter-spacing: 0.02em;
}

.metric-sub {
  font-size: 11px;
  color: var(--text-muted);
}

/* Popover 悬浮明细 */
.metric-popover {
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  margin-top: 8px;
  background: var(--bg-card);
  border: 1px solid var(--border-strong, #D7D4CD);
  border-radius: 8px;
  padding: 12px 14px;
  min-width: 220px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
  z-index: 10;
  font-size: 12px;
}

/* popover 小箭头 */
.metric-popover::before {
  content: '';
  position: absolute;
  top: -6px;
  left: 50%;
  transform: translateX(-50%) rotate(45deg);
  width: 10px;
  height: 10px;
  background: var(--bg-card);
  border-left: 1px solid var(--border-strong, #D7D4CD);
  border-top: 1px solid var(--border-strong, #D7D4CD);
}

.popover-title {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-tertiary);
  letter-spacing: 0.04em;
  text-transform: uppercase;
  margin-bottom: 8px;
  padding-bottom: 6px;
  border-bottom: 1px dashed var(--border);
}

.popover-item {
  display: grid;
  grid-template-columns: 10px 1fr auto auto;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
}

.popover-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.popover-identity .popover-dot { background: var(--blue); }
.popover-define .popover-dot { background: var(--green); }
.popover-confirm .popover-dot { background: var(--accent); }

.popover-label {
  color: var(--text-secondary);
}

.popover-amount {
  font-family: 'JetBrains Mono', 'SF Mono', monospace;
  font-variant-numeric: tabular-nums;
  font-weight: 600;
  color: var(--text-primary);
}

.popover-count {
  font-size: 11px;
  color: var(--text-muted);
}

@media (prefers-reduced-motion: reduce) {
  .metrics-spinner {
    animation: none;
  }
  .metric-card:hover {
    transform: none;
  }
}
</style>

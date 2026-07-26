<template>
  <div class="sales-twin dashboard-page" :class="{ embedded: embedded }">
    <!-- 顶部导航栏 -->
    <header v-if="!embedded" class="dashboard-nav">
      <div class="dashboard-nav-left">
        <h1 class="dashboard-nav-title">{{ t('sidebar.salesWorkspace') }}</h1>
      </div>
      <nav class="dashboard-nav-links" :aria-label="t('dashboard.mainNav')">
        <router-link to="/sales-twin" class="dashboard-nav-link">{{ t('sidebar.brandTitle') }}</router-link>
      </nav>
    </header>

    <!-- 主内容区（支持上下滚动） -->
    <main class="dashboard-main">
      <!-- 页面标题区 + 时间范围选择器 -->
      <div class="dashboard-header">
        <div class="dashboard-header-left">
          <span class="dashboard-deco">◇</span>
          <h2 class="dashboard-title">{{ t('dashboard.salesOverview') }}</h2>
        </div>
        <TimeRangeSelector v-model="timeRange" @update:modelValue="onTimeRangeChange" />
      </div>

      <!-- 错误状态 -->
      <div v-if="error" class="dashboard-error" role="alert">
        <div class="dashboard-error-icon" aria-hidden="true">!</div>
        <div class="dashboard-error-body">
          <p class="dashboard-error-title">{{ t('dashboard.loadFailed') }}</p>
          <p class="dashboard-error-desc">{{ error }}</p>
        </div>
        <button type="button" class="dashboard-retry-btn" @click="loadDashboardData">{{ t('common.retry') }}</button>
      </div>

      <template v-else>
        <!-- 核心指标区 -->
        <DashboardMetrics
          :expectedClose="dashboardData?.expected_close"
          :actualClose="dashboardData?.actual_close"
          :loading="loading"
        />

        <!-- 重点关注事项区 -->
        <section class="dashboard-section" :aria-label="t('dashboard.attentionItems')">
          <div class="dashboard-section-header">
            <span class="dashboard-section-deco">◇</span>
            <h3 class="dashboard-section-title">{{ t('dashboard.attentionItems') }}</h3>
          </div>
          <AttentionItems
            :items="dashboardData?.attention_items"
            :loading="loading"
          />
        </section>

        <!-- LLM 智能洞察区 -->
        <section class="dashboard-section" :aria-label="t('dashboard.aiInsight')">
          <div class="dashboard-section-header">
            <div class="dashboard-section-title-row">
              <span class="dashboard-section-deco">◆</span>
              <h3 class="dashboard-section-title">{{ t('dashboard.aiInsight') }}</h3>
            </div>
            <button
              type="button"
              class="dashboard-refresh-btn"
              @click="refreshInsights"
              :disabled="refreshingInsights"
              :aria-label="refreshingInsights ? t('dashboard.refreshingInsight') : t('dashboard.refreshInsight')"
            >
              <span aria-hidden="true">↻</span>
              {{ refreshingInsights ? t('dashboard.refreshing') : t('dashboard.refreshInsight') }}
            </button>
          </div>
          <InsightPanel
            :insights="dashboardData?.llm_insights"
            :loading="loading || refreshingInsights"
            @retry="loadDashboardData"
          />
        </section>

        <!-- 底部快速链接 -->
        <div v-if="!embedded" class="dashboard-footer">
          <router-link to="/sales-twin" class="dashboard-footer-link">
            {{ t('dashboard.viewAllProjects') }}
            <span class="dashboard-footer-arrow" aria-hidden="true">→</span>
          </router-link>
        </div>
      </template>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import TimeRangeSelector from '@/components/dashboard/TimeRangeSelector.vue'
import DashboardMetrics from '@/components/dashboard/DashboardMetrics.vue'
import AttentionItems from '@/components/dashboard/AttentionItems.vue'
import InsightPanel from '@/components/dashboard/InsightPanel.vue'
import { getDashboard, refreshDashboardInsights } from '@/api/salesTwin'

const { t } = useI18n()

defineProps({
  embedded: {
    type: Boolean,
    default: false
  }
})

const router = useRouter()

// 响应式状态
const dashboardData = ref(null)
const loading = ref(false)
const error = ref(null)
const refreshingInsights = ref(false)
const timeRange = ref({
  period: 'this_quarter',
  start: '',
  end: '',
  label: t('dashboard.thisQuarter')
})

// 加载 Dashboard 数据
async function loadDashboardData() {
  loading.value = true
  error.value = null
  try {
    const params = {}
    if (timeRange.value.period === 'custom' && timeRange.value.start && timeRange.value.end) {
      params.start = timeRange.value.start
      params.end = timeRange.value.end
    } else if (timeRange.value.period !== 'custom') {
      params.period = timeRange.value.period
    }
    const res = await getDashboard(params)
    dashboardData.value = res
    // 同步后端返回的时间范围标签
    if (res?.time_range) {
      timeRange.value = {
        ...timeRange.value,
        start: res.time_range.start,
        end: res.time_range.end,
        label: res.time_range.label
      }
    }
  } catch (e) {
    console.error('[Dashboard] 加载失败:', e)
    error.value = e?.message || t('dashboard.networkErrorHint')
  } finally {
    loading.value = false
  }
}

// 刷新智能洞察（清缓存并触发 LLM 重新生成）
async function refreshInsights() {
  if (refreshingInsights.value) return
  refreshingInsights.value = true
  try {
    const params = {}
    if (timeRange.value.period === 'custom' && timeRange.value.start && timeRange.value.end) {
      params.start = timeRange.value.start
      params.end = timeRange.value.end
    } else if (timeRange.value.period !== 'custom') {
      params.period = timeRange.value.period
    }
    await refreshDashboardInsights(params)
    // 刷新成功后重新加载 dashboard 数据（此时缓存已清，会重新调用 LLM）
    await loadDashboardData()
  } catch (e) {
    console.error('[Dashboard] 刷新洞察失败:', e)
    error.value = e?.message || t('dashboard.refreshInsightFailed')
  } finally {
    refreshingInsights.value = false
  }
}

// 时间范围变化时重新加载
function onTimeRangeChange(newRange) {
  timeRange.value = newRange
  loadDashboardData()
}

// 组件挂载时加载数据
onMounted(() => {
  loadDashboardData()
})
</script>

<style scoped>
/* ============ Dashboard 页面布局 ============ */
.dashboard-page {
  min-height: 100vh;
  background: var(--bg-base, #F4F0E7);
  display: flex;
  flex-direction: column;
  font-family: var(--font-sans, 'Noto Sans SC', system-ui, sans-serif);
  color: var(--text-primary, #15171D);
}

/* ============ 嵌入模式（嵌入 SalesTwin 主内容区） ============ */
.dashboard-page.embedded {
  min-height: 100%;
  height: 100%;
  background: transparent;
}

.dashboard-page.embedded .dashboard-main {
  padding: 20px 24px 24px;
  height: 100%;
  overflow-y: auto;
}

/* ============ 顶部导航栏 ============ */
.dashboard-nav {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 32px;
  background: var(--bg-card, #FCFBF5);
  border-bottom: 1px solid var(--border, #E8E8E0);
  flex-shrink: 0;
}

.dashboard-nav-title {
  font-size: 18px;
  font-weight: 700;
  margin: 0;
  color: var(--text-primary, #15171D);
  letter-spacing: -0.01em;
}

.dashboard-nav-links {
  display: flex;
  gap: 20px;
}

.dashboard-nav-link {
  font-size: 13px;
  color: var(--text-secondary, #494A4D);
  text-decoration: none;
  padding: 6px 12px;
  border-radius: 6px;
  transition: color 0.15s, background 0.15s;
}

.dashboard-nav-link:hover {
  color: var(--accent, #CD5036);
  background: rgba(205, 80, 54, 0.06);
}

.dashboard-nav-link:focus-visible {
  outline: 2px solid var(--focus-ring, #15171D);
  outline-offset: 2px;
}

/* ============ 主内容区 ============ */
.dashboard-main {
  flex: 1;
  overflow-y: auto;
  padding: 28px 32px 40px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* ============ 页面标题区 ============ */
.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--divider, #D7D4CD);
  flex-wrap: wrap;
}

.dashboard-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.dashboard-deco {
  color: var(--accent, #CD5036);
  font-size: 14px;
  font-weight: 300;
}

.dashboard-title {
  font-size: 20px;
  font-weight: 700;
  margin: 0;
  color: var(--text-primary, #15171D);
  letter-spacing: -0.01em;
}

/* ============ 区块通用样式 ============ */
.dashboard-section {
  background: transparent;
}

.dashboard-section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
}

.dashboard-section-deco {
  color: var(--accent, #CD5036);
  font-size: 14px;
  font-weight: 300;
}

.dashboard-section-title {
  font-size: 15px;
  font-weight: 600;
  margin: 0;
  color: var(--text-primary, #15171D);
  letter-spacing: -0.005em;
}

.dashboard-section-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
}

.dashboard-refresh-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  background: var(--bg-card, #FCFBF5);
  border: 1px solid var(--border, #E8E8E0);
  border-radius: 6px;
  color: var(--text-secondary, #494A4D);
  font-size: 11px;
  font-family: inherit;
  cursor: pointer;
  transition: border-color 0.15s, color 0.15s;
  flex-shrink: 0;
}

.dashboard-refresh-btn:hover:not(:disabled) {
  border-color: var(--accent, #CD5036);
  color: var(--accent, #CD5036);
}

.dashboard-refresh-btn:focus-visible {
  outline: 2px solid var(--focus-ring, #15171D);
  outline-offset: 2px;
}

.dashboard-refresh-btn:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

/* ============ 错误状态 ============ */
.dashboard-error {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 20px 24px;
  background: var(--bg-card, #FCFBF5);
  border: 1px solid var(--red, #C4391C);
  border-radius: 10px;
}

.dashboard-error-icon {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--red, #C4391C);
  color: #FFFFFF;
  border-radius: 50%;
  font-size: 16px;
  font-weight: 700;
  flex-shrink: 0;
}

.dashboard-error-body {
  flex: 1;
  min-width: 0;
}

.dashboard-error-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary, #15171D);
  margin: 0 0 4px;
}

.dashboard-error-desc {
  font-size: 12px;
  color: var(--text-tertiary, #807E7E);
  margin: 0;
  word-break: break-all;
}

.dashboard-retry-btn {
  background: var(--accent, #CD5036);
  color: #FFFFFF;
  border: none;
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
  flex-shrink: 0;
}

.dashboard-retry-btn:hover {
  background: var(--accent-hover, #C4391C);
}

.dashboard-retry-btn:focus-visible {
  outline: 2px solid var(--focus-ring, #15171D);
  outline-offset: 2px;
}

/* ============ 底部快速链接 ============ */
.dashboard-footer {
  display: flex;
  justify-content: center;
  padding: 16px 0 8px;
  border-top: 1px solid var(--border, #E8E8E0);
  margin-top: 8px;
}

.dashboard-footer-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 10px 20px;
  background: var(--bg-card, #FCFBF5);
  border: 1px solid var(--border-strong, #D7D4CD);
  border-radius: 8px;
  color: var(--text-primary, #15171D);
  text-decoration: none;
  font-size: 13px;
  font-weight: 600;
  transition: border-color 0.15s, color 0.15s, transform 0.1s;
}

.dashboard-footer-link:hover {
  border-color: var(--accent, #CD5036);
  color: var(--accent, #CD5036);
  transform: translateY(-1px);
}

.dashboard-footer-link:focus-visible {
  outline: 2px solid var(--focus-ring, #15171D);
  outline-offset: 2px;
}

.dashboard-footer-arrow {
  font-size: 14px;
  transition: transform 0.15s;
}

.dashboard-footer-link:hover .dashboard-footer-arrow {
  transform: translateX(2px);
}

/* ============ 响应式 ============ */
@media (max-width: 768px) {
  .dashboard-nav {
    padding: 12px 16px;
  }
  .dashboard-main {
    padding: 20px 16px 32px;
    gap: 20px;
  }
  .dashboard-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
  .dashboard-title {
    font-size: 18px;
  }
}

@media (max-width: 480px) {
  .dashboard-nav-links {
    gap: 8px;
  }
  .dashboard-nav-link {
    padding: 4px 8px;
    font-size: 12px;
  }
}
</style>

<template>
  <div class="learning-center">
    <!-- 页面标题 -->
    <header class="page-header">
      <div class="header-left">
        <span class="section-deco" aria-hidden="true">◇</span>
        <h1 class="page-title">{{ t('learning.title') }}</h1>
      </div>
      <div class="header-right">
        <span class="project-count">{{ counts[''] || 0 }} PATTERNS</span>
      </div>
    </header>

    <!-- 筛选标签 -->
    <div class="workspace-subnav" role="tablist" :aria-label="t('common.filter')">
      <button
        v-for="t in tabs"
        :key="t.value || 'all'"
        type="button"
        role="tab"
        :class="['ws-tab', { active: filter === t.value }]"
        :aria-selected="filter === t.value"
        :aria-controls="`lc-panel-${t.value || 'all'}`"
        @click="setFilter(t.value)"
        @keydown="onTabKeydown($event, t.value)"
      >
        {{ t.label }}
        <span v-if="counts[t.value]" class="ws-count">{{ counts[t.value] }}</span>
      </button>
    </div>

    <!-- 加载中 -->
    <div v-if="loading" class="empty-state" role="status" aria-live="polite">
      <div class="lc-spinner" aria-hidden="true"></div>
      <p class="empty-text">{{ t('common.loading') }}</p>
    </div>

    <!-- 空状态 -->
    <div v-else-if="!patterns.length" class="empty-state" aria-live="polite">
      <div class="empty-icon" aria-hidden="true">❖</div>
      <p class="empty-text">{{ t('learning.noPatterns') }}</p>
      <p class="empty-hint">{{ t('learning.noPatternsHint') }}</p>
    </div>

    <!-- 模式卡片列表 -->
    <div
      v-else
      :id="`lc-panel-${filter || 'all'}`"
      class="lc-patterns"
      role="tabpanel"
      :aria-label="currentTabLabel"
    >
      <article
        v-for="p in patterns"
        :key="p.id"
        class="pattern-card"
        :class="p.status"
      >
        <div class="pattern-top">
          <span class="pattern-type" :class="p.pattern_type">
            {{ p.pattern_type === 'success_pattern' ? t('learning.successPattern') : t('learning.failurePattern') }}
          </span>
          <span class="pattern-status" :class="p.status">{{ statusLabel(p.status) }}</span>
        </div>
        <h3 class="pattern-name" :title="p.name">{{ p.name }}</h3>
        <p class="pattern-play">{{ p.recommended_play }}</p>
        <div class="pattern-stats">
          <span class="stat">{{ t('learning.sampleCount') }} <strong>{{ p.evidence_count }}</strong></span>
          <span class="stat">{{ t('learning.successRate') }} <strong>{{ formatRate(p.success_rate) }}</strong></span>
        </div>
        <div v-if="p.trigger_conditions && Object.keys(p.trigger_conditions).length" class="pattern-conditions">
          <span class="cond-label">{{ t('learning.triggerConditions') }}</span>
          <span v-for="(v, k) in p.trigger_conditions" :key="k" class="cond-chip">
            <span class="cond-key">{{ k }}</span><span class="cond-sep">:</span><span class="cond-val">{{ v }}</span>
          </span>
        </div>
        <div class="pattern-actions">
          <button
            v-if="p.status === 'candidate'"
            type="button"
            class="btn-primary btn-sm"
            :disabled="actingId === p.id"
            @click="handleApprove(p.id)"
          >
            <span v-if="actingId === p.id" class="btn-spinner" aria-hidden="true"></span>
            {{ t('learning.approve') }}
          </button>
          <button
            v-if="p.status !== 'deprecated'"
            type="button"
            class="btn-secondary btn-sm"
            :disabled="actingId === p.id"
            @click="handleDeprecate(p)"
          >
            {{ t('learning.deprecate') }}
          </button>
        </div>
      </article>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { getLearningPatterns, approvePattern, deprecatePattern } from '../../api/salesTwin'
import { requestConfirm, showToast } from '../../composables/salesTwin/useConfirmToast'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

const patterns = ref([])
const loading = ref(false)
const actingId = ref(null)  // 当前正在操作的 pattern id，用于按钮 loading
// 从 URL 读取初始 filter，支持深链
const filter = ref(route.query.status || 'candidate')

const tabs = computed(() => [
  { value: 'candidate', label: t('learning.candidatePatterns') },
  { value: 'approved', label: t('learning.approvedPatterns') },
  { value: 'deprecated', label: t('learning.deprecatedPatterns') },
  { value: '', label: t('common.all') },
])

// 各 tab 的计数（用于徽章显示）
const counts = ref({})

const currentTabLabel = computed(() => {
  const tab = tabs.value.find(item => item.value === filter.value)
  return tab ? tab.label : t('common.all')
})

function setFilter(value) {
  if (filter.value === value) return
  filter.value = value
  // 同步到 URL，支持深链/前进后退
  router.replace({ query: { ...route.query, status: value || undefined } })
}

// tablist 键盘导航：左右切换
function onTabKeydown(e, currentValue) {
  const idx = tabs.value.findIndex(item => item.value === currentValue)
  if (idx === -1) return
  if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
    e.preventDefault()
    const next = tabs.value[(idx + 1) % tabs.value.length]
    setFilter(next.value)
  } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
    e.preventDefault()
    const prev = tabs.value[(idx - 1 + tabs.value.length) % tabs.value.length]
    setFilter(prev.value)
  }
}

function formatRate(rate) {
  if (rate == null) return '—'
  return `${(rate * 100).toFixed(0)}%`
}

const fetchPatterns = async () => {
  loading.value = true
  try {
    const res = await getLearningPatterns(filter.value || undefined)
    patterns.value = res.patterns || []
  } catch (e) {
    console.error('获取学习模式失败:', e)
    showToast(t('toast.loadFailed'), 'error')
  } finally {
    loading.value = false
  }
}

// 加载各状态计数（仅首次加载时）
const fetchCounts = async () => {
  try {
    const res = await getLearningPatterns()
    const all = res.patterns || []
    counts.value = {
      candidate: all.filter(p => p.status === 'candidate').length,
      approved: all.filter(p => p.status === 'approved').length,
      deprecated: all.filter(p => p.status === 'deprecated').length,
      '': all.length,
    }
  } catch (e) {
    // 计数失败不影响主流程
  }
}

const handleApprove = async (id) => {
  actingId.value = id
  try {
    await approvePattern(id)
    showToast(t('toast.operationSuccess'), 'success')
    await Promise.all([fetchPatterns(), fetchCounts()])
  } catch (e) {
    showToast(t('toast.operationFailed'), 'error')
  } finally {
    actingId.value = null
  }
}

const handleDeprecate = async (p) => {
  // 破坏性操作：需确认
  const ok = await requestConfirm({
    title: t('modal.confirmTitle'),
    message: t('learning.deprecateConfirm', { name: p.name }),
    confirmText: t('learning.deprecate'),
    cancelText: t('common.cancel'),
    danger: true,
  })
  if (!ok) return
  actingId.value = p.id
  try {
    await deprecatePattern(p.id)
    showToast(t('toast.operationSuccess'), 'info')
    await Promise.all([fetchPatterns(), fetchCounts()])
  } catch (e) {
    showToast(t('toast.operationFailed'), 'error')
  } finally {
    actingId.value = null
  }
}

const statusLabel = (status) => {
  const map = {
    candidate: t('learning.status.candidate'),
    approved: t('learning.status.approved'),
    deprecated: t('learning.status.deprecated'),
  }
  return map[status] || status
}

// 监听 URL query 变化（浏览器前进/后退）
watch(() => route.query.status, (newStatus) => {
  const next = newStatus || ''
  if (next !== filter.value) {
    filter.value = next
    fetchPatterns()
  }
})

watch(filter, fetchPatterns)
onMounted(() => {
  fetchPatterns()
  fetchCounts()
})
</script>

<style scoped>
.learning-center {
  /* 继承 .main-content 的 padding，不再自定义容器内边距与宽度 */
}

/* 模式卡片列表 */
.lc-patterns {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.pattern-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 18px;
  box-shadow: var(--shadow-sm);
  transition: box-shadow 0.15s, border-color 0.15s, transform 0.1s;
}

.pattern-card:hover {
  border-color: var(--border-strong);
  box-shadow: var(--shadow-md);
  transform: translateY(-1px);
}

.pattern-card.deprecated {
  opacity: 0.6;
}

.pattern-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.pattern-type {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: var(--fs-xs);
  font-weight: 600;
  font-family: var(--font-mono);
  letter-spacing: 0.03em;
  text-transform: uppercase;
}

.pattern-type.success_pattern {
  background: var(--green-light);
  color: var(--green);
  border: 1px solid rgba(17, 138, 88, 0.2);
}

.pattern-type.failure_pattern {
  background: var(--red-light);
  color: var(--red);
  border: 1px solid rgba(196, 57, 28, 0.2);
}

.pattern-status {
  font-size: var(--fs-xs);
  color: var(--text-tertiary);
  font-weight: 500;
}

.pattern-status.approved {
  color: var(--green);
}

.pattern-status.deprecated {
  color: var(--text-muted);
}

.pattern-name {
  font-size: var(--fs-lg);
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 6px;
  letter-spacing: -0.005em;
  line-height: 1.3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pattern-play {
  font-size: var(--fs-sm);
  color: var(--text-secondary);
  margin: 0 0 12px;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.pattern-stats {
  display: flex;
  gap: 16px;
  margin-bottom: 12px;
}

.stat {
  font-size: var(--fs-xs);
  color: var(--text-tertiary);
  font-variant-numeric: tabular-nums;
}

.stat strong {
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-weight: 600;
  margin-left: 3px;
}

.pattern-conditions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin-bottom: 12px;
  padding-top: 10px;
  border-top: 1px dashed var(--border);
}

.cond-label {
  font-size: var(--fs-xs);
  color: var(--text-tertiary);
  margin-right: 4px;
}

.cond-chip {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 2px 8px;
  background: rgba(21, 23, 29, 0.04);
  border: 1px solid var(--border);
  border-radius: 10px;
  font-size: var(--fs-xs);
  color: var(--text-secondary);
  font-family: var(--font-mono);
  max-width: 240px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cond-key {
  color: var(--text-tertiary);
}

.cond-sep {
  color: var(--text-muted);
  margin: 0 1px;
}

.cond-val {
  color: var(--text-primary);
  font-weight: 500;
}

.pattern-actions {
  display: flex;
  gap: 8px;
  margin-top: 4px;
  padding-top: 12px;
  border-top: 1px solid var(--border);
}

/* 加载 spinner */
.lc-spinner {
  width: 24px;
  height: 24px;
  border: 2px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: lc-spin 0.7s linear infinite;
  margin: 0 auto 12px;
}

/* 按钮 spinner */
.btn-spinner {
  width: 11px;
  height: 11px;
  border: 1.5px solid currentColor;
  border-top-color: transparent;
  border-radius: 50%;
  animation: lc-spin 0.7s linear infinite;
}

@keyframes lc-spin {
  to { transform: rotate(360deg); }
}

/* tablist focus 样式（对齐全局 ws-tab:focus-visible） */
.ws-tab:focus-visible {
  outline: 2px solid var(--focus-ring);
  outline-offset: 2px;
}

/* 减少动画 */
@media (prefers-reduced-motion: reduce) {
  .pattern-card,
  .btn-primary.btn-sm,
  .btn-secondary.btn-sm,
  .ws-tab {
    transition: none;
  }
  .lc-spinner,
  .btn-spinner {
    animation: none;
  }
}
</style>

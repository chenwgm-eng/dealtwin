<template>
  <div class="insight-panel">
    <div v-if="loading" class="insight-loading">
      <span class="insight-spinner"></span>
      <span>{{ t('dashboard.aiAnalyzing') }}</span>
    </div>
    <template v-else>
      <!-- 降级状态 -->
      <div v-if="isFallback" class="insight-fallback">
        <span class="insight-fallback-icon">!</span>
        <span class="insight-fallback-text">{{ t('dashboard.insightUnavailable') }}</span>
        <button class="insight-retry-btn" @click="$emit('retry')">{{ t('common.retry') }}</button>
      </div>
      <template v-else>
        <!-- 执行摘要 -->
        <div class="insight-summary">
          <div class="insight-summary-icon" aria-hidden="true">◆</div>
          <div class="insight-summary-body">
            <div class="insight-summary-label">{{ t('dashboard.aiInsight') }}</div>
            <p class="insight-summary-text">{{ insights?.executive_summary }}</p>
          </div>
        </div>

        <!-- 风险预警 -->
        <section v-if="insights?.risk_alerts?.length > 0" class="insight-section" :aria-label="t('dashboard.riskAlerts')">
          <h4 class="insight-section-title">
            <span class="insight-section-deco" aria-hidden="true">⚠</span>
            {{ t('dashboard.riskAlerts') }}
          </h4>
          <div class="insight-alert-list">
            <article
              v-for="(alert, idx) in insights.risk_alerts"
              :key="'alert-'+idx"
              class="insight-alert-card"
              :class="[`alert-level-${alert.level}`, { 'is-clickable': alert.related_project_id }]"
              :role="alert.related_project_id ? 'button' : undefined"
              :tabindex="alert.related_project_id ? 0 : undefined"
              @click="alert.related_project_id && goToProject(alert.related_project_id)"
              @keydown.enter="alert.related_project_id && goToProject(alert.related_project_id)"
              @keydown.space.prevent="alert.related_project_id && goToProject(alert.related_project_id)"
              :aria-label="alert.related_project_id ? t('dashboard.jumpToProject', { title: alert.title }) : undefined"
            >
              <div class="alert-header">
                <span class="alert-level-dot" :class="`level-${alert.level}`"></span>
                <span class="alert-level-tag" :class="`level-${alert.level}`">{{ levelLabel(alert.level) }}</span>
                <span v-if="alert.category" class="alert-category">{{ alert.category }}</span>
                <span class="alert-title">{{ alert.title }}</span>
                <span v-if="alert.related_project_id" class="alert-jump-hint" aria-hidden="true">→</span>
              </div>
              <p class="alert-description">{{ alert.description }}</p>
              <p v-if="alert.impact" class="alert-impact">
                <span class="alert-impact-label">{{ t('dashboard.impact') }}</span>
                {{ alert.impact }}
              </p>
              <p v-if="alert.suggestion" class="alert-recommendation">
                <span class="alert-rec-label">{{ t('dashboard.suggestion') }}</span>
                {{ alert.suggestion }}
              </p>
            </article>
          </div>
        </section>

        <!-- 机会提示 -->
        <section v-if="insights?.opportunities?.length > 0" class="insight-section" :aria-label="t('dashboard.opportunityHints')">
          <h4 class="insight-section-title">
            <span class="insight-section-deco insight-deco-opportunity" aria-hidden="true">★</span>
            {{ t('dashboard.opportunityHints') }}
          </h4>
          <div class="insight-opportunity-list">
            <article
              v-for="(opp, idx) in insights.opportunities"
              :key="'opp-'+idx"
              class="insight-opportunity-card"
              :class="{ 'is-clickable': opp.related_project_id }"
              :role="opp.related_project_id ? 'button' : undefined"
              :tabindex="opp.related_project_id ? 0 : undefined"
              @click="opp.related_project_id && goToProject(opp.related_project_id)"
              @keydown.enter="opp.related_project_id && goToProject(opp.related_project_id)"
              @keydown.space.prevent="opp.related_project_id && goToProject(opp.related_project_id)"
              :aria-label="opp.related_project_id ? t('dashboard.jumpToProject', { title: opp.title }) : undefined"
            >
              <div class="opp-header">
                <span class="opp-title">{{ opp.title }}</span>
                <span v-if="opp.related_project_id" class="opp-jump-hint" aria-hidden="true">→</span>
              </div>
              <p class="opp-description">{{ opp.description }}</p>
              <p v-if="opp.potential_value" class="opp-potential-value">
                <span class="opp-value-label">{{ t('dashboard.potentialValue') }}</span>
                {{ opp.potential_value }}
              </p>
              <p v-if="opp.action" class="opp-recommendation">
                <span class="opp-rec-label">{{ t('dashboard.suggestion') }}</span>
                {{ opp.action }}
              </p>
            </article>
          </div>
        </section>

        <!-- 优先级行动建议 -->
        <section v-if="insights?.priority_actions?.length > 0" class="insight-section" :aria-label="t('dashboard.priorityActions')">
          <h4 class="insight-section-title">
            <span class="insight-section-deco insight-deco-action" aria-hidden="true">→</span>
            {{ t('dashboard.priorityActions') }}
          </h4>
          <ol class="insight-action-list">
            <li
              v-for="action in sortedActions"
              :key="action.sequence"
              class="insight-action-item"
              :class="{ 'is-clickable': action.related_project_id }"
              :role="action.related_project_id ? 'button' : undefined"
              :tabindex="action.related_project_id ? 0 : undefined"
              @click="action.related_project_id && goToProject(action.related_project_id)"
              @keydown.enter="action.related_project_id && goToProject(action.related_project_id)"
              @keydown.space.prevent="action.related_project_id && goToProject(action.related_project_id)"
              :aria-label="action.related_project_id ? t('dashboard.jumpToProject', { title: action.title }) : undefined"
            >
              <span class="action-sequence">{{ action.sequence }}</span>
              <div class="action-body">
                <div class="action-text">{{ action.title }}</div>
                <div v-if="action.description" class="action-reason">{{ action.description }}</div>
                <div class="action-meta">
                  <span v-if="action.owner" class="action-owner">
                    <span class="action-meta-label">{{ t('dashboard.owner') }}</span>
                    {{ action.owner }}
                  </span>
                  <span v-if="action.deadline" class="action-deadline">
                    <span class="action-meta-label">{{ t('dashboard.deadline') }}</span>
                    {{ action.deadline }}
                  </span>
                  <span v-if="action.related_project_id" class="action-jump-hint" aria-hidden="true">{{ t('dashboard.clickToJump') }}</span>
                </div>
              </div>
            </li>
          </ol>
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

// Props：LLM 智能洞察聚合
const props = defineProps({
  insights: {
    type: Object,
    default: () => ({})
  },
  loading: {
    type: Boolean,
    default: false
  }
})

// Emits：LLM 失败时点击重试
defineEmits(['retry'])

const router = useRouter()

// 降级状态：明确返回 fallback 文案或没有 executive_summary
const isFallback = computed(() => {
  return !props.insights?.executive_summary || props.insights.executive_summary === '智能洞察暂不可用'
})

// 优先级行动按 sequence 升序排序
const sortedActions = computed(() => {
  const actions = props.insights?.priority_actions
  if (!Array.isArray(actions)) return []
  return [...actions].sort((a, b) => (a?.sequence ?? 0) - (b?.sequence ?? 0))
})

// 风险等级文案映射
function levelLabel(level) {
  return t(`workspace.severityLabels.${level}`)
}

// 跳转到关联项目
function goToProject(projectId) {
  router.push({ path: '/sales-twin', query: { project: projectId } })
}
</script>

<style scoped>
/* 面板容器：与右侧 aside 一致的卡片风格 */
.insight-panel {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* 加载状态 */
.insight-loading {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 32px;
  color: var(--text-secondary);
  font-size: 13px;
  justify-content: center;
}

.insight-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: insight-spin 0.8s linear infinite;
}

@keyframes insight-spin {
  to { transform: rotate(360deg); }
}

/* 降级状态 */
.insight-fallback {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 13px;
  color: var(--text-secondary);
}

.insight-fallback-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--yellow);
  color: #ffffff;
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
}

.insight-fallback-text {
  flex: 1;
  min-width: 0;
}

.insight-retry-btn {
  padding: 4px 12px;
  background: var(--bg-card);
  border: 1px solid var(--border-strong);
  border-radius: 4px;
  color: var(--text-secondary);
  font-size: 12px;
  font-family: inherit;
  cursor: pointer;
  transition: border-color 0.15s, color 0.15s;
  flex-shrink: 0;
}

.insight-retry-btn:hover {
  border-color: var(--accent);
  color: var(--accent);
}

.insight-retry-btn:focus-visible {
  outline: 2px solid var(--focus-ring);
  outline-offset: 1px;
}

/* 执行摘要 */
.insight-summary {
  display: flex;
  gap: 12px;
  background: var(--bg-surface);
  border-radius: 8px;
  padding: 16px;
  align-items: flex-start;
}

.insight-summary-icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: var(--accent);
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  flex-shrink: 0;
}

.insight-summary-body {
  flex: 1;
  min-width: 0;
}

.insight-summary-label {
  font-size: 11px;
  color: var(--text-muted);
  letter-spacing: 0.05em;
  text-transform: uppercase;
  margin-bottom: 4px;
}

.insight-summary-text {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1.5;
}

/* 区块标题 */
.insight-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.insight-section-title {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 6px;
}

.insight-section-deco {
  color: var(--red);
  font-weight: 400;
}

.insight-deco-opportunity {
  color: var(--green);
}

.insight-deco-action {
  color: var(--accent);
}

/* 风险预警卡片 */
.insight-alert-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.insight-alert-card {
  position: relative;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 12px;
  overflow: hidden;
  transition: border-color 0.15s, box-shadow 0.15s, transform 0.1s;
}

.insight-alert-card::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
}

/* 左色条按风险等级 */
.alert-level-critical::before { background: var(--red); }
.alert-level-high::before { background: #F59E0B; }
.alert-level-medium::before { background: var(--yellow); }

.insight-alert-card:hover {
  border-color: var(--accent);
}

/* 可点击卡片样式 */
.insight-alert-card.is-clickable,
.insight-opportunity-card.is-clickable,
.insight-action-item.is-clickable {
  cursor: pointer;
}

.insight-alert-card.is-clickable:hover,
.insight-opportunity-card.is-clickable:hover,
.insight-action-item.is-clickable:hover {
  border-color: var(--accent);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  transform: translateY(-1px);
}

.insight-alert-card.is-clickable:focus-visible,
.insight-opportunity-card.is-clickable:focus-visible,
.insight-action-item.is-clickable:focus-visible {
  outline: 2px solid var(--focus-ring, #15171D);
  outline-offset: 2px;
}

/* 跳转提示箭头 */
.alert-jump-hint,
.opp-jump-hint {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  line-height: 1;
  color: var(--text-muted);
  flex-shrink: 0;
  transition: color 0.15s, transform 0.15s;
}

.is-clickable:hover .alert-jump-hint,
.is-clickable:hover .opp-jump-hint {
  color: var(--accent);
  transform: translateX(2px);
}

.action-jump-hint {
  font-size: 11px;
  color: var(--text-muted);
  margin-left: auto;
  transition: color 0.15s;
}

.is-clickable:hover .action-jump-hint {
  color: var(--accent);
}

.alert-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
  flex-wrap: wrap;
}

.alert-level-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.alert-level-dot.level-critical { background: var(--red); }
.alert-level-dot.level-high { background: #F59E0B; }
.alert-level-dot.level-medium { background: var(--yellow); }

.alert-level-tag {
  font-size: 11px;
  padding: 1px 6px;
  border: 1px solid var(--border);
  border-radius: 2px;
  font-family: 'JetBrains Mono', 'SF Mono', monospace;
  font-weight: 600;
}

.alert-level-tag.level-critical {
  border-color: var(--red);
  color: var(--red);
}
.alert-level-tag.level-high {
  border-color: #F59E0B;
  color: #F59E0B;
}
.alert-level-tag.level-medium {
  border-color: var(--yellow);
  color: var(--yellow);
}

.alert-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  flex: 1;
  min-width: 0;
}

.alert-description {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.6;
}

.alert-recommendation {
  margin: 8px 0 0;
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.6;
  padding-left: 8px;
  border-left: 2px solid var(--border-strong);
}

.alert-rec-label {
  display: inline-block;
  margin-right: 6px;
  font-size: 11px;
  font-weight: 600;
  color: var(--accent);
  letter-spacing: 0.05em;
}

/* 机会提示卡片 */
.insight-opportunity-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.insight-opportunity-card {
  position: relative;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 12px;
  overflow: hidden;
  transition: border-color 0.15s;
}

.insight-opportunity-card::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: var(--green);
}

.insight-opportunity-card:hover {
  border-color: var(--accent);
}

.opp-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
}

.opp-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  flex: 1;
  min-width: 0;
}

.opp-description {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.6;
}

.opp-recommendation {
  margin: 8px 0 0;
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.6;
  padding-left: 8px;
  border-left: 2px solid var(--border-strong);
}

.opp-rec-label {
  display: inline-block;
  margin-right: 6px;
  font-size: 11px;
  font-weight: 600;
  color: var(--green);
  letter-spacing: 0.05em;
}

/* 优先级行动列表 */
.insight-action-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.insight-action-item {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  padding: 12px;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 6px;
  transition: border-color 0.15s;
}

.insight-action-item:hover {
  border-color: var(--accent);
}

.action-sequence {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--accent);
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  font-family: 'JetBrains Mono', 'SF Mono', monospace;
  flex-shrink: 0;
}

.action-body {
  flex: 1;
  min-width: 0;
}

.action-text {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1.4;
}

.action-reason {
  margin-top: 4px;
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.6;
}

.action-target {
  margin-top: 4px;
  font-size: 11px;
  color: var(--text-muted);
  font-family: 'JetBrains Mono', 'SF Mono', monospace;
}

/* 风险类别标签 */
.alert-category {
  font-size: 11px;
  padding: 1px 6px;
  border: 1px solid var(--border);
  border-radius: 2px;
  color: var(--text-tertiary);
  font-weight: 500;
}

/* 影响行 */
.alert-impact {
  margin: 6px 0 0;
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.6;
  padding-left: 8px;
  border-left: 2px solid var(--yellow);
}

.alert-impact-label {
  display: inline-block;
  margin-right: 6px;
  font-size: 11px;
  font-weight: 600;
  color: var(--yellow);
  letter-spacing: 0.05em;
}

/* 机会潜在价值 */
.opp-potential-value {
  margin: 6px 0 0;
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.6;
  padding-left: 8px;
  border-left: 2px solid var(--green);
}

.opp-value-label {
  display: inline-block;
  margin-right: 6px;
  font-size: 11px;
  font-weight: 600;
  color: var(--green);
  letter-spacing: 0.05em;
}

/* 行动建议 meta 行 */
.action-meta {
  margin-top: 6px;
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 11px;
  color: var(--text-muted);
}

.action-owner,
.action-deadline {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.action-meta-label {
  font-size: 10px;
  font-weight: 600;
  color: var(--accent);
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.action-deadline .action-meta-label {
  color: var(--text-tertiary);
}

@media (prefers-reduced-motion: reduce) {
  .insight-spinner {
    animation: none;
  }
}
</style>

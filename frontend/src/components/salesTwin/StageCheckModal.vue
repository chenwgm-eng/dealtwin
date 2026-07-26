<template>
  <div v-if="show" class="modal-overlay" tabindex="-1"
    role="dialog" aria-modal="true" :aria-label="t('stages.checkReport')"
    @click.self="emit('close')"
    @keydown.esc="emit('close')">
    <div class="modal" style="max-width:640px;">
      <div class="modal-header">
        <h3 class="modal-title">{{ t('stages.checkReport') }}</h3>
        <button type="button" class="modal-close" @click="emit('close')" :aria-label="t('common.close')">×</button>
      </div>
      <div class="modal-body">
        <div v-if="!checkResult" class="sdp-check-empty">{{ t('stages.noCheckResult') }}</div>
        <div v-else class="sdp-check-content">
          <!-- 完成度大数字展示 -->
          <div class="sdp-check-overview">
            <div class="sdp-check-rate" :class="rateClass">
              <span class="sdp-check-rate-num">{{ checkResult.completion_rate.toFixed(1) }}</span>
              <span class="sdp-check-rate-unit">%</span>
            </div>
            <div class="sdp-check-detail">
              <p class="sdp-check-stage">{{ t('stages.stageLabel', { stage: stageLabel }) }}</p>
              <p class="sdp-check-count">{{ t('stages.itemsCompleted', { completed: checkResult.completed_items, total: checkResult.total_items }) }}</p>
            </div>
          </div>

          <!-- 推荐建议 -->
          <div class="sdp-check-recommendation" :class="{ ok: checkResult.can_advance, warn: !checkResult.can_advance }">
            <span class="sdp-rec-icon">{{ checkResult.can_advance ? '✓' : '!' }}</span>
            <span>{{ checkResult.recommendation }}</span>
          </div>

          <!-- 退出条件检查 -->
          <div v-if="checkResult.exit_conditions_check?.length" class="sdp-check-section">
            <h4 class="sdp-section-title">{{ t('stages.exitConditionCheck') }}</h4>
            <ul class="sdp-exit-list">
              <li v-for="(ec, i) in checkResult.exit_conditions_check" :key="i" :class="{ satisfied: ec.satisfied, unsatisfied: !ec.satisfied }">
                <span class="sdp-exit-icon">{{ ec.satisfied ? '✓' : '✗' }}</span>
                <span>{{ ec.condition }}</span>
              </li>
            </ul>
          </div>

          <!-- 未完成交付物列表（按分组展示） -->
          <div v-if="checkResult.pending_items?.length" class="sdp-check-section">
            <h4 class="sdp-section-title">{{ t('stages.pendingDeliverables', { count: checkResult.pending_items.length }) }}</h4>
            <ul class="sdp-pending-list">
              <li v-for="(item, i) in checkResult.pending_items" :key="i">
                <span class="sdp-pending-group">{{ item.group_name }}</span>
                <span class="sdp-pending-sep">/</span>
                <span class="sdp-pending-name">{{ item.name }}</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn-secondary" @click="emit('close')">
          {{ checkResult?.can_advance ? t('stages.advanceLater') : t('common.close') }}
        </button>
        <button v-if="checkResult?.can_advance" type="button" class="btn-primary" @click="emit('advance-stage')">
          {{ t('stages.advanceNow', { nextStage: nextStageLabel }) }} →
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const props = defineProps({
  show: { type: Boolean, default: false },
  // checkResult 由 API 返回的检查报告，结构：
  // {
  //   stage: 'suspect',
  //   completion_rate: 60.0,
  //   total_items: 5,
  //   completed_items: 3,
  //   pending_items: [{ key, name, group_name }],
  //   exit_conditions_check: [{ condition, satisfied }],
  //   recommendation: '暂缓推进，请优先完成未完成交付物',
  //   can_advance: false
  // }
  checkResult: { type: Object, default: () => null },
  currentStage: { type: String, default: '' },
  nextStage: { type: String, default: '' }
})

const emit = defineEmits([
  'close',          // () - 关闭 modal
  'advance-stage'   // () - 用户点击"立即推进"按钮
])

// 阶段标签映射
const VALID_STAGES = ['suspect', 'identity', 'define', 'confirm', 'closed_won', 'closed_lost']

const stageLabel = computed(() => {
  if (!props.currentStage) return ''
  return VALID_STAGES.includes(props.currentStage) ? t(`stages.${props.currentStage}`) : props.currentStage
})
const nextStageLabel = computed(() => {
  if (!props.nextStage) return t('stages.nextStage')
  return VALID_STAGES.includes(props.nextStage) ? t(`stages.${props.nextStage}`) : props.nextStage
})

// 完成度颜色档位：>=80% 绿色，40-80% 黄色，<40% 红色
const rateClass = computed(() => {
  const r = props.checkResult?.completion_rate ?? 0
  if (r >= 80) return 'rate-ok'
  if (r >= 40) return 'rate-warn'
  return 'rate-danger'
})
</script>

<style scoped>
/* ============ 空状态 ============ */
.sdp-check-empty {
  text-align: center;
  padding: 32px 12px;
  color: var(--text-muted);
  font-size: var(--fs-base);
}

/* ============ 内容容器 ============ */
.sdp-check-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ============ 完成度大数字展示 ============ */
.sdp-check-overview {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 16px 20px;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 8px;
}

.sdp-check-rate {
  display: flex;
  align-items: baseline;
  gap: 2px;
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  line-height: 1;
}

.sdp-check-rate-num {
  font-size: 48px;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.sdp-check-rate-unit {
  font-size: var(--fs-lg);
  font-weight: 600;
  color: var(--text-muted);
}

.sdp-check-rate.rate-ok .sdp-check-rate-num { color: var(--green); }
.sdp-check-rate.rate-warn .sdp-check-rate-num { color: var(--yellow); }
.sdp-check-rate.rate-danger .sdp-check-rate-num { color: var(--red); }

.sdp-check-detail {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.sdp-check-stage {
  margin: 0;
  font-size: var(--fs-md);
  font-weight: 600;
  color: var(--text-primary);
}

.sdp-check-count {
  margin: 0;
  font-size: var(--fs-sm);
  color: var(--text-secondary);
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}

/* ============ 推荐建议条 ============ */
.sdp-check-recommendation {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-radius: 6px;
  font-size: var(--fs-sm);
  line-height: 1.5;
  border: 1px solid transparent;
}

.sdp-check-recommendation.ok {
  background: var(--green-light);
  border-color: rgba(17, 138, 88, 0.25);
  color: var(--green);
}

.sdp-check-recommendation.warn {
  background: var(--red-light);
  border-color: rgba(196, 57, 28, 0.25);
  color: var(--red);
}

.sdp-rec-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  font-size: var(--fs-xs);
  font-weight: 700;
  flex-shrink: 0;
  color: var(--bg-card);
}

/* 图标底色随上下文（绿/红），字符反白 */
.sdp-check-recommendation.ok .sdp-rec-icon {
  background: var(--green);
}

.sdp-check-recommendation.warn .sdp-rec-icon {
  background: var(--red);
}

/* ============ 区块标题 ============ */
.sdp-check-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.sdp-section-title {
  margin: 0;
  font-size: var(--fs-sm);
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: 0.02em;
}

/* ============ 退出条件检查列表 ============ */
.sdp-exit-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.sdp-exit-list li {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 8px 12px;
  border: 1px solid var(--border);
  border-radius: 4px;
  background: var(--bg-card);
  font-size: var(--fs-sm);
  line-height: 1.5;
  color: var(--text-primary);
}

.sdp-exit-list li.satisfied {
  border-left: 3px solid var(--green);
  background: var(--green-light);
}

.sdp-exit-list li.unsatisfied {
  border-left: 3px solid var(--red);
  background: var(--red-light);
}

.sdp-exit-icon {
  flex-shrink: 0;
  font-weight: 700;
  line-height: 1.5;
}

.sdp-exit-list li.satisfied .sdp-exit-icon { color: var(--green); }
.sdp-exit-list li.unsatisfied .sdp-exit-icon { color: var(--red); }

/* ============ 未完成交付物列表（两列紧凑布局） ============ */
.sdp-pending-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 6px;
}

.sdp-pending-list li {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border: 1px solid var(--border);
  border-radius: 4px;
  background: var(--bg-card);
  font-size: var(--fs-xs);
  line-height: 1.4;
  min-width: 0;
}

.sdp-pending-group {
  color: var(--text-muted);
  font-family: var(--font-mono);
  flex-shrink: 0;
  max-width: 40%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sdp-pending-sep {
  color: var(--text-muted);
  flex-shrink: 0;
}

.sdp-pending-name {
  color: var(--text-primary);
  font-weight: 500;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 窄屏：未完成交付物列表回退为单列 */
@media (max-width: 600px) {
  .sdp-pending-list {
    grid-template-columns: 1fr;
  }

  .sdp-check-overview {
    gap: 12px;
    padding: 12px 14px;
  }

  .sdp-check-rate-num {
    font-size: 40px;
  }
}
</style>

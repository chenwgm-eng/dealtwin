<template>
  <div class="time-range-selector">
    <select v-model="selectedPeriod" @change="onPeriodChange" class="trs-select" :aria-label="t('dashboard.selectTimeRange')">
      <option value="this_month">{{ t('dashboard.thisMonth') }}</option>
      <option value="this_quarter">{{ t('dashboard.thisQuarter') }}</option>
      <option value="next_quarter">{{ t('dashboard.nextQuarter') }}</option>
      <option value="this_year">{{ t('dashboard.thisYear') }}</option>
      <option value="custom">{{ t('dashboard.custom') }}</option>
    </select>
    <div v-if="selectedPeriod === 'custom'" class="trs-custom-range">
      <input type="date" v-model="customStart" @change="onCustomChange" class="trs-date-input" :aria-label="t('dashboard.startDate')" />
      <span class="trs-separator">{{ t('dashboard.dateRangeTo') }}</span>
      <input type="date" v-model="customEnd" @change="onCustomChange" class="trs-date-input" :aria-label="t('dashboard.endDate')" />
    </div>
    <span v-else class="trs-range-text">{{ rangeText }}</span>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

// Props：受控值，格式 { period, start, end, label }
const props = defineProps({
  modelValue: {
    type: Object,
    default: () => ({ period: 'this_quarter', start: '', end: '', label: '' })
  }
})

// Emits：切换时间范围时触发
const emit = defineEmits(['update:modelValue'])

// 当前选中的预设周期（默认本季度）
const selectedPeriod = ref(props.modelValue?.period || 'this_quarter')
// 自定义起止日期
const customStart = ref(props.modelValue?.start || '')
const customEnd = ref(props.modelValue?.end || '')

// 季度计算：Q1=1-3月, Q2=4-6月, Q3=7-9月, Q4=10-12月
function getQuarterBounds(date) {
  const month = date.getMonth() // 0-11
  const quarter = Math.floor(month / 3) // 0-3
  const startMonth = quarter * 3
  const endMonth = startMonth + 2
  const start = new Date(date.getFullYear(), startMonth, 1)
  const end = new Date(date.getFullYear(), endMonth + 1, 0) // 月末
  return { start, end }
}

// 下一季度的起止日期
function getNextQuarterBounds(date) {
  const month = date.getMonth()
  const quarter = Math.floor(month / 3)
  const nextQuarter = (quarter + 1) % 4
  const year = nextQuarter === 0 ? date.getFullYear() + 1 : date.getFullYear()
  const startMonth = nextQuarter * 3
  const endMonth = startMonth + 2
  const start = new Date(year, startMonth, 1)
  const end = new Date(year, endMonth + 1, 0)
  return { start, end }
}

// 日期格式化为 YYYY-MM-DD
function formatDateString(date) {
  const yyyy = date.getFullYear()
  const mm = String(date.getMonth() + 1).padStart(2, '0')
  const dd = String(date.getDate()).padStart(2, '0')
  return `${yyyy}-${mm}-${dd}`
}

// 本月起止
function getThisMonthBounds(date) {
  const start = new Date(date.getFullYear(), date.getMonth(), 1)
  const end = new Date(date.getFullYear(), date.getMonth() + 1, 0)
  return { start, end }
}

// 本年起止
function getThisYearBounds(date) {
  const start = new Date(date.getFullYear(), 0, 1)
  const end = new Date(date.getFullYear(), 11, 31)
  return { start, end }
}

// 根据预设周期计算 { period, start, end, label }
function computePresetRange(period) {
  const now = new Date()
  let bounds
  let label
  switch (period) {
    case 'this_month':
      bounds = getThisMonthBounds(now)
      label = t('dashboard.thisMonth')
      break
    case 'this_quarter':
      bounds = getQuarterBounds(now)
      label = t('dashboard.thisQuarter')
      break
    case 'next_quarter':
      bounds = getNextQuarterBounds(now)
      label = t('dashboard.nextQuarter')
      break
    case 'this_year':
      bounds = getThisYearBounds(now)
      label = t('dashboard.thisYear')
      break
    default:
      return null
  }
  return {
    period,
    start: formatDateString(bounds.start),
    end: formatDateString(bounds.end),
    label
  }
}

// 当前显示的时间范围文本
const rangeText = computed(() => {
  if (selectedPeriod.value === 'custom') {
    if (customStart.value && customEnd.value) {
      return `${customStart.value} ${t('dashboard.dateRangeTo')} ${customEnd.value}`
    }
    return ''
  }
  const range = computePresetRange(selectedPeriod.value)
  return range ? `${range.start} ${t('dashboard.dateRangeTo')} ${range.end}` : ''
})

// 预设切换：立即 emit 新值
function onPeriodChange() {
  if (selectedPeriod.value === 'custom') {
    // 自定义模式：保留已有日期，若两个日期都已填则 emit
    if (customStart.value && customEnd.value) {
      emit('update:modelValue', {
        period: 'custom',
        start: customStart.value,
        end: customEnd.value,
        label: `${customStart.value} ${t('dashboard.dateRangeTo')} ${customEnd.value}`
      })
    }
    return
  }
  const range = computePresetRange(selectedPeriod.value)
  if (range) {
    emit('update:modelValue', range)
  }
}

// 自定义日期变化：两个日期都填写后才 emit
function onCustomChange() {
  if (customStart.value && customEnd.value) {
    // 校验顺序：若起始日期晚于结束日期，自动交换
    if (customStart.value > customEnd.value) {
      const tmp = customStart.value
      customStart.value = customEnd.value
      customEnd.value = tmp
    }
    emit('update:modelValue', {
      period: 'custom',
      start: customStart.value,
      end: customEnd.value,
      label: `${customStart.value} ${t('dashboard.dateRangeTo')} ${customEnd.value}`
    })
  }
}

// 初始化时计算当前季度的日期范围并 emit
onMounted(() => {
  if (selectedPeriod.value === 'custom') {
    // 自定义模式：仅当两个日期都已填时 emit
    if (customStart.value && customEnd.value) {
      emit('update:modelValue', {
        period: 'custom',
        start: customStart.value,
        end: customEnd.value,
        label: `${customStart.value} ${t('dashboard.dateRangeTo')} ${customEnd.value}`
      })
    }
    return
  }
  // 预设模式：计算当前预设的日期范围并 emit
  const range = computePresetRange(selectedPeriod.value)
  if (range) {
    emit('update:modelValue', range)
  }
})
</script>

<style scoped>
/* 时间范围选择器：使用 .sales-twin 内的 CSS 变量保持视觉一致 */
.time-range-selector {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--text-primary);
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 6px 10px;
}

.trs-select {
  appearance: none;
  -webkit-appearance: none;
  background: transparent;
  border: 1px solid var(--border-strong);
  border-radius: 4px;
  padding: 4px 8px;
  font-size: 13px;
  color: var(--text-primary);
  cursor: pointer;
  line-height: 1.4;
  font-family: inherit;
}

.trs-select:focus-visible {
  outline: 2px solid var(--focus-ring);
  outline-offset: 1px;
}

.trs-custom-range {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  animation: trs-slide-in 0.2s ease;
}

.trs-date-input {
  border: 1px solid var(--border-strong);
  background: var(--bg-card);
  color: var(--text-primary);
  border-radius: 4px;
  padding: 4px 6px;
  font-size: 13px;
  font-family: inherit;
}

.trs-date-input:focus-visible {
  outline: 2px solid var(--focus-ring);
  outline-offset: 1px;
}

.trs-separator {
  color: var(--text-muted);
  font-size: 12px;
}

.trs-range-text {
  color: var(--text-secondary);
  font-size: 12px;
  white-space: nowrap;
}

/* 自定义日期输入框出现时的过渡动画 */
@keyframes trs-slide-in {
  from {
    opacity: 0;
    transform: translateX(-4px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}
</style>

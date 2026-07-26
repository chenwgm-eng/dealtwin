<template>
  <section class="info-section" aria-labelledby="proj-info-title">
    <div class="section-header">
      <span class="section-deco" aria-hidden="true">◇</span>
      <h3 id="proj-info-title" class="section-title">{{ t('project.projectInfo') }}</h3>
    </div>
    <div class="info-table">
      <!-- 客户名称：关联客户管理，下拉选择 -->
      <div class="info-row">
        <span class="info-label">{{ t('customer.customerName') }}</span>
        <select
          v-if="editing.field === 'customer_id'"
          v-focus v-model="editing.value"
          class="inline-edit-input"
          @change="saveEdit"
          @blur="saveEdit"
          @keydown.esc.prevent="cancelEdit"
          :disabled="editing.saving"
        >
          <option :value="null">{{ t('project.noCustomerLinked') }}</option>
          <option v-for="c in allCustomers" :key="c.id" :value="c.id">{{ c.name }}</option>
        </select>
        <span v-else
          class="info-value info-value-editable"
          @dblclick="startEdit('customer_id')"
          :title="t('project.dblclickToSelectCustomer')"
          tabindex="0"
          role="button"
          @keydown.enter="startEdit('customer_id')"
        >{{ currentProject?.customer_name || t('project.noCustomerLinked') }}</span>
      </div>
      <!-- 2列配对：预算 | 预算确定性 -->
      <div class="info-row-pair">
        <div class="info-pair-cell">
          <span class="info-label">{{ t('project.budget') }}</span>
          <input
            v-if="editing.field === 'budget'"
            v-focus v-model="editing.value"
            type="number"
            step="0.01"
            class="inline-edit-input"
            :placeholder="t('project.budgetPlaceholder')"
            @blur="saveEdit"
            @keydown.ctrl.enter.prevent="saveEdit"
            @keydown.esc.prevent="cancelEdit"
            :disabled="editing.saving"
          >
          <span v-else
            class="info-value info-value-editable"
            @dblclick="startEdit('budget')"
            :title="t('common.dblclickToEdit')"
            tabindex="0"
            role="button"
            @keydown.enter="startEdit('budget')"
          >{{ currentProject?.budget ? formatCurrency(currentProject.budget) : '-' }}</span>
        </div>
        <div class="info-pair-cell">
          <span class="info-label">{{ t('project.budgetCertainty') }}</span>
          <span class="info-value">
            <span class="cert-dots cert-dots-editable" role="radiogroup" :aria-label="t('project.budgetCertainty')">
              <button type="button" class="cert-dot" :class="{ active: currentProject?.budget_certainty === 1, red: currentProject?.budget_certainty === 1 }" :aria-checked="currentProject?.budget_certainty === 1" role="radio" :title="t('workspace.priorityLabels.low')" @click="setCert('budget_certainty', 1)"></button>
              <button type="button" class="cert-dot" :class="{ active: currentProject?.budget_certainty === 2, yellow: currentProject?.budget_certainty === 2 }" :aria-checked="currentProject?.budget_certainty === 2" role="radio" :title="t('workspace.priorityLabels.medium')" @click="setCert('budget_certainty', 2)"></button>
              <button type="button" class="cert-dot" :class="{ active: currentProject?.budget_certainty === 3, green: currentProject?.budget_certainty === 3 }" :aria-checked="currentProject?.budget_certainty === 3" role="radio" :title="t('workspace.priorityLabels.high')" @click="setCert('budget_certainty', 3)"></button>
            </span>
          </span>
        </div>
      </div>
      <!-- 2列配对：预计关闭 | 时间确定性 -->
      <div class="info-row-pair">
        <div class="info-pair-cell">
          <span class="info-label">{{ t('project.expectedCloseDate') }}</span>
          <input
            v-if="editing.field === 'expected_close_date'"
            v-focus v-model="editing.value"
            type="date"
            class="inline-edit-input"
            @blur="saveEdit"
            @keydown.ctrl.enter.prevent="saveEdit"
            @keydown.esc.prevent="cancelEdit"
            :disabled="editing.saving"
          >
          <span v-else
            class="info-value info-value-editable"
            @dblclick="startEdit('expected_close_date')"
            :title="t('common.dblclickToEdit')"
            tabindex="0"
            role="button"
            @keydown.enter="startEdit('expected_close_date')"
          >{{ currentProject?.expected_close_date ? formatDate(currentProject.expected_close_date) : t('project.dblclickToSet') }}</span>
        </div>
        <div class="info-pair-cell">
          <span class="info-label">{{ t('project.timeCertainty') }}</span>
          <span class="info-value">
            <span class="cert-dots cert-dots-editable" role="radiogroup" :aria-label="t('project.timeCertainty')">
              <button type="button" class="cert-dot" :class="{ active: currentProject?.time_certainty === 1, red: currentProject?.time_certainty === 1 }" :aria-checked="currentProject?.time_certainty === 1" role="radio" :title="t('workspace.priorityLabels.low')" @click="setCert('time_certainty', 1)"></button>
              <button type="button" class="cert-dot" :class="{ active: currentProject?.time_certainty === 2, yellow: currentProject?.time_certainty === 2 }" :aria-checked="currentProject?.time_certainty === 2" role="radio" :title="t('workspace.priorityLabels.medium')" @click="setCert('time_certainty', 2)"></button>
              <button type="button" class="cert-dot" :class="{ active: currentProject?.time_certainty === 3, green: currentProject?.time_certainty === 3 }" :aria-checked="currentProject?.time_certainty === 3" role="radio" :title="t('workspace.priorityLabels.high')" @click="setCert('time_certainty', 3)"></button>
            </span>
          </span>
        </div>
      </div>
      <!-- 2列配对：销售阶段 | 倾向性 -->
      <div class="info-row-pair">
        <div class="info-pair-cell">
          <span class="info-label">{{ t('project.salesStage') }}</span>
          <select
            v-if="editing.field === 'sales_stage'"
            v-focus v-model="editing.value"
            class="inline-edit-input"
            @change="saveEdit"
            @blur="saveEdit"
            @keydown.esc.prevent="cancelEdit"
            :disabled="editing.saving"
          >
            <option v-for="(label, key) in stageLabels" :key="key" :value="key">{{ label }}</option>
          </select>
          <span v-else
            class="info-value info-value-editable"
            @dblclick="startEdit('sales_stage')"
            :title="t('common.dblclickToEdit')"
            tabindex="0"
            role="button"
            @keydown.enter="startEdit('sales_stage')"
          >
            <span class="stage-badge" :class="`stage-${currentProject?.sales_stage || 'suspect'}`">{{ stageLabels[currentProject?.sales_stage] || '-' }}</span>
          </span>
        </div>
        <div class="info-pair-cell">
          <span class="info-label">{{ t('project.tendency') }}</span>
          <span class="info-value">
            <span class="cert-dots cert-dots-editable" role="radiogroup" :aria-label="t('project.tendency')">
              <button type="button" class="cert-dot" :class="{ active: currentProject?.tendency === 1, red: currentProject?.tendency === 1 }" :aria-checked="currentProject?.tendency === 1" role="radio" :title="t('workspace.priorityLabels.low')" @click="setCert('tendency', 1)"></button>
              <button type="button" class="cert-dot" :class="{ active: currentProject?.tendency === 2, yellow: currentProject?.tendency === 2 }" :aria-checked="currentProject?.tendency === 2" role="radio" :title="t('workspace.priorityLabels.medium')" @click="setCert('tendency', 2)"></button>
              <button type="button" class="cert-dot" :class="{ active: currentProject?.tendency === 3, green: currentProject?.tendency === 3 }" :aria-checked="currentProject?.tendency === 3" role="radio" :title="t('workspace.priorityLabels.high')" @click="setCert('tendency', 3)"></button>
            </span>
          </span>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { reactive, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { formatDate as defaultFormatDate, formatCurrency as defaultFormatCurrency } from '../../composables/salesTwin/formatters.js'

const { t } = useI18n()

const props = defineProps({
  currentProject: { type: Object, default: () => ({}) },
  allCustomers: { type: Array, default: () => [] },
  formatDate: { type: Function, default: defaultFormatDate },
  formatCurrency: { type: Function, default: defaultFormatCurrency },
})

const emit = defineEmits(['update-project'])

const stageLabels = computed(() => ({
  suspect: t('stages.suspect'),
  identity: t('stages.identity'),
  define: t('stages.define'),
  confirm: t('stages.confirm'),
  closed_won: t('stages.closed_won'),
  closed_lost: t('stages.closed_lost'),
}))

// v-focus 指令：渲染时自动聚焦
const vFocus = {
  mounted: (el) => {
    if (typeof el.focus === 'function') el.focus()
    if (el && typeof el.select === 'function' && el.tagName === 'INPUT') el.select()
  }
}

// 内联编辑状态
const editing = reactive({ field: null, value: '', saving: false })

function startEdit(field) {
  editing.field = field
  const raw = props.currentProject?.[field]
  // 数字字段保留原值，input v-model 会自动转字符串；其余字段统一为字符串
  if (field === 'budget') {
    editing.value = raw == null ? '' : String(raw)
  } else if (field === 'expected_close_date') {
    // 后端返回 ISO 日期字符串 'YYYY-MM-DD' 或 'YYYY-MM-DDTHH:MM:SS'
    if (!raw) {
      editing.value = ''
    } else {
      editing.value = String(raw).slice(0, 10)
    }
  } else if (field === 'customer_id') {
    // customer_id：null 或数字
    editing.value = raw == null ? null : raw
  } else {
    editing.value = raw ?? ''
  }
}

function cancelEdit() {
  editing.field = null
  editing.value = ''
}

async function saveEdit() {
  if (!editing.field || editing.saving) return
  const field = editing.field
  let newVal = editing.value
  const oldVal = props.currentProject?.[field] ?? ''
  editing.field = null
  // 数字字段：空字符串转 null，否则转数字
  if (field === 'budget') {
    if (newVal === '' || newVal == null) {
      newVal = null
    } else {
      const n = Number(newVal)
      newVal = Number.isFinite(n) ? n : oldVal
    }
  }
  // 日期字段：空字符串转 null
  if (field === 'expected_close_date' && !newVal) {
    newVal = null
  }
  // customer_id：空字符串/0 转 null，否则转数字
  if (field === 'customer_id') {
    if (newVal === '' || newVal == null || newVal === 0) {
      newVal = null
    } else {
      const n = Number(newVal)
      newVal = Number.isFinite(n) ? n : oldVal
    }
  }
  // 无变化直接退出
  const oldCmp = oldVal == null ? '' : oldVal
  const newCmp = newVal == null ? '' : newVal
  if (newCmp === oldCmp) return
  // 通过 emit 让父组件处理保存
  emit('update-project', { field, value: newVal })
}

// 确定性/倾向性：点击圆点直接保存（无需进入编辑模式）
function setCert(field, val) {
  const oldVal = props.currentProject?.[field] ?? null
  if (oldVal === val) return
  emit('update-project', { field, value: val })
}
</script>

<style scoped>
/* ============ 信息区块卡片 ============ */
.info-section {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 24px 28px;
  box-shadow: var(--shadow-sm);
}

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

/* ============ 项目信息表格布局 ============ */
.info-table {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.info-row {
  display: flex;
  align-items: baseline;
  gap: 16px;
  padding: 12px 0;
  border-bottom: 1px solid var(--divider);
}

.info-row:last-child {
  border-bottom: none;
}

.info-row-pair {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
  padding: 12px 0;
  border-bottom: 1px solid var(--divider);
}

.info-row-pair:last-child {
  border-bottom: none;
}

.info-pair-cell {
  display: flex;
  align-items: baseline;
  gap: 12px;
  min-width: 0;
}

.info-label {
  font-size: var(--fs-sm);
  color: var(--text-muted);
  white-space: nowrap;
  flex-shrink: 0;
  min-width: 70px;
}

.info-value {
  font-size: var(--fs-base);
  color: var(--text-primary);
  font-weight: 500;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ============ 内联编辑 ============ */
.info-value-editable {
  cursor: pointer;
  border-radius: 4px;
  transition: background 0.15s;
}

.info-value-editable:hover {
  background: var(--bg-surface);
  outline: 1px dashed var(--border-strong);
}

.info-value-editable:focus-visible {
  outline: 2px solid var(--focus-ring);
  outline-offset: 2px;
}

/* ============ 内联编辑 input/select ============ */
.inline-edit-input {
  flex: 1;
  min-width: 0;
  font-family: var(--font-sans);
  font-size: var(--fs-base);
  color: var(--text-primary);
  background: var(--bg-surface);
  border: 1px solid var(--accent);
  border-radius: 6px;
  padding: 6px 10px;
  touch-action: manipulation;
}

.inline-edit-input:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 2px rgba(205, 80, 54, 0.12);
}

.inline-edit-input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

select.inline-edit-input {
  cursor: pointer;
  appearance: auto;
}

/* ============ 三档点点组件 ============ */
.cert-dots {
  display: inline-flex;
  gap: 6px;
  align-items: center;
}

.cert-dot {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 2px solid var(--border-strong);
  background: var(--bg-card);
  padding: 0;
  position: relative;
}

.cert-dot.red { background: var(--red); border-color: var(--red); }
.cert-dot.yellow { background: var(--yellow); border-color: var(--yellow); }
.cert-dot.green { background: var(--green); border-color: var(--green); }
.cert-dot.active { transform: scale(1.15); }

/* 可点击的 cert-dots：button 元素重置 */
.cert-dots-editable .cert-dot {
  cursor: pointer;
  font: inherit;
  outline: none;
  transition: transform 0.12s ease, box-shadow 0.12s ease;
}

.cert-dots-editable .cert-dot:hover {
  transform: scale(1.2);
}

.cert-dots-editable .cert-dot:focus-visible {
  outline: 2px solid var(--focus-ring);
  outline-offset: 2px;
}

.cert-dots-editable .cert-dot:not(.active) {
  opacity: 0.55;
}

.cert-dots-editable .cert-dot:not(.active):hover {
  opacity: 0.85;
}

/* ============ 销售阶段徽章 ============ */
.stage-badge {
  font-family: var(--font-sans);
  font-size: var(--fs-xs);
  padding: 3px 8px;
  border: 1px solid var(--border);
  border-radius: 12px;
  color: var(--text-secondary);
  background: var(--bg-card);
  white-space: nowrap;
  flex-shrink: 0;
  letter-spacing: 0.02em;
}

.stage-badge.suspect { border-color: var(--yellow); color: var(--yellow); background: var(--yellow-light); }
.stage-badge.identity { border-color: var(--blue); color: var(--blue); background: var(--blue-light); }
.stage-badge.define { border-color: var(--green); color: var(--green); background: var(--green-light); }
.stage-badge.confirm { border-color: var(--accent); color: var(--accent-hover); background: var(--bg-surface); }
.stage-badge.closed_won { border-color: var(--green); color: var(--green); background: var(--green-light); }
.stage-badge.closed_lost { border-color: var(--red); color: var(--red); background: var(--red-light); }
</style>

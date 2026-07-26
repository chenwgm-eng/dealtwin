<template>
  <div v-if="show" class="modal-overlay" tabindex="-1" role="dialog" aria-modal="true"
    :aria-label="t('closeReview.title')"
    @click.self="skip" @keydown.esc="skip">
    <div class="modal cr-modal">
      <div class="modal-header">
        <h3 class="modal-title">{{ t('closeReview.title') }}</h3>
        <button type="button" class="modal-close" :disabled="submitting" @click="skip" :aria-label="t('common.close')">×</button>
      </div>
      <div class="modal-body">
        <!-- 结果（只读） -->
        <div class="cr-result" :class="result">
          <span class="cr-result-dot" aria-hidden="true"></span>
          {{ t('closeReview.result') }}：{{ result === 'closed_won' ? t('closeReview.won') : t('closeReview.lost') }}
        </div>
        <p v-if="result === 'closed_lost'" class="cr-hint">{{ t('closeReview.lostHint') }}</p>

        <!-- 原因分类 -->
        <div class="cr-form-group">
          <span class="cr-field-label">{{ t('closeReview.reasonCategory') }}</span>
          <div class="cr-category-row" role="radiogroup" :aria-label="t('closeReview.reasonCategory')">
            <button
              v-for="cat in CATEGORIES"
              :key="cat"
              type="button"
              role="radio"
              :aria-checked="form.close_reason_category === cat"
              :class="['cr-category-btn', { active: form.close_reason_category === cat }]"
              @click="form.close_reason_category = cat"
            >{{ t('closeReview.categories.' + cat) }}</button>
          </div>
        </div>

        <!-- 原因详述 -->
        <div class="cr-form-group">
          <label class="cr-field-label" for="cr-detail">{{ t('closeReview.reasonDetail') }}</label>
          <textarea id="cr-detail" v-model="form.close_reason_detail" rows="3" class="cr-input"
            :placeholder="t('common.optional')"></textarea>
        </div>

        <!-- 经验教训 -->
        <div class="cr-form-group">
          <label class="cr-field-label" for="cr-lessons">{{ t('closeReview.lessonsLearned') }}</label>
          <textarea id="cr-lessons" v-model="form.lessons_learned" rows="3" class="cr-input"
            :placeholder="t('common.optional')"></textarea>
        </div>
      </div>
      <div class="modal-footer">
        <button type="button" class="cr-link" :disabled="submitting" @click="skip">{{ t('closeReview.later') }}</button>
        <button type="button" class="btn-primary" :disabled="submitting || !form.close_reason_category" @click="submit">
          {{ submitting ? t('common.saving') : t('closeReview.submit') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { submitCloseReview } from '../../api/salesTwin'
import { showToast } from '../../composables/salesTwin/useConfirmToast'

const { t } = useI18n()

const props = defineProps({
  show: { type: Boolean, default: false },
  projectId: { type: [Number, String], default: null },
  // 'closed_won' | 'closed_lost'
  result: { type: String, default: 'closed_lost' },
  // 当前项目对象（用于预填已有复盘）
  project: { type: Object, default: null },
})

const emit = defineEmits(['close', 'submitted'])

const CATEGORIES = ['price', 'product', 'relationship', 'competition', 'timing', 'no_decision', 'other']

const submitting = ref(false)
const form = reactive({
  close_reason_category: '',
  close_reason_detail: '',
  lessons_learned: '',
})

watch(() => props.show, (v) => {
  if (!v) return
  form.close_reason_category = props.project?.close_reason_category || ''
  form.close_reason_detail = props.project?.close_reason_detail || ''
  form.lessons_learned = props.project?.lessons_learned || ''
})

function skip() {
  if (submitting.value) return
  emit('close')
}

async function submit() {
  if (submitting.value || !props.projectId || !form.close_reason_category) return
  submitting.value = true
  try {
    await submitCloseReview(props.projectId, {
      close_reason_category: form.close_reason_category,
      close_reason_detail: form.close_reason_detail || '',
      lessons_learned: form.lessons_learned || '',
    })
    showToast(t('closeReview.submitSuccess'), 'success')
    emit('submitted')
    emit('close')
  } catch (e) {
    console.error('提交复盘失败:', e)
    showToast(t('closeReview.submitFailed', { reason: e?.message || e }), 'error')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.cr-modal {
  max-width: 520px;
  width: 92%;
}

.cr-result {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 14px;
}

.cr-result.closed_won {
  background: var(--green-light, rgba(17, 138, 88, 0.08));
  color: var(--green, #118A58);
}

.cr-result.closed_lost {
  background: var(--red-light, rgba(196, 57, 28, 0.08));
  color: var(--red, #C4391C);
}

.cr-result-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
}

.cr-hint {
  margin: -6px 0 14px;
  font-size: 11px;
  color: rgba(21, 23, 29, 0.6);
  background: rgba(205, 80, 54, 0.06);
  border-left: 2px solid var(--accent, #CD5036);
  padding: 8px 12px;
  border-radius: 0 4px 4px 0;
  line-height: 1.6;
}

.cr-form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 14px;
}

.cr-field-label {
  font-size: 11px;
  color: rgba(21, 23, 29, 0.5);
  font-family: var(--font-mono, 'JetBrains Mono', monospace);
}

.cr-category-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.cr-category-btn {
  padding: 5px 12px;
  border: 1px solid rgba(21, 23, 29, 0.15);
  border-radius: 4px;
  background: var(--bg-card, #FCFBF5);
  cursor: pointer;
  font-size: 12px;
  font-family: inherit;
  color: rgba(21, 23, 29, 0.65);
  transition: background 0.12s, border-color 0.12s, color 0.12s;
}

.cr-category-btn:hover {
  border-color: var(--accent, #CD5036);
  color: var(--accent, #CD5036);
}

.cr-category-btn.active {
  background: var(--text-primary, #15171D);
  border-color: var(--text-primary, #15171D);
  color: var(--bg-card, #FCFBF5);
}

.cr-input {
  padding: 6px 8px;
  border: 1px solid rgba(21, 23, 29, 0.15);
  border-radius: 2px;
  font-size: 12px;
  font-family: inherit;
  background: var(--bg-card, #FCFBF5);
  resize: vertical;
}

.cr-input:focus {
  outline: 2px solid transparent;
  border-color: var(--accent, #CD5036);
}

.cr-link {
  background: none;
  border: none;
  color: rgba(21, 23, 29, 0.6);
  cursor: pointer;
  font-size: 12px;
  padding: 4px 8px;
  text-decoration: underline;
  font-family: inherit;
}

.cr-link:hover:not(:disabled) {
  color: var(--text-primary, #15171D);
}

/* 弹窗基础样式（与现有 modal 风格一致的最小子集） */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(21, 23, 29, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: var(--bg-card, #FCFBF5);
  border-radius: 8px;
  box-shadow: 0 12px 40px rgba(21, 23, 29, 0.18);
  display: flex;
  flex-direction: column;
  max-height: 88vh;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  border-bottom: 1px solid var(--border, #E8E8E0);
}

.modal-title {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary, #15171D);
}

.modal-close {
  background: none;
  border: none;
  font-size: 20px;
  line-height: 1;
  cursor: pointer;
  color: rgba(21, 23, 29, 0.5);
  padding: 2px 6px;
}

.modal-close:hover:not(:disabled) {
  color: var(--text-primary, #15171D);
}

.modal-body {
  padding: 16px 18px;
  overflow-y: auto;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 12px 18px;
  border-top: 1px solid var(--border, #E8E8E0);
}

.btn-primary {
  background: var(--green, #118A58);
  color: #fff;
  border: 1px solid var(--green, #118A58);
  padding: 7px 16px;
  font-size: 12px;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  border-radius: 6px;
}

.btn-primary:disabled {
  background: #93BFA3;
  border-color: #93BFA3;
  cursor: not-allowed;
}
</style>

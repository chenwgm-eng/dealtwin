<template>
  <div class="agent-job-manager">
    <!-- 页面标题 -->
    <header class="page-header">
      <div class="header-left">
        <span class="section-deco" aria-hidden="true">◇</span>
        <h1 class="page-title">{{ t('agent.title') }}</h1>
      </div>
      <div class="header-right">
        <span class="project-count">{{ jobs.length }} JOBS</span>
      </div>
    </header>

    <!-- 加载中 -->
    <div v-if="loading" class="empty-state" role="status" aria-live="polite">
      <div class="ajm-spinner" aria-hidden="true"></div>
      <p class="empty-text">{{ t('common.loading') }}</p>
    </div>

    <!-- 空状态 -->
    <div v-else-if="!jobs.length" class="empty-state" aria-live="polite">
      <div class="empty-icon" aria-hidden="true">⏱</div>
      <p class="empty-text">{{ t('agent.noJobs') }}</p>
      <p class="empty-hint">{{ t('agent.noJobsHint') }}</p>
    </div>

    <!-- 任务卡片列表 -->
    <div v-else class="ajm-job-list">
      <article
        v-for="job in jobs"
        :key="job.id"
        class="job-card"
        :class="{ paused: job.is_paused }"
      >
        <div class="job-card-header">
          <div class="job-main">
            <div class="job-top">
              <h3 class="job-name">{{ jobDisplayName(job.id) }}</h3>
              <span class="job-status" :class="job.is_paused ? 'paused' : 'running'">
                {{ job.is_paused ? t('agent.status.paused') : t('agent.status.running') }}
              </span>
            </div>
            <p class="job-desc">{{ jobDescription(job.id) }}</p>
            <div class="job-meta">
              <span class="meta-item">
                <svg class="meta-icon" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
                  <circle cx="8" cy="8" r="6"/>
                  <path d="M8 4v4l2.5 2"/>
                </svg>
                <span class="meta-label">{{ t('agent.schedule') }}</span>
                <code class="meta-value">{{ job.cron_expr }}</code>
              </span>
              <span v-if="job.next_run_time && !job.is_paused" class="meta-item">
                <svg class="meta-icon" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
                  <rect x="2" y="3" width="12" height="11" rx="1.5"/>
                  <path d="M2 6h12M5 1.5v3M11 1.5v3"/>
                </svg>
                <span class="meta-label">{{ t('agent.nextRun') }}</span>
                <span class="meta-value">{{ formatDateTime(job.next_run_time) }}</span>
              </span>
            </div>
          </div>

          <div class="job-actions">
            <button
              v-if="job.is_paused"
              type="button"
              class="btn-secondary btn-sm"
              :disabled="actingId === job.id"
              @click="handleResume(job.id)"
            >
              <span v-if="actingId === job.id" class="btn-spinner" aria-hidden="true"></span>
              {{ t('agent.resume') }}
            </button>
            <button
              v-else
              type="button"
              class="btn-secondary btn-sm"
              :disabled="actingId === job.id"
              @click="handlePause(job.id)"
            >
              <span v-if="actingId === job.id" class="btn-spinner" aria-hidden="true"></span>
              {{ t('agent.pause') }}
            </button>
            <button
              type="button"
              class="btn-secondary btn-sm"
              :disabled="actingId === job.id"
              @click="handleRunNow(job)"
            >
              {{ t('agent.runNow') }}
            </button>
            <button
              type="button"
              class="btn-primary btn-sm"
              @click="openEditModal(job)"
            >
              {{ t('agent.setSchedule') }}
            </button>
          </div>
        </div>

        <!-- 最近运行记录 -->
        <div class="job-runs" v-if="jobRuns[job.id] && jobRuns[job.id].length">
          <div class="job-runs-title">
            <svg class="runs-icon" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.4" aria-hidden="true">
              <path d="M2 7a5 5 0 1 0 5-5"/>
              <path d="M4 4L2 2M2 2v3"/>
            </svg>
            <span>{{ t('agent.runHistory') }}</span>
          </div>
          <ul class="runs-list">
            <li v-for="run in jobRuns[job.id].slice(0, 3)" :key="run.id" class="run-item">
              <span class="run-status-dot" :class="run.status" :title="runStatusText(run.status)" aria-hidden="true"></span>
              <span class="run-time">{{ formatDateTime(run.started_at) }}</span>
              <span class="run-summary" :title="run.summary">{{ run.summary || runStatusText(run.status) }}</span>
            </li>
          </ul>
        </div>
        <div class="job-runs job-runs-empty" v-else-if="jobRunsLoaded[job.id]">
          <span class="runs-empty-text">{{ t('agent.noRuns') }}</span>
        </div>
      </article>
    </div>

    <!-- 时间设置弹窗 -->
    <div v-if="editingJob" class="ajm-modal-overlay" @click.self="closeEditModal">
      <div class="ajm-modal" role="dialog" aria-modal="true" :aria-label="t('agent.setSchedule') + ' - ' + jobDisplayName(editingJob.id)">
        <div class="ajm-modal-header">
          <h3 class="ajm-modal-title">{{ t('agent.setSchedule') }}</h3>
          <button type="button" class="ajm-modal-close" @click="closeEditModal" :aria-label="t('common.close')">
            <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true">
              <path d="M3.5 3.5l9 9M12.5 3.5l-9 9"/>
            </svg>
          </button>
        </div>
        <div class="ajm-modal-body">
          <p class="ajm-modal-job-name">{{ jobDisplayName(editingJob.id) }}</p>
          <div class="ajm-form-group">
            <label for="edit-hour">{{ t('agent.hourField') }}</label>
            <input id="edit-hour" v-model="editForm.hour" type="text" placeholder="*" />
          </div>
          <div class="ajm-form-group">
            <label for="edit-minute">{{ t('agent.minuteField') }}</label>
            <input id="edit-minute" v-model="editForm.minute" type="text" placeholder="0" />
          </div>
          <div class="ajm-form-group">
            <label for="edit-dow">{{ t('agent.dowField') }}</label>
            <input id="edit-dow" v-model="editForm.day_of_week" type="text" placeholder="*" />
          </div>
        </div>
        <div class="ajm-modal-actions">
          <button type="button" class="btn-secondary" @click="closeEditModal">{{ t('common.cancel') }}</button>
          <button type="button" class="btn-primary" :disabled="savingSchedule" @click="submitSchedule">
            <span v-if="savingSchedule" class="btn-spinner" aria-hidden="true"></span>
            {{ t('agent.saveSchedule') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  getAgentJobs, pauseAgentJob, resumeAgentJob,
  runAgentJobNow, updateAgentJobSchedule, getAgentJobRuns
} from '../../api/salesTwin'
import { requestConfirm, showToast } from '../../composables/salesTwin/useConfirmToast'

const { t } = useI18n()

const jobs = ref([])
const loading = ref(false)
const actingId = ref(null)
const editingJob = ref(null)
const savingSchedule = ref(false)
const editForm = ref({ hour: '*', minute: '0', day_of_week: '*' })
// 任务运行历史：{ [job_id]: RunRecord[] }
const jobRuns = ref({})
const jobRunsLoaded = ref({})  // 标记哪些 job 已加载过运行记录

// 任务 ID → i18n key 映射
const JOB_NAME_KEYS = {
  Daily_Health_Scan: 'agent.dailyHealthScan',
  Daily_News_Fetch: 'agent.dailyNewsFetch',
  Weekly_Learning_Eval: 'agent.weeklyLearningEval',
}
const JOB_DESC_KEYS = {
  Daily_Health_Scan: 'agent.jobDescription.dailyHealthScan',
  Daily_News_Fetch: 'agent.jobDescription.dailyNewsFetch',
  Weekly_Learning_Eval: 'agent.jobDescription.weeklyLearningEval',
}

function jobDisplayName(id) {
  return JOB_NAME_KEYS[id] ? t(JOB_NAME_KEYS[id]) : id
}

function jobDescription(id) {
  return JOB_DESC_KEYS[id] ? t(JOB_DESC_KEYS[id]) : ''
}

function formatDateTime(isoStr) {
  if (!isoStr) return '—'
  try {
    const d = new Date(isoStr)
    const month = String(d.getMonth() + 1).padStart(2, '0')
    const day = String(d.getDate()).padStart(2, '0')
    const hour = String(d.getHours()).padStart(2, '0')
    const minute = String(d.getMinutes()).padStart(2, '0')
    return `${month}-${day} ${hour}:${minute}`
  } catch {
    return isoStr
  }
}

function runStatusText(status) {
  const map = {
    success: t('agent.status.success'),
    failed: t('agent.status.failed'),
    partial: t('agent.status.partial'),
  }
  return map[status] || status
}

// 获取所有任务的最近运行记录（并行请求）
async function fetchAllJobRuns() {
  for (const job of jobs.value) {
    fetchJobRuns(job.id)
  }
}

async function fetchJobRuns(jobId) {
  try {
    const res = await getAgentJobRuns(jobId, 5)
    if (res.success) {
      jobRuns.value[jobId] = res.data || []
    }
    jobRunsLoaded.value[jobId] = true
  } catch (e) {
    jobRunsLoaded.value[jobId] = true
    // 运行记录加载失败不提示，保持静默
  }
}

const fetchJobs = async () => {
  loading.value = true
  try {
    const res = await getAgentJobs()
    if (res.success) {
      jobs.value = res.data || []
      // 加载任务列表后并行获取每个任务的运行历史
      fetchAllJobRuns()
    }
  } catch (e) {
    showToast(t('toast.loadFailed'), 'error')
  } finally {
    loading.value = false
  }
}

const handlePause = async (id) => {
  actingId.value = id
  try {
    await pauseAgentJob(id)
    showToast(t('agent.jobPaused'), 'info')
    await fetchJobs()
  } catch (e) {
    showToast(t('toast.operationFailed'), 'error')
  } finally {
    actingId.value = null
  }
}

const handleResume = async (id) => {
  actingId.value = id
  try {
    await resumeAgentJob(id)
    showToast(t('agent.jobResumed'), 'success')
    await fetchJobs()
  } catch (e) {
    showToast(t('toast.operationFailed'), 'error')
  } finally {
    actingId.value = null
  }
}

const handleRunNow = async (job) => {
  const ok = await requestConfirm({
    title: t('modal.confirmTitle'),
    message: t('agent.confirmRun', { name: jobDisplayName(job.id) }),
    confirmText: t('common.confirm'),
    cancelText: t('common.cancel'),
  })
  if (!ok) return
  actingId.value = job.id
  try {
    await runAgentJobNow(job.id)
    showToast(t('agent.runDispatched'), 'success')
    await fetchJobs()
    // 延迟刷新运行记录，等待任务执行完成
    setTimeout(() => fetchJobRuns(job.id), 5000)
  } catch (e) {
    showToast(t('toast.operationFailed'), 'error')
  } finally {
    actingId.value = null
  }
}

function openEditModal(job) {
  editingJob.value = job
  // 从 cron_expr 解析回填表单（格式: "minute hour day month day_of_week"）
  const parts = (job.cron_expr || '').split(/\s+/)
  editForm.value = {
    minute: parts[0] || '0',
    hour: parts[1] || '*',
    day_of_week: parts[4] || '*',
  }
}

function closeEditModal() {
  editingJob.value = null
}

const submitSchedule = async () => {
  savingSchedule.value = true
  try {
    await updateAgentJobSchedule(editingJob.value.id, editForm.value)
    showToast(t('toast.saveSuccess'), 'success')
    editingJob.value = null
    await fetchJobs()
  } catch (e) {
    showToast(t('toast.updateFailed'), 'error')
  } finally {
    savingSchedule.value = false
  }
}

onMounted(() => {
  fetchJobs()
})
</script>

<style scoped>
/* 任务卡片列表 */
.ajm-job-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.job-card {
  display: flex;
  flex-direction: column;
  gap: 14px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 18px;
  box-shadow: var(--shadow-sm);
  transition: box-shadow 0.15s, border-color 0.15s, transform 0.1s;
}

.job-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.job-card:hover {
  border-color: var(--border-strong);
  box-shadow: var(--shadow-md);
  transform: translateY(-1px);
}

.job-card.paused {
  opacity: 0.65;
}

.job-main {
  flex: 1;
  min-width: 0;
}

.job-top {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 4px;
}

.job-name {
  font-size: var(--fs-lg);
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
  letter-spacing: -0.005em;
}

.job-status {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: var(--fs-xs);
  font-weight: 600;
  letter-spacing: 0.03em;
  flex-shrink: 0;
}

.job-status.running {
  background: var(--green-light);
  color: var(--green);
  border: 1px solid rgba(17, 138, 88, 0.2);
}

.job-status.paused {
  background: rgba(205, 80, 54, 0.08);
  color: var(--accent);
  border: 1px solid rgba(205, 80, 54, 0.2);
}

.job-desc {
  font-size: var(--fs-sm);
  color: var(--text-secondary);
  margin: 0 0 10px;
  line-height: 1.5;
}

.job-meta {
  display: flex;
  gap: 18px;
  flex-wrap: wrap;
}

.meta-item {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: var(--fs-xs);
  color: var(--text-tertiary);
}

.meta-icon {
  width: 13px;
  height: 13px;
  flex-shrink: 0;
  opacity: 0.8;
}

.meta-label {
  color: var(--text-tertiary);
}

.meta-value {
  color: var(--text-secondary);
  font-variant-numeric: tabular-nums;
}

.meta-value.code,
code.meta-value {
  font-family: var(--font-mono, 'SF Mono', 'Consolas', monospace);
  font-size: var(--fs-xs);
  background: rgba(21, 23, 29, 0.04);
  padding: 1px 6px;
  border-radius: 4px;
  border: 1px solid var(--border);
}

.job-actions {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
}

/* 最近运行记录 */
.job-runs {
  padding-top: 12px;
  border-top: 1px dashed var(--border);
}

.job-runs-title {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: var(--fs-xs);
  color: var(--text-tertiary);
  font-weight: 600;
  margin-bottom: 8px;
  letter-spacing: 0.02em;
}

.runs-icon {
  width: 12px;
  height: 12px;
  opacity: 0.7;
}

.runs-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.run-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: var(--fs-xs);
  color: var(--text-secondary);
}

.run-status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}

.run-status-dot.success {
  background: var(--green);
}

.run-status-dot.failed {
  background: var(--red);
}

.run-status-dot.partial {
  background: var(--yellow);
}

.run-time {
  font-family: var(--font-mono, 'SF Mono', 'Consolas', monospace);
  color: var(--text-tertiary);
  font-variant-numeric: tabular-nums;
  flex-shrink: 0;
  min-width: 90px;
}

.run-summary {
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  min-width: 0;
}

.job-runs-empty {
  padding-top: 12px;
  border-top: 1px dashed var(--border);
}

.runs-empty-text {
  font-size: var(--fs-xs);
  color: var(--text-muted);
}

/* 加载动画 */
.ajm-spinner {
  width: 28px;
  height: 28px;
  border: 2.5px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  margin: 0 auto 12px;
  animation: ajm-spin 0.7s linear infinite;
}

@keyframes ajm-spin {
  to { transform: rotate(360deg); }
}

.btn-spinner {
  display: inline-block;
  width: 12px;
  height: 12px;
  border: 2px solid currentColor;
  border-top-color: transparent;
  border-radius: 50%;
  animation: ajm-spin 0.6s linear infinite;
  margin-right: 2px;
}

/* 弹窗 */
.ajm-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(21, 23, 29, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: ajm-fade-in 0.15s ease;
}

@keyframes ajm-fade-in {
  from { opacity: 0; }
  to { opacity: 1; }
}

.ajm-modal {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 12px;
  box-shadow: var(--shadow-lg);
  width: 400px;
  max-width: calc(100vw - 32px);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.ajm-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border);
}

.ajm-modal-title {
  font-size: var(--fs-md);
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.ajm-modal-close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  padding: 0;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: var(--text-tertiary);
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}

.ajm-modal-close:hover {
  background: rgba(21, 23, 29, 0.06);
  color: var(--text-primary);
}

.ajm-modal-close svg {
  width: 14px;
  height: 14px;
}

.ajm-modal-body {
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.ajm-modal-job-name {
  font-size: var(--fs-sm);
  font-weight: 600;
  color: var(--text-secondary);
  margin: 0 0 4px;
  padding: 6px 10px;
  background: rgba(205, 80, 54, 0.05);
  border-radius: 6px;
  border: 1px solid rgba(205, 80, 54, 0.1);
}

.ajm-form-group {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.ajm-form-group label {
  font-size: var(--fs-xs);
  color: var(--text-tertiary);
  font-weight: 500;
}

.ajm-form-group input {
  padding: 7px 10px;
  border: 1px solid var(--border-strong);
  border-radius: 6px;
  font-size: var(--fs-sm);
  font-family: var(--font-mono, 'SF Mono', 'Consolas', monospace);
  color: var(--text-primary);
  background: var(--bg-card);
  transition: border-color 0.15s, box-shadow 0.15s;
}

.ajm-form-group input:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 2px rgba(205, 80, 54, 0.1);
}

.ajm-modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 14px 20px;
  border-top: 1px solid var(--border);
}

/* 减少动画 */
@media (prefers-reduced-motion: reduce) {
  .job-card,
  .ajm-spinner,
  .btn-spinner,
  .ajm-modal-overlay {
    transition: none;
    animation: none;
  }
}
</style>

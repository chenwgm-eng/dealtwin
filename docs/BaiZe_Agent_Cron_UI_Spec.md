# 白泽 (BaiZe OS) - Agent 定时任务可视化管理 UI 开发指南

> **目标受众**: AI 辅助编程系统 (Cursor/Trae/Windsurf 等)
> **架构核心**: 在 Vue 3 前端提供对 Flask-APScheduler 定时任务的完整生命周期管理（查看、暂停、恢复、立即执行、修改定时规则）。

---

## 1. 后端 API 扩展 (Backend API)
**修改/新建文件**: `backend/app/api/sales_twin/agent_monitor.py`

在之前的基础上，丰富调度器管理 API。`Flask-APScheduler` 默认提供了部分功能，但为了与前端统一，我们自定义包装。

```python
from flask import request, jsonify
from app.api.sales_twin import sales_twin_bp
from app.extensions import scheduler

@sales_twin_bp.route('/agent/jobs', methods=['GET'])
def get_agent_jobs():
    # 获取任务列表及详细调度信息
    jobs = scheduler.get_jobs()
    job_list = []
    for job in jobs:
        trigger = job.trigger
        # 解析 cron trigger 的表达式供前端回显
        cron_expr = str(trigger) if hasattr(trigger, 'fields') else "N/A"

        job_list.append({
            "id": job.id,
            "name": job.name,
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            "is_paused": job.next_run_time is None, # next_run_time 为空通常表示已暂停
            "cron_expr": cron_expr
        })
    return jsonify({"success": True, "data": job_list})

@sales_twin_bp.route('/agent/jobs/<job_id>/pause', methods=['POST'])
def pause_job(job_id):
    scheduler.pause_job(job_id)
    return jsonify({"success": True, "message": f"任务 {job_id} 已暂停"})

@sales_twin_bp.route('/agent/jobs/<job_id>/resume', methods=['POST'])
def resume_job(job_id):
    scheduler.resume_job(job_id)
    return jsonify({"success": True, "message": f"任务 {job_id} 已恢复"})

@sales_twin_bp.route('/agent/jobs/<job_id>/run', methods=['POST'])
def run_job_now(job_id):
    # 立即异步执行一次任务，不影响原有时间表
    scheduler.modify_job(job_id, next_run_time=datetime.now(timezone.utc))
    return jsonify({"success": True, "message": f"任务 {job_id} 已触发执行"})

@sales_twin_bp.route('/agent/jobs/<job_id>/schedule', methods=['PUT'])
def update_job_schedule(job_id):
    # 更新 cron 表达式 (示例：接收 hour, minute)
    data = request.json
    hour = data.get('hour', '*')
    minute = data.get('minute', '0')
    day_of_week = data.get('day_of_week', '*')

    scheduler.modify_job(job_id, trigger='cron', hour=hour, minute=minute, day_of_week=day_of_week)
    return jsonify({"success": True, "message": f"任务 {job_id} 定时规则已更新"})
```

---

## 2. 前端 API 封装 (Frontend API)
**修改文件**: `frontend/src/api/salesTwin.js`

新增针对 Agent 任务的接口：

```javascript
// Agent 定时任务管理
export const getAgentJobs = () => request.get('/sales-twin/agent/jobs');
export const pauseAgentJob = (jobId) => request.post(`/sales-twin/agent/jobs/${jobId}/pause`);
export const resumeAgentJob = (jobId) => request.post(`/sales-twin/agent/jobs/${jobId}/resume`);
export const runAgentJobNow = (jobId) => request.post(`/sales-twin/agent/jobs/${jobId}/run`);
export const updateAgentJobSchedule = (jobId, scheduleData) => request.put(`/sales-twin/agent/jobs/${jobId}/schedule`, scheduleData);
```

---

## 3. 前端 UI 组件开发 (Frontend View)

### 3.1 增加侧边栏入口
**修改文件**: `frontend/src/components/SalesTwinSidebar.vue`
在菜单中增加一项“白泽中枢”或“Agent 任务”，`activeMenu` 设为 `'agent_jobs'`。

### 3.2 任务管理面板组件
**新建文件**: `frontend/src/components/salesTwin/AgentJobManager.vue`

```vue
<template>
  <div class="agent-job-manager">
    <div class="header">
      <h2>白泽 Agent 调度中枢</h2>
      <p class="subtitle">管理后台自动化策略提取、盲区扫描与情报抓取任务</p>
    </div>

    <div class="job-list">
      <div v-for="job in jobs" :key="job.id" class="job-card" :class="{ paused: job.is_paused }">
        <div class="job-info">
          <h3>{{ job.name || job.id }}</h3>
          <div class="job-meta">
            <span class="badge" :class="job.is_paused ? 'badge-warning' : 'badge-success'">
              {{ job.is_paused ? '已暂停' : '运行中' }}
            </span>
            <span class="schedule"><i data-lucide="clock"></i> 规则: {{ job.cron_expr }}</span>
            <span class="next-run" v-if="!job.is_paused">
              下次执行: {{ formatDateTime(job.next_run_time) }}
            </span>
          </div>
        </div>

        <div class="job-actions">
          <button v-if="job.is_paused" @click="handleResume(job.id)" class="btn-ghost text-success">恢复</button>
          <button v-else @click="handlePause(job.id)" class="btn-ghost text-warning">暂停</button>
          <button @click="handleRunNow(job.id)" class="btn-ghost text-primary">立即执行</button>
          <button @click="openEditModal(job)" class="btn-primary">设置时间</button>
        </div>
      </div>
    </div>

    <!-- 时间设置弹窗 (简易版) -->
    <div v-if="editingJob" class="modal-overlay" @click.self="editingJob = null">
      <div class="modal-content">
        <h3>设置执行时间: {{ editingJob.name || editingJob.id }}</h3>
        <div class="form-group">
          <label>小时 (0-23, * 表示每小时)</label>
          <input v-model="editForm.hour" type="text" placeholder="*" />
        </div>
        <div class="form-group">
          <label>分钟 (0-59)</label>
          <input v-model="editForm.minute" type="text" placeholder="0" />
        </div>
        <div class="form-group">
          <label>星期 (mon, tue, *, 等)</label>
          <input v-model="editForm.day_of_week" type="text" placeholder="*" />
        </div>
        <div class="modal-actions">
          <button @click="editingJob = null" class="btn-ghost">取消</button>
          <button @click="submitSchedule" class="btn-primary">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { getAgentJobs, pauseAgentJob, resumeAgentJob, runAgentJobNow, updateAgentJobSchedule } from '@/api/salesTwin';
import { formatDateTime } from '@/composables/formatters';
import { useConfirmToast } from '@/composables/salesTwin/useConfirmToast';

const { showToast } = useConfirmToast();
const jobs = ref([]);
const editingJob = ref(null);
const editForm = ref({ hour: '*', minute: '0', day_of_week: '*' });

const fetchJobs = async () => {
  try {
    const res = await getAgentJobs();
    if (res.data.success) {
      jobs.value = res.data.data;
    }
  } catch (error) {
    showToast('获取任务列表失败', 'error');
  }
};

const handlePause = async (id) => {
  await pauseAgentJob(id);
  showToast('任务已暂停', 'success');
  fetchJobs();
};

const handleResume = async (id) => {
  await resumeAgentJob(id);
  showToast('任务已恢复', 'success');
  fetchJobs();
};

const handleRunNow = async (id) => {
  await runAgentJobNow(id);
  showToast('已下发立即执行指令', 'success');
  fetchJobs();
};

const openEditModal = (job) => {
  editingJob.value = job;
  // 简单重置表单，实际应用中可以从 job.cron_expr 解析回填
  editForm.value = { hour: '*', minute: '0', day_of_week: '*' };
};

const submitSchedule = async () => {
  try {
    await updateAgentJobSchedule(editingJob.value.id, editForm.value);
    showToast('时间规则已更新', 'success');
    editingJob.value = null;
    fetchJobs();
  } catch (error) {
    showToast('更新失败', 'error');
  }
};

onMounted(() => {
  fetchJobs();
});
</script>

<style scoped>
/* 继承项目现有的 CSS 变量 */
.agent-job-manager {
  padding: var(--space-6);
  max-width: var(--content-default);
  margin: 0 auto;
}
.header { margin-bottom: var(--space-8); }
.subtitle { color: var(--color-text-muted); }
.job-list { display: flex; flex-direction: column; gap: var(--space-4); }
.job-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-4) var(--space-6);
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
}
.job-card.paused { opacity: 0.7; background: var(--color-surface-offset); }
.job-meta {
  display: flex;
  gap: var(--space-4);
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  margin-top: var(--space-2);
  align-items: center;
}
.job-actions { display: flex; gap: var(--space-2); }
/* Modal styles... 沿用系统现有弹窗样式 */
</style>
```

### 3.3 路由/主视图接入
**修改文件**: `frontend/src/views/SalesTwin.vue`
在动态渲染区域（如 `<component :is="currentComponent">` 或 `v-if/v-else` 逻辑）中，增加对 `activeMenu === 'agent_jobs'` 的处理，渲染 `<AgentJobManager />`。

import * as salesTwinApi from '../../api/salesTwin'
import { requestConfirm, showToast } from './useConfirmToast'
import { useI18n } from 'vue-i18n'

// SalesTwin 工作台事件处理：盲区扫描、行动建议、待办编辑、预案管理、反馈提交
// 这些 handler 依赖 useSalesTwin 提供的响应式 state，接收 salesTwin composable 对象以保持引用一致
export function useSalesTwinWorkspace(salesTwinState) {
  const { t } = useI18n()
  const {
    selectedProject, activeMenu,
    scanningBlindSpots, blindSpots, winRateData,
    generatingActions, nextActions,
    sortingTasks, taskSortSuggestions, applyingSort,
    tasks, selectedTask, editingTaskInline, taskEditForm,
    expandedRecordId, loadingRecordId,
    meetingPlans, selectedPlan, planEditForm, editingPlan, savingPlan,
    feedbackRecords, feedbackText, feedbackAttachments,
    feedbackRelatedTaskIds, feedbackRelatedPlanId,
    feedbackResult, stakeholders, stateLogs,
  } = salesTwinState

  // ============ 工作台事件处理 ============

  // 盲区扫描
  async function handleScanBlindSpots() {
    if (!selectedProject.value || scanningBlindSpots.value) return
    scanningBlindSpots.value = true
    try {
      const res = await salesTwinApi.scanBlindSpots(selectedProject.value)
      blindSpots.value = res
      // 同时刷新健康度
      try {
        winRateData.value = await salesTwinApi.getWinRate(selectedProject.value)
      } catch (e) { /* 健康度加载失败不影响主流程 */ }
    } catch (e) {
      console.error('扫描盲区失败:', e)
      showToast(t('toast.scanBlindSpotsFailed', { reason: e?.message || e }), 'error')
    } finally {
      scanningBlindSpots.value = false
    }
  }

  // 一键生成行动建议（跳转到 actions 子菜单并自动生成）
  async function handleGoToActions() {
    activeMenu.value = 'actions'
    await handleLoadActions()
  }

  // 生成行动建议
  async function handleLoadActions() {
    if (!selectedProject.value || generatingActions.value) return
    generatingActions.value = true
    try {
      nextActions.value = await salesTwinApi.getNextBestAction(selectedProject.value)
    } catch (e) {
      console.error('生成行动建议失败:', e)
      showToast(t('toast.generateActionsFailed', { reason: e?.message || e }), 'error')
    } finally {
      generatingActions.value = false
    }
  }

  // 采纳行动为待办
  async function handleAdoptAction(action) {
    if (!selectedProject.value) return
    try {
      // 自进化引擎：有 recommendation_id 时走新 API
      if (action.recommendation_id) {
        await salesTwinApi.adoptRecommendation(action.recommendation_id, { adopted: true })
      } else {
        await salesTwinApi.adoptAction(selectedProject.value, {
          title: action.title,
          description: action.description,
          priority: action.priority,
          task_type: action.task_type || 'follow_up',
          stakeholder_id: action.stakeholder_id || null,
          stakeholder_ids: action.stakeholder_ids || [],
          source_action: action,
        })
      }
      // 刷新待办列表
      const tasksRes = await salesTwinApi.getTasks(selectedProject.value)
      tasks.value = tasksRes.tasks || []
      // 标记行动已采纳（前端状态）
      if (nextActions.value?.recommended_actions) {
        nextActions.value.recommended_actions = nextActions.value.recommended_actions.map(a =>
          a === action ? { ...a, adopted: true } : a
        )
      }
    } catch (e) {
      console.error('采纳行动失败:', e)
      showToast(t('toast.adoptActionFailed', { reason: e?.message || e }), 'error')
    }
  }

  // 自进化引擎：拒绝推荐（记录拒绝原因）
  async function handleRejectAction(action, rejectReason) {
    if (!action.recommendation_id) return
    try {
      await salesTwinApi.adoptRecommendation(action.recommendation_id, {
        adopted: false,
        reject_reason: rejectReason
      })
      // 标记行动已拒绝（前端状态）
      if (nextActions.value?.recommended_actions) {
        nextActions.value.recommended_actions = nextActions.value.recommended_actions.map(a =>
          a === action ? { ...a, rejected: true, showReject: false } : a
        )
      }
      showToast(t('toast.rejectReasonRecorded', { reason: rejectReason }), 'info')
    } catch (e) {
      console.error('拒绝推荐失败:', e)
      showToast(t('toast.rejectActionFailed', { reason: e?.message || e }), 'error')
    }
  }

  // 查看已采纳的待办
  function handleViewAdoptedTask(action) {
    const task = tasks.value.find(t =>
      t.source_action && (
        t.source_action.title === action.title ||
        t.title === action.title
      )
    )
    if (task) {
      selectedTask.value = task
      activeMenu.value = 'tasks'
    } else {
      showToast(t('toast.taskNotFound'), 'warning')
    }
  }

  // 智能排序待办
  async function handleAutoSortTasks() {
    if (!selectedProject.value) return
    sortingTasks.value = true
    try {
      const res = await salesTwinApi.autoSortTasks(selectedProject.value)
      taskSortSuggestions.value = res.suggestions || res
    } catch (e) {
      console.error('智能排序失败:', e)
      showToast(t('toast.autoSortFailed', { reason: e?.message || e }), 'error')
    } finally {
      sortingTasks.value = false
    }
  }

  // 应用排序建议
  async function handleApplyTaskSort() {
    if (!selectedProject.value || !taskSortSuggestions.value?.length) return
    applyingSort.value = true
    try {
      await salesTwinApi.applyTaskSort(selectedProject.value, taskSortSuggestions.value)
      // 刷新待办列表
      const tasksRes = await salesTwinApi.getTasks(selectedProject.value)
      tasks.value = tasksRes.tasks || []
      taskSortSuggestions.value = null
    } catch (e) {
      console.error('应用排序失败:', e)
      showToast(t('toast.applySortFailed', { reason: e?.message || e }), 'error')
    } finally {
      applyingSort.value = false
    }
  }

  // 选择待办
  function handleSelectTask(task) {
    selectedTask.value = task
    editingTaskInline.value = false
  }

  // 开始内联编辑待办
  function handleStartInlineEditTask() {
    if (!selectedTask.value) return
    taskEditForm.value = {
      title: selectedTask.value.title || '',
      description: selectedTask.value.description || '',
      priority: selectedTask.value.priority || 'medium',
      task_type: selectedTask.value.task_type || 'follow_up',
      stakeholder_id: selectedTask.value.stakeholder_id || null,
      stakeholder_ids: selectedTask.value.stakeholder_ids || (selectedTask.value.stakeholder_id ? [selectedTask.value.stakeholder_id] : []),
      due_date: selectedTask.value.due_date ? String(selectedTask.value.due_date).slice(0, 10) : '',
    }
    editingTaskInline.value = true
  }

  // 提交内联编辑待办
  async function handleSubmitInlineEditTask() {
    if (!selectedTask.value) return
    try {
      const res = await salesTwinApi.updateTask(selectedTask.value.id, {
        title: taskEditForm.value.title,
        description: taskEditForm.value.description,
        priority: taskEditForm.value.priority,
        task_type: taskEditForm.value.task_type,
        stakeholder_id: taskEditForm.value.stakeholder_id,
        stakeholder_ids: taskEditForm.value.stakeholder_ids,
        due_date: taskEditForm.value.due_date || null,
      })
      // 更新本地数据
      const idx = tasks.value.findIndex(t => t.id === selectedTask.value.id)
      if (idx !== -1) {
        tasks.value[idx] = { ...tasks.value[idx], ...res.task }
        selectedTask.value = tasks.value[idx]
      }
      editingTaskInline.value = false
    } catch (e) {
      console.error('保存待办失败:', e)
      showToast(t('toast.saveTaskFailed', { reason: e?.message || e }), 'error')
    }
  }

  // 删除待办
  async function handleRemoveTask(task) {
    if (!task) return
    const confirmed = await requestConfirm({
      title: t('modal.deleteTaskTitle'),
      message: t('modal.deleteTaskMessage', { name: task.title }),
      confirmText: t('modal.deleteButton'),
      danger: true,
    })
    if (!confirmed) return
    try {
      await salesTwinApi.deleteTask(task.id)
      tasks.value = tasks.value.filter(t => t.id !== task.id)
      if (selectedTask.value?.id === task.id) selectedTask.value = null
      showToast(t('toast.taskDeleted'), 'success')
    } catch (e) {
      console.error('删除待办失败:', e)
      showToast(t('toast.deleteTaskFailed', { reason: e?.message || e }), 'error')
    }
  }

  // 修改待办状态
  async function handleChangeTaskStatus(task, newStatus) {
    if (!task) return
    try {
      const res = await salesTwinApi.updateTask(task.id, { status: newStatus })
      const idx = tasks.value.findIndex(t => t.id === task.id)
      if (idx !== -1) {
        tasks.value[idx] = { ...tasks.value[idx], ...res.task }
        if (selectedTask.value?.id === task.id) selectedTask.value = tasks.value[idx]
      }
    } catch (e) {
      console.error('更新状态失败:', e)
      showToast(t('toast.updateStatusFailed', { reason: e?.message || e }), 'error')
    }
  }

  // 在拜访记录中查看反馈详情
  function handleViewFeedbackInVisit(record) {
    activeMenu.value = 'visit'
    expandedRecordId.value = record.id
    // 滚动到对应记录
    setTimeout(() => {
      const el = document.querySelector(`[data-record-id="${record.id}"]`)
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }, 100)
  }

  // 查看预案详情
  function handleViewPlan(plan) {
    selectedPlan.value = plan
    editingPlan.value = false
  }

  // 编辑预案
  function handleOpenEditPlan(plan) {
    if (!plan) return
    selectedPlan.value = plan
    planEditForm.value = {
      name: plan.name || '',
      meeting_purpose: plan.meeting_purpose || '',
      meeting_type: plan.meeting_type || 'first_visit',
      stakeholder_id: plan.stakeholder_id || null,
      stakeholder_ids: plan.stakeholder_ids || (plan.stakeholder_id ? [plan.stakeholder_id] : []),
      related_task_ids: plan.related_task_ids || [],
    }
    editingPlan.value = true
  }

  // 提交预案编辑
  async function handleSubmitPlanEdit() {
    if (!selectedPlan.value) return
    savingPlan.value = true
    try {
      const res = await salesTwinApi.updateMeetingPlan(selectedPlan.value.id, {
        name: planEditForm.value.name,
        meeting_purpose: planEditForm.value.meeting_purpose,
        meeting_type: planEditForm.value.meeting_type,
        stakeholder_id: planEditForm.value.stakeholder_id,
        stakeholder_ids: planEditForm.value.stakeholder_ids,
        related_task_ids: planEditForm.value.related_task_ids,
      })
      // 更新本地数据
      const idx = meetingPlans.value.findIndex(p => p.id === selectedPlan.value.id)
      if (idx !== -1) {
        meetingPlans.value[idx] = { ...meetingPlans.value[idx], ...res.plan }
        selectedPlan.value = meetingPlans.value[idx]
      }
      editingPlan.value = false
    } catch (e) {
      console.error('保存预案失败:', e)
      showToast(t('toast.savePlanFailed', { reason: e?.message || e }), 'error')
    } finally {
      savingPlan.value = false
    }
  }

  // 删除预案
  async function handleRemovePlan(plan) {
    if (!plan) return
    const confirmed = await requestConfirm({
      title: t('modal.deletePlanTitle'),
      message: t('modal.deletePlanMessage', { name: plan.name }),
      confirmText: t('modal.deleteButton'),
      danger: true,
    })
    if (!confirmed) return
    try {
      await salesTwinApi.deleteMeetingPlan(plan.id)
      meetingPlans.value = meetingPlans.value.filter(p => p.id !== plan.id)
      if (selectedPlan.value?.id === plan.id) selectedPlan.value = null
      showToast(t('toast.planDeleted'), 'success')
    } catch (e) {
      console.error('删除预案失败:', e)
      showToast(t('toast.deletePlanFailed', { reason: e?.message || e }), 'error')
    }
  }

  // 选择反馈附件
  function handleFeedbackFileSelect(e) {
    const files = Array.from(e.target.files || [])
    feedbackAttachments.value = [...feedbackAttachments.value, ...files]
  }

  // 移除附件
  function handleRemoveAttachment(index) {
    feedbackAttachments.value = feedbackAttachments.value.filter((_, i) => i !== index)
  }

  // 提交反馈（拜访记录）
  async function handleSubmitFeedback() {
    if (!selectedProject.value) return
    if (!feedbackText.value || !feedbackText.value.trim()) return
    try {
      const res = await salesTwinApi.submitFeedback(
        selectedProject.value,
        feedbackText.value,
        feedbackRelatedTaskIds.value,
        feedbackRelatedPlanId.value,
        feedbackAttachments.value
      )
      feedbackResult.value = res
      // 清空输入
      feedbackText.value = ''
      feedbackAttachments.value = []
      feedbackRelatedTaskIds.value = []
      feedbackRelatedPlanId.value = null
      // 刷新反馈记录列表
      const recordsRes = await salesTwinApi.getFeedbackRecords(selectedProject.value)
      feedbackRecords.value = recordsRes.records || []
      // 刷新待办（反馈可能更新了待办状态）
      const tasksRes = await salesTwinApi.getTasks(selectedProject.value)
      tasks.value = tasksRes.tasks || []
      // 刷新干系人（反馈可能更新了干系人态度）
      const stakeholdersRes = await salesTwinApi.getStakeholders(selectedProject.value)
      stakeholders.value = stakeholdersRes.stakeholders || []
      // 刷新状态日志
      try {
        const logsRes = await salesTwinApi.getStateLogs(selectedProject.value)
        stateLogs.value = logsRes.logs || []
      } catch (e) { /* 日志加载失败不影响主流程 */ }
      showToast(t('toast.feedbackSuccess', { summary: res.summary || `${res.total_changes || 0}` }), 'success')
    } catch (e) {
      console.error('提交反馈失败:', e)
      showToast(t('toast.submitFeedbackFailed', { reason: e?.message || e }), 'error')
    }
  }

  // 展开/收起记录
  async function handleToggleRecordExpand(record) {
    if (expandedRecordId.value === record.id) {
      expandedRecordId.value = null
      return
    }
    expandedRecordId.value = record.id
    // 如果记录还没有完整内容，加载详情
    if (record.feedback_text === undefined) {
      loadingRecordId.value = record.id
      try {
        const full = await salesTwinApi.getFeedbackRecord(record.id)
        const idx = feedbackRecords.value.findIndex(r => r.id === record.id)
        if (idx !== -1) {
          feedbackRecords.value[idx] = { ...feedbackRecords.value[idx], ...full.record }
        }
      } catch (e) {
        console.error('加载记录详情失败:', e)
      } finally {
        loadingRecordId.value = null
      }
    }
  }

  return {
    handleScanBlindSpots,
    handleGoToActions,
    handleLoadActions,
    handleAdoptAction,
    handleRejectAction,
    handleViewAdoptedTask,
    handleAutoSortTasks,
    handleApplyTaskSort,
    handleSelectTask,
    handleStartInlineEditTask,
    handleSubmitInlineEditTask,
    handleRemoveTask,
    handleChangeTaskStatus,
    handleViewFeedbackInVisit,
    handleViewPlan,
    handleOpenEditPlan,
    handleSubmitPlanEdit,
    handleRemovePlan,
    handleFeedbackFileSelect,
    handleRemoveAttachment,
    handleSubmitFeedback,
    handleToggleRecordExpand,
  }
}

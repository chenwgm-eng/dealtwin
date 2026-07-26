import request from './index'

export function getProjects() {
  return request({
    url: '/api/sales-twin/projects',
    method: 'get'
  })
}

export function getProject(projectId) {
  return request({
    url: `/api/sales-twin/projects/${projectId}`,
    method: 'get'
  })
}

export function createProject(data) {
  return request({
    url: '/api/sales-twin/projects',
    method: 'post',
    data
  })
}

export function updateProject(projectId, data) {
  return request({
    url: `/api/sales-twin/projects/${projectId}`,
    method: 'put',
    data
  })
}

export function deleteProject(projectId) {
  return request({
    url: `/api/sales-twin/projects/${projectId}`,
    method: 'delete'
  })
}

export function getStakeholders(projectId) {
  return request({
    url: `/api/sales-twin/projects/${projectId}/stakeholders`,
    method: 'get'
  })
}

export function getProjectStakeholderContacts(projectId) {
  return request({
    url: `/api/sales-twin/projects/${projectId}/stakeholders/contacts`,
    method: 'get'
  })
}

export function createStakeholder(projectId, data) {
  return request({
    url: `/api/sales-twin/projects/${projectId}/stakeholders`,
    method: 'post',
    data
  })
}

export function updateStakeholder(stakeholderId, data) {
  return request({
    url: `/api/sales-twin/stakeholders/${stakeholderId}`,
    method: 'put',
    data
  })
}

export function deleteStakeholder(stakeholderId) {
  return request({
    url: `/api/sales-twin/stakeholders/${stakeholderId}`,
    method: 'delete'
  })
}

export function mergeStakeholders(projectId, primaryId, secondaryId, override = {}) {
  return request({
    url: `/api/sales-twin/projects/${projectId}/stakeholders/merge`,
    method: 'post',
    data: { primary_id: primaryId, secondary_id: secondaryId, override }
  })
}

export function getRelationships(projectId) {
  return request({
    url: `/api/sales-twin/projects/${projectId}/relationships`,
    method: 'get'
  })
}

export function createRelationship(projectId, data) {
  return request({
    url: `/api/sales-twin/projects/${projectId}/relationships`,
    method: 'post',
    data
  })
}

export function updateRelationship(projectId, relationshipId, data) {
  return request({
    url: `/api/sales-twin/projects/${projectId}/relationships/${relationshipId}`,
    method: 'put',
    data
  })
}

export function deleteRelationship(projectId, relationshipId) {
  return request({
    url: `/api/sales-twin/projects/${projectId}/relationships/${relationshipId}`,
    method: 'delete'
  })
}

export function scanBlindSpots(projectId) {
  return request({
    url: `/api/sales-twin/projects/${projectId}/scan`,
    method: 'post'
  })
}

export function getNextBestAction(projectId) {
  return request({
    url: `/api/sales-twin/projects/${projectId}/next-best-action`,
    method: 'post'
  })
}

export function getActionBrief(projectId, stakeholderId) {
  return request({
    url: `/api/sales-twin/projects/${projectId}/action-brief/${stakeholderId}`,
    method: 'post'
  })
}

export function submitFeedback(projectId, feedback, relatedTaskIds = [], relatedMeetingPlanId = null, files = []) {
  // 有附件时使用 multipart/form-data，附件作为LLM解析输入之一
  if (files && files.length > 0) {
    const formData = new FormData()
    formData.append('feedback', feedback)
    formData.append('related_task_ids', JSON.stringify(relatedTaskIds || []))
    if (relatedMeetingPlanId) {
      formData.append('related_meeting_plan_id', relatedMeetingPlanId)
    }
    files.forEach(f => formData.append('files', f))
    return request({
      url: `/api/sales-twin/projects/${projectId}/feedback`,
      method: 'post',
      data: formData,
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  }
  // 无附件：JSON模式
  return request({
    url: `/api/sales-twin/projects/${projectId}/feedback`,
    method: 'post',
    data: {
      feedback,
      related_task_ids: relatedTaskIds,
      related_meeting_plan_id: relatedMeetingPlanId
    }
  })
}

export function getStateLogs(projectId, limit = 50) {
  return request({
    url: `/api/sales-twin/projects/${projectId}/state-logs`,
    method: 'get',
    params: { limit }
  })
}

export function getWinRate(projectId) {
  return request({
    url: `/api/sales-twin/projects/${projectId}/win-rate`,
    method: 'get'
  })
}

export function simulateFermentation(projectId, rounds = 3, initialEvents = [], extras = {}) {
  return request({
    url: `/api/sales-twin/projects/${projectId}/fermentation`,
    method: 'post',
    data: {
      rounds,
      mode: extras.mode || 'narrative',
      initial_events: initialEvents,
      related_task_ids: extras.related_task_ids || [],
      related_feedback_ids: extras.related_feedback_ids || [],
      related_materials: extras.related_materials || []
    }
  })
}

export function interviewStakeholder(projectId, stakeholderId, question, simulationContext = null) {
  return request({
    url: `/api/sales-twin/projects/${projectId}/fermentation/interview`,
    method: 'post',
    data: {
      stakeholder_id: stakeholderId,
      question,
      simulation_context: simulationContext
    }
  })
}

// 基于发酵推演结果生成结构化推演报告
export function generateFermentationReport(projectId, fermentationResult) {
  return request({
    url: `/api/sales-twin/projects/${projectId}/fermentation/report`,
    method: 'post',
    data: { fermentation_result: fermentationResult }
  })
}

// ============ 待办事项（项目计划）API ============

export function getTasks(projectId, status = null) {
  const url = status
    ? `/api/sales-twin/projects/${projectId}/tasks?status=${status}`
    : `/api/sales-twin/projects/${projectId}/tasks`
  return request({ url, method: 'get' })
}

export function createTask(projectId, data) {
  return request({
    url: `/api/sales-twin/projects/${projectId}/tasks`,
    method: 'post',
    data
  })
}

export function adoptAction(projectId, actionData) {
  return request({
    url: `/api/sales-twin/projects/${projectId}/tasks/adopt-action`,
    method: 'post',
    data: actionData
  })
}

export function autoSortTasks(projectId) {
  return request({
    url: `/api/sales-twin/projects/${projectId}/tasks/auto-sort`,
    method: 'post'
  })
}

export function applyTaskSort(projectId, suggestions) {
  return request({
    url: `/api/sales-twin/projects/${projectId}/tasks/apply-sort`,
    method: 'post',
    data: { suggestions }
  })
}

export function updateTask(taskId, data) {
  return request({
    url: `/api/sales-twin/tasks/${taskId}`,
    method: 'put',
    data
  })
}

export function deleteTask(taskId) {
  return request({
    url: `/api/sales-twin/tasks/${taskId}`,
    method: 'delete'
  })
}

// ============ 拜访预案 API ============

export function getMeetingPlans(projectId) {
  return request({
    url: `/api/sales-twin/projects/${projectId}/meeting-plans`,
    method: 'get'
  })
}

export function createMeetingPlan(projectId, data) {
  return request({
    url: `/api/sales-twin/projects/${projectId}/meeting-plans`,
    method: 'post',
    data
  })
}

export function getMeetingPlan(planId) {
  return request({
    url: `/api/sales-twin/meeting-plans/${planId}`,
    method: 'get'
  })
}

export function updateMeetingPlan(planId, data) {
  return request({
    url: `/api/sales-twin/meeting-plans/${planId}`,
    method: 'put',
    data
  })
}

export function deleteMeetingPlan(planId) {
  return request({
    url: `/api/sales-twin/meeting-plans/${planId}`,
    method: 'delete'
  })
}

// ============ 反馈记录 API ============

export function getFeedbackRecords(projectId) {
  return request({
    url: `/api/sales-twin/projects/${projectId}/feedback-records`,
    method: 'get'
  })
}

export function getFeedbackRecord(recordId) {
  return request({
    url: `/api/sales-twin/feedback-records/${recordId}`,
    method: 'get'
  })
}

// 上传拜访记录附件
export function uploadFeedbackAttachments(recordId, fileList) {
  const formData = new FormData()
  fileList.forEach(f => formData.append('files', f))
  return request({
    url: `/api/sales-twin/feedback-records/${recordId}/attachments`,
    method: 'post',
    data: formData,
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

// 删除拜访记录附件
export function deleteFeedbackAttachment(recordId, filename) {
  return request({
    url: `/api/sales-twin/feedback-records/${recordId}/attachments/${encodeURIComponent(filename)}`,
    method: 'delete'
  })
}

// 拜访记录附件下载URL（用于 <a> 标签下载）
export function feedbackAttachmentUrl(recordId, filename) {
  return `/api/sales-twin/feedback-records/${recordId}/attachments/${encodeURIComponent(filename)}`
}

// 加载项目图谱数据（节点边全部来自数据库注入）
export function getProjectGraph(projectId) {
  return request({
    url: `/api/sales-twin/projects/${projectId}/graph`,
    method: 'get'
  })
}

// 网络调研目标公司背景信息（用于补充图谱构建上下文）
export function researchCompany(projectId, extraKeywords = '') {
  return request({
    url: `/api/sales-twin/projects/${projectId}/research`,
    method: 'post',
    data: { extra_keywords: extraKeywords }
  })
}

// 基于SWOT生成竞争分析
export function generateCompetitiveAnalysis(projectId, documentTexts = []) {
  return request({
    url: `/api/sales-twin/projects/${projectId}/competitive-analysis`,
    method: 'post',
    data: { document_texts: documentTexts }
  })
}

// AI排版优化已有文本（不改变实质内容）
export function reformatText(projectId, field) {
  return request({
    url: `/api/sales-twin/projects/${projectId}/reformat-text`,
    method: 'post',
    data: { field }
  })
}

// ============ 建议池 API ============

export function getSuggestions(projectId) {
  return request({
    url: `/api/sales-twin/projects/${projectId}/suggestions`,
    method: 'get'
  })
}

export function addSuggestion(projectId, data) {
  return request({
    url: `/api/sales-twin/projects/${projectId}/suggestions`,
    method: 'post',
    data
  })
}

export function updateSuggestion(suggestionId, data) {
  return request({
    url: `/api/sales-twin/suggestions/${suggestionId}`,
    method: 'put',
    data
  })
}

export function deleteSuggestion(suggestionId) {
  return request({
    url: `/api/sales-twin/suggestions/${suggestionId}`,
    method: 'delete'
  })
}

export function generateTasksFromSuggestions(projectId, data = {}) {
  return request({
    url: `/api/sales-twin/projects/${projectId}/suggestions/generate-tasks`,
    method: 'post',
    data
  })
}

// ============ 客户管理 API ============

// 客户列表（?tree=1返回树形，?parent_id=N返回子客户）
export function getCustomers(params = {}) {
  return request({
    url: '/api/sales-twin/customers',
    method: 'get',
    params
  })
}

// 所有客户扁平列表（供选择器使用）
export function getAllCustomersFlat() {
  return request({
    url: '/api/sales-twin/customers/all',
    method: 'get'
  })
}

// 新建客户
export function createCustomer(data) {
  return request({
    url: '/api/sales-twin/customers',
    method: 'post',
    data
  })
}

// 客户详情（含联系人/项目/子公司）
export function getCustomer(customerId) {
  return request({
    url: `/api/sales-twin/customers/${customerId}`,
    method: 'get'
  })
}

// 更新客户档案
export function updateCustomer(customerId, data) {
  return request({
    url: `/api/sales-twin/customers/${customerId}`,
    method: 'put',
    data
  })
}

// 删除客户
export function deleteCustomer(customerId) {
  return request({
    url: `/api/sales-twin/customers/${customerId}`,
    method: 'delete'
  })
}

// LLM工具调用检索工商信息
export function fetchCustomerBusinessInfo(customerId) {
  return request({
    url: `/api/sales-twin/customers/${customerId}/fetch-business-info`,
    method: 'post'
  })
}

// 生成客户概览（客户档案模块）
export function generateCustomerProfileOverview(customerId) {
  return request({
    url: `/api/sales-twin/customers/${customerId}/generate-overview`,
    method: 'post'
  })
}

// 合并客户
export function mergeCustomers(sourceId, targetId) {
  return request({
    url: '/api/sales-twin/customers/merge',
    method: 'post',
    data: { source_id: sourceId, target_id: targetId }
  })
}

// ============ 联系人 CRUD ============

export function getContacts(customerId) {
  return request({
    url: `/api/sales-twin/customers/${customerId}/contacts`,
    method: 'get'
  })
}

export function createContact(customerId, data) {
  return request({
    url: `/api/sales-twin/customers/${customerId}/contacts`,
    method: 'post',
    data
  })
}

export function updateContact(contactId, data) {
  return request({
    url: `/api/sales-twin/customers/contacts/${contactId}`,
    method: 'put',
    data
  })
}

export function deleteContact(contactId) {
  return request({
    url: `/api/sales-twin/customers/contacts/${contactId}`,
    method: 'delete'
  })
}

// 获取联系人详情（含互动触达状态 + 参与的商机列表）
export function getContactDetail(contactId) {
  return request({
    url: `/api/sales-twin/customers/contacts/${contactId}`,
    method: 'get'
  })
}

// ============ 客户组织架构图谱 ============

export function getOrgGraph(customerId) {
  return request({
    url: `/api/sales-twin/customers/${customerId}/org-graph`,
    method: 'get'
  })
}

export function updateContactReportsTo(contactId, reportsToId) {
  return request({
    url: `/api/sales-twin/customers/contacts/${contactId}/reports-to`,
    method: 'put',
    data: { reports_to_id: reportsToId }
  })
}

export function updateContactInteractionStatus(contactId, status) {
  return request({
    url: `/api/sales-twin/customers/contacts/${contactId}/interaction-status`,
    method: 'put',
    data: { status }
  })
}

export function searchContactsWeb(customerId) {
  return request({
    url: `/api/sales-twin/customers/${customerId}/contacts/search-web`,
    method: 'post'
  })
}

export function batchCreateContacts(customerId, contacts) {
  return request({
    url: `/api/sales-twin/customers/${customerId}/contacts/batch`,
    method: 'post',
    data: { contacts }
  })
}

// ============ 阶段交付物追踪 API ============

// 获取项目阶段交付物清单（含完成状态和完成率）
// @param stage 可选，不传时使用项目当前 sales_stage
export function getStageDeliverables(projectId, stage = null) {
  const params = stage ? { stage } : {}
  return request({
    url: `/api/sales-twin/projects/${projectId}/stage-deliverables`,
    method: 'get',
    params
  })
}

// 更新交付物状态（勾选/取消勾选/修改备注）
// @param deliverableKey 形如 'account_plan.company_structure'
// @param stage 可选，不传时使用项目当前 sales_stage
export function updateStageDeliverable(projectId, deliverableKey, stage, { is_completed, notes }) {
  const params = stage ? { stage } : {}
  return request({
    url: `/api/sales-twin/projects/${projectId}/stage-deliverables/${deliverableKey}`,
    method: 'put',
    params,
    data: { is_completed, notes }
  })
}

// 上传阶段交付物附件（技术方案、商务方案等系统无对应上下文的材料）
// @param deliverableKey 形如 'solution_doc.technical_solution'
// @param stage 可选，不传时使用项目当前 sales_stage
// @param fileList File 数组
export function uploadStageDeliverableAttachments(projectId, deliverableKey, stage, fileList) {
  const formData = new FormData()
  fileList.forEach(f => formData.append('files', f))
  const params = stage ? { stage } : {}
  return request({
    url: `/api/sales-twin/projects/${projectId}/stage-deliverables/${deliverableKey}/attachments`,
    method: 'post',
    params,
    data: formData,
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

// 删除阶段交付物附件
export function deleteStageDeliverableAttachment(projectId, deliverableKey, stage, filename) {
  const params = stage ? { stage } : {}
  return request({
    url: `/api/sales-twin/projects/${projectId}/stage-deliverables/${deliverableKey}/attachments/${encodeURIComponent(filename)}`,
    method: 'delete',
    params
  })
}

// 阶段交付物附件下载 URL（用于 <a> 标签下载）
export function stageDeliverableAttachmentUrl(projectId, deliverableKey, stage, filename) {
  const base = `/api/sales-twin/projects/${projectId}/stage-deliverables/${deliverableKey}/attachments/${encodeURIComponent(filename)}`
  return stage ? `${base}?stage=${encodeURIComponent(stage)}` : base
}

// 执行阶段检查，返回检查报告（含完成度、未完成项、退出条件检查、推进建议）
export function checkStageReadiness(projectId) {
  return request({
    url: `/api/sales-twin/projects/${projectId}/stage-check`,
    method: 'post'
  })
}

// ============ 商机历程时间线 API ============

export function getStageTimeline(projectId) {
  return request({
    url: `/api/sales-twin/projects/${projectId}/stage-timeline`,
    method: 'get'
  })
}

// ============ Dashboard 聚合数据 API ============

/**
 * 获取 Dashboard 聚合数据
 * @param {Object} params - { period?: string, start?: string, end?: string }
 * @returns {Promise<Object>} dashboard 数据
 */
export function getDashboard(params = {}) {
  return request({
    url: '/api/sales-twin/dashboard',
    method: 'get',
    params
  })
}

/**
 * 刷新 Dashboard 智能洞察（清缓存并触发重新生成）
 * @param {Object} params - { period?: string, start?: string, end?: string }
 * @returns {Promise<Object>}
 */
export function refreshDashboardInsights(params = {}) {
  return request({
    url: '/api/sales-twin/dashboard/insights/refresh',
    method: 'post',
    data: params
  })
}

// ============ 3-3-3 战略项 API ============

// 获取项目下的战略项列表
export function getStrategyItems(projectId) {
  return request({
    url: `/api/sales-twin/projects/${projectId}/strategy-items`,
    method: 'get'
  })
}

// 新建战略项
export function createStrategyItem(projectId, data) {
  return request({
    url: `/api/sales-twin/projects/${projectId}/strategy-items`,
    method: 'post',
    data
  })
}

// 更新指定战略项
export function updateStrategyItem(projectId, itemId, data) {
  return request({
    url: `/api/sales-twin/projects/${projectId}/strategy-items/${itemId}`,
    method: 'put',
    data
  })
}

// 删除指定战略项
export function deleteStrategyItem(projectId, itemId) {
  return request({
    url: `/api/sales-twin/projects/${projectId}/strategy-items/${itemId}`,
    method: 'delete'
  })
}

// AI 生成战略项
export function aiGenerateStrategyItems(projectId) {
  return request({
    url: `/api/sales-twin/projects/${projectId}/strategy-items/ai-generate`,
    method: 'post'
  })
}

// ============ 三个WHY 上下文 API ============

// 获取项目下的三个WHY上下文列表
export function getWhyContexts(projectId) {
  return request({
    url: `/api/sales-twin/projects/${projectId}/why-contexts`,
    method: 'get'
  })
}

// 新建（或 upsert）WHY 上下文
export function upsertWhyContext(projectId, data) {
  return request({
    url: `/api/sales-twin/projects/${projectId}/why-contexts`,
    method: 'post',
    data
  })
}

// 删除指定 WHY 上下文
export function deleteWhyContext(projectId, contextId) {
  return request({
    url: `/api/sales-twin/projects/${projectId}/why-contexts/${contextId}`,
    method: 'delete'
  })
}

// AI 生成三个WHY上下文
export function aiGenerateWhyContexts(projectId) {
  return request({
    url: `/api/sales-twin/projects/${projectId}/why-contexts/ai-generate`,
    method: 'post'
  })
}

// ============ 设置 API ============

// 获取全局设置（公司信息 / LLM 配置 / 产品资料附件）
export function getSettings() {
  return request({
    url: '/api/sales-twin/settings',
    method: 'get'
  })
}

// 更新全局设置（公司信息 + LLM 配置）
export function updateSettings(data) {
  return request({
    url: '/api/sales-twin/settings',
    method: 'put',
    data
  })
}

// 上传产品资料附件（multipart/form-data，字段名 file）
export function uploadCompanyAttachment(file) {
  const formData = new FormData()
  formData.append('file', file)
  return request({
    url: '/api/sales-twin/settings/attachments',
    method: 'post',
    data: formData,
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

// 删除产品资料附件
export function deleteCompanyAttachment(id) {
  return request({
    url: `/api/sales-twin/settings/attachments/${id}`,
    method: 'delete'
  })
}

// 产品资料附件下载 URL（用于 window.open 下载）
export function getCompanyAttachmentDownloadUrl(id) {
  return `/api/sales-twin/settings/attachments/${id}/download`
}

// ==================== 自进化引擎 ====================

export function adoptRecommendation(recId, data) {
  return request({
    url: `/api/sales-twin/recommendations/${recId}/adopt`,
    method: 'post',
    data
  })
}

export function getLearningPatterns(status) {
  const params = status ? `?status=${status}` : ''
  return request({
    url: `/api/sales-twin/learning/patterns${params}`,
    method: 'get'
  })
}

export function approvePattern(patternId) {
  return request({
    url: `/api/sales-twin/learning/patterns/${patternId}/approve`,
    method: 'post'
  })
}

export function deprecatePattern(patternId) {
  return request({
    url: `/api/sales-twin/learning/patterns/${patternId}/deprecate`,
    method: 'post'
  })
}

// ============= Agent 定时任务管理 =============
export function getAgentJobs() {
  return request({
    url: '/api/sales-twin/agent/jobs',
    method: 'get'
  })
}

export function pauseAgentJob(jobId) {
  return request({
    url: `/api/sales-twin/agent/jobs/${jobId}/pause`,
    method: 'post'
  })
}

export function resumeAgentJob(jobId) {
  return request({
    url: `/api/sales-twin/agent/jobs/${jobId}/resume`,
    method: 'post'
  })
}

export function runAgentJobNow(jobId) {
  return request({
    url: `/api/sales-twin/agent/jobs/${jobId}/run`,
    method: 'post'
  })
}

export function updateAgentJobSchedule(jobId, scheduleData) {
  return request({
    url: `/api/sales-twin/agent/jobs/${jobId}/schedule`,
    method: 'put',
    data: scheduleData
  })
}

// ============= Agent 任务运行历史 =============
export function getAgentJobRuns(jobId, limit = 10) {
  return request({
    url: `/api/sales-twin/agent/jobs/${jobId}/runs`,
    method: 'get',
    params: { limit }
  })
}

// ============= 盲区扫描报告持久化 =============
export function getBlindSpotReports(projectId, limit = 10) {
  return request({
    url: `/api/sales-twin/projects/${projectId}/blind-spot-reports`,
    method: 'get',
    params: { limit }
  })
}

export function getLatestBlindSpotReport(projectId) {
  return request({
    url: `/api/sales-twin/projects/${projectId}/blind-spot-latest`,
    method: 'get'
  })
}

// ============= 客户情报历史快照 =============
export function getCustomerIntelSnapshots(customerId, limit = 10) {
  return request({
    url: `/api/sales-twin/customers/${customerId}/intel-snapshots`,
    method: 'get',
    params: { limit }
  })
}

// ============ 商机里程碑（OM10-OM70）API ============

// 获取项目里程碑决策列表（固定 5 条，未决策为 pending 占位）
export function getMilestones(projectId) {
  return request({
    url: `/api/sales-twin/projects/${projectId}/milestones`,
    method: 'get'
  })
}

// 更新指定里程碑的评估与决策
export function updateMilestone(projectId, milestone, data) {
  return request({
    url: `/api/sales-twin/projects/${projectId}/milestones/${milestone}`,
    method: 'put',
    data
  })
}

// 更新项目销售模式（inside_sales / prescriptive_pursuit / value_solution_selling / null）
export function updateSalesMode(projectId, salesMode) {
  return request({
    url: `/api/sales-twin/projects/${projectId}/sales-mode`,
    method: 'put',
    data: { sales_mode: salesMode }
  })
}

// ============ Challenger 商业指导话术 API ============

// 生成商业指导话术（同步 LLM 生成，可能 10-30 秒）
export function generateChallengerTeaching(projectId, { stakeholderId = null, name = '' } = {}) {
  return request({
    url: `/api/sales-twin/projects/${projectId}/challenger-teachings`,
    method: 'post',
    data: { stakeholder_id: stakeholderId, name }
  })
}

// 获取项目商业指导话术列表
export function getChallengerTeachings(projectId) {
  return request({
    url: `/api/sales-twin/projects/${projectId}/challenger-teachings`,
    method: 'get'
  })
}

// 获取单条商业指导话术
export function getChallengerTeaching(teachingId) {
  return request({
    url: `/api/sales-twin/challenger-teachings/${teachingId}`,
    method: 'get'
  })
}

// 更新商业指导话术（名称 / 内容）
export function updateChallengerTeaching(teachingId, data) {
  return request({
    url: `/api/sales-twin/challenger-teachings/${teachingId}`,
    method: 'put',
    data
  })
}

// 删除商业指导话术
export function deleteChallengerTeaching(teachingId) {
  return request({
    url: `/api/sales-twin/challenger-teachings/${teachingId}`,
    method: 'delete'
  })
}

// 获取 Challenger 检查清单（5 项）
export function getChallengerChecklist(projectId) {
  return request({
    url: `/api/sales-twin/projects/${projectId}/challenger-checklist`,
    method: 'get'
  })
}

// ============ 关闭复盘 API ============

// 提交赢单/丢单复盘（仅 closed_won/closed_lost 时可用）
export function submitCloseReview(projectId, data) {
  return request({
    url: `/api/sales-twin/projects/${projectId}/close-review`,
    method: 'put',
    data
  })
}



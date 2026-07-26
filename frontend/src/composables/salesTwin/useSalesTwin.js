import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import * as salesTwinApi from '../../api/salesTwin'
import { SALES_STAGES, ACTIVE_STAGES } from '../../constants/salesStages'
import { formatStructuredText, formatDate, formatDateTime, formatCurrency, truncateText, formatFileSize } from './formatters'
import { showToast } from './useConfirmToast'

export function useSalesTwin() {
  const { t } = useI18n()
  // ============ 项目状态 ============
  const projects = ref([])
  const allCustomers = ref([])
  const selectedProject = ref(null)
  const activeMenu = ref('dashboard')
  const showCreateModal = ref(false)
  const showStakeholderModal = ref(false)
  const stakeholderModalMode = ref('add')


  // ============ 数据状态 ============
  const stakeholders = ref([])
  const relationships = ref([])
  const blindSpots = ref(null)
  const sortedFindings = computed(() => {
    if (!blindSpots.value?.findings) return []
    const severityOrder = { critical: 0, high: 1, medium: 2, low: 3, positive: 4 }
    return [...blindSpots.value.findings].sort((a, b) =>
      (severityOrder[a.severity] ?? 5) - (severityOrder[b.severity] ?? 5)
    )
  })
  const nextActions = ref(null)
  const winRateData = ref(null)
  const showWinRatePanel = ref(false)
  const feedbackText = ref('')
  const feedbackResult = ref(null)
  const stateLogs = ref(null)
  const fermentationResult = ref(null)
  const chartSvg = ref(null)
  const interviewTargetId = ref(null)
  const interviewQuestion = ref('')
  const interviewResult = ref(null)
  const interviewing = ref(false)
  const interviewHistory = ref([])
  const presetQuestions = computed(() => [
    t('simulation.presetQuestions.q1'),
    t('simulation.presetQuestions.q2'),
    t('simulation.presetQuestions.q3'),
    t('simulation.presetQuestions.q4'),
  ])
  const showReportView = ref(false)
  const showInterviewView = ref(false)
  const showSuggestionPool = ref(false)
  const fermentationReport = ref(null)
  const generatingOverview = ref(false)
  const generatingValueProp = ref(false)
  const generatingCompetitive = ref(false)
  const generatingPainPoints = ref(false)
  const reformattingField = ref(null)
  const tasks = ref([])
  const taskFilter = ref('pending')
  const editingTask = ref(null)
  const showTaskModal = ref(false)
  const newTask = ref({ title: '', description: '', priority: 'medium', stakeholder_id: null, stakeholder_ids: [], task_type: 'follow_up', due_date: '' })
  const selectedTask = ref(null)
  const editingTaskInline = ref(false)
  const taskEditForm = ref({ title: '', description: '', priority: 'medium', stakeholder_id: null, stakeholder_ids: [], task_type: 'follow_up', due_date: '' })
  const sortingTasks = ref(false)
  const taskSortSuggestions = ref(null)
  const applyingSort = ref(false)
  // 工作台操作状态：盲区扫描、生成建议、自动排序
  const scanningBlindSpots = ref(false)
  const generatingActions = ref(false)
  const meetingPlans = ref([])
  const showPlanModal = ref(false)
  const newPlan = ref({ stakeholder_id: null, stakeholder_ids: [], meeting_purpose: '', meeting_type: 'first_visit', related_task_ids: [], name: '' })
  const selectedPlan = ref(null)
  const generatingPlan = ref(false)
  const planFilter = ref('active')
  const actionFilter = ref('pending')
  const editingPlan = ref(false)
  const planEditForm = ref({ name: '', meeting_purpose: '', meeting_type: 'first_visit', stakeholder_id: null, stakeholder_ids: [], related_task_ids: [] })
  const savingPlan = ref(false)
  const expandedRecordId = ref(null)
  const expandedRecordText = ref('')
  const loadingRecordId = ref(null)
  const showAllFeedbackRecords = ref(false)
  const feedbackRelatedTaskIds = ref([])
  const feedbackRelatedPlanId = ref(null)
  const feedbackRecords = ref([])
  const displayedFeedbackRecords = computed(() => {
    return showAllFeedbackRecords.value
      ? feedbackRecords.value
      : feedbackRecords.value.slice(0, 5)
  })
  const feedbackAttachments = ref([])
  const feedbackFileInput = ref(null)
  const fermentationInput = ref({ related_task_ids: [], related_feedback_ids: [], related_materials: [], initial_events: [] })
  const editingStakeholder = ref(null)
  const showStakeholderEditModal = ref(false)
  const stakeholderEditForm = ref({})
  const stakeholderEditReason = ref('')
  const showProjectEditModal = ref(false)
  const projectEditForm = ref({})
  const projectEditReason = ref('')
  const savingProject = ref(false)
  const inlineEditField = ref(null)
  const inlineEditValue = ref('')
  const inlineEditSaving = ref(false)
  const mergeMode = ref(false)
  const mergePrimary = ref(null)
  const selectedStakeholderId = ref(null)

  // ============ 阶段交付物追踪 ============
  const stageDeliverables = ref(null)       // 阶段交付物数据
  const stageDeliverablesLoading = ref(false)
  const stageCheckResult = ref(null)        // 阶段检查报告
  const showStageCheckModal = ref(false)

  // ============ 商机历程时间线 ============
  const stageTimeline = ref(null)           // 项目阶段时间线数据
  const stageTimelineLoading = ref(false)

  // ============ 图谱状态 ============
  const graphData = ref(null)
  const graphLoading = ref(false)
  const graphSidebar = ref(false)
  const runningSim = ref(false)

  // ============ 关闭复盘（关单时弹出） ============
  // { projectId, result: 'closed_won' | 'closed_lost' } | null
  const pendingCloseReview = ref(null)

  // v-focus 指令
  const vFocus = { mounted: (el) => el.focus() }

  // ============ Computed ============
  const currentProject = computed(() => selectedProject.value ? projects.value.find(p => p.id === selectedProject.value) : null)
  const stageLabels = computed(() => {
    const map = {}
    SALES_STAGES.forEach(s => { map[s.value] = t('stages.' + s.value) })
    return map
  })
  const activeStages = computed(() => ACTIVE_STAGES)
  const wonProjects = computed(() => projects.value.filter(p => p.sales_stage === 'closed_won'))
  const lostProjects = computed(() => projects.value.filter(p => p.sales_stage === 'closed_lost'))
  const selectedStakeholder = computed(() => {
    if (!selectedStakeholderId.value) return null
    return stakeholders.value.find(s => s.id === selectedStakeholderId.value) || null
  })
  const stateLogsArray = computed(() => stateLogs.value || [])
  const buyerRoleLabels = computed(() => ({
    champion: t('stakeholder.buyerRoleOptions.champion'),
    blocker: t('stakeholder.buyerRoleOptions.blocker'),
    mobilizer: t('stakeholder.buyerRoleOptions.mobilizer'),
    guide: t('stakeholder.buyerRoleOptions.guide'),
    skeptic: t('stakeholder.buyerRoleOptions.skeptic'),
    coach: t('stakeholder.buyerRoleOptions.coach'),
  }))
  const buyerRoleTooltips = computed(() => ({
    champion: t('stakeholder.buyerRoleTooltips.champion'),
    blocker: t('stakeholder.buyerRoleTooltips.blocker'),
    mobilizer: t('stakeholder.buyerRoleTooltips.mobilizer'),
    guide: t('stakeholder.buyerRoleTooltips.guide'),
    skeptic: t('stakeholder.buyerRoleTooltips.skeptic'),
    coach: t('stakeholder.buyerRoleTooltips.coach'),
  }))
  // 项目角色（采购决策职能）
  const projectRoleLabels = computed(() => ({
    technical_buyer: t('stakeholder.projectRoleOptions.technical_buyer'),
    business_buyer: t('stakeholder.projectRoleOptions.business_buyer'),
    financial_buyer: t('stakeholder.projectRoleOptions.financial_buyer'),
    influencer: t('stakeholder.projectRoleOptions.influencer'),
    decision_maker: t('stakeholder.projectRoleOptions.decision_maker'),
    user: t('stakeholder.projectRoleOptions.user'),
  }))
  const projectRoleTooltips = computed(() => ({
    technical_buyer: t('stakeholder.projectRoleTooltips.technical_buyer'),
    business_buyer: t('stakeholder.projectRoleTooltips.business_buyer'),
    financial_buyer: t('stakeholder.projectRoleTooltips.financial_buyer'),
    influencer: t('stakeholder.projectRoleTooltips.influencer'),
    decision_maker: t('stakeholder.projectRoleTooltips.decision_maker'),
    user: t('stakeholder.projectRoleTooltips.user'),
  }))
  // 干系人识别状态
  const stakeholderStatusLabels = computed(() => ({
    confirmed: t('stakeholder.confirmed'),
    pending: t('stakeholder.pending'),
  }))
  const winRateColor = computed(() => {
    const rate = winRateData.value?.win_rate || 0
    if (rate >= 70) return 'text-success'
    if (rate >= 40) return 'text-warning'
    return 'text-error'
  })

  // ============ 表单数据 ============
  const newProject = ref({
    name: '',
    customer_name: '',
    sales_stage: 'suspect',
    budget: null,
    industry: ''
  })

  // ============ 方法 ============
  function projectsByStage(stage) {
    return projects.value.filter(p => p.sales_stage === stage)
  }

  function certClass(value) {
    // 与详情页 OverviewPane 一致：1=红=低、2=黄=中、3=绿=高
    if (value === 1 || value === 'red' || value === 'low') return 'dot-red'
    if (value === 2 || value === 'yellow' || value === 'medium') return 'dot-yellow'
    if (value === 3 || value === 'green' || value === 'high') return 'dot-green'
    return 'dot-empty'
  }

  function certLabel(type, value) {
    const typeKey = { time: 'project.timeCertainty', budget: 'project.budgetCertainty', tendency: 'project.tendency' }[type]
    const label = typeKey ? t(typeKey) : ''
    // 与详情页一致：1=低、2=中、3=高
    if (value === 1 || value === 'red' || value === 'low') return `${label}：${t('workspace.priorityLabels.low')}`
    if (value === 2 || value === 'yellow' || value === 'medium') return `${label}：${t('workspace.priorityLabels.medium')}`
    if (value === 3 || value === 'green' || value === 'high') return `${label}：${t('workspace.priorityLabels.high')}`
    return `${label}：${t('common.notSet')}`
  }

  function formatBudgetShort(n) {
    if (!n) return ''
    if (n >= 10000) return `¥${(n / 10000).toFixed(0)}${t('common.tenThousand')}`
    return `¥${Number(n).toLocaleString()}`
  }

  function getCustomerStats(c) {
    const projects = c.projects || []
    const activeCount = projects.filter(p => !['closed_won', 'closed_lost'].includes(p.sales_stage)).length
    const stageBudgets = {}
    projects.forEach(p => {
      if (p.sales_stage && p.budget) {
        stageBudgets[p.sales_stage] = (stageBudgets[p.sales_stage] || 0) + p.budget
      }
    })
    return { activeCount, stageBudgets, total: projects.length }
  }

  // ============ 数据加载 ============
  async function loadProjects() {
    try {
      const res = await salesTwinApi.getProjects()
      projects.value = res.projects || []
    } catch (e) {
      console.error('加载项目失败:', e)
    }
  }


  // ============ 项目操作 ============
  async function selectProject(projectId) {
    selectedProject.value = projectId
    activeMenu.value = 'overview'
    fermentationResult.value = null
    fermentationReport.value = null
    showReportView.value = false
    showInterviewView.value = false
    // 重置图谱状态（切换项目时清理）
    graphData.value = null
    // 先加载核心项目数据（干系人/任务/反馈等），确保 UI 切到 overview 时有数据
    await loadProjectData(projectId)
    // 并行加载次要数据，全部等待完成后再返回，避免 UI 渲染空状态
    await Promise.allSettled([
      loadProjectGraph(projectId),
      loadStageDeliverables(projectId),
      loadStageTimeline(projectId),
      loadStakeholderLinkContacts(),
    ])
  }

  async function loadProjectData(projectId) {
    if (!projectId) return
    try {
      const [stakeholdersRes, winRateRes, tasksRes, plansRes, feedbackRecordsRes] = await Promise.all([
        salesTwinApi.getStakeholders(projectId),
        salesTwinApi.getWinRate(projectId),
        salesTwinApi.getTasks(projectId),
        salesTwinApi.getMeetingPlans(projectId),
        salesTwinApi.getFeedbackRecords(projectId)
      ])
      stakeholders.value = stakeholdersRes.stakeholders || []
      winRateData.value = winRateRes
      tasks.value = tasksRes.tasks || []
      meetingPlans.value = plansRes.plans || []
      feedbackRecords.value = feedbackRecordsRes.records || []
      // 加载状态变更日志（用于干系人趋势图和交流历史）
      try {
        const logsRes = await salesTwinApi.getStateLogs(projectId)
        stateLogs.value = logsRes.logs || []
      } catch (e) {
        console.error('加载状态日志失败:', e)
      }
      // 加载最新盲区报告（从数据库读取，避免每次进项目都要重新扫描）
      try {
        const latestReport = await salesTwinApi.getLatestBlindSpotReport(projectId)
        if (latestReport && latestReport.data) {
          blindSpots.value = latestReport.data
        } else {
          blindSpots.value = null
        }
      } catch (e) {
        // 加载最新报告失败不影响主流程
      }
    } catch (e) {
      console.error('加载项目数据失败:', e)
    }
  }

  // ============ 阶段交付物追踪 ============
  // 加载阶段交付物清单
  async function loadStageDeliverables(projectId, stage = null) {
    if (!projectId) return
    stageDeliverablesLoading.value = true
    try {
      const res = await salesTwinApi.getStageDeliverables(projectId, stage)
      stageDeliverables.value = res
    } catch (e) {
      console.error('加载阶段交付物失败:', e)
      stageDeliverables.value = null
    } finally {
      stageDeliverablesLoading.value = false
    }
  }

  // 切换交付物完成状态
  async function toggleStageDeliverable(deliverableKey, isCompleted) {
    if (!selectedProject.value) return
    const stage = stageDeliverables.value?.stage
    if (!stage) return
    try {
      await salesTwinApi.updateStageDeliverable(selectedProject.value, deliverableKey, stage, {
        is_completed: isCompleted,
        notes: undefined  // 切换状态时不修改备注
      })
      // 刷新交付物数据
      await loadStageDeliverables(selectedProject.value, stage)
    } catch (e) {
      console.error('更新交付物状态失败:', e)
      showToast(t('toast.updateDeliverableFailed', { reason: e?.message || e }), 'error')
    }
  }

  // 更新交付物备注
  async function updateDeliverableNotes(deliverableKey, notes) {
    if (!selectedProject.value) return
    const stage = stageDeliverables.value?.stage
    if (!stage) return
    // 找到当前交付物项，获取其 is_completed 状态（避免覆盖）
    const currentItem = stageDeliverables.value?.deliverables
      ?.flatMap(g => g.items)
      ?.find(i => i.key === deliverableKey)
    try {
      await salesTwinApi.updateStageDeliverable(selectedProject.value, deliverableKey, stage, {
        is_completed: currentItem?.is_completed || false,
        notes: notes
      })
      await loadStageDeliverables(selectedProject.value, stage)
    } catch (e) {
      console.error('更新备注失败:', e)
      showToast(t('toast.updateNoteFailed', { reason: e?.message || e }), 'error')
    }
  }

  // 执行阶段检查
  async function runStageCheck() {
    if (!selectedProject.value) return
    try {
      stageCheckResult.value = await salesTwinApi.checkStageReadiness(selectedProject.value)
      showStageCheckModal.value = true
    } catch (e) {
      console.error('阶段检查失败:', e)
      showToast(t('toast.stageCheckFailed', { reason: e?.message || e }), 'error')
    }
  }

  // 关闭阶段检查 modal
  function closeStageCheckModal() {
    showStageCheckModal.value = false
  }

  // ============ 商机历程时间线 ============
  async function loadStageTimeline(projectId) {
    if (!projectId) return
    stageTimelineLoading.value = true
    try {
      const res = await salesTwinApi.getStageTimeline(projectId)
      stageTimeline.value = res
    } catch (e) {
      console.error('加载商机历程失败:', e)
      stageTimeline.value = null
    } finally {
      stageTimelineLoading.value = false
    }
  }

  async function createNewProject() {
    if (!newProject.value.name.trim()) return
    try {
      const res = await salesTwinApi.createProject(newProject.value)
      projects.value.unshift(res.project)
      showCreateModal.value = false
      newProject.value = {
        name: '',
        customer_name: '',
        sales_stage: 'suspect',
        budget: null,
        industry: ''
      }
      selectProject(res.project.id)
    } catch (e) {
      console.error('创建项目失败:', e)
    }
  }


  // ============ 拖拽处理 ============
  async function onDrop(e, targetStage, projectId) {
    if (!projectId || !targetStage) return
    try {
      await salesTwinApi.updateProject(projectId, { sales_stage: targetStage })
      const idx = projects.value.findIndex(p => p.id === projectId)
      if (idx !== -1) {
        projects.value[idx].sales_stage = targetStage
      }
      // 关单（赢单/丢单）时弹出关闭复盘
      if (targetStage === 'closed_won' || targetStage === 'closed_lost') {
        pendingCloseReview.value = { projectId, result: targetStage }
      }
    } catch (err) {
      console.error('更新阶段失败:', err)
    }
  }

  // ============ 干系人：关联联系人 / 创建 / 删除 ============
  const stakeholderLinkContacts = ref([])  // 供关联选择用的客户联系人列表
  const stakeholderLinkLoading = ref(false)

  async function loadStakeholderLinkContacts() {
    if (!selectedProject.value) return
    stakeholderLinkLoading.value = true
    try {
      const res = await salesTwinApi.getProjectStakeholderContacts(selectedProject.value)
      stakeholderLinkContacts.value = res.contacts || []
    } catch (e) {
      console.error('加载客户联系人失败:', e)
      stakeholderLinkContacts.value = []
    } finally {
      stakeholderLinkLoading.value = false
    }
  }

  // 添加干系人（支持关联客户联系人或手工输入）
  const showStakeholderAddModal = ref(false)
  const stakeholderAddForm = ref({
    name: '',
    position: '',
    level: '',
    contact_id: null,
    buyer_role: '',
    project_role: '',
    status: 'confirmed',
    decision_power: 5,
    support_level: 5,
    urgency: 5,
    responsibilities: '',
    personal_agenda: '',
  })
  const savingStakeholder = ref(false)

  // 姓名 typeahead 状态
  const showStakeholderNameSuggestions = ref(false)
  const stakeholderNameSuggestions = ref([])
  const stakeholderNameActiveIdx = ref(-1)
  const stakeholderNameInput = ref(null)

  function openStakeholderAddModal() {
    stakeholderAddForm.value = {
      name: '', position: '', level: '', contact_id: null,
      buyer_role: '', project_role: '', status: 'confirmed',
      decision_power: 5, support_level: 5, urgency: 5,
      responsibilities: '', personal_agenda: '',
    }
    showStakeholderAddModal.value = true
    showStakeholderNameSuggestions.value = false
    stakeholderNameSuggestions.value = []
    stakeholderNameActiveIdx.value = -1
    loadStakeholderLinkContacts()
  }

  // 姓名 input 输入时模糊匹配客户联系人
  function onStakeholderNameInput() {
    const q = (stakeholderAddForm.value.name || '').trim().toLowerCase()
    // 输入即清空 contact_id（视为第三方），除非再次选中建议
    stakeholderAddForm.value.contact_id = null
    if (!q) {
      stakeholderNameSuggestions.value = []
      showStakeholderNameSuggestions.value = false
      stakeholderNameActiveIdx.value = -1
      return
    }
    const matched = (stakeholderLinkContacts.value || []).filter(ct =>
      (ct.name || '').toLowerCase().includes(q) ||
      (ct.department || '').toLowerCase().includes(q) ||
      (ct.position || '').toLowerCase().includes(q)
    ).slice(0, 8)
    stakeholderNameSuggestions.value = matched
    showStakeholderNameSuggestions.value = matched.length > 0
    stakeholderNameActiveIdx.value = matched.length > 0 ? 0 : -1
  }

  function onStakeholderNameBlur() {
    setTimeout(() => {
      showStakeholderNameSuggestions.value = false
    }, 150)
  }

  function onStakeholderNameEnter() {
    if (showStakeholderNameSuggestions.value && stakeholderNameActiveIdx.value >= 0) {
      const ct = stakeholderNameSuggestions.value[stakeholderNameActiveIdx.value]
      if (ct) {
        selectStakeholderNameSuggestion(ct)
        return
      }
    }
    showStakeholderNameSuggestions.value = false
  }

  function selectStakeholderNameSuggestion(ct) {
    stakeholderAddForm.value.contact_id = ct.id
    stakeholderAddForm.value.name = ct.name
    stakeholderAddForm.value.position = ct.position || ''
    showStakeholderNameSuggestions.value = false
    stakeholderNameActiveIdx.value = -1
  }

  function selectStakeholderNameAsThirdParty() {
    stakeholderAddForm.value.contact_id = null
    showStakeholderNameSuggestions.value = false
  }

  async function saveNewStakeholder() {
    if (!selectedProject.value) return
    if (!stakeholderAddForm.value.name?.trim()) {
      showToast(t('toast.nameRequired'), 'warning')
      return
    }
    savingStakeholder.value = true
    try {
      const res = await salesTwinApi.createStakeholder(selectedProject.value, {
        ...stakeholderAddForm.value,
        name: stakeholderAddForm.value.name.trim(),
      })
      stakeholders.value.push(res.stakeholder)
      showStakeholderAddModal.value = false
      // 刷新联系人列表的 linked 状态
      loadStakeholderLinkContacts()
    } catch (e) {
      console.error('创建干系人失败:', e)
      showToast(t('toast.createFailed', { reason: e?.message || e }), 'error')
    } finally {
      savingStakeholder.value = false
    }
  }

  // 删除干系人（仅从当前商机中移除）
  const showStakeholderDeleteConfirm = ref(false)
  const stakeholderToDelete = ref(null)
  const deletingStakeholder = ref(false)

  function confirmDeleteStakeholder(stakeholder) {
    stakeholderToDelete.value = stakeholder
    showStakeholderDeleteConfirm.value = true
  }

  async function performDeleteStakeholder() {
    if (!stakeholderToDelete.value) return
    deletingStakeholder.value = true
    try {
      await salesTwinApi.deleteStakeholder(stakeholderToDelete.value.id)
      const id = stakeholderToDelete.value.id
      stakeholders.value = stakeholders.value.filter(s => s.id !== id)
      // 解除其他干系人的汇报关系
      stakeholders.value.forEach(s => {
        if (s.reports_to_id === id) s.reports_to_id = null
      })
      if (selectedStakeholderId.value === id) selectedStakeholderId.value = null
      showStakeholderDeleteConfirm.value = false
      stakeholderToDelete.value = null
      // 刷新联系人列表的 linked 状态
      loadStakeholderLinkContacts()
    } catch (e) {
      console.error('删除干系人失败:', e)
      showToast(t('toast.deleteFailed', { reason: e?.message || e }), 'error')
    } finally {
      deletingStakeholder.value = false
    }
  }


  // ============ 图谱加载 ============
  // 加载项目图谱数据（切换项目时调用）；图谱数据全部来自数据库注入
  async function loadProjectGraph(projectId) {
    if (!projectId) return
    try {
      const res = await salesTwinApi.getProjectGraph(projectId)
      if (res?.graph_data) {
        graphData.value = res.graph_data
      } else {
        graphData.value = null
      }
    } catch (e) {
      // 静默失败：尚未维护图谱数据是正常情况
      graphData.value = null
    }
  }

  // 刷新当前图谱数据（GraphPanel/GraphView 调用）
  function refreshGraph() {
    if (!selectedProject.value) return
    graphLoading.value = true
    loadProjectGraph(selectedProject.value).finally(() => {
      graphLoading.value = false
    })
  }

  // ============ 干系人编辑/合并 ============
  // 注：StakeholderDetailPanel 内部已支持字段双击内联编辑，emit('updated') 后由父组件刷新。
  // 这里 openEditStakeholderModal 仅选中该干系人，让其显示在右侧详情面板中。
  function openEditStakeholderModal(stakeholder) {
    if (!stakeholder) return
    selectedStakeholderId.value = stakeholder.id
  }

  function startMerge(stakeholder) {
    if (!stakeholder) return
    mergePrimary.value = stakeholder
    mergeMode.value = true
  }

  function cancelMerge() {
    mergeMode.value = false
    mergePrimary.value = null
  }

  async function executeMerge(secondary) {
    if (!selectedProject.value || !mergePrimary.value || !secondary) return
    if (mergePrimary.value.id === secondary.id) return
    try {
      await salesTwinApi.mergeStakeholders(
        selectedProject.value,
        mergePrimary.value.id,
        secondary.id
      )
      // 合并成功后重新加载干系人列表
      const res = await salesTwinApi.getStakeholders(selectedProject.value)
      stakeholders.value = res.stakeholders || []
      // 解除其他干系人对已删除干系人的汇报关系
      const deletedId = secondary.id
      stakeholders.value.forEach(s => {
        if (s.reports_to_id === deletedId) s.reports_to_id = null
      })
      // 刷新状态日志
      try {
        const logsRes = await salesTwinApi.getStateLogs(selectedProject.value)
        stateLogs.value = logsRes.logs || []
      } catch (e) { /* 日志加载失败不影响主流程 */ }
      // 退出合并模式
      mergeMode.value = false
      mergePrimary.value = null
      // 刷新客户联系人列表的 linked 状态
      loadStakeholderLinkContacts()
    } catch (e) {
      console.error('合并干系人失败:', e)
      showToast(t('toast.mergeFailed', { reason: e?.message || e }), 'error')
    }
  }

  // openAddStakeholderModal 作为 openStakeholderAddModal 的别名（StakeholderView emit 的是 open-add-modal）
  const openAddStakeholderModal = openStakeholderAddModal

  // ============ 生命周期 ============
  onMounted(() => {
    loadProjects()
  })

  return {
    // State
    projects, allCustomers, selectedProject, activeMenu, showCreateModal, showStakeholderModal, stakeholderModalMode,
    newProject, stakeholders, relationships, blindSpots, sortedFindings, nextActions,
    winRateData, showWinRatePanel, feedbackText, feedbackResult, stateLogs, fermentationResult, chartSvg,
    interviewTargetId, interviewQuestion, interviewResult, interviewing, interviewHistory, presetQuestions,
    showReportView, showInterviewView, showSuggestionPool, fermentationReport, generatingOverview,
    generatingValueProp, generatingCompetitive, generatingPainPoints, reformattingField, tasks, taskFilter,
    editingTask, showTaskModal, newTask, selectedTask, editingTaskInline, taskEditForm, sortingTasks,
    taskSortSuggestions, applyingSort, scanningBlindSpots, generatingActions, meetingPlans, showPlanModal, newPlan, selectedPlan, generatingPlan,
    planFilter, actionFilter, editingPlan, planEditForm, savingPlan, expandedRecordId, expandedRecordText,
    loadingRecordId, showAllFeedbackRecords, feedbackRelatedTaskIds, feedbackRelatedPlanId, feedbackRecords,
    displayedFeedbackRecords, feedbackAttachments, feedbackFileInput, fermentationInput, editingStakeholder,
    showStakeholderEditModal, stakeholderEditForm, stakeholderEditReason, showProjectEditModal, projectEditForm,
    projectEditReason, savingProject, inlineEditField, inlineEditValue, inlineEditSaving, mergeMode, mergePrimary,
    selectedStakeholderId, graphData,
    graphLoading, graphSidebar, runningSim,
    // 关闭复盘（关单时弹出）
    pendingCloseReview,
    // 阶段交付物追踪
    stageDeliverables, stageDeliverablesLoading, stageCheckResult, showStageCheckModal,
    // 商机历程时间线
    stageTimeline, stageTimelineLoading,
    // 干系人：关联联系人 / 创建 / 删除
    stakeholderLinkContacts, stakeholderLinkLoading,
    showStakeholderAddModal, stakeholderAddForm, savingStakeholder,
    showStakeholderNameSuggestions, stakeholderNameSuggestions, stakeholderNameActiveIdx, stakeholderNameInput,
    onStakeholderNameInput, onStakeholderNameBlur, onStakeholderNameEnter,
    selectStakeholderNameSuggestion, selectStakeholderNameAsThirdParty,
    showStakeholderDeleteConfirm, stakeholderToDelete, deletingStakeholder,
    // Computed
    currentProject, stageLabels, activeStages, wonProjects, lostProjects, selectedStakeholder, stateLogsArray,
    buyerRoleLabels, buyerRoleTooltips, projectRoleLabels, projectRoleTooltips, stakeholderStatusLabels, winRateColor,
    // Methods
    projectsByStage, certClass, certLabel, formatBudgetShort, getCustomerStats,
    loadProjects, loadProjectData,
    selectProject, createNewProject, onDrop,
    loadStageDeliverables, toggleStageDeliverable, updateDeliverableNotes, runStageCheck, closeStageCheckModal,
    loadStageTimeline,
    loadStakeholderLinkContacts, openStakeholderAddModal, openAddStakeholderModal, saveNewStakeholder,
    confirmDeleteStakeholder, performDeleteStakeholder,
    // 干系人编辑/合并
    openEditStakeholderModal, startMerge, cancelMerge, executeMerge,
    // 图谱
    refreshGraph, loadProjectGraph,
    // Formatters
    formatStructuredText, formatDate, formatDateTime, formatCurrency, truncateText, formatFileSize,
    // Directives
    vFocus,
  }
}

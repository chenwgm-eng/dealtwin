<template>
  <div class="sales-twin">
    <SalesTwinSidebar
      :projects="projects"
      :selectedProject="currentProject"
      :activeMenu="activeMenu"
      :stakeholderCount="stakeholders.length"
      @select-menu="handleSelectMenu"
      @clear-project="activeMenu = 'projects'"
      @go-home="activeMenu = 'projects'"
    />

    <main class="main-content">
      <!-- 仪表盘（嵌入 SalesDashboard） -->
      <SalesDashboard
        v-if="activeMenu === 'dashboard'"
        embedded
      />

      <!-- 项目列表 -->
      <ProjectList
        v-if="activeMenu === 'projects'"
        :projects="projects"
        :stageLabels="stageLabels"
        :activeStages="activeStages"
        :formatCurrency="formatCurrency"
        :formatDate="formatDate"
        :truncateText="truncateText"
        :certClass="certClass"
        :certLabel="certLabel"
        @select-project="selectProject"
        @show-create-modal="showCreateModal = true"
        @drop="onDrop"
    />

      <!-- 设置（全局，不依赖选中项目） -->
      <SettingsPanel
        v-else-if="activeMenu === 'settings'"
      />

      <!-- 学习中心（自进化引擎：模式审核台，全局，不依赖选中项目） -->
      <LearningCenter
        v-else-if="activeMenu === 'learning'"
      />

      <!-- Agent 调度中枢（后台定时任务管理，全局） -->
      <AgentJobManager
        v-else-if="activeMenu === 'agent_jobs'"
      />

      <!-- 项目详情 -->
      <div v-else-if="selectedProject" class="project-detail-view">
        <div class="detail-header">
          <div class="header-left">
            <h1 class="page-title">{{ currentProject?.name }}</h1>
            <span v-if="currentProject?.customer_name" class="detail-customer">
              {{ currentProject.customer_name }}
            </span>
          </div>
          <span class="stage-badge" :class="currentProject?.sales_stage">
            {{ stageLabels[currentProject?.sales_stage] }}
          </span>
        </div>

        <div class="tab-content" :class="{ 'with-sidebar': graphSidebar && graphData && activeMenu !== 'graph' }">
          <!-- 图谱侧栏 -->
          <div v-if="graphSidebar && graphData && activeMenu !== 'graph'" class="graph-sidebar">
            <GraphPanel
              :graphData="graphData"
              :loading="graphLoading"
              @refresh="refreshGraph"
              @toggle-maximize="activeMenu = 'graph'; graphSidebar = false"
            />
          </div>

          <!-- 右侧内容区 -->
          <div class="tab-content-main">
            <!-- 概览 -->
            <OverviewPane
              v-if="activeMenu === 'overview'"
              :currentProject="currentProject"
              :stakeholders="stakeholders"
              :tasks="tasks"
              :winRateData="winRateData"
              :sortedFindings="sortedFindings"
              :winRateColor="winRateColor"
              :allCustomers="allCustomers"
              :formatStructuredText="formatStructuredText"
              :formatDate="formatDate"
              :formatCurrency="formatCurrency"
              :stageDeliverables="stageDeliverables"
              :stageDeliverablesLoading="stageDeliverablesLoading"
              :feedbackRecords="feedbackRecords"
              :stateLogs="stateLogsArray"
              @navigate-to="activeMenu = $event"
              @update-project="handleUpdateProjectField"
              @refresh-project="handleRefreshProject"
              @reload-stage-deliverables="handleReloadStageDeliverables"
              @run-stage-check="runStageCheck"
            />

            <!-- 商机历程 -->
            <StageTimeline
              v-else-if="activeMenu === 'timeline'"
              :timelineData="stageTimeline"
              :loading="stageTimelineLoading"
              :formatDate="formatDate"
            />

            <!-- 图谱 -->
            <GraphView
              v-else-if="activeMenu === 'graph'"
              :graphData="graphData"
              :graphLoading="graphLoading"
              @refresh="refreshGraph"
              @toggle-maximize="graphSidebar = false"
            />

            <!-- 干系人 -->
            <StakeholderView
              v-else-if="activeMenu === 'stakeholders'"
              :stakeholders="stakeholders"
              :selectedStakeholderId="selectedStakeholderId"
              :mergeMode="mergeMode"
              :mergePrimary="mergePrimary"
              :stateLogsArray="stateLogsArray"
              :fermentationResult="fermentationResult"
              :meetingPlans="meetingPlans"
              :buyerRoleLabels="buyerRoleLabels"
              :buyerRoleTooltips="buyerRoleTooltips"
              :projectRoleLabels="projectRoleLabels"
              :projectRoleTooltips="projectRoleTooltips"
              :customerContacts="stakeholderLinkContacts"
              @select-stakeholder="selectedStakeholderId = $event"
              @open-edit-modal="openEditStakeholderModal"
              @start-merge="startMerge"
              @cancel-merge="cancelMerge"
              @execute-merge="executeMerge"
              @open-add-modal="openStakeholderAddModal"
              @stakeholder-updated="handleStakeholderInlineUpdated"
              @delete-stakeholder="confirmDeleteStakeholder"
            />

            <!-- 工作台 -->
            <WorkspaceView
              v-else-if="['blindspot', 'actions', 'tasks', 'meeting', 'visit', 'teaching'].includes(activeMenu)"
              :activeSubMenu="activeMenu"
              :project-id="selectedProject"
              :sales-mode="currentProject?.sales_mode || null"
              :sortedFindings="sortedFindings"
              :blindSpots="blindSpots"
              :nextActions="nextActions"
              :tasks="tasks"
              :taskFilter="taskFilter"
              :meetingPlans="meetingPlans"
              :planFilter="planFilter"
              :actionFilter="actionFilter"
              :stakeholders="stakeholders"
              :stateLogsArray="stateLogsArray"
              :fermentationResult="fermentationResult"
              :feedbackRecords="feedbackRecords"
              :showAllFeedbackRecords="showAllFeedbackRecords"
              :feedbackText="feedbackText"
              :feedbackResult="feedbackResult"
              :feedbackAttachments="feedbackAttachments"
              :feedbackRelatedTaskIds="feedbackRelatedTaskIds"
              :feedbackRelatedPlanId="feedbackRelatedPlanId"
              :winRateData="winRateData"
              :showWinRatePanel="showWinRatePanel"
              :interviewHistory="interviewHistory"
              :interviewTargetId="interviewTargetId"
              :interviewQuestion="interviewQuestion"
              :interviewResult="interviewResult"
              :interviewing="interviewing"
              :presetQuestions="presetQuestions"
              :selectedTask="selectedTask"
              :selectedPlan="selectedPlan"
              :editingTaskInline="editingTaskInline"
              :editingPlan="editingPlan"
              :showTaskModal="showTaskModal"
              :showPlanModal="showPlanModal"
              :newTask="newTask"
              :newPlan="newPlan"
              :taskEditForm="taskEditForm"
              :planEditForm="planEditForm"
              :expandedRecordId="expandedRecordId"
              :showSuggestionPool="showSuggestionPool"
              :scanningBlindSpots="scanningBlindSpots"
              :generatingActions="generatingActions"
              :sortingTasks="sortingTasks"
              @navigate-to="activeMenu = $event"
              @update:activeSubMenu="activeMenu = $event"
              @update:taskFilter="taskFilter = $event"
              @update:planFilter="planFilter = $event"
              @update:actionFilter="actionFilter = $event"
              @update:showAllFeedbackRecords="showAllFeedbackRecords = $event"
              @update:feedbackText="feedbackText = $event"
              @update:feedbackRelatedTaskIds="feedbackRelatedTaskIds = $event"
              @update:feedbackRelatedPlanId="feedbackRelatedPlanId = $event"
              @update:showWinRatePanel="showWinRatePanel = $event"
              @update:interviewTargetId="interviewTargetId = $event"
              @update:interviewQuestion="interviewQuestion = $event"
              @update:showSuggestionPool="showSuggestionPool = $event"
              @update:editingTaskInline="editingTaskInline = $event"
              @update:editingPlan="editingPlan = $event"
              @update:showTaskModal="showTaskModal = $event"
              @update:showPlanModal="showPlanModal = $event"
              @update:selectedTask="selectedTask = $event"
              @update:selectedPlan="selectedPlan = $event"
              @update:expandedRecordId="expandedRecordId = $event"
              @toggle-win-rate-panel="showWinRatePanel = !showWinRatePanel"
              @scan-blindspots="handleScanBlindSpots"
              @go-to-actions="handleGoToActions"
              @load-actions="handleLoadActions"
              @adopt-action="handleAdoptAction"
              @reject-action="handleRejectAction"
              @view-adopted-task="handleViewAdoptedTask"
              @auto-sort-tasks="handleAutoSortTasks"
              @apply-task-sort="handleApplyTaskSort"
              @clear-sort-suggestions="taskSortSuggestions = null"
              @open-task-modal="showTaskModal = true"
              @select-task="handleSelectTask"
              @start-inline-edit-task="handleStartInlineEditTask"
              @remove-task="handleRemoveTask"
              @submit-inline-edit-task="handleSubmitInlineEditTask"
              @cancel-inline-edit="editingTaskInline = false"
              @change-task-status="handleChangeTaskStatus"
              @view-feedback-in-visit="handleViewFeedbackInVisit"
              @open-plan-modal="showPlanModal = true"
              @view-plan="handleViewPlan"
              @open-edit-plan="handleOpenEditPlan"
              @remove-plan="handleRemovePlan"
              @submit-plan-edit="handleSubmitPlanEdit"
              @cancel-plan-edit="editingPlan = false"
              @feedback-file-select="handleFeedbackFileSelect"
              @remove-attachment="handleRemoveAttachment"
              @submit-feedback="handleSubmitFeedback"
              @toggle-record-expand="handleToggleRecordExpand"
              @toggle-show-all-feedback="showAllFeedbackRecords = !showAllFeedbackRecords"
              @open-edit-modal="openEditStakeholderModal"
              @open-add-modal="openAddStakeholderModal"
              @sales-mode-changed="handleSalesModeChanged"
            />

            <!-- 推演模拟 -->
            <SimulationView
              v-else-if="activeMenu === 'feedback'"
              :fermentationResult="fermentationResult"
              :fermentationInput="fermentationInput"
              :runningSim="runningSim"
              :feedbackRecords="feedbackRecords"
              :tasks="tasks"
              :stakeholders="stakeholders"
              :buyerRoleLabels="buyerRoleLabels"
              :interviewHistory="interviewHistory"
              :interviewTargetId="interviewTargetId"
              :interviewQuestion="interviewQuestion"
              :interviewResult="interviewResult"
              :interviewing="interviewing"
              :presetQuestions="presetQuestions"
              :showReportView="showReportView"
              :showInterviewView="showInterviewView"
              :showSuggestionPool="showSuggestionPool"
              :fermentationReport="fermentationReport"
              :chartSvg="chartSvg"
              @run-simulation="runSimulation"
              @reset-simulation="resetSimulation"
              @run-interview="runInterview"
              @update:fermentationInput="fermentationInput = $event"
              @update:interviewTargetId="interviewTargetId = $event"
              @update:interviewQuestion="interviewQuestion = $event"
              @update:showReportView="showReportView = $event"
              @update:showInterviewView="showInterviewView = $event"
              @update:showSuggestionPool="showSuggestionPool = $event"
              @close-interview-result="interviewResult = null"
            />
          </div>
        </div>
      </div>
    </main>

    <!-- 推演报告全屏视图 -->
    <SalesSimulationReport
      v-if="showReportView"
      :project-id="selectedProject"
      :stakeholders="stakeholders"
      :fermentation-result="fermentationResult"
      :initial-report="fermentationReport"
      @close="showReportView = false"
      @go-interview="showReportView = false; showInterviewView = true"
      @report-generated="fermentationReport = $event"
      @open-suggestions="showSuggestionPool = true"
    />

    <!-- 深度访谈全屏视图 -->
    <SalesDeepInterview
      v-if="showInterviewView"
      :project-id="selectedProject"
      :stakeholders="stakeholders"
      :fermentation-result="fermentationResult"
      @close="showInterviewView = false"
      @open-suggestions="showSuggestionPool = true"
    />

    <!-- 建议池抽屉 -->
    <SuggestionPoolDrawer
      :visible="showSuggestionPool"
      :project-id="selectedProject"
      @close="showSuggestionPool = false"
    />

    <!-- 添加干系人弹窗 -->
    <StakeholderAddModal
      :show="showStakeholderAddModal"
      :form="stakeholderAddForm"
      :saving="savingStakeholder"
      :suggestions="stakeholderNameSuggestions"
      :suggestion-active-idx="stakeholderNameActiveIdx"
      :show-suggestions="showStakeholderNameSuggestions"
      :link-contacts="stakeholderLinkContacts"
      :link-loading="stakeholderLinkLoading"
      @close="showStakeholderAddModal = false"
      @save="saveNewStakeholder"
      @name-input="onStakeholderNameInput"
      @name-enter="onStakeholderNameEnter"
      @name-blur="onStakeholderNameBlur"
      @hover-suggestion="stakeholderNameActiveIdx = $event"
      @select-suggestion="selectStakeholderNameSuggestion"
      @select-as-third-party="selectStakeholderNameAsThirdParty"
      @update:form="Object.assign(stakeholderAddForm, $event)"
    />

    <!-- 删除干系人确认弹窗 -->
    <StakeholderDeleteConfirmModal
      :show="showStakeholderDeleteConfirm"
      :stakeholder="stakeholderToDelete"
      :deleting="deletingStakeholder"
      @close="showStakeholderDeleteConfirm = false"
      @confirm="performDeleteStakeholder"
    />

    <!-- 新建项目弹窗 -->
    <NewProjectModal
      :show="showCreateModal"
      :form="newProject"
      :active-stages="activeStages"
      @close="showCreateModal = false"
      @create="createNewProject"
      @update:form="Object.assign(newProject, $event)"
    />

    <!-- 新建待办弹窗 -->
    <NewTaskModal
      :show="showTaskModal"
      :form="newTask"
      :stakeholders="stakeholders"
      @close="showTaskModal = false"
      @create="handleCreateTask"
      @update:form="Object.assign(newTask, $event)"
    />

    <!-- 生成预案弹窗 -->
    <NewPlanModal
      :show="showPlanModal"
      :form="newPlan"
      :stakeholders="stakeholders"
      :tasks="tasks"
      :generating="generatingPlan"
      @close="showPlanModal = false"
      @create="handleCreatePlan"
      @update:form="Object.assign(newPlan, $event)"
    />

    <!-- 阶段检查 modal -->
    <StageCheckModal
      :show="showStageCheckModal"
      :checkResult="stageCheckResult"
      :currentStage="currentProject?.sales_stage || ''"
      :nextStage="nextSalesStage"
      @close="closeStageCheckModal"
      @advance-stage="handleAdvanceStage"
    />

    <!-- 关闭复盘弹窗（关单时弹出） -->
    <CloseReviewModal
      :show="!!pendingCloseReview"
      :project-id="pendingCloseReview?.projectId"
      :result="pendingCloseReview?.result"
      :project="closeReviewProject"
      @close="pendingCloseReview = null"
      @submitted="pendingCloseReview = null"
    />

    <!-- 通用确认弹窗（替代原生 confirm()） -->
    <GenericConfirmModal />

    <!-- 全局 Toast 通知（替代原生 alert()） -->
    <GlobalToast />
  </div>
</template>

<script setup>
import { computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useSalesTwin } from '../composables/salesTwin/useSalesTwin'
import * as salesTwinApi from '../api/salesTwin'
import SalesTwinSidebar from '../components/SalesTwinSidebar.vue'
import SalesDashboard from './SalesDashboard.vue'
import ProjectList from '../components/salesTwin/ProjectList.vue'
import OverviewPane from '../components/salesTwin/OverviewPane.vue'
import GraphView from '../components/salesTwin/GraphView.vue'
import StakeholderView from '../components/salesTwin/StakeholderView.vue'
import WorkspaceView from '../components/salesTwin/WorkspaceView.vue'
import SimulationView from '../components/salesTwin/SimulationView.vue'
import SalesSimulationReport from '../components/salesTwin/SalesSimulationReport.vue'
import SalesDeepInterview from '../components/salesTwin/SalesDeepInterview.vue'
import SuggestionPoolDrawer from '../components/salesTwin/SuggestionPoolDrawer.vue'
import GraphPanel from '../components/GraphPanel.vue'
import StageCheckModal from '../components/salesTwin/StageCheckModal.vue'
import StageTimeline from '../components/salesTwin/StageTimeline.vue'
import CloseReviewModal from '../components/salesTwin/CloseReviewModal.vue'
import SettingsPanel from '../components/salesTwin/SettingsPanel.vue'
import LearningCenter from '../components/salesTwin/LearningCenter.vue'
import AgentJobManager from '../components/salesTwin/AgentJobManager.vue'
// 拆分出的 modal 子组件（L-04：SalesTwin.vue 行数优化）
import NewProjectModal from '../components/salesTwin/NewProjectModal.vue'
import NewTaskModal from '../components/salesTwin/NewTaskModal.vue'
import NewPlanModal from '../components/salesTwin/NewPlanModal.vue'
import StakeholderAddModal from '../components/salesTwin/StakeholderAddModal.vue'
import StakeholderDeleteConfirmModal from '../components/salesTwin/StakeholderDeleteConfirmModal.vue'
import GenericConfirmModal from '../components/salesTwin/GenericConfirmModal.vue'
import GlobalToast from '../components/salesTwin/GlobalToast.vue'
import { showToast } from '../composables/salesTwin/useConfirmToast'
import { useSalesTwinWorkspace } from '../composables/salesTwin/useSalesTwinWorkspace'

const { t } = useI18n()

// Import all state and methods from composable
const salesTwin = useSalesTwin()
const {
  projects, selectedProject, activeMenu, stakeholders,
  currentProject, stageLabels, activeStages, wonProjects, lostProjects,
  // 阶段交付物追踪
  stageDeliverables, stageDeliverablesLoading, stageCheckResult, showStageCheckModal,
  // 关闭复盘（关单时弹出）
  pendingCloseReview,
  // 商机历程时间线
  stageTimeline, stageTimelineLoading,
  sortedFindings, blindSpots, nextActions, winRateData, showWinRatePanel, feedbackText, feedbackResult,
  stateLogs, fermentationResult, chartSvg, interviewTargetId, interviewQuestion,
  interviewResult, interviewing, interviewHistory, presetQuestions, showReportView,
  showInterviewView, showSuggestionPool, tasks, taskFilter, editingTask, showTaskModal,
  newTask, selectedTask, editingTaskInline, taskEditForm, meetingPlans, showPlanModal,
  newPlan, selectedPlan, planFilter, actionFilter, editingPlan, planEditForm,
  expandedRecordId, showAllFeedbackRecords, feedbackRecords, displayedFeedbackRecords,
  feedbackAttachments, feedbackFileInput, fermentationInput, mergeMode, mergePrimary,
  selectedStakeholderId, selectedStakeholder, stateLogsArray, buyerRoleLabels, buyerRoleTooltips,
  projectRoleLabels, projectRoleTooltips, stakeholderStatusLabels,
  winRateColor, graphData,
  graphLoading, graphSidebar, runningSim, showCreateModal,
  showStakeholderModal, stakeholderModalMode, editingStakeholder, showStakeholderEditModal,
  stakeholderEditForm, stakeholderEditReason, showProjectEditModal, projectEditForm,
  projectEditReason, savingProject, inlineEditField, inlineEditValue, inlineEditSaving,
  generatingOverview, generatingValueProp, generatingCompetitive, generatingPainPoints,
  reformattingField, sortingTasks, taskSortSuggestions, applyingSort, scanningBlindSpots, generatingActions, generatingPlan,
  savingPlan, expandedRecordText, loadingRecordId, feedbackRelatedTaskIds, feedbackRelatedPlanId,
  fermentationReport, allCustomers, newProject,
  projectsByStage, certClass, certLabel, formatBudgetShort, getCustomerStats,
  loadProjects, loadProjectData,
  loadStageDeliverables, toggleStageDeliverable, updateDeliverableNotes, runStageCheck, closeStageCheckModal,
  loadStageTimeline,
  // 干系人：关联联系人 / 创建 / 删除
  stakeholderLinkContacts, stakeholderLinkLoading,
  showStakeholderAddModal, stakeholderAddForm, savingStakeholder,
  showStakeholderNameSuggestions, stakeholderNameSuggestions, stakeholderNameActiveIdx, stakeholderNameInput,
  onStakeholderNameInput, onStakeholderNameBlur, onStakeholderNameEnter,
  selectStakeholderNameSuggestion, selectStakeholderNameAsThirdParty,
  showStakeholderDeleteConfirm, stakeholderToDelete, deletingStakeholder,
  loadStakeholderLinkContacts, openStakeholderAddModal, openAddStakeholderModal, saveNewStakeholder,
  confirmDeleteStakeholder, performDeleteStakeholder,
  // 干系人编辑/合并
  openEditStakeholderModal, startMerge, cancelMerge, executeMerge,
  // 图谱
  refreshGraph,
  selectProject, createNewProject, onDrop,
  formatStructuredText, formatDate, formatDateTime, formatCurrency, truncateText, formatFileSize,
  vFocus,
} = salesTwin

// 工作台事件处理（盲区扫描、行动建议、待办编辑、预案管理、反馈提交）
// 这些 handler 依赖 useSalesTwin 提供的响应式 state，通过传入 salesTwin composable 保持引用一致
const {
  handleScanBlindSpots, handleGoToActions, handleLoadActions, handleAdoptAction,
  handleRejectAction, handleViewAdoptedTask, handleAutoSortTasks, handleApplyTaskSort, handleSelectTask,
  handleStartInlineEditTask, handleSubmitInlineEditTask, handleRemoveTask,
  handleChangeTaskStatus, handleViewFeedbackInVisit, handleViewPlan, handleOpenEditPlan,
  handleSubmitPlanEdit, handleRemovePlan, handleFeedbackFileSelect, handleRemoveAttachment,
  handleSubmitFeedback, handleToggleRecordExpand,
} = useSalesTwinWorkspace(salesTwin)

const route = useRoute()

// 合法的菜单白名单（支持通过 URL query 直接定位菜单）
const VALID_MENUS = ['dashboard', 'projects', 'tasks', 'stakeholders', 'meeting', 'visit', 'feedback', 'teaching']

// 应用 query 参数：支持 ?menu=xxx 和 ?project=xxx
// - 若带 project 且与当前不同，先 selectProject（会加载项目数据并设 activeMenu='overview'）
// - 然后用 query.menu 覆盖 activeMenu
async function applyRouteQuery(query) {
  if (!query?.menu) return
  if (!VALID_MENUS.includes(query.menu)) return

  // 若指定项目且与当前不同，先切换项目
  if (query.project != null) {
    const pid = Number(query.project)
    if (!isNaN(pid) && pid !== selectedProject.value) {
      await selectProject(pid)
    }
  }
  activeMenu.value = query.menu
}

// 处理 ?menu= 查询参数，支持通过 URL 直接定位菜单（初次挂载）
onMounted(() => {
  applyRouteQuery(route.query)
})

// 监听 query 变化（从 Dashboard 子组件点击跳转时，组件已挂载，onMounted 不会再触发）
watch(
  () => route.query,
  (q) => applyRouteQuery(q),
  { deep: true }
)

// 处理侧边栏菜单切换：
// - 切到「仪表盘」「客户管理」「商机台账」这类全局视图时，清空已选项目状态，
//   避免残留的 selectedProject 导致从仪表盘切回项目时仍停留在旧项目，
//   并避免 dashboard 页面底部出现残留的项目信息行。
// - 切到项目级菜单（overview/timeline/graph/stakeholders/...）时保持 selectedProject。
function handleSelectMenu(menu) {
  const GLOBAL_MENUS = ['dashboard', 'projects', 'settings', 'learning', 'agent_jobs']
  if (GLOBAL_MENUS.includes(menu)) {
    selectedProject.value = null
    // 同步清理项目相关的临时状态，避免残留
    fermentationResult.value = null
    fermentationReport.value = null
    showReportView.value = false
    showInterviewView.value = false
    showSuggestionPool.value = false
  }
  activeMenu.value = menu
}

// 销售阶段顺序（用于计算下一阶段）
const SALES_STAGE_ORDER = ['suspect', 'identity', 'define', 'confirm', 'closed_won']

// 下一销售阶段（用于阶段推进按钮显示）
const nextSalesStage = computed(() => {
  const current = currentProject.value?.sales_stage
  if (!current) return ''
  const idx = SALES_STAGE_ORDER.indexOf(current)
  if (idx < 0 || idx >= SALES_STAGE_ORDER.length - 1) return ''
  return SALES_STAGE_ORDER[idx + 1]
})

// 关闭复盘弹窗预填项目（拖拽关单时不一定是当前选中项目）
const closeReviewProject = computed(() => {
  if (!pendingCloseReview.value) return null
  return projects.value.find(p => p.id === pendingCloseReview.value.projectId) || null
})

// 推进销售阶段
async function handleAdvanceStage() {
  if (!selectedProject.value) return
  if (!nextSalesStage.value) return
  const targetStage = nextSalesStage.value
  try {
    await salesTwinApi.updateProject(selectedProject.value, {
      sales_stage: targetStage
    })
    // 关闭 modal
    closeStageCheckModal()
    // 刷新项目数据（包括 currentProject 和 stageDeliverables）
    await loadProjectData(selectedProject.value)
    await loadStageDeliverables(selectedProject.value)
    // 刷新商机历程时间线
    await loadStageTimeline(selectedProject.value)
    // 刷新项目列表（侧边栏阶段徽章可能变化）
    await loadProjects()
    // 关单（赢单）时弹出关闭复盘
    if (targetStage === 'closed_won' || targetStage === 'closed_lost') {
      pendingCloseReview.value = { projectId: selectedProject.value, result: targetStage }
    }
  } catch (e) {
    console.error('推进销售阶段失败:', e)
    showToast(t('toast.advanceStageFailed', { reason: e?.message || e }), 'error')
  }
}

// 销售模式变更（里程碑面板）：后端已写库，同步更新本地 projects 数组中的项目
function handleSalesModeChanged(mode) {
  if (!selectedProject.value || !mode) return
  const idx = projects.value.findIndex(p => p.id === selectedProject.value)
  if (idx !== -1) projects.value[idx].sales_mode = mode
}

// 项目字段内联编辑保存
async function handleUpdateProjectField({ field, value }) {
  if (!selectedProject.value) return
  try {
    const res = await salesTwinApi.updateProject(selectedProject.value, {
      [field]: value,
      // INTENTIONAL: edit_reason 保持固定中文不翻译——该值持久化到数据库 StateChangeLog 审计日志，
      // 动态翻译会导致历史记录语言混杂，故作为系统级固定标识符
      edit_reason: '双击内联编辑',
    })
    // currentProject 是 computed（只读），更新 projects 数组中的对应项
    if (res.project) {
      const idx = projects.value.findIndex(p => p.id === selectedProject.value)
      if (idx !== -1) Object.assign(projects.value[idx], res.project)
    }
    // 销售阶段变更后联动刷新阶段交付物面板
    if (field === 'sales_stage') {
      await loadStageDeliverables(selectedProject.value)
      // 关单（赢单/丢单）时弹出关闭复盘
      if (value === 'closed_won' || value === 'closed_lost') {
        pendingCloseReview.value = { projectId: selectedProject.value, result: value }
      }
    }
  } catch (e) {
    console.error('保存项目字段失败:', e)
  }
}

// LLM 生成业务洞察后，后端已写库并返回最新 project，直接刷新本地 projects 数组
function handleRefreshProject(project) {
  if (!project?.id) return
  const idx = projects.value.findIndex(p => p.id === project.id)
  if (idx !== -1) {
    Object.assign(projects.value[idx], project)
  }
}

// OverviewPane 触发的阶段交付物重载（手工勾选/附件上传/附件删除后调用）
function handleReloadStageDeliverables() {
  if (!selectedProject.value) return
  loadStageDeliverables(selectedProject.value)
}

// Graph handlers 和 Stakeholder handlers 已移至 useSalesTwin composable 统一实现
async function handleStakeholderInlineUpdated(res) {
  if (!res?.stakeholder) return
  const updated = res.stakeholder
  const idx = stakeholders.value.findIndex(s => s.id === updated.id)
  if (idx >= 0) {
    stakeholders.value[idx] = updated
  }
  // 刷新状态日志，让交流历史与趋势图反映最新变更
  if (selectedProject.value) {
    try {
      const logsRes = await salesTwinApi.getStateLogs(selectedProject.value)
      stateLogs.value = logsRes.logs || []
    } catch (e) {
      console.warn('刷新状态日志失败:', e)
    }
  }
  // 刷新客户联系人列表的 linked 状态
  loadStakeholderLinkContacts()
}

// ============ 推演模拟 ============
// 启动闭门发酵推演
async function runSimulation() {
  if (!selectedProject.value) return
  if (runningSim.value) return
  runningSim.value = true
  fermentationResult.value = null
  try {
    const input = fermentationInput.value || {}
    const res = await salesTwinApi.simulateFermentation(
      selectedProject.value,
      3,
      input.initial_events || [],
      {
        mode: 'narrative',
        related_task_ids: input.related_task_ids || [],
        related_feedback_ids: input.related_feedback_ids || [],
        related_materials: input.related_materials || [],
      }
    )
    fermentationResult.value = res
  } catch (e) {
    console.error('推演失败:', e)
    showToast(t('toast.simulationFailed', { reason: e?.message || e }), 'error')
  } finally {
    runningSim.value = false
  }
}

// 重新推演：清空结果，恢复输入面板显示
function resetSimulation() {
  fermentationResult.value = null
  interviewResult.value = null
}

// 干系人访谈（基于当前推演上下文）
async function runInterview() {
  if (!selectedProject.value) return
  if (!interviewTargetId.value) {
    showToast(t('toast.selectInterviewTarget'), 'warning')
    return
  }
  if (!interviewQuestion.value || !interviewQuestion.value.trim()) {
    showToast(t('toast.inputInterviewQuestion'), 'warning')
    return
  }
  if (interviewing.value) return
  interviewing.value = true
  interviewResult.value = null
  try {
    const res = await salesTwinApi.interviewStakeholder(
      selectedProject.value,
      interviewTargetId.value,
      interviewQuestion.value.trim(),
      fermentationResult.value || null
    )
    interviewResult.value = res
    // 追加到访谈历史
    interviewHistory.value.push({
      stakeholder_id: interviewTargetId.value,
      question: interviewQuestion.value.trim(),
      answer: res?.answer || res?.response || '',
      timestamp: new Date().toISOString(),
    })
  } catch (e) {
    console.error('访谈失败:', e)
    showToast(t('toast.interviewFailed', { reason: e?.message || e }), 'error')
  } finally {
    interviewing.value = false
  }
}

// ============ 新建待办/预案 modal 提交 ============
async function handleCreateTask() {
  if (!selectedProject.value) return
  if (!newTask.value.title || !newTask.value.title.trim()) {
    showToast(t('toast.inputTaskTitle'), 'warning')
    return
  }
  try {
    await salesTwinApi.createTask(selectedProject.value, {
      title: newTask.value.title.trim(),
      description: newTask.value.description || '',
      priority: newTask.value.priority || 'medium',
      task_type: newTask.value.task_type || 'follow_up',
      stakeholder_id: newTask.value.stakeholder_id || null,
      stakeholder_ids: newTask.value.stakeholder_ids || [],
      due_date: newTask.value.due_date || '',
    })
    // 刷新待办列表
    const tasksRes = await salesTwinApi.getTasks(selectedProject.value)
    tasks.value = tasksRes.tasks || []
    // 重置表单
    newTask.value = { title: '', description: '', priority: 'medium', stakeholder_id: null, stakeholder_ids: [], task_type: 'follow_up', due_date: '' }
    showTaskModal.value = false
  } catch (e) {
    console.error('创建待办失败:', e)
    showToast(t('toast.createTaskFailed', { reason: e?.message || e }), 'error')
  }
}

async function handleCreatePlan() {
  if (!selectedProject.value) return
  if (!newPlan.value.stakeholder_id) {
    showToast(t('toast.selectTargetStakeholder'), 'warning')
    return
  }
  generatingPlan.value = true
  try {
    await salesTwinApi.createMeetingPlan(selectedProject.value, {
      stakeholder_id: newPlan.value.stakeholder_id,
      stakeholder_ids: newPlan.value.stakeholder_ids || [],
      meeting_purpose: newPlan.value.meeting_purpose || '',
      meeting_type: newPlan.value.meeting_type || t('workspace.meetingTypes.first_visit'),
      related_task_ids: newPlan.value.related_task_ids || [],
      related_materials: [],
      name: newPlan.value.name || '',
    })
    // 刷新预案列表
    const plansRes = await salesTwinApi.getMeetingPlans(selectedProject.value)
    meetingPlans.value = plansRes.plans || plansRes || []
    // 重置表单
    newPlan.value = { stakeholder_id: null, stakeholder_ids: [], meeting_purpose: '', meeting_type: t('workspace.meetingTypes.first_visit'), related_task_ids: [], name: '' }
    showPlanModal.value = false
  } catch (e) {
    console.error('生成预案失败:', e)
    showToast(t('toast.generatePlanFailed', { reason: e?.message || e }), 'error')
  } finally {
    generatingPlan.value = false
  }
}
</script>

<style>
@import '../styles/salesTwin.css';
</style>

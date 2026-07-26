<template>
  <div class="tab-pane workspace-tab-pane">
    <!-- 工作台子导航：5个路径按销售闭环顺序排列 -->
    <div class="workspace-subnav">
      <button
        :class="['ws-tab', { active: activeSubMenu === 'blindspot' }]"
        @click="$emit('navigate-to', 'blindspot')"
      >{{ t('workspace.blindSpotScan') }} <span class="ws-count">{{ sortedFindings.length || 0 }}</span></button>
      <span class="ws-arrow">→</span>
      <button
        :class="['ws-tab', { active: activeSubMenu === 'actions' }]"
        @click="$emit('navigate-to', 'actions')"
      >{{ t('workspace.actionSuggestions') }} <span class="ws-count">{{ nextActions?.recommended_actions?.length || 0 }}</span></button>
      <span class="ws-arrow">→</span>
      <button
        :class="['ws-tab', { active: activeSubMenu === 'tasks' }]"
        @click="$emit('navigate-to', 'tasks')"
      >{{ t('workspace.todoItems') }} <span class="ws-count">{{ tasks.filter(t => t.status === 'pending' || t.status === 'in_progress').length }}</span></button>
      <span class="ws-arrow">→</span>
      <button
        :class="['ws-tab', { active: activeSubMenu === 'meeting' }]"
        @click="$emit('navigate-to', 'meeting')"
      >{{ t('workspace.visitPlan') }} <span class="ws-count">{{ meetingPlans.filter(p => p.status === 'active' || p.status === 'pending' || p.status === 'generated').length }}</span></button>
      <span class="ws-arrow">→</span>
      <button
        :class="['ws-tab', { active: activeSubMenu === 'visit' }]"
        @click="$emit('navigate-to', 'visit')"
      >{{ t('workspace.visitRecords') }} <span class="ws-count">{{ feedbackRecords.length }}</span></button>
      <span class="ws-arrow">→</span>
      <button
        :class="['ws-tab', { active: activeSubMenu === 'teaching' }]"
        @click="$emit('navigate-to', 'teaching')"
      >{{ t('workspace.challengerTeaching') }}</button>
      <span class="ws-arrow">|</span>
      <!-- 项目健康度（随盲区扫描自动更新，点击展开详情） -->
      <div class="ws-winrate">
        <button type="button" class="ws-health-btn"
          :class="healthColor"
          @click="$emit('toggle-win-rate-panel')"
          :aria-expanded="showWinRatePanel"
          :aria-label="t('workspace.projectHealth')"
        >
          <span class="ws-health-label">{{ t('workspace.projectHealth') }}</span>
          <span v-if="blindSpots && typeof blindSpots.overall_score === 'number'" class="ws-health-num">{{ blindSpots.overall_score }}</span>
          <span v-else class="ws-health-num muted">--</span>
        </button>
        <!-- 项目健康度详情下拉面板 -->
        <div v-if="showWinRatePanel" class="ws-winrate-panel">
          <div v-if="blindSpots" class="ws-winrate-detail">
            <div class="ws-winrate-big" :class="healthColor">
              {{ blindSpots.overall_score ?? '--' }}<span class="metric-unit">/100</span>
            </div>
            <p v-if="blindSpots.summary" class="ws-winrate-analysis">{{ blindSpots.summary }}</p>
            <p v-if="sortedFindings.length" class="ws-winrate-row">
              <span class="ws-winrate-key">{{ t('workspace.riskFindings') }}</span>{{ t('workspace.itemsCount', { count: sortedFindings.length }) }}
            </p>
          </div>
          <div v-else class="ws-winrate-empty">
            <p>{{ t('workspace.scanFirst') }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- 商机里程碑条（OM10-OM70 + 销售模式，固定在工作台顶部，所有子页可见） -->
    <MilestonePanel
      :project-id="projectId"
      :sales-mode="salesMode"
      @sales-mode-changed="$emit('sales-mode-changed', $event)"
    />

    <!-- 工作台内容区：支持上下滚动 -->
    <div class="workspace-content">

    <!-- 子视图1：盲区扫描 -->
    <div v-if="activeSubMenu === 'blindspot'">
    <!-- 盲区扫描 -->
    <div class="analysis-section">
      <div class="section-header">
        <span class="section-deco">◇</span>
        <h3 class="section-title">{{ t('workspace.blindSpotScan') }}</h3>
        <span v-if="blindSpots && blindSpots.scanned_at" class="bs-last-scan">
          {{ t('workspace.lastScan') }} {{ formatScanTime(blindSpots.scanned_at) }}
          <span v-if="blindSpots.scan_source === 'cron'" class="bs-source-tag">{{ t('workspace.autoScan') }}</span>
          <span v-else-if="blindSpots.scan_source === 'manual'" class="bs-source-tag manual">{{ t('workspace.manualScan') }}</span>
        </span>
        <button type="button" class="btn-primary btn-sm" :disabled="scanningBlindSpots" @click="$emit('scan-blindspots')">
          <span v-if="scanningBlindSpots" class="btn-spinner" aria-hidden="true"></span>
          {{ scanningBlindSpots ? t('workspace.scanning') : (blindSpots ? t('workspace.rescan') : t('workspace.scanBlindSpots')) }}
        </button>
      </div>
      <!-- 盲区扫描结果 -->
      <div v-if="blindSpots && blindSpots.total_stakeholders > 0" class="blind-spots-container">
        <!-- 综合评分 -->
        <div class="bs-score-bar">
          <span class="bs-score-label">{{ t('workspace.graphHealth') }}</span>
          <div class="bs-score-track">
            <div class="bs-score-fill" :style="{ width: blindSpots.overall_score + '%' }"
              :class="{
                'score-danger': blindSpots.overall_score < 40,
                'score-warn': blindSpots.overall_score >= 40 && blindSpots.overall_score < 70,
                'score-ok': blindSpots.overall_score >= 70
              }"></div>
          </div>
          <span class="bs-score-num">{{ blindSpots.overall_score }}</span>
        </div>
        <p class="bs-summary">{{ blindSpots.summary }}</p>

        <!-- 盲区发现列表 -->
        <div v-if="sortedFindings.length > 0" class="bs-findings">
          <div v-for="(finding, idx) in sortedFindings" :key="idx" class="bs-finding-card" :class="finding.severity">
            <span class="bs-finding-dot" :class="finding.severity" aria-hidden="true"></span>
            <div class="bs-finding-body">
              <div class="bs-finding-top">
                <span class="bs-finding-cat">{{ finding.category }}</span>
                <span class="bs-finding-sev" :class="finding.severity">{{ severityLabels[finding.severity] || finding.severity }}</span>
              </div>
              <p class="bs-finding-title">{{ finding.title }}</p>
              <p class="bs-finding-desc">{{ finding.description }}</p>
              <p class="bs-finding-rec" v-if="finding.recommendation">→ {{ finding.recommendation }}</p>
            </div>
          </div>
        </div>
        <div v-else class="empty-inline">{{ t('workspace.noBlindSpots') }}</div>
        <!-- 一键生成行动建议 -->
        <div v-if="sortedFindings.length > 0" class="bs-action-bar">
          <button type="button" class="btn-primary btn-sm" @click="$emit('go-to-actions')">
            {{ t('workspace.generateActions') }} →
          </button>
        </div>
      </div>
      <div v-else-if="blindSpots" class="empty-inline">{{ t('workspace.noStakeholders') }}</div>
      <div v-else-if="scanningBlindSpots" class="empty-inline loading-hint">
        <span class="btn-spinner" aria-hidden="true"></span>
        {{ t('workspace.scanningHint') }}
      </div>
      <div v-else class="empty-inline">{{ t('workspace.clickToScan') }}</div>
    </div>
    </div><!-- /activeSubMenu=blindspot -->

    <!-- 子视图2：行动建议 -->
    <div v-if="activeSubMenu === 'actions'">
    <div class="analysis-section">
      <div class="section-header">
        <span class="section-deco">◇</span>
        <h3 class="section-title">{{ t('workspace.actionSuggestions') }}</h3>
        <div class="section-actions">
          <button
            :class="['filter-chip', { active: actionFilter === 'pending' }]"
            @click="$emit('update:actionFilter', 'pending')"
          >{{ t('workspace.actionPending') }} ({{ actionCounts.pending }})</button>
          <button
            :class="['filter-chip', { active: actionFilter === 'adopted' }]"
            @click="$emit('update:actionFilter', 'adopted')"
          >{{ t('workspace.adopted') }} ({{ actionCounts.adopted }})</button>
          <button
            :class="['filter-chip', { active: actionFilter === 'all' }]"
            @click="$emit('update:actionFilter', 'all')"
          >{{ t('common.all') }} ({{ actionCounts.all }})</button>
          <button type="button" class="btn-primary btn-sm" :disabled="generatingActions" @click="$emit('load-actions')">
            <span v-if="generatingActions" class="btn-spinner" aria-hidden="true"></span>
            {{ generatingActions ? t('common.generating') : t('workspace.generateSuggestions') }}
          </button>
        </div>
      </div>
      <p class="section-hint" v-if="generatingActions">
        <span class="btn-spinner" aria-hidden="true"></span>
        {{ t('workspace.generatingActionsHint') }}
      </p>
      <p class="section-hint" v-else-if="nextActions?.recommended_actions?.length">
        {{ t('workspace.actionsExistHint', { count: nextActions.recommended_actions.length }) }}
      </p>
      <div v-if="filteredActions.length" class="actions-list">
        <div v-for="(action, idx) in filteredActions" :key="idx" class="action-card" :class="{ adopted: isActionAdopted(action) }">
          <div class="action-top">
            <span class="priority-tag" :class="'p' + action.priority">P{{ action.priority }}</span>
            <span class="action-target">{{ action.target_stakeholder || t('workspace.generic') }}</span>
            <span v-if="action.urgency" class="action-urgency" :class="action.urgency">{{ t('workspace.urgencyLabels.' + action.urgency) }}</span>
            <span v-if="isActionAdopted(action)" class="adopted-tag">{{ t('workspace.adopted') }}</span>
          </div>
          <input
            v-if="action.editing"
            :value="action.title"
            @input="action.title = $event.target.value"
            class="action-title-input"
            :placeholder="t('workspace.actionTitle')"
          />
          <h4 v-else class="action-title">{{ action.title }}</h4>
          <textarea
            v-if="action.editing"
            :value="action.description"
            @input="action.description = $event.target.value"
            class="action-desc-input"
            rows="3"
            :placeholder="t('workspace.actionDescription')"
          ></textarea>
          <p v-else class="action-desc">{{ action.description }}</p>
          <div v-if="action.reasoning && !action.editing" class="action-reasoning">
            <span class="reasoning-label">{{ t('workspace.why') }}</span>
            <span>{{ action.reasoning }}</span>
          </div>
          <div v-if="action.action_brief && !action.editing" class="action-brief">
            <span class="brief-label">{{ t('workspace.visitBrief') }}</span>
            <p><span class="brief-key">{{ t('workspace.painPointStatement') }}</span>{{ action.action_brief.pain_point_statement }}</p>
            <p><span class="brief-key">{{ t('workspace.insightChallenge') }}</span>{{ action.action_brief.insight_challenge }}</p>
            <p><span class="brief-key">{{ t('workspace.solutionIntro') }}</span>{{ action.action_brief.solution_intro }}</p>
          </div>
          <div class="action-footer">
            <button type="button" v-if="!action.editing" class="btn-link" @click="action.editing = true">{{ t('common.edit') }}</button>
            <button type="button" v-if="action.editing" class="btn-link" @click="action.editing = false">{{ t('common.done') }}</button>
            <button type="button" v-if="!isActionAdopted(action)" class="btn-primary btn-sm"
              @click="$emit('adopt-action', action)"
            >
              {{ t('workspace.adoptAsTask') }}
            </button>
            <!-- 自进化引擎：拒绝反馈 -->
            <div v-if="!isActionAdopted(action) && action.recommendation_id" class="reject-dropdown">
              <button type="button" class="btn-ghost btn-sm" @click="action.showReject = !action.showReject">{{ t('workspace.notApplicable') }}</button>
              <ul v-if="action.showReject" class="reject-menu">
                <li @click="$emit('reject-action', action, 'insufficientInfo')">{{ t('workspace.rejectReasons.insufficientInfo') }}</li>
                <li @click="$emit('reject-action', action, 'badTiming')">{{ t('workspace.rejectReasons.badTiming') }}</li>
                <li @click="$emit('reject-action', action, 'notFit')">{{ t('workspace.rejectReasons.notFit') }}</li>
                <li @click="$emit('reject-action', action, 'alreadyDone')">{{ t('workspace.rejectReasons.alreadyDone') }}</li>
              </ul>
            </div>
            <span v-if="isActionAdopted(action)" class="adopted-status">{{ t('workspace.adopted') }}</span>
            <button v-if="isActionAdopted(action)" type="button" class="btn-link" @click="$emit('view-adopted-task', action)">{{ t('workspace.viewTask') }} →</button>
            <span v-if="action.rejected" class="rejected-status">{{ t('workspace.rejected') }}</span>
          </div>
        </div>
      </div>
      <div v-else-if="nextActions?.recommended_actions?.length" class="empty-inline">
        {{ t('workspace.noActionsInFilter', { reason: actionFilter === 'pending' ? t('workspace.allActionsAdopted') : t('workspace.noAdoptedActions') }) }}
      </div>
      <div v-else class="empty-inline">{{ t('workspace.noSuggestions') }}</div>
    </div>
    </div><!-- /activeSubMenu=actions -->

    <!-- 子视图3：待办事项（左右栏：左侧列表，右侧详情） -->
    <div v-if="activeSubMenu === 'tasks'">
    <div class="section-header">
      <span class="section-deco">◇</span>
      <h3 class="section-title">{{ t('workspace.todoItems') }}</h3>
      <div class="section-actions">
        <button
          v-for="opt in ['pending','in_progress','all','completed','cancelled']"
          :key="opt"
          :class="['filter-chip', { active: taskFilter === opt }]"
          @click="$emit('update:taskFilter', opt)"
        >{{ opt === 'all' ? t('common.all') : taskStatusLabels[opt] }} ({{ opt === 'all' ? tasks.length : tasks.filter(t => t.status === opt).length }})</button>
        <button type="button" class="btn-link" :disabled="sortingTasks" @click="$emit('auto-sort-tasks')">
          <span v-if="sortingTasks" class="btn-spinner" aria-hidden="true"></span>
          {{ sortingTasks ? t('workspace.sorting') : t('workspace.autoSort') }}
        </button>
        <button type="button" class="btn-primary btn-sm" @click="$emit('open-task-modal')">
          <span class="btn-plus">+</span> {{ t('workspace.createTask') }}
        </button>
      </div>
    </div>
    <p class="section-hint" v-if="taskSortSuggestions?.length">
      {{ t('workspace.taskSortHint', { count: taskSortSuggestions.length }) }}
      <button type="button" class="btn-link" @click="$emit('apply-task-sort')" style="margin-left:8px">{{ t('workspace.applySort') }}</button>
      <button type="button" class="btn-link" @click="$emit('clear-sort-suggestions')" style="margin-left:4px">{{ t('workspace.ignore') }}</button>
    </p>

    <div v-if="filteredTasks.length" class="plan-split-layout">
      <!-- 左栏：待办列表 -->
      <aside class="plan-list-pane">
        <div
          v-for="task in filteredTasks"
          :key="task.id"
          :class="['plan-list-item', 'task-list-item', { selected: selectedTask && selectedTask.id === task.id }]"
          role="button"
          tabindex="0"
          @click="$emit('select-task', task)"
          @keydown.enter="$emit('select-task', task)"
          @keydown.space.prevent="$emit('select-task', task)"
          :aria-label="t('workspace.viewTaskAria', { name: task.title })"
        >
          <div class="plan-list-top">
            <span class="task-type-tag">{{ taskTypeLabels[task.task_type] || task.task_type }}</span>
            <span class="priority-tag" :class="task.priority">{{ priorityLabels[task.priority] }}</span>
            <span class="task-status" :class="taskStatusClasses[task.status]">{{ taskStatusLabels[task.status] }}</span>
            <span v-if="getSortSuggestion(task.id)" class="sort-tag" :title="getSortSuggestion(task.id).reason">
              {{ t('workspace.suggestedPrefix') }}{{ priorityLabels[getSortSuggestion(task.id).suggested_priority] || getSortSuggestion(task.id).suggested_priority }}
            </span>
          </div>
          <h4 class="plan-list-name">{{ task.title }}</h4>
          <p v-if="task.description" class="plan-list-purpose">{{ task.description.substring(0, 80) }}{{ task.description.length > 80 ? '…' : '' }}</p>
          <div class="plan-list-meta">
            <span v-if="task.stakeholder_name" class="meta-item"><span class="meta-icon">▤</span>{{ task.stakeholder_name }}</span>
            <span v-if="task.due_date" class="meta-item"><span class="meta-icon">◷</span>{{ formatDate(task.due_date) }}</span>
            <span v-if="task.source === 'recommended_action'" class="meta-item source-tag">{{ taskSourceLabels[task.source] }}</span>
          </div>
        </div>
      </aside>

      <!-- 右栏：待办详情 -->
      <section class="plan-detail-pane">
        <div v-if="!selectedTask" class="empty-inline">{{ t('workspace.selectTaskHint') }}</div>
        <div v-else class="plan-detail-content">
          <div class="plan-detail-header">
            <div class="plan-detail-title-row">
              <h3 class="plan-detail-title">{{ selectedTask.title }}</h3>
              <div class="plan-detail-actions">
                <button type="button" class="btn-link" @click="$emit('start-inline-edit-task')">{{ t('common.edit') }}</button>
                <button type="button" class="btn-link danger" @click="$emit('remove-task', selectedTask)">{{ t('common.delete') }}</button>
              </div>
            </div>
            <div class="plan-detail-meta">
              <span class="meta-item"><span class="meta-icon">◇</span>{{ taskTypeLabels[selectedTask.task_type] || selectedTask.task_type }}</span>
              <span class="meta-item"><span class="meta-icon">▤</span>{{ (selectedTask.stakeholder_names && selectedTask.stakeholder_names.length) ? selectedTask.stakeholder_names.join('、') : (selectedTask.stakeholder_name || t('workspace.generic')) }}</span>
              <span class="meta-item"><span class="meta-icon">◷</span>{{ selectedTask.due_date ? formatDate(selectedTask.due_date) : t('workspace.noDueDate') }}</span>
              <span v-if="selectedTask.completed_at" class="meta-item"><span class="meta-icon">✓</span>{{ t('workspace.completedAt', { date: formatDate(selectedTask.completed_at) }) }}</span>
            </div>
            <div class="task-detail-tags">
              <span class="priority-tag" :class="selectedTask.priority">{{ t('workspace.priorityWithTag', { label: priorityLabels[selectedTask.priority] }) }}</span>
              <span class="task-status" :class="taskStatusClasses[selectedTask.status]">{{ taskStatusLabels[selectedTask.status] }}</span>
              <span v-if="selectedTask.source === 'recommended_action'" class="source-tag">{{ taskSourceLabels[selectedTask.source] }}</span>
              <span v-if="getSortSuggestion(selectedTask.id)" class="sort-tag" :title="getSortSuggestion(selectedTask.id).reason">
                {{ t('workspace.suggestedSortPrefix') }}{{ priorityLabels[getSortSuggestion(selectedTask.id).suggested_priority] || getSortSuggestion(selectedTask.id).suggested_priority }}
                <span v-if="getSortSuggestion(selectedTask.id).suggested_due_date">· {{ getSortSuggestion(selectedTask.id).suggested_due_date }}</span>
              </span>
            </div>
          </div>

          <!-- 内联编辑表单 -->
          <div v-if="editingTaskInline" class="plan-edit-form">
            <div class="form-group">
              <label class="field-label" for="edit-task-title">{{ t('workspace.taskTitle') }}</label>
              <input id="edit-task-title" type="text" v-model="taskEditForm.title" class="form-input" autocomplete="off">
            </div>
            <div class="form-group">
              <label class="field-label" for="edit-task-desc">{{ t('workspace.taskDescription') }}</label>
              <textarea id="edit-task-desc" v-model="taskEditForm.description" rows="3" class="form-input"></textarea>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label class="field-label" for="edit-task-priority">{{ t('common.priority') }}</label>
                <select id="edit-task-priority" v-model="taskEditForm.priority" class="form-input">
                  <option value="high">{{ t('workspace.priorityLabels.high') }}</option>
                  <option value="medium">{{ t('workspace.priorityLabels.medium') }}</option>
                  <option value="low">{{ t('workspace.priorityLabels.low') }}</option>
                </select>
              </div>
              <div class="form-group">
                <label class="field-label" for="edit-task-type">{{ t('workspace.taskType') }}</label>
                <select id="edit-task-type" v-model="taskEditForm.task_type" class="form-input">
                  <option value="blind_spot">{{ t('workspace.taskTypes.blind_spot') }}</option>
                  <option value="address_concerns">{{ t('workspace.taskTypes.address_concerns') }}</option>
                  <option value="build_alliance">{{ t('workspace.taskTypes.build_alliance') }}</option>
                  <option value="provide_material">{{ t('workspace.taskTypes.provide_material') }}</option>
                  <option value="meeting">{{ t('workspace.taskTypes.meeting') }}</option>
                  <option value="follow_up">{{ t('workspace.taskTypes.follow_up') }}</option>
                </select>
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label class="field-label">{{ t('workspace.relatedStakeholdersMulti') }}</label>
                <div class="stakeholder-checkbox-list">
                  <label v-for="s in stakeholders" :key="s.id" class="stakeholder-checkbox">
                    <input
                      type="checkbox"
                      :value="s.id"
                      v-model="taskEditForm.stakeholder_ids"
                      :aria-label="t('workspace.relatedStakeholderAria', { name: s.name })"
                    >
                    <span>{{ s.name }}</span>
                  </label>
                  <span v-if="!stakeholders.length" class="form-hint">{{ t('stakeholder.noStakeholders') }}</span>
                </div>
              </div>
              <div class="form-group">
                <label class="field-label" for="edit-task-due">{{ t('workspace.dueDate') }}</label>
                <input id="edit-task-due" type="date" v-model="taskEditForm.due_date" class="form-input">
              </div>
            </div>
            <div class="task-actions">
              <button type="button" class="btn-primary btn-sm" @click="$emit('submit-inline-edit-task')">{{ t('common.save') }}</button>
              <button type="button" class="btn-link" @click="$emit('cancel-inline-edit')">{{ t('common.cancel') }}</button>
            </div>
          </div>

          <!-- 详情展示 -->
          <div v-else class="task-detail-body">
            <div v-if="selectedTask.description" class="plan-block">
              <h4>{{ t('workspace.taskDescription') }}</h4>
              <p class="task-detail-desc">{{ selectedTask.description }}</p>
            </div>
            <div v-if="selectedTask.completion_note" class="plan-block">
              <h4>{{ t('workspace.completionNote') }}</h4>
              <p>{{ selectedTask.completion_note }}</p>
            </div>
            <div v-if="selectedTask.action_brief" class="plan-block">
              <h4>{{ t('workspace.visitBrief') }}</h4>
              <div v-if="typeof selectedTask.action_brief === 'object'">
                <p v-if="selectedTask.action_brief.pain_point_statement"><span class="brief-key">{{ t('workspace.painPointStatement') }}</span>{{ selectedTask.action_brief.pain_point_statement }}</p>
                <p v-if="selectedTask.action_brief.insight_challenge"><span class="brief-key">{{ t('workspace.insightChallenge') }}</span>{{ selectedTask.action_brief.insight_challenge }}</p>
                <p v-if="selectedTask.action_brief.solution_intro"><span class="brief-key">{{ t('workspace.solutionIntro') }}</span>{{ selectedTask.action_brief.solution_intro }}</p>
              </div>
              <p v-else>{{ selectedTask.action_brief }}</p>
            </div>
            <div v-if="selectedTask.source_action && selectedTask.source_action.reasoning" class="plan-block">
              <h4>{{ t('workspace.adoptionReason') }}</h4>
              <p>{{ selectedTask.source_action.reasoning }}</p>
            </div>
            <div v-if="selectedTask.source_action && selectedTask.source_action.merged_from?.length" class="plan-block">
              <h4>{{ t('workspace.mergedSuggestions', { count: selectedTask.source_action.merged_from.length }) }}</h4>
              <ul class="merged-from-list">
                <li v-for="(m, i) in selectedTask.source_action.merged_from" :key="i">
                  <strong>{{ m.original_title }}</strong>
                  <span v-if="m.reason"> — {{ m.reason }}</span>
                </li>
              </ul>
            </div>

            <!-- 状态变更 -->
            <div class="plan-block">
              <h4>{{ t('common.status') }}</h4>
              <div class="task-status-row">
                <select
                  v-if="selectedTask.status !== 'completed'"
                  class="task-status-select"
                  :value="selectedTask.status"
                  @change="$emit('change-task-status', selectedTask, $event.target.value)"
                >
                  <option value="pending">{{ t('workspace.taskStatus.pending') }}</option>
                  <option value="in_progress">{{ t('workspace.taskStatus.in_progress') }}</option>
                  <option value="completed">{{ t('workspace.markAsComplete') }}</option>
                  <option value="cancelled">{{ t('workspace.taskStatus.cancelled') }}</option>
                </select>
                <span v-else class="task-status" :class="taskStatusClasses.completed">{{ t('workspace.taskStatus.completed') }}</span>
              </div>
            </div>

            <!-- 关联拜访记录及产生的影响 -->
            <div v-if="taskFeedbackRecords(selectedTask).length" class="plan-block">
              <h4>{{ t('workspace.relatedVisitRecords', { count: taskFeedbackRecords(selectedTask).length }) }}</h4>
              <div
                v-for="fr in taskFeedbackRecords(selectedTask)"
                :key="fr.id"
                class="task-feedback-item"
              >
                <div class="task-feedback-top">
                  <span class="task-feedback-time">{{ formatDate(fr.created_at) }}</span>
                  <span v-if="fr.total_changes" class="task-feedback-changes">{{ t('workspace.itemsAffected', { count: fr.total_changes }) }}</span>
                  <button type="button" class="btn-link btn-tiny" @click="$emit('view-feedback-in-visit', fr)">{{ t('workspace.viewFull') }} →</button>
                </div>
                <p class="task-feedback-text">{{ (fr.feedback_text || '').substring(0, 120) }}{{ (fr.feedback_text || '').length > 120 ? '…' : '' }}</p>
                <p v-if="fr.parse_summary" class="task-feedback-impact"><span class="impact-label">{{ t('workspace.impactSummary') }}</span>{{ fr.parse_summary }}</p>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
    <div v-else class="empty-state">
      <div class="empty-icon">☑</div>
      <p class="empty-text">{{ t('workspace.noTodoItems', { filter: taskFilter === 'all' ? '' : taskStatusLabels[taskFilter] }) }}</p>
      <p class="empty-hint">{{ t('workspace.noTodoItemsHint') }}</p>
    </div>
    </div><!-- /activeSubMenu=tasks -->

    <!-- 子视图4：拜访预案（左右栏：左侧列表，右侧详情，默认显示活动任务预案） -->
    <div v-if="activeSubMenu === 'meeting'">
    <div class="section-header">
      <span class="section-deco">◇</span>
      <h3 class="section-title">{{ t('workspace.visitPlan') }}</h3>
      <div class="section-actions">
        <button
          :class="['filter-chip', { active: planFilter === 'active' }]"
          @click="$emit('update:planFilter', 'active')"
        >{{ t('workspace.planFilterActive') }} ({{ activeMeetingPlans.length }})</button>
        <button
          :class="['filter-chip', { active: planFilter === 'completed' }]"
          @click="$emit('update:planFilter', 'completed')"
        >{{ t('workspace.planFilterCompleted') }} ({{ completedMeetingPlans.length }})</button>
        <button
          :class="['filter-chip', { active: planFilter === 'all' }]"
          @click="$emit('update:planFilter', 'all')"
        >{{ t('common.all') }} ({{ meetingPlans.length }})</button>
        <button type="button" class="btn-primary btn-sm" @click="$emit('open-plan-modal')">
          <span class="btn-plus">+</span> {{ t('workspace.generatePlan') }}
        </button>
      </div>
    </div>

    <div v-if="displayedMeetingPlans.length" class="plan-split-layout">
      <!-- 左栏：预案列表 -->
      <aside class="plan-list-pane">
        <div
          v-for="plan in displayedMeetingPlans"
          :key="plan.id"
          :class="['plan-list-item', { selected: selectedPlan && selectedPlan.id === plan.id }]"
          role="button"
          tabindex="0"
          @click="$emit('view-plan', plan)"
          @keydown.enter="$emit('view-plan', plan)"
          @keydown.space.prevent="$emit('view-plan', plan)"
          :aria-label="t('workspace.viewPlanAria', { name: plan.name })"
        >
          <div class="plan-list-top">
            <span class="plan-type">{{ meetingTypeLabel(plan.meeting_type) }}</span>
            <span class="plan-status" :class="plan.status">{{ planStatusLabels[plan.status] || plan.status }}</span>
          </div>
          <h4 class="plan-list-name">{{ plan.name }}</h4>
          <p class="plan-list-purpose">{{ plan.meeting_purpose }}</p>
          <div class="plan-list-meta">
            <span class="meta-item"><span class="meta-icon" aria-hidden="true">▤</span>{{ plan.stakeholder_name }}</span>
            <span class="meta-item"><span class="meta-icon" aria-hidden="true">◷</span>{{ formatDate(plan.created_at) }}</span>
          </div>
        </div>
      </aside>

      <!-- 右栏：预案详情（非弹出式） -->
      <section class="plan-detail-pane">
        <div v-if="!selectedPlan" class="empty-inline">{{ t('workspace.selectPlanHint') }}</div>
        <div v-else class="plan-detail-content">
          <div class="plan-detail-header">
            <div class="plan-detail-title-row">
              <h3 class="plan-detail-title">{{ selectedPlan.name }}</h3>
              <div class="plan-detail-actions">
                <button type="button" class="btn-link" @click="$emit('open-edit-plan', selectedPlan)">{{ t('common.edit') }}</button>
                <button type="button" class="btn-link danger" @click="$emit('remove-plan', selectedPlan)">{{ t('common.delete') }}</button>
              </div>
            </div>
            <div class="plan-detail-meta">
              <span class="meta-item"><span class="meta-icon">▤</span>{{ (selectedPlan.stakeholder_names && selectedPlan.stakeholder_names.length) ? selectedPlan.stakeholder_names.join('、') : selectedPlan.stakeholder_name }}</span>
              <span class="meta-item"><span class="meta-icon">◇</span>{{ meetingTypeLabel(selectedPlan.meeting_type) }}</span>
              <span class="meta-item"><span class="meta-icon">◷</span>{{ formatDate(selectedPlan.created_at) }}</span>
            </div>
            <p class="plan-detail-purpose"><strong>{{ t('workspace.meetingPurpose') }}：</strong>{{ selectedPlan.meeting_purpose }}</p>
          </div>

          <div v-if="editingPlan" class="plan-edit-form">
            <div class="form-row">
              <div class="form-group">
                <label class="field-label" for="edit-plan-stakeholder">{{ t('workspace.primaryStakeholder') }} *</label>
                <select id="edit-plan-stakeholder" v-model="planEditForm.stakeholder_id" class="form-input">
                  <option v-for="sh in stakeholders" :key="sh.id" :value="sh.id">
                    {{ sh.name }}{{ sh.position ? ' - ' + sh.position : '' }}
                  </option>
                </select>
              </div>
              <div class="form-group">
                <label class="field-label" for="edit-plan-type">{{ t('workspace.meetingType') }}</label>
                <select id="edit-plan-type" v-model="planEditForm.meeting_type" class="form-input">
                  <option value="first_visit">{{ t('workspace.meetingTypes.first_visit') }}</option>
                  <option value="proposal_report">{{ t('workspace.meetingTypes.proposal_report') }}</option>
                  <option value="objection_handling">{{ t('workspace.meetingTypes.objection_handling') }}</option>
                  <option value="relationship_maintenance">{{ t('workspace.meetingTypes.relationship_maintenance') }}</option>
                </select>
              </div>
            </div>
            <div class="form-group">
              <label class="field-label" for="edit-plan-name">{{ t('workspace.planName') }}</label>
              <input id="edit-plan-name" type="text" v-model="planEditForm.name" class="form-input" autocomplete="off">
            </div>
            <div class="form-group">
              <label class="field-label">{{ t('workspace.otherStakeholdersMulti') }}</label>
              <div class="chip-list">
                <label v-for="sh in stakeholders.filter(s => s.id !== planEditForm.stakeholder_id)" :key="sh.id" class="chip-item">
                  <input type="checkbox" :value="sh.id" v-model="planEditForm.stakeholder_ids">
                  <span>{{ sh.name }}</span>
                </label>
              </div>
            </div>
            <div class="form-group">
              <label class="field-label" for="edit-plan-purpose">{{ t('workspace.meetingPurpose') }} *</label>
              <textarea id="edit-plan-purpose" v-model="planEditForm.meeting_purpose" rows="2" class="form-input"></textarea>
            </div>
            <div v-if="tasks.length > 0" class="form-group">
              <label class="field-label">{{ t('workspace.relatedTasksAsTopics') }}</label>
              <div class="chip-list">
                <label v-for="task in tasks.filter(t => t.status !== 'cancelled')" :key="task.id" class="chip-item">
                  <input type="checkbox" :value="task.id" v-model="planEditForm.related_task_ids">
                  <span>{{ task.title }}</span>
                </label>
              </div>
            </div>
            <div class="task-actions">
              <button type="button" class="btn-primary btn-sm" @click="$emit('submit-plan-edit')">{{ t('common.save') }}</button>
              <button type="button" class="btn-link" @click="$emit('cancel-plan-edit')">{{ t('common.cancel') }}</button>
            </div>
          </div>

          <div v-else-if="selectedPlan.plan_content" class="plan-content">
            <div class="plan-block">
              <h4>{{ t('workspace.opening') }}</h4>
              <p>{{ selectedPlan.plan_content.opening }}</p>
            </div>
            <div class="plan-block">
              <h4>{{ t('workspace.keyTopics') }}</h4>
              <ul>
                <li v-for="(topic, i) in selectedPlan.plan_content.key_topics" :key="i">{{ topic }}</li>
              </ul>
            </div>
            <div v-if="selectedPlan.plan_content.expected_objections?.length" class="plan-block">
              <h4>{{ t('workspace.expectedObjections') }}</h4>
              <div v-for="(obj, i) in selectedPlan.plan_content.expected_objections" :key="i" class="objection-item">
                <p><strong>{{ t('workspace.objection') }}：</strong>{{ obj.objection }}</p>
                <p><strong>{{ t('workspace.underlyingConcern') }}：</strong>{{ obj.underlying_concern }}</p>
                <p><strong>{{ t('workspace.response') }}：</strong>{{ obj.response }}</p>
              </div>
            </div>
            <div v-if="selectedPlan.plan_content.response_strategies?.length" class="plan-block">
              <h4>{{ t('workspace.responseStrategies') }}</h4>
              <div v-for="(s, i) in selectedPlan.plan_content.response_strategies" :key="i" class="strategy-item">
                <p><strong>{{ s.strategy }}</strong>：{{ s.tactic }}</p>
                <p class="muted">{{ s.talking_points }}</p>
              </div>
            </div>
            <div class="plan-block">
              <h4>{{ t('workspace.successCriteria') }}</h4>
              <p>{{ selectedPlan.plan_content.success_criteria }}</p>
            </div>
            <div v-if="selectedPlan.plan_content.follow_up_actions?.length" class="plan-block">
              <h4>{{ t('workspace.followUpActions') }}</h4>
              <ul>
                <li v-for="(a, i) in selectedPlan.plan_content.follow_up_actions" :key="i">{{ a }}</li>
              </ul>
            </div>
            <div v-if="selectedPlan.plan_content.risk_warnings?.length" class="plan-block warning">
              <h4>{{ t('workspace.riskWarnings') }}</h4>
              <ul>
                <li v-for="(r, i) in selectedPlan.plan_content.risk_warnings" :key="i">{{ r }}</li>
              </ul>
            </div>
          </div>
          <div v-else class="empty-inline">{{ t('workspace.noPlanContent') }}</div>
        </div>
      </section>
    </div>
    <div v-else class="empty-state">
      <div class="empty-icon">◈</div>
      <p class="empty-text">{{ t('workspace.noPlans') }}</p>
      <p class="empty-hint">{{ t('workspace.noPlansHint') }}</p>
    </div>
    </div><!-- /activeSubMenu=meeting -->

    <!-- 子视图5：拜访记录（原反馈录入） -->
    <div v-if="activeSubMenu === 'visit'">
      <div class="feedback-grid">
        <!-- 左列：拜访记录录入 -->
        <section class="feedback-section" aria-labelledby="fb-input-title">
          <div class="section-header">
            <span class="section-deco">◇</span>
            <h3 id="fb-input-title" class="section-title">{{ t('workspace.visitRecordInput') }}</h3>
          </div>

        <!-- 关联待办事项选择 -->
        <div v-if="tasks.length > 0" class="feedback-related-tasks">
          <span class="field-label">{{ t('workspace.relatedTasksOptionalHint') }}</span>
          <div class="task-checkbox-list">
            <label
              v-for="task in tasks.filter(t => t.status !== 'completed' && t.status !== 'cancelled')"
              :key="task.id"
              class="task-checkbox"
            >
              <input
                type="checkbox"
                :value="task.id"
                :checked="feedbackRelatedTaskIds && feedbackRelatedTaskIds.includes(task.id)"
                @change="toggleFeedbackTaskId(task.id, $event.target.checked)"
              >
              <span>{{ task.title }}</span>
            </label>
          </div>
        </div>

        <!-- 关联拜访预案选择 -->
        <div v-if="meetingPlans.length > 0" class="feedback-related-tasks">
          <label class="field-label" for="feedback-plan-select">{{ t('workspace.relatedPlanOptionalHint') }}</label>
          <select
            id="feedback-plan-select"
            :value="feedbackRelatedPlanId"
            @change="$emit('update:feedbackRelatedPlanId', $event.target.value ? Number($event.target.value) : null)"
            class="plan-select"
          >
            <option :value="null">{{ t('workspace.noRelatedPlan') }}</option>
            <option v-for="plan in meetingPlans" :key="plan.id" :value="plan.id">
              {{ plan.name }}（{{ meetingTypeLabel(plan.meeting_type) }}）· {{ formatDate(plan.created_at) }}
            </option>
          </select>
        </div>

        <label class="sr-only" for="feedback-text">{{ t('workspace.visitRecordContent') }}</label>
        <textarea
          id="feedback-text"
          :value="feedbackText"
          @input="$emit('update:feedbackText', $event.target.value)"
          class="feedback-input"
          :placeholder="t('workspace.visitRecordPlaceholder')"
          rows="6"
          aria-describedby="fb-help"
        ></textarea>
        <p id="fb-help" class="field-hint">{{ t('workspace.visitRecordHint') }}</p>

        <!-- 附件上传（作为提交解析的输入之一） -->
        <div class="feedback-attachments-input">
          <label class="field-label" for="feedback-file-input">
            <span class="attach-label-text">{{ t('workspace.attachmentsHint') }}</span>
          </label>
          <input
            id="feedback-file-input"
            ref="feedbackFileInput"
            type="file"
            multiple
            class="sr-only"
            @change="$emit('feedback-file-select', $event)"
            accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.md,.png,.jpg,.jpeg,.gif,.zip,.rar"
          >
          <button
            type="button"
            class="btn-secondary btn-sm"
            @click="$refs.feedbackFileInput?.click()"
          >
            + {{ t('workspace.selectFile') }}
          </button>
          <div v-if="feedbackAttachments && feedbackAttachments.length" class="attach-chip-list">
            <span v-for="(f, i) in feedbackAttachments" :key="i" class="attach-chip">
              <span class="attach-chip-name" :title="f.name">{{ f.name }}</span>
              <span class="attach-chip-size">{{ formatFileSize(f.size) }}</span>
              <button
                type="button"
                class="attach-chip-remove"
                @click="$emit('remove-attachment', i)"
                :aria-label="t('workspace.removeAttachmentAria', { name: f.name })"
              >×</button>
            </span>
          </div>
        </div>

        <div class="feedback-actions">
          <button
            type="button"
            class="btn-primary"
            @click="$emit('submit-feedback')"
            :disabled="!feedbackText || !feedbackText.trim()"
          >
            {{ t('workspace.submitParse') }}
          </button>
        </div>
        <div v-if="feedbackResult" class="feedback-result" aria-live="polite">
          <span class="brief-label">{{ t('workspace.feedbackResult') }}</span>
          <p class="feedback-summary">{{ feedbackResult.summary || t('workspace.noUpdatesDetected') }}</p>
          <p class="feedback-changes">{{ t('workspace.totalUpdates', { count: feedbackResult.total_changes || 0 }) }}</p>
          <div v-if="feedbackResult.task_updates?.length" class="task-updates">
            <span class="brief-label">{{ t('workspace.taskStatusUpdates') }}</span>
            <div v-for="(tu, i) in feedbackResult.task_updates" :key="i" class="task-update-item">
              <span class="task-update-title">{{ tu.title }}</span>
              <span class="task-update-status">
                {{ taskStatusLabels[tu.old_status] }} → {{ taskStatusLabels[tu.new_status] }}
              </span>
            </div>
          </div>
        </div>
        </section>

        <!-- 右列：历史记录（点击查看完整会议记录） -->
        <aside class="feedback-side">
          <div v-if="feedbackRecords.length" class="feedback-records-section">
            <div class="section-header">
              <span class="section-deco">◇</span>
              <h3 class="section-title">{{ t('workspace.historyRecords', { count: feedbackRecords.length }) }}</h3>
            </div>
            <div class="feedback-record-list">
              <div
                v-for="record in displayedFeedbackRecords"
                :key="record.id"
                :class="['feedback-record-item', { clickable: true, expanded: expandedRecordId === record.id }]"
                role="button"
                tabindex="0"
                @click="$emit('toggle-record-expand', record)"
                @keydown.enter="$emit('toggle-record-expand', record)"
              >
                <div class="record-top">
                  <span class="record-time">{{ formatDate(record.created_at) }}</span>
                  <span v-if="record.total_changes" class="record-changes">{{ t('workspace.changesCount', { count: record.total_changes }) }}</span>
                </div>
                <p v-if="expandedRecordId === record.id" class="record-text record-full">{{ record.feedback_text }}</p>
                <p v-else class="record-text">{{ record.feedback_text.substring(0, 150) }}{{ record.feedback_text.length > 150 ? '…' : '' }}</p>
                <p v-if="record.parse_summary" class="record-summary">{{ record.parse_summary }}</p>
                <!-- 展开时显示录入时上传的附件（只读，不可上传） -->
                <div v-if="expandedRecordId === record.id && record.attachments && record.attachments.length" class="record-attachments" @click.stop>
                  <span class="brief-label">{{ t('workspace.attachmentsCount', { count: record.attachments.length }) }}</span>
                  <div class="attachment-list">
                    <div v-for="att in record.attachments" :key="att.filename" class="attachment-item">
                      <a
                        :href="feedbackAttachmentUrl(record.id, att.filename)"
                        :download="att.original_filename"
                        class="attachment-link"
                        :title="t('workspace.downloadAria', { name: att.original_filename })"
                      >
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/></svg>
                        <span class="attachment-name">{{ att.original_filename }}</span>
                        <span class="attachment-size">({{ formatFileSize(att.size) }})</span>
                      </a>
                    </div>
                  </div>
                </div>
              </div>
              <button
                v-if="feedbackRecords.length > 5"
                type="button"
                class="feedback-record-more"
                @click="$emit('toggle-show-all-feedback')"
              >
                {{ showAllFeedbackRecords ? t('workspace.collapseAll') : t('workspace.expandAll', { count: feedbackRecords.length }) }}
              </button>
            </div>
          </div>
        </aside>
      </div>
    </div><!-- /activeSubMenu=visit -->

    <!-- 子视图6：商业指导（Challenger 话术） -->
    <div v-if="activeSubMenu === 'teaching'">
      <ChallengerTeachingPanel
        :project-id="projectId"
        :stakeholders="stakeholders"
      />
    </div><!-- /activeSubMenu=teaching -->

    </div><!-- /.workspace-content -->
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { formatDate, formatFileSize } from '../../composables/salesTwin/formatters.js'
import MilestonePanel from './MilestonePanel.vue'
import ChallengerTeachingPanel from './ChallengerTeachingPanel.vue'

const { t } = useI18n()

const emit = defineEmits([
  'navigate-to',
  'toggle-win-rate-panel',
  'scan-blindspots',
  'go-to-actions',
  'load-actions',
  'adopt-action',
  'reject-action',
  'view-adopted-task',
  'update:actionFilter',
  'update:taskFilter',
  'update:planFilter',
  'auto-sort-tasks',
  'apply-task-sort',
  'clear-sort-suggestions',
  'open-task-modal',
  'select-task',
  'start-inline-edit-task',
  'remove-task',
  'submit-inline-edit-task',
  'cancel-inline-edit',
  'change-task-status',
  'view-feedback-in-visit',
  'open-plan-modal',
  'view-plan',
  'open-edit-plan',
  'remove-plan',
  'submit-plan-edit',
  'cancel-plan-edit',
  'update:feedbackText',
  'update:feedbackRelatedPlanId',
  'update:feedbackRelatedTaskIds',
  'feedback-file-select',
  'remove-attachment',
  'submit-feedback',
  'toggle-record-expand',
  'toggle-show-all-feedback',
  'sales-mode-changed',
])

const props = defineProps({
  activeSubMenu: { type: String, default: 'blindspot' },
  projectId: { type: [Number, String], default: null },
  salesMode: { type: String, default: null },
  sortedFindings: { type: Array, default: () => [] },
  blindSpots: { type: Object, default: null },
  nextActions: { type: Object, default: null },
  tasks: { type: Array, default: () => [] },
  taskFilter: { type: String, default: 'pending' },
  meetingPlans: { type: Array, default: () => [] },
  planFilter: { type: String, default: 'active' },
  actionFilter: { type: String, default: 'pending' },
  stakeholders: { type: Array, default: () => [] },
  stateLogsArray: { type: Array, default: () => [] },
  fermentationResult: { type: Object, default: null },
  feedbackRecords: { type: Array, default: () => [] },
  showAllFeedbackRecords: { type: Boolean, default: false },
  feedbackText: { type: String, default: '' },
  feedbackResult: { type: Object, default: null },
  feedbackAttachments: { type: Array, default: () => [] },
  feedbackRelatedTaskIds: { type: Array, default: () => [] },
  feedbackRelatedPlanId: { type: [Number, null], default: null },
  winRateData: { type: Object, default: null },
  showWinRatePanel: { type: Boolean, default: false },
  interviewHistory: { type: Array, default: () => [] },
  interviewTargetId: { type: [Number, null], default: null },
  interviewQuestion: { type: String, default: '' },
  interviewResult: { type: Object, default: null },
  interviewing: { type: Boolean, default: false },
  presetQuestions: { type: Array, default: () => [] },
  selectedTask: { type: Object, default: null },
  selectedPlan: { type: Object, default: null },
  editingTaskInline: { type: Boolean, default: false },
  editingPlan: { type: Boolean, default: false },
  showTaskModal: { type: Boolean, default: false },
  showPlanModal: { type: Boolean, default: false },
  newTask: { type: Object, default: () => ({}) },
  newPlan: { type: Object, default: () => ({}) },
  taskEditForm: { type: Object, default: () => ({}) },
  planEditForm: { type: Object, default: () => ({}) },
  expandedRecordId: { type: [Number, null], default: null },
  showSuggestionPool: { type: Boolean, default: false },
  taskSortSuggestions: { type: Array, default: null },
  scanningBlindSpots: { type: Boolean, default: false },
  generatingActions: { type: Boolean, default: false },
  sortingTasks: { type: Boolean, default: false },
})

const severityLabels = computed(() => ({
  critical: t('workspace.severityLabels.critical'),
  high: t('workspace.severityLabels.high'),
  medium: t('workspace.severityLabels.medium'),
  low: t('workspace.severityLabels.low'),
}))

// 格式化扫描时间显示
function formatScanTime(isoStr) {
  if (!isoStr) return ''
  try {
    const d = new Date(isoStr)
    const now = new Date()
    const diff = now - d
    const oneDay = 24 * 60 * 60 * 1000
    const month = String(d.getMonth() + 1).padStart(2, '0')
    const day = String(d.getDate()).padStart(2, '0')
    const hour = String(d.getHours()).padStart(2, '0')
    const minute = String(d.getMinutes()).padStart(2, '0')
    if (diff < oneDay && now.getDate() === d.getDate()) {
      return `${t('common.today')} ${hour}:${minute}`
    }
    return `${month}-${day} ${hour}:${minute}`
  } catch {
    return isoStr
  }
}

const taskTypeLabels = computed(() => ({
  blind_spot: t('workspace.taskTypes.blind_spot'),
  address_concerns: t('workspace.taskTypes.address_concerns'),
  build_alliance: t('workspace.taskTypes.build_alliance'),
  provide_material: t('workspace.taskTypes.provide_material'),
  meeting: t('workspace.taskTypes.meeting'),
  follow_up: t('workspace.taskTypes.follow_up'),
}))

const taskStatusLabels = computed(() => ({
  pending: t('workspace.taskStatus.pending'),
  in_progress: t('workspace.taskStatus.in_progress'),
  completed: t('workspace.taskStatus.completed'),
  cancelled: t('workspace.taskStatus.cancelled'),
}))

const taskStatusClasses = {
  pending: 'pending',
  in_progress: 'in-progress',
  completed: 'completed',
  cancelled: 'cancelled',
}

const taskSourceLabels = computed(() => ({
  recommended_action: t('workspace.actionSuggestions'),
  manual: t('workspace.manualScan'),
  feedback: t('workspace.feedbackSource'),
}))

const priorityLabels = computed(() => ({
  high: t('workspace.priorityLabels.high'),
  medium: t('workspace.priorityLabels.medium'),
  low: t('workspace.priorityLabels.low'),
}))

const planStatusLabels = computed(() => ({
  pending: t('workspace.planStatus.pending'),
  generated: t('workspace.planStatus.generated'),
  reviewed: t('workspace.planStatus.reviewed'),
  active: t('workspace.planStatus.active'),
  completed: t('workspace.planStatus.completed'),
}))

// 会议类型显示标签：支持英文 key 和旧版中文值
const meetingTypeMap = {
  first_visit: 'workspace.meetingTypes.first_visit',
  proposal_report: 'workspace.meetingTypes.proposal_report',
  objection_handling: 'workspace.meetingTypes.objection_handling',
  relationship_maintenance: 'workspace.meetingTypes.relationship_maintenance',
  tech_exchange: 'workspace.meetingTypes.tech_exchange',
  business_negotiation: 'workspace.meetingTypes.business_negotiation',
  proposal_demo: 'workspace.meetingTypes.proposal_demo',
  follow_up_visit: 'workspace.meetingTypes.follow_up_visit',
  // 旧版中文值兼容
  '初次拜访': 'workspace.meetingTypes.first_visit',
  '方案汇报': 'workspace.meetingTypes.proposal_report',
  '异议处理': 'workspace.meetingTypes.objection_handling',
  '关系维护': 'workspace.meetingTypes.relationship_maintenance',
}
function meetingTypeLabel(type) {
  if (!type) return t('workspace.defaultVisitType')
  return meetingTypeMap[type] ? t(meetingTypeMap[type]) : type
}

const healthColor = computed(() => {
  const score = props.blindSpots?.overall_score
  if (score == null) return ''
  if (score >= 70) return 'text-success'
  if (score >= 40) return 'text-warning'
  return 'text-error'
})

const filteredTasks = computed(() => {
  if (props.taskFilter === 'all') return props.tasks
  return props.tasks.filter(t => t.status === props.taskFilter)
})

const activeMeetingPlans = computed(() => {
  return props.meetingPlans.filter(p => {
    if (p.status === 'active') return true
    if (p.status === 'pending' || p.status === 'generated') return true
    return false
  })
})

const completedMeetingPlans = computed(() => {
  return props.meetingPlans.filter(p => p.status === 'completed')
})

const displayedMeetingPlans = computed(() => {
  if (props.planFilter === 'all') return props.meetingPlans
  if (props.planFilter === 'completed') return completedMeetingPlans.value
  return activeMeetingPlans.value
})

const filteredActions = computed(() => {
  const actions = props.nextActions?.recommended_actions || []
  if (props.actionFilter === 'all') return actions
  if (props.actionFilter === 'adopted') return actions.filter(a => isActionAdopted(a))
  return actions.filter(a => !isActionAdopted(a))
})

const actionCounts = computed(() => {
  const actions = props.nextActions?.recommended_actions || []
  return {
    pending: actions.filter(a => !isActionAdopted(a)).length,
    adopted: actions.filter(a => isActionAdopted(a)).length,
    all: actions.length,
  }
})

const displayedFeedbackRecords = computed(() => {
  return props.showAllFeedbackRecords
    ? props.feedbackRecords
    : props.feedbackRecords.slice(0, 5)
})

function isActionAdopted(action) {
  return props.tasks.some(t => {
    if (t.source !== 'recommended_action' || !t.source_action) {
      const sa = t.source_action
      if (!sa) return t.title === action.title
      const mergedFrom = sa.merged_from || []
      return mergedFrom.some(m => (m.original_title || m.action_title) === action.title)
    }
    const orig = t.source_action.original_title || t.source_action.action_title
    if (orig === action.title) return true
    const mergedFrom = t.source_action.merged_from || []
    if (mergedFrom.some(m => (m.original_title || m.action_title) === action.title)) return true
    return t.title === action.title
  })
}

function getSortSuggestion(taskId) {
  const suggestions = props.taskSortSuggestions
  if (!suggestions) return null
  return suggestions.find(s => s.task_id === taskId) || null
}

function taskFeedbackRecords(task) {
  if (!task) return []
  return props.feedbackRecords.filter(r => {
    const ids = r.related_task_ids || []
    return ids.includes(task.id)
  })
}

function toggleFeedbackTaskId(taskId, checked) {
  const current = [...(props.feedbackRelatedTaskIds || [])]
  const idx = current.indexOf(taskId)
  if (checked && idx < 0) {
    current.push(taskId)
    emit('update:feedbackRelatedTaskIds', current)
  } else if (!checked && idx >= 0) {
    current.splice(idx, 1)
    emit('update:feedbackRelatedTaskIds', current)
  }
}

function feedbackAttachmentUrl(recordId, filename) {
  return `/api/sales-twin/feedback-records/${recordId}/attachments/${filename}`
}
</script>

<style scoped>
/* ============ 按钮 loading 旋转图标 ============ */
.btn-spinner {
  display: inline-block;
  width: 12px;
  height: 12px;
  margin-right: 5px;
  border: 2px solid currentColor;
  border-top-color: transparent;
  border-radius: 50%;
  animation: ws-btn-spin 0.7s linear infinite;
  vertical-align: -2px;
}

@keyframes ws-btn-spin {
  to { transform: rotate(360deg); }
}

@media (prefers-reduced-motion: reduce) {
  .btn-spinner { animation: none; }
}

.loading-hint {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--accent, #CD5036);
  font-weight: 500;
}

.loading-hint .btn-spinner {
  width: 14px;
  height: 14px;
  border-width: 2px;
}

.section-hint {
  display: flex;
  align-items: center;
  gap: 6px;
}

/* 工作台根容器：flex 列布局，子导航固定在顶部，内容区独立滚动 */
.workspace-tab-pane {
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.workspace-tab-pane > .workspace-subnav {
  flex-shrink: 0;
}

/* 工作台内容区：支持上下滚动，避免内容过多被裁切 */
.workspace-content {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding-right: 4px;
}

/* 滚动条美化 */
.workspace-content::-webkit-scrollbar {
  width: 8px;
}

.workspace-content::-webkit-scrollbar-track {
  background: transparent;
}

.workspace-content::-webkit-scrollbar-thumb {
  background: rgba(21, 23, 29, 0.15);
  border-radius: 4px;
}

.workspace-content::-webkit-scrollbar-thumb:hover {
  background: rgba(21, 23, 29, 0.25);
}

/* ============ CSS 变量 ============ */
.workspace-view {
  --bg-base: #F4F0E7;
  --bg-surface: #F8F4EC;
  --bg-card: #FCFBF5;
  --sidebar-bg: #EBE7DC;
  --sidebar-border: #D7D4CD;
  --panel-bg: #EFEDE2;

  --text-primary: #15171D;
  --text-secondary: #494A4D;
  --text-tertiary: #807E7E;
  --text-muted: #93959D;

  --border: #E8E8E0;
  --border-strong: #D7D4CD;
  --divider: #D7D4CD;

  --accent: #CD5036;
  --accent-light: #D88573;
  --accent-hover: #C4391C;
  --green: #118A58;
  --green-light: rgba(17, 138, 88, 0.08);
  --red: #C4391C;
  --red-light: rgba(196, 57, 28, 0.08);
  --yellow: #CBB88C;
  --yellow-light: rgba(203, 184, 140, 0.12);
  --blue: #90B0C8;
  --blue-light: rgba(144, 176, 200, 0.12);

  --focus-ring: #15171D;
  --shadow-sm: 0 1px 2px rgba(21, 23, 29, 0.04);
  --shadow-md: 0 4px 12px rgba(21, 23, 29, 0.05);
  --shadow-lg: 0 8px 24px rgba(21, 23, 29, 0.06);

  --font-mono: 'JetBrains Mono', 'SF Mono', monospace;
  --font-sans: 'Noto Sans SC', 'PingFang SC', 'Microsoft YaHei', system-ui, sans-serif;

  --fs-xs: 11px;
  --fs-sm: 12px;
  --fs-base: 13px;
  --fs-md: 14px;
  --fs-lg: 16px;
  --fs-xl: 20px;
  --fs-2xl: 26px;

  --lh-tight: 1.3;
  --lh-base: 1.5;
  --lh-loose: 1.65;
}

/* ============ 工作台子导航 ============ */
.workspace-subnav {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: rgba(21, 23, 29, 0.04);
  border-radius: 8px;
  margin-bottom: 20px;
}

.ws-tab {
  padding: 8px 16px;
  border: 1px solid rgba(21, 23, 29, 0.1);
  border-radius: 6px;
  background: var(--bg-card);
  cursor: pointer;
  font-size: var(--fs-sm);
  font-weight: 500;
  color: rgba(21, 23, 29, 0.6);
  transition: border-color 0.2s, color 0.2s, background-color 0.2s;
  display: flex;
  align-items: center;
  gap: 6px;
}

.ws-tab:hover {
  border-color: var(--yellow);
  color: var(--yellow);
}

.ws-tab.active {
  background: var(--text-primary);
  color: var(--bg-card);
  border-color: var(--text-primary);
}

.ws-count {
  display: inline-block;
  min-width: 20px;
  padding: 1px 6px;
  border-radius: 10px;
  font-size: var(--fs-xs);
  font-family: 'JetBrains Mono', monospace;
  background: rgba(21, 23, 29, 0.1);
  text-align: center;
}

.ws-tab.active .ws-count {
  background: rgba(255, 255, 255, 0.2);
  color: var(--bg-card);
}

.ws-arrow {
  color: rgba(21, 23, 29, 0.35);
  font-size: var(--fs-base);
}

.ws-winrate {
  position: relative;
  margin-left: auto;
  display: inline-flex;
  align-items: center;
}

.ws-health-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 2px 4px;
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: var(--fs-xs);
  font-family: 'JetBrains Mono', monospace;
  color: rgba(21, 23, 29, 0.7);
  transition: opacity 0.15s;
}

.ws-health-btn:hover {
  opacity: 0.7;
}

.ws-health-btn.text-success { color: var(--green); }
.ws-health-btn.text-warning { color: var(--yellow); }
.ws-health-btn.text-error { color: var(--red); }

.ws-health-label {
  font-size: var(--fs-xs);
  color: rgba(21, 23, 29, 0.5);
  font-family: 'Space Grotesk', sans-serif;
}

.ws-health-num {
  font-weight: 600;
  font-size: var(--fs-base);
}

.ws-health-num.muted {
  color: rgba(21, 23, 29, 0.35);
  font-weight: 400;
}

.ws-winrate-panel {
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  min-width: 280px;
  max-width: 360px;
  background: var(--bg-card);
  border: 1px solid rgba(21, 23, 29, 0.12);
  border-radius: 4px;
  box-shadow: 0 4px 16px rgba(21, 23, 29, 0.08);
  padding: 16px;
  z-index: 100;
  animation: ws-panel-fade 0.15s ease-out;
}

@keyframes ws-panel-fade {
  from { opacity: 0; transform: translateY(-4px); }
  to { opacity: 1; transform: translateY(0); }
}

.ws-winrate-detail {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.ws-winrate-big {
  font-size: var(--fs-2xl);
  font-weight: 700;
  font-family: 'JetBrains Mono', monospace;
  line-height: 1.2;
}

.ws-winrate-big .metric-unit {
  font-size: var(--fs-base);
  font-weight: 400;
  margin-left: 2px;
}

.ws-winrate-big.text-success { color: var(--green); }
.ws-winrate-big.text-warning { color: var(--yellow); }
.ws-winrate-big.text-error { color: var(--red); }

.ws-winrate-row {
  font-size: var(--fs-xs);
  color: rgba(21, 23, 29, 0.7);
  line-height: 1.6;
  margin: 0;
  display: flex;
  gap: 8px;
}

.ws-winrate-key {
  flex-shrink: 0;
  min-width: 56px;
  color: rgba(21, 23, 29, 0.4);
  font-family: 'JetBrains Mono', monospace;
  font-size: var(--fs-xs);
}

.ws-winrate-analysis {
  font-size: var(--fs-xs);
  color: rgba(21, 23, 29, 0.65);
  line-height: 1.7;
  margin: 4px 0 0;
  padding-top: 8px;
  border-top: 1px solid rgba(21, 23, 29, 0.06);
}

.ws-winrate-empty {
  text-align: center;
  padding: 8px 0;
}

.ws-winrate-empty p {
  font-size: var(--fs-xs);
  color: rgba(21, 23, 29, 0.5);
}

/* ============ 通用组件 ============ */
.tab-pane {
  display: flex;
  flex-direction: column;
  flex: 1;
}

.btn-primary {
  background: var(--green);
  color: #FFFFFF;
  border: 1px solid var(--green);
  padding: 7px 16px;
  font-family: var(--font-sans);
  font-size: var(--fs-sm);
  font-weight: 600;
  letter-spacing: 0.02em;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border-radius: 6px;
  transition: background 0.15s, border-color 0.15s, transform 0.1s;
}

.btn-primary:hover:not(:disabled) {
  background: #0E7349;
  border-color: #0E7349;
}

.btn-primary:active:not(:disabled) {
  transform: translateY(1px);
}

.btn-primary:disabled {
  background: #93BFA3;
  border-color: #93BFA3;
  cursor: not-allowed;
}

.btn-primary.btn-sm {
  padding: 5px 12px;
  font-size: var(--fs-xs);
}

.btn-plus {
  font-size: var(--fs-md);
  line-height: 1;
}

.btn-secondary {
  background: var(--bg-card);
  color: var(--text-secondary);
  border: 1px solid var(--border-strong);
  padding: 7px 16px;
  font-family: var(--font-sans);
  font-size: var(--fs-sm);
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s, border-color 0.2s, color 0.2s, box-shadow 0.2s;
}

.btn-secondary:hover {
  background: var(--bg-surface);
  border-color: var(--border-strong);
  color: var(--text-primary);
}

.btn-sm {
  padding: 4px 12px;
  font-size: var(--fs-xs);
}

.btn-link {
  background: none;
  border: none;
  color: rgba(21, 23, 29, 0.6);
  cursor: pointer;
  font-size: var(--fs-xs);
  padding: 4px 8px;
  text-decoration: underline;
  font-family: inherit;
}

.btn-link:hover {
  color: var(--yellow);
}

.btn-link.danger {
  color: var(--red);
}

.btn-link.danger:hover {
  color: var(--red);
}

.btn-tiny {
  padding: 0 6px;
  font-size: var(--fs-base);
  line-height: 1.4;
}

.btn-tiny:hover {
  color: var(--text-primary);
}

/* ============ 区块标题 ============ */
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

/* 盲区扫描：上次扫描时间标签 */
.bs-last-scan {
  font-size: var(--fs-xs);
  color: var(--text-tertiary);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
  flex-shrink: 0;
}

.bs-source-tag {
  display: inline-block;
  padding: 1px 5px;
  margin-left: 4px;
  border-radius: 3px;
  font-size: 10px;
  font-weight: 600;
  background: var(--green-light);
  color: var(--green);
  border: 1px solid rgba(17, 138, 88, 0.15);
}

.bs-source-tag.manual {
  background: var(--blue-light);
  color: var(--blue);
  border: 1px solid rgba(144, 176, 200, 0.2);
}

.section-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
}

.section-hint {
  font-size: var(--fs-xs);
  color: rgba(21, 23, 29, 0.62);
  background: rgba(196, 154, 69, 0.1);
  border-left: 2px solid var(--yellow);
  padding: 8px 12px;
  border-radius: 0 4px 4px 0;
  margin: 8px 0 12px;
  line-height: 1.6;
}

.analysis-section {
  margin-bottom: 32px;
  padding-bottom: 28px;
  border-bottom: 1px solid var(--border);
}

.analysis-section:last-child {
  border-bottom: none;
}

/* ============ 空状态 ============ */
.empty-state {
  text-align: center;
  padding: 60px 20px;
}

.empty-icon {
  font-size: var(--fs-2xl);
  color: var(--border);
  margin-bottom: 16px;
}

.empty-text {
  font-size: var(--fs-md);
  color: var(--text-secondary);
  margin: 0 0 6px;
}

.empty-hint {
  font-size: var(--fs-base);
  color: var(--text-muted);
  margin: 0;
}

.empty-inline {
  padding: 20px;
  text-align: center;
  color: var(--text-muted);
  font-size: var(--fs-base);
}

/* ============ 文本辅助 ============ */
.text-success { color: var(--green); }
.text-warning { color: var(--yellow); }
.text-error { color: var(--red); }
.muted { color: rgba(21, 23, 29, 0.5); }
.metric-unit { font-size: 16px; font-weight: 500; margin-left: 2px; }

/* ============ 标签/元信息 ============ */
.meta-item {
  font-size: var(--fs-sm);
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  gap: 4px;
}

.meta-icon {
  font-size: var(--fs-xs);
  color: var(--text-muted);
}

/* ============ 过滤器芯片 ============ */
.filter-chip {
  padding: 4px 12px;
  border: 1px solid rgba(21, 23, 29, 0.12);
  border-radius: 16px;
  background: transparent;
  cursor: pointer;
  font-size: var(--fs-xs);
  font-family: 'JetBrains Mono', monospace;
  color: rgba(21, 23, 29, 0.6);
  transition: background 0.2s, border-color 0.2s, color 0.2s, box-shadow 0.2s;
}

.filter-chip:hover {
  border-color: var(--yellow);
  color: var(--yellow);
}

.filter-chip.active {
  background: var(--text-primary);
  color: var(--bg-card);
  border-color: var(--text-primary);
}

/* ============ 盲区扫描 ============ */
.blind-spots-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.bs-score-bar {
  display: flex;
  align-items: center;
  gap: 10px;
}

.bs-score-label {
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  white-space: nowrap;
}

.bs-score-track {
  flex: 1;
  height: 6px;
  background: var(--border);
  border-radius: 3px;
  overflow: hidden;
}

.bs-score-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.5s ease-out;
}

.bs-score-fill.score-danger { background: var(--red); }
.bs-score-fill.score-warn { background: var(--yellow); }
.bs-score-fill.score-ok { background: var(--green); }

.bs-score-num {
  font-family: var(--font-mono);
  font-size: var(--fs-sm);
  font-weight: 700;
  color: var(--text-primary);
  min-width: 24px;
  text-align: right;
}

.bs-summary {
  font-size: var(--fs-sm);
  color: var(--text-secondary);
  margin: 0;
  line-height: 1.5;
}

.bs-findings {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.bs-finding-card {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: 4px;
  border-left: 3px solid var(--text-secondary);
  background: var(--bg-card);
  transition: border-color 0.2s, background-color 0.2s;
}

.bs-finding-card.critical { border-left-color: var(--red); background: var(--red-light); }
.bs-finding-card.high { border-left-color: var(--yellow); }
.bs-finding-card.medium { border-left-color: var(--yellow); }
.bs-finding-card.low { border-left-color: var(--text-muted); }

.bs-finding-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
  margin-top: 5px;
}

.bs-finding-dot.critical { background: var(--red); }
.bs-finding-dot.high { background: var(--yellow); }
.bs-finding-dot.medium { background: var(--yellow); }
.bs-finding-dot.low { background: var(--text-muted); }

.bs-finding-body {
  flex: 1;
  min-width: 0;
}

.bs-finding-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.bs-finding-cat {
  font-size: var(--fs-xs);
  font-family: var(--font-mono);
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.bs-finding-sev {
  font-size: var(--fs-xs);
  font-family: var(--font-mono);
  padding: 1px 6px;
  border: 1px solid;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.bs-finding-sev.critical { color: var(--red); border-color: var(--red); }
.bs-finding-sev.high { color: var(--yellow); border-color: var(--yellow); }
.bs-finding-sev.medium { color: var(--yellow); border-color: var(--yellow); }
.bs-finding-sev.low { color: var(--text-muted); border-color: var(--text-muted); }

.bs-finding-title {
  font-size: var(--fs-base);
  font-weight: 600;
  margin: 0 0 4px;
}

.bs-finding-desc {
  font-size: var(--fs-sm);
  color: var(--text-secondary);
  margin: 0;
  line-height: 1.5;
}

.bs-finding-rec {
  font-size: var(--fs-xs);
  color: var(--yellow);
  margin: 4px 0 0;
  line-height: 1.5;
  padding-left: 8px;
  border-left: 2px solid rgba(196, 154, 69, 0.35);
}

.bs-action-bar {
  display: flex;
  justify-content: flex-end;
  margin-top: 8px;
}

/* ============ 行动建议 ============ */
.actions-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.action-card {
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 18px;
  background: var(--bg-card);
}

.action-top {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.priority-tag {
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  padding: 2px 8px;
  border: 1px solid var(--border);
  font-weight: 600;
}

.priority-tag.p1 { border-color: var(--red); color: var(--red); }
.priority-tag.p2 { border-color: var(--yellow); color: var(--yellow); }
.priority-tag.p3 { border-color: var(--yellow); color: var(--yellow); }
.priority-tag.p4 { border-color: var(--text-secondary); color: var(--text-secondary); }
.priority-tag.high { border-color: var(--red); color: var(--red); }
.priority-tag.medium { border-color: var(--yellow); color: var(--yellow); }
.priority-tag.low { border-color: var(--text-muted); color: var(--text-muted); }

.action-target {
  font-size: var(--fs-xs);
  color: var(--text-muted);
}

.action-title {
  margin: 0 0 8px;
  font-size: var(--fs-md);
  font-weight: 600;
}

.action-desc {
  margin: 0;
  font-size: var(--fs-base);
  color: var(--text-secondary);
  line-height: 1.6;
}

.action-urgency {
  margin-left: 6px;
  font-size: var(--fs-xs);
  padding: 1px 6px;
  border: 1px solid var(--text-secondary);
  border-radius: 2px;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}
.action-urgency.high { border-color: var(--red); color: var(--red); }
.action-urgency.medium { border-color: var(--yellow); color: var(--yellow); }
.action-urgency.low { border-color: var(--text-muted); color: var(--text-muted); }

.action-reasoning {
  margin-top: 8px;
  padding: 8px 10px;
  background: rgba(196, 154, 69, 0.08);
  border-left: 2px solid var(--yellow);
  font-size: var(--fs-sm);
  color: var(--text-secondary);
  line-height: 1.5;
}
.action-reasoning .reasoning-label {
  display: inline-block;
  margin-right: 6px;
  font-weight: 600;
  color: var(--yellow);
  font-size: var(--fs-xs);
  letter-spacing: 0.5px;
}

.action-brief {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border);
}

.brief-label {
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  display: block;
  margin-bottom: 6px;
}

.action-brief p {
  margin: 4px 0;
  font-size: var(--fs-sm);
  color: var(--text-secondary);
  line-height: 1.6;
}

.brief-key {
  font-weight: 600;
  color: var(--text-primary);
}

.action-footer {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(21, 23, 29, 0.06);
}

.action-title-input,
.action-desc-input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid rgba(21, 23, 29, 0.12);
  border-radius: 4px;
  font-family: inherit;
  font-size: var(--fs-base);
  margin-bottom: 8px;
  background: var(--bg-card);
}

.action-title-input {
  font-weight: 600;
  font-size: var(--fs-base);
}

.adopted-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 3px;
  font-size: var(--fs-xs);
  font-family: 'JetBrains Mono', monospace;
  background: rgba(0, 128, 0, 0.1);
  color: var(--green);
  border: 1px solid rgba(0, 128, 0, 0.2);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.action-card.adopted {
  background: rgba(21, 23, 29, 0.02);
  border-color: rgba(21, 23, 29, 0.06);
  opacity: 0.75;
}

.action-card.adopted .action-title {
  color: rgba(21, 23, 29, 0.55);
}

.adopted-status {
  font-size: var(--fs-xs);
  font-family: 'JetBrains Mono', monospace;
  color: var(--green);
  padding: 2px 8px;
}

/* 自进化引擎：拒绝下拉 */
.reject-dropdown {
  position: relative;
  display: inline-block;
}
.reject-menu {
  position: absolute;
  bottom: 100%;
  right: 0;
  background: var(--bg-card);
  border: 1px solid var(--border, rgba(21, 23, 29, 0.12));
  border-radius: 4px;
  list-style: none;
  padding: 4px 0;
  margin: 0 0 4px;
  box-shadow: 0 -4px 12px rgba(0, 0, 0, 0.1);
  z-index: 10;
  min-width: 140px;
}
.reject-menu li {
  padding: 6px 12px;
  font-size: var(--fs-xs, 12px);
  cursor: pointer;
  white-space: nowrap;
}
.reject-menu li:hover {
  background: rgba(21, 23, 29, 0.04);
}
.btn-ghost {
  background: transparent;
  border: 1px solid var(--border, rgba(21, 23, 29, 0.12));
  color: var(--text-secondary, #494A4D);
  border-radius: 4px;
  cursor: pointer;
  font-size: var(--fs-xs, 12px);
}
.btn-ghost:hover {
  border-color: var(--text-secondary, #494A4D);
}
.rejected-status {
  font-size: var(--fs-xs, 12px);
  color: var(--text-tertiary, #807E7E);
}

/* ============ 标签 ============ */
.task-type-tag {
  padding: 2px 8px;
  border-radius: 3px;
  font-size: var(--fs-xs);
  font-family: 'JetBrains Mono', monospace;
  background: rgba(21, 23, 29, 0.06);
  color: rgba(21, 23, 29, 0.7);
}

.source-tag {
  padding: 2px 6px;
  border-radius: 3px;
  font-size: var(--fs-xs);
  font-family: 'JetBrains Mono', monospace;
  background: rgba(196, 154, 69, 0.16);
  color: var(--yellow);
  text-transform: uppercase;
}

.task-status {
  padding: 2px 6px;
  border-radius: 3px;
  font-size: var(--fs-xs);
  font-family: 'JetBrains Mono', monospace;
  background: rgba(21, 23, 29, 0.06);
  color: rgba(21, 23, 29, 0.6);
  text-transform: uppercase;
}

.task-status.pending { background: rgba(196, 154, 69, 0.16); color: var(--yellow); }
.task-status.in-progress { background: var(--blue-light); color: var(--blue); }
.task-status.completed { background: var(--green-light); color: var(--green); }
.task-status.cancelled { background: rgba(21, 23, 29, 0.06); color: var(--text-muted); }

.sort-tag {
  display: inline-flex;
  align-items: center;
  padding: 1px 6px;
  border-radius: 2px;
  font-size: var(--fs-xs);
  font-family: 'JetBrains Mono', monospace;
  background: rgba(196, 154, 69, 0.16);
  color: var(--yellow);
  margin-left: 4px;
  cursor: help;
}

/* ============ 左右栏布局 ============ */
.plan-split-layout {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 16px;
  min-height: 480px;
}

.plan-list-pane {
  border-right: 1px solid rgba(21, 23, 29, 0.08);
  padding-right: 12px;
  overflow-y: auto;
  max-height: 70vh;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.plan-list-item {
  padding: 12px;
  border: 1px solid rgba(21, 23, 29, 0.08);
  border-radius: 4px;
  background: var(--bg-card);
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}

.plan-list-item:hover {
  border-color: rgba(21, 23, 29, 0.2);
}

.plan-list-item.selected {
  border-color: var(--yellow);
  background: rgba(196, 154, 69, 0.08);
}

.plan-list-top {
  display: flex;
  gap: 6px;
  align-items: center;
  margin-bottom: 6px;
}

.plan-list-name {
  font-size: var(--fs-base);
  font-weight: 600;
  margin: 4px 0;
  line-height: 1.4;
}

.plan-list-purpose {
  font-size: var(--fs-xs);
  color: rgba(21, 23, 29, 0.6);
  margin: 4px 0;
  line-height: 1.5;
}

.plan-list-meta {
  display: flex;
  gap: 12px;
  font-size: var(--fs-xs);
  color: rgba(21, 23, 29, 0.5);
  font-family: 'JetBrains Mono', monospace;
  margin-top: 6px;
}

.plan-detail-pane {
  padding-left: 12px;
  overflow-y: auto;
  max-height: 70vh;
}

.plan-detail-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.plan-detail-header {
  border-bottom: 1px solid rgba(21, 23, 29, 0.08);
  padding-bottom: 12px;
}

.plan-detail-title-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 8px;
}

.plan-detail-title {
  font-size: var(--fs-lg);
  font-weight: 600;
  margin: 0;
  flex: 1;
}

.plan-detail-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.plan-detail-meta {
  display: flex;
  gap: 16px;
  font-size: var(--fs-xs);
  color: rgba(21, 23, 29, 0.6);
  font-family: 'JetBrains Mono', monospace;
  margin-bottom: 8px;
}

.plan-detail-purpose {
  font-size: var(--fs-sm);
  color: rgba(21, 23, 29, 0.78);
  margin: 8px 0 0;
  line-height: 1.6;
}

.plan-edit-form {
  background: rgba(21, 23, 29, 0.02);
  padding: 16px;
  border-radius: 4px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* ============ 待办详情 ============ */
.task-detail-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-top: 8px;
}

.task-detail-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.task-detail-desc {
  white-space: pre-wrap;
  line-height: 1.7;
  font-size: var(--fs-sm);
  color: rgba(21, 23, 29, 0.78);
}

.task-status-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.task-status-select {
  padding: 4px 8px;
  border: 1px solid rgba(21, 23, 29, 0.12);
  border-radius: 4px;
  font-size: var(--fs-xs);
  font-family: inherit;
  background: var(--bg-card);
  cursor: pointer;
}

.merged-from-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.merged-from-list li {
  font-size: var(--fs-xs);
  color: rgba(21, 23, 29, 0.65);
  padding: 6px 8px;
  background: rgba(21, 23, 29, 0.02);
  border-radius: 2px;
  line-height: 1.6;
}

.task-actions {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-top: 12px;
}

/* ============ 计划状态 ============ */
.plan-type {
  padding: 2px 8px;
  border-radius: 3px;
  font-size: var(--fs-xs);
  font-family: 'JetBrains Mono', monospace;
  background: rgba(196, 154, 69, 0.16);
  color: var(--yellow);
}

.plan-status {
  padding: 2px 6px;
  border-radius: 3px;
  font-size: var(--fs-xs);
  font-family: 'JetBrains Mono', monospace;
  background: rgba(21, 23, 29, 0.06);
  color: rgba(21, 23, 29, 0.6);
  text-transform: uppercase;
}

.plan-status.pending,
.plan-status.generated {
  background: rgba(196, 154, 69, 0.16);
  color: var(--yellow);
}

.plan-status.reviewed {
  background: rgba(0, 128, 0, 0.1);
  color: var(--green);
}

.plan-status.active {
  background: rgba(196, 154, 69, 0.18);
  color: var(--yellow);
  font-weight: 600;
}

.plan-status.completed {
  background: rgba(0, 128, 0, 0.12);
  color: var(--green);
  font-weight: 600;
}

/* ============ 计划内容 ============ */
.plan-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.plan-block {
  padding: 12px;
  border-left: 3px solid var(--yellow);
  background: rgba(196, 154, 69, 0.06);
  border-radius: 0 6px 6px 0;
}

.plan-block h4 {
  font-size: var(--fs-sm);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin: 0 0 8px;
  color: var(--yellow);
  font-family: 'JetBrains Mono', monospace;
}

.plan-block ul {
  margin: 0;
  padding-left: 20px;
}

.plan-block li {
  font-size: var(--fs-sm);
  line-height: 1.6;
  color: rgba(21, 23, 29, 0.78);
}

.plan-block p {
  font-size: var(--fs-sm);
  line-height: 1.6;
  color: rgba(21, 23, 29, 0.78);
}

.plan-block.warning {
  border-left-color: var(--red);
  background: rgba(220, 53, 69, 0.04);
}

.plan-block.warning h4 {
  color: var(--red);
}

.objection-item,
.strategy-item {
  padding: 8px;
  margin: 8px 0;
  background: var(--bg-card);
  border-radius: 4px;
  border: 1px solid rgba(21, 23, 29, 0.06);
}

.objection-item p,
.strategy-item p {
  margin: 4px 0;
  font-size: var(--fs-xs);
}

.strategy-item .muted {
  color: rgba(21, 23, 29, 0.5);
  font-size: var(--fs-xs);
}

/* ============ 表单 ============ */
.form-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.field-label {
  font-size: var(--fs-xs);
  color: rgba(21, 23, 29, 0.5);
  font-family: 'JetBrains Mono', monospace;
}

.form-input {
  padding: 6px 8px;
  border: 1px solid rgba(21, 23, 29, 0.15);
  border-radius: 2px;
  font-size: var(--fs-sm);
  font-family: inherit;
  background: var(--bg-card);
}

.form-input:focus {
  outline: 2px solid transparent;
  border-color: var(--yellow);
}

.form-hint {
  font-size: var(--fs-xs);
  color: rgba(21, 23, 29, 0.4);
  font-style: italic;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

/* ============ 多选列表 ============ */
.stakeholder-checkbox-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 12px;
  padding: 4px 0;
}

.stakeholder-checkbox {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: var(--fs-xs);
  color: rgba(21, 23, 29, 0.78);
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 2px;
  transition: background 0.15s ease;
}

.stakeholder-checkbox:hover {
  background: rgba(21, 23, 29, 0.04);
}

.stakeholder-checkbox input[type="checkbox"] {
  margin: 0;
  cursor: pointer;
}

.chip-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 2px 0;
}

.chip-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border: 1px solid var(--border);
  border-radius: 2px;
  font-size: var(--fs-xs);
  color: rgba(21, 23, 29, 0.78);
  cursor: pointer;
  background: var(--bg-card);
  transition: border-color 0.15s, background 0.15s, color 0.15s;
  user-select: none;
}

.chip-item:hover {
  border-color: var(--text-primary);
}

.chip-item input[type="checkbox"] {
  margin: 0;
  width: 12px;
  height: 12px;
  cursor: pointer;
  accent-color: var(--text-primary);
}

.chip-item:has(input:checked) {
  background: var(--text-primary);
  color: var(--bg-card);
  border-color: var(--text-primary);
}

.chip-item:has(input:checked) input[type="checkbox"] {
  accent-color: var(--bg-card);
}

.chip-item:focus-within {
  outline: 2px solid var(--text-primary);
  outline-offset: 1px;
}

/* ============ 拜访记录 ============ */
.feedback-grid {
  display: grid;
  grid-template-columns: 1.4fr 1fr;
  gap: 24px;
  align-items: start;
  margin-bottom: 32px;
}

.feedback-section {
  margin-bottom: 32px;
}

.feedback-side {
  display: flex;
  flex-direction: column;
  gap: 20px;
  position: sticky;
  top: 12px;
}

.feedback-input {
  width: 100%;
  padding: 14px;
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: var(--fs-base);
  font-family: var(--font-sans);
  resize: vertical;
  margin-bottom: 12px;
  transition: border-color 0.2s;
}

.feedback-input:focus {
  outline: 2px solid transparent;
  border-color: var(--text-primary);
}

.feedback-input:focus-visible {
  outline: 2px solid var(--text-primary);
  outline-offset: 1px;
  border-color: var(--text-primary);
}

.field-hint {
  font-size: var(--fs-xs);
  color: var(--text-muted);
  margin: 4px 0 8px;
  line-height: 1.4;
}

.feedback-actions {
  margin-bottom: 16px;
}

.feedback-attachments-input {
  margin: 10px 0 14px;
}

.feedback-attachments-input .field-label {
  display: block;
  margin-bottom: 6px;
}

.attach-label-text {
  font-size: var(--fs-xs);
  color: rgba(21, 23, 29, 0.6);
}

.attach-chip-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}

.attach-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px 4px 10px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 2px;
  font-size: var(--fs-xs);
  color: rgba(21, 23, 29, 0.8);
  max-width: 220px;
}

.attach-chip-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
}

.attach-chip-size {
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  color: rgba(21, 23, 29, 0.4);
  flex-shrink: 0;
}

.attach-chip-remove {
  background: none;
  border: none;
  color: rgba(21, 23, 29, 0.4);
  cursor: pointer;
  padding: 0 2px;
  font-size: var(--fs-base);
  line-height: 1;
  border-radius: 2px;
  transition: color 0.15s;
}

.attach-chip-remove:hover {
  color: var(--text-primary);
}

.feedback-result {
  padding: 16px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--bg-surface);
}

.feedback-summary {
  font-size: var(--fs-base);
  color: var(--text-primary);
  margin: 6px 0;
}

.feedback-changes {
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  color: var(--text-secondary);
  margin: 4px 0 0;
}

.task-updates {
  margin-top: 12px;
  padding: 8px;
  background: rgba(196, 154, 69, 0.1);
  border-radius: 4px;
}

.task-update-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0;
  font-size: var(--fs-xs);
}

.task-update-title {
  font-weight: 500;
}

.task-update-status {
  font-family: 'JetBrains Mono', monospace;
  color: rgba(21, 23, 29, 0.6);
}

/* ============ 反馈关联 ============ */
.feedback-related-tasks {
  margin-bottom: 16px;
  padding: 12px;
  background: rgba(21, 23, 29, 0.02);
  border-radius: 6px;
}

.feedback-related-tasks .plan-select {
  display: block;
  width: 100%;
  margin-top: 6px;
  padding: 6px 8px;
  border: 1px solid rgba(21, 23, 29, 0.12);
  border-radius: 4px;
  font-size: var(--fs-sm);
  font-family: inherit;
  background: var(--bg-card);
  cursor: pointer;
}

.task-checkbox-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 8px;
}

.task-checkbox {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 4px;
  cursor: pointer;
  font-size: var(--fs-sm);
  transition: background 0.2s;
}

.task-checkbox:hover {
  background: rgba(21, 23, 29, 0.04);
}

.task-checkbox input[type="checkbox"] {
  cursor: pointer;
}

/* ============ 历史记录 ============ */
.feedback-records-section {
  margin-top: 24px;
}

.feedback-record-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.feedback-record-item {
  padding: 12px;
  border: 1px solid rgba(21, 23, 29, 0.08);
  border-radius: 6px;
  background: var(--bg-card);
}

.feedback-record-item.clickable {
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
}

.feedback-record-item.clickable:hover {
  background: rgba(196, 154, 69, 0.06);
  border-color: rgba(196, 154, 69, 0.35);
}

.feedback-record-item.expanded {
  background: rgba(196, 154, 69, 0.08);
  border-color: var(--yellow);
}

.record-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.record-time {
  font-size: var(--fs-xs);
  font-family: 'JetBrains Mono', monospace;
  color: rgba(21, 23, 29, 0.5);
}

.record-changes {
  font-size: var(--fs-xs);
  padding: 2px 6px;
  border-radius: 3px;
  background: rgba(196, 154, 69, 0.16);
  color: var(--yellow);
  font-family: 'JetBrains Mono', monospace;
}

.record-text {
  font-size: var(--fs-sm);
  color: rgba(21, 23, 29, 0.7);
  line-height: 1.5;
  margin: 4px 0;
}

.record-text.record-full {
  white-space: pre-wrap;
  background: rgba(21, 23, 29, 0.02);
  padding: 8px;
  border-radius: 3px;
  font-size: var(--fs-sm);
  line-height: 1.7;
  max-height: 400px;
  overflow-y: auto;
}

.record-summary {
  font-size: var(--fs-xs);
  color: rgba(21, 23, 29, 0.5);
  margin-top: 4px;
  font-style: italic;
}

.feedback-record-more {
  display: block;
  width: 100%;
  padding: 8px;
  font-size: var(--fs-xs);
  color: rgba(21, 23, 29, 0.5);
  text-align: center;
  font-family: 'JetBrains Mono', monospace;
  background: none;
  border: none;
  border-top: 1px solid var(--border);
  cursor: pointer;
  transition: color 0.15s, background 0.15s;
}

.feedback-record-more:hover {
  color: var(--text-primary);
  background: rgba(21, 23, 29, 0.04);
}

/* ============ 附件 ============ */
.record-attachments {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed rgba(21, 23, 29, 0.1);
}

.record-attachments .brief-label {
  display: block;
  font-size: var(--fs-xs);
  color: rgba(21, 23, 29, 0.5);
  margin-bottom: 4px;
  font-family: 'JetBrains Mono', monospace;
}

.attachment-list {
  margin-bottom: 6px;
}

.attachment-item {
  padding: 2px 0;
}

.attachment-link {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: var(--fs-xs);
  color: rgba(21, 23, 29, 0.78);
  text-decoration: none;
  word-break: break-all;
  transition: color 0.15s;
}

.attachment-link:hover {
  color: var(--text-primary);
  text-decoration: underline;
}

.attachment-link svg {
  flex-shrink: 0;
  color: rgba(21, 23, 29, 0.4);
}

.attachment-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
}

.attachment-size {
  color: rgba(21, 23, 29, 0.4);
  font-size: var(--fs-xs);
  font-family: var(--font-mono);
  flex-shrink: 0;
}

/* ============ 待办关联反馈 ============ */
.task-feedback-item {
  padding: 8px 10px;
  border-left: 2px solid var(--yellow);
  background: rgba(21, 23, 29, 0.02);
  margin-bottom: 6px;
  border-radius: 2px;
}

.task-feedback-top {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
  font-size: var(--fs-xs);
  font-family: 'JetBrains Mono', monospace;
  color: rgba(21, 23, 29, 0.5);
}

.task-feedback-time {
  font-weight: 600;
  color: rgba(21, 23, 29, 0.7);
}

.task-feedback-changes {
  color: var(--yellow);
}

.task-feedback-text {
  font-size: var(--fs-xs);
  color: rgba(21, 23, 29, 0.7);
  line-height: 1.5;
  margin: 2px 0;
}

.task-feedback-impact {
  font-size: var(--fs-xs);
  color: rgba(21, 23, 29, 0.6);
  margin-top: 4px;
  font-style: italic;
}

.impact-label {
  color: rgba(21, 23, 29, 0.45);
  font-style: normal;
}

/* ============ 响应式 ============ */
@media (max-width: 1024px) {
  .plan-split-layout {
    grid-template-columns: 1fr;
  }
  .plan-list-pane {
    border-right: none;
    border-bottom: 1px solid rgba(21, 23, 29, 0.08);
    padding-right: 0;
    padding-bottom: 12px;
    max-height: 300px;
  }
  .plan-detail-pane {
    padding-left: 0;
    max-height: none;
  }
  .feedback-grid {
    grid-template-columns: 1fr;
  }
  .feedback-side {
    position: static;
  }
}

@media (max-width: 640px) {
  .form-row {
    grid-template-columns: 1fr;
  }
  .workspace-subnav {
    flex-wrap: wrap;
  }
}
</style>
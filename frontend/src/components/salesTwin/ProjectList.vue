<template>
  <div class="project-list-view">
    <div class="page-header">
      <div class="header-left">
        <span class="section-deco">◇</span>
        <h1 class="page-title">{{ t('project.title') }}</h1>
      </div>
      <div class="header-right">
        <span class="project-count">{{ projects.length }} {{ t('project.projectsLabel') }}</span>
        <button type="button" class="btn-primary btn-sm" @click="$emit('show-create-modal')">+ {{ t('project.createProject') }}</button>
      </div>
    </div>

    <div v-if="projects.length === 0" class="empty-state">
      <div class="empty-icon">❖</div>
      <p class="empty-text">{{ t('project.noProjectsShort') }}</p>
      <p class="empty-hint">{{ t('project.createFirstHint') }}</p>
    </div>

    <div v-else class="swimlane-board">
      <!-- 前4列：活跃阶段 -->
      <div
        v-for="stage in activeStages"
        :key="stage.value"
        class="swimlane"
        @dragover.prevent="onDragOver($event, stage.value)"
        @dragleave="onDragLeave($event)"
        @drop="onDrop($event, stage.value)"
      >
        <div class="swimlane-header">
          <span class="swimlane-dot" :class="'dot-' + stage.value"></span>
          <span class="swimlane-title">{{ t('stages.' + stage.value) }}</span>
          <span class="swimlane-count">{{ projectsByStage(stage.value).length }}</span>
        </div>
        <div class="swimlane-body">
          <div
            v-for="project in projectsByStage(stage.value)"
            :key="project.id"
            class="project-card"
            role="button"
            tabindex="0"
            draggable="true"
            @dragstart="onDragStart($event, project)"
            @dragend="onDragEnd($event)"
            @click="selectProject(project.id)"
            @keydown.enter="selectProject(project.id)"
            @keydown.space.prevent="selectProject(project.id)"
            :aria-label="t('project.viewProject', { name: project.name })"
          >
            <div class="card-top">
              <h3 class="project-name">{{ project.name }}</h3>
              <span class="stage-badge" :class="project.sales_stage">
                {{ t('stages.' + project.sales_stage) }}
              </span>
            </div>
            <div class="card-meta">
              <span v-if="project.customer_name" class="meta-item">
                <span class="meta-icon">■</span>{{ project.customer_name }}
              </span>
              <span v-if="project.budget" class="meta-item budget">
                <span class="meta-icon">¥</span>{{ formatCurrency(project.budget) }}
              </span>
            </div>
            <p v-if="project.pain_points_summary" class="project-desc">
              {{ truncateText(project.pain_points_summary, 80) }}
            </p>
            <div class="card-footer">
              <span class="update-time">{{ formatDate(project.expected_close_date) }}</span>
              <span class="card-indicators">
                <span class="card-dot" :class="certClass(project.budget_certainty)" :title="certLabel('budget', project.budget_certainty)"></span>
                <span class="card-dot" :class="certClass(project.time_certainty)" :title="certLabel('time', project.time_certainty)"></span>
                <span class="card-dot" :class="certClass(project.tendency)" :title="certLabel('tendency', project.tendency)"></span>
              </span>
              <span class="card-arrow">→</span>
            </div>
          </div>
          <div v-if="projectsByStage(stage.value).length === 0" class="swimlane-empty">
            {{ t('project.dragCardHere') }}
          </div>
        </div>
      </div>
      <!-- 第5列：赢单（上）+ 丢单（下），各自独立泳道，默认仅本月 -->
      <div class="swimlane-closed-col">
        <!-- 赢单 -->
        <div
          class="swimlane"
          @dragover.prevent="onDragOver($event, 'closed_won')"
          @dragleave="onDragLeave($event)"
          @drop="onDrop($event, 'closed_won')"
        >
          <div class="swimlane-header">
            <span class="swimlane-dot dot-closed_won"></span>
            <span class="swimlane-title">{{ t('stages.closed_won') }}</span>
            <span class="swimlane-count">{{ wonProjects.length }}</span>
            <button
              type="button"
              class="swimlane-toggle-btn"
              @click="showAllClosed = !showAllClosed"
              :aria-label="showAllClosed ? t('project.showThisMonthOnly') : t('project.viewAll')"
            >{{ showAllClosed ? t('project.thisMonthOnly') : t('project.viewAll') }}</button>
          </div>
          <div class="swimlane-body">
            <div
              v-for="project in wonProjects"
              :key="project.id"
              class="project-card"
              role="button"
              tabindex="0"
              draggable="true"
              @dragstart="onDragStart($event, project)"
              @dragend="onDragEnd($event)"
              @click="selectProject(project.id)"
              @keydown.enter="selectProject(project.id)"
              @keydown.space.prevent="selectProject(project.id)"
              :aria-label="t('project.viewProject', { name: project.name })"
            >
              <div class="card-top">
                <h3 class="project-name">{{ project.name }}</h3>
                <span class="stage-badge" :class="project.sales_stage">
                  {{ t('stages.' + project.sales_stage) }}
                </span>
              </div>
              <div class="card-meta">
                <span v-if="project.customer_name" class="meta-item">
                  <span class="meta-icon">■</span>{{ project.customer_name }}
                </span>
                <span v-if="project.budget" class="meta-item budget">
                  <span class="meta-icon">¥</span>{{ formatCurrency(project.budget) }}
                </span>
              </div>
              <div class="card-footer">
                <span class="update-time">{{ formatDate(project.expected_close_date) }}</span>
                <span class="card-indicators">
                  <span class="card-dot" :class="certClass(project.budget_certainty)" :title="certLabel('budget', project.budget_certainty)"></span>
                  <span class="card-dot" :class="certClass(project.time_certainty)" :title="certLabel('time', project.time_certainty)"></span>
                  <span class="card-dot" :class="certClass(project.tendency)" :title="certLabel('tendency', project.tendency)"></span>
                </span>
                <span class="card-arrow">→</span>
              </div>
            </div>
            <div v-if="wonProjects.length === 0" class="swimlane-empty">
              {{ showAllClosed ? t('project.noWon') : t('project.noWonThisMonth') }}
            </div>
          </div>
        </div>
        <!-- 丢单 -->
        <div
          class="swimlane"
          @dragover.prevent="onDragOver($event, 'closed_lost')"
          @dragleave="onDragLeave($event)"
          @drop="onDrop($event, 'closed_lost')"
        >
          <div class="swimlane-header">
            <span class="swimlane-dot dot-closed_lost"></span>
            <span class="swimlane-title">{{ t('stages.closed_lost') }}</span>
            <span class="swimlane-count">{{ lostProjects.length }}</span>
          </div>
          <div class="swimlane-body">
            <div
              v-for="project in lostProjects"
              :key="project.id"
              class="project-card"
              role="button"
              tabindex="0"
              draggable="true"
              @dragstart="onDragStart($event, project)"
              @dragend="onDragEnd($event)"
              @click="selectProject(project.id)"
              @keydown.enter="selectProject(project.id)"
              @keydown.space.prevent="selectProject(project.id)"
              :aria-label="t('project.viewProject', { name: project.name })"
            >
              <div class="card-top">
                <h3 class="project-name">{{ project.name }}</h3>
                <span class="stage-badge" :class="project.sales_stage">
                  {{ t('stages.' + project.sales_stage) }}
                </span>
              </div>
              <div class="card-meta">
                <span v-if="project.customer_name" class="meta-item">
                  <span class="meta-icon">■</span>{{ project.customer_name }}
                </span>
                <span v-if="project.budget" class="meta-item budget">
                  <span class="meta-icon">¥</span>{{ formatCurrency(project.budget) }}
                </span>
              </div>
              <div class="card-footer">
                <span class="update-time">{{ formatDate(project.expected_close_date) }}</span>
                <span class="card-indicators">
                  <span class="card-dot" :class="certClass(project.budget_certainty)" :title="certLabel('budget', project.budget_certainty)"></span>
                  <span class="card-dot" :class="certClass(project.time_certainty)" :title="certLabel('time', project.time_certainty)"></span>
                  <span class="card-dot" :class="certClass(project.tendency)" :title="certLabel('tendency', project.tendency)"></span>
                </span>
                <span class="card-arrow">→</span>
              </div>
            </div>
            <div v-if="lostProjects.length === 0" class="swimlane-empty">
              {{ showAllClosed ? t('project.noLost') : t('project.noLostThisMonth') }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  formatCurrency as defaultFormatCurrency,
  formatDate as defaultFormatDate,
  truncateText as defaultTruncateText
} from '../../composables/salesTwin/formatters.js'

const { t } = useI18n()

const props = defineProps({
  projects: { type: Array, default: () => [] },
  stageLabels: { type: Object, default: () => ({}) },
  activeStages: { type: Array, default: () => [] },
  formatCurrency: { type: Function, default: defaultFormatCurrency },
  formatDate: { type: Function, default: defaultFormatDate },
  truncateText: { type: Function, default: defaultTruncateText },
  certClass: {
    type: Function,
    default: (val) => {
      if (val === 1) return 'dot-red'
      if (val === 2) return 'dot-yellow'
      if (val === 3) return 'dot-green'
      return 'dot-empty'
    }
  },
  certLabel: {
    type: Function,
    // Note: default cannot reference t() due to defineProps constraints.
    // Parent (useSalesTwin.js) always provides an i18n-aware certLabel.
    default: (type, val) => `${type}: ${val ?? '—'}`
  }
})

const emit = defineEmits(['select-project', 'drag-start', 'drag-end', 'drag-over', 'drag-leave', 'drop', 'show-create-modal'])

const showAllClosed = ref(false)

let _draggedProjectId = null
let _dragOverStage = null

function isCurrentMonth(dateStr) {
  if (!dateStr) return false
  const d = new Date(dateStr)
  if (isNaN(d.getTime())) return false
  const now = new Date()
  return d.getFullYear() === now.getFullYear() && d.getMonth() === now.getMonth()
}

function projectsByStage(stageValue) {
  return props.projects.filter(p => p.sales_stage === stageValue)
}

const wonProjects = computed(() => {
  const all = props.projects.filter(p => p.sales_stage === 'closed_won')
  return showAllClosed.value ? all : all.filter(p => isCurrentMonth(p.updated_at))
})

const lostProjects = computed(() => {
  const all = props.projects.filter(p => p.sales_stage === 'closed_lost')
  return showAllClosed.value ? all : all.filter(p => isCurrentMonth(p.updated_at))
})

function selectProject(projectId) {
  emit('select-project', projectId)
}

function onDragStart(e, project) {
  _draggedProjectId = project.id
  e.dataTransfer.effectAllowed = 'move'
  e.dataTransfer.setData('text/plain', String(project.id))
  e.target.classList.add('dragging')
  emit('drag-start', e, project)
}

function onDragEnd(e) {
  e.target.classList.remove('dragging')
  _draggedProjectId = null
  _dragOverStage = null
  emit('drag-end', e)
}

function onDragOver(e, stageValue) {
  e.dataTransfer.dropEffect = 'move'
  if (_dragOverStage !== stageValue) {
    _dragOverStage = stageValue
  }
  const body = e.currentTarget.querySelector('.swimlane-body')
  if (body) body.classList.add('drag-over')
  emit('drag-over', e, stageValue)
}

function onDragLeave(e) {
  const body = e.currentTarget.querySelector('.swimlane-body')
  if (body && !body.contains(e.relatedTarget)) {
    body.classList.remove('drag-over')
  }
  emit('drag-leave', e)
}

function onDrop(e, targetStage) {
  e.preventDefault()
  const body = e.currentTarget.querySelector('.swimlane-body')
  if (body) body.classList.remove('drag-over')
  emit('drop', e, targetStage, _draggedProjectId)
  _draggedProjectId = null
  _dragOverStage = null
}
</script>

<style scoped>
.project-list-view {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  padding: 20px 24px 28px;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.section-deco {
  color: var(--color-primary, #6c5ce7);
  font-size: 18px;
}

.page-title {
  font-size: 22px;
  font-weight: 600;
  margin: 0;
  color: var(--color-text-primary, #1a1a2e);
}

.project-count {
  font-size: 12px;
  letter-spacing: 1px;
  color: var(--color-text-tertiary, #999);
  font-weight: 500;
}

.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.empty-icon {
  font-size: 48px;
  color: var(--color-text-tertiary, #ccc);
}

.empty-text {
  font-size: 16px;
  color: var(--color-text-secondary, #666);
  margin: 0;
}

.empty-hint {
  font-size: 13px;
  color: var(--color-text-tertiary, #999);
  margin: 0;
}

.swimlane-board {
  display: flex;
  gap: 12px;
  flex: 1;
  overflow-x: auto;
  overflow-y: hidden;
  padding-bottom: 8px;
}

.swimlane {
  flex: 1 1 0;
  min-width: 180px;
  display: flex;
  flex-direction: column;
  background: var(--color-bg-secondary, #f8f9fc);
  border-radius: 10px;
  overflow: hidden;
}

.swimlane-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 16px;
  border-bottom: 1px solid var(--color-border, #e8e8ef);
  flex-shrink: 0;
}

.swimlane-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.swimlane-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary, #1a1a2e);
  flex: 1;
}

.swimlane-count {
  font-size: 12px;
  color: var(--color-text-tertiary, #999);
  background: var(--color-bg-tertiary, #eee);
  padding: 2px 8px;
  border-radius: 10px;
}

.swimlane-toggle-btn {
  font-size: 11px;
  color: var(--color-primary, #6c5ce7);
  background: none;
  border: 1px solid var(--color-primary, #6c5ce7);
  border-radius: 4px;
  padding: 2px 6px;
  cursor: pointer;
  white-space: nowrap;
}

.swimlane-toggle-btn:hover {
  background: var(--color-primary, #6c5ce7);
  color: #fff;
}

.swimlane-body {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 120px;
}

.swimlane-body.drag-over {
  background: rgba(108, 92, 231, 0.06);
}

.swimlane-empty {
  text-align: center;
  color: var(--color-text-tertiary, #bbb);
  font-size: 12px;
  padding: 20px 0;
}

.swimlane-closed-col {
  flex: 1 1 0;
  min-width: 180px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.swimlane-closed-col .swimlane {
  flex: 1;
  min-width: 0;
}

.project-card {
  background: #fff;
  border-radius: 10px;
  padding: 14px;
  cursor: pointer;
  border: 1px solid var(--color-border, #e8e8ef);
  transition: box-shadow 0.15s, transform 0.15s;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.project-card:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
  transform: translateY(-2px);
}

.project-card:focus-visible {
  outline: 2px solid var(--color-primary, #6c5ce7);
  outline-offset: 2px;
}

.project-card.dragging {
  opacity: 0.5;
}

.card-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}

.project-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary, #1a1a2e);
  margin: 0;
  line-height: 1.4;
  flex: 1;
}

.stage-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  white-space: nowrap;
  flex-shrink: 0;
  background: var(--color-bg-tertiary, #eee);
  color: var(--color-text-secondary, #666);
}

.card-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 12px;
  color: var(--color-text-secondary, #666);
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.meta-item.budget {
  color: var(--color-success, #00b894);
  font-weight: 500;
}

.meta-icon {
  font-size: 10px;
}

.project-desc {
  font-size: 12px;
  color: var(--color-text-tertiary, #999);
  margin: 0;
  line-height: 1.5;
}

.card-footer {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  color: var(--color-text-tertiary, #aaa);
}

.update-time {
  flex: 1;
}

.card-indicators {
  display: flex;
  gap: 4px;
}

.card-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.card-dot.dot-red { background: #ff6b6b; }
.card-dot.dot-yellow { background: #feca57; }
.card-dot.dot-green { background: #1dd1a1; }
.card-dot.dot-empty { background: #ddd; }

.card-arrow {
  font-size: 13px;
  color: var(--color-text-tertiary, #ccc);
}

.swimlane-dot.dot-closed_won { background: #1dd1a1; }
.swimlane-dot.dot-closed_lost { background: #ff6b6b; }
</style>

<template>
  <BaseGraph
    class="graph-panel"
    :loading="loading"
    :isEmpty="!graphData"
    :title="$t('graph.panelTitle')"
    :showRefresh="false"
    :showFullscreen="false"
    @refresh="$emit('refresh')"
    @fullscreen="$emit('toggle-maximize')"
  >
    <template #actions>
      <button
        type="button"
        class="bg-btn"
        @click="$emit('refresh')"
        :disabled="loading"
        :title="$t('graph.refreshGraph')"
        :aria-label="$t('graph.refreshGraph')"
      >
        <span :class="{ 'spinning': loading }" aria-hidden="true">↻</span>
        <span class="bg-btn-text">{{ t('common.refresh') }}</span>
      </button>
      <button
        type="button"
        class="bg-btn"
        @click="$emit('toggle-maximize')"
        :title="$t('graph.toggleMaximize')"
        :aria-label="$t('graph.toggleMaximize')"
      >
        <span aria-hidden="true">⛶</span>
      </button>
    </template>

    <!-- 主体：图谱画布 + 详情面板 + 图例 + 边标签开关 -->
    <div class="graph-container" ref="graphContainer">
      <!-- 图谱可视化 -->
      <div class="graph-view">
        <svg ref="graphSvg" class="graph-svg"></svg>

        <!-- 模拟中提示 -->
        <div v-if="isSimulating" class="graph-building-hint">
          <div class="memory-icon-wrapper">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="memory-icon">
              <path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96.44 2.5 2.5 0 0 1-2.96-3.08 3 3 0 0 1-.34-5.58 2.5 2.5 0 0 1 1.32-4.24 2.5 2.5 0 0 1 4.44-4.04z" />
              <path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96.44 2.5 2.5 0 0 0 2.96-3.08 3 3 0 0 0 .34-5.58 2.5 2.5 0 0 0-1.32-4.24 2.5 2.5 0 0 0-4.44-4.04z" />
            </svg>
          </div>
          {{ isSimulating ? $t('graph.graphMemoryRealtime') : $t('graph.realtimeUpdating') }}
        </div>

        <!-- 模拟结束后的提示 -->
        <div v-if="showSimulationFinishedHint" class="graph-building-hint finished-hint">
          <div class="hint-icon-wrapper">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="hint-icon">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="12" y1="16" x2="12" y2="12"></line>
              <line x1="12" y1="8" x2="12.01" y2="8"></line>
            </svg>
          </div>
          <span class="hint-text">{{ $t('graph.pendingContentHint') }}</span>
          <button type="button" class="hint-close-btn" @click="dismissFinishedHint" :title="$t('graph.closeHint')" :aria-label="$t('graph.closeHint')">
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>

        <!-- 节点/边详情面板 -->
        <div v-if="selectedItem" class="detail-panel">
          <div class="detail-panel-header">
            <span class="detail-title">{{ selectedItem.type === 'node' ? $t('graph.nodeDetails') : $t('graph.relationship') }}</span>
            <span v-if="selectedItem.type === 'node'" class="detail-type-badge" :style="{ background: selectedItem.color, color: '#fff' }">
              {{ selectedItem.data?.attributes?.node_type_label || NODE_TYPE_LABELS[selectedItem.entityType] || selectedItem.entityType }}
            </span>
            <button type="button" class="detail-close" @click="closeDetailPanel" :aria-label="t('common.close')" :title="t('common.close')">×</button>
          </div>

          <!-- 节点详情 -->
          <div v-if="selectedItem.type === 'node'" class="detail-content">
            <div class="detail-row">
              <span class="detail-label">{{ t('graph.detailLabels.name') }}</span>
              <span class="detail-value">{{ selectedItem.data.name }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">{{ t('graph.detailLabels.uuid') }}</span>
              <span class="detail-value uuid-text">{{ selectedItem.data.uuid }}</span>
            </div>
            <div class="detail-row" v-if="selectedItem.data.created_at">
              <span class="detail-label">{{ t('graph.detailLabels.createdAt') }}</span>
              <span class="detail-value">{{ formatDateTime(selectedItem.data.created_at) }}</span>
            </div>

            <!-- IndustryTrend 节点详情 -->
            <template v-if="selectedNodeType === 'IndustryTrend'">
              <div class="detail-section">
                <div class="section-title">{{ t('graph.nodeTypeLabels.industryTrend') }}</div>
                <div class="detail-row">
                  <span class="detail-label">{{ t('graph.detailLabels.trendName') }}</span>
                  <span class="detail-value">{{ selectedNode.attributes?.trend_name }}</span>
                </div>
                <div class="detail-row">
                  <span class="detail-label">{{ t('graph.detailLabels.trendDescription') }}</span>
                  <span class="detail-value">{{ selectedNode.attributes?.trend_description }}</span>
                </div>
                <div class="detail-row">
                  <span class="detail-label">{{ t('graph.detailLabels.impactArea') }}</span>
                  <span class="detail-value">{{ selectedNode.attributes?.impact_area || t('graph.unspecified') }}</span>
                </div>
                <div class="detail-row related-list" v-if="relatedStrategies.length">
                  <span class="detail-label">{{ t('graph.detailLabels.drivenByTrend') }}</span>
                  <ul class="related-items">
                    <li v-for="s in relatedStrategies" :key="s.uuid">{{ s.name }}</li>
                  </ul>
                </div>
              </div>
            </template>

            <!-- CurrentMeasure 节点详情 -->
            <template v-if="selectedNodeType === 'CurrentMeasure'">
              <div class="detail-section">
                <div class="section-title">{{ t('graph.nodeTypeLabels.currentMeasure') }}</div>
                <div class="detail-row">
                  <span class="detail-label">{{ t('graph.detailLabels.measureName') }}</span>
                  <span class="detail-value">{{ selectedNode.attributes?.measure_name }}</span>
                </div>
                <div class="detail-row">
                  <span class="detail-label">{{ t('graph.detailLabels.measureDescription') }}</span>
                  <span class="detail-value">{{ selectedNode.attributes?.measure_description }}</span>
                </div>
                <div class="detail-row">
                  <span class="detail-label">{{ t('graph.detailLabels.effectiveness') }}</span>
                  <span class="detail-value">{{ selectedNode.attributes?.effectiveness || t('graph.unknown') }}</span>
                </div>
                <div class="detail-row related-list" v-if="relatedPains.length">
                  <span class="detail-label">{{ t('graph.detailLabels.addressedPains') }}</span>
                  <ul class="related-items">
                    <li v-for="p in relatedPains" :key="p.uuid">{{ p.name }}</li>
                  </ul>
                </div>
              </div>
            </template>

            <!-- ProjectContext 节点详情 -->
            <template v-if="selectedNodeType === 'ProjectContext'">
              <div class="detail-section">
                <div class="section-title">{{ t('graph.nodeTypeLabels.projectContext') }}</div>
                <div class="detail-row">
                  <span class="detail-label">{{ t('graph.detailLabels.contextType') }}</span>
                  <span class="detail-value">{{ getContextTypeLabel(selectedNode.attributes?.context_type) }}</span>
                </div>
                <div class="detail-row">
                  <span class="detail-label">{{ t('graph.detailLabels.contextText') }}</span>
                  <span class="detail-value">{{ selectedNode.attributes?.context_text }}</span>
                </div>
                <div class="detail-row" v-if="selectedNode.attributes?.rationale">
                  <span class="detail-label">{{ t('graph.detailLabels.rationale') }}</span>
                  <span class="detail-value">{{ selectedNode.attributes?.rationale }}</span>
                </div>
                <div class="detail-row related-list" v-if="relatedStrategies.length">
                  <span class="detail-label">{{ t('graph.detailLabels.relatedStrategies') }}</span>
                  <ul class="related-items">
                    <li v-for="s in relatedStrategies" :key="s.uuid">{{ s.name }}</li>
                  </ul>
                </div>
                <div class="detail-row related-list" v-if="relatedTrendsAndMeasures.length">
                  <span class="detail-label">{{ t('graph.detailLabels.reframedTrends') }}</span>
                  <ul class="related-items">
                    <li v-for="t in relatedTrendsAndMeasures" :key="t.uuid">{{ t.name }}</li>
                  </ul>
                </div>
                <div class="detail-row related-list" v-if="relatedAgendas.length">
                  <span class="detail-label">{{ t('graph.detailLabels.addressedAgendas') }}</span>
                  <ul class="related-items">
                    <li v-for="a in relatedAgendas" :key="a.uuid">{{ a.name }}</li>
                  </ul>
                </div>
              </div>
            </template>

            <!-- StakeholderAgenda 节点详情 -->
            <template v-if="selectedNodeType === 'StakeholderAgenda'">
              <div class="detail-section">
                <div class="section-title">{{ t('graph.nodeTypeLabels.stakeholderAgenda') }}</div>
                <div class="detail-row">
                  <span class="detail-label">{{ t('graph.detailLabels.agendaText') }}</span>
                  <span class="detail-value">{{ selectedNode.attributes?.agenda_text }}</span>
                </div>
                <div class="detail-row">
                  <span class="detail-label">{{ t('graph.detailLabels.type') }}</span>
                  <span class="detail-value">{{ selectedNode.attributes?.agenda_type === 'business' ? t('graph.agendaType.business') : t('graph.agendaType.personal') }}</span>
                </div>
                <div class="detail-row">
                  <span class="detail-label">{{ t('graph.detailLabels.stakeholder') }}</span>
                  <span class="detail-value">{{ selectedNode.attributes?.stakeholder_name }}</span>
                </div>
                <div class="detail-row related-list" v-if="relatedTasks.length">
                  <span class="detail-label">{{ t('graph.detailLabels.relatedTasks') }}</span>
                  <ul class="related-items">
                    <li v-for="t in relatedTasks" :key="t.uuid">{{ t.name }}</li>
                  </ul>
                </div>
              </div>
            </template>

            <!-- Task 节点详情 -->
            <template v-if="selectedNodeType === 'Task'">
              <div class="detail-section">
                <div class="section-title">{{ t('graph.nodeTypeLabels.task') }}</div>
                <div class="detail-row">
                  <span class="detail-label">{{ t('graph.detailLabels.title') }}</span>
                  <span class="detail-value">{{ selectedNode.attributes?.title }}</span>
                </div>
                <div class="detail-row">
                  <span class="detail-label">{{ t('common.priority') }}</span>
                  <span class="detail-value">{{ selectedNode.attributes?.priority }}</span>
                </div>
                <div class="detail-row">
                  <span class="detail-label">{{ t('graph.detailLabels.dueDate') }}</span>
                  <span class="detail-value">{{ selectedNode.attributes?.due_date || t('graph.unspecified') }}</span>
                </div>
                <div class="detail-row">
                  <span class="detail-label">{{ t('common.status') }}</span>
                  <span class="detail-value">{{ selectedNode.attributes?.status }}</span>
                </div>
                <div class="detail-row" v-if="selectedNode.attributes?.description">
                  <span class="detail-label">{{ t('common.description') }}</span>
                  <span class="detail-value">{{ selectedNode.attributes?.description }}</span>
                </div>
                <div class="detail-row related-list" v-if="relatedStakeholders.length">
                  <span class="detail-label">{{ t('graph.detailLabels.relatedStakeholders') }}</span>
                  <ul class="related-items">
                    <li v-for="s in relatedStakeholders" :key="s.uuid">{{ s.name }}</li>
                  </ul>
                </div>
                <div class="detail-row related-list" v-if="relatedGoals.length">
                  <span class="detail-label">{{ t('graph.detailLabels.relatedGoals') }}</span>
                  <ul class="related-items">
                    <li v-for="g in relatedGoals" :key="g.uuid">{{ g.name }}</li>
                  </ul>
                </div>
              </div>
            </template>

            <!-- Properties（仅对非 5 类扩展节点显示通用属性列表）-->
            <div class="detail-section" v-if="showGenericProperties && selectedItem.data.attributes && Object.keys(selectedItem.data.attributes).length > 0">
              <div class="section-title">{{ t('graph.detailLabels.properties') }}</div>
              <div class="properties-list">
                <div v-for="(value, key) in selectedItem.data.attributes" :key="key" class="property-item">
                  <span class="property-key">{{ key }}:</span>
                  <span class="property-value">{{ value || 'None' }}</span>
                </div>
              </div>
            </div>

            <!-- Summary -->
            <div class="detail-section" v-if="selectedItem.data.summary">
              <div class="section-title">{{ t('graph.detailLabels.summary') }}</div>
              <div class="summary-text">{{ selectedItem.data.summary }}</div>
            </div>

            <!-- Labels -->
            <div class="detail-section" v-if="selectedItem.data.labels && selectedItem.data.labels.length > 0">
              <div class="section-title">{{ t('graph.detailLabels.labels') }}</div>
              <div class="labels-list">
                <span v-for="label in selectedItem.data.labels" :key="label" class="label-tag">
                  {{ label }}
                </span>
              </div>
            </div>
          </div>

          <!-- 边详情 -->
          <div v-else class="detail-content">
            <!-- 自环组详情 -->
            <template v-if="selectedItem.data.isSelfLoopGroup">
              <div class="edge-relation-header self-loop-header">
                {{ t('graph.selfLoopRelation', { name: selectedItem.data.source_name }) }}
                <span class="self-loop-count">{{ t('graph.itemsCount', { count: selectedItem.data.selfLoopCount }) }}</span>
              </div>

              <div class="self-loop-list">
                <div
                  v-for="(loop, idx) in selectedItem.data.selfLoopEdges"
                  :key="loop.uuid || idx"
                  class="self-loop-item"
                  :class="{ expanded: expandedSelfLoops.has(loop.uuid || idx) }"
                >
                  <button
                    type="button"
                    class="self-loop-item-header"
                    @click="toggleSelfLoop(loop.uuid || idx)"
                    :aria-expanded="expandedSelfLoops.has(loop.uuid || idx)"
                    :aria-label="t('graph.expandSelfLoop', { name: loop.attributes?.edge_type_label || edgeTypeLabels[loop.name] || loop.name || loop.fact_type || t('graph.edgeTypeLabels.related') })"
                  >
                    <span class="self-loop-index">#{{ idx + 1 }}</span>
                    <span class="self-loop-name">{{ loop.attributes?.edge_type_label || edgeTypeLabels[loop.name] || loop.name || loop.fact_type || t('graph.edgeTypeLabels.related') }}</span>
                    <span class="self-loop-toggle" aria-hidden="true">{{ expandedSelfLoops.has(loop.uuid || idx) ? '−' : '+' }}</span>
                  </button>

                  <div class="self-loop-item-content" v-show="expandedSelfLoops.has(loop.uuid || idx)">
                    <div class="detail-row" v-if="loop.uuid">
                      <span class="detail-label">{{ t('graph.detailLabels.uuid') }}</span>
                      <span class="detail-value uuid-text">{{ loop.uuid }}</span>
                    </div>
                    <div class="detail-row" v-if="loop.fact">
                      <span class="detail-label">{{ t('graph.detailLabels.fact') }}</span>
                      <span class="detail-value fact-text">{{ loop.fact }}</span>
                    </div>
                    <div class="detail-row" v-if="loop.fact_type">
                      <span class="detail-label">{{ t('graph.detailLabels.type') }}</span>
                      <span class="detail-value">{{ loop.attributes?.edge_type_label || edgeTypeLabels[loop.fact_type] || loop.fact_type }}</span>
                    </div>
                    <div class="detail-row" v-if="loop.created_at">
                      <span class="detail-label">{{ t('graph.detailLabels.createdAt') }}</span>
                      <span class="detail-value">{{ formatDateTime(loop.created_at) }}</span>
                    </div>
                    <div v-if="loop.episodes && loop.episodes.length > 0" class="self-loop-episodes">
                      <span class="detail-label">{{ t('graph.detailLabels.episodes') }}</span>
                      <div class="episodes-list compact">
                        <span v-for="ep in loop.episodes" :key="ep" class="episode-tag small">{{ ep }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </template>

            <!-- 普通边详情 -->
            <template v-else>
              <div class="edge-relation-header">
                {{ selectedItem.data.source_name }} → {{ selectedItem.data.attributes?.edge_type_label || edgeTypeLabels[selectedItem.data.name] || selectedItem.data.name || t('graph.edgeTypeLabels.related') }} → {{ selectedItem.data.target_name }}
              </div>

              <div class="detail-row">
                <span class="detail-label">{{ t('graph.detailLabels.uuid') }}</span>
                <span class="detail-value uuid-text">{{ selectedItem.data.uuid }}</span>
              </div>
              <div class="detail-row">
                <span class="detail-label">{{ t('graph.detailLabels.labels') }}</span>
                <span class="detail-value">{{ selectedItem.data.attributes?.edge_type_label || edgeTypeLabels[selectedItem.data.name] || selectedItem.data.name || t('graph.edgeTypeLabels.related') }}</span>
              </div>
              <div class="detail-row">
                <span class="detail-label">{{ t('graph.detailLabels.type') }}</span>
                <span class="detail-value">{{ selectedItem.data.attributes?.edge_type_label || edgeTypeLabels[selectedItem.data.fact_type] || selectedItem.data.fact_type || t('graph.unknown') }}</span>
              </div>
              <div class="detail-row" v-if="selectedItem.data.fact">
                <span class="detail-label">{{ t('graph.detailLabels.fact') }}</span>
                <span class="detail-value fact-text">{{ selectedItem.data.fact }}</span>
              </div>

              <!-- Episodes -->
              <div class="detail-section" v-if="selectedItem.data.episodes && selectedItem.data.episodes.length > 0">
                <div class="section-title">{{ t('graph.detailLabels.episodes') }}</div>
                <div class="episodes-list">
                  <span v-for="ep in selectedItem.data.episodes" :key="ep" class="episode-tag">
                    {{ ep }}
                  </span>
                </div>
              </div>

              <div class="detail-row" v-if="selectedItem.data.created_at">
                <span class="detail-label">{{ t('graph.detailLabels.createdAt') }}</span>
                <span class="detail-value">{{ formatDateTime(selectedItem.data.created_at) }}</span>
              </div>
              <div class="detail-row" v-if="selectedItem.data.valid_at">
                <span class="detail-label">{{ t('graph.detailLabels.validAt') }}</span>
                <span class="detail-value">{{ formatDateTime(selectedItem.data.valid_at) }}</span>
              </div>
            </template>
          </div>
        </div>
      </div>

      <!-- 底部图例 (Bottom Left) -->
      <div v-if="graphData && entityTypes.length" class="graph-legend">
        <span class="legend-title">{{ t('graph.entityTypes') }}</span>
        <div class="legend-items">
          <div class="legend-item" v-for="type in entityTypes" :key="type.name">
            <span class="legend-dot" :style="{ background: type.color }"></span>
            <span class="legend-label">{{ type.name }}</span>
          </div>
        </div>
      </div>

      <!-- 视图筛选工具栏 (Top Left) -->
      <div v-if="graphData" class="graph-view-filter" role="group" :aria-label="t('graph.viewFilter')">
        <button type="button" :class="{ active: viewFilter === 'all' }" @click="setViewFilter('all')">{{ t('graph.viewFilterOptions.all') }}</button>
        <button type="button" :class="{ active: viewFilter === 'strategy' }" @click="setViewFilter('strategy')">{{ t('graph.viewFilterOptions.strategy') }}</button>
        <button type="button" :class="{ active: viewFilter === 'stakeholder' }" @click="setViewFilter('stakeholder')">{{ t('graph.viewFilterOptions.stakeholder') }}</button>
        <button type="button" :class="{ active: viewFilter === 'task' }" @click="setViewFilter('task')">{{ t('graph.viewFilterOptions.task') }}</button>
      </div>

      <!-- 显示边标签开关 -->
      <div v-if="graphData" class="edge-labels-toggle">
        <label class="toggle-switch">
          <input type="checkbox" v-model="showEdgeLabels" :aria-label="t('graph.showEdgeLabels')" aria-labelledby="edge-labels-toggle-label" />
          <span class="slider" aria-hidden="true"></span>
        </label>
        <span class="toggle-label" id="edge-labels-toggle-label">{{ t('graph.showEdgeLabels') }}</span>
      </div>
    </div>
  </BaseGraph>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import * as d3 from 'd3'
import BaseGraph from './BaseGraph.vue'

const { t } = useI18n()

const props = defineProps({
  graphData: Object,
  loading: Boolean,
  isSimulating: Boolean
})

const emit = defineEmits(['refresh', 'toggle-maximize'])

const graphContainer = ref(null)
const graphSvg = ref(null)
const selectedItem = ref(null)
const showEdgeLabels = ref(true) // 默认显示边标签
const expandedSelfLoops = ref(new Set()) // 展开的自环项
const showSimulationFinishedHint = ref(false) // 模拟结束后的提示
const wasSimulating = ref(false) // 追踪之前是否在模拟中

// 节点类型中文标签映射（11 类，覆盖 6 核心 + 5 扩展）
const NODE_TYPE_LABELS = computed(() => ({
  'StrategicInitiative': t('graph.nodeTypeLabels.strategicInitiative'),
  'BusinessGoal': t('graph.nodeTypeLabels.businessGoal'),
  'PainPoint': t('graph.nodeTypeLabels.painPoint'),
  'DecisionStage': t('graph.nodeTypeLabels.decisionStage'),
  'Stakeholder': t('graph.nodeTypeLabels.stakeholder'),
  'Organization': t('graph.nodeTypeLabels.organization'),
  'IndustryTrend': t('graph.nodeTypeLabels.industryTrend'),
  'CurrentMeasure': t('graph.nodeTypeLabels.currentMeasure'),
  'ProjectContext': t('graph.nodeTypeLabels.projectContext'),
  'StakeholderAgenda': t('graph.nodeTypeLabels.stakeholderAgenda'),
  'Task': t('graph.nodeTypeLabels.task'),
  'Entity': t('graph.nodeTypeLabels.entity'),
  'Person': t('graph.nodeTypeLabels.person'),
}))

// 节点类型配色映射（11 类，保持现有 6 类原配色 + 新增 5 类扩展配色）
const NODE_TYPE_COLORS = {
  'StrategicInitiative': '#FF6B35',
  'BusinessGoal': '#004E89',
  'PainPoint': '#C5283D',
  'DecisionStage': '#7B2D8E',
  'Stakeholder': '#1A936F',
  'Organization': '#E9724C',
  'IndustryTrend': '#0EA5E9',
  'CurrentMeasure': '#38BDF8',
  'ProjectContext': '#F97316',
  'StakeholderAgenda': '#A855F7',
  'Task': '#10B981',
}

// 未知类型的兜底调色板（保持原 colors 数组前 6 项以兼容历史视觉）
const FALLBACK_COLORS = ['#FF6B35', '#004E89', '#7B2D8E', '#1A936F', '#C5283D', '#E9724C', '#3498db', '#9b59b6', '#27ae60', '#f39c12']

// 边类型中文标签映射（21 类，覆盖 12 核心 + 9 扩展）
const edgeTypeLabels = computed(() => ({
  // 现有 12 类核心关系
  'REPORTS_TO': t('graph.edgeTypeLabels.reportsTo'),
  'DRIVES_GOAL': t('graph.edgeTypeLabels.drivesGoal'),
  'ADDRESSES_PAIN': t('graph.edgeTypeLabels.addressesPain'),
  'SUPPORTS': t('graph.edgeTypeLabels.supports'),
  'OPPOSES': t('graph.edgeTypeLabels.opposes'),
  'RESPONSIBLE_FOR': t('graph.edgeTypeLabels.responsibleFor'),
  'APPROVES': t('graph.edgeTypeLabels.approves'),
  'PARTICIPATES_IN': t('graph.edgeTypeLabels.participatesIn'),
  'INFLUENCES': t('graph.edgeTypeLabels.influences'),
  'OWNS_INITIATIVE': t('graph.edgeTypeLabels.ownsInitiative'),
  'PROCUREMENT_METHOD': t('graph.edgeTypeLabels.procurementMethod'),
  'PART_OF': t('graph.edgeTypeLabels.partOf'),
  'HAS_ROLE': t('graph.edgeTypeLabels.hasRole'),
  'WORKS_AT': t('graph.edgeTypeLabels.worksAt'),
  'LOCATED_IN': t('graph.edgeTypeLabels.locatedIn'),
  'RELATED': t('graph.edgeTypeLabels.related'),
  'RELATED_TO': t('graph.edgeTypeLabels.relatedTo'),
  'SELF_LOOP': t('graph.edgeTypeLabels.selfLoop'),
  // 新增 9 类扩展关系
  'DRIVEN_BY_TREND': t('graph.edgeTypeLabels.drivenByTrend'),
  'GOAL_ALIGNS_INITIATIVE': t('graph.edgeTypeLabels.goalAlignsInitiative'),
  'MEASURE_ADDRESSES_PAIN': t('graph.edgeTypeLabels.measureAddressesPain'),
  'ALIGNS_WITH': t('graph.edgeTypeLabels.alignsWith'),
  'TEACHING_REFRAMES': t('graph.edgeTypeLabels.teachingReframes'),
  'ASSIGNED_TO': t('graph.edgeTypeLabels.assignedTo'),
  'CONTRIBUTES_TO': t('graph.edgeTypeLabels.contributesTo'),
  'HAS_AGENDA': t('graph.edgeTypeLabels.hasAgenda'),
  'ADDRESSES_AGENDA': t('graph.edgeTypeLabels.addressesAgenda'),
  'TARGETS_AGENDA': t('graph.edgeTypeLabels.targetsAgenda'),
}))

// 视图筛选配置：all 显示全部；其他键定义允许显示的节点 labels
// strategy（战略与Teaching）：合并自原"仅战略"+"仅Teaching"，覆盖 3-3-3 战略（IndustryTrend/PainPoint/CurrentMeasure）
// + 战略举措/业务目标 + 三个WHY（ProjectContext），节点间关联边自动保留
const VIEW_FILTERS = {
  all: null,
  strategy: ['StrategicInitiative', 'BusinessGoal', 'PainPoint', 'IndustryTrend', 'CurrentMeasure', 'ProjectContext'],
  stakeholder: ['Stakeholder', 'Organization', 'StakeholderAgenda'],
  task: ['Task', 'Stakeholder', 'BusinessGoal'],
}

const viewFilter = ref('all')

const setViewFilter = (filter) => {
  viewFilter.value = filter
}

// 关闭模拟结束提示
const dismissFinishedHint = () => {
  showSimulationFinishedHint.value = false
}

// 监听 isSimulating 变化，检测模拟结束
watch(() => props.isSimulating, (newValue, oldValue) => {
  if (wasSimulating.value && !newValue) {
    // 从模拟中变为非模拟状态，显示结束提示
    showSimulationFinishedHint.value = true
  }
  wasSimulating.value = newValue
}, { immediate: true })

// 切换自环项展开/折叠状态
const toggleSelfLoop = (id) => {
  const newSet = new Set(expandedSelfLoops.value)
  if (newSet.has(id)) {
    newSet.delete(id)
  } else {
    newSet.add(id)
  }
  expandedSelfLoops.value = newSet
}

// 前端筛选后的图谱数据：根据 viewFilter 过滤节点和边，不重新请求后端
const filteredGraphData = computed(() => {
  const raw = props.graphData
  if (!raw) return raw
  if (!viewFilter.value || viewFilter.value === 'all') return raw
  const allowedTypes = VIEW_FILTERS[viewFilter.value]
  if (!allowedTypes) return raw

  const nodes = (raw.nodes || []).filter(n => {
    const labels = n.labels || []
    return labels.some(l => allowedTypes.includes(l))
  })
  const allowedUuids = new Set(nodes.map(n => n.uuid))
  const edges = (raw.edges || []).filter(e => {
    const src = e.source_node_uuid || e.source
    const tgt = e.target_node_uuid || e.target
    return allowedUuids.has(src) && allowedUuids.has(tgt)
  })

  return { ...raw, nodes, edges, node_count: nodes.length, edge_count: edges.length }
})

// 计算实体类型用于图例（基于筛选后的数据，使用 NODE_TYPE_COLORS/LABELS）
const entityTypes = computed(() => {
  if (!filteredGraphData.value?.nodes) return []
  const typeMap = {}
  let fallbackIndex = 0

  filteredGraphData.value.nodes.forEach(node => {
    const type = node.labels?.find(l => l !== 'Entity') || 'Entity'
    if (!typeMap[type]) {
      const label = node.attributes?.node_type_label || NODE_TYPE_LABELS.value[type] || type
      const color = NODE_TYPE_COLORS[type] || FALLBACK_COLORS[fallbackIndex++ % FALLBACK_COLORS.length]
      typeMap[type] = { name: label, originalName: type, count: 0, color }
    }
    typeMap[type].count++
  })
  return Object.values(typeMap)
})

// 当前选中节点数据（便于模板访问）
const selectedNode = computed(() => {
  if (!selectedItem.value || selectedItem.value.type !== 'node') return null
  return selectedItem.value.data
})

// 当前选中节点的类型（取第一个非 Entity 标签）
const selectedNodeType = computed(() => {
  if (!selectedNode.value) return null
  const labels = selectedNode.value.labels || []
  return labels.find(l => l !== 'Entity') || labels[0] || null
})

// ProjectContext 背景类型中文映射
function getContextTypeLabel(type) {
  const map = { why: t('insight.whyChange'), why_now: t('insight.whyNow'), why_us: t('insight.whyUs') }
  return map[type] || type || ''
}

// 通过当前图谱 edges 反向查找关联节点（使用原始 props.graphData，避免筛选影响）
function getRelatedNodes(targetUuid, edgeTypes = []) {
  if (!targetUuid || !props.graphData) return []
  const edges = props.graphData.edges || []
  const nodes = props.graphData.nodes || []
  const relatedUuids = new Set()

  for (const e of edges) {
    const src = e.source_node_uuid || e.source
    const tgt = e.target_node_uuid || e.target
    const eType = e.name || e.fact_type || ''
    if (edgeTypes.length && !edgeTypes.includes(eType)) continue
    if (tgt === targetUuid) relatedUuids.add(src)
    if (src === targetUuid) relatedUuids.add(tgt)
  }

  return nodes.filter(n => relatedUuids.has(n.uuid))
}

// 各类关联节点 computed
const relatedStrategies = computed(() => {
  if (!selectedNode.value) return []
  return getRelatedNodes(selectedNode.value.uuid, ['DRIVEN_BY_TREND', 'GOAL_ALIGNS_INITIATIVE', 'ALIGNS_WITH'])
    .filter(n => (n.labels || []).includes('StrategicInitiative'))
})

const relatedPains = computed(() => {
  if (!selectedNode.value) return []
  return getRelatedNodes(selectedNode.value.uuid, ['MEASURE_ADDRESSES_PAIN'])
    .filter(n => (n.labels || []).includes('PainPoint'))
})

const relatedTrendsAndMeasures = computed(() => {
  if (!selectedNode.value) return []
  return getRelatedNodes(selectedNode.value.uuid, ['TEACHING_REFRAMES'])
    .filter(n => (n.labels || []).some(l => ['IndustryTrend', 'CurrentMeasure'].includes(l)))
})

const relatedAgendas = computed(() => {
  if (!selectedNode.value) return []
  return getRelatedNodes(selectedNode.value.uuid, ['ADDRESSES_AGENDA', 'HAS_AGENDA'])
    .filter(n => (n.labels || []).includes('StakeholderAgenda'))
})

const relatedTasks = computed(() => {
  if (!selectedNode.value) return []
  return getRelatedNodes(selectedNode.value.uuid, ['TARGETS_AGENDA', 'ASSIGNED_TO'])
    .filter(n => (n.labels || []).includes('Task'))
})

const relatedStakeholders = computed(() => {
  if (!selectedNode.value) return []
  return getRelatedNodes(selectedNode.value.uuid, ['ASSIGNED_TO', 'HAS_AGENDA', 'REPORTS_TO', 'INFLUENCES'])
    .filter(n => (n.labels || []).includes('Stakeholder'))
})

const relatedGoals = computed(() => {
  if (!selectedNode.value) return []
  return getRelatedNodes(selectedNode.value.uuid, ['CONTRIBUTES_TO'])
    .filter(n => (n.labels || []).includes('BusinessGoal'))
})

// 5 类扩展节点类型集合，用于在详情面板隐藏通用 Properties 区段
const EXTENDED_NODE_TYPES = ['IndustryTrend', 'CurrentMeasure', 'ProjectContext', 'StakeholderAgenda', 'Task']
const showGenericProperties = computed(() => {
  if (!selectedNode.value) return true
  const labels = selectedNode.value.labels || []
  return !labels.some(l => EXTENDED_NODE_TYPES.includes(l))
})

// 格式化时间
const formatDateTime = (dateStr) => {
  if (!dateStr) return ''
  try {
    const date = new Date(dateStr)
    return date.toLocaleString('zh-CN', {
      month: 'long',
      day: 'numeric',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: false
    })
  } catch {
    return dateStr
  }
}

const closeDetailPanel = () => {
  selectedItem.value = null
  expandedSelfLoops.value = new Set() // 重置展开状态
}

let currentSimulation = null
let linkLabelsRef = null
let linkLabelBgRef = null

const renderGraph = () => {
  if (!graphSvg.value || !filteredGraphData.value) return

  // 停止之前的仿真
  if (currentSimulation) {
    currentSimulation.stop()
  }

  const container = graphContainer.value
  if (!container) return
  // 容器尺寸为0时使用默认值，避免SVG渲染为0x0导致空白
  const width = container.clientWidth || 600
  const height = container.clientHeight || 400

  const svg = d3.select(graphSvg.value)
    .attr('width', width)
    .attr('height', height)
    .attr('viewBox', `0 0 ${width} ${height}`)

  svg.selectAll('*').remove()

  const nodesData = filteredGraphData.value.nodes || []
  const edgesData = filteredGraphData.value.edges || []

  if (nodesData.length === 0) return

  // Prep data
  const nodeMap = {}
  nodesData.forEach(n => nodeMap[n.uuid] = n)

  const nodes = nodesData.map(n => ({
    id: n.uuid,
    name: n.name || t('graph.unnamed'),
    type: n.labels?.find(l => l !== 'Entity') || 'Entity',
    rawData: n
  }))

  const nodeIds = new Set(nodes.map(n => n.id))

  // 处理边数据，计算同一对节点间的边数量和索引
  const edgePairCount = {}
  const selfLoopEdges = {} // 按节点分组的自环边
  const tempEdges = edgesData
    .filter(e => nodeIds.has(e.source_node_uuid) && nodeIds.has(e.target_node_uuid))

  // 统计每对节点之间的边数量，收集自环边
  tempEdges.forEach(e => {
    if (e.source_node_uuid === e.target_node_uuid) {
      // 自环 - 收集到数组中
      if (!selfLoopEdges[e.source_node_uuid]) {
        selfLoopEdges[e.source_node_uuid] = []
      }
      selfLoopEdges[e.source_node_uuid].push({
        ...e,
        source_name: nodeMap[e.source_node_uuid]?.name,
        target_name: nodeMap[e.target_node_uuid]?.name
      })
    } else {
      const pairKey = [e.source_node_uuid, e.target_node_uuid].sort().join('_')
      edgePairCount[pairKey] = (edgePairCount[pairKey] || 0) + 1
    }
  })

  // 记录当前处理到每对节点的第几条边
  const edgePairIndex = {}
  const processedSelfLoopNodes = new Set() // 已处理的自环节点

  const edges = []

  tempEdges.forEach(e => {
    const isSelfLoop = e.source_node_uuid === e.target_node_uuid

    if (isSelfLoop) {
      // 自环边 - 每个节点只添加一条合并的自环
      if (processedSelfLoopNodes.has(e.source_node_uuid)) {
        return // 已处理过，跳过
      }
      processedSelfLoopNodes.add(e.source_node_uuid)

      const allSelfLoops = selfLoopEdges[e.source_node_uuid]
      const nodeName = nodeMap[e.source_node_uuid]?.name || t('graph.unknown')

      edges.push({
        source: e.source_node_uuid,
        target: e.target_node_uuid,
        type: 'SELF_LOOP',
        name: t('graph.selfLoopName', { count: allSelfLoops.length }),
        curvature: 0,
        isSelfLoop: true,
        rawData: {
          isSelfLoopGroup: true,
          source_name: nodeName,
          target_name: nodeName,
          selfLoopCount: allSelfLoops.length,
          selfLoopEdges: allSelfLoops // 存储所有自环边的详细信息
        }
      })
      return
    }

    const pairKey = [e.source_node_uuid, e.target_node_uuid].sort().join('_')
    const totalCount = edgePairCount[pairKey]
    const currentIndex = edgePairIndex[pairKey] || 0
    edgePairIndex[pairKey] = currentIndex + 1

    // 判断边的方向是否与标准化方向一致（源UUID < 目标UUID）
    const isReversed = e.source_node_uuid > e.target_node_uuid

    // 计算曲率：多条边时分散开，单条边为直线
    let curvature = 0
    if (totalCount > 1) {
      // 均匀分布曲率，确保明显区分
      // 曲率范围根据边数量增加，边越多曲率范围越大
      const curvatureRange = Math.min(1.2, 0.6 + totalCount * 0.15)
      curvature = ((currentIndex / (totalCount - 1)) - 0.5) * curvatureRange * 2

      // 如果边的方向与标准化方向相反，翻转曲率
      // 这样确保所有边在同一参考系下分布，不会因方向不同而重叠
      if (isReversed) {
        curvature = -curvature
      }
    }

    edges.push({
      source: e.source_node_uuid,
      target: e.target_node_uuid,
      type: e.fact_type || e.name || t('graph.edgeTypeLabels.related'),
      name: e.name || e.fact_type || t('graph.edgeTypeLabels.related'),
      curvature,
      isSelfLoop: false,
      pairIndex: currentIndex,
      pairTotal: totalCount,
      rawData: {
        ...e,
        source_name: nodeMap[e.source_node_uuid]?.name,
        target_name: nodeMap[e.target_node_uuid]?.name
      }
    })
  })

  // Color scale
  const colorMap = {}
  entityTypes.value.forEach(t => colorMap[t.originalName] = t.color)
  const getColor = (type) => colorMap[type] || '#999'

  // Simulation - 根据边数量动态调整节点间距
  const simulation = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(edges).id(d => d.id).distance(d => {
      // 根据这对节点之间的边数量动态调整距离
      // 基础距离 150，每多一条边增加 40
      const baseDistance = 150
      const edgeCount = d.pairTotal || 1
      return baseDistance + (edgeCount - 1) * 50
    }))
    .force('charge', d3.forceManyBody().strength(-400))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collide', d3.forceCollide(50))
    // 添加向中心的引力，让独立的节点群聚集到中心区域
    .force('x', d3.forceX(width / 2).strength(0.04))
    .force('y', d3.forceY(height / 2).strength(0.04))

  currentSimulation = simulation

  const g = svg.append('g')

  // Zoom
  svg.call(d3.zoom().extent([[0, 0], [width, height]]).scaleExtent([0.1, 4]).on('zoom', (event) => {
    g.attr('transform', event.transform)
  }))

  // Links - 使用 path 支持曲线
  const linkGroup = g.append('g').attr('class', 'links')

  // 计算曲线路径
  const getLinkPath = (d) => {
    const sx = d.source.x, sy = d.source.y
    const tx = d.target.x, ty = d.target.y

    // 检测自环
    if (d.isSelfLoop) {
      // 自环：绘制一个圆弧从节点出发再返回
      const loopRadius = 30
      // 从节点右侧出发，绕一圈回来
      const x1 = sx + 8  // 起点偏移
      const y1 = sy - 4
      const x2 = sx + 8  // 终点偏移
      const y2 = sy + 4
      // 使用圆弧绘制自环（sweep-flag=1 顺时针）
      return `M${x1},${y1} A${loopRadius},${loopRadius} 0 1,1 ${x2},${y2}`
    }

    if (d.curvature === 0) {
      // 直线
      return `M${sx},${sy} L${tx},${ty}`
    }

    // 计算曲线控制点 - 根据边数量和距离动态调整
    const dx = tx - sx, dy = ty - sy
    const dist = Math.sqrt(dx * dx + dy * dy)
    // 垂直于连线方向的偏移，根据距离比例计算，保证曲线明显可见
    // 边越多，偏移量占距离的比例越大
    const pairTotal = d.pairTotal || 1
    const offsetRatio = 0.25 + pairTotal * 0.05 // 基础25%，每多一条边增加5%
    const baseOffset = Math.max(35, dist * offsetRatio)
    const offsetX = -dy / dist * d.curvature * baseOffset
    const offsetY = dx / dist * d.curvature * baseOffset
    const cx = (sx + tx) / 2 + offsetX
    const cy = (sy + ty) / 2 + offsetY

    return `M${sx},${sy} Q${cx},${cy} ${tx},${ty}`
  }

  // 计算曲线中点（用于标签定位）
  const getLinkMidpoint = (d) => {
    const sx = d.source.x, sy = d.source.y
    const tx = d.target.x, ty = d.target.y

    // 检测自环
    if (d.isSelfLoop) {
      // 自环标签位置：节点右侧
      return { x: sx + 70, y: sy }
    }

    if (d.curvature === 0) {
      return { x: (sx + tx) / 2, y: (sy + ty) / 2 }
    }

    // 二次贝塞尔曲线的中点 t=0.5
    const dx = tx - sx, dy = ty - sy
    const dist = Math.sqrt(dx * dx + dy * dy)
    const pairTotal = d.pairTotal || 1
    const offsetRatio = 0.25 + pairTotal * 0.05
    const baseOffset = Math.max(35, dist * offsetRatio)
    const offsetX = -dy / dist * d.curvature * baseOffset
    const offsetY = dx / dist * d.curvature * baseOffset
    const cx = (sx + tx) / 2 + offsetX
    const cy = (sy + ty) / 2 + offsetY

    // 二次贝塞尔曲线公式 B(t) = (1-t)²P0 + 2(1-t)tP1 + t²P2, t=0.5
    const midX = 0.25 * sx + 0.5 * cx + 0.25 * tx
    const midY = 0.25 * sy + 0.5 * cy + 0.25 * ty

    return { x: midX, y: midY }
  }

  const link = linkGroup.selectAll('path')
    .data(edges)
    .enter().append('path')
    .attr('stroke', '#C0C0C0')
    .attr('stroke-width', 1.5)
    .attr('fill', 'none')
    .style('cursor', 'pointer')
    .on('click', (event, d) => {
      event.stopPropagation()
      // 重置之前选中边的样式
      linkGroup.selectAll('path').attr('stroke', '#C0C0C0').attr('stroke-width', 1.5)
      linkLabelBg.attr('fill', 'rgba(255,255,255,0.95)')
      linkLabels.attr('fill', '#666')
      // 高亮当前选中的边
      d3.select(event.target).attr('stroke', '#3498db').attr('stroke-width', 3)

      selectedItem.value = {
        type: 'edge',
        data: d.rawData
      }
    })

  // Link labels background (白色背景使文字更清晰)
  const linkLabelBg = linkGroup.selectAll('rect')
    .data(edges)
    .enter().append('rect')
    .attr('fill', 'rgba(255,255,255,0.95)')
    .attr('rx', 3)
    .attr('ry', 3)
    .style('cursor', 'pointer')
    .style('pointer-events', 'all')
    .style('display', showEdgeLabels.value ? 'block' : 'none')
    .on('click', (event, d) => {
      event.stopPropagation()
      linkGroup.selectAll('path').attr('stroke', '#C0C0C0').attr('stroke-width', 1.5)
      linkLabelBg.attr('fill', 'rgba(255,255,255,0.95)')
      linkLabels.attr('fill', '#666')
      // 高亮对应的边
      link.filter(l => l === d).attr('stroke', '#3498db').attr('stroke-width', 3)
      d3.select(event.target).attr('fill', 'rgba(52, 152, 219, 0.1)')

      selectedItem.value = {
        type: 'edge',
        data: d.rawData
      }
    })

  // Link labels
  const linkLabels = linkGroup.selectAll('text')
    .data(edges)
    .enter().append('text')
    .text(d => d.rawData?.attributes?.edge_type_label || edgeTypeLabels.value[d.name] || d.name)
    .attr('font-size', '9px')
    .attr('fill', '#666')
    .attr('text-anchor', 'middle')
    .attr('dominant-baseline', 'middle')
    .style('cursor', 'pointer')
    .style('pointer-events', 'all')
    .style('font-family', 'system-ui, sans-serif')
    .style('display', showEdgeLabels.value ? 'block' : 'none')
    .on('click', (event, d) => {
      event.stopPropagation()
      linkGroup.selectAll('path').attr('stroke', '#C0C0C0').attr('stroke-width', 1.5)
      linkLabelBg.attr('fill', 'rgba(255,255,255,0.95)')
      linkLabels.attr('fill', '#666')
      // 高亮对应的边
      link.filter(l => l === d).attr('stroke', '#3498db').attr('stroke-width', 3)
      d3.select(event.target).attr('fill', '#3498db')

      selectedItem.value = {
        type: 'edge',
        data: d.rawData
      }
    })

  // 保存引用供外部控制显隐
  linkLabelsRef = linkLabels
  linkLabelBgRef = linkLabelBg

  // Nodes group
  const nodeGroup = g.append('g').attr('class', 'nodes')

  // Node circles
  const node = nodeGroup.selectAll('circle')
    .data(nodes)
    .enter().append('circle')
    .attr('r', 10)
    .attr('fill', d => getColor(d.type))
    .attr('stroke', '#fff')
    .attr('stroke-width', 2.5)
    .style('cursor', 'pointer')
    .call(d3.drag()
      .on('start', (event, d) => {
        // 只记录位置，不重启仿真（区分点击和拖拽）
        d.fx = d.x
        d.fy = d.y
        d._dragStartX = event.x
        d._dragStartY = event.y
        d._isDragging = false
      })
      .on('drag', (event, d) => {
        // 检测是否真正开始拖拽（移动超过阈值）
        const dx = event.x - d._dragStartX
        const dy = event.y - d._dragStartY
        const distance = Math.sqrt(dx * dx + dy * dy)

        if (!d._isDragging && distance > 3) {
          // 首次检测到真正拖拽，才重启仿真
          d._isDragging = true
          simulation.alphaTarget(0.3).restart()
        }

        if (d._isDragging) {
          d.fx = event.x
          d.fy = event.y
        }
      })
      .on('end', (event, d) => {
        // 只有真正拖拽过才让仿真逐渐停止
        if (d._isDragging) {
          simulation.alphaTarget(0)
        }
        d.fx = null
        d.fy = null
        d._isDragging = false
      })
    )
    .on('click', (event, d) => {
      event.stopPropagation()
      // 重置所有节点样式
      node.attr('stroke', '#fff').attr('stroke-width', 2.5)
      linkGroup.selectAll('path').attr('stroke', '#C0C0C0').attr('stroke-width', 1.5)
      // 高亮选中节点
      d3.select(event.target).attr('stroke', '#E91E63').attr('stroke-width', 4)
      // 高亮与此节点相连的边
      link.filter(l => l.source.id === d.id || l.target.id === d.id)
        .attr('stroke', '#E91E63')
        .attr('stroke-width', 2.5)

      selectedItem.value = {
        type: 'node',
        data: d.rawData,
        entityType: d.type,
        color: getColor(d.type)
      }
    })
    .on('mouseenter', (event, d) => {
      if (!selectedItem.value || selectedItem.value.data?.uuid !== d.rawData.uuid) {
        d3.select(event.target).attr('stroke', '#333').attr('stroke-width', 3)
      }
    })
    .on('mouseleave', (event, d) => {
      if (!selectedItem.value || selectedItem.value.data?.uuid !== d.rawData.uuid) {
        d3.select(event.target).attr('stroke', '#fff').attr('stroke-width', 2.5)
      }
    })

  // Node Labels
  const nodeLabels = nodeGroup.selectAll('text')
    .data(nodes)
    .enter().append('text')
    .text(d => d.name.length > 8 ? d.name.substring(0, 8) + '…' : d.name)
    .attr('font-size', '11px')
    .attr('fill', '#333')
    .attr('font-weight', '500')
    .attr('dx', 14)
    .attr('dy', 4)
    .style('pointer-events', 'none')
    .style('font-family', 'system-ui, sans-serif')

  simulation.on('tick', () => {
    // 更新曲线路径
    link.attr('d', d => getLinkPath(d))

    // 更新边标签位置（无旋转，水平显示更清晰）
    linkLabels.each(function(d) {
      const mid = getLinkMidpoint(d)
      d3.select(this)
        .attr('x', mid.x)
        .attr('y', mid.y)
        .attr('transform', '') // 移除旋转，保持水平
    })

    // 更新边标签背景
    linkLabelBg.each(function(d, i) {
      const mid = getLinkMidpoint(d)
      const textEl = linkLabels.nodes()[i]
      const bbox = textEl.getBBox()
      d3.select(this)
        .attr('x', mid.x - bbox.width / 2 - 4)
        .attr('y', mid.y - bbox.height / 2 - 2)
        .attr('width', bbox.width + 8)
        .attr('height', bbox.height + 4)
        .attr('transform', '') // 移除旋转
    })

    node
      .attr('cx', d => d.x)
      .attr('cy', d => d.y)

    nodeLabels
      .attr('x', d => d.x)
      .attr('y', d => d.y)
  })

  // 点击空白处关闭详情面板
  svg.on('click', () => {
    selectedItem.value = null
    node.attr('stroke', '#fff').attr('stroke-width', 2.5)
    linkGroup.selectAll('path').attr('stroke', '#C0C0C0').attr('stroke-width', 1.5)
    linkLabelBg.attr('fill', 'rgba(255,255,255,0.95)')
    linkLabels.attr('fill', '#666')
  })
}

watch(() => filteredGraphData.value, () => {
  nextTick(renderGraph)
}, { deep: true, immediate: true })

// 视图筛选切换时关闭详情面板，避免显示已被筛选掉的节点
watch(viewFilter, () => {
  closeDetailPanel()
})

// 监听边标签显示开关
watch(showEdgeLabels, (newVal) => {
  if (linkLabelsRef) {
    linkLabelsRef.style('display', newVal ? 'block' : 'none')
  }
  if (linkLabelBgRef) {
    linkLabelBgRef.style('display', newVal ? 'block' : 'none')
  }
})

const handleResize = () => {
  nextTick(renderGraph)
}

onMounted(() => {
  window.addEventListener('resize', handleResize)
  // 组件挂载时如果有数据，立即渲染
  if (props.graphData) {
    nextTick(renderGraph)
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  if (currentSimulation) {
    currentSimulation.stop()
  }
})
</script>

<style scoped>
/* 图谱容器：撑满 BaseGraph body */
.graph-container {
  position: relative;
  width: 100%;
  height: 100%;
  flex: 1;
  min-height: 0;
  background-color: var(--bg-surface, #FAFAFA);
  background-image: radial-gradient(var(--border-strong, #D0D0D0) 1.5px, transparent 1.5px);
  background-size: 24px 24px;
  overflow: hidden;
}

.graph-view, .graph-svg {
  width: 100%;
  height: 100%;
  display: block;
}

/* 自定义工具栏按钮：复用 BaseGraph .bg-btn 样式，扩展业务样式 */
/* 注意：BaseGraph 的 .bg-btn 是 scoped，不会作用到 #actions slot 内容，
   此处显式定义 .bg-btn 基础样式，确保按钮在 slot 中也正确渲染 */
.bg-btn {
  appearance: none;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 6px;
  padding: 4px 8px;
  font-family: var(--font-sans, 'Noto Sans SC', 'PingFang SC', 'Microsoft YaHei', system-ui, sans-serif);
  font-size: var(--fs-md, 14px);
  line-height: 1;
  color: var(--text-muted, #93959D);
  cursor: pointer;
  transition: color 0.15s, border-color 0.15s, background 0.15s;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.bg-btn:hover:not(:disabled) {
  color: var(--accent, #CD5036);
  background: rgba(205, 80, 54, 0.06);
  border-color: rgba(205, 80, 54, 0.2);
}

.bg-btn:focus-visible {
  outline: 2px solid var(--focus-ring, #15171D);
  outline-offset: 2px;
}

.bg-btn:active {
  transform: scale(0.96);
}

.bg-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.bg-btn-text {
  font-size: 12px;
}

.bg-btn .spinning {
  animation: bg-btn-spin 1s linear infinite;
  display: inline-block;
}

@keyframes bg-btn-spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* 更新图谱按钮 - 醒目橙色 */
.bg-btn-rebuild {
  background: #FF4500;
  border-color: #FF4500;
  color: #fff;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.bg-btn-rebuild:hover:not(:disabled) {
  background: #E63E00;
  border-color: #E63E00;
  color: #fff;
}

.bg-btn-rebuild:focus-visible {
  outline: 2px solid #FF4500;
  outline-offset: 2px;
}

.bg-btn-rebuild:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Entity Types Legend - Bottom Left */
.graph-legend {
  position: absolute;
  bottom: 24px;
  left: 24px;
  background: rgba(255,255,255,0.95);
  padding: 12px 16px;
  border-radius: 8px;
  border: 1px solid var(--border, #EAEAEA);
  box-shadow: 0 4px 16px rgba(0,0,0,0.06);
  z-index: 10;
}

.legend-title {
  display: block;
  font-size: 11px;
  font-weight: 600;
  color: var(--accent, #E91E63);
  margin-bottom: 10px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.legend-items {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 16px;
  max-width: 320px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-secondary, #555);
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.legend-label {
  white-space: nowrap;
}

/* Edge Labels Toggle - Top Right */
.edge-labels-toggle {
  position: absolute;
  top: 16px;
  right: 16px;
  display: flex;
  align-items: center;
  gap: 10px;
  background: var(--bg-card, #FFF);
  padding: 8px 14px;
  border-radius: 20px;
  border: 1px solid var(--border-strong, #E0E0E0);
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
  z-index: 10;
}

/* View Filter Toolbar - Top Left */
.graph-view-filter {
  position: absolute;
  top: 16px;
  left: 16px;
  display: flex;
  align-items: center;
  gap: 4px;
  background: var(--bg-card, #FFF);
  padding: 4px;
  border-radius: 8px;
  border: 1px solid var(--border-strong, #E0E0E0);
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
  z-index: 10;
}

.graph-view-filter button {
  appearance: none;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 6px;
  padding: 6px 12px;
  font-family: var(--font-sans, 'Noto Sans SC', 'PingFang SC', 'Microsoft YaHei', system-ui, sans-serif);
  font-size: 12px;
  line-height: 1;
  color: var(--text-muted, #93959D);
  cursor: pointer;
  transition: color 0.15s, background 0.15s, border-color 0.15s;
  white-space: nowrap;
}

.graph-view-filter button:hover:not(.active) {
  color: var(--text-primary, #15171D);
  background: rgba(0, 0, 0, 0.04);
}

.graph-view-filter button:focus-visible {
  outline: 2px solid var(--accent, #CD5036);
  outline-offset: 2px;
}

.graph-view-filter button.active {
  background: #15171D;
  color: #FFF;
  border-color: #15171D;
}

/* Related nodes list inside detail panel */
.related-list {
  flex-direction: column;
  align-items: flex-start;
}

.related-items {
  margin: 4px 0 0;
  padding-left: 18px;
  list-style: disc;
  color: var(--text-primary, #333);
  font-size: 12px;
  line-height: 1.6;
}

.related-items li {
  word-break: break-word;
}

.toggle-switch {
  position: relative;
  display: inline-block;
  width: 40px;
  height: 22px;
}

.toggle-switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.toggle-switch input:focus-visible + .slider {
  box-shadow: 0 0 0 2px var(--accent, #7B2D8E);
}

.slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: var(--border-strong, #E0E0E0);
  border-radius: 22px;
  transition: background-color 0.3s;
}

.slider:before {
  position: absolute;
  content: "";
  height: 16px;
  width: 16px;
  left: 3px;
  bottom: 3px;
  background-color: white;
  border-radius: 50%;
  transition: transform 0.3s;
}

input:checked + .slider {
  background-color: var(--accent, #7B2D8E);
}

input:checked + .slider:before {
  transform: translateX(18px);
}

.toggle-label {
  font-size: 12px;
  color: var(--text-tertiary, #666);
}

/* Detail Panel - Right Side */
.detail-panel {
  position: absolute;
  top: 60px;
  right: 20px;
  width: 320px;
  max-height: calc(100% - 100px);
  background: var(--bg-card, #FFF);
  border: 1px solid var(--border, #EAEAEA);
  border-radius: 10px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.1);
  overflow: hidden;
  font-family: 'Noto Sans SC', system-ui, sans-serif;
  font-size: 13px;
  z-index: 20;
  display: flex;
  flex-direction: column;
}

.detail-panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 16px;
  background: var(--bg-surface, #FAFAFA);
  border-bottom: 1px solid var(--border, #EEE);
  flex-shrink: 0;
}

.detail-title {
  font-weight: 600;
  color: var(--text-primary, #333);
  font-size: 14px;
}

.detail-type-badge {
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 500;
  margin-left: auto;
  margin-right: 12px;
}

.detail-close {
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
  color: var(--text-muted, #999);
  line-height: 1;
  padding: 4px 8px;
  border-radius: 4px;
  transition: color 0.2s, background-color 0.2s;
  touch-action: manipulation;
}

.detail-close:hover {
  color: var(--text-primary, #333);
  background: rgba(0,0,0,0.05);
}

.detail-close:focus-visible {
  outline: 2px solid var(--accent, #7B2D8E);
  outline-offset: 1px;
  color: var(--text-primary, #333);
}

.detail-content {
  padding: 16px;
  overflow-y: auto;
  flex: 1;
}

.detail-row {
  margin-bottom: 12px;
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.detail-label {
  color: var(--text-muted, #888);
  font-size: 12px;
  font-weight: 500;
  min-width: 80px;
}

.detail-value {
  color: var(--text-primary, #333);
  flex: 1;
  word-break: break-word;
}

.detail-value.uuid-text {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: var(--text-tertiary, #666);
}

.detail-value.fact-text {
  line-height: 1.5;
  color: var(--text-secondary, #444);
}

.detail-section {
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px solid var(--border, #F0F0F0);
}

.section-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-tertiary, #666);
  margin-bottom: 10px;
}

.properties-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.property-item {
  display: flex;
  gap: 8px;
}

.property-key {
  color: var(--text-muted, #888);
  font-weight: 500;
  min-width: 90px;
}

.property-value {
  color: var(--text-primary, #333);
  flex: 1;
}

.summary-text {
  line-height: 1.6;
  color: var(--text-secondary, #444);
  font-size: 12px;
}

.labels-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.label-tag {
  display: inline-block;
  padding: 4px 12px;
  background: var(--bg-surface, #F5F5F5);
  border: 1px solid var(--border-strong, #E0E0E0);
  border-radius: 16px;
  font-size: 11px;
  color: var(--text-secondary, #555);
}

.episodes-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.episode-tag {
  display: inline-block;
  padding: 6px 10px;
  background: var(--bg-surface, #F8F8F8);
  border: 1px solid var(--border, #E8E8E8);
  border-radius: 6px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  color: var(--text-tertiary, #666);
  word-break: break-all;
}

/* Edge relation header */
.edge-relation-header {
  background: var(--bg-surface, #F8F8F8);
  padding: 12px;
  border-radius: 8px;
  margin-bottom: 16px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary, #333);
  line-height: 1.5;
  word-break: break-word;
}

/* Building hint */
.graph-building-hint {
  position: absolute;
  bottom: 160px; /* Moved up from 80px */
  left: 50%;
  transform: translateX(-50%);
  background: rgba(0, 0, 0, 0.65);
  backdrop-filter: blur(8px);
  color: #fff;
  padding: 10px 20px;
  border-radius: 30px;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 10px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.1);
  font-weight: 500;
  letter-spacing: 0.5px;
  z-index: 100;
}

.memory-icon-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  animation: breathe 2s ease-in-out infinite;
}

.memory-icon {
  width: 18px;
  height: 18px;
  color: var(--green, #4CAF50);
}

@keyframes breathe {
  0%, 100% { opacity: 0.7; transform: scale(1); filter: drop-shadow(0 0 2px rgba(76, 175, 80, 0.3)); }
  50% { opacity: 1; transform: scale(1.15); filter: drop-shadow(0 0 8px rgba(76, 175, 80, 0.6)); }
}

/* 模拟结束后的提示样式 */
.graph-building-hint.finished-hint {
  background: rgba(0, 0, 0, 0.65);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.finished-hint .hint-icon-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
}

.finished-hint .hint-icon {
  width: 18px;
  height: 18px;
  color: #FFF;
}

.finished-hint .hint-text {
  flex: 1;
  white-space: nowrap;
}

.hint-close-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  background: rgba(255, 255, 255, 0.2);
  border: none;
  border-radius: 50%;
  cursor: pointer;
  color: #FFF;
  transition: background-color 0.2s, transform 0.2s;
  margin-left: 8px;
  flex-shrink: 0;
  touch-action: manipulation;
}

.hint-close-btn:hover {
  background: rgba(255, 255, 255, 0.35);
  transform: scale(1.1);
}

.hint-close-btn:focus-visible {
  outline: 2px solid #FFF;
  outline-offset: 2px;
}

/* Self-loop styles */
/* 自环关系专用绿色主题：保留硬编码色值以维持语义一致性 */
.self-loop-header {
  display: flex;
  align-items: center;
  gap: 8px;
  background: linear-gradient(135deg, #E8F5E9 0%, #F1F8E9 100%);
  border: 1px solid #C8E6C9;
}

.self-loop-count {
  margin-left: auto;
  font-size: 11px;
  color: var(--text-tertiary, #666);
  background: rgba(255,255,255,0.8);
  padding: 2px 8px;
  border-radius: 10px;
}

.self-loop-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.self-loop-item {
  background: var(--bg-surface, #FAFAFA);
  border: 1px solid var(--border, #EAEAEA);
  border-radius: 8px;
}

.self-loop-item-header {
  display: flex;
  width: 100%;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  background: var(--bg-surface, #F5F5F5);
  cursor: pointer;
  transition: background-color 0.2s;
  border: none;
  border-radius: 8px;
  text-align: left;
  font: inherit;
  color: inherit;
  touch-action: manipulation;
}

.self-loop-item-header:hover {
  background: var(--bg-surface, #EEEEEE);
}

.self-loop-item-header:focus-visible {
  outline: 2px solid var(--accent, #7B2D8E);
  outline-offset: -2px;
}

.self-loop-item.expanded .self-loop-item-header {
  background: var(--border, #E8E8E8);
}

.self-loop-index {
  font-size: 10px;
  font-weight: 600;
  color: var(--text-muted, #888);
  background: var(--border-strong, #E0E0E0);
  padding: 2px 6px;
  border-radius: 4px;
}

.self-loop-name {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-primary, #333);
  flex: 1;
}

.self-loop-toggle {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-muted, #888);
  background: var(--border-strong, #E0E0E0);
  border-radius: 4px;
  transition: background-color 0.2s, color 0.2s;
}

.self-loop-item.expanded .self-loop-toggle {
  background: var(--border-strong, #D0D0D0);
  color: var(--text-tertiary, #666);
}

.self-loop-item-content {
  padding: 12px;
  border-top: 1px solid var(--border, #EAEAEA);
}

.self-loop-item-content .detail-row {
  margin-bottom: 8px;
}

.self-loop-item-content .detail-label {
  font-size: 11px;
  min-width: 60px;
}

.self-loop-item-content .detail-value {
  font-size: 12px;
}

.self-loop-episodes {
  margin-top: 8px;
}

.episodes-list.compact {
  flex-direction: row;
  flex-wrap: wrap;
  gap: 4px;
}

.episode-tag.small {
  padding: 3px 6px;
  font-size: 9px;
}

/* 尊重用户的动效偏好设置 */
@media (prefers-reduced-motion: reduce) {
  .bg-btn .spinning,
  .memory-icon-wrapper {
    animation: none;
  }

  .bg-btn,
  .bg-btn-rebuild,
  .detail-close,
  .hint-close-btn,
  .self-loop-item-header,
  .self-loop-toggle,
  .slider,
  .slider:before {
    transition: none;
  }

  .hint-close-btn:hover {
    transform: none;
  }
}
</style>

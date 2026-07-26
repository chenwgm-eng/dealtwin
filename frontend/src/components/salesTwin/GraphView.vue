<template>
  <!-- Tab: 商机图谱（数据全部来自数据库注入，无需构建按钮） -->
  <div class="tab-pane graph-view-pane">
    <!-- 有图谱数据时：展示图谱视图 -->
    <div v-if="graphData" class="graph-panel-wrapper">
      <GraphPanel
        :graphData="graphData"
        :loading="graphLoading"
        @refresh="$emit('refresh')"
        @toggle-maximize="$emit('toggle-maximize')"
      />
      <!-- 节点/边统计摘要 -->
      <div class="build-result-bar">
        <div class="result-item">
          <span class="result-value">{{ graphData.node_count || graphData.nodes?.length || 0 }}</span>
          <span class="result-label">{{ t('graph.entityNodes') }}</span>
        </div>
        <div class="result-item">
          <span class="result-value">{{ graphData.edge_count || graphData.edges?.length || 0 }}</span>
          <span class="result-label">{{ t('graph.relationshipEdges') }}</span>
        </div>
      </div>
    </div>

    <!-- 空状态：无图谱数据 -->
    <div v-else class="graph-empty">
      <div class="empty-icon" aria-hidden="true">◇</div>
      <p class="empty-title">{{ t('graph.noGraphData') }}</p>
      <p class="empty-desc">{{ t('graph.emptyHint') }}</p>
      <button type="button" class="btn-refresh" @click="$emit('refresh')">
        <span aria-hidden="true">↻</span> {{ t('graph.refreshGraph') }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { useI18n } from 'vue-i18n'
import GraphPanel from '../GraphPanel.vue'

const { t } = useI18n()

defineProps({
  graphData: { type: Object, default: null },
  graphLoading: { type: Boolean, default: false },
})

defineEmits([
  'refresh',
  'toggle-maximize',
])
</script>

<style scoped>
.graph-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 60px 24px;
  text-align: center;
  background: var(--bg-card, #FCFBF5);
  border: 1px dashed var(--border-strong, #D7D4CD);
  border-radius: 10px;
}

.empty-icon {
  font-size: 32px;
  color: var(--accent, #CD5036);
  font-weight: 300;
  line-height: 1;
}

.empty-title {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary, #15171D);
}

.empty-desc {
  margin: 0;
  font-size: 12px;
  color: var(--text-tertiary, #807E7E);
  line-height: 1.5;
  max-width: 320px;
}

.btn-refresh {
  margin-top: 8px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 14px;
  background: transparent;
  border: 1px solid var(--border-strong, #D7D4CD);
  border-radius: 6px;
  color: var(--text-secondary, #494A4D);
  font-size: 12px;
  font-family: inherit;
  cursor: pointer;
  transition: border-color 0.15s, color 0.15s;
}

.btn-refresh:hover:not(:disabled) {
  border-color: var(--accent, #CD5036);
  color: var(--accent, #CD5036);
}

.btn-refresh:focus-visible {
  outline: 2px solid var(--focus-ring, #15171D);
  outline-offset: 2px;
}

.build-result-bar {
  display: flex;
  gap: 24px;
  align-items: center;
  padding: 12px 16px;
  background: var(--bg-card, #FCFBF5);
  border: 1px solid var(--border, #E8E8E0);
  border-radius: 8px;
  margin-top: 12px;
}

.result-item {
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.result-value {
  font-family: var(--font-mono, 'JetBrains Mono', monospace);
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary, #15171D);
  font-variant-numeric: tabular-nums;
}

.result-label {
  font-size: 12px;
  color: var(--text-tertiary, #807E7E);
}
</style>

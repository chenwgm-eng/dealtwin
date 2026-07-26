<template>
  <div class="base-graph" role="region" :aria-label="title || t('graph.graphView')">
    <!-- 工具栏 -->
    <div v-if="showToolbar" class="base-graph-toolbar">
      <span class="base-graph-title">{{ title }}</span>
      <div class="base-graph-actions">
        <!-- 自定义工具栏插槽：传入则完全替代默认按钮 -->
        <slot name="actions">
          <button v-if="showRefresh" type="button" class="bg-btn" @click="$emit('refresh')" :aria-label="t('common.refresh')" :title="t('common.refresh')">↻</button>
          <button v-if="showFullscreen" type="button" class="bg-btn" @click="$emit('fullscreen')" :aria-label="t('graph.fullscreen')" :title="t('graph.fullscreen')">⛶</button>
          <button v-if="showExport" type="button" class="bg-btn" @click="$emit('export')" :aria-label="t('graph.export')" :title="t('graph.export')">⬇</button>
        </slot>
      </div>
    </div>
    <!-- 主体:默认插槽 -->
    <div class="base-graph-body">
      <!-- 加载状态 -->
      <div v-if="loading" class="base-graph-loading" aria-live="polite">
        <div class="base-graph-spinner" aria-hidden="true"></div>
        <span>{{ t('common.loading') }}</span>
      </div>
      <!-- 空状态 -->
      <div v-else-if="isEmpty" class="base-graph-empty" role="status">
        <div class="base-graph-empty-icon" aria-hidden="true">◇</div>
        <p>{{ t('graph.noGraphData') }}</p>
        <p class="base-graph-empty-hint">{{ t('graph.buildGraphFirst') }}</p>
      </div>
      <!-- 图谱渲染主体 -->
      <slot v-else></slot>
    </div>
    <!-- 详情面板插槽(可选) -->
    <div v-if="$slots.detail" class="base-graph-detail">
      <slot name="detail"></slot>
    </div>
  </div>
</template>

<script setup>
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

defineProps({
  loading: { type: Boolean, default: false },
  isEmpty: { type: Boolean, default: false },
  title: { type: String, default: '' },
  showToolbar: { type: Boolean, default: true },
  showRefresh: { type: Boolean, default: true },
  showFullscreen: { type: Boolean, default: true },
  showExport: { type: Boolean, default: false },
})

defineEmits(['refresh', 'fullscreen', 'export'])
</script>

<style scoped>
/* ============ 容器 ============ */
.base-graph {
  display: flex;
  flex-direction: column;
  gap: 0;
  background: var(--bg-base, #FFFFFF);
  color: var(--text-primary, #15171D);
  border: 1px solid var(--border, #E8E8E0);
  border-radius: 10px;
  box-shadow: var(--shadow-sm, 0 1px 2px rgba(21, 23, 29, 0.04));
  font-family: var(--font-sans, 'Noto Sans SC', 'PingFang SC', 'Microsoft YaHei', system-ui, sans-serif);
  font-size: var(--fs-base, 13px);
  min-width: 0;
  min-height: 0;
  height: 100%;
}

/* ============ 工具栏 ============ */
.base-graph-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: var(--bg-base, #FFFFFF);
  border-bottom: 1px solid var(--border, #E8E8E0);
  border-radius: 10px 10px 0 0;
  flex-shrink: 0;
}

.base-graph-title {
  flex: 1;
  min-width: 0;
  font-size: var(--fs-md, 14px);
  font-weight: 600;
  color: var(--text-primary, #15171D);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.base-graph-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

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
}

.bg-btn:hover {
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

/* ============ 主体 ============ */
.base-graph-body {
  flex: 1;
  min-height: 0;
  min-width: 0;
  position: relative;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* ============ 加载状态 ============ */
.base-graph-loading {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  background: var(--bg-base, #FFFFFF);
  color: var(--text-secondary, #494A4D);
  font-size: var(--fs-sm, 12px);
  z-index: 1;
}

.base-graph-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid var(--border, #E8E8E0);
  border-top-color: var(--accent, #CD5036);
  border-radius: 50%;
  animation: bg-spin 0.8s linear infinite;
  transform-origin: center;
}

@keyframes bg-spin {
  to { transform: rotate(360deg); }
}

/* ============ 空状态 ============ */
.base-graph-empty {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 24px;
  background: var(--bg-base, #FFFFFF);
  color: var(--text-muted, #93959D);
  text-align: center;
  z-index: 1;
}

.base-graph-empty-icon {
  font-size: 32px;
  font-weight: 300;
  color: var(--accent, #CD5036);
  line-height: 1;
  margin-bottom: 4px;
}

.base-graph-empty p {
  margin: 0;
  font-size: var(--fs-sm, 12px);
  color: var(--text-secondary, #494A4D);
}

.base-graph-empty-hint {
  color: var(--text-muted, #93959D);
  font-size: var(--fs-xs, 11px);
  font-style: italic;
}

/* ============ 详情面板 ============ */
.base-graph-detail {
  border-top: 1px solid var(--border, #E8E8E0);
  background: var(--bg-base, #FFFFFF);
  flex-shrink: 0;
}

/* ============ 动画无障碍 ============ */
@media (prefers-reduced-motion: reduce) {
  .base-graph-spinner {
    animation: none;
  }
  .bg-btn {
    transition: none;
  }
  .bg-btn:active {
    transform: none;
  }
}
</style>

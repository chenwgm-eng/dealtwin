<template>
  <aside class="sales-twin-sidebar" role="navigation" :aria-label="t('sidebar.brandTitle')">
    <!-- 品牌区 -->
    <button
      type="button"
      class="sidebar-brand"
      @click="$emit('go-home')"
      @keydown.enter="$emit('go-home')"
      @keydown.space.prevent="$emit('go-home')"
      :aria-label="t('common.back')"
    >
      <div class="brand-logo" aria-hidden="true">
        <svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
          <rect x="3" y="3" width="11" height="11" rx="3" fill="currentColor" opacity="0.9"/>
          <rect x="18" y="3" width="11" height="11" rx="3" fill="currentColor" opacity="0.55"/>
          <rect x="3" y="18" width="11" height="11" rx="3" fill="currentColor" opacity="0.55"/>
          <rect x="18" y="18" width="11" height="11" rx="3" fill="currentColor" opacity="0.3"/>
        </svg>
      </div>
      <div class="brand-text">
        <span class="brand-title">{{ t('sidebar.brandTitle') }}</span>
        <span class="brand-subtitle">{{ t('sidebar.brandSubtitle') }}</span>
      </div>
    </button>

    <!-- 全局菜单 -->
    <nav class="sidebar-section">
      <div class="sidebar-section-title">{{ t('sidebar.global') }}</div>
      <ul class="sidebar-menu">
        <li>
          <button
            type="button"
            class="sidebar-item"
            :class="{ active: activeMenu === 'dashboard' }"
            @click="$emit('select-menu', 'dashboard')"
            :aria-label="t('sidebar.dashboard')"
          >
            <span class="sidebar-icon" aria-hidden="true">
              <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6">
                <rect x="3" y="3" width="6" height="6" rx="1"/>
                <rect x="11" y="3" width="6" height="6" rx="1"/>
                <rect x="3" y="11" width="6" height="6" rx="1"/>
                <circle cx="14" cy="14" r="3"/>
              </svg>
            </span>
            <span class="sidebar-label">{{ t('sidebar.dashboard') }}</span>
          </button>
        </li>

        <li>
          <button
            type="button"
            class="sidebar-item"
            :class="{ active: activeMenu === 'projects' }"
            @click="$emit('select-menu', 'projects')"
            :aria-label="t('sidebar.opportunityLedger')"
          >
            <span class="sidebar-icon" aria-hidden="true">
              <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6">
                <rect x="3" y="3" width="6" height="6" rx="1.5"/>
                <rect x="11" y="3" width="6" height="6" rx="1.5"/>
                <rect x="3" y="11" width="6" height="6" rx="1.5"/>
                <rect x="11" y="11" width="6" height="6" rx="1.5"/>
              </svg>
            </span>
            <span class="sidebar-label">{{ t('sidebar.opportunityLedger') }}</span>
            <span v-if="projects.length" class="sidebar-count">{{ projects.length }}</span>
          </button>
        </li>
        <li>
          <button
            type="button"
            class="sidebar-item"
            :class="{ active: activeMenu === 'learning' }"
            @click="$emit('select-menu', 'learning')"
            :aria-label="t('sidebar.intelligentEvolution')"
          >
            <span class="sidebar-icon" aria-hidden="true">
              <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6">
                <path d="M10 3.5a3 3 0 00-3 3v.5a3 3 0 00-2 5.2V14a3 3 0 005 2.2A3 3 0 0015 14v-1.8a3 3 0 00-2-5.2v-.5a3 3 0 00-3-3z"/>
                <path d="M10 3.5v13"/>
              </svg>
            </span>
            <span class="sidebar-label">{{ t('sidebar.intelligentEvolution') }}</span>
          </button>
        </li>
        <li>
          <button
            type="button"
            class="sidebar-item"
            :class="{ active: activeMenu === 'agent_jobs' }"
            @click="$emit('select-menu', 'agent_jobs')"
            :aria-label="t('sidebar.agentJobs')"
          >
            <span class="sidebar-icon" aria-hidden="true">
              <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6">
                <circle cx="10" cy="10" r="6"/>
                <path d="M10 6v4l2.5 2"/>
                <path d="M4 4l1.5 1.5M16 4l-1.5 1.5"/>
              </svg>
            </span>
            <span class="sidebar-label">{{ t('sidebar.agentJobs') }}</span>
          </button>
        </li>
      </ul>
    </nav>

    <!-- 项目级菜单 -->
    <nav v-if="selectedProject" class="sidebar-section">
      <div class="sidebar-section-title">
        <span>{{ t('sidebar.currentProject') }}</span>
        <button
          type="button"
          class="project-clear-btn"
          @click="$emit('clear-project')"
          :aria-label="t('sidebar.backToProjectList')"
          :title="t('sidebar.backToProjectList')"
        >
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true">
            <path d="M4 8h8M7 5l-3 3 3 3"/>
          </svg>
        </button>
      </div>
      <div class="current-project-name" :title="currentProjectName">{{ currentProjectName }}</div>

      <ul class="sidebar-menu">
        <li>
          <button
            type="button"
            class="sidebar-item"
            :class="{ active: activeMenu === 'overview' }"
            @click="$emit('select-menu', 'overview')"
            :aria-label="t('sidebar.opportunityOverview')"
          >
            <span class="sidebar-icon" aria-hidden="true">
              <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6">
                <rect x="3" y="3" width="7" height="7" rx="1.5"/>
                <rect x="12" y="3" width="5" height="5" rx="1.5"/>
                <rect x="3" y="12" width="5" height="5" rx="1.5"/>
                <rect x="12" y="12" width="5" height="5" rx="1.5"/>
              </svg>
            </span>
            <span class="sidebar-label">{{ t('sidebar.opportunityOverview') }}</span>
          </button>
        </li>
        <li>
          <button
            type="button"
            class="sidebar-item"
            :class="{ active: activeMenu === 'timeline' }"
            @click="$emit('select-menu', 'timeline')"
            :aria-label="t('sidebar.opportunityJourney')"
          >
            <span class="sidebar-icon" aria-hidden="true">
              <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6">
                <circle cx="4" cy="5" r="2"/>
                <circle cx="4" cy="15" r="2"/>
                <path d="M4 7v6"/>
                <path d="M9 5h8"/>
                <path d="M9 15h8"/>
                <path d="M12 5v10"/>
              </svg>
            </span>
            <span class="sidebar-label">{{ t('sidebar.opportunityJourney') }}</span>
          </button>
        </li>
        <li>
          <button
            type="button"
            class="sidebar-item"
            :class="{ active: activeMenu === 'graph' }"
            @click="$emit('select-menu', 'graph')"
            :aria-label="t('sidebar.opportunityGraph')"
          >
            <span class="sidebar-icon" aria-hidden="true">
              <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6">
                <circle cx="6" cy="6" r="2.5"/>
                <circle cx="14" cy="6" r="2.5"/>
                <circle cx="6" cy="14" r="2.5"/>
                <circle cx="14" cy="14" r="2.5"/>
                <path d="M8 6h3.5M6 8.5v3M14 8.5v3M8 14h3.5"/>
              </svg>
            </span>
            <span class="sidebar-label">{{ t('sidebar.opportunityGraph') }}</span>
          </button>
        </li>
        <li>
          <button
            type="button"
            class="sidebar-item"
            :class="{ active: activeMenu === 'stakeholders' }"
            @click="$emit('select-menu', 'stakeholders')"
            :aria-label="t('sidebar.opportunityStakeholders')"
          >
            <span class="sidebar-icon" aria-hidden="true">
              <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6">
                <circle cx="10" cy="6" r="3"/>
                <path d="M3 17a7 7 0 0114 0"/>
              </svg>
            </span>
            <span class="sidebar-label">{{ t('sidebar.opportunityStakeholders') }}</span>
            <span v-if="stakeholderCount" class="sidebar-count">{{ stakeholderCount }}</span>
          </button>
        </li>

        <!-- 销售工作台子菜单 -->
        <li class="sidebar-group">
          <button
            type="button"
            class="sidebar-item sidebar-group-toggle"
            :class="{ active: isWorkspaceActive, expanded: workspaceExpanded }"
            @click="toggleWorkspace"
            :aria-expanded="workspaceExpanded"
            :aria-label="t('sidebar.salesWorkspace')"
          >
            <span class="sidebar-icon" aria-hidden="true">
              <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6">
                <path d="M3 6h14"/>
                <path d="M3 10h10"/>
                <path d="M3 14h6"/>
              </svg>
            </span>
            <span class="sidebar-label">{{ t('sidebar.salesWorkspace') }}</span>
            <span class="sidebar-chevron" :class="{ expanded: workspaceExpanded }" aria-hidden="true">
              <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6">
                <path d="M5 3l6 5-6 5"/>
              </svg>
            </span>
          </button>
          <Transition name="submenu">
            <ul v-show="workspaceExpanded" class="sidebar-submenu">
              <li>
                <button
                  type="button"
                  class="sidebar-subitem"
                  :class="{ active: activeMenu === 'blindspot' }"
                  @click="$emit('select-menu', 'blindspot')"
                >{{ t('sidebar.blindSpotScan') }}</button>
              </li>
              <li>
                <button
                  type="button"
                  class="sidebar-subitem"
                  :class="{ active: activeMenu === 'actions' }"
                  @click="$emit('select-menu', 'actions')"
                >{{ t('sidebar.actionSuggestions') }}</button>
              </li>
              <li>
                <button
                  type="button"
                  class="sidebar-subitem"
                  :class="{ active: activeMenu === 'tasks' }"
                  @click="$emit('select-menu', 'tasks')"
                >{{ t('sidebar.todoItems') }}</button>
              </li>
              <li>
                <button
                  type="button"
                  class="sidebar-subitem"
                  :class="{ active: activeMenu === 'meeting' }"
                  @click="$emit('select-menu', 'meeting')"
                >{{ t('sidebar.visitPlan') }}</button>
              </li>
              <li>
                <button
                  type="button"
                  class="sidebar-subitem"
                  :class="{ active: activeMenu === 'visit' }"
                  @click="$emit('select-menu', 'visit')"
                >{{ t('sidebar.visitRecords') }}</button>
              </li>
            </ul>
          </Transition>
        </li>

        <li>
          <button
            type="button"
            class="sidebar-item"
            :class="{ active: activeMenu === 'feedback' }"
            @click="$emit('select-menu', 'feedback')"
            :aria-label="t('sidebar.simulationRoom')"
          >
            <span class="sidebar-icon" aria-hidden="true">
              <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6">
                <path d="M3 10a7 7 0 1114 0"/>
                <path d="M10 10V5"/>
                <path d="M10 10l3.5 2"/>
              </svg>
            </span>
            <span class="sidebar-label">{{ t('sidebar.simulationRoom') }}</span>
          </button>
        </li>
      </ul>
    </nav>

    <!-- 底部信息 -->
    <div class="sidebar-footer">
      <!-- 语言切换 -->
      <div class="lang-switcher">
        <button
          v-for="loc in availableLocales"
          :key="loc.key"
          type="button"
          class="lang-btn"
          :class="{ active: currentLocale === loc.key }"
          @click="switchLocale(loc.key)"
          :aria-label="loc.label"
          :title="loc.label"
        >{{ loc.key === 'zh' ? '中' : loc.key.toUpperCase() }}</button>
      </div>
      <!-- 设置 + 版本号同行 -->
      <div class="sidebar-footer-row">
        <button
          type="button"
          class="sidebar-item sidebar-footer-settings"
          :class="{ active: activeMenu === 'settings' }"
          @click="$emit('select-menu', 'settings')"
          :aria-label="t('sidebar.settings')"
        >
          <span class="sidebar-icon" aria-hidden="true">
            <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6">
              <circle cx="10" cy="10" r="3"/>
              <path d="M10 1.5v2M10 16.5v2M1.5 10h2M16.5 10h2M3.9 3.9l1.4 1.4M14.7 14.7l1.4 1.4M3.9 16.1l1.4-1.4M14.7 5.3l1.4-1.4"/>
            </svg>
          </span>
          <span class="sidebar-label">{{ t('sidebar.settings') }}</span>
        </button>
        <div class="build-info">{{ t('sidebar.version') }}</div>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { availableLocales } from '../i18n'

const { t, locale } = useI18n()
const currentLocale = computed(() => locale.value)

function switchLocale(key) {
  locale.value = key
  localStorage.setItem('locale', key)
  document.title = t('meta.title')
}

const props = defineProps({
  projects: { type: Array, default: () => [] },
  selectedProject: { type: Object, default: null },
  activeMenu: { type: String, default: 'projects' },
  stakeholderCount: { type: Number, default: 0 }
})

defineEmits(['select-menu', 'clear-project', 'go-home'])

const workspaceMenus = ['blindspot', 'actions', 'tasks', 'meeting', 'visit']
const isWorkspaceActive = computed(() => workspaceMenus.includes(props.activeMenu))
const workspaceExpanded = ref(isWorkspaceActive.value)

watch(() => props.activeMenu, (val) => {
  if (workspaceMenus.includes(val)) {
    workspaceExpanded.value = true
  }
}, { immediate: true })

function toggleWorkspace() {
  workspaceExpanded.value = !workspaceExpanded.value
}

const currentProjectName = computed(() => {
  return props.selectedProject?.name || t('sidebar.noProjectSelected')
})
</script>

<style scoped>
.sales-twin-sidebar {
  width: 220px;
  min-width: 220px;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--sidebar-bg, #EBE7DC);
  border-right: 1px solid var(--sidebar-border, #D7D4CD);
  color: var(--text-primary, #15171D);
  font-family: var(--font-sans, 'Noto Sans SC', 'PingFang SC', 'Microsoft YaHei', system-ui, sans-serif);
  font-size: var(--fs-sm, 12px);
  line-height: 1.45;
  overflow-y: auto;
  -webkit-font-smoothing: antialiased;
}

/* 品牌区 */
.sidebar-brand {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 20px 16px 18px;
  cursor: pointer;
  user-select: none;
  text-align: left;
  border: none;
  background: transparent;
  color: inherit;
  transition: background 0.15s;
}

.sidebar-brand:hover {
  background: rgba(255, 255, 255, 0.35);
}

.sidebar-brand:focus-visible {
  outline: 2px solid var(--focus-ring, #15171D);
  outline-offset: -2px;
}

.brand-logo {
  width: 28px;
  height: 28px;
  color: var(--accent, #CD5036);
  flex-shrink: 0;
}

.brand-logo svg {
  width: 100%;
  height: 100%;
}

.brand-text {
  display: flex;
  flex-direction: column;
  gap: 1px;
  overflow: hidden;
}

.brand-title {
  font-size: var(--fs-md, 14px);
  font-weight: 700;
  letter-spacing: -0.01em;
  color: var(--text-primary, #15171D);
}

.brand-subtitle {
  font-size: var(--fs-xs, 11px);
  color: var(--text-tertiary, #807E7E);
  font-weight: 500;
}

/* 菜单分区 */
.sidebar-section {
  padding: 8px 12px;
}

.sidebar-section + .sidebar-section {
  border-top: 1px solid var(--sidebar-border, #D7D4CD);
}

.sidebar-section-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 8px 6px;
  font-size: var(--fs-xs, 11px);
  font-weight: 600;
  color: var(--text-tertiary, #807E7E);
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.project-clear-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  padding: 0;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: var(--text-tertiary, #807E7E);
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}

.project-clear-btn:hover {
  background: rgba(21, 23, 29, 0.06);
  color: var(--text-primary, #15171D);
}

.project-clear-btn:focus-visible {
  outline: 2px solid var(--focus-ring, #15171D);
  outline-offset: 1px;
}

.project-clear-btn svg {
  width: 14px;
  height: 14px;
}

.current-project-name {
  padding: 0 8px 8px;
  font-size: var(--fs-sm, 12px);
  font-weight: 600;
  color: var(--text-secondary, #494A4D);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 菜单列表 */
.sidebar-menu,
.sidebar-submenu {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.sidebar-item,
.sidebar-subitem {
  position: relative;
  width: 100%;
  display: flex;
  align-items: center;
  gap: 8px;
  text-align: left;
  border: none;
  background: transparent;
  color: var(--text-secondary, #494A4D);
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}

.sidebar-item {
  padding: 8px 10px;
  border-radius: 8px;
  font-size: var(--fs-sm, 12px);
  font-weight: 500;
}

.sidebar-item:hover:not(.active) {
  background: rgba(255, 255, 255, 0.45);
  color: var(--text-primary, #15171D);
}

.sidebar-item.active {
  background: rgba(205, 80, 54, 0.08);
  color: var(--accent, #CD5036);
}

.sidebar-item.active .sidebar-icon {
  color: var(--accent, #CD5036);
}

.sidebar-item:focus-visible {
  outline: 2px solid var(--focus-ring, #15171D);
  outline-offset: 1px;
}

.sidebar-icon {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
  color: currentColor;
  opacity: 0.85;
}

.sidebar-icon svg {
  width: 100%;
  height: 100%;
}

.sidebar-label {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sidebar-count {
  flex-shrink: 0;
  font-size: var(--fs-xs, 11px);
  font-weight: 600;
  color: var(--text-tertiary, #807E7E);
  background: rgba(255, 255, 255, 0.55);
  padding: 1px 6px;
  border-radius: 10px;
  border: 1px solid var(--border, #E8E8E0);
}

.sidebar-item.active .sidebar-count {
  color: var(--accent, #CD5036);
  background: rgba(255, 255, 255, 0.75);
}

/* 可展开工作组 */
.sidebar-group-toggle {
  justify-content: flex-start;
}

.sidebar-chevron {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
  transition: transform 0.2s;
  color: var(--text-tertiary, #807E7E);
}

.sidebar-chevron.expanded {
  transform: rotate(90deg);
}

.sidebar-submenu {
  padding-left: 26px;
  overflow: hidden;
}

.sidebar-subitem {
  padding: 6px 10px 6px 12px;
  border-radius: 6px;
  font-size: var(--fs-xs, 11px);
  font-weight: 500;
  color: var(--text-tertiary, #807E7E);
}

.sidebar-subitem:hover:not(.active) {
  background: rgba(255, 255, 255, 0.4);
  color: var(--text-secondary, #494A4D);
}

.sidebar-subitem.active {
  background: rgba(205, 80, 54, 0.08);
  color: var(--accent, #CD5036);
}

.sidebar-subitem:focus-visible {
  outline: 2px solid var(--focus-ring, #15171D);
  outline-offset: 1px;
}

/* 子菜单展开动画 */
.submenu-enter-active,
.submenu-leave-active {
  transition: opacity 0.2s, transform 0.2s;
  transform-origin: top;
}

.submenu-enter-from,
.submenu-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

/* 底部 */
.sidebar-footer {
  margin-top: auto;
  padding: 8px 12px 10px;
  border-top: 1px solid var(--sidebar-border, #D7D4CD);
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 8px;
}

.sidebar-footer-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.sidebar-footer-settings {
  flex: 1;
  min-width: 0;
  padding: 6px 10px;
  border-radius: 6px;
  font-size: var(--fs-sm, 12px);
  font-weight: 500;
}

.build-info {
  flex-shrink: 0;
  font-size: var(--fs-xs, 11px);
  color: var(--text-muted, #93959D);
  letter-spacing: 0.03em;
}

/* 语言切换 */
.lang-switcher {
  align-self: center;
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 2px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.45);
  border: 1px solid var(--sidebar-border, #D7D4CD);
}

.lang-btn {
  appearance: none;
  border: none;
  background: transparent;
  color: var(--text-muted, #93959D);
  font-size: var(--fs-xs, 11px);
  font-weight: 600;
  line-height: 1;
  padding: 4px 8px;
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
  font-family: inherit;
}

.lang-btn:hover {
  color: var(--text-primary, #15171D);
  background: rgba(255, 255, 255, 0.6);
}

.lang-btn.active {
  background: var(--accent, #CD5036);
  color: #FFFFFF;
}

.lang-btn:focus-visible {
  outline: 2px solid var(--focus-ring, #15171D);
  outline-offset: 1px;
}

/* 减少动画 */
@media (prefers-reduced-motion: reduce) {
  .sidebar-item,
  .sidebar-subitem,
  .project-clear-btn,
  .sidebar-brand,
  .sidebar-chevron,
  .submenu-enter-active,
  .submenu-leave-active {
    transition: none;
  }
}
</style>

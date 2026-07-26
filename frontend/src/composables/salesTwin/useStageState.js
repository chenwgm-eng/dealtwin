import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import * as salesTwinApi from '../../api/salesTwin'
import { showToast } from './useConfirmToast'

// 阶段交付物追踪 + 商机历程时间线
export function useStageState(ctx) {
  const { t } = useI18n()
  const { selectedProject } = ctx

  // ============ 阶段交付物追踪 ============
  const stageDeliverables = ref(null)
  const stageDeliverablesLoading = ref(false)
  const stageCheckResult = ref(null)
  const showStageCheckModal = ref(false)

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

  async function toggleStageDeliverable(deliverableKey, isCompleted) {
    if (!selectedProject.value) return
    const stage = stageDeliverables.value?.stage
    if (!stage) return
    try {
      await salesTwinApi.updateStageDeliverable(selectedProject.value, deliverableKey, stage, {
        is_completed: isCompleted,
        notes: undefined
      })
      await loadStageDeliverables(selectedProject.value, stage)
    } catch (e) {
      console.error('更新交付物状态失败:', e)
      showToast(t('toast.updateDeliverableFailed', { reason: e?.message || e }), 'error')
    }
  }

  async function updateDeliverableNotes(deliverableKey, notes) {
    if (!selectedProject.value) return
    const stage = stageDeliverables.value?.stage
    if (!stage) return
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

  function closeStageCheckModal() {
    showStageCheckModal.value = false
  }

  // ============ 商机历程时间线 ============
  const stageTimeline = ref(null)
  const stageTimelineLoading = ref(false)

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

  return {
    // 阶段交付物
    stageDeliverables, stageDeliverablesLoading, stageCheckResult, showStageCheckModal,
    loadStageDeliverables, toggleStageDeliverable, updateDeliverableNotes, runStageCheck, closeStageCheckModal,
    // 商机历程
    stageTimeline, stageTimelineLoading, loadStageTimeline,
  }
}

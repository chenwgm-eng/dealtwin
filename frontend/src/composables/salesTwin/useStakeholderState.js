import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import * as salesTwinApi from '../../api/salesTwin'
import { showToast } from './useConfirmToast'

// 干系人状态管理：创建、删除、合并、关联联系人
// 接收 useSalesTwin 提供的共享响应式 state，保持引用一致
export function useStakeholderState(ctx) {
  const { t } = useI18n()
  const {
    selectedProject, selectedStakeholderId, stakeholders, stateLogs,
  } = ctx

  // ============ 关联联系人 ============
  const stakeholderLinkContacts = ref([])
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

  // ============ 添加干系人 ============
  const showStakeholderAddModal = ref(false)
  const stakeholderAddForm = ref({
    name: '', position: '', level: '', contact_id: null,
    buyer_role: '', project_role: '', status: 'confirmed', social_style: '',
    decision_power: 5, support_level: 5, urgency: 5,
    responsibilities: '', personal_agenda: '',
  })
  const savingStakeholder = ref(false)

  // 姓名 typeahead
  const showStakeholderNameSuggestions = ref(false)
  const stakeholderNameSuggestions = ref([])
  const stakeholderNameActiveIdx = ref(-1)
  const stakeholderNameInput = ref(null)

  function openStakeholderAddModal() {
    stakeholderAddForm.value = {
      name: '', position: '', level: '', contact_id: null,
      buyer_role: '', project_role: '', status: 'confirmed', social_style: '',
      decision_power: 5, support_level: 5, urgency: 5,
      responsibilities: '', personal_agenda: '',
    }
    showStakeholderAddModal.value = true
    showStakeholderNameSuggestions.value = false
    stakeholderNameSuggestions.value = []
    stakeholderNameActiveIdx.value = -1
    loadStakeholderLinkContacts()
  }

  function onStakeholderNameInput() {
    const q = (stakeholderAddForm.value.name || '').trim().toLowerCase()
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
    setTimeout(() => { showStakeholderNameSuggestions.value = false }, 150)
  }

  function onStakeholderNameEnter() {
    if (showStakeholderNameSuggestions.value && stakeholderNameActiveIdx.value >= 0) {
      const ct = stakeholderNameSuggestions.value[stakeholderNameActiveIdx.value]
      if (ct) { selectStakeholderNameSuggestion(ct); return }
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
      loadStakeholderLinkContacts()
    } catch (e) {
      console.error('创建干系人失败:', e)
      showToast(t('toast.createFailed', { reason: e?.message || e }), 'error')
    } finally {
      savingStakeholder.value = false
    }
  }

  // ============ 删除干系人 ============
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
      stakeholders.value.forEach(s => {
        if (s.reports_to_id === id) s.reports_to_id = null
      })
      if (selectedStakeholderId.value === id) selectedStakeholderId.value = null
      showStakeholderDeleteConfirm.value = false
      stakeholderToDelete.value = null
      loadStakeholderLinkContacts()
    } catch (e) {
      console.error('删除干系人失败:', e)
      showToast(t('toast.deleteFailed', { reason: e?.message || e }), 'error')
    } finally {
      deletingStakeholder.value = false
    }
  }

  // ============ 编辑/合并 ============
  function openEditStakeholderModal(stakeholder) {
    if (!stakeholder) return
    selectedStakeholderId.value = stakeholder.id
  }

  const mergeMode = ref(false)
  const mergePrimary = ref(null)

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
      const res = await salesTwinApi.getStakeholders(selectedProject.value)
      stakeholders.value = res.stakeholders || []
      const deletedId = secondary.id
      stakeholders.value.forEach(s => {
        if (s.reports_to_id === deletedId) s.reports_to_id = null
      })
      try {
        const logsRes = await salesTwinApi.getStateLogs(selectedProject.value)
        stateLogs.value = logsRes.logs || []
      } catch (e) { /* 日志加载失败不影响主流程 */ }
      mergeMode.value = false
      mergePrimary.value = null
      loadStakeholderLinkContacts()
    } catch (e) {
      console.error('合并干系人失败:', e)
      showToast(t('toast.mergeFailed', { reason: e?.message || e }), 'error')
    }
  }

  // openAddStakeholderModal 作为 openStakeholderAddModal 的别名
  const openAddStakeholderModal = openStakeholderAddModal

  return {
    // 关联联系人
    stakeholderLinkContacts, stakeholderLinkLoading, loadStakeholderLinkContacts,
    // 添加干系人
    showStakeholderAddModal, stakeholderAddForm, savingStakeholder,
    showStakeholderNameSuggestions, stakeholderNameSuggestions, stakeholderNameActiveIdx, stakeholderNameInput,
    onStakeholderNameInput, onStakeholderNameBlur, onStakeholderNameEnter,
    selectStakeholderNameSuggestion, selectStakeholderNameAsThirdParty,
    openStakeholderAddModal, openAddStakeholderModal, saveNewStakeholder,
    // 删除干系人
    showStakeholderDeleteConfirm, stakeholderToDelete, deletingStakeholder,
    confirmDeleteStakeholder, performDeleteStakeholder,
    // 编辑/合并
    openEditStakeholderModal, mergeMode, mergePrimary, startMerge, cancelMerge, executeMerge,
  }
}

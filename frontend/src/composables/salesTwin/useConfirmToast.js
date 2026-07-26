import { reactive } from 'vue'
import i18n from '../../i18n'

// 全局确认弹窗与 Toast 通知状态（单例，跨组件共享）
const state = reactive({
  // 确认弹窗
  confirm: {
    show: false,
    title: '',
    message: '',
    confirmText: '',
    cancelText: '',
    danger: false, // 是否为危险操作（红色按钮）
    loading: false,
    _resolve: null,
  },
  // Toast 通知
  toast: {
    show: false,
    msg: '',
    type: 'success', // success | error | warning | info
    _timer: null,
  },
})

/**
 * 请求确认（替代原生 confirm()）
 * @param {Object} options
 * @param {string} options.title - 标题
 * @param {string} options.message - 提示内容
 * @param {string} [options.confirmText] - 确认按钮文案
 * @param {string} [options.cancelText] - 取消按钮文案
 * @param {boolean} [options.danger] - 是否危险操作
 * @returns {Promise<boolean>} 用户点击确认返回 true，取消返回 false
 */
export function requestConfirm(options = {}) {
  return new Promise((resolve) => {
    state.confirm.show = true
    state.confirm.title = options.title || i18n.global.t('modal.confirmTitle')
    state.confirm.message = options.message || ''
    state.confirm.confirmText = options.confirmText || i18n.global.t('modal.confirmButton')
    state.confirm.cancelText = options.cancelText || i18n.global.t('modal.cancelButton')
    state.confirm.danger = !!options.danger
    state.confirm.loading = false
    state.confirm._resolve = resolve
  })
}

/** 用户点击确认 */
export function resolveConfirm() {
  const resolve = state.confirm._resolve
  state.confirm.show = false
  state.confirm._resolve = null
  if (resolve) resolve(true)
}

/** 用户点击取消 */
export function cancelConfirm() {
  const resolve = state.confirm._resolve
  state.confirm.show = false
  state.confirm._resolve = null
  if (resolve) resolve(false)
}

/** 设置确认弹窗 loading 状态（用于异步操作中） */
export function setConfirmLoading(loading) {
  state.confirm.loading = !!loading
}

/**
 * 显示 Toast 通知（替代原生 alert()）
 * @param {string} msg - 消息内容
 * @param {string} [type] - 类型：success | error | warning | info
 * @param {number} [duration] - 显示时长（毫秒），默认 3000
 */
export function showToast(msg, type = 'success', duration = 3000) {
  // 清除已有定时器
  if (state.toast._timer) {
    clearTimeout(state.toast._timer)
    state.toast._timer = null
  }
  state.toast.msg = msg
  state.toast.type = type
  state.toast.show = true
  state.toast._timer = setTimeout(() => {
    state.toast.show = false
    state.toast._timer = null
  }, duration)
}

export function useConfirmToast() {
  return {
    confirmState: state.confirm,
    toastState: state.toast,
    requestConfirm,
    resolveConfirm,
    cancelConfirm,
    setConfirmLoading,
    showToast,
  }
}

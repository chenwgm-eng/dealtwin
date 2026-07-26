<template>
  <Transition name="toast-fade">
    <div v-if="state.show" class="st-toast" :class="`st-toast-${state.type}`" role="alert">
      <span class="st-toast-icon" aria-hidden="true">{{ iconMap[state.type] || 'ℹ' }}</span>
      <span class="st-toast-msg">{{ state.msg }}</span>
    </div>
  </Transition>
</template>

<script setup>
import { useConfirmToast } from '../../composables/salesTwin/useConfirmToast'

const { toastState: state } = useConfirmToast()

const iconMap = {
  success: '✓',
  error: '✕',
  warning: '⚠',
  info: 'ℹ',
}
</script>

<style scoped>
.st-toast {
  position: fixed;
  top: 24px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 10000;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 18px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
  max-width: 80vw;
  pointer-events: auto;
}

.st-toast-icon {
  font-size: 14px;
  font-weight: 700;
  flex-shrink: 0;
}

.st-toast-msg {
  line-height: 1.4;
  word-break: break-word;
}

.st-toast-success {
  background: #fff;
  color: #15171D;
  border: 1px solid #E8E8E0;
  border-left: 3px solid #059669;
}

.st-toast-success .st-toast-icon {
  color: #059669;
}

.st-toast-error {
  background: #fff;
  color: #15171D;
  border: 1px solid #E8E8E0;
  border-left: 3px solid #C4391C;
}

.st-toast-error .st-toast-icon {
  color: #C4391C;
}

.st-toast-warning {
  background: #fff;
  color: #15171D;
  border: 1px solid #E8E8E0;
  border-left: 3px solid #B45309;
}

.st-toast-warning .st-toast-icon {
  color: #B45309;
}

.st-toast-info {
  background: #fff;
  color: #15171D;
  border: 1px solid #E8E8E0;
  border-left: 3px solid #6B7280;
}

.st-toast-info .st-toast-icon {
  color: #6B7280;
}

.toast-fade-enter-active,
.toast-fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.toast-fade-enter-from,
.toast-fade-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(-10px);
}
</style>

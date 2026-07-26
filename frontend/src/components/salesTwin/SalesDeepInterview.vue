<template>
  <div class="deep-interview-overlay">
    <!-- 顶部导航栏 -->
    <header class="di-header">
      <div class="di-header-left">
        <button type="button" class="di-back-btn" @click="$emit('close')" :aria-label="t('common.back')">
          <span aria-hidden="true">←</span>
          <span>{{ t('simulation.backToSimulation') }}</span>
        </button>
      </div>
      <div class="di-header-center">
        <span class="di-title">{{ t('simulation.deepInterview') }}</span>
      </div>
      <div class="di-header-right">
        <button type="button" class="di-suggestion-btn" @click="$emit('open-suggestions')" :aria-label="t('simulation.openSuggestionPool')">
          <svg viewBox="0 0 16 16" width="13" height="13" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
            <rect x="2" y="3" width="12" height="11" rx="1"/>
            <line x1="2" y1="6" x2="14" y2="6"/>
            <line x1="5" y1="1" x2="5" y2="4"/>
            <line x1="11" y1="1" x2="11" y2="4"/>
          </svg>
          <span>{{ t('simulation.suggestionPool') }}</span>
        </button>
        <span class="di-step-indicator">Step 5/5</span>
      </div>
    </header>

    <main class="di-main">
      <!-- 左面板：干系人列表 -->
      <aside class="di-left-panel">
        <div class="di-left-header">
          <span class="di-left-title">{{ t('simulation.stakeholderList') }}</span>
          <span class="di-left-count">{{ t('simulation.peopleCount', { count: stakeholders.length }) }}</span>
        </div>
        <div class="di-agent-list">
          <button
            v-for="s in stakeholders"
            :key="s.id"
            type="button"
            class="di-agent-item"
            :class="{ active: selectedStakeholderId === s.id }"
            @click="selectStakeholder(s)"
          >
            <div class="di-agent-avatar">{{ s.name[0] }}</div>
            <div class="di-agent-info">
              <span class="di-agent-name">{{ s.name }}</span>
              <span class="di-agent-role">{{ s.position || t('simulation.unknownPosition') }}</span>
            </div>
            <span v-if="chatHistories[s.id]?.length" class="di-agent-badge">{{ chatHistories[s.id].length }}</span>
          </button>
        </div>
      </aside>

      <!-- 右面板：聊天区 -->
      <section class="di-right-panel">
        <!-- 聊天对象信息栏 -->
        <div v-if="selectedStakeholder" class="di-chat-header">
          <div class="di-chat-target">
            <div class="di-chat-avatar">{{ selectedStakeholder.name[0] }}</div>
            <div class="di-chat-target-info">
              <span class="di-chat-name">{{ selectedStakeholder.name }}</span>
              <span class="di-chat-meta">
                {{ selectedStakeholder.position || t('simulation.unknown') }} ·
                {{ buyerRoleLabels[selectedStakeholder.buyer_role] || t('simulation.uncategorized') }} ·
                {{ t('simulation.supportLevel', { value: selectedStakeholder.support_level }) }}
              </span>
            </div>
          </div>
        </div>

        <!-- 消息列表 -->
        <div v-if="selectedStakeholder" class="di-chat-messages" ref="chatMessagesRef" @mouseup="handleMessagesMouseUp">
          <div v-if="!currentMessages.length" class="di-chat-empty">
            <div class="di-empty-icon" aria-hidden="true">💬</div>
            <p class="di-empty-text">{{ t('simulation.askPrompt', { name: selectedStakeholder.name }) }}</p>
            <div class="di-suggest-list">
              <button
                v-for="(q, i) in presetQuestions"
                :key="i"
                type="button"
                class="di-suggest-btn"
                @click="sendMessage(q)"
              >{{ q }}</button>
            </div>
          </div>
          <template v-else>
            <div
              v-for="(msg, idx) in currentMessages"
              :key="idx"
              class="di-message"
              :class="msg.role"
            >
              <div class="di-msg-avatar" aria-hidden="true">
                <span v-if="msg.role === 'user'">U</span>
                <span v-else>{{ selectedStakeholder.name[0] }}</span>
              </div>
              <div class="di-msg-content">
                <div class="di-msg-header">
                  <span class="di-msg-sender">{{ msg.role === 'user' ? t('simulation.you') : selectedStakeholder.name }}</span>
                  <span class="di-msg-time">{{ formatMsgTime(msg.timestamp) }}</span>
                </div>
                <div class="di-msg-text">{{ msg.content }}</div>
              </div>
            </div>
          </template>

          <!-- 打字指示器 -->
          <div v-if="isSending" class="di-message assistant">
            <div class="di-msg-avatar">{{ selectedStakeholder?.name[0] || '?' }}</div>
            <div class="di-msg-content">
              <div class="di-typing" :aria-label="t('simulation.typing')">
                <span></span><span></span><span></span>
              </div>
            </div>
          </div>
        </div>

        <!-- 未选择干系人 -->
        <div v-else class="di-no-target">
          <div class="di-no-target-icon" aria-hidden="true">←</div>
          <p>{{ t('simulation.selectStakeholderHint') }}</p>
        </div>

        <!-- 输入区 -->
        <div v-if="selectedStakeholder" class="di-input-area">
          <textarea
            v-model="chatInput"
            class="di-chat-input"
            :aria-label="t('simulation.interviewInput')"
            :placeholder="t('simulation.inputPlaceholder')"
            rows="1"
            ref="chatInputRef"
            :disabled="isSending"
            @keydown.enter.exact.prevent="sendMessage()"
          ></textarea>
          <button
            type="button"
            class="di-send-btn"
            :disabled="!chatInput.trim() || isSending"
            @click="sendMessage()"
            :aria-label="t('simulation.sendQuestion')"
          >
            <span v-if="isSending" class="di-send-spinner" aria-hidden="true"></span>
            <span v-else aria-hidden="true">→</span>
          </button>
        </div>
      </section>
    </main>

    <!-- 选中文字浮动采纳按钮 -->
    <Transition name="di-popover">
      <button
        v-if="showAdoptPopover"
        type="button"
        class="di-adopt-popover"
        :style="{ top: popoverY + 'px', left: popoverX + 'px' }"
        @click="adoptSelection"
        @mousedown.prevent
        :aria-label="t('simulation.adoptSuggestionAria')"
      >
        <span aria-hidden="true">💡</span>
        <span>{{ t('simulation.adoptSuggestion') }}</span>
      </button>
    </Transition>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, watch, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import * as salesTwinApi from '../../api/salesTwin'

const { t } = useI18n()

const props = defineProps({
  projectId: { type: [Number, String], required: true },
  stakeholders: { type: Array, default: () => [] },
  fermentationResult: { type: Object, default: null }
})

defineEmits(['close', 'open-suggestions'])

const selectedStakeholderId = ref(null)
const selectedStakeholder = computed(() =>
  props.stakeholders.find(s => s.id === selectedStakeholderId.value)
)

const chatHistories = ref({})
const chatInput = ref('')
const isSending = ref(false)
const chatMessagesRef = ref(null)
const chatInputRef = ref(null)

// 选中文字采纳建议
const showAdoptPopover = ref(false)
const popoverX = ref(0)
const popoverY = ref(0)
const selectedText = ref('')

function handleMessagesMouseUp(e) {
  const selection = window.getSelection()
  const text = selection.toString().trim()
  if (text && text.length > 5 && e.target.closest('.di-msg-text')) {
    selectedText.value = text
    popoverX.value = e.clientX
    popoverY.value = e.clientY - 45
    showAdoptPopover.value = true
  } else {
    showAdoptPopover.value = false
  }
}

function handleDocumentMouseDown(e) {
  if (!e.target.closest('.di-adopt-popover')) {
    showAdoptPopover.value = false
  }
}

async function adoptSelection() {
  if (!selectedText.value || !props.projectId) return
  const text = selectedText.value
  showAdoptPopover.value = false
  window.getSelection()?.removeAllRanges()
  try {
    await salesTwinApi.addSuggestion(props.projectId, {
      content: text,
      source: 'interview',
      source_context: selectedStakeholder.value ? {
        stakeholder_name: selectedStakeholder.value.name
      } : null
    })
    // 简短提示
    const popover = document.createElement('div')
    popover.textContent = t('simulation.adoptedToPool')
    popover.style.cssText = 'position:fixed;top:20px;left:50%;transform:translateX(-50%);background:#4CAF50;color:#fff;padding:8px 20px;border-radius:6px;font-size:13px;z-index:3000;box-shadow:0 4px 12px rgba(0,0,0,0.15)'
    document.body.appendChild(popover)
    setTimeout(() => popover.remove(), 2000)
  } catch (e) {
    console.error('采纳建议失败:', e)
  }
}

onMounted(() => {
  document.addEventListener('mousedown', handleDocumentMouseDown)
})

onUnmounted(() => {
  document.removeEventListener('mousedown', handleDocumentMouseDown)
})

const presetQuestions = computed(() => [
  t('simulation.presetQuestions.q1'),
  t('simulation.presetQuestions.q2'),
  t('simulation.presetQuestions.q3'),
  t('simulation.presetQuestions.q4'),
])

const buyerRoleLabels = computed(() => ({
  mobilizer: t('stakeholder.buyerRoleOptions.mobilizer'),
  blocker: t('stakeholder.buyerRoleOptions.blocker'),
  guide: t('stakeholder.buyerRoleOptions.guide'),
  champion: t('stakeholder.buyerRoleOptions.champion'),
  skeptic: t('stakeholder.buyerRoleOptions.skeptic'),
  coach: t('stakeholder.buyerRoleOptions.coach'),
}))

const currentMessages = computed(() => {
  if (!selectedStakeholderId.value) return []
  return chatHistories.value[selectedStakeholderId.value] || []
})

function selectStakeholder(s) {
  selectedStakeholderId.value = s.id
  nextTick(() => {
    chatInputRef.value?.focus()
    scrollToBottom()
  })
}

function formatMsgTime(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

function scrollToBottom() {
  nextTick(() => {
    if (chatMessagesRef.value) {
      chatMessagesRef.value.scrollTop = chatMessagesRef.value.scrollHeight
    }
  })
}

async function sendMessage(presetQuestion) {
  const question = (presetQuestion || chatInput.value).trim()
  if (!question || !selectedStakeholderId.value || isSending.value) return

  const sid = selectedStakeholderId.value
  if (!chatHistories.value[sid]) {
    chatHistories.value[sid] = []
  }

  // 添加用户消息
  chatHistories.value[sid].push({
    role: 'user',
    content: question,
    timestamp: new Date().toISOString()
  })

  chatInput.value = ''
  isSending.value = true
  scrollToBottom()

  try {
    const simCtx = props.fermentationResult ? {
      narrative_history: props.fermentationResult.narrative_history
    } : null

    const res = await salesTwinApi.interviewStakeholder(
      props.projectId,
      sid,
      question,
      simCtx
    )

    chatHistories.value[sid].push({
      role: 'assistant',
      content: res.answer || t('simulation.noAnswer'),
      timestamp: new Date().toISOString()
    })
  } catch (e) {
    chatHistories.value[sid].push({
      role: 'assistant',
      content: t('simulation.interviewFailed', { reason: e.message || t('simulation.unknownError') }),
      timestamp: new Date().toISOString()
    })
  } finally {
    isSending.value = false
    scrollToBottom()
  }
}

// 切换干系人时滚动到底部
watch(currentMessages, () => scrollToBottom(), { deep: true })
</script>

<style scoped>
.deep-interview-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  background: #fff;
  display: flex;
  flex-direction: column;
  font-family: 'Space Grotesk', 'Noto Sans SC', system-ui, sans-serif;
}

/* 顶部导航 */
.di-header {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  border-bottom: 1px solid #EAEAEA;
  flex-shrink: 0;
}

.di-back-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: transparent;
  border: 1px solid #EAEAEA;
  border-radius: 4px;
  font-size: 0.82rem;
  color: #333;
  cursor: pointer;
  transition: border-color 0.2s, color 0.2s;
}

.di-back-btn:hover {
  border-color: #000;
  color: #000;
}

.di-back-btn:focus-visible {
  outline: 2px solid #000;
  outline-offset: 1px;
}

.di-title {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.9rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  color: #000;
}

.di-step-indicator {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.78rem;
  color: #999;
}

/* 主体布局 */
.di-main {
  flex: 1;
  display: flex;
  min-height: 0;
}

/* 左面板：干系人列表 */
.di-left-panel {
  width: 280px;
  border-right: 1px solid #EAEAEA;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.di-left-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid #F0F0F0;
}

.di-left-title {
  font-size: 0.8rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #000;
}

.di-left-count {
  font-size: 0.72rem;
  color: #999;
  font-family: 'JetBrains Mono', monospace;
}

.di-agent-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.di-agent-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 10px 12px;
  border: none;
  border-radius: 8px;
  background: transparent;
  cursor: pointer;
  text-align: left;
  margin-bottom: 2px;
  transition: background-color 0.15s;
}

.di-agent-item:hover {
  background: #F5F5F5;
}

.di-agent-item.active {
  background: #F0F0F0;
}

.di-agent-item:focus-visible {
  outline: 2px solid #000;
  outline-offset: -2px;
}

.di-agent-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #1F2937;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.85rem;
  font-weight: 600;
  flex-shrink: 0;
}

.di-agent-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.di-agent-name {
  font-size: 0.82rem;
  font-weight: 600;
  color: #000;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.di-agent-role {
  font-size: 0.7rem;
  color: #999;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.di-agent-badge {
  font-size: 0.65rem;
  min-width: 18px;
  height: 18px;
  border-radius: 9px;
  background: #1F2937;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 5px;
  font-family: 'JetBrains Mono', monospace;
  flex-shrink: 0;
}

/* 右面板：聊天区 */
.di-right-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.di-chat-header {
  padding: 12px 24px;
  border-bottom: 1px solid #EAEAEA;
  flex-shrink: 0;
}

.di-chat-target {
  display: flex;
  align-items: center;
  gap: 10px;
}

.di-chat-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #F3F4F6;
  color: #374151;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.95rem;
  font-weight: 600;
  flex-shrink: 0;
}

.di-chat-target-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.di-chat-name {
  font-size: 0.9rem;
  font-weight: 600;
  color: #000;
}

.di-chat-meta {
  font-size: 0.72rem;
  color: #999;
}

/* 消息列表 */
.di-chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.di-chat-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  text-align: center;
}

.di-empty-icon {
  font-size: 3rem;
  opacity: 0.3;
}

.di-empty-text {
  font-size: 0.85rem;
  color: #999;
  margin: 0;
}

.di-suggest-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
  max-width: 500px;
}

.di-suggest-btn {
  padding: 6px 14px;
  font-size: 0.78rem;
  border: 1px solid #EAEAEA;
  border-radius: 16px;
  background: #fff;
  color: #666;
  cursor: pointer;
  transition: border-color 0.15s, color 0.15s;
}

.di-suggest-btn:hover {
  border-color: #000;
  color: #000;
}

.di-suggest-btn:focus-visible {
  outline: 2px solid #000;
  outline-offset: 1px;
}

/* 消息气泡 */
.di-message {
  display: flex;
  gap: 12px;
}

.di-message.user {
  flex-direction: row-reverse;
}

.di-msg-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.82rem;
  font-weight: 600;
  flex-shrink: 0;
}

.di-message.user .di-msg-avatar {
  background: #1F2937;
  color: #fff;
}

.di-message.assistant .di-msg-avatar {
  background: #F3F4F6;
  color: #374151;
}

.di-msg-content {
  max-width: 70%;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.di-message.user .di-msg-content {
  align-items: flex-end;
}

.di-msg-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.di-message.user .di-msg-header {
  flex-direction: row-reverse;
}

.di-msg-sender {
  font-size: 0.75rem;
  font-weight: 600;
  color: #666;
}

.di-msg-time {
  font-size: 0.65rem;
  color: #BBB;
  font-family: 'JetBrains Mono', monospace;
}

.di-msg-text {
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 0.85rem;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

.di-message.user .di-msg-text {
  background: #1F2937;
  color: #fff;
  border-bottom-right-radius: 4px;
}

.di-message.assistant .di-msg-text {
  background: #F3F4F6;
  color: #374151;
  border-bottom-left-radius: 4px;
}

/* 打字指示器 */
.di-typing {
  display: flex;
  gap: 4px;
  padding: 12px 14px;
  background: #F3F4F6;
  border-radius: 12px;
  border-bottom-left-radius: 4px;
}

.di-typing span {
  width: 8px;
  height: 8px;
  background: #9CA3AF;
  border-radius: 50%;
  animation: di-typing 1.4s infinite ease-in-out;
}

.di-typing span:nth-child(1) { animation-delay: 0s; }
.di-typing span:nth-child(2) { animation-delay: 0.2s; }
.di-typing span:nth-child(3) { animation-delay: 0.4s; }

@keyframes di-typing {
  0%, 60%, 100% { transform: translateY(0); }
  30% { transform: translateY(-8px); }
}

/* 未选择干系人 */
.di-no-target {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: #999;
}

.di-no-target-icon {
  font-size: 2rem;
}

.di-no-target p {
  font-size: 0.85rem;
  margin: 0;
}

/* 输入区 */
.di-input-area {
  padding: 16px 24px;
  border-top: 1px solid #EAEAEA;
  display: flex;
  gap: 12px;
  align-items: flex-end;
  flex-shrink: 0;
}

.di-chat-input {
  flex: 1;
  padding: 12px 16px;
  font-size: 0.85rem;
  border: 1px solid #EAEAEA;
  border-radius: 8px;
  resize: none;
  font-family: inherit;
  line-height: 1.5;
  max-height: 120px;
  transition: border-color 0.2s;
}

.di-chat-input:focus-visible {
  outline: 2px solid transparent;
  border-color: #1F2937;
}

.di-chat-input:focus-visible {
  outline: 2px solid transparent;
  border-color: #1F2937;
}

.di-send-btn {
  width: 44px;
  height: 44px;
  background: #1F2937;
  color: #fff;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 1.1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.2s;
  flex-shrink: 0;
}

.di-send-btn:hover:not(:disabled) {
  background: #374151;
}

.di-send-btn:disabled {
  background: #E5E7EB;
  color: #9CA3AF;
  cursor: not-allowed;
}

.di-send-btn:focus-visible {
  outline: 2px solid #000;
  outline-offset: 2px;
}

.di-send-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: di-spin 0.6s linear infinite;
}

@keyframes di-spin {
  to { transform: rotate(360deg); }
}

/* 响应式 */
@media (max-width: 768px) {
  .di-left-panel {
    width: 200px;
  }
  .di-msg-content {
    max-width: 85%;
  }
}

@media (prefers-reduced-motion: reduce) {
  .di-typing span,
  .di-send-spinner {
    animation: none;
  }
}

/* 建议池入口按钮——与系统 btn-primary 风格一致 */
.di-suggestion-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border: 1px solid #000;
  background: transparent;
  color: #000;
  border-radius: 2px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.05em;
  cursor: pointer;
  transition: background-color 0.2s, color 0.2s;
  touch-action: manipulation;
}

.di-suggestion-btn:hover {
  background: #000;
  color: #fff;
}

.di-suggestion-btn:focus-visible {
  outline: 2px solid #FF4500;
  outline-offset: 2px;
}

/* 选中文字浮动采纳按钮——黑底白字，hover变橙 */
.di-adopt-popover {
  position: fixed;
  z-index: 2100;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  background: #000;
  color: #fff;
  border: none;
  border-radius: 2px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.05em;
  cursor: pointer;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25);
  transition: background-color 0.2s;
  touch-action: manipulation;
}

.di-adopt-popover:hover {
  background: #FF4500;
}

.di-adopt-popover:focus-visible {
  outline: 2px solid #FF4500;
  outline-offset: 2px;
}

/* 浮动按钮过渡 */
.di-popover-enter-active,
.di-popover-leave-active {
  transition: opacity 0.15s, transform 0.15s;
}

.di-popover-enter-from,
.di-popover-leave-to {
  opacity: 0;
  transform: translateY(8px);
}

@media (prefers-reduced-motion: reduce) {
  .di-suggestion-btn,
  .di-adopt-popover,
  .di-popover-enter-active,
  .di-popover-leave-active {
    transition: none;
  }
}
</style>

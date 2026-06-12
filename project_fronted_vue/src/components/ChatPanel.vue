<template>
  <div class="chat-panel">
    <!-- ===== 左侧：对话历史侧栏 ===== -->
    <div class="history-sidebar" :class="{ collapsed: !showHistory }">
      <div class="history-header">
        <div class="history-title">
          <el-icon :size="16"><Clock /></el-icon>
          <span v-show="showHistory">历史记录</span>
        </div>
        <el-button text @click="showHistory = !showHistory" class="toggle-btn">
          <el-icon><Fold v-if="showHistory" /><Expand v-else /></el-icon>
        </el-button>
      </div>

      <!-- 新对话按钮 -->
      <div v-show="showHistory" class="new-conv-btn">
        <el-button type="primary" size="small" @click="startNewConversation" style="width:100%">
          <el-icon><Plus /></el-icon> 新对话
        </el-button>
      </div>

      <!-- 对话列表 -->
      <div v-show="showHistory" class="conv-list" v-loading="loadingHistory">
        <div
          v-for="conv in conversations"
          :key="conv.id"
          class="conv-item"
          :class="{ active: conv.id === currentConvId }"
          @click="switchConversation(conv)"
        >
          <div class="conv-item-title">{{ conv.title }}</div>
          <div class="conv-item-meta">
            {{ formatTime(conv.updated_at) }}
            <span class="dot">·</span>
            {{ conv.message_count }} 条
          </div>
        </div>

        <div v-if="conversations.length === 0 && !loadingHistory" class="conv-empty">
          暂无历史记录
        </div>
      </div>
    </div>

    <!-- ===== 右侧：主聊天区 ===== -->
    <div class="chat-main-area">
      <!-- Header -->
      <div class="chat-header">
        <div class="chat-header-left">
          <el-button text @click="showHistory = !showHistory" class="toggle-btn">
            <el-icon><Fold v-if="showHistory" /><Expand v-else /></el-icon>
          </el-button>
          <div class="chat-header-info">
            <h2 v-if="currentConvId" class="chat-header-title">{{ currentConvTitle }}</h2>
            <p v-else class="chat-header-placeholder">选择知识库开始提问</p>
          </div>
        </div>
        <div class="chat-header-actions">
          <el-button text size="small" @click="startNewConversation" :disabled="!selectedKb">
            <el-icon><Plus /></el-icon> 新对话
          </el-button>
          <el-tooltip content="清空当前对话消息（不会删除历史记录）" placement="top">
            <el-button text size="small" @click="resetChat">
              <el-icon><Delete /></el-icon>
            </el-button>
          </el-tooltip>
        </div>
      </div>

      <!-- 消息列表 -->
      <div class="chat-messages" ref="msgContainer">
        <div v-if="messages.length === 0" class="chat-empty">
          <div class="empty-icon">✦</div>
          <h3>DocMind 智能问答</h3>
          <p>正在与「{{ kbName }}」对话</p>
          <p class="empty-hint">输入问题开始智能问答，AI 将从文档中检索相关信息回答</p>
          <div class="suggestions">
            <el-tag
              v-for="(s, i) in suggestions"
              :key="i"
              round
              class="suggestion-tag"
              @click="inputText = s; sendMessage()"
            >
              {{ s }}
            </el-tag>
          </div>
        </div>

        <div
          v-for="(msg, idx) in messages"
          :key="msg.id"
          class="msg-wrapper"
          :class="{ 'is-user': msg.role === 'user', 'is-assistant': msg.role === 'assistant' }"
        >
          <div v-if="msg.role === 'user'" class="msg user-msg">
            <div class="msg-content">
              <div class="msg-bubble user-bubble">
                <p class="msg-text">{{ msg.content }}</p>
              </div>
            </div>
            <div class="msg-avatar user-avatar">U</div>
          </div>

          <div v-else class="msg assistant-msg">
            <div class="msg-avatar assistant-avatar">D</div>
            <div class="msg-content">
              <div class="msg-bubble assistant-bubble">
                <div class="msg-markdown" v-html="renderMarkdown(msg.displayContent)"></div>
                <span v-if="msg.streaming" class="stream-cursor">▊</span>
              </div>

              <div v-if="msg.references && msg.references.length > 0" class="msg-references">
                <div class="refs-toggle" @click="msg.showRefs = !msg.showRefs">
                  <el-icon :size="13"><Connection /></el-icon>
                  <span>{{ msg.references.length }} 个引用来源</span>
                  <el-icon :class="{ rotated: msg.showRefs }" :size="12"><ArrowDown /></el-icon>
                </div>
                <transition name="slide">
                  <div v-show="msg.showRefs" class="refs-list">
                    <SourceCard v-for="(ref, ri) in msg.references" :key="ri" :doc="ref" />
                  </div>
                </transition>
              </div>

              <div v-if="!msg.streaming && msg.content" class="msg-actions">
                <el-tooltip content="复制回答" placement="top">
                  <el-button text size="small" @click="copyContent(msg.content)">
                    <el-icon :size="14"><CopyDocument /></el-icon>
                  </el-button>
                </el-tooltip>
              </div>
            </div>
          </div>
        </div>

        <!-- 思考中动画 -->
        <div v-if="streaming && messages[messages.length - 1]?.role === 'assistant' && !messages[messages.length - 1]?.content" class="msg assistant-msg">
          <div class="msg-avatar assistant-avatar">D</div>
          <div class="msg-content">
            <div class="msg-bubble assistant-bubble thinking-bubble">
              <span class="thinking-dot"></span>
              <span class="thinking-dot"></span>
              <span class="thinking-dot"></span>
            </div>
          </div>
        </div>
      </div>

      <!-- 输入区 -->
      <div class="chat-input-area">
        <div class="input-wrapper">
          <el-input
            v-model="inputText"
            type="textarea"
            :rows="1"
            :disabled="!selectedKb || streaming"
            :placeholder="selectedKb ? '输入问题，Enter 发送，Shift+Enter 换行...' : '请先选择知识库'"
            class="chat-input-el"
            resize="none"
            @keydown="handleKeydown"
            autofocus
          />
          <el-button
            type="primary"
            :icon="streaming ? 'Loading' : 'Top'"
            :disabled="!inputText.trim() || !selectedKb || streaming"
            @click="sendMessage"
            class="send-btn-el"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted, watch } from 'vue'
import { useAppStore } from '@/stores/app'
import { ElMessage } from 'element-plus'
import {
  ArrowDown,
  Connection,
  CopyDocument,
  Fold,
  Expand,
  Plus,
  Clock,
  Delete,
} from '@element-plus/icons-vue'
import { marked } from 'marked'
import SourceCard from './SourceCard.vue'

const props = defineProps({
  kbId: { type: String, required: true },
  kbName: { type: String, default: '' },
})

const store = useAppStore()

// ============ 对话历史状态 ============
const showHistory = ref(true)
const conversations = ref([])
const loadingHistory = ref(false)
const currentConvId = ref(null)
const currentConvTitle = ref('')

// ============ 聊天状态 ============
const messages = ref([])
const inputText = ref('')
const streaming = ref(false)
const msgContainer = ref(null)

// 流式消息跟踪：当前正在流出的 assistant 消息在 messages 中的索引
// 以及对应的 conversation 消息索引，用于更新后端
const streamingMsgIndex = ref(-1)
const streamingConvMsgIndex = ref(-1)

const selectedKb = ref(true)

const suggestions = [
  '这个知识库包含哪些内容？',
  '总结所有文档的要点',
  '帮我查找相关规范',
]

// 配置 marked
marked.setOptions({
  breaks: true,
  gfm: true,
})

function renderMarkdown(text) {
  if (!text) return ''
  try {
    return marked.parse(text)
  } catch {
    return text
  }
}

function scrollToBottom() {
  nextTick(() => {
    if (msgContainer.value) {
      msgContainer.value.scrollTop = msgContainer.value.scrollHeight
    }
  })
}

function handleKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
}

function formatTime(t) {
  if (!t) return ''
  try {
    const d = new Date(t)
    const now = new Date()
    const isToday = d.toDateString() === now.toDateString()
    if (isToday) {
      return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    }
    return d.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
  } catch {
    return t
  }
}

// =============================================
// 对话历史管理
// =============================================

async function loadConversations() {
  if (!store.isConfigured || !props.kbId) return
  loadingHistory.value = true
  try {
    const data = await store.listConversations(props.kbId)
    conversations.value = data.items || []
  } catch (e) {
    console.error('加载对话历史失败:', e)
  } finally {
    loadingHistory.value = false
  }
}

async function startNewConversation() {
  if (!store.isConfigured || !props.kbId) return

  // 清空当前对话
  messages.value = []
  currentConvId.value = null
  currentConvTitle.value = ''
  inputText.value = ''

  try {
    const conv = await store.createConversation(props.kbId, props.kbName)
    currentConvId.value = conv.id
    currentConvTitle.value = '新对话'
    // 刷新历史列表
    await loadConversations()
    ElMessage.success('已创建新对话')
  } catch (e) {
    ElMessage.error('创建对话失败: ' + e.message)
  }
}

async function switchConversation(conv) {
  if (conv.id === currentConvId.value) return
  try {
    const fullConv = await store.getConversation(conv.id)
    currentConvId.value = fullConv.id
    currentConvTitle.value = fullConv.title || '新对话'

    // 将后端消息转为前端消息格式
    messages.value = (fullConv.messages || []).map((msg, i) => {
      if (msg.role === 'assistant') {
        return {
          id: `hist-${i}`,
          role: 'assistant',
          content: msg.content || '',
          displayContent: msg.content || '',
          references: msg.references || [],
          showRefs: false,
          streaming: false,
        }
      } else {
        return {
          id: `hist-${i}`,
          role: 'user',
          content: msg.content || '',
        }
      }
    })

    scrollToBottom()
  } catch (e) {
    ElMessage.error('加载对话失败: ' + e.message)
  }
}

// =============================================
// 发送消息 + 自动保存
// =============================================

async function sendMessage() {
  const text = inputText.value.trim()
  if (!text || !props.kbId || streaming.value) return

  inputText.value = ''
  streaming.value = true

  // ---- 如果没有当前对话，先创建一个 ----
  if (!currentConvId.value) {
    try {
      const conv = await store.createConversation(props.kbId, props.kbName)
      currentConvId.value = conv.id
      currentConvTitle.value = '新对话'
      // 刷新历史列表
      await loadConversations()
    } catch (e) {
      ElMessage.error('创建对话失败: ' + e.message)
      streaming.value = false
      return
    }
  }

  // ---- 添加用户消息（前端 + 后端） ----
  const userMsgId = Date.now().toString()
  messages.value.push({
    id: userMsgId,
    role: 'user',
    content: text,
  })

  // 保存到后端
  try {
    await store.appendMessage(currentConvId.value, 'user', text)
  } catch (e) {
    console.error('保存用户消息失败:', e)
  }

  // ---- 准备助手消息 ----
  const msgId = (Date.now() + 1).toString()
  const assistantMsgIndex = messages.value.length
  const assistantMsg = {
    id: msgId,
    role: 'assistant',
    content: '',
    displayContent: '',
    references: [],
    showRefs: false,
    streaming: true,
  }
  messages.value.push(assistantMsg)

  // 在后端创建空的 assistant 消息（占位），记下索引
  try {
    const updatedConv = await store.appendMessage(currentConvId.value, 'assistant', '')
    // 找到刚追加的 assistant 消息的索引
    const backendMsgs = updatedConv.messages || []
    let foundIndex = -1
    for (let i = backendMsgs.length - 1; i >= 0; i--) {
      if (backendMsgs[i].role === 'assistant' && backendMsgs[i].content === '') {
        foundIndex = i
        break
      }
    }
    streamingConvMsgIndex.value = foundIndex
  } catch (e) {
    console.error('创建助手消息占位失败:', e)
    streamingConvMsgIndex.value = -1
  }

  scrollToBottom()

  // ---- 发送 SSE 请求 ----
  try {
    const url = `${store.getBaseUrl() || ''}/api/v1/chat`
    // 创建 AbortController 用于超时控制（30秒无数据自动中断）
    const abortController = new AbortController()
    const timeoutTimer = setTimeout(() => {
      abortController.abort()
    }, 30000)  // 30秒超时

    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': store.apiKey,
      },
      body: JSON.stringify({
        knowledge_base_id: props.kbId,
        question: text,
        stream: true,
        top_k: 5,
      }),
      signal: abortController.signal,
    })

    clearTimeout(timeoutTimer)

    if (!res.ok) {
      let detail = `请求失败 (${res.status})`
      try {
        const body = await res.json()
        detail = body.detail || detail
      } catch {}
      throw new Error(detail)
    }

    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let accumulatedContent = ''
    let finalReferences = []

    while (true) {
      // 每次 reader.read() 设置 30 秒超时，防止流中间卡死
      let readResult;
      try {
        const readTimeout = setTimeout(() => abortController.abort(), 30000);
        readResult = await reader.read();
        clearTimeout(readTimeout);
      } catch (e) {
        // 读取超时或出错，设置错误信息后退出循环
        if (!accumulatedContent) {
          assistantMsg.content = '**请求超时：** 后端响应超过30秒，请检查模型配置或网络连接';
          assistantMsg.displayContent = assistantMsg.content;
        }
        break;
      }

      const { done, value } = readResult
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        const t = line.trim()
        if (!t || !t.startsWith('data: ')) continue

        const payload = t.slice(6)
        if (payload === '[DONE]') {
          // 流式结束：更新后端消息（最终内容 + 引用）
          if (streamingConvMsgIndex.value >= 0) {
            try {
              await store.updateMessage(
                currentConvId.value,
                streamingConvMsgIndex.value,
                accumulatedContent,
                finalReferences.length > 0 ? finalReferences : null,
              )
            } catch (e) {
              console.error('更新最终消息失败:', e)
            }
          }
          // 更新对话标题（如果后台还没自动更新）
          if (conversations.value.length > 0) {
            loadConversations()
          }
          assistantMsg.streaming = false
          streaming.value = false
          scrollToBottom()
          return
        }

        try {
          const d = JSON.parse(payload)
          if (d.type === 'references') {
            finalReferences = d.references || []
            assistantMsg.references = d.references || []
          } else if (d.type === 'text') {
            accumulatedContent += d.content
            assistantMsg.content = accumulatedContent
            assistantMsg.displayContent = accumulatedContent

            // 流式过程中实时更新后端（每收到一些内容就保存，防丢）
            if (streamingConvMsgIndex.value >= 0 && accumulatedContent.length % 500 < 50) {
              try {
                await store.updateMessage(
                  currentConvId.value,
                  streamingConvMsgIndex.value,
                  accumulatedContent,
                )
              } catch {}
            }

            scrollToBottom()
          }
        } catch {}
      }
    }
  } catch (e) {
    if (e.name === 'AbortError') {
      assistantMsg.content = '**请求超时：** 后端响应超过30秒，请检查模型配置或网络连接'
    } else {
      assistantMsg.content = '**出错了：** ' + e.message
    }
    assistantMsg.displayContent = assistantMsg.content
    // 出错时也尝试保存到后端
    if (streamingConvMsgIndex.value >= 0) {
      try {
        await store.updateMessage(
          currentConvId.value,
          streamingConvMsgIndex.value,
          assistantMsg.content,
        )
      } catch {}
    }
  }

  assistantMsg.streaming = false
  streaming.value = false
  scrollToBottom()
}

async function copyContent(text) {
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制到剪贴板')
  } catch {
    ElMessage.warning('复制失败')
  }
}

function resetChat() {
  messages.value = []
  // 不清除 currentConvId，保留当前对话的上下文
  inputText.value = ''
}

// =============================================
// 生命周期
// =============================================

// 当知识库切换时，重新加载对话历史
watch(() => props.kbId, () => {
  messages.value = []
  currentConvId.value = null
  currentConvTitle.value = ''
  if (props.kbId) {
    loadConversations()
  }
})

onMounted(() => {
  if (props.kbId) {
    loadConversations()
  }
})
</script>

<style scoped>
.chat-panel {
  display: flex;
  height: 100%;
  overflow: hidden;
}

/* ========== 历史侧栏 ========== */
.history-sidebar {
  width: 240px;
  min-width: 240px;
  border-right: 1px solid var(--docmind-border);
  display: flex;
  flex-direction: column;
  background: var(--docmind-bg-secondary);
  transition: width 0.2s, min-width 0.2s;
  overflow: hidden;
}

.history-sidebar.collapsed {
  width: 44px;
  min-width: 44px;
}

.history-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 12px 8px;
  flex-shrink: 0;
}

.history-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 600;
  color: var(--docmind-text);
  white-space: nowrap;
}

.toggle-btn {
  color: var(--docmind-text-muted) !important;
  flex-shrink: 0;
  padding: 4px !important;
}

.toggle-btn:hover {
  color: var(--docmind-text) !important;
}

.new-conv-btn {
  padding: 4px 12px 8px;
  flex-shrink: 0;
}

.conv-list {
  flex: 1;
  overflow-y: auto;
  padding: 0 8px;
}

.conv-item {
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s;
  margin-bottom: 2px;
}

.conv-item:hover {
  background: var(--docmind-bg-surface-hover, rgba(255,255,255,0.04));
}

.conv-item.active {
  background: var(--docmind-bg-surface);
  border: 1px solid rgba(217,119,6,0.15);
}

.conv-item-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--docmind-text);
  margin-bottom: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.conv-item-meta {
  font-size: 11px;
  color: var(--docmind-text-muted);
}

.conv-item-meta .dot {
  margin: 0 4px;
}

.conv-empty {
  text-align: center;
  padding: 32px 12px;
  font-size: 13px;
  color: var(--docmind-text-muted);
}

/* ========== 主聊天区 ========== */
.chat-main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
}

.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  border-bottom: 1px solid var(--docmind-border);
  background: var(--docmind-bg-secondary);
  flex-shrink: 0;
}

.chat-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.chat-header-info {
  display: flex;
  flex-direction: column;
}

.chat-header-title {
  font-family: 'Playfair Display', Georgia, serif;
  font-size: 16px;
  font-weight: 600;
  margin: 0;
  color: var(--docmind-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 300px;
}

.chat-header-placeholder {
  color: var(--docmind-text-muted);
  font-size: 14px;
  margin: 0;
}

.chat-header-actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}

/* ========== 消息列表 ========== */
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.chat-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 40px 20px;
}

.empty-icon {
  font-size: 48px;
  color: var(--docmind-primary-light);
  margin-bottom: 12px;
  opacity: 0.7;
}

.chat-empty h3 {
  font-family: 'Playfair Display', Georgia, serif;
  font-size: 22px;
  font-weight: 600;
  color: var(--docmind-text);
  margin: 0 0 6px;
}

.chat-empty p {
  font-size: 14px;
  color: var(--docmind-text-muted);
  margin: 0 0 4px;
}

.empty-hint {
  margin-bottom: 20px !important;
}

.suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
  max-width: 400px;
}

.suggestion-tag {
  cursor: pointer !important;
  padding: 4px 12px !important;
  background: var(--docmind-bg-surface) !important;
  border-color: var(--docmind-border) !important;
  color: var(--docmind-text-secondary) !important;
  transition: all 0.2s;
}

.suggestion-tag:hover {
  border-color: var(--docmind-primary) !important;
  color: var(--docmind-primary-light) !important;
}

/* 消息样式 */
.msg {
  display: flex;
  gap: 12px;
  animation: msgFadeIn 0.3s ease-out;
}

@keyframes msgFadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.user-msg {
  justify-content: flex-end;
}

.assistant-msg {
  justify-content: flex-start;
}

.msg-avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 700;
  flex-shrink: 0;
  margin-top: 4px;
}

.user-avatar {
  background: var(--docmind-bg-elevated);
  color: var(--docmind-text-secondary);
  order: 1;
}

.assistant-avatar {
  background: linear-gradient(135deg, var(--docmind-primary-dark), var(--docmind-primary-light));
  color: #0d0d14;
}

.msg-content {
  max-width: 75%;
  min-width: 0;
}

.user-bubble {
  background: linear-gradient(135deg, var(--docmind-primary), var(--docmind-primary-light));
  color: #0d0d14;
  border-bottom-right-radius: 4px;
}

.assistant-bubble {
  background: var(--docmind-bg-surface);
  border: 1px solid var(--docmind-border);
  border-bottom-left-radius: 4px;
}

.msg-bubble {
  padding: 12px 16px;
  border-radius: 14px;
  line-height: 1.7;
  font-size: 14px;
  word-wrap: break-word;
}

.msg-text {
  white-space: pre-wrap;
  margin: 0;
}

.msg-markdown {
  line-height: 1.7;
}

.msg-markdown :deep(p) {
  margin: 0 0 8px;
}

.msg-markdown :deep(p:last-child) {
  margin-bottom: 0;
}

.msg-markdown :deep(pre) {
  background: var(--docmind-bg);
  border: 1px solid var(--docmind-border);
  border-radius: 8px;
  padding: 12px;
  overflow-x: auto;
  font-size: 13px;
  margin: 8px 0;
}

.msg-markdown :deep(code) {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 13px;
}

.msg-markdown :deep(:not(pre) > code) {
  background: var(--docmind-bg);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
}

.msg-markdown :deep(strong) {
  font-weight: 600;
}

.msg-markdown :deep(ul),
.msg-markdown :deep(ol) {
  padding-left: 20px;
  margin: 6px 0;
}

.msg-markdown :deep(li) {
  margin-bottom: 4px;
}

.msg-markdown :deep(a) {
  color: var(--docmind-primary-light);
  text-decoration: underline;
}

.msg-markdown :deep(blockquote) {
  border-left: 3px solid var(--docmind-primary);
  padding-left: 12px;
  margin: 8px 0;
  color: var(--docmind-text-secondary);
}

.stream-cursor {
  display: inline-block;
  color: var(--docmind-primary-light);
  animation: cursorBlink 0.8s step-end infinite;
  margin-left: 2px;
}

@keyframes cursorBlink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

/* 思考中动画 */
.thinking-bubble {
  display: flex;
  gap: 4px;
  align-items: center;
  padding: 16px 20px;
}

.thinking-dot {
  width: 8px;
  height: 8px;
  background: var(--docmind-text-muted);
  border-radius: 50%;
  animation: thinkingBounce 1.4s ease-in-out infinite;
}

.thinking-dot:nth-child(2) { animation-delay: 0.2s; }
.thinking-dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes thinkingBounce {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}

/* 引用来源 */
.msg-references {
  margin-top: 8px;
}

.refs-toggle {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--docmind-text-muted);
  cursor: pointer;
  padding: 4px 10px;
  border-radius: 6px;
  transition: all 0.2s;
}

.refs-toggle:hover {
  background: var(--docmind-bg-surface-hover);
  color: var(--docmind-text-secondary);
}

.refs-toggle .rotated {
  transform: rotate(180deg);
}

.refs-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 8px;
}

/* 消息操作按钮 */
.msg-actions {
  margin-top: 6px;
  padding-left: 4px;
  display: flex;
  gap: 4px;
}

/* ========== 输入区 ========== */
.chat-input-area {
  flex-shrink: 0;
  padding: 12px 20px 16px;
  border-top: 1px solid var(--docmind-border);
  background: var(--docmind-bg-secondary);
}

.input-wrapper {
  display: flex;
  gap: 10px;
  align-items: flex-end;
}

.chat-input-el {
  flex: 1;
}

.chat-input-el :deep(.el-textarea__inner) {
  background: var(--docmind-bg-surface) !important;
  border: 1px solid var(--docmind-border) !important;
  border-radius: 12px !important;
  color: var(--docmind-text) !important;
  font-size: 14px;
  line-height: 1.6;
  padding: 10px 16px;
  min-height: 44px;
  transition: all 0.2s;
}

.chat-input-el :deep(.el-textarea__inner:focus) {
  border-color: var(--docmind-primary) !important;
  box-shadow: 0 0 0 2px rgba(217, 119, 6, 0.1) !important;
}

.chat-input-el :deep(.el-textarea__inner::placeholder) {
  color: var(--docmind-text-muted);
}

.send-btn-el {
  height: 44px !important;
  width: 44px !important;
  flex-shrink: 0;
  border-radius: 12px !important;
}

/* 过渡动画 */
.slide-enter-active,
.slide-leave-active {
  transition: all 0.2s ease;
  overflow: hidden;
}

.slide-enter-from,
.slide-leave-to {
  opacity: 0;
  max-height: 0;
}
</style>

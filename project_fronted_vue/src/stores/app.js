import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

const STORAGE_KEY_API_KEY = 'docmind_api_key'
const STORAGE_KEY_BASE_URL = 'docmind_base_url'
const REQUEST_TIMEOUT = 15000  // 所有 API 请求 15 秒超时

export const useAppStore = defineStore('app', () => {
  // ==================== API 配置 ====================
  const apiBaseUrl = ref('http://localhost:8000')
  const apiKey = ref('')

  function saveToStorage() {
    localStorage.setItem(STORAGE_KEY_API_KEY, apiKey.value.trim())
    localStorage.setItem(STORAGE_KEY_BASE_URL, apiBaseUrl.value.trim())
  }

  function loadFromStorage() {
    apiKey.value = localStorage.getItem(STORAGE_KEY_API_KEY) || ''
    apiBaseUrl.value = localStorage.getItem(STORAGE_KEY_BASE_URL) || 'http://localhost:8000'
  }

  // ==================== 全局状态 ====================
  const kbs = ref([])
  const loading = ref(false)

  function getBaseUrl() {
    return apiBaseUrl.value || ''
  }

  /**
   * 带超时的 fetch 封装
   * 所有 API 请求统一走此函数，避免因后端无响应导致页面无限转圈
   */
  async function fetchWithTimeout(url, options = {}, timeoutMs = REQUEST_TIMEOUT) {
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), timeoutMs)
    try {
      const res = await fetch(url, { ...options, signal: controller.signal })
      return res
    } finally {
      clearTimeout(timer)
    }
  }

  async function request(path, opts = {}) {
    const url = `${getBaseUrl()}${path}`
    const headers = {
      'Content-Type': 'application/json',
      'X-API-Key': apiKey.value,
      ...opts.headers,
    }
    // 使用带超时的 fetch
    const res = await fetchWithTimeout(url, { ...opts, headers })
    if (!res.ok) {
      let detail = `请求失败 (${res.status})`
      try {
        const body = await res.json()
        detail = body.detail || detail
      } catch {}
      throw new Error(detail)
    }
    return opts.raw ? res : res.json()
  }

  async function fetchKnowledgeBases() {
    loading.value = true
    try {
      kbs.value = await request('/api/v1/knowledge-bases')
      return kbs.value
    } finally {
      loading.value = false
    }
  }

  async function createKnowledgeBase(name, description = '') {
    const kb = await request('/api/v1/knowledge-bases', {
      method: 'POST',
      body: JSON.stringify({ name, description }),
    })
    await fetchKnowledgeBases()
    return kb
  }

  async function deleteKnowledgeBase(id) {
    await request(`/api/v1/knowledge-bases/${id}`, { method: 'DELETE' })
    await fetchKnowledgeBases()
  }

  async function updateKnowledgeBase(id, data) {
    const kb = await request(`/api/v1/knowledge-bases/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
    await fetchKnowledgeBases()
    return kb
  }

  async function uploadDocument(kbId, file) {
    const fd = new FormData()
    fd.append('file', file)
    const url = `${getBaseUrl()}/api/v1/knowledge-bases/${kbId}/documents`
    // uploadDocument 不走 request() 因为 Content-Type 由浏览器自动设置
    const res = await fetchWithTimeout(url, {
      method: 'POST',
      headers: { 'X-API-Key': apiKey.value },
      body: fd,
    })
    if (!res.ok) {
      let detail = `上传失败 (${res.status})`
      try { const b = await res.json(); detail = b.detail || detail } catch {}
      throw new Error(detail)
    }
    return res.json()
  }

  async function getDocuments(kbId) {
    return request(`/api/v1/knowledge-bases/${kbId}/documents`)
  }

  async function deleteDocument(kbId, docId) {
    return request(`/api/v1/knowledge-bases/${kbId}/documents/${docId}`, {
      method: 'DELETE',
    })
  }

  async function getKnowledgeBase(id) {
    return request(`/api/v1/knowledge-bases/${id}`)
  }

  // ==================== 对话历史 API ====================

  async function listConversations(kbId) {
    return request(`/api/v1/conversations?kb_id=${kbId}&limit=50`)
  }

  async function createConversation(kbId, kbName = '') {
    return request('/api/v1/conversations', {
      method: 'POST',
      body: JSON.stringify({ kb_id: kbId, kb_name: kbName }),
    })
  }

  async function getConversation(convId) {
    return request(`/api/v1/conversations/${convId}`)
  }

  async function appendMessage(convId, role, content, references = null) {
    return request(`/api/v1/conversations/${convId}`, {
      method: 'PUT',
      body: JSON.stringify({ role, content, index: -1, references }),
    })
  }

  async function updateMessage(convId, index, content, references = null) {
    return request(`/api/v1/conversations/${convId}`, {
      method: 'PUT',
      body: JSON.stringify({ role: 'assistant', content, index, references }),
    })
  }

  async function deleteConversation(convId) {
    return request(`/api/v1/conversations/${convId}`, { method: 'DELETE' })
  }

  const isConfigured = computed(() => !!apiKey.value)

  return {
    apiBaseUrl,
    apiKey,
    kbs,
    loading,
    getBaseUrl,
    saveToStorage,
    loadFromStorage,
    request,
    fetchKnowledgeBases,
    createKnowledgeBase,
    deleteKnowledgeBase,
    updateKnowledgeBase,
    uploadDocument,
    getDocuments,
    deleteDocument,
    getKnowledgeBase,
    listConversations,
    createConversation,
    getConversation,
    appendMessage,
    updateMessage,
    deleteConversation,
    isConfigured,
  }
})

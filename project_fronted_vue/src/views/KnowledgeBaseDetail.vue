<template>
  <div class="kb-detail-page" v-loading="pageLoading">
    <!-- 头部 -->
    <div class="detail-header">
      <div class="header-left">
        <el-button text @click="$router.push('/knowledge-bases')" class="back-btn">
          <el-icon><ArrowLeft /></el-icon>
          返回
        </el-button>
        <div v-if="kb" class="header-info">
          <h1 class="kb-title">{{ kb.name }}</h1>
          <p class="kb-desc">{{ kb.description || '暂无描述' }}</p>
        </div>
      </div>
      <div class="header-stats" v-if="kb">
        <el-tag round>{{ kb.document_count || 0 }} 文档</el-tag>
        <el-tag round type="info">{{ kb.chunk_count || 0 }} 片段</el-tag>
      </div>
    </div>

    <!-- Tabs -->
    <div class="detail-tabs" v-if="kb">
      <el-tabs v-model="activeTab" class="custom-tabs">
        <el-tab-pane label="文档管理" name="documents">
          <DocumentList :kb-id="kb.id" @update="refreshKb" />
        </el-tab-pane>
        <el-tab-pane label="智能问答" name="chat">
          <ChatPanel :kb-id="kb.id" :kb-name="kb.name" />
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- 知识库不存在 -->
    <div v-else-if="!pageLoading" class="not-found">
      <el-empty description="知识库不存在或已被删除">
        <el-button type="primary" @click="$router.push('/knowledge-bases')">返回列表</el-button>
      </el-empty>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { ElMessage } from 'element-plus'
import { ArrowLeft } from '@element-plus/icons-vue'
import DocumentList from '@/components/DocumentList.vue'
import ChatPanel from '@/components/ChatPanel.vue'

const route = useRoute()
const store = useAppStore()

const kb = ref(null)
const pageLoading = ref(false)
const activeTab = ref('documents')

async function loadKb() {
  pageLoading.value = true
  try {
    kb.value = await store.getKnowledgeBase(route.params.id)
  } catch (e) {
    kb.value = null
    ElMessage.error('获取知识库失败')
  } finally {
    pageLoading.value = false
  }
}

async function refreshKb() {
  try {
    kb.value = await store.getKnowledgeBase(route.params.id)
  } catch {}
}

onMounted(loadKb)
</script>

<style scoped>
.kb-detail-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 20px 28px 0;
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.back-btn {
  font-size: 14px;
  color: var(--docmind-text-secondary) !important;
  margin-top: 2px;
}

.back-btn:hover {
  color: var(--docmind-text) !important;
}

.header-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.kb-title {
  font-family: 'Playfair Display', Georgia, serif;
  font-size: 24px;
  font-weight: 700;
  margin: 0;
  color: var(--docmind-text);
}

.kb-desc {
  font-size: 14px;
  color: var(--docmind-text-muted);
  margin: 0;
}

.header-stats {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.detail-tabs {
  flex: 1;
  padding: 8px 28px 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.custom-tabs {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.custom-tabs :deep(.el-tabs__content) {
  flex: 1;
  overflow: hidden;
}

.custom-tabs :deep(.el-tab-pane) {
  height: 100%;
  overflow: hidden;
}

.custom-tabs :deep(.el-tabs__header) {
  margin-bottom: 16px;
  border-bottom-color: var(--docmind-border);
}

.custom-tabs :deep(.el-tabs__item) {
  color: var(--docmind-text-secondary);
  font-size: 14px;
  font-weight: 500;
}

.custom-tabs :deep(.el-tabs__item.is-active) {
  color: var(--docmind-primary-light);
}

.custom-tabs :deep(.el-tabs__active-bar) {
  background-color: var(--docmind-primary-light);
}

.not-found {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1;
}
</style>

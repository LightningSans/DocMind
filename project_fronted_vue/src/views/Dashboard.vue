<template>
  <div class="dashboard">
    <!-- ⚠️ 未配置 API 的引导提示 -->
    <div v-if="!store.isConfigured" class="setup-banner">
      <div class="setup-banner-content">
        <div class="setup-icon">⚙️</div>
        <div class="setup-text">
          <h3>欢迎使用 DocMind</h3>
          <p>请先配置 API 连接信息，才能开始使用</p>
        </div>
        <el-button type="primary" size="large" @click="$router.push('/settings')">
          <el-icon><Setting /></el-icon>
          前往配置
        </el-button>
      </div>
    </div>

    <!-- Hero -->
    <div class="dashboard-hero">
      <div class="hero-content">
        <h1 class="hero-title">DocMind</h1>
        <p class="hero-subtitle">基于 RAG 技术的企业文档智能问答引擎</p>
        <div class="hero-actions">
          <el-button type="primary" size="large" @click="$router.push('/knowledge-bases')">
            <el-icon><FolderOpened /></el-icon>
            管理知识库
          </el-button>
          <el-button size="large" @click="$router.push('/settings')">
            <el-icon><Setting /></el-icon>
            API 设置
          </el-button>
        </div>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-row">
      <el-card shadow="never" class="stat-card" v-loading="loading">
        <div class="stat-inner">
          <div class="stat-icon" style="background: rgba(217,119,6,0.12)">
            <el-icon :size="24" color="#f59e0b"><FolderOpened /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.kbCount }}</div>
            <div class="stat-label">知识库</div>
          </div>
        </div>
      </el-card>
      <el-card shadow="never" class="stat-card">
        <div class="stat-inner">
          <div class="stat-icon" style="background: rgba(16,185,129,0.12)">
            <el-icon :size="24" color="#10b981"><Document /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.docCount }}</div>
            <div class="stat-label">文档</div>
          </div>
        </div>
      </el-card>
      <el-card shadow="never" class="stat-card">
        <div class="stat-inner">
          <div class="stat-icon" style="background: rgba(99,102,241,0.12)">
            <el-icon :size="24" color="#6366f1"><Connection /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.chunkCount }}</div>
            <div class="stat-label">文本片段</div>
          </div>
        </div>
      </el-card>
      <el-card shadow="never" class="stat-card">
        <div class="stat-inner">
          <div class="stat-icon" style="background: rgba(236,72,153,0.12)">
            <el-icon :size="24" color="#ec4899"><ChatDotRound /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">RAG</div>
            <div class="stat-label">检索增强生成</div>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 最近知识库 -->
    <div class="section">
      <div class="section-header">
        <h2 class="section-title">最近知识库</h2>
        <el-button text type="primary" @click="$router.push('/knowledge-bases')">
          查看全部 <el-icon><ArrowRight /></el-icon>
        </el-button>
      </div>

      <div v-if="!store.isConfigured" class="empty-state">
        <el-empty description="配置 API 后即可查看知识库" />
      </div>

      <div v-else-if="loading" v-loading="loading" style="height:80px"></div>

      <div v-else-if="!store.kbs.items || store.kbs.items.length === 0" class="empty-state">
        <el-empty description="还没有知识库，点击右上角创建" />
      </div>

      <div v-else class="kb-cards">
        <el-card
          v-for="kb in recentKbs"
          :key="kb.id"
          shadow="never"
          class="kb-card"
          @click="$router.push(`/knowledge-bases/${kb.id}`)"
        >
          <div class="kb-card-body">
            <div class="kb-card-header">
              <el-icon color="#f59e0b"><Folder /></el-icon>
              <span class="kb-card-name">{{ kb.name }}</span>
            </div>
            <p class="kb-card-desc">{{ kb.description || '暂无描述' }}</p>
            <div class="kb-card-meta">
              <el-tag size="small" round>{{ kb.document_count || 0 }} 文档</el-tag>
              <el-tag size="small" round type="info">{{ kb.chunk_count || 0 }} 片段</el-tag>
            </div>
          </div>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, watch } from 'vue'
import { useAppStore } from '@/stores/app'
import { ElMessage } from 'element-plus'

const store = useAppStore()
const loading = computed(() => store.loading)

const stats = reactive({
  kbCount: 0,
  docCount: 0,
  chunkCount: 0,
})

const recentKbs = computed(() => {
  const items = store.kbs.items || []
  return items.slice(0, 6)
})

/**
 * 当 API 配置从 false 变为 true 时自动加载数据
 * 解决：用户在设置页保存后回到概览页，数据不加载的问题
 */
watch(() => store.isConfigured, (newVal) => {
  if (newVal) {
    loadDashboardData()
  }
})

async function loadDashboardData() {
  try {
    const data = await store.fetchKnowledgeBases()
    if (data && data.items) {
      stats.kbCount = data.total || data.items.length
      stats.docCount = data.items.reduce((s, kb) => s + (kb.document_count || 0), 0)
      stats.chunkCount = data.items.reduce((s, kb) => s + (kb.chunk_count || 0), 0)
    }
  } catch (e) {
    console.error('Dashboard 加载数据失败:', e)
    ElMessage.warning('获取知识库列表失败，请检查 API 设置')
  }
}

onMounted(async () => {
  if (!store.isConfigured) return
  await loadDashboardData()
})
</script>

<style scoped>
.dashboard {
  padding: 0;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  height: 100%;
}

/* ===== API 未配置引导条 ===== */
.setup-banner {
  background: linear-gradient(135deg, rgba(217,119,6,0.12), rgba(245,158,11,0.06));
  border-bottom: 1px solid rgba(217,119,6,0.2);
  padding: 16px 36px;
}

.setup-banner-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.setup-icon {
  font-size: 32px;
  flex-shrink: 0;
}

.setup-text {
  flex: 1;
}

.setup-text h3 {
  margin: 0 0 2px;
  font-size: 16px;
  font-weight: 600;
  color: var(--docmind-text);
}

.setup-text p {
  margin: 0;
  font-size: 14px;
  color: var(--docmind-text-muted);
}

.dashboard-hero {
  padding: 40px 36px 32px;
  background: linear-gradient(135deg, var(--docmind-bg-secondary) 0%, var(--docmind-bg) 100%);
  border-bottom: 1px solid var(--docmind-border);
}

.hero-title {
  font-family: 'Playfair Display', Georgia, serif;
  font-size: 36px;
  font-weight: 700;
  margin: 0 0 8px;
  color: var(--docmind-text);
}

.hero-subtitle {
  font-size: 15px;
  color: var(--docmind-text-secondary);
  margin: 0 0 24px;
}

.hero-actions {
  display: flex;
  gap: 12px;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  padding: 24px 36px;
}

.stat-card {
  border: 1px solid var(--docmind-border) !important;
  border-radius: var(--docmind-radius) !important;
  background: var(--docmind-bg-secondary) !important;
}

.stat-card:hover {
  border-color: var(--docmind-border-light) !important;
}

.stat-inner {
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  flex-shrink: 0;
}

.stat-info {
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--docmind-text);
  line-height: 1.2;
}

.stat-label {
  font-size: 13px;
  color: var(--docmind-text-muted);
  margin-top: 2px;
}

.section {
  padding: 0 36px 32px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.section-title {
  font-family: 'Playfair Display', Georgia, serif;
  font-size: 20px;
  font-weight: 600;
  margin: 0;
  color: var(--docmind-text);
}

.empty-state {
  padding: 40px 0;
}

.kb-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
}

.kb-card {
  border: 1px solid var(--docmind-border) !important;
  border-radius: var(--docmind-radius) !important;
  background: var(--docmind-bg-secondary) !important;
  cursor: pointer;
  transition: all 0.2s;
}

.kb-card:hover {
  border-color: var(--docmind-primary) !important;
  transform: translateY(-2px);
}

.kb-card-body {
  padding: 0;
}

.kb-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.kb-card-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--docmind-text);
}

.kb-card-desc {
  font-size: 13px;
  color: var(--docmind-text-muted);
  margin: 0 0 12px;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.kb-card-meta {
  display: flex;
  gap: 6px;
}
</style>

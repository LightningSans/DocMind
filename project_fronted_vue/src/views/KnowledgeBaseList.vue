<template>
  <div class="kb-list-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <div>
        <h1 class="page-title">知识库管理</h1>
        <p class="page-desc">创建和管理您的知识库，上传文档后进行智能问答</p>
      </div>
      <el-button type="primary" @click="showCreateDialog = true">
        <el-icon><Plus /></el-icon>
        新建知识库
      </el-button>
    </div>

    <!-- 搜索 & 表格 -->
    <el-card shadow="never" class="content-card">
      <div class="toolbar">
        <el-input
          v-model="searchQuery"
          placeholder="搜索知识库..."
          clearable
          :prefix-icon="Search"
          class="search-input"
        />
        <el-button text @click="loadKbs" :loading="loading" style="margin-left:8px">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>

      <el-table
        :data="filteredKbs"
        v-loading="loading"
        stripe
        style="width: 100%"
        @row-click="goToDetail"
      >
        <el-table-column prop="name" label="名称" min-width="160">
          <template #default="{ row }">
            <div class="kb-name-cell">
              <el-icon color="#f59e0b"><Folder /></el-icon>
              <span>{{ row.name }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="desc-text">{{ row.description || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="document_count" label="文档数" width="100" align="center">
          <template #default="{ row }">
            <el-tag round size="small">{{ row.document_count || 0 }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="chunk_count" label="片段数" width="100" align="center">
          <template #default="{ row }">
            <el-tag round size="small" type="info">{{ row.chunk_count || 0 }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="180" align="center">
          <template #default="{ row }">
            <span class="time-text">{{ formatTime(row.created_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" align="center" fixed="right">
          <template #default="{ row }">
            <el-button text type="danger" size="small" @click.stop="handleDelete(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div v-if="!loading && filteredKbs.length === 0" class="table-empty">
        <el-empty :description="searchQuery ? '没有匹配的知识库' : '还没有知识库，点击右上角创建'" />
      </div>
    </el-card>

    <!-- 创建对话框 -->
    <el-dialog v-model="showCreateDialog" title="新建知识库" width="480px" top="25vh">
      <el-form :model="createForm" :rules="createRules" ref="createFormRef" label-width="80px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="createForm.name" placeholder="输入知识库名称" maxlength="200" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input
            v-model="createForm.description"
            type="textarea"
            :rows="3"
            placeholder="可选：简要描述知识库的用途"
            maxlength="1000"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="handleCreate" :loading="creating">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Plus, Folder, Refresh } from '@element-plus/icons-vue'

const router = useRouter()
const store = useAppStore()
const loading = ref(false)
const searchQuery = ref('')
const showCreateDialog = ref(false)
const creating = ref(false)
const createFormRef = ref(null)

const createForm = ref({ name: '', description: '' })
const createRules = {
  name: [{ required: true, message: '请输入知识库名称', trigger: 'blur' }],
}

const filteredKbs = computed(() => {
  const items = store.kbs.items || []
  if (!searchQuery.value) return items
  const q = searchQuery.value.toLowerCase()
  return items.filter((kb) => kb.name.toLowerCase().includes(q) || (kb.description || '').toLowerCase().includes(q))
})

async function loadKbs() {
  if (!store.isConfigured) {
    ElMessage.warning('请先在 API 设置中配置连接信息')
    return
  }
  loading.value = true
  try {
    await store.fetchKnowledgeBases()
  } catch (e) {
    console.error('获取知识库列表失败:', e)
    ElMessage.warning('获取知识库列表失败，请检查 API 设置')
  } finally {
    loading.value = false
  }
}

/**
 * 当 API 配置状态从 false 变为 true 时自动加载数据
 * 这样用户在设置页面保存后回到此页面，数据会自动加载
 */
watch(() => store.isConfigured, (newVal) => {
  if (newVal) {
    loadKbs()
  }
})

async function handleCreate() {
  const valid = await createFormRef.value?.validate().catch(() => false)
  if (!valid) return
  creating.value = true
  try {
    await store.createKnowledgeBase(createForm.value.name, createForm.value.description)
    ElMessage.success('知识库创建成功')
    showCreateDialog.value = false
    createForm.value = { name: '', description: '' }
  } catch (e) {
    ElMessage.error('创建失败：' + e.message)
  } finally {
    creating.value = false
  }
}

function handleDelete(row) {
  ElMessageBox.confirm(`确定要删除知识库「${row.name}」吗？所有文档数据将永久移除。`, '确认删除', {
    confirmButtonText: '删除',
    cancelButtonText: '取消',
    type: 'warning',
    confirmButtonClass: 'el-button--danger',
  }).then(async () => {
    try {
      await store.deleteKnowledgeBase(row.id)
      ElMessage.success('已删除')
    } catch (e) {
      ElMessage.error('删除失败：' + e.message)
    }
  }).catch(() => {})
}

function goToDetail(row) {
  router.push(`/knowledge-bases/${row.id}`)
}

function formatTime(t) {
  if (!t) return '-'
  try {
    const d = new Date(t)
    return d.toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
  } catch {
    return t
  }
}

onMounted(() => {
  if (store.isConfigured) {
    loadKbs()
  }
})
</script>

<style scoped>
.kb-list-page {
  padding: 28px 32px;
  overflow-y: auto;
  height: 100%;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.page-title {
  font-family: 'Playfair Display', Georgia, serif;
  font-size: 26px;
  font-weight: 700;
  margin: 0 0 4px;
  color: var(--docmind-text);
}

.page-desc {
  font-size: 14px;
  color: var(--docmind-text-muted);
  margin: 0;
}

.content-card {
  border: 1px solid var(--docmind-border) !important;
  border-radius: 12px !important;
  background: var(--docmind-bg-secondary) !important;
}

.toolbar {
  display: flex;
  align-items: center;
  margin-bottom: 16px;
}

.search-input {
  width: 320px;
}

.kb-name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

.desc-text {
  color: var(--docmind-text-secondary);
  font-size: 13px;
}

.time-text {
  color: var(--docmind-text-muted);
  font-size: 13px;
}

.table-empty {
  padding: 40px 0;
}
</style>

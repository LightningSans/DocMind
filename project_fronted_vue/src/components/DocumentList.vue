<template>
  <div class="document-list-page">
    <!-- 工具栏 -->
    <div class="doc-toolbar">
      <div class="doc-info-text">
        <el-icon color="#8b8694"><Document /></el-icon>
        <span>共 <strong>{{ documents.length }}</strong> 个文档</span>
      </div>
      <el-button type="primary" size="default" @click="showUpload = true">
        <el-icon><Upload /></el-icon>
        上传文档
      </el-button>
    </div>

    <!-- 文档表格 -->
    <el-table :data="documents" v-loading="loadingDocs" stripe style="width: 100%" empty-text="暂无文档">
      <el-table-column label="文件名" min-width="200">
        <template #default="{ row }">
          <div class="doc-name-cell">
            <el-icon :color="fileIconColor(row.filename)">
              <template v-if="row.filename?.endsWith('.pdf')"><Tickets /></template>
              <template v-else-if="row.filename?.endsWith('.md')"><Document /></template>
              <template v-else><Document /></template>
            </el-icon>
            <span>{{ row.filename || row.document_id?.slice(0, 12) }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="类型" width="90" align="center">
        <template #default="{ row }">
          <el-tag size="small" round>{{ getFileExt(row.filename) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="文本块数" width="110" align="center">
        <template #default="{ row }">
          <el-tag round size="small" type="info">{{ row.chunk_count || 0 }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="100" align="center" fixed="right">
        <template #default="{ row }">
          <el-popconfirm title="确认删除此文档？" @confirm="handleDelete(row)">
            <template #reference>
              <el-button text type="danger" size="small">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <!-- 上传对话框 -->
    <el-dialog v-model="showUpload" title="上传文档" width="520px" top="20vh">
      <el-upload
        ref="uploadRef"
        drag
        :auto-upload="false"
        :limit="1"
        :on-change="onFileChange"
        accept=".txt,.md,.pdf"
        class="upload-area"
      >
        <el-icon class="upload-icon" :size="48"><UploadFilled /></el-icon>
        <div class="upload-text">
          <span>拖拽文件到此处，或 <em>点击选择</em></span>
        </div>
        <template #tip>
          <div class="upload-tip">
            支持 .txt、.md、.pdf 格式，单文件不超过 20MB
          </div>
        </template>
      </el-upload>
      <div v-if="selectedFile" class="file-preview">
        <el-tag closable @close="clearFile" type="info">
          {{ selectedFile.name }}
        </el-tag>
      </div>
      <div v-if="uploadStatus" :class="['upload-status', { error: uploadStatus.type === 'error' }]">
        {{ uploadStatus.text }}
      </div>
      <template #footer>
        <el-button @click="showUpload = false">取消</el-button>
        <el-button type="primary" :disabled="!selectedFile" :loading="uploading" @click="handleUpload">
          {{ uploading ? '上传中...' : '上传' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useAppStore } from '@/stores/app'
import { ElMessage } from 'element-plus'
import { Upload, UploadFilled, Document, Tickets } from '@element-plus/icons-vue'

const props = defineProps({
  kbId: { type: String, required: true },
})

const emit = defineEmits(['update'])

const store = useAppStore()
const documents = ref([])
const loadingDocs = ref(false)
const showUpload = ref(false)
const selectedFile = ref(null)
const uploading = ref(false)
const uploadStatus = ref(null)
const uploadRef = ref(null)

async function loadDocuments() {
  loadingDocs.value = true
  try {
    const data = await store.getDocuments(props.kbId)
    documents.value = data.items || []
  } catch (e) {
    ElMessage.error('获取文档列表失败')
  } finally {
    loadingDocs.value = false
  }
}

function onFileChange(file) {
  selectedFile.value = file.raw
  uploadStatus.value = null
}

function clearFile() {
  selectedFile.value = null
  uploadRef.value?.clearFiles()
}

async function handleUpload() {
  if (!selectedFile.value) return
  uploading.value = true
  uploadStatus.value = { text: '上传中...', type: 'info' }
  try {
    const result = await store.uploadDocument(props.kbId, selectedFile.value)
    uploadStatus.value = { text: result.message || '上传成功 ✓', type: 'success' }
    ElMessage.success('文档上传成功')
    setTimeout(() => {
      showUpload.value = false
      selectedFile.value = null
      uploadRef.value?.clearFiles()
      uploadStatus.value = null
      loadDocuments()
      emit('update')
    }, 1000)
  } catch (e) {
    uploadStatus.value = { text: '失败: ' + e.message, type: 'error' }
  } finally {
    uploading.value = false
  }
}

async function handleDelete(row) {
  try {
    await store.deleteDocument(props.kbId, row.id || row.document_id)
    ElMessage.success('文档已删除')
    loadDocuments()
    emit('update')
  } catch (e) {
    ElMessage.error('删除失败：' + e.message)
  }
}

function getFileExt(name) {
  if (!name) return '?'
  const ext = name.split('.').pop()?.toUpperCase()
  return ext || '?'
}

function fileIconColor(name) {
  if (!name) return '#8b8694'
  if (name.endsWith('.pdf')) return '#ef4444'
  if (name.endsWith('.md')) return '#3b82f6'
  return '#8b8694'
}

onMounted(loadDocuments)
</script>

<style scoped>
.document-list-page {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.doc-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-shrink: 0;
}

.doc-info-text {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  color: var(--docmind-text-secondary);
}

.doc-name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
}

.upload-area {
  width: 100%;
}

.upload-area :deep(.el-upload-dragger) {
  background: var(--docmind-bg) !important;
  border: 2px dashed var(--docmind-border-light) !important;
  border-radius: 12px !important;
  padding: 32px !important;
  width: 100%;
}

.upload-area :deep(.el-upload-dragger:hover) {
  border-color: var(--docmind-primary) !important;
  background: rgba(217, 119, 6, 0.03) !important;
}

.upload-icon {
  color: var(--docmind-text-muted);
  margin-bottom: 12px;
}

.upload-text {
  font-size: 14px;
  color: var(--docmind-text-secondary);
}

.upload-text em {
  color: var(--docmind-primary-light);
  font-style: normal;
  font-weight: 600;
}

.upload-tip {
  font-size: 12px;
  color: var(--docmind-text-muted);
  margin-top: 8px;
}

.file-preview {
  margin-top: 12px;
}

.upload-status {
  margin-top: 12px;
  padding: 8px 14px;
  border-radius: 8px;
  font-size: 13px;
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
}

.upload-status.error {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
}
</style>

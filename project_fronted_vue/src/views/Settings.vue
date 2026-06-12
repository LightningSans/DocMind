<template>
  <div class="settings-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">API 设置</h1>
        <p class="page-desc">配置 DocMind 后端服务的连接信息</p>
      </div>
    </div>

    <div class="settings-content">
      <el-card shadow="never" class="settings-card">
        <el-form :model="form" label-width="140px" label-position="left">
          <el-form-item label="API 地址">
            <el-input v-model="form.apiBaseUrl" placeholder="例如 http://localhost:8000" />
            <div class="form-tip">建议填写完整地址如 http://localhost:8000，直连后端可避免流式问答被代理缓冲</div>
          </el-form-item>
          <el-form-item label="API Key">
            <el-input v-model="form.apiKey" type="password" show-password placeholder="输入 API Key" />
            <div class="form-tip">后端配置的 DOCMIND_API_KEY 值</div>
          </el-form-item>
          <el-form-item label="连接测试">
            <el-button @click="testConnection" :loading="testing">
              测试连接
            </el-button>
            <span v-if="testResult !== null" :class="['test-result', testResult ? 'success' : 'fail']">
              {{ testResult ? '✓ 连接成功' : '✗ 连接失败' }}
            </span>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="saveSettings">保存设置</el-button>
          </el-form-item>
        </el-form>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAppStore } from '@/stores/app'
import { ElMessage } from 'element-plus'

const store = useAppStore()

const form = ref({
  apiBaseUrl: '',
  apiKey: '',
})

const testing = ref(false)
const testResult = ref(null)

onMounted(() => {
  form.value.apiBaseUrl = store.apiBaseUrl
  form.value.apiKey = store.apiKey
})

async function saveSettings() {
  store.apiBaseUrl = form.value.apiBaseUrl
  store.apiKey = form.value.apiKey
  store.saveToStorage()
  ElMessage.success('设置已保存')
}

async function testConnection() {
  testing.value = true
  testResult.value = null
  try {
    const url = `${form.value.apiBaseUrl || ''}/health`
    const res = await fetch(url, {
      headers: { 'X-API-Key': form.value.apiKey },
    })
    const data = await res.json()
    testResult.value = data.status === 'ok'
  } catch (e) {
    testResult.value = false
  } finally {
    testing.value = false
  }
}
</script>

<style scoped>
.settings-page {
  padding: 28px 32px;
  overflow-y: auto;
  height: 100%;
}

.page-header {
  margin-bottom: 28px;
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

.settings-content {
  max-width: 600px;
}

.settings-card {
  border: 1px solid var(--docmind-border) !important;
  border-radius: 12px !important;
  background: var(--docmind-bg-secondary) !important;
  padding: 8px;
}

.form-tip {
  font-size: 12px;
  color: var(--docmind-text-muted);
  margin-top: 4px;
}

.test-result {
  margin-left: 12px;
  font-size: 14px;
  font-weight: 600;
}

.test-result.success {
  color: #10b981;
}

.test-result.fail {
  color: #ef4444;
}
</style>

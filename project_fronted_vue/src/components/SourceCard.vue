<template>
  <div class="source-card">
    <div class="source-header" @click="expanded = !expanded">
      <div class="source-doc-info">
        <el-icon :size="14" color="#8b8694"><Tickets /></el-icon>
        <span class="source-doc-name">{{ doc.document_name || doc.document_id?.slice(0, 10) || '来源文档' }}</span>
      </div>
      <div class="source-meta">
        <span class="source-score" :class="{ high: (doc.score || 0) > 0.75 }">
          {{ ((doc.score || 0) * 100).toFixed(0) }}%
        </span>
        <el-icon :size="14" class="expand-icon" :class="{ expanded }">
          <ArrowDown />
        </el-icon>
      </div>
    </div>
    <transition name="slide">
      <div v-show="expanded" class="source-body">
        <p class="source-text">{{ doc.content || '（无内容）' }}</p>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { Tickets, ArrowDown } from '@element-plus/icons-vue'

defineProps({
  doc: { type: Object, required: true },
})

const expanded = ref(false)
</script>

<style scoped>
.source-card {
  background: var(--docmind-bg);
  border: 1px solid var(--docmind-border);
  border-radius: 8px;
  overflow: hidden;
  transition: border-color 0.2s;
}

.source-card:hover {
  border-color: var(--docmind-border-light);
}

.source-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  cursor: pointer;
  user-select: none;
}

.source-doc-info {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.source-doc-name {
  font-size: 12px;
  font-weight: 600;
  color: var(--docmind-text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.source-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.source-score {
  font-size: 11px;
  font-weight: 700;
  color: var(--docmind-text-muted);
  padding: 1px 8px;
  border-radius: 10px;
  background: var(--docmind-bg-surface);
}

.source-score.high {
  color: #10b981;
  background: rgba(16, 185, 129, 0.1);
}

.expand-icon {
  color: var(--docmind-text-muted);
  transition: transform 0.2s;
}

.expand-icon.expanded {
  transform: rotate(180deg);
}

.source-body {
  border-top: 1px solid var(--docmind-border);
  padding: 10px 12px;
}

.source-text {
  font-size: 12px;
  color: var(--docmind-text-muted);
  line-height: 1.6;
  margin: 0;
}

.slide-enter-active,
.slide-leave-active {
  transition: all 0.2s ease;
  overflow: hidden;
}

.slide-enter-from,
.slide-leave-to {
  opacity: 0;
  max-height: 0;
  padding-top: 0;
  padding-bottom: 0;
}
</style>

<template>
  <el-container class="app-container">
    <!-- 侧边栏 -->
    <el-aside :width="sidebarWidth" class="app-sidebar">
      <div class="sidebar-inner">
        <!-- Logo -->
        <div class="sidebar-logo">
          <span class="logo-icon">✦</span>
          <span class="logo-text" v-show="!isCollapsed">DocMind</span>
        </div>

        <!-- 导航菜单 -->
        <el-menu
          :default-active="activeMenu"
          :collapse="isCollapsed"
          :collapse-transition="false"
          router
          class="sidebar-menu"
        >
          <el-menu-item index="/">
            <el-icon><Odometer /></el-icon>
            <template #title>概览</template>
          </el-menu-item>
          <el-menu-item index="/knowledge-bases">
            <el-icon><FolderOpened /></el-icon>
            <template #title>知识库管理</template>
          </el-menu-item>
          <el-menu-item index="/settings">
            <el-icon><Setting /></el-icon>
            <template #title>API 设置</template>
          </el-menu-item>
        </el-menu>

        <!-- 底部折叠按钮 -->
        <div class="sidebar-collapse-btn" @click="toggleCollapse">
          <el-icon><Fold v-if="!isCollapsed" /><Expand v-else /></el-icon>
          <span v-show="!isCollapsed">收起侧栏</span>
        </div>
      </div>
    </el-aside>

    <!-- 主内容区 -->
    <el-container class="app-main">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const isCollapsed = ref(false)
const sidebarWidth = computed(() => (isCollapsed.value ? '64px' : '240px'))

const activeMenu = computed(() => route.path)

function toggleCollapse() {
  isCollapsed.value = !isCollapsed.value
}
</script>

<style scoped>
.app-container {
  height: 100vh;
  background: var(--docmind-bg);
}

.app-sidebar {
  background: var(--docmind-bg-secondary) !important;
  border-right: 1px solid var(--docmind-border);
  display: flex;
  flex-direction: column;
  transition: width 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
}

.sidebar-inner {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 0;
}

.sidebar-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 24px 20px 20px;
  flex-shrink: 0;
}

.logo-icon {
  font-size: 26px;
  color: var(--docmind-primary-light);
  flex-shrink: 0;
}

.logo-text {
  font-family: 'Playfair Display', Georgia, serif;
  font-size: 22px;
  font-weight: 600;
  color: var(--docmind-text);
  letter-spacing: -0.02em;
  white-space: nowrap;
}

.sidebar-menu {
  flex: 1;
  border-right: none !important;
  padding: 0 8px;
}

.sidebar-menu .el-menu-item {
  border-radius: 8px;
  margin-bottom: 2px;
  font-size: 14px;
}

.sidebar-menu .el-menu-item.is-active {
  background: var(--docmind-bg-surface) !important;
  color: var(--docmind-primary-light) !important;
  font-weight: 600;
}

.sidebar-menu .el-menu-item:hover {
  background: var(--docmind-bg-surface-hover, rgba(255, 255, 255, 0.04)) !important;
}

.sidebar-collapse-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  border-top: 1px solid var(--docmind-border);
  color: var(--docmind-text-muted);
  font-size: 13px;
  cursor: pointer;
  transition: color 0.2s;
  flex-shrink: 0;
  white-space: nowrap;
}

.sidebar-collapse-btn:hover {
  color: var(--docmind-text-secondary);
}

.app-main {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
</style>

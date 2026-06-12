# DocMind 前端 — Vue 3 + Element Plus

DocMind 智能文档问答引擎的前端界面，基于 **Vue 3 + Element Plus + Vite + Pinia** 构建。

## 功能概览

| 页面 | 功能 |
|------|------|
| **概览** | 数据统计看板（知识库数、文档数、片段数）、快捷操作、最近知识库 |
| **知识库管理** | 创建/搜索/编辑/删除知识库，表格展示 |
| **知识库详情** | 文档管理（上传、列表、删除）+ 智能问答（流式对话、来源引用） |
| **API 设置** | 配置后端地址和 API Key，连接测试 |

## 技术栈

- **框架**: Vue 3 (Composition API + `<script setup>`)
- **UI 组件**: Element Plus
- **路由**: Vue Router 4
- **状态管理**: Pinia
- **构建工具**: Vite 6
- **Markdown 渲染**: marked

---

## 📥 从 Gitee 克隆后的第一步

### ❌ 已从仓库中排除的文件/目录

| 排除项 | 原因 | 需要手动 |
|--------|------|----------|
| `node_modules/` | npm 依赖包（平台相关、体积巨大） | ✅ `npm install` |
| `dist/` | 生产构建产物 | ✅ 需要时执行 `npm run build` |

项目本身不包含 API Key 等敏感配置（前端 API Key 由用户在页面「API 设置」中填写，
存储在浏览器 localStorage 中，不会提交到仓库）。

---

## 快速启动

### 1. 确保后端已启动

DocMind 后端必须先启动（默认端口 8000）：

```bash
cd docmind
# 详情请查看后端 README.md
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. 安装前端依赖

```bash
cd project_fronted_vue
npm install
```

### 3. 启动开发服务器

```bash
npm run dev
```

开发服务器默认运行在 `http://localhost:5173`。

Vite 已配置 `/api` 代理到 `http://localhost:8000`，所以开发环境中前端页面内的 API 地址可以不填或留空。

### 4. 在页面中配置连接

打开浏览器访问 `http://localhost:5173`，进入 **API 设置** 页面：

1. **API 地址**：使用 Vite 代理时留空即可，直连后端则填 `http://localhost:8000`
2. **API Key**：填写后端 `.env` 中配置的 `DOCMIND_API_KEY` 值
3. 点击「保存设置」

> 前端 API Key 只保存在浏览器 localStorage 中，不会上传到服务器或提交到 Git 仓库。

## 生产构建

```bash
npm run build   # 输出到 dist/
npm run preview # 预览构建结果
```

`dist/` 目录已被 `.gitignore` 排除，构建产物不会提交到仓库。
部署时请手动构建，或将 `dist/` 目录上传到服务器。

---

## 目录结构

```
project_fronted_vue/
├── index.html
├── package.json
├── vite.config.js
└── src/
    ├── main.js              # 应用入口
    ├── App.vue              # 根组件
    ├── router/
    │   └── index.js         # 路由配置
    ├── stores/
    │   └── app.js           # Pinia 全局状态
    ├── layout/
    │   └── AppLayout.vue    # 整体布局（侧边栏 + 内容区）
    ├── views/
    │   ├── Dashboard.vue         # 概览看板
    │   ├── KnowledgeBaseList.vue # 知识库列表
    │   ├── KnowledgeBaseDetail.vue # 知识库详情
    │   └── Settings.vue          # API 设置
    ├── components/
    │   ├── ChatPanel.vue    # 聊天面板（流式对话）
    │   ├── DocumentList.vue # 文档管理
    │   └── SourceCard.vue   # 引用来源卡片
    └── styles/
        └── theme.css        # 全局样式 & Element Plus 主题覆盖
```

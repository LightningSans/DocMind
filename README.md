# DocMind — 企业文档智能问答引擎

> DocMind 是基于 RAG（检索增强生成）技术的企业文档智能问答系统。
> 支持多知识库隔离管理、文档上传自动向量化，用户可通过自然语言对话查询文档内容，
> 实现**「上传即问」**的智能文档体验。

---

## 功能特性

### 📚 知识库管理
- **创建知识库**：按主题或部门创建独立的知识库（如产品手册、财务制度、技术文档）
- **多知识库隔离**：每个知识库在 Qdrant 中拥有独立的向量集合，数据物理隔离
- **支持增删改查**：创建、列表、详情、更新、删除

### 📄 文档管理
- **多格式支持**：支持 `.txt`、`.md`、`.pdf` 格式文档上传
- **智能分块**：滑动窗口分块算法，带重叠区防止语义截断
- **自动向量化**：上传后自动提取文本 → 分块 → Embedding → 存入向量库
- **文档列表与删除**：按文档查看块数统计，支持删除

### 🤖 智能问答（RAG 核心）
- **语义检索**：用户问题经向量化后在 Qdrant 中执行余弦相似度搜索
- **流式输出（SSE）**：打字机效果逐字输出答案，体验流畅
- **引用溯源**：回答中标注来源文档片段及相似度分数，可信可查
- **上下文增强**：检索到的文档片段作为上下文注入 LLM 提示词

### 💬 对话管理
- **对话历史持久化**：JSON 文件本地存储，支持创建/查询/追加/删除
- **自动标题生成**：从首条消息自动提取对话标题
- **多轮对话**：完整对话上下文，连续提问体验

---

## 系统要求

| 环境 | 版本要求 | 用途 |
|------|----------|------|
| Python | 3.10+ | 运行后端 |
| Node.js | 18+ | 运行前端 |
| Docker | 最新版 | 运行 Qdrant 向量数据库 |
| API Key | 见下方 | DeepSeek + Embedding 服务 |

---

## ⚠️ 从 Gitee 克隆后必须完成的步骤

为避免敏感信息泄露，以下文件已被 `.gitignore` 排除。**克隆后需要手动补全才能运行：**

### 后端（docmind/）

| 缺失项 | 原因 | 操作方式 |
|--------|------|----------|
| `.env` | 包含 API Key 等敏感凭证 | 复制 `.env.example` 为 `.env` 并填写真实值 |
| `.venv/` | Python 虚拟环境（平台相关） | 执行 `python -m venv .venv` 再装依赖 |
| `uploads/` | 用户上传的文档（运行时数据） | 程序自动创建，无需手动 |
| `conversations/` | 用户对话历史（运行时数据） | 程序自动创建，无需手动 |

### 前端（project_fronted_vue/）

| 缺失项 | 原因 | 操作方式 |
|--------|------|----------|
| `node_modules/` | npm 依赖包（体积巨大） | 执行 `npm install` |
| `dist/` | 生产构建产物 | 需要时执行 `npm run build` |

> **详细步骤请分别查看各子目录内的 README.md。**

---

## RAG 系统架构（工作流程）

```
上传文档                             提问
  |                                    |
  v                                    v
提取文本(.txt/.md/.pdf)          Embedding 向量化
  |                                    |
  v                                    v
文本分块(滑动窗口+重叠)        Qdrant cosine 相似度搜索
  |                                    |
  v                                    v
批量 Embedding 向量化         匹配到的文档片段(TOP-K)
  |                                    |
  v                                    v
存入 Qdrant                    拼接上下文 + LLM 生成
                                 SSE 流式返回 + 引用来源
```

用户视角：上传文档 → 直接提问 → 获得带来源引用的答案。

---

## 技术栈

### 后端（docmind/）

| 层次 | 技术 | 用途 |
|------|------|------|
| Web 框架 | FastAPI + Uvicorn | 高性能异步 API 服务，自动生成 Swagger 文档 |
| 向量数据库 | Qdrant（Docker, Cosine 相似度） | 存储文档向量，执行语义检索 |
| 大模型 | DeepSeek Chat（兼容 OpenAI 接口） | 文档问答答案生成 |
| Embedding | 阿里云 DashScope text-embedding-v4 | 文本向量化 |
| 文档处理 | pypdf | 解析 PDF 文件 |
| 数据校验 | Pydantic + pydantic-settings | 请求验证 + 配置管理 |

### 前端（project_fronted_vue/）

| 技术 | 用途 |
|------|------|
| Vue 3 + Vue Router 4 | 前端框架 |
| Element Plus 2.9 | UI 组件库 |
| Pinia | 状态管理 |
| Vite 6 | 构建工具 |
| marked | Markdown 渲染（聊天内容） |

---

## 快速上手（TL;DR）

```bash
# 1. 配置后端环境变量
cd docmind
cp .env.example .env
# 编辑 .env 填入你的 API Key ↓

# 2. 安装后端依赖
python -m venv .venv
# Windows:
.venv\Scripts\pip install -r requirements.txt
# macOS / Linux:
source .venv/bin/activate && pip install -r requirements.txt

# 3. 启动 Qdrant 向量数据库
docker run -d -p 6333:6333 -p 6334:6334 qdrant/qdrant

# 4. 启动后端（默认 http://localhost:8000）
# Windows:
.venv\Scripts\uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
# macOS / Linux:
source .venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 5. 新开终端，启动前端
cd project_fronted_vue
npm install
npm run dev     # 默认 http://localhost:5173
```

---

## 使用示例

### 创建知识库

```bash
curl -X POST http://localhost:8000/api/v1/knowledge-bases \
  -H "X-API-Key: 你的DOCMIND_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "产品手册", "description": "产品使用文档"}'
```

### 上传文档

```bash
curl -X POST http://localhost:8000/api/v1/knowledge-bases/{kb_id}/documents \
  -H "X-API-Key: 你的DOCMIND_API_KEY" \
  -F "file=@document.pdf"
```

### 提问

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "X-API-Key: 你的DOCMIND_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"knowledge_base_id": "{kb_id}", "question": "产品的保修政策是什么？", "stream": true}'
```

---

## 配置项说明

编辑 `docmind/.env` 文件可配置以下参数：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `DOCMIND_API_KEY` | yueyun | API 鉴权密钥，所有接口必须携带 |
| `QDRANT_HOST` | localhost | Qdrant 主机地址 |
| `QDRANT_PORT` | 6333 | Qdrant 端口 |
| `EMBEDDING_API_KEY` | - | Embedding API 密钥（必填） |
| `EMBEDDING_MODEL` | text-embedding-v4 | 向量模型名称 |
| `EMBEDDING_DIMENSION` | 1024 | 向量维度（需与模型匹配） |
| `LLM_API_KEY` | - | 大模型 API 密钥（必填） |
| `LLM_MODEL` | deepseek-chat | 大模型名称 |
| `LLM_TEMPERATURE` | 0.3 | 生成温度（越低越精确） |
| `CHUNK_SIZE` | 512 | 文档分块大小（字符数） |
| `CHUNK_OVERLAP` | 64 | 分块重叠字符数 |
| `RETRIEVAL_TOP_K` | 5 | 每次检索返回的片段数 |
| `MAX_UPLOAD_SIZE_MB` | 20 | 上传文件大小限制 |

### 支持的文件类型

- **.txt**：UTF-8 纯文本文件
- **.md**：Markdown 文档
- **.pdf**：文字型 PDF（扫描件暂不支持 OCR）

---

## API 文档速览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/knowledge-bases` | 知识库列表 |
| POST | `/api/v1/knowledge-bases` | 创建知识库 |
| GET | `/api/v1/knowledge-bases/{id}` | 知识库详情 |
| PUT | `/api/v1/knowledge-bases/{id}` | 更新知识库 |
| DELETE | `/api/v1/knowledge-bases/{id}` | 删除知识库 |
| POST | `/api/v1/knowledge-bases/{id}/documents` | 上传文档 |
| GET | `/api/v1/knowledge-bases/{id}/documents` | 文档列表 |
| DELETE | `/api/v1/knowledge-bases/{id}/documents/{doc}` | 删除文档 |
| POST | `/api/v1/chat` | 智能问答（支持 SSE 流式） |
| GET | `/api/v1/conversations` | 对话历史列表 |
| POST | `/api/v1/conversations` | 创建对话 |
| GET | `/api/v1/conversations/{id}` | 对话详情 |
| PUT | `/api/v1/conversations/{id}` | 追加/更新消息 |
| DELETE | `/api/v1/conversations/{id}` | 删除对话 |

完整 API 文档启动后端后访问：http://localhost:8000/docs

---

## 项目结构

```
project_end/
├── docmind/                        # Python 后端
│   ├── app/
│   │   ├── main.py                 # FastAPI 入口
│   │   ├── config.py               # 全局配置
│   │   ├── api/
│   │   │   ├── chat.py             # RAG 问答接口
│   │   │   ├── knowledge.py        # 知识库+文档 CRUD
│   │   │   ├── conversation.py     # 对话历史 CRUD
│   │   │   └── deps.py             # API Key 鉴权
│   │   ├── services/
│   │   │   ├── llm_service.py      # 大模型调用
│   │   │   ├── qdrant_service.py   # Qdrant 操作封装
│   │   │   ├── chunk_service.py    # 文档分块+向量化
│   │   │   └── conversation_service.py  # 对话历史存储
│   │   └── models/schemas.py       # 数据模型
│   ├── requirements.txt
│   ├── .env.example
│   ├── start.bat / start.sh
│   └── README.md
│
└── project_fronted_vue/            # Vue 3 前端
    └── src/
        ├── views/                  # 页面（概览/知识库/设置）
        ├── components/             # 组件（聊天面板/文档列表/来源卡片）
        ├── stores/                 # Pinia 全局状态
        ├── router/                 # 路由配置
        └── styles/                 # 全局样式
```

---

## 许可证

本项目仅供学习和个人使用。

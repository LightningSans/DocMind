# DocMind — 企业文档智能问答引擎

基于 RAG（检索增强生成）技术的企业文档智能问答 API 服务，支持多知识库隔离、文档上传即问、流式输出。

## 技术栈

- **Web 框架**: FastAPI（异步、高性能）
- **向量数据库**: Qdrant（Docker 部署）
- **大模型**: DeepSeek（OpenAI 兼容接口）
- **文档处理**: pypdf + 文本分块
- **Embedding**: text-embedding-v4 / text-embedding-ada-002（OpenAI 兼容接口）

---

## 📥 从 Gitee 克隆后的第一步

本项目将敏感和运行时文件排除在版本控制之外（参见根目录 `.gitignore`），
**克隆后需要手动补全以下内容才能运行**：

### ❌ 已从仓库中排除的文件/目录

| 排除项 | 原因 | 需要手动 |
|--------|------|----------|
| `.env` | 包含 API Key 等敏感凭证 | ✅ 复制 `.env.example` 并填写真实值 |
| `.venv/` | Python 虚拟环境（平台相关） | ✅ 重新创建并安装依赖 |
| `uploads/` | 用户上传的文档（运行时数据） | ✅ 自动创建（也可手动新建空目录） |
| `conversations/` | 用户对话历史（运行时数据） | ✅ 自动创建（也可手动新建空目录） |
| `__pycache__/` | Python 字节码缓存 | ❌ 无操作，运行时自动生成 |

---

## 快速开始

### 1. 配置环境变量（必须）

```bash
cd docmind
cp .env.example .env
```

然后编辑 `.env` 文件，填写真实的 API Key：

```ini
# ---------- API 鉴权 ----------
# 用于访问 API 的密钥，请修改为随机字符串
DOCMIND_API_KEY=你的API密钥

# ---------- Embedding 模型 ----------
EMBEDDING_API_KEY=你的阿里云DashScope或其他兼容API Key
EMBEDDING_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
EMBEDDING_MODEL=text-embedding-v4
EMBEDDING_DIMENSION=1024

# ---------- DeepSeek LLM ----------
LLM_API_KEY=你的DeepSeek API Key
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
LLM_MAX_TOKENS=4096
LLM_TEMPERATURE=0.3
```

> **注意：** `.env` 文件包含敏感信息，已被 `.gitignore` 排除，
> 修改后不会意外提交到 Git 仓库。

### 2. 安装依赖

```bash
# 创建虚拟环境（推荐）
python -m venv .venv

# Windows
.venv\Scripts\pip install -r requirements.txt

# macOS / Linux
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. 确保 Qdrant 已运行

```bash
# 如果尚未启动 Qdrant 向量数据库（需要安装 Docker）：
docker run -d -p 6333:6333 -p 6334:6334 qdrant/qdrant
```

### 4. 启动服务

```bash
# 使用一键启动脚本（推荐）
# Windows:
start.bat

# macOS / Linux:
bash start.sh

# 或手动启动：
# Windows:
.venv\Scripts\uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# macOS / Linux:
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. 访问文档

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- 健康检查: http://localhost:8000/health

---

## 常见问题

### Q: 启动时提示 ".env 文件不存在"？

A: 执行 `cp .env.example .env`，然后编辑 `.env` 填入你的 API Key。

### Q: 启动时提示 Qdrant 连接失败？

A: 确保 Docker 已安装并运行了 Qdrant：
```bash
docker run -d -p 6333:6333 -p 6334:6334 qdrant/qdrant
```

### Q: `uploads/` 或 `conversations/` 目录不存在？

A: 服务启动时会自动创建这两个目录，也可以手动创建：
```bash
mkdir uploads conversations
```

---

## API 概览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/knowledge-bases` | 获取知识库列表 |
| POST | `/api/v1/knowledge-bases` | 创建知识库 |
| GET | `/api/v1/knowledge-bases/{id}` | 获取知识库详情 |
| PUT | `/api/v1/knowledge-bases/{id}` | 更新知识库 |
| DELETE | `/api/v1/knowledge-bases/{id}` | 删除知识库 |
| POST | `/api/v1/knowledge-bases/{id}/documents` | 上传文档 |
| GET | `/api/v1/knowledge-bases/{id}/documents` | 获取文档列表 |
| DELETE | `/api/v1/knowledge-bases/{id}/documents/{doc_id}` | 删除文档 |
| POST | `/api/v1/chat` | 问答（支持 SSE 流式） |

### 问答接口示例

```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "X-API-Key: 你的DOCMIND_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "knowledge_base_id": "your-kb-id",
    "question": "公司考勤制度是怎么规定的？",
    "stream": true
  }'
```

## 项目结构

```
docmind/
├── app/
│   ├── main.py                # FastAPI 入口
│   ├── config.py              # 配置管理
│   ├── api/
│   │   ├── knowledge.py       # 知识库 CRUD
│   │   ├── chat.py            # 问答流式接口
│   │   ├── conversation.py    # 对话历史管理
│   │   └── deps.py            # API Key 校验
│   ├── services/
│   │   ├── qdrant_service.py  # Qdrant 操作封装
│   │   ├── llm_service.py     # 大模型调用
│   │   ├── chunk_service.py   # 文档分块与向量化
│   │   └── conversation_service.py # 对话历史文件存储
│   └── models/
│       └── schemas.py         # Pydantic 模型
├── .env.example               # 环境变量模板（安全，可提交）
├── .env                       # 环境变量（已排除，请自行创建）
├── uploads/                   # 上传文件目录（已排除）
├── conversations/             # 对话历史目录（已排除）
├── requirements.txt
├── start.bat                  # Windows 启动脚本
├── start.sh                   # Linux/macOS 启动脚本
└── README.md
```

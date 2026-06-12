"""
DocMind 应用包

├── main.py          # FastAPI 应用入口（启动点）
├── config.py        # 全局配置管理（.env + 环境变量）
├── api/             # API 路由层（处理 HTTP 请求与响应）
│   ├── knowledge.py # 知识库 + 文档 CRUD 接口
│   ├── chat.py      # RAG 问答接口（流式+非流式）
│   └── deps.py      # API Key 鉴权中间件
├── services/        # 业务逻辑层（核心处理）
│   ├── chunk_service.py   # 文档提取 → 分块 → 向量化
│   ├── llm_service.py     # 大模型调用（流式+非流式）
│   └── qdrant_service.py  # Qdrant 向量数据库操作
└── models/          # 数据模型层
    └── schemas.py   # Pydantic 请求/响应模型

DocMind 是基于 RAG 技术的企业文档智能问答引擎。
支持多知识库隔离、文档上传即问、流式 SSE 输出。
"""

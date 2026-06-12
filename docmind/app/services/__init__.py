"""
业务逻辑层 — 核心处理服务

包含三个模块：
  chunk_service.py    文档提取 → 文本分块 → Embedding 向量化
  llm_service.py      大模型调用（封装 OpenAI 兼容接口）
  qdrant_service.py   Qdrant 向量数据库 CRUD + 相似度搜索

每个 service 函数被 api/ 层的路由调用，形成完整请求链路。
"""

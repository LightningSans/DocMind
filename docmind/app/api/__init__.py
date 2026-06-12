"""
API 路由层 — HTTP 接口定义

包含三个模块：
  knowledge.py  知识库管理 + 文档管理 CRUD
  chat.py       RAG 问答（流式 SSE + 非流式 JSON）
  deps.py       API Key 鉴权依赖注入

所有路由通过 app/main.py 中的 app.include_router() 注册。
"""

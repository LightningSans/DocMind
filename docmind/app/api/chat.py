"""
问答 API 路由 — RAG 检索增强生成接口

本模块是 DocMind 的核心功能，实现了完整的 RAG 问答流程：

  用户提问 → 向量化问题 → Qdrant 相似度搜索 →
  拼接上下文 → LLM 生成答案 → 流式/非流式返回

支持两种响应模式：
  1. 流式输出（SSE）：通过 Server-Sent Events 逐字返回答案，
     前端可实现打字机效果。推荐方式，用户体验更佳。
  2. 非流式输出：等待 LLM 完整生成后一次性返回 JSON。

所有问答都会附带引用来源信息，包含匹配到的文档片段
和相似度分数，提升回答的可信度。

路由前缀：/api/v1/chat
"""

import json

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.api.deps import verify_api_key
from app.models.schemas import ChatRequest, ChatResponse, ReferenceSegment
from app.services.llm_service import chat_non_stream, chat_stream
from app.services.qdrant_service import get_knowledge_base, search_similar
from app.services.chunk_service import get_embedding

router = APIRouter(prefix="/api/v1/chat", tags=["文档问答"])


@router.post("")
async def chat(
    body: ChatRequest,
    _=Depends(verify_api_key),
):
    """向知识库提问，支持流式或非流式输出

    完整 RAG 流程：
      第1步：检查知识库是否存在
      第2步：将用户问题向量化（调用 Embedding API）
      第3步：在 Qdrant 中搜索相似文本片段
      第4步：如果没有找到相关片段，返回提示信息
      第5步：将检索到的片段 + 问题拼成 Prompt
      第6步：调用 LLM 生成答案（流式或非流式）

    请求体（JSON）：
        knowledge_base_id: 知识库 ID（必填）
        question: 用户问题（必填，1-10000字符）
        top_k: 检索片段数量（可选，默认5，范围1-20）
        stream: 是否流式输出（可选，默认true）

    流式响应（SSE 格式）：
        data: {"type":"references","references":[...]}
        data: {"type":"text","content":"逐字输出..."}
        data: [DONE]

    非流式响应（JSON）：
        {
          "answer": "完整答案",
          "references": [{...}]
        }
    """
    # =============================================
    # 第1步：验证知识库是否存在
    # =============================================
    kb = await get_knowledge_base(body.knowledge_base_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    # =============================================
    # 第2步：将用户问题向量化
    # 使用与文档相同的 Embedding 模型，确保
    # 向量空间一致，余弦相似度计算才能有效
    # =============================================
    try:
        query_vector = await get_embedding(body.question)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"向量化失败: {str(e)}")

    # =============================================
    # 第3步：在 Qdrant 中检索相似文本片段
    # 使用 Cosine 相似度检索 top_k 个最相关片段
    # =============================================
    try:
        retrieved = await search_similar(
            body.knowledge_base_id,
            query_vector,
            top_k=body.top_k,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检索失败: {str(e)}")

    # =============================================
    # 第4步：未找到相关片段时的兜底处理
    # =============================================
    if not retrieved:
        return ChatResponse(
            answer="未在文档中找到相关信息，请尝试调整问题或上传更多文档。",
            references=[],
        )

    # =============================================
    # 第5步：准备上下文和引用信息
    # =============================================
    # 提取文本内容作为 LLM 上下文
    context_chunks = [r["text"] for r in retrieved]
    # 构建引用来源信息（含文件名和相似度分数）
    references = [
        ReferenceSegment(
            document_id=r["document_id"],
            document_name=r.get("filename") or r["document_id"][:8],
            content=r["text"][:200],
            score=r["score"],
        )
        for r in retrieved
    ]

    # =============================================
    # 第6步：根据 stream 参数选择响应模式
    # =============================================
    if body.stream:
        # ---- 流式模式（SSE） ----
        async def generate():
            """生成 SSE 事件流

            先发送引用来源信息，让前端可以立即展示
            引用了哪些文档片段，然后再逐字输出答案。
            """
            # 先发送引用信息事件
            refs_payload = {
                "type": "references",
                "references": [
                    {
                        "document_id": r.document_id,
                        "document_name": r.document_name,
                        "content": r.content,
                        "score": r.score,
                    }
                    for r in references
                ],
            }
            yield f"data: {json.dumps(refs_payload)}\n\n"

            # 流式输出答案（逐个 token）
            async for token in chat_stream(body.question, context_chunks):
                yield token

            # 发送结束标记
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",       # 禁止缓存
                "Connection": "keep-alive",        # 保持长连接
                "X-Accel-Buffering": "no",         # 禁用 Nginx 缓冲
            },
        )
    else:
        # ---- 非流式模式（JSON） ----
        answer = await chat_non_stream(body.question, context_chunks)
        return ChatResponse(answer=answer, references=references)

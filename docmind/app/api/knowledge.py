"""
知识库管理 API 路由 — 知识库 + 文档的 CRUD 接口

本模块提供知识库和文档的完整增删改查功能，包括：

知识库管理（路由前缀：/api/v1/knowledge-bases）：
  - GET    /                             获取所有知识库列表
  - POST   /                             创建新知识库
  - GET    /{kb_id}                      获取知识库详情
  - PUT    /{kb_id}                      更新知识库
  - DELETE /{kb_id}                      删除知识库

文档管理（路由前缀：/api/v1/knowledge-bases）：
  - POST   /{kb_id}/documents            上传文档（自动分块+向量化）
  - GET    /{kb_id}/documents            获取文档列表
  - DELETE /{kb_id}/documents/{doc_id}   删除文档

所有接口都需要在 Header 中携带 API Key 进行鉴权。
"""

import os
import uuid
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.api.deps import verify_api_key
from app.models.schemas import (
    DocumentList,
    DocumentOut,
    KnowledgeBaseCreate,
    KnowledgeBaseList,
    KnowledgeBaseOut,
    KnowledgeBaseUpdate,
    MessageOut,
)
from app.services.chunk_service import process_document
from app.services.qdrant_service import (
    create_knowledge_base,
    delete_document_chunks,
    delete_knowledge_base,
    get_kb_documents,
    get_knowledge_base,
    insert_chunks,
    list_knowledge_bases,
    update_knowledge_base,
)
from app.config import settings

# 创建路由实例，所有接口以 /api/v1/knowledge-bases 为前缀
router = APIRouter(prefix="/api/v1/knowledge-bases", tags=["知识库管理"])


# =============================================
# 知识库 CRUD
# =============================================

@router.get("", response_model=KnowledgeBaseList)
async def list_kbs(_=Depends(verify_api_key)):
    """获取所有知识库列表

    返回所有知识库的基本信息，包括每个知识库的
    文档数量和文本块数量的统计。
    """
    items = await list_knowledge_bases()
    # 将原始字典列表转 Pydantic 模型以验证和规范化输出
    full_items = []
    for kb in items:
        full_items.append(KnowledgeBaseOut(**kb))
    return KnowledgeBaseList(total=len(full_items), items=full_items)


@router.post("", response_model=KnowledgeBaseOut, status_code=status.HTTP_201_CREATED)
async def create_kb(body: KnowledgeBaseCreate, _=Depends(verify_api_key)):
    """创建新的知识库

    知识库是文档的容器，上传文档前必须先创建知识库。
    创建时自动在 Qdrant 中创建对应的向量集合。

    请求体（JSON）：
        name: 知识库名称（必填，1-200字符）
        description: 描述（可选，最多1000字符）
    """
    kb = await create_knowledge_base(body.name, body.description)
    return KnowledgeBaseOut(**kb)


@router.get("/{kb_id}", response_model=KnowledgeBaseOut)
async def get_kb(kb_id: str, _=Depends(verify_api_key)):
    """获取指定知识库的详情

    包括文档数量、文本块数量等统计信息。

    参数：
        kb_id: 知识库 UUID（创建时返回的 id）
    """
    kb = await get_knowledge_base(kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    return KnowledgeBaseOut(**kb)


@router.put("/{kb_id}", response_model=KnowledgeBaseOut)
async def update_kb(kb_id: str, body: KnowledgeBaseUpdate, _=Depends(verify_api_key)):
    """更新知识库信息

    可修改名称和/或描述，只提供需要修改的字段即可。

    请求体（JSON）：
        name: 新名称（可选）
        description: 新描述（可选）
    """
    ok = await update_knowledge_base(kb_id, body.name, body.description)
    if not ok:
        raise HTTPException(status_code=404, detail="知识库不存在")
    kb = await get_knowledge_base(kb_id)
    return KnowledgeBaseOut(**kb)


@router.delete("/{kb_id}", response_model=MessageOut)
async def delete_kb(kb_id: str, _=Depends(verify_api_key)):
    """删除知识库及其所有数据

    警告：此操作不可逆！会同时删除：
      - 知识库的所有文档向量数据
      - 知识库的元数据记录

    参数：
        kb_id: 要删除的知识库 UUID
    """
    ok = await delete_knowledge_base(kb_id)
    if not ok:
        raise HTTPException(status_code=404, detail="知识库不存在")
    return MessageOut(message="知识库已删除")


# =============================================
# 文档管理
# =============================================

# 支持上传的文件类型
SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf"}


@router.post("/{kb_id}/documents", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    kb_id: str,
    file: UploadFile = File(...),
    _=Depends(verify_api_key),
):
    """上传文档到知识库（自动处理）

    上传后的自动处理流程：
      1. 检查文件类型（仅支持 .txt / .md / .pdf）
      2. 检查文件大小（默认不超过 20MB）
      3. 提取文本内容（按文件类型使用不同解析器）
      4. 将文本切分为带重叠的小块
      5. 调用 Embedding API 将每个块转为向量
      6. 将向量+文本存入 Qdrant

    参数：
        kb_id: 目标知识库 UUID
        file: 上传的文件（支持 .txt/.md/.pdf）

    返回：
        处理结果，包含分块数量和文件名
    """
    # 1. 检查知识库是否存在
    kb = await get_knowledge_base(kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    # 2. 校验文件类型（白名单机制）
    file_ext = os.path.splitext(file.filename or "")[1].lower()
    if file_ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {file_ext}，支持: {', '.join(SUPPORTED_EXTENSIONS)}",
        )

    # 3. 读取文件内容并检查大小
    content = await file.read()
    file_size = len(content)
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if file_size > max_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"文件大小超过限制 ({settings.MAX_UPLOAD_SIZE_MB}MB)",
        )

    # 4. 处理文档（提取文本 → 分块 → 向量化）
    try:
        chunks = await process_document(kb_id, file.filename or "unknown", content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文档处理失败: {str(e)}")

    # 5. 如果文档为空（无法提取文本），返回提示信息
    if not chunks:
        return MessageOut(message="文档为空或无法提取文本", detail=file.filename)

    # 6. 将处理后的向量块插入到 Qdrant
    await insert_chunks(kb_id, chunks)

    return MessageOut(
        message=f"文档处理完成，共 {len(chunks)} 个文本块",
        detail=file.filename,
    )


@router.get("/{kb_id}/documents", response_model=DocumentList)
async def list_documents(kb_id: str, _=Depends(verify_api_key)):
    """获取知识库中的文档列表

    返回每个文档的 ID、文件名、文件类型、文本块数量。
    文档列表是从 Qdrant 向量数据中按 document_id 去重统计得出。

    参数：
        kb_id: 知识库 UUID
    """
    kb = await get_knowledge_base(kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    docs = await get_kb_documents(kb_id)
    items = [
        DocumentOut(
            id=d.get("document_id", d.get("id", "")),
            filename=d.get("filename", ""),
            knowledge_base_id=kb_id,
            file_size=0,
            file_type=os.path.splitext(d.get("filename", ""))[1].lower(),
            chunk_count=d.get("chunk_count", 0),
        )
        for d in docs
    ]
    return DocumentList(total=len(items), items=items)


@router.delete("/{kb_id}/documents/{document_id}", response_model=MessageOut)
async def delete_document(kb_id: str, document_id: str, _=Depends(verify_api_key)):
    """删除文档及其所有向量块

    从 Qdrant 中删除该文档对应的所有文本块向量，
    并更新知识库的文档数和块数统计。

    参数：
        kb_id: 知识库 UUID
        document_id: 文档 ID（上传时自动生成的 UUID）
    """
    kb = await get_knowledge_base(kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    await delete_document_chunks(kb_id, document_id)
    return MessageOut(message="文档已删除")

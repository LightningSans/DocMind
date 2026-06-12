"""
Qdrant 向量数据库操作封装（异步版）

本模块封装了所有与 Qdrant 向量数据库的交互操作，包括：
  - 知识库 CRUD（增删改查）
  - 知识库元数据管理
  - 文档向量块的插入与删除
  - 向量相似度搜索（RAG 检索核心）
  - 文档列表统计

数据模型说明：
  在 Qdrant 中维护两类 Collection（集合）：
  1. _kb_meta（元数据集合）：
     存储所有知识库的基本信息（名称、描述、文档数等）
     虽然是向量库，但元数据用 Dummy Vector，只利用其 Payload 能力
  2. kb_{kb_id}（向量集合）：
     每个知识库对应一个独立集合，存储文档块的向量+文本
     集合名 = "kb_" + 知识库 UUID（连字符替换为下划线）

  这种设计实现了多知识库之间的数据隔离，每个知识库的
  文档向量互不干扰，搜索时只在目标知识库的集合中查询。
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from qdrant_client import AsyncQdrantClient, models

from app.config import settings

# =============================================
# 常量定义
# =============================================
KB_META_COLLECTION = "_kb_meta"                        # 知识库元数据集合名
DEFAULT_VECTOR = [0.0] * settings.EMBEDDING_DIMENSION    # 元数据使用的占位向量

# Qdrant 连接超时（秒），连接不上快速失败，不要死等
QDRANT_TIMEOUT = 10


# 全局单例异步 Qdrant 客户端
_client_instance: AsyncQdrantClient | None = None


async def _get_client() -> AsyncQdrantClient:
    """
    获取或创建 Qdrant 异步客户端（全局单例）

    复用 HTTP 连接池，避免每个请求都重新建连。
    单例模式，所有 API 调用共享一个连接。
    """
    global _client_instance
    if _client_instance is None:
        _client_instance = AsyncQdrantClient(url=settings.qdrant_url, timeout=QDRANT_TIMEOUT)
    return _client_instance


# =============================================
# 集合管理
# =============================================

async def _ensure_kb_meta_collection():
    """
    确保知识库元数据集合存在

    如果 _kb_meta 集合不存在，则创建一个。
    该集合使用占位向量（全零），因为元数据查询
    只依赖 payload 过滤，不需要向量搜索。

    此函数在每次操作前都会被调用（幂等设计）。
    """
    client = await _get_client()
    collections = await client.get_collections()
    names = {c.name for c in collections.collections}
    if KB_META_COLLECTION not in names:
        await client.create_collection(
            collection_name=KB_META_COLLECTION,
            vectors_config=models.VectorParams(
                size=settings.EMBEDDING_DIMENSION,
                distance=models.Distance.COSINE,  # 使用余弦相似度
            ),
        )


def _kb_collection_name(kb_id: str) -> str:
    """
    根据知识库 ID 生成对应的 Qdrant 集合名称

    规则：将 UUID 中的连字符替换为下划线
    例如：kb_550e8400_e29b_41d4_a716_446655440000

    参数：
        kb_id: 知识库 UUID

    返回：
        Qdrant 集合名称
    """
    return f"kb_{kb_id.replace('-', '_')}"


async def _ensure_kb_collection(kb_id: str):
    """
    确保指定知识库的向量集合存在

    集合的向量配置（维度、距离算法）从 settings 读取，
    与 Embedding 模型配置保持一致。

    参数：
        kb_id: 知识库 UUID
    """
    client = await _get_client()
    name = _kb_collection_name(kb_id)
    collections = await client.get_collections()
    names = {c.name for c in collections.collections}
    if name not in names:
        await client.create_collection(
            collection_name=name,
            vectors_config=models.VectorParams(
                size=settings.EMBEDDING_DIMENSION,
                distance=models.Distance.COSINE,
            ),
        )


# =============================================
# 知识库 CRUD
# =============================================

async def create_knowledge_base(name: str, description: str = "") -> Dict[str, Any]:
    """
    创建新的知识库

    操作步骤：
      1. 确保元数据集合存在
      2. 生成唯一 UUID 作为知识库 ID
      3. 在 _kb_meta 集合中插入一条记录
      4. 创建知识库专属的向量集合（kb_{id}）

    参数：
        name: 知识库名称
        description: 知识库描述（可选）

    返回：
        包含新知识库完整信息的字典
    """
    await _ensure_kb_meta_collection()
    client = await _get_client()
    kb_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    await client.upsert(
        collection_name=KB_META_COLLECTION,
        points=[
            models.PointStruct(
                id=kb_id,
                vector=DEFAULT_VECTOR,  # 元数据不需要真实向量
                payload={
                    "name": name,
                    "description": description,
                    "document_count": 0,
                    "chunk_count": 0,
                    "created_at": now,
                },
            )
        ],
    )
    # 同时创建该知识库专属的向量集合
    await _ensure_kb_collection(kb_id)
    return {
        "id": kb_id,
        "name": name,
        "description": description,
        "document_count": 0,
        "chunk_count": 0,
        "created_at": now,
    }


async def list_knowledge_bases() -> List[Dict[str, Any]]:
    """
    获取所有知识库列表

    使用 scroll 扫描 _kb_meta 集合中的所有记录，
    返回包含完整信息（含文档统计）的列表。

    返回：
        知识库字典列表，每个字典包含 id/name/description/
        document_count/chunk_count/created_at
    """
    await _ensure_kb_meta_collection()
    client = await _get_client()
    points, _ = await client.scroll(
        collection_name=KB_META_COLLECTION,
        limit=1000,          # 最多返回 1000 条
        with_payload=True,   # 需要 payload 中的元数据
        with_vectors=False,  # 不需要向量（占用带宽）
    )
    results = []
    for p in points:
        results.append({
            "id": p.id,
            "name": p.payload.get("name", ""),
            "description": p.payload.get("description", ""),
            "document_count": p.payload.get("document_count", 0),
            "chunk_count": p.payload.get("chunk_count", 0),
            "created_at": p.payload.get("created_at"),
        })
    return results


async def get_knowledge_base(kb_id: str) -> Optional[Dict[str, Any]]:
    """
    获取单个知识库详情

    参数：
        kb_id: 知识库 UUID

    返回：
        知识库信息字典，如果不存在则返回 None
    """
    client = await _get_client()
    points = await client.retrieve(
        collection_name=KB_META_COLLECTION,
        ids=[kb_id],
        with_payload=True,
        with_vectors=False,
    )
    if not points:
        return None
    p = points[0]
    return {
        "id": p.id,
        "name": p.payload.get("name", ""),
        "description": p.payload.get("description", ""),
        "document_count": p.payload.get("document_count", 0),
        "chunk_count": p.payload.get("chunk_count", 0),
        "created_at": p.payload.get("created_at"),
    }


async def update_knowledge_base(kb_id: str, name: Optional[str] = None, description: Optional[str] = None) -> bool:
    """
    更新知识库信息（名称/描述）

    只更新提供的字段，未提供的字段保持不变。
    先检查知识库是否存在，不存在返回 False。

    参数：
        kb_id: 要更新的知识库 UUID
        name: 新名称（None 表示不更新）
        description: 新描述（None 表示不更新）

    返回：
        True 更新成功，False 知识库不存在
    """
    kb = await get_knowledge_base(kb_id)
    if not kb:
        return False
    client = await _get_client()
    payload = {}
    if name is not None:
        payload["name"] = name
    if description is not None:
        payload["description"] = description
    if payload:
        await client.set_payload(
            collection_name=KB_META_COLLECTION,
            payload=payload,
            points=[kb_id],
        )
    return True


async def delete_knowledge_base(kb_id: str) -> bool:
    """
    删除知识库及其所有文档向量

    操作步骤：
      1. 检查知识库是否存在
      2. 删除知识库对应的向量集合（kb_{id}），清空所有文档块
      3. 从 _kb_meta 集合中删除元数据记录

    注意：此操作不可逆！所有文档数据会永久丢失。

    参数：
        kb_id: 要删除的知识库 UUID

    返回：
        True 删除成功，False 知识库不存在
    """
    kb = await get_knowledge_base(kb_id)
    if not kb:
        return False
    client = await _get_client()
    # 1. 删除向量集合（所有文档块）
    coll_name = _kb_collection_name(kb_id)
    try:
        await client.delete_collection(collection_name=coll_name)
    except Exception:
        pass
    # 2. 删除元数据记录
    await client.delete(
        collection_name=KB_META_COLLECTION,
        points_selector=models.PointIdsList(points=[kb_id]),
    )
    return True


async def _update_kb_counts(kb_id: str, delta_chunks: int = 0, delta_docs: int = 0):
    """
    更新知识库的文档数和文本块数统计（增量更新）

    不再全量扫描，而是通过传人的增/减量直接更新计数器。
    相比之前每次 scroll 全量统计，速度快了一个数量级。

    参数：
        kb_id: 知识库 UUID
        delta_chunks: 文本块数量的变化（正=增加，负=减少）
        delta_docs: 文档数量的变化（正=增加，负=减少）
    """
    if delta_chunks == 0 and delta_docs == 0:
        return
    client = await _get_client()
    kb = await get_knowledge_base(kb_id)
    if not kb:
        return
    try:
        new_chunk_count = max(0, (kb.get("chunk_count") or 0) + delta_chunks)
        new_doc_count = max(0, (kb.get("document_count") or 0) + delta_docs)
        await client.set_payload(
            collection_name=KB_META_COLLECTION,
            payload={
                "document_count": new_doc_count,
                "chunk_count": new_chunk_count,
            },
            points=[kb_id],
        )
    except Exception:
        pass


# =============================================
# 文档块操作
# =============================================

async def insert_chunks(kb_id: str, chunks: List[Tuple[str, str, str, str, List[float]]]):
    """
    将文档块插入到知识库的向量集合中

    chunks 参数结构：
      (chunk_id, document_id, filename, text, vector)
      由 chunk_service.process_document() 生成

    插入步骤：
      1. 确保知识库的向量集合存在
      2. 逐条构建 PointStruct（含向量 + 文本 + 文档ID + 文件名）
      3. 每 100 条一批批量插入（避免单次请求过大）
      4. 更新知识库的文档数和块数统计

    参数：
        kb_id: 目标知识库 UUID
        chunks: 文档块元组列表
    """
    await _ensure_kb_collection(kb_id)
    client = await _get_client()
    coll_name = _kb_collection_name(kb_id)
    points = []
    for chunk_id, doc_id, fname, text, vector in chunks:
        points.append(
            models.PointStruct(
                id=chunk_id,   # 文本块唯一 ID
                vector=vector, # 文本向量（用于相似度搜索）
                payload={
                    "document_id": doc_id,  # 所属文档 ID
                    "filename": fname,      # 原始文件名（用于来源显示）
                    "text": text,           # 文本内容
                },
            )
        )
    # 分批插入，每批 100 条
    batch_size = 100
    for i in range(0, len(points), batch_size):
        await client.upsert(
            collection_name=coll_name,
            points=points[i : i + batch_size],
        )
    # 更新知识库统计
    await _update_kb_counts(kb_id, delta_chunks=len(chunks), delta_docs=1)


async def delete_document_chunks(kb_id: str, document_id: str):
    """
    删除指定文档的所有向量块

    使用 Qdrant 的 Filter 功能，筛选出所有
    document_id 匹配的 points 并删除。

    参数：
        kb_id: 知识库 UUID
        document_id: 要删除的文档 ID
    """
    client = await _get_client()
    coll_name = _kb_collection_name(kb_id)
    # 先统计要删除的文本块数量，用于更新 chunk_count
    try:
        count_result = await client.count(
            collection_name=coll_name,
            count_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="document_id",
                        match=models.MatchValue(value=document_id),
                    )
                ]
            ),
            exact=True,
        )
        chunk_count = count_result.count
    except Exception:
        chunk_count = 0  # 如果 count 失败，至少文档计数还是对的
    # 使用 Filter 按 document_id 匹配删除
    await client.delete(
        collection_name=coll_name,
        points_selector=models.FilterSelector(
            filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="document_id",
                        match=models.MatchValue(value=document_id),
                    )
                ]
            )
        ),
    )
    # 更新知识库统计（同时减少文档数和块数）
    await _update_kb_counts(kb_id, delta_docs=-1, delta_chunks=-chunk_count)


# =============================================
# 向量搜索（RAG 核心）
# =============================================

async def search_similar(kb_id: str, query_vector: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
    """
    在知识库中搜索与查询向量最相似的文本片段

    这是 RAG（检索增强生成）的核心步骤：
      1. 用户的问题被 Embedding 模型转为 query_vector
      2. 在 Qdrant 中执行 cosine 相似度搜索
      3. 返回最相似的 top_k 个文本片段
      4. 这些片段作为上下文传递给 LLM 生成答案

    参数：
        kb_id: 知识库 UUID
        query_vector: 问题的向量表示
        top_k: 返回的最相似片段数

    返回：
        搜索结果列表，每个结果包含：
          - chunk_id: 文本块 ID
          - document_id: 所属文档 ID
          - filename: 原始文件名
          - text: 文本内容
          - score: 相似度分数（0~1，越高越相似）
    """
    client = await _get_client()
    coll_name = _kb_collection_name(kb_id)
    hits = await client.search(
        collection_name=coll_name,
        query_vector=query_vector,  # 查询向量
        limit=top_k,                # 返回 top K 条
        with_payload=True,          # 同时返回文本内容
    )
    results = []
    for hit in hits:
        results.append({
            "chunk_id": hit.id,
            "document_id": hit.payload.get("document_id", ""),
            "filename": hit.payload.get("filename", ""),
            "text": hit.payload.get("text", ""),
            "score": hit.score,  # Qdrant 自动计算的余弦相似度
        })
    return results


# =============================================
# 文档列表
# =============================================

async def get_kb_documents(kb_id: str) -> List[Dict[str, Any]]:
    """
    获取知识库中的文档列表

    扫描知识库的向量集合，按 document_id 去重，
    统计每个文档包含的文本块数。

    返回的每个文档信息包含：
      - id: 文档 ID
      - document_id: 同 id
      - filename: 原始文件名
      - chunk_count: 该文档的文本块数量

    参数：
        kb_id: 知识库 UUID

    返回：
        文档信息字典列表
    """
    client = await _get_client()
    coll_name = _kb_collection_name(kb_id)
    points, _ = await client.scroll(
        collection_name=coll_name,
        limit=10000,
        with_payload=["document_id", "filename"],
        with_vectors=False,
    )
    # 按 document_id 去重并统计块数
    doc_map: Dict[str, Dict] = {}
    for p in points:
        doc_id = p.payload.get("document_id", "")
        if doc_id and doc_id not in doc_map:
            doc_map[doc_id] = {
                "id": doc_id,
                "document_id": doc_id,
                "filename": p.payload.get("filename", ""),
                "chunk_count": 0,
            }
        if doc_id in doc_map:
            doc_map[doc_id]["chunk_count"] += 1
    return list(doc_map.values())

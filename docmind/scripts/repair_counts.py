"""
知识库计数器修复脚本
=====================
用法：在项目根目录（docmind 文件夹）下执行：
    .venv\Scripts\python scripts\repair_counts.py

作用：扫描 Qdrant 中每个知识库的真实文档数和文本块数，
      更新 _kb_meta 元数据，让显示的数字跟实际一致。
"""

import sys
import os

# 把项目根目录加入 sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qdrant_client import AsyncQdrantClient, models
from app.config import settings
import asyncio


async def repair():
    print(f"正在连接 Qdrant: {settings.qdrant_url}")
    client = AsyncQdrantClient(url=settings.qdrant_url, timeout=10)

    # 1. 获取所有知识库
    collections = await client.get_collections()
    names = {c.name for c in collections.collections}

    if "_kb_meta" not in names:
        print("没有找到知识库元数据集合")
        return

    points, _ = await client.scroll(
        collection_name="_kb_meta",
        limit=1000,
        with_payload=True,
        with_vectors=False,
    )

    print(f"找到 {len(points)} 个知识库\n")

    for p in points:
        kb_id = p.id
        kb_name = p.payload.get("name", "未命名")
        coll_name = f"kb_{kb_id.replace('-', '_')}"

        if coll_name not in names:
            print(f"[{kb_name}] 向量集合不存在，跳过")
            continue

        # 2. 扫描该知识库的所有数据
        doc_points, _ = await client.scroll(
            collection_name=coll_name,
            limit=10000,
            with_payload=["document_id", "filename"],
            with_vectors=False,
        )

        total_chunks = len(doc_points)
        # 按 document_id 去重统计文档数
        doc_ids = set()
        for dp in doc_points:
            doc_id = dp.payload.get("document_id", "")
            if doc_id:
                doc_ids.add(doc_id)

        old_chunks = p.payload.get("chunk_count", 0)
        old_docs = p.payload.get("document_count", 0)

        if total_chunks != old_chunks or len(doc_ids) != old_docs:
            print(f"[{kb_name}]")
            print(f"  旧值: document_count={old_docs}, chunk_count={old_chunks}")
            print(f"  实际: document_count={len(doc_ids)}, chunk_count={total_chunks}")
            await client.set_payload(
                collection_name="_kb_meta",
                payload={
                    "document_count": len(doc_ids),
                    "chunk_count": total_chunks,
                },
                points=[kb_id],
            )
            print(f"  ✅ 已修复")
        else:
            print(f"[{kb_name}] ✅ 计数正确（{total_chunks} chunks / {len(doc_ids)} docs）")

        print()

    await client.close()
    print("全部修复完成！")


if __name__ == "__main__":
    asyncio.run(repair())

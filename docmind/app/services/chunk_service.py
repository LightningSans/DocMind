"""
文档分块与向量化服务 — 文档处理流水线

本模块负责将上传的文档经过以下完整流水线处理：
  原始文件 → 提取文本 → 切分文本块 → 向量化 → 返回结构化数据

流程说明：
  1. extract_text()：根据文件类型（.txt/.md/.pdf）提取纯文本
  2. chunk_text()：将长文本切分为带重叠的短文本块
  3. get_embedding() / get_embeddings_batch()：调用 Embedding API
     将文本转为向量
  4. process_document()：串联以上步骤，一条函数完成全流程

支持的文档格式：
  - .txt：直接 UTF-8 解码
  - .md：去除 Markdown 标记（目前按纯文本处理）
  - .pdf：使用 pypdf 库解析
"""

import os
import tempfile
import uuid
from typing import List, Tuple

from app.config import settings


# =============================================
# 文本分块
# =============================================

def chunk_text(text: str, chunk_size: int = None, overlap: int = None) -> List[str]:
    """
    将长文本切分为带重叠的短文本块

    为什么要重叠？
      避免在句子中间截断导致语义丢失。例如：
      块1："今天天气真好啊我们去公"
      块2："我们去公园散步吧"
      如果没有 overlap，"公园"这个信息就可能在两个块中
      都不完整，影响检索效果。

    参数：
        text: 原始长文本
        chunk_size: 每块的最大字符数（默认 settings.CHUNK_SIZE=512）
        overlap: 相邻块重叠字符数（默认 settings.CHUNK_OVERLAP=64）

    返回：
        文本块列表，如 ["块1内容...", "块2内容...", ...]
    """
    chunk_size = chunk_size or settings.CHUNK_SIZE
    overlap = overlap or settings.CHUNK_OVERLAP
    step = chunk_size - overlap  # 每次前进的步长

    # 如果步长 <= 0，退化为步长=一半块大小（防止死循环）
    if step <= 0:
        step = chunk_size // 2

    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break  # 已到达文本末尾，退出循环
        start += step  # 滑动窗口前进

    return chunks if chunks else [text]  # 如果切分结果为空，至少返回原文


# =============================================
# 文本提取（按文件类型）
# =============================================

def extract_text_from_txt(content: bytes) -> str:
    """
    从 .txt 文件内容中提取文本

    参数：
        content: 文件的二进制内容

    返回：
        解码后的 UTF-8 文本（遇到无法解码的字符用替换符代替）
    """
    return content.decode("utf-8", errors="replace")


def extract_text_from_md(content: bytes) -> str:
    """
    从 .md 文件内容中提取纯文本

    目前直接返回纯文本内容（不做 Markdown 标记剥离），
    后续可升级为使用 markdown 库解析后提取纯文本。

    参数：
        content: 文件的二进制内容

    返回：
        纯文本内容
    """
    return content.decode("utf-8", errors="replace")


def extract_text_from_pdf(file_path: str) -> str:
    """
    从 .pdf 文件中提取文本

    使用 pypdf 库逐页提取。注意：
      - 只能提取文字型 PDF（非扫描件 OCR）
      - 扫描件 PDF 需要 OCR 工具（暂不支持）

    参数：
        file_path: PDF 文件的本地路径

    返回：
        所有页面文本拼接而成的字符串
    """
    try:
        from pypdf import PdfReader

        reader = PdfReader(file_path)
        text_parts = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
        return "\n".join(text_parts)
    except ImportError:
        raise ImportError("pypdf is required for PDF support. Install with: pip install pypdf")


def extract_text(file_path: str, file_type: str, content: bytes) -> str:
    """
    根据文件类型路由到对应的文本提取函数

    参数：
        file_path: 文件路径
        file_type: 文件扩展名（如 .txt, .md, .pdf）
        content: 文件二进制内容

    返回：
        提取出的纯文本内容
    """
    if file_type == ".txt":
        return extract_text_from_txt(content)
    elif file_type == ".md":
        return extract_text_from_md(content)
    elif file_type == ".pdf":
        return extract_text_from_pdf(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_type}")


# =============================================
# 向量化（Embedding）
# =============================================

# 全局单例 Embedding 客户端，复用连接池
_embedding_client = None


def _get_embedding_client():
    """获取或创建 Embedding 异步客户端（全局单例）"""
    global _embedding_client
    if _embedding_client is None:
        from openai import AsyncOpenAI
        _embedding_client = AsyncOpenAI(
            api_key=settings.EMBEDDING_API_KEY,
            base_url=settings.EMBEDDING_BASE_URL,
        )
    return _embedding_client


async def get_embedding(text: str) -> List[float]:
    """单段文本向量化（复用连接池）"""
    client = _get_embedding_client()
    resp = await client.embeddings.create(
        input=text,
        model=settings.EMBEDDING_MODEL,
        timeout=15,
    )
    return resp.data[0].embedding


async def get_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """批量文本向量化（复用连接池）"""
    client = _get_embedding_client()
    resp = await client.embeddings.create(
        input=texts,
        model=settings.EMBEDDING_MODEL,
        timeout=15,
    )
    indexed = [(r.index, r.embedding) for r in resp.data]
    indexed.sort(key=lambda x: x[0])
    return [emb for _, emb in indexed]

    return [emb for _, emb in indexed]


# =============================================
# 完整文档处理流水线
# =============================================

async def process_document(
    kb_id: str,
    file_name: str,
    file_content: bytes,
) -> List[Tuple[str, str, str, str, List[float]]]:
    """
    一条函数完成文档处理的完整流水线：
      原始文件 → 提取文本 → 分块 → 向量化 → 返回结构化数据

    处理流程详述：
      1. 从文件名判断文档类型（.txt / .md / .pdf）
      2. 为整个文档生成一个唯一的 document_id
      3. 将文件内容写入临时文件（PDF 需要文件路径来读取）
      4. 按文件类型提取文本
      5. 将文本切分为带重叠的小块
      6. 批量调用 Embedding API 将每个文本块转为向量
      7. 为每个块生成唯一的 chunk_id
      8. 返回结构化数据

    参数：
        kb_id: 所属知识库 ID
        file_name: 原始文件名（用于判断类型和记录来源）
        file_content: 文件的二进制内容

    返回：
        list of (chunk_id, document_id, filename, text, vector)
        每个元组代表一个文本块的所有信息：
          - chunk_id：文本块唯一标识
          - document_id：所属文档的唯一标识（同一文档的所有块共享）
          - filename：原始文件名，用于引用来源时显示
          - text：文本块内容
          - vector：文本块的向量表示
    """
    # 1. 获取文件扩展名
    file_ext = os.path.splitext(file_name)[1].lower()

    # 2. 为整个文档生成唯一 ID
    document_id = str(uuid.uuid4())

    # 3. 写入临时文件（PDF 需要文件路径来读取页面）
    with tempfile.NamedTemporaryFile(suffix=file_ext, delete=False) as tmp:
        tmp.write(file_content)
        tmp_path = tmp.name

    # 4. 提取文本（自动根据文件类型选择解析方式）
    try:
        text = extract_text(tmp_path, file_ext, file_content)
    finally:
        # 确保临时文件被删除
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

    # 5. 如果文档为空，返回空列表
    if not text.strip():
        return []

    # 6. 将文本切分为小块
    raw_chunks = chunk_text(text)

    # 7. 批量调用 Embedding API 进行向量化
    vectors = await get_embeddings_batch(raw_chunks)

    # 8. 组装结果为结构化元组列表
    results = []
    for i, (chunk_text_content, vector) in enumerate(zip(raw_chunks, vectors)):
        chunk_id = str(uuid.uuid4())  # 每个文本块生成唯一 ID
        results.append((
            chunk_id,       # 文本块 ID
            document_id,    # 所属文档 ID
            file_name,      # 文件名（用于引用来源）
            chunk_text_content,  # 文本块内容
            vector,         # 文本块向量
        ))

    return results

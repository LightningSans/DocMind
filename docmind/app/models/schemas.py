"""
Pydantic 数据模型定义 — 请求/响应 JSON 数据结构

本模块定义了所有 API 接口的请求体和响应体数据模型，
使用 Pydantic 实现自动的请求验证和响应序列化。

模型分类：
  1. 知识库相关：KnowledgeBaseCreate / Update / Out / List
  2. 文档相关：DocumentOut / DocumentList
  3. 问答相关：ChatRequest / ReferenceSegment / ChatResponse
  4. 通用：MessageOut

每个模型都包含完整的类型标注和字段描述，
保证 API 请求和响应的数据结构清晰、类型安全。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# =============================================
# 知识库模型
# =============================================

class KnowledgeBaseCreate(BaseModel):
    """创建知识库的请求体

    前端/客户端发送 POST 请求时使用。
    """
    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="知识库名称，必填，1-200字符",
    )
    description: Optional[str] = Field(
        "",
        max_length=1000,
        description="知识库描述，可选，最多1000字符",
    )


class KnowledgeBaseUpdate(BaseModel):
    """更新知识库的请求体

    所有字段都是可选的（只需要传需要修改的字段）。
    """
    name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=200,
        description="新的知识库名称（可选）",
    )
    description: Optional[str] = Field(
        None,
        max_length=1000,
        description="新的知识库描述（可选）",
    )


class KnowledgeBaseOut(BaseModel):
    """知识库的输出模型

    创建/查询知识库时的响应数据结构。
    """
    id: str                                      # 知识库 UUID
    name: str                                    # 知识库名称
    description: str                             # 知识库描述
    document_count: int = 0                      # 文档数量
    chunk_count: int = 0                         # 文本块数量
    created_at: Optional[str] = None             # 创建时间（ISO 8601格式）

    model_config = {"from_attributes": True}     # 允许从 dict 创建


class KnowledgeBaseList(BaseModel):
    """知识库列表的输出模型"""
    total: int                                   # 知识库总数
    items: List[KnowledgeBaseOut]                # 知识库列表


# =============================================
# 文档模型
# =============================================

class DocumentOut(BaseModel):
    """文档的输出模型"""
    id: str                                      # 文档 ID（UUID）
    filename: str                                # 文件名（含扩展名）
    knowledge_base_id: str                       # 所属知识库 ID
    file_size: int                               # 文件大小（字节）
    file_type: str                               # 文件类型（.txt / .md / .pdf）
    chunk_count: int = 0                         # 文本块数量
    status: str = "completed"                    # 处理状态（processing/completed/failed）
    created_at: Optional[str] = None             # 上传时间

    model_config = {"from_attributes": True}


class DocumentList(BaseModel):
    """文档列表的输出模型"""
    total: int                                   # 文档总数
    items: List[DocumentOut]                     # 文档列表


# =============================================
# 问答模型
# =============================================

class ChatRequest(BaseModel):
    """问答请求体

    前端/客户端发送问答请求时使用。
    支持流式和非流式两种响应模式。
    """
    knowledge_base_id: str = Field(
        ...,
        description="知识库 ID，指定在哪个知识库中检索",
    )
    question: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="用户问题，至少1字符，最多10000字符",
    )
    top_k: Optional[int] = Field(
        5,
        ge=1,
        le=20,
        description="检索文档片段数量，范围1-20，默认5",
    )
    stream: Optional[bool] = Field(
        True,
        description="是否流式输出 SSE 事件，默认true（推荐）",
    )


class ReferenceSegment(BaseModel):
    """引用文档片段的模型

    回答中标注的引用来源，包含原文片段和匹配度分数，
    用于增强回答的可信度和可追溯性。
    """
    document_id: str                             # 来源文档 ID
    document_name: str                           # 来源文档名称（文件名）
    content: str                                 # 匹配到的原文片段（最多200字符）
    score: float                                 # 相似度分数（0~1，越高越匹配）


class ChatResponse(BaseModel):
    """非流式问答的响应体

    当 stream=false 时返回完整的 JSON 响应。
    流式模式下返回的是 SSE 事件，不使用此模型。
    """
    answer: str                                  # 生成的答案文本
    references: List[ReferenceSegment] = []      # 引用的文档片段列表


# =============================================
# 对话历史
# =============================================

class ConversationCreate(BaseModel):
    """创建对话的请求体"""
    kb_id: str = Field(..., description="知识库 ID")
    kb_name: Optional[str] = Field("", description="知识库名称（可选，用于列表显示）")


class ConversationMessage(BaseModel):
    """对话中的一条消息"""
    role: str                                        # "user" 或 "assistant"
    content: str                                     # 消息文本内容
    references: List[ReferenceSegment] = []           # 引用来源（仅 assistant 有）
    timestamp: Optional[str] = None                  # 消息时间戳


class ConversationOut(BaseModel):
    """对话的输出模型"""
    id: str                                          # 对话 ID
    kb_id: str                                       # 所属知识库 ID
    kb_name: str = ""                                # 知识库名称
    title: str = "新对话"                            # 对话标题
    messages: List[Dict[str, Any]] = []              # 消息列表
    created_at: Optional[str] = None                 # 创建时间
    updated_at: Optional[str] = None                 # 最后更新时间


class ConversationSummary(BaseModel):
    """对话摘要（列表用，不含完整消息）"""
    id: str
    kb_id: str
    kb_name: str = ""
    title: str = "新对话"
    message_count: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ConversationList(BaseModel):
    """对话列表的输出模型"""
    total: int
    items: List[ConversationSummary]


class ConversationAppend(BaseModel):
    """追加或更新消息的请求体"""
    role: str = Field(..., description="消息角色：user 或 assistant")
    content: str = Field("", description="消息内容")
    index: Optional[int] = Field(None, description="消息索引：-1=追加新消息，>=0=更新指定消息")
    references: Optional[List[Dict[str, Any]]] = Field(None, description="引用来源（可选）")


# =============================================
# 通用模型
# =============================================

class MessageOut(BaseModel):
    """通用消息响应

    用于返回操作结果提示，如删除成功、处理状态等。
    """
    message: str                                 # 操作结果消息
    detail: Optional[str] = None                 # 详细信息（可选）

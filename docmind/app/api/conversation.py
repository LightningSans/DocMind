"""
对话历史 API 路由 — 聊天的增删改查

本模块提供对话历史的完整管理功能：

  GET    /api/v1/conversations?kb_id=xxx   获取对话列表
  POST   /api/v1/conversations             创建新对话
  GET    /api/v1/conversations/{id}         获取对话详情（含完整消息）
  PUT    /api/v1/conversations/{id}         追加消息或更新内容
  DELETE /api/v1/conversations/{id}         删除对话

所有接口都需要 API Key 鉴权。
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import verify_api_key
from app.models.schemas import (
    ConversationCreate,
    ConversationOut,
    ConversationList,
    ConversationAppend,
    MessageOut,
)
from app.services import conversation_service

router = APIRouter(prefix="/api/v1/conversations", tags=["对话历史"])


@router.get("", response_model=ConversationList)
async def list_convs(
    kb_id: Optional[str] = Query(None, description="按知识库 ID 过滤"),
    limit: int = Query(50, ge=1, le=200, description="最大返回条数"),
    _=Depends(verify_api_key),
):
    """获取对话历史列表

    可选按知识库过滤（推荐传入 kb_id），
    只返回摘要信息，不包含完整消息内容。
    按最后更新时间降序排列。
    """
    items = conversation_service.list_conversations(kb_id=kb_id, limit=limit)
    return ConversationList(total=len(items), items=items)


@router.post("", response_model=ConversationOut, status_code=201)
async def create_conv(body: ConversationCreate, _=Depends(verify_api_key)):
    """创建新的空对话

    在开始提问前先创建对话，获得 conv_id，
    后续通过 PUT 接口追加消息。

    请求体：
        kb_id: 知识库 ID
        kb_name: 知识库名称（可选，用于列表显示）
    """
    conv = conversation_service.create_conversation(
        kb_id=body.kb_id,
        kb_name=body.kb_name or "",
    )
    return ConversationOut(**conv)


@router.get("/{conv_id}", response_model=ConversationOut)
async def get_conv(conv_id: str, _=Depends(verify_api_key)):
    """获取对话详情（包含完整消息列表）

    返回该对话的所有消息和引用来源。
    """
    conv = conversation_service.get_conversation(conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")
    return ConversationOut(**conv)


@router.put("/{conv_id}", response_model=ConversationOut)
async def update_conv(conv_id: str, body: ConversationAppend, _=Depends(verify_api_key)):
    """追加消息或更新已有消息

    两种操作模式：
      1. 追加新消息：index 不传或传 -1
      2. 更新已有消息：index 传消息在列表中的位置

    用户发送问题时 → append（role=user）
    收到回答时 → 先 append（role=assistant, content=""）
                 流式过程中 → update（更新 content）
                 流式结束 → update（final content + references）

    请求体：
        role: "user" | "assistant"
        content: 消息内容
        index: 消息索引（-1=追加新消息, >=0=更新指定消息）
        references: 引用来源（可选）
    """
    if body.index is None or body.index < 0:
        # 追加新消息
        ok = conversation_service.append_message(
            conv_id=conv_id,
            role=body.role,
            content=body.content,
            references=body.references,
        )
    else:
        # 更新已有消息
        ok = conversation_service.update_message(
            conv_id=conv_id,
            message_index=body.index,
            content=body.content,
            references=body.references,
        )

    if not ok:
        raise HTTPException(status_code=404, detail="对话不存在或操作失败")

    conv = conversation_service.get_conversation(conv_id)
    return ConversationOut(**conv)


@router.delete("/{conv_id}", response_model=MessageOut)
async def delete_conv(conv_id: str, _=Depends(verify_api_key)):
    """删除对话

    参数：
        conv_id: 对话 ID
    """
    ok = conversation_service.delete_conversation(conv_id)
    if not ok:
        raise HTTPException(status_code=404, detail="对话不存在")
    return MessageOut(message="对话已删除")

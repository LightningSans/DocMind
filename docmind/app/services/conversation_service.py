"""
对话历史服务 — 在本地磁盘上存储/读取聊天记录

使用 JSON 文件存储，每个对话存一个独立的 .json 文件。
目录结构：
  conversations/
    {conversation_id}.json    # 完整对话数据

为什么不存 Qdrant？
  Qdrant 是向量数据库，适合存向量+少量 payload。
  对话历史是结构化的 JSON 数据，JSON 文件更简单直观，
  且不需要额外数据库依赖。

每个对话文件的内容结构：
  {
    "id": "conv-uuid",
    "kb_id": "kb-uuid",
    "kb_name": "知识库名称",
    "title": "对话标题（从首条消息自动生成）",
    "messages": [
      {
        "role": "user" | "assistant",
        "content": "消息内容",
        "references": [...]  (仅 assistant 消息有),
        "timestamp": "ISO 8601"
      }
    ],
    "created_at": "ISO 8601",
    "updated_at": "ISO 8601"
  }
"""

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config import settings

# =============================================
# 对话存储目录
# 在项目根目录下创建 conversations/ 文件夹
# =============================================
CONVERSATIONS_DIR = Path(__file__).resolve().parent.parent.parent / "conversations"


def _ensure_dir():
    """确保对话存储目录存在"""
    CONVERSATIONS_DIR.mkdir(parents=True, exist_ok=True)


def _conv_path(conv_id: str) -> Path:
    """获取对话文件的完整路径"""
    return CONVERSATIONS_DIR / f"{conv_id}.json"


def _now() -> str:
    """返回当前 UTC 时间的 ISO 格式字符串"""
    return datetime.now(timezone.utc).isoformat()


def _generate_title(messages: List[Dict]) -> str:
    """
    从对话内容自动生成标题

    规则：
      - 取第一条用户消息的前 20 个字符作为标题
      - 如果超长则加 "..."
    """
    for msg in messages:
        if msg.get("role") == "user":
            text = msg.get("content", "").strip()
            if text:
                return text[:20] + ("..." if len(text) > 20 else "")
    return "新对话"


# =============================================
# 对话 CRUD
# =============================================

def create_conversation(kb_id: str, kb_name: str = "") -> Dict[str, Any]:
    """
    创建新的空对话

    参数：
        kb_id: 知识库 ID
        kb_name: 知识库名称（用于列表显示）

    返回：
        新创建的对话字典
    """
    _ensure_dir()
    conv_id = str(uuid.uuid4())
    now = _now()
    conv = {
        "id": conv_id,
        "kb_id": kb_id,
        "kb_name": kb_name,
        "title": "新对话",
        "messages": [],
        "created_at": now,
        "updated_at": now,
    }
    with open(_conv_path(conv_id), "w", encoding="utf-8") as f:
        json.dump(conv, f, ensure_ascii=False, indent=2)
    return conv


def get_conversation(conv_id: str) -> Optional[Dict[str, Any]]:
    """
    获取单个对话的完整内容（含所有消息）

    参数：
        conv_id: 对话 ID

    返回：
        对话字典，不存在则返回 None
    """
    path = _conv_path(conv_id)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def list_conversations(kb_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    """
    获取对话列表

    可选按知识库过滤。返回摘要信息（不含完整 messages 列表），
    列表按 updated_at 降序排列（最近更新的排最前）。

    参数：
        kb_id: 可选，按知识库 ID 过滤
        limit: 最大返回条数

    返回：
        对话摘要字典列表（每条含 id/kb_id/kb_name/title/message_count/created_at/updated_at）
    """
    _ensure_dir()
    results = []
    for fpath in sorted(CONVERSATIONS_DIR.glob("*.json"), reverse=True):
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                conv = json.load(f)
        except (json.JSONDecodeError, IOError):
            continue

        # 按知识库过滤
        if kb_id and conv.get("kb_id") != kb_id:
            continue

        results.append({
            "id": conv["id"],
            "kb_id": conv.get("kb_id", ""),
            "kb_name": conv.get("kb_name", ""),
            "title": conv.get("title", "新对话"),
            "message_count": len(conv.get("messages", [])),
            "created_at": conv.get("created_at", ""),
            "updated_at": conv.get("updated_at", ""),
        })

        if len(results) >= limit:
            break

    # 按 updated_at 降序排列
    results.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    return results


def append_message(conv_id: str, role: str, content: str, references: Optional[List[Dict]] = None) -> bool:
    """
    向对话追加一条消息

    参数：
        conv_id: 对话 ID
        role: 消息角色（"user" | "assistant"）
        content: 消息文本内容
        references: 引用来源列表（仅 assistant 消息需要）

    返回：
        True 成功，False 对话不存在或写入失败
    """
    conv = get_conversation(conv_id)
    if not conv:
        return False

    message = {
        "role": role,
        "content": content,
        "timestamp": _now(),
    }
    if references:
        message["references"] = references

    conv["messages"].append(message)
    conv["updated_at"] = _now()

    # 如果是第一条用户消息，自动生成对话标题
    if role == "user" and conv.get("title") == "新对话":
        conv["title"] = _generate_title(conv["messages"])

    try:
        with open(_conv_path(conv_id), "w", encoding="utf-8") as f:
            json.dump(conv, f, ensure_ascii=False, indent=2)
        return True
    except IOError:
        return False


def update_message(
    conv_id: str,
    message_index: int,
    content: str,
    references: Optional[List[Dict]] = None,
) -> bool:
    """
    更新对话中某条消息的内容（用于流式输出时实时更新答案）

    参数：
        conv_id: 对话 ID
        message_index: 要更新的消息在 messages 列表中的索引
        content: 新的消息内容
        references: 引用来源（可选）

    返回：
        True 成功，False 对话不存在
    """
    conv = get_conversation(conv_id)
    if not conv:
        return False

    if message_index < 0 or message_index >= len(conv["messages"]):
        return False

    conv["messages"][message_index]["content"] = content
    if references:
        conv["messages"][message_index]["references"] = references
    conv["updated_at"] = _now()

    try:
        with open(_conv_path(conv_id), "w", encoding="utf-8") as f:
            json.dump(conv, f, ensure_ascii=False, indent=2)
        return True
    except IOError:
        return False


def delete_conversation(conv_id: str) -> bool:
    """
    删除对话

    参数：
        conv_id: 对话 ID

    返回：
        True 删除成功，False 对话不存在
    """
    path = _conv_path(conv_id)
    if not path.exists():
        return False
    try:
        path.unlink()
        return True
    except IOError:
        return False

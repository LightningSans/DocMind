"""
大模型调用服务 — 封装 LLM API 的流式/非流式调用

本模块负责与 DeepSeek（或其他 OpenAI 兼容接口）通信，
将检索到的文档片段拼接成 Prompt，调用大模型生成答案。

提供两个核心函数：
  - chat_stream()：流式调用，逐字输出 SSE 事件
  - chat_non_stream()：非流式调用，一次性返回完整答案

工作流程：
  调用方传入(问题, 相关文档片段列表) → 本模块组装 Prompt →
  调用 LLM API → 返回答案（流式逐字或完整文本）
"""

import json
from typing import AsyncGenerator, List

from openai import AsyncOpenAI

from app.config import settings

# ========================================
# 全局单例异步客户端
# 复用 OpenAI AsyncOpenAI 实例，避免每次请求都创建新连接
# ========================================
_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    """
    获取或创建 AsyncOpenAI 客户端（单例模式）

    从 settings 读取 LLM_API_KEY 和 LLM_BASE_URL，
    因此更换模型只需修改 .env 配置，无需改代码。

    返回：
        AsyncOpenAI 客户端实例
    """
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
        )
    return _client


# =============================================
# 流式调用（SSE 逐词输出）
# 用于前端聊天对话，打字机效果逐字展示
# =============================================
async def chat_stream(
    question: str,
    context_chunks: List[str],
    model: str = None,
) -> AsyncGenerator[str, None]:
    """
    流式调用 LLM，逐个 block 产出 SSE 格式数据

    参数：
        question: 用户提出的问题
        context_chunks: 从 Qdrant 检索到的相关文档片段列表
        model: 可选的模型名称覆盖（留空使用 settings 中的默认值）

    产出的 SSE 数据格式：
        data: {"type": "text", "content": "逐字内容"}\n\n

    调用方（chat.py）会在 SSE 流之前先发送 references 事件，
    本函数只负责逐词输出文本内容。
    """
    client = _get_client()

    # 构建系统提示词——定义 AI 助手的角色和行为规则
    system_prompt = (
        "你是一个专业的企业文档智能助手。请根据提供的文档内容回答用户问题。\n\n"
        "规则：\n"
        "1. 仅基于提供的文档内容回答，如果文档中没有相关信息，请如实告知。\n"
        "2. 回答应简洁、准确、有逻辑。\n"
        "3. 引用相关文档内容时，用 [来源N] 标记引用来源。\n"
    )

    # 将多个文档片段拼接为一个上下文文本块
    # 每个片段标注来源编号，方便 LLM 在回答中引用
    context_text = "\n\n---\n".join(
        [f"[来源 {i+1}] {chunk}" for i, chunk in enumerate(context_chunks)]
    )

    # 组装最终的用户消息 = 上下文 + 问题
    user_prompt = f"文档内容：\n{context_text}\n\n---\n\n用户问题：{question}"

    # 调用 LLM API，启用 stream=True 启用流式响应
    response = await client.chat.completions.create(
        model=model or settings.LLM_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=settings.LLM_MAX_TOKENS,
        temperature=settings.LLM_TEMPERATURE,
        stream=True,  # 开启流式模式
        timeout=60,   # 60 秒超时，防止一直挂起
    )

    # 逐 block 读取流式响应，包装为 SSE 格式产出
    async for chunk in response:
        if chunk.choices and len(chunk.choices) > 0:
            delta = chunk.choices[0].delta
            if delta.content:
                # 每个 token 包装为 SSE 事件
                yield f"data: {json.dumps({'type': 'text', 'content': delta.content})}\n\n"


# =============================================
# 非流式调用（一次性返回）
# 用于内部处理或非流式 API 调用
# =============================================
async def chat_non_stream(
    question: str,
    context_chunks: List[str],
    model: str = None,
) -> str:
    """
    非流式调用 LLM，等待完整生成后一次性返回

    参数：
        question: 用户问题
        context_chunks: 检索到的相关文档片段
        model: 可选的模型覆盖

    返回：
        完整的回答文本字符串

    与 chat_stream() 的区别：
        stream=False，一次性获取全部响应再返回
    """
    client = _get_client()

    # 系统提示词（与流式版本一致）
    system_prompt = (
        "你是一个专业的企业文档智能助手。请根据提供的文档内容回答用户问题。\n\n"
        "规则：\n"
        "1. 仅基于提供的文档内容回答，如果文档中没有相关信息，请如实告知。\n"
        "2. 回答应简洁、准确、有逻辑。\n"
        "3. 引用相关文档内容时，用 [来源N] 标记引用来源。\n"
    )

    # 拼接上下文（与流式版本一致）
    context_text = "\n\n---\n".join(
        [f"[来源 {i+1}] {chunk}" for i, chunk in enumerate(context_chunks)]
    )

    user_prompt = f"文档内容：\n{context_text}\n\n---\n\n用户问题：{question}"

    response = await client.chat.completions.create(
        model=model or settings.LLM_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=settings.LLM_MAX_TOKENS,
        temperature=settings.LLM_TEMPERATURE,
        stream=False,
        timeout=60,
    )

    return response.choices[0].message.content or ""

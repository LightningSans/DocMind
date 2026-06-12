"""
DocMind 应用配置 — 全局配置管理

本模块使用 pydantic-settings 库管理所有配置项。
配置来源（优先级从高到低）：
  1. 环境变量（通过 os.environ）
  2. .env 文件（项目根目录下的 .env 文件）
  3. 代码中的默认值

所有配置项集中定义在 Settings 类中，通过
单例对象 settings 全局访问。

需要配置的 Key：
  - LLM_API_KEY / DEEPSEEK_API_KEY：大模型 API Key
  - EMBEDDING_API_KEY / ALIYUN_API_KEY：向量模型 API Key
  - DOCMIND_API_KEY：本服务的 API 鉴权密钥
"""

import os
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings


def _env(key: str, default: str = "") -> str:
    """
    从环境变量读取配置值的辅助函数
    """
    return os.environ.get(key, default)


class Settings(BaseSettings):
    # =============================================
    # 应用基础配置
    # =============================================
    APP_NAME: str = "DocMind - 智能文档问答引擎"  # 应用名称，显示在 Swagger 标题栏
    APP_VERSION: str = "1.0.0"                    # 版本号
    DEBUG: bool = False                           # 调试模式开关

    # =============================================
    # API 鉴权配置
    # 客户端调用所有 API 时必须在 Header 中携带
    # X-API-Key: yueyun
    # =============================================
    DOCMIND_API_KEY: str = "yueyun"               # 默认 API Key，生产环境请修改

    # =============================================
    # Qdrant 向量数据库连接配置
    # 默认连接本地 Docker 部署的 Qdrant
    # 支持两种连接方式（URL 优先级更高）：
    #   1. QDRANT_URL = "http://localhost:6333"
    #   2. QDRANT_HOST + QDRANT_PORT
    # =============================================
    QDRANT_HOST: str = "localhost"                # Qdrant 主机地址
    QDRANT_PORT: int = 6333                       # Qdrant gRPC+HTTP 端口
    QDRANT_URL: Optional[str] = None              # 完整连接 URL（可选，优先级高于 HOST+PORT）

    @property
    def qdrant_url(self) -> str:
        """获取 Qdrant 连接 URL"""
        return self.QDRANT_URL or f"http://{self.QDRANT_HOST}:{self.QDRANT_PORT}"

    # =============================================
    # Embedding 向量模型配置（默认阿里云 DashScope）
    # 用于将文本转为向量存入 Qdrant 进行相似度搜索
    # 兼容所有 OpenAI-format 的 Embedding API
    # =============================================
    EMBEDDING_API_KEY: str = ""                   # Embedding API Key
    EMBEDDING_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    EMBEDDING_MODEL: str = "text-embedding-v4"    # 阿里云文本嵌入模型
    EMBEDDING_DIMENSION: int = 1024               # 向量维度（需与模型匹配）

    # =============================================
    # DeepSeek 大模型配置
    # 用于文档问答的答案生成
    # 兼容所有 OpenAI-format 的 LLM API
    # =============================================
    LLM_API_KEY: str = ""                         # 大模型 API Key
    LLM_BASE_URL: str = "https://api.deepseek.com/v1"  # DeepSeek API 地址
    LLM_MODEL: str = "deepseek-chat"              # 模型名称
    LLM_MAX_TOKENS: int = 4096                    # 最大生成长度
    LLM_TEMPERATURE: float = 0.3                  # 生成温度（越低越精确）

    # =============================================
    # 文档分块配置
    # 上传的文档被切分为小块以便向量化检索
    # =============================================
    CHUNK_SIZE: int = 512          # 每块最大字符数
    CHUNK_OVERLAP: int = 64        # 相邻块之间的重叠字符数（避免切断语义）

    # =============================================
    # RAG 检索配置
    # 问答时从向量库检索相关片段的参数
    # =============================================
    RETRIEVAL_TOP_K: int = 5            # 每次检索返回的最相似片段数
    RETRIEVAL_SCORE_THRESHOLD: float = 0.6  # 相似度分数阈值（低于此值不返回）

    # =============================================
    # 文件上传配置
    # =============================================
    UPLOAD_DIR: str = str(Path(__file__).resolve().parent.parent / "uploads")  # 文件上传存储目录
    MAX_UPLOAD_SIZE_MB: int = 20  # 单文件最大上传大小（MB）

    def model_post_init(self, __context):
        """
        pydantic 初始化后置钩子

        作用：当主要配置项（EMBEDDING_API_KEY / LLM_API_KEY）
        未设置时，尝试从备用环境变量名读取，兼容不同的命名习惯。
          - EMBEDDING_API_KEY 未填时读取 ALIYUN_API_KEY
          - LLM_API_KEY 未填时读取 DEEPSEEK_API_KEY
        """
        if not self.EMBEDDING_API_KEY or self.EMBEDDING_API_KEY.startswith("{"):
            self.EMBEDDING_API_KEY = os.environ.get("ALIYUN_API_KEY", "")
            if self.EMBEDDING_API_KEY.startswith("{"):
                self.EMBEDDING_API_KEY = ""
        if not self.LLM_API_KEY or self.LLM_API_KEY.startswith("{"):
            self.LLM_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
            if self.LLM_API_KEY.startswith("{"):
                self.LLM_API_KEY = ""

    # pydantic-settings 配置
    model_config = {
        "env_file": ".env",          # 从项目根目录的 .env 文件加载
        "env_file_encoding": "utf-8",
        "extra": "ignore",           # 忽略 .env 中未定义的字段
    }


# =============================================
# 全局单例配置对象
# 在项目中通过 from app.config import settings 使用
# =============================================
settings = Settings()

"""
API 鉴权依赖 — API Key 验证中间件

本模块提供 verify_api_key 依赖函数，用于保护所有 API 接口。
客户端在请求时必须携带 X-API-Key 请求头，值需与配置中的
DOCMIND_API_KEY 一致。

使用方式（在路由函数中通过 Depends 注入）：
    @router.get("/example")
    async def example(_=Depends(verify_api_key)):
        ...

验证失败时返回 HTTP 401 Unauthorized。
"""

from fastapi import Header, HTTPException, status

from app.config import settings


async def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    """
    API Key 验证依赖函数

    从请求头中提取 X-API-Key，与 settings.DOCMIND_API_KEY 比对。
    不匹配时抛出 HTTP 401 异常，中断请求处理。

    参数：
        x_api_key: 从请求头自动获取的 API Key 值
                   Header(..., alias="X-API-Key") 表示：
                   - ... 表示该字段必填（请求头缺失则自动返回 422）
                   - alias="X-API-Key" 将参数名映射到请求头字段

    返回：
        API Key 值（验证通过后可用）

    抛出：
        HTTPException 401：API Key 无效或缺失
    """
    if x_api_key != settings.DOCMIND_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key",
        )
    return x_api_key

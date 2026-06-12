@echo off
chcp 65001 >nul
echo ====================================
echo  DocMind Backend — 一键启动
echo ====================================
echo.

:: 1. 检查 .env
if not exist ".env" (
    echo [错误] .env 文件不存在！请先复制 .env.example 为 .env 并配置 API Key
    pause
    exit /b 1
)

:: 2. 检查虚拟环境
if not exist ".venv\Scripts\python.exe" (
    echo [信息] 未找到虚拟环境，正在创建...
    python -m venv .venv
    if errorlevel 1 (
        echo [错误] 创建虚拟环境失败，请确保已安装 Python 3.10+
        pause
        exit /b 1
    )
    echo [信息] 正在安装依赖...
    call .venv\Scripts\pip install -r requirements.txt
    if errorlevel 1 (
        echo [错误] 依赖安装失败
        pause
        exit /b 1
    )
)

:: 3. 检查 Qdrant 是否可达
echo [检查] 连接 Qdrant 向量数据库...
call .venv\Scripts\python -c "from qdrant_client import QdrantClient; QdrantClient(url='http://localhost:6333').get_collections(); print('  -> Qdrant 连接正常')" 2>nul
if errorlevel 1 (
    echo [警告] Qdrant 未检测到，请确保 Docker 容器已启动：
    echo         docker run -d -p 6333:6333 -p 6334:6334 qdrant/qdrant
    echo.
    choice /c YN /M "忽略警告继续启动？"
    if errorlevel 2 exit /b 1
)

:: 4. 启动
echo.
echo [启动] 服务运行在 http://localhost:8000
echo [文档] Swagger UI: http://localhost:8000/docs
echo.
call .venv\Scripts\uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

pause

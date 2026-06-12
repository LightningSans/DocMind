#!/bin/bash
echo "===================================="
echo " DocMind Backend — 一键启动"
echo "===================================="

# 检查 .env
if [ ! -f ".env" ]; then
    echo "[错误] .env 文件不存在！请先复制 .env.example 为 .env 并配置 API Key"
    exit 1
fi

# 检查虚拟环境
if [ ! -f ".venv/bin/python" ] && [ ! -f ".venv/Scripts/python" ]; then
    echo "[信息] 未找到虚拟环境，正在创建..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
else
    if [ -f ".venv/bin/python" ]; then
        source .venv/bin/activate
    elif [ -f ".venv/Scripts/python" ]; then
        source .venv/Scripts/activate
    fi
fi

# 检查 Qdrant
echo "[检查] Qdrant 向量数据库..."
python -c "from qdrant_client import QdrantClient; QdrantClient(url='http://localhost:6333').get_collections(); print('  -> Qdrant 连接正常')" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "[警告] Qdrant 未检测到，请确保 Docker 容器已启动："
    echo "        docker run -d -p 6333:6333 -p 6334:6334 qdrant/qdrant"
    echo ""
    read -p "按 Enter 忽略警告继续启动，或 Ctrl+C 退出..."
fi

echo ""
echo "[启动] 服务运行在 http://localhost:8000"
echo "[文档] Swagger UI: http://localhost:8000/docs"
echo ""

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

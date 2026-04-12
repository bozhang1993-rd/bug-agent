#!/bin/bash

# Bug Agent 启动脚本

echo "=== Bug Agent 启动中 ==="

# 检查 Python 版本
python_version=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1)
if [ "$python_version" -lt 3 ]; then
    echo "错误: 需要 Python 3.10+"
    exit 1
fi

# 安装依赖
echo "安装依赖..."
cd "$(dirname "$0")/server"
pip install -r requirements.txt

# 启动服务
echo "启动 Bug Agent 服务..."
echo "服务地址: http://127.0.0.1:8765"
echo "API 文档: http://127.0.0.1:8765/docs"
echo ""
echo "按 Ctrl+C 停止服务"
echo ""

python3 main.py

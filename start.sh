#!/bin/bash

echo "========================================"
echo "  本地化配送服务商智能订货统计工具"
echo "========================================"
echo ""

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未检测到Python3,请先安装Python 3.8+"
    exit 1
fi

echo "[1/4] 检查依赖..."
pip3 show flask &> /dev/null
if [ $? -ne 0 ]; then
    echo "[提示] 正在安装依赖包..."
    pip3 install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "[错误] 依赖安装失败"
        exit 1
    fi
fi

echo "[2/4] 检查配置文件..."
if [ ! -f .env ]; then
    echo "[警告] 未找到.env配置文件"
    echo "[提示] 请复制 .env.example 并修改配置"
    echo "  cp .env.example .env"
fi

echo "[3/4] 数据库初始化提示..."
echo "[提示] 请手动执行 database/schema.sql 到MySQL"

echo "[4/4] 选择要启动的服务:"
echo "  1. HTTP消息接收服务 (core/app.py) - 端口5000"
echo "  2. TCP消息接收服务 (core/tcp_server.py) - 端口61108"
echo "  3. 完整业务服务 (main.py) - 端口5000"
echo ""
read -p "请选择 (1/2/3): " choice

case $choice in
    1)
        echo "启动HTTP消息接收服务..."
        python3 core/app.py
        ;;
    2)
        echo "启动TCP消息接收服务..."
        python3 core/tcp_server.py
        ;;
    3)
        echo "启动完整业务服务..."
        python3 main.py
        ;;
    *)
        echo "[错误] 无效选择"
        exit 1
        ;;
esac

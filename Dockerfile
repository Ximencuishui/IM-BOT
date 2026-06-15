# 多阶段构建 - 生产镜像
FROM python:3.12-slim AS builder

WORKDIR /app

# 安装构建依赖
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# 生产阶段
FROM python:3.12-slim

WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai

# 安装时区
RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖
COPY --from=builder /install /usr/local

# 复制应用代码
COPY . .

# 创建日志和报表目录
RUN mkdir -p logs reports

# 暴露端口
EXPOSE 5000 61108

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" || exit 1

# 启动命令 (默认启动完整业务服务)
CMD ["python", "main.py"]

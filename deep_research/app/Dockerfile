# ============================================================================
# DeepResearch 后端镜像（FastAPI + LangGraph + LangChain）
# 构建上下文 = 项目根目录（deep_research/）
# 手动构建：docker build -f app/Dockerfile -t deepresearch-backend .
# 运行入口：python app/app_main.py  ->  uvicorn 0.0.0.0:8000
# ============================================================================
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/workspace/app \
    WORKSPACE_DIR=/workspace \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple

WORKDIR /workspace

# 1) 先安装依赖，充分利用构建缓存
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 2) 拷贝源码与配置文件
COPY app/ /workspace/app/
COPY config.json /workspace/config.json
COPY main.py /workspace/main.py

# 3) 运行时数据目录（SQLite 记忆库 / 工作区输出）
RUN mkdir -p /workspace/app/data /workspace/output

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5).status==200 else 1)"

CMD ["python", "app/app_main.py"]

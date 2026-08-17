# 本地知识库文档目录

把需要导入 Milvus 向量库的文档放在本目录（支持 `.md`、`.txt`、`.markdown`，支持子目录递归），然后执行：

```bash
# 全栈部署方式（容器内执行入库）
docker compose --env-file .env.docker --profile ingest run --rm ingest

# 本地开发方式（先启动基础设施，再在本机 Python 环境执行）
python -m mult_agents.rag.ingest
# 或指定路径（默认读本目录 docs/）
$env:INGEST_INPUT_PATH = "D:\你的文档目录"; python -m mult_agents.rag.ingest
```

入库完成后，Milvus 的 `MILVUS_COLLECTION`（默认 `mult_agent_memory`）中即可被 Local RAG Scout 检索。

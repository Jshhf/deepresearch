# DeepResearch 多 Agent 行业深度研究助手 · 部署说明

> 本文档基于项目真实源码生成。源码目录：`app/`（FastAPI 后端）+ `front/agent_front/`（Vue3 前端）。
> 参考文档：《环境搭建.docx》《项目拆解-核心代码.docx》《DeepResearch多Agent行业深度研究助手.docx》。

## 1. 部署架构

```text
┌─────────────────────────────────────────────────────────────────┐
│  docker-compose.yml（全栈，一个命令拉起）                         │
│                                                                 │
│  frontend (Nginx :8080)  ──proxy /api,/health──▶  backend :8000 │
│                                                    │            │
│      postgres :5432   redis :6379                  │            │
│      etcd :2379  minio :9000/9001                  │            │
│      milvus :19530/9091   attu :8001(可选)          │            │
└─────────────────────────────────────────────────────────────────┘
```

## 2. 前置条件

- 已安装 **Docker Desktop**（Windows 需要 WSL2 后端；启动 Docker 后确认 `docker version` 可用）。
- 两个外部 API Key：
  - `DASHSCOPE_API_KEY`：阿里云百炼（必填，用于 Qwen 推理 + Embedding）。
  - `BOCHA_API_KEY`：博查 Web Search（可选，不填则 Web Scout 检索返回空，RAG/直接回答仍可用）。
- 国内拉取镜像慢时，先在 Docker Desktop Settings 里配置 registry-mirrors（参考《环境搭建.docx》）。

## 3. 快速开始（全栈容器部署）

在项目根目录 `deep_research/` 下执行：

```powershell
# 1) 生成 Docker 环境变量文件并编辑，填入 Key
Copy-Item .env.docker.example .env.docker
notepad .env.docker

# 2) 构建并启动全部服务（首次构建需等待 pip/npm 安装，约 5-15 分钟）
docker compose --env-file .env.docker up -d --build

# 3) 查看状态
docker compose --env-file .env.docker ps
```

访问地址：

| 服务 | 地址 |
| --- | --- |
| 前端工作台 | http://localhost:8080 |
| 后端 API（Swagger） | http://localhost:8000/docs |
| 后端健康检查 | http://localhost:8000/health |
| Milvus 管理界面 Attu（可选） | http://localhost:8001 （`docker compose --env-file .env.docker --profile tools up -d attu` 后可用） |
| MinIO 控制台 | http://localhost:9001 （账号 `minioadmin` / 密码见 `.env.docker`） |

> 首次启动 Milvus 需要 1-3 分钟初始化（etcd + MinIO + Milvus 依次健康检查），`backend` 会等 Milvus 健康后再启动，属正常现象。

## 4. 健康检查命令

```powershell
# 容器整体状态
docker compose --env-file .env.docker ps

# 后端
curl http://localhost:8000/health
# 期望输出：{"status":"ok","service":"deepresearch-backend"}

# 前端
curl -I http://localhost:8080

# PostgreSQL
docker compose --env-file .env.docker exec postgres pg_isready -U deepresearch -d deepresearch

# Redis
docker compose --env-file .env.docker exec redis redis-cli -a deepresearch ping   # 期望 PONG

# Milvus（HTTP 健康端口）
curl http://localhost:9091/healthz

# etcd
docker compose --env-file .env.docker exec etcd etcdctl endpoint health

# MinIO
curl http://localhost:9000/minio/health/live
```

## 5. 向量数据入库（RAG 本地知识库）

1. 把 `.md` / `.txt` / `.markdown` 文档放到项目根目录 `docs/`（支持子目录）。
2. 执行一次性入库任务（会调用 DashScope Embedding 写入 Milvus）：

```powershell
docker compose --env-file .env.docker --profile ingest run --rm ingest
```

3. 看到 `入库完成 | 文件数=N | chunk数=M | collection=mult_agent_memory` 即成功。

> 已修复：`app/mult_agents/rag/ingest.py` 原先引用了原作者机器的路径
> （`/Users/pengshaoyong/...` 和 `mult_agents_memory.*` 导入），现改为
> `INGEST_INPUT_PATH` 环境变量 + 项目内 `docs/` 默认目录，导入路径与扁平化目录结构已兼容。

## 6. 常用运维命令

```powershell
# 查看后端日志
docker compose --env-file .env.docker logs -f backend

# 查看某个服务日志
docker compose --env-file .env.docker logs -f milvus-standalone

# 重启后端（改配置后）
docker compose --env-file .env.docker restart backend

# 停止全部（保留数据卷）
docker compose --env-file .env.docker down

# 停止并删除数据卷（慎用，清空所有数据库/向量数据）
docker compose --env-file .env.docker down -v

# 重新构建
docker compose --env-file .env.docker up -d --build --force-recreate
```

## 7. 数据持久化说明

| 数据 | 位置 | 说明 |
| --- | --- | --- |
| PostgreSQL 数据 | 命名卷 `postgres-data` | LangGraph Checkpointer、短期/长期记忆表 |
| Redis 数据 | 命名卷 `redis-data` | 会话缓存（本项目默认 `CHECKPOINTER_BACKEND=postgres`，Redis 为可选） |
| Milvus 向量数据 | 命名卷 `milvus-data` | 向量集合 `mult_agent_memory` |
| Milvus 日志 | 命名卷 `milvus-logs` | |
| MinIO 对象数据 | 命名卷 `minio-data` | Milvus 存储后端 |
| etcd 元数据 | 命名卷 `etcd-data` | Milvus 元数据 |
| SQLite 记忆库 | 绑定挂载 `./app/data:/workspace/app/data` | `memory.db`（长期记忆降级存储） |
| 工作区输出 | 绑定挂载 `./output:/workspace/output` | `WORKSPACE_DIR` 报告/文件输出 |
| 待入库文档 | 绑定挂载 `./docs:/workspace/docs` | 向量入库输入 |

> 命名卷由 Docker 管理（`docker volume ls` 可见）；绑定挂载直接落在项目目录，便于备份。
> 生产环境请把 `.env.docker` 中的默认密码全部修改，并限制端口对外暴露。

## 8. 本地开发模式（不使用全栈 compose）

只想让后端/前端在本机跑、数据库用容器：

```powershell
# 1) 只启动基础设施
docker compose -f docker-compose.infrastructure.yml --env-file .env.docker up -d

# 2) 本机 .env（由 .env.example 复制）填写本机地址
Copy-Item .env.example .env
# POSTGRES_DSN=postgresql://deepresearch:deepresearch@127.0.0.1:5432/deepresearch
# REDIS_URL=redis://:deepresearch@127.0.0.1:6379/0
# MILVUS_HOST=127.0.0.1

# 3) 后端（Python 3.10/3.11）
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app/app_main.py            # http://localhost:8000

# 4) 前端（Node 20.19+ / 22.12+，本机 node v16 不满足 Vite 7 要求，需升级）
cd front/agent_front
npm install
npm run dev                       # http://localhost:5173（已代理 /api 到 127.0.0.1:8000）
```

> 本机 Python 是 3.10.8 32 位，`requirements.txt` 中 numpy/grpcio/pymilvus 等大包可能没有 32 位 wheel，
> 本地开发建议使用 64 位 Python 3.11；容器内不受此限制（镜像基于 64 位 python:3.11-slim）。

## 9. 端口占用一览

| 端口 | 服务 | 用途 |
| --- | --- | --- |
| 5432 | PostgreSQL | 数据库 |
| 6379 | Redis | 缓存/会话 |
| 2379 | etcd | Milvus 元数据（容器内） |
| 9000 / 9001 | MinIO | 对象存储 API / 控制台 |
| 19530 / 9091 | Milvus | gRPC / 健康检查 |
| 8001 | Attu | Milvus 管理界面（可选） |
| 8000 | backend | FastAPI |
| 8080 | frontend | Nginx 前端 |
| 5173 | vite dev | 本地开发前端 |

## 10. 环境变量说明

### `.env.docker`（容器部署）

| 变量 | 说明 |
| --- | --- |
| `DASHSCOPE_API_KEY` | 阿里云百炼 Key（必填） |
| `BOCHA_API_KEY` | 博查搜索 Key（可选） |
| `MODEL` | Qwen 模型名，默认 `qwen-plus` |
| `TENANT_ID` / `USER_ID` / `THREAD_ID` | 多租户/会话标识 |
| `MAX_ITERATIONS` | 多 Agent 迭代预算，默认 3 |
| `ENABLE_MEMORY` / `ENABLE_MILVUS` | 记忆 / 向量检索开关 |
| `SHORT_TERM_BACKEND` / `LONG_TERM_BACKEND` / `CHECKPOINTER_BACKEND` | 记忆后端（文档推荐 `postgres`） |
| `MILVUS_COLLECTION` | 向量集合名，默认 `mult_agent_memory` |
| `POSTGRES_DSN` / `REDIS_URL` / `MILVUS_HOST` / `MILVUS_PORT` | 容器网络内连接串 |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | 数据库账号（compose 用） |
| `REDIS_PASSWORD` / `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` | 中间件账号（compose 用） |

### 应用读取优先级

`环境变量 > config.json`（`config.json` 的 `api_key` 留空即可，实际走环境变量）。
后端启动时若缺少 `DASHSCOPE_API_KEY` 会在首次研究请求时报错：`缺少 DASHSCOPE_API_KEY 配置`。

## 11. 常见问题排查

### Milvus 起不来 / 一直 unhealthy
- 首次启动等待 1-3 分钟；`docker compose --env-file .env.docker logs milvus-standalone` 看日志。
- 检查内存：Milvus 需要至少 2GB 可用内存；Docker Desktop 设置中调大 WSL2 内存。
- 端口冲突：`netstat -ano | findstr 19530`，被占用则改 compose 端口映射。

### 后端健康但提问报错
- 先看 `docker compose --env-file .env.docker logs backend`。
- 未配置 `DASHSCOPE_API_KEY` → 检查 `.env.docker` 后 `docker compose --env-file .env.docker restart backend`。
- `PostgreSQL checkpointer 初始化失败` → 确认 postgres 健康、`POSTGRES_DSN` 正确；`CHECKPOINTER_BACKEND=auto` 时会自动降级为内存，不影响启动。
- `Redis checkpointer ... FT._LIST` → 当前 Redis 无 RediSearch，属预期降级；文档推荐 `CHECKPOINTER_BACKEND=postgres`。

### 前端构建失败（npm run build）
- 容器内使用 Node 22，满足 Vite 7 的 `engines` 要求。若本机构建失败，多半是 Node 版本过低（需 ≥ 20.19）。
- `vue-tsc` 类型检查失败时，可临时改为 `npm run build-only` 排查是否为类型问题。

### 向量入库失败
- 确认 `docs/` 下有 `.md`/`.txt` 文件；确认 Milvus 健康；确认 `DASHSCOPE_API_KEY` 有效（Embedding 走 DashScope）。
- 检查日志：`docker compose --env-file .env.docker --profile ingest run --rm ingest`（前台直接输出）。

## 12. 本次交付/修改文件清单

```text
deep_research/
├── docker-compose.yml                  [新增] 全栈编排（infra + backend + frontend + ingest）
├── docker-compose.infrastructure.yml   [新增] 仅基础设施（Postgres/Redis/etcd/MinIO/Milvus/Attu）
├── .env.docker.example                 [新增] 容器部署环境变量模板
├── .env.example                        [更新] 补齐 BOCHA_API_KEY 与注释
├── README-部署说明.md                  [新增] 本文档
├── docs/README-待入库文档.md           [新增] 向量入库说明
├── app/Dockerfile                      [新增] 后端镜像
├── .dockerignore                       [新增] 后端构建上下文排除项
├── app/mult_agents/rag/ingest.py       [修复] 导入路径 + INGEST_INPUT_PATH 可配置
└── front/agent_front/
    ├── Dockerfile                      [新增] 前端镜像（Node 构建 + Nginx）
    ├── nginx.conf                      [新增] /api、/health 反向代理 + SSE 支持
    └── .dockerignore                   [新增] 前端构建上下文排除项
```

> 未修改任何业务代码逻辑；仅对 `ingest.py` 做了部署必需的最小适配。

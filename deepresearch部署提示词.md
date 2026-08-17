# 角色与目标

你是一名资深 DevOps 工程师，当前环境是 Windows（PowerShell）。请帮我完整部署 DeepResearch 多 Agent 深度研究项目，让前后端及全部依赖服务稳定运行，最后给出部署记录、验证结果和使用说明。全程使用中文。

如果你能直接访问本机文件系统（如 Codex、Claude Desktop），请直接读取文件并执行；如果只能远程给指令，则按步骤给出命令和检查点，等我确认后再继续。

# 项目信息

- 项目根目录：`D:\deepresearch\deep_research`
- 部署说明（必须阅读）：`D:\deepresearch\deep_research\README-部署说明.md`
- 部署方式：Docker Compose 全栈部署（frontend、backend、postgres、redis、etcd、minio、milvus，attu/ingest 按需）
- 环境变量模板：`D:\deepresearch\deep_research\.env.docker.example`
- 部署状态文件（硬性要求）：`D:\deepresearch\deploy-progress.md`

# Token 管理与断点续跑（硬性要求）

部署耗时长，单个会话的 token 可能不够。必须按以下方式工作，实现“一次启动、多段续跑、最终完成”：

1. 拆成 5 个阶段：环境检查 → Docker 配置 → 应用配置与构建启动 → 健康检查 → 文档入库；每完成一个阶段立即更新部署状态文件。
2. 状态文件记录：已完成项、关键命令与输出摘要、错误及解决办法、当前阶段、下一步动作。
3. 每次会话先读部署状态文件；已有内容就从断点继续，不重复已完成步骤，不重新阅读大文件。
4. 输出节制：日志重定向到 `D:\deepresearch\deploy.log`，只查看最后 50-100 行或按错误关键词过滤；大文件用 `Select-Object -First`/`rg` 只看关键部分，不粘贴完整日志。
5. 长命令（拉镜像、构建）先说明预计时长再执行；完成后立刻更新状态文件。
6. 如果本会话 token 将要用完，主动停下并更新状态文件，然后告诉用户：新建会话后发送“继续部署，先读 D:\deepresearch\deploy-progress.md”即可续跑。
7. 把可脚本化步骤固化为 `deploy.ps1`（幂等、可重复执行），新会话直接运行脚本并从状态文件续跑。

# 硬性要求

1. Docker Desktop、WSL2、镜像、容器数据全部放 D 盘：C 盘仅剩约 20GB，D 盘约 227GB 可用。
2. 安装 Docker Desktop 到 D 盘，例如：`Docker Desktop Installer.exe install --accept-license --backend=wsl-2 --installation-dir="D:\Docker" --wsl-default-data-root="D:\DockerData"`；若安装器不支持这些参数，装好后在 Docker Desktop 设置中把磁盘镜像/数据位置改到 `D:\DockerData`。
3. 已有 WSL 发行版在 C 盘时，先导出再导入 D 盘；操作前先给方案，不直接卸载。
4. API Key 只写入 `.env.docker`，不写入源码、不上传仓库。
5. 不修改业务代码，除非是部署必需 bug；确需修改时先说明原因。

# 部署步骤

阶段一 环境检查：Windows 版本、`wsl --status`、`wsl --version`、虚拟化、内存、磁盘、Docker 是否已装、端口占用（5432/6379/19530/8000/8080）；更新状态文件。

阶段二 Docker 配置：安装并启动 Docker Desktop（数据在 D 盘），确认 `docker version`、`docker compose version` 可用；配置 registry-mirrors 镜像加速；更新状态文件。

阶段三 应用配置与构建启动：`Copy-Item .env.docker.example .env.docker`，填入 `DASHSCOPE_API_KEY`（必填）、`BOCHA_API_KEY`（可选）；执行 `docker compose --env-file .env.docker up -d --build`；首次构建约 5-15 分钟，Milvus 初始化约 1-3 分钟，等待全部服务 healthy；更新状态文件。

阶段四 健康检查：按 README 第 4 节逐项验证 backend `/health`、frontend 8080、postgres、redis、milvus `/healthz`、etcd、minio，把真实输出摘要写入状态文件。

阶段五 文档入库（可选）：若 `docs/` 有待入库文档，执行 `docker compose --env-file .env.docker --profile ingest run --rm ingest`，确认出现“入库完成”。

# 交付总结

最后给出：访问地址、服务状态、密钥保管提醒、常用启停命令、数据在 D 盘的实际位置、部署前后 C 盘空间对比，并把部署状态文件标记为完成。

# 报错处理

- 不跳过报错；先看 `docker compose --env-file .env.docker logs --tail=100 <service>`、端口检查，定位并修复后把原因和解决办法记入状态文件。
- 缺少 `DASHSCOPE_API_KEY` 时，先完成其余部署并验证，最后提示补 Key 后执行 `docker compose --env-file .env.docker restart backend`。

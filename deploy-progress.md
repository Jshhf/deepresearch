# DeepResearch 部署进度

> 本文件由部署 AI 维护，用户无需手动编辑。每次会话先读本文件，从“当前阶段/下一步”继续；每完成一个阶段立即更新。

## 总体状态

- [x] 阶段一：环境检查
- [x] 阶段二：Docker 配置（数据放 D 盘）
- [x] 阶段三：应用配置与构建启动
- [x] 阶段四：健康检查
- [x] 阶段五：文档入库（已用新 Key 完成）
- [x] 交付总结

## 当前阶段

全部完成（部署 + 健康检查 + 文档入库均通过）

## 下一步

无（可直接使用）。后续更换 Key 时：更新 .env.docker 后执行 docker compose --env-file .env.docker up -d --force-recreate backend，再按需重跑入库。

## 环境摘要

- Windows 版本：Windows 11 Home China Build 26200，64 位，LENOVO 82WM
- WSL：WSL 2.7.11.0，内核 6.18.33.2-2；VirtualMachinePlatform 与 WSL 功能已启用；Ubuntu 发行版为 v1（已停止），位于 C 盘 AppData，本次部署不卸载/不迁移
- Docker：Docker Desktop 4.85.0 已安装到 D:\Docker；引擎 29.6.2；Docker Compose v5.3.1；Docker 数据根 D:\DockerData（docker-desktop BasePath=D:\DockerData\main）
- 端口占用：6379 原被本机 Redis 服务占用，已停止该服务并改为 Manual；其余目标端口均空闲
- 虚拟化：VirtualizationFirmwareEnabled=True；内存 15.7GB
- 磁盘（部署前）：C 盘可用 19.7GB / D 盘可用 227.2GB
- 磁盘（部署后）：C 盘可用 26.0GB / D 盘可用 215.5GB；D:\Docker 约 4.07GB，D:\DockerData 约 6.73GB
- 当前用户非管理员：Docker Desktop 安装会触发 UAC，需用户确认
- registry-mirrors 已配置：daocloud / 1ms.run / xuanyuan.me / 163 / baidubce，并已重启引擎生效
- 后端 Dockerfile 已加清华 PyPI 镜像（PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple），解决直连 PyPI 极慢问题

## 关键命令与输出摘要

- 阶段一环境检查完成（2026-08-08）：
  - OS=Microsoft Windows 11 Home China Build=26200 Arch=64-bit
  - RAM_GB=15.7；VirtualizationFirmwareEnabled=True；IsAdmin=False
  - WSL 版本 2.7.11.0 / 内核 6.18.33.2-2；wsl --list：Ubuntu Stopped v1
  - 磁盘：C 280.4GB 已用 / 19.7GB 空闲；D 424.3GB 已用 / 227.2GB 空闲
  - docker 命令不存在（DOCKER_NOT_FOUND）
  - 端口监听：PORT=6379 PID=6736 PROC=redis-server（Windows 服务 Redis，Automatic）
- 阶段二完成（2026-08-08）：
  - 直接 curl 下载到 154.5MB 时连接重置；改用 winget download Docker.DockerDesktop 完成下载（4.85.0，596.1MB，哈希校验通过）
  - 安装命令：Docker Desktop Installer.exe install --accept-license --backend=wsl-2 --installation-dir=D:\Docker --wsl-default-data-root=D:\DockerData
  - 安装结果：D:\Docker 存在 Docker Desktop.exe，卸载注册表 InstallLocation=D:\Docker，Docker Desktop 服务 com.docker.service 已安装
  - docker version：Client 29.6.2 / Server Docker Desktop 4.85.0 Engine 29.6.2；docker compose version v5.3.1
  - docker info：Root=/var/lib/docker，Mem=7.6GB；Registry Mirrors 已生效
  - WSL：docker-desktop v2 Running，BasePath=\\?\D:\DockerData\main
  - 端口处理：Stop-Service Redis；Set-Service Redis -StartupType Manual（6379 已释放）
  - .env.docker 已由 .env.docker.example 生成，DASHSCOPE_API_KEY 已从环境变量写入，BOCHA_API_KEY 留空
- 阶段三四五执行结果（2026-08-08，deploy.ps1）：
  - docker compose --env-file .env.docker up -d --build 成功；deepresearch-backend/frontend 镜像构建完成
  - docker compose ps：backend Up (healthy)、frontend Up、postgres/redis/etcd/minio/milvus 全部 healthy
  - backend /health：{"status":"ok","service":"deepresearch-backend"}
  - frontend 8080：HTTP 200；浏览器已打开 http://localhost:8080/
  - postgres：accepting connections；redis：PONG；milvus /healthz：OK；etcd：healthy；minio：HTTP 200
  - ingest 运行失败：DashScope Embedding 返回 status_code=400 code=Arrearage message=Access denied, please make sure your account is in good standing（阿里云百炼账号欠费，非部署问题）
- 新 Key 验证与入库完成（2026-08-08）：
  - 用户更换 DASHSCOPE_API_KEY 后已写入 .env.docker（仅该文件保存，未入仓库/状态文件）
  - DashScope chat 测试：HTTP 200，qwen-plus 正常返回
  - 后端已用新 Key 重建：docker compose --env-file .env.docker up -d --force-recreate backend；/health 返回 ok
  - 入库成功：入库完成 | 文件数=1 | chunk数=1 | collection=mult_agent_memory
  - deploy.ps1 已改为优先保留 .env.docker 中已有 Key，避免后续重跑时被旧环境变量覆盖

## 已解决问题

1. 下载中断：Docker 安装包 curl 下载在 154.5MB 处连接重置；解决：改用 winget download，完整下载并校验哈希。
2. 安装返回码异常：Start-Process -Verb RunAs 返回 1073807364，但实际安装成功（D:\Docker + 注册表均确认）。
3. 端口 6379 冲突：Windows 服务 Redis（Automatic）占用；解决：以管理员停止该服务并改为 Manual，已释放端口。
4. 构建过慢：直连 PyPI 30 秒超时，后端 pip install 卡死 40 分钟+；解决：app/Dockerfile 增加 PIP_INDEX_URL 清华镜像，后端镜像 101 秒构建完成。
5. deploy.ps1 首次运行被 PowerShell 5.1 的 NativeCommandError 打断（docker 构建进度走 stderr）；解决：脚本顶部 $ErrorActionPreference 改为 Continue，重跑成功。
6. 文档入库失败：DashScope 账号欠费（Arrearage）；用户充值并更换 Key 后已解决，入库成功。

## 备注

- 项目根目录：D:\deepresearch\deep_research
- 部署说明：D:\deepresearch\deep_research\README-部署说明.md
- 完整部署日志：D:\deepresearch\deploy.log
- 可重复执行脚本：D:\deepresearch\deploy.ps1（幂等；已用于本次构建、健康检查、入库）
- API Key 只写入 .env.docker，未写入源码、未显示明文
- 数据实际位置：Docker Desktop 程序 D:\Docker；WSL/Docker 数据 D:\DockerData；项目输出 ./output、记忆 ./app/data、入库文档 ./docs 绑定挂载；Postgres/Redis/etcd/MinIO/Milvus 数据在 Docker 命名卷（位于 D:\DockerData 内）
- 常用命令：查看 docker compose --env-file .env.docker ps；启停 docker compose --env-file .env.docker up -d / down；重启后端 docker compose --env-file .env.docker restart backend；日志 docker compose --env-file .env.docker logs -f backend

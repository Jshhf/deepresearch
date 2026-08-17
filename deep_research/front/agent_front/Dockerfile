# ============================================================================
# DeepResearch 前端镜像（Vue3 + Vite 构建 -> Nginx 托管）
# 构建上下文 = front/agent_front
# ============================================================================

# ---- 构建阶段 ----
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# ---- 运行阶段 ----
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80

# API Audit Platform

内部开放平台的 API 调用审计与访问凭证管理后端服务。

## 功能特性

- **应用接入登记**：应用的增删改查，记录负责人、描述等信息
- **访问凭证发放**：为应用生成 API Key / Secret，Secret 仅创建时返回一次
- **调用身份校验**：通过 API Key（可选 Secret）校验调用方身份
- **全量审计日志**：自动记录每次 API 调用的请求、响应、耗时、IP、UA 等
- **多维查询**：按应用、接口路径、HTTP 方法、状态码、时间范围查询审计日志
- **凭证启停**：支持手动禁用/启用凭证，禁用后立即失效
- **安全边界**：Secret 使用 bcrypt 散列存储，请求/响应体按大小截断

## 技术栈

- FastAPI 0.115（异步 + 自动 OpenAPI 文档）
- SQLAlchemy 2.0 + asyncpg（异步 PostgreSQL）
- passlib[bcrypt]（Secret 散列）
- Docker / Docker Compose

## 快速启动

### Docker 一键部署（推荐）

```bash
docker-compose up -d --build
```

启动后：
- 服务地址：http://localhost:8000
- API 文档：http://localhost:8000/docs
- 管理员 Token（默认）：`admin-token-change-me`

### 本地开发

```bash
pip install -r requirements.txt
cp .env.example .env
# 确保本地 PostgreSQL 可用，修改 .env 中 DATABASE_URL
uvicorn app.main:app --reload
```

## 目录结构

```
app/
├── core/              # 横切关注点：鉴权、审计中间件、安全工具
│   ├── auth.py        # 管理员 Token 校验 + API Key 鉴权依赖
│   ├── audit_middleware.py  # 全量审计中间件
│   └── security.py    # Key/Secret 生成、bcrypt 散列、指纹
├── models/            # 数据实体
│   └── entities.py    # Application / ApiCredential / AuditLog
├── schemas/           # 请求/响应 DTO
│   └── dtos.py
├── services/          # 业务服务层
│   ├── app_service.py # 应用 + 凭证管理
│   └── audit_service.py
├── routers/           # API 路由
│   ├── admin.py       # 应用管理 + 凭证管理（需管理员 Token）
│   ├── audit.py       # 审计日志查询（需管理员 Token）
│   └── demo.py        # Demo 业务接口（需 API Key）
├── config.py          # 环境配置
├── database.py        # DB 引擎与会话
└── main.py            # 应用入口
examples/
└── demo_flow.py       # 端到端调用示例
```

## 主要 API

所有管理接口需在 Header 中携带 `Authorization: Bearer <ADMIN_TOKEN>`。

### 应用管理

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/admin/applications` | 创建应用 |
| GET  | `/api/v1/admin/applications` | 应用列表（支持 keyword 搜索） |
| GET  | `/api/v1/admin/applications/{app_id}` | 应用详情 |
| PATCH | `/api/v1/admin/applications/{app_id}` | 更新应用 |
| DELETE | `/api/v1/admin/applications/{app_id}` | 删除应用（级联删除凭证） |

### 凭证管理

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/admin/applications/{app_id}/credentials` | 发放凭证（仅首次返回 Secret 明文） |
| GET  | `/api/v1/admin/applications/{app_id}/credentials` | 凭证列表 |
| POST | `/api/v1/admin/applications/{app_id}/credentials/{id}/disable` | 禁用凭证 |
| POST | `/api/v1/admin/applications/{app_id}/credentials/{id}/enable` | 启用凭证 |

### 审计日志

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/admin/audit` | 多维查询（app_id / api_key / method / path / status_code / start_time / end_time） |
| GET | `/api/v1/admin/audit/{id}` | 单条详情（含请求/响应体） |
| GET | `/api/v1/admin/audit/request/{request_id}` | 按 request_id 查详情 |

### Demo 接口（需 API Key）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET  | `/api/v1/demo/hello`  | hello 示例 |
| POST | `/api/v1/demo/echo`   | 回显请求体 |
| GET  | `/api/v1/demo/whoami` | 返回当前调用方身份 |

### 鉴权方式

业务接口支持两种方式传递 API Key：

1. **Header 方式**：`X-API-Key: <api_key>`，可选 `X-API-Secret: <api_secret>`
2. **Bearer 方式**：`Authorization: Bearer <api_key>`

## 运行示例脚本

```bash
pip install requests
python examples/demo_flow.py
```

脚本会走通：建应用 → 发凭证 → 调用 Demo → 查审计 → 禁用/恢复凭证 全流程。

## 安全说明

- API Secret 仅在创建时返回一次明文，数据库只存 bcrypt 散列和指纹
- 管理接口使用独立的管理员 Token，需妥善保管
- 审计日志中的请求/响应体按配置阈值截断，避免存储膨胀
- 凭证禁用后下一次调用鉴权直接返回 403，立即生效

## 环境变量

参见 `.env.example`：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `APP_NAME` | 服务名 | API Audit Platform |
| `APP_ENV` | 运行环境 | dev |
| `DEBUG` | 是否开启调试 | true |
| `DATABASE_URL` | PostgreSQL 连接串 | - |
| `ADMIN_TOKEN` | 管理接口访问令牌 | admin-token-change-me |
| `AUDIT_BODY_MAX_SIZE` | 审计日志 body 最大字节 | 32768 |

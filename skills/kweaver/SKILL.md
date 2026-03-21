---
name: kweaver
description: >-
  操作 KWeaver 知识网络与 Decision Agent — 构建知识网络、查询 Schema/实例、
  语义搜索、执行 Action、Agent CRUD 与对话。
  操作 Vega 可观测平台 — 查询 Catalog/资源/连接器类型、健康巡检。
  当用户提到"知识网络"、"知识图谱"、"查询对象类"、
  "执行 Action"、"有哪些 Agent"、"创建 Agent"、"跟 Agent 对话"、
  "数据源"、"Catalog"、"Vega"、
  "健康检查"、"巡检"等意图时自动使用。
allowed-tools: Bash(npx kweaver *)
argument-hint: [自然语言指令]
---

# KWeaver CLI

KWeaver 平台的命令行工具，覆盖认证、知识网络管理与查询、Agent CRUD 与对话、数据源管理。

> **此 skill 替代旧版 `kweaver-core`**，新增 Vega 可观测平台、BKN push/pull 等功能。
> 旧版仍可使用但不再更新。

## 安装

```bash
npm install -g @kweaver-ai/kweaver-sdk
```

需 Node.js 22+。也可用 `npx kweaver` 临时运行。

## 使用方式

```bash
kweaver <command> [subcommand] [options]
```

## 使用前提

**认证凭据通过 `~/.kweaver/` 管理，支持自动刷新。禁止提前检查环境变量，禁止询问用户提供密码或 Token。**

### 认证优先级

1. `KWEAVER_TOKEN` + `KWEAVER_BASE_URL` 环境变量 → 静态 Token（如存在则优先使用，**不会**自动刷新）
2. `~/.kweaver/` 凭据（`kweaver auth login` 写入）→ 自动刷新（推荐）

## 命令组总览

| 命令组 | 说明 | 详细参考 |
|--------|------|---------|
| `auth` | 认证管理（login/logout/status） | `references/auth.md` |
| `token` | 打印当前 access token（自动刷新） | — |
| `bkn` | BKN 知识网络管理、Schema、查询、Action | `references/bkn.md` |
| `agent` | Agent CRUD、发布、对话 | `references/agent.md` |
| `ds` | 数据源管理 | `references/ds.md` |
| `vega` | Vega 可观测平台（catalogs、resources、connector-types、health） | `references/vega.md` |
| `config` | 平台配置（business domain 等） | `references/config.md` |
| `context-loader` | MCP 分层检索 | `references/context-loader.md` |
| `call` | 通用 API 调用 | `references/call.md` |

**按需阅读**：需要具体命令参数或编排示例时，读取对应的 reference 文件。

## 注意事项

- **不要自行猜测 business_domain 值**。首次使用时运行 `kweaver config show` 确认当前 business domain。如果返回 `bd_public (default)` 但命令结果为空，可能需要用 `kweaver config set-bd <uuid>` 设置正确的值（从平台 UI 的请求头中获取 `X-Business-Domain`）
- Action 执行有副作用，执行前向用户确认
- Token 1 小时过期，SDK 的 `connect()` 和 CLI 的 `ensureValidToken` 自动刷新
- 如果 refresh token 也失效，提示用户 `kweaver auth login`

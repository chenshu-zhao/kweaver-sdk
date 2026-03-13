# KWeaver SDK

ADP (AI Data Platform) Python SDK -- 面向 AI Agent 的知识网络构建与查询工具集。

## 安装

```bash
pip install -e .
```

需要 Python >= 3.10，依赖 `httpx` 和 `pydantic`。

## 快速开始

```python
from kweaver import ADPClient

client = ADPClient(
    base_url="https://your-adp-instance.com",
    token="Bearer ory_at_xxx",           # ADP Bearer Token
    business_domain="bd_public",          # 业务域（可选）
)
```

## Skills

SDK 提供 6 个 Skill，覆盖从数据库连接到 Agent 对话的完整流程：

### 1. ConnectDbSkill -- 连接数据库

注册外部数据库并发现表结构。

```python
from kweaver.skills import ConnectDbSkill

skill = ConnectDbSkill(client=client)
result = skill.run(
    db_type="mysql",
    host="10.0.0.1",
    port=3306,
    database="erp",
    account="readonly",
    password="***",
)
# result:
# {
#     "datasource_id": "ds_01",
#     "tables": [
#         {"name": "orders", "columns": [{"name": "id", "type": "bigint", "comment": "主键"}, ...]},
#         ...
#     ]
# }
```

### 2. BuildKnSkill -- 构建知识网络

从已注册的数据源自动创建知识网络（对象类型、关系类型），并触发构建。

```python
from kweaver.skills import BuildKnSkill

skill = BuildKnSkill(client=client)
result = skill.run(
    datasource_id="ds_01",
    network_name="供应链知识网络",
    tables=["orders", "products", "suppliers"],       # 可选，不传则使用全部表
    relations=[                                        # 可选，定义表间关系
        {
            "name": "订单包含产品",
            "from_table": "orders",
            "from_field": "product_id",
            "to_table": "products",
            "to_field": "id",
        },
    ],
)
# result:
# {
#     "kn_id": "kn_abc",
#     "kn_name": "供应链知识网络",
#     "object_types": [{"name": "orders", "id": "ot_01", "field_count": 8}, ...],
#     "relation_types": [{"name": "订单包含产品", "from": "orders", "to": "products"}],
#     "status": "completed"
# }
```

### 3. LoadKnContextSkill -- 加载知识网络上下文

发现并浏览知识网络的 schema 和实例数据，适合为 LLM 提供上下文。

```python
from kweaver.skills import LoadKnContextSkill

skill = LoadKnContextSkill(client=client)

# 模式 1: overview -- 列出所有知识网络
result = skill.run(mode="overview")
# {"knowledge_networks": [{"id": "kn_01", "name": "供应链", "object_type_count": 5, ...}]}

# 模式 2: schema -- 获取知识网络的完整 schema
result = skill.run(
    mode="schema",
    kn_id="kn_01",                  # 或 kn_name="供应链"
    include_properties=True,         # 包含属性定义（默认 True）
    include_samples=True,            # 包含示例数据（默认 False）
    sample_size=3,
)
# {
#     "kn_name": "供应链",
#     "object_types": [
#         {"name": "orders", "properties": [...], "sample_data": [...]},
#         ...
#     ],
#     "relation_types": [{"name": "订单包含产品", "source": "orders", "target": "products"}]
# }

# 模式 3: instances -- 浏览对象类型的实例数据
result = skill.run(
    mode="instances",
    kn_id="kn_01",
    object_type="orders",            # 对象类型名称或 ID
    limit=20,
)
# {"data": [{...}, ...], "total_count": 1200, "has_more": true, "object_type_schema": {...}}
```

### 4. QueryKnSkill -- 查询知识网络

语义搜索、实例查询和子图查询。

```python
from kweaver.skills import QueryKnSkill

skill = QueryKnSkill(client=client)

# 模式 1: search -- 语义搜索
result = skill.run(mode="search", kn_id="kn_01", query="华东地区库存不足的产品")
# {"data": [{"concept_type": "...", "concept_name": "...", ...}], "summary": "找到 5 个相关概念"}

# 模式 2: instances -- 条件查询
result = skill.run(
    mode="instances",
    kn_id="kn_01",
    object_type="products",
    conditions={"field": "stock", "operation": "lt", "value": 100},
    limit=50,
)
# {"data": [{...}], "summary": "查询到 23 条记录"}

# 模式 3: subgraph -- 子图查询
result = skill.run(
    mode="subgraph",
    kn_id="kn_01",
    start_object="orders",
    start_condition={"field": "status", "operation": "eq", "value": "pending"},
    path=["products", "suppliers"],
)
```

### 5. DiscoverAgentsSkill -- 发现 Agent

列出平台上的 Decision Agent 及其详情。

```python
from kweaver.skills import DiscoverAgentsSkill

skill = DiscoverAgentsSkill(client=client)

# 模式 1: list -- 列出 Agent
result = skill.run(mode="list")
# {"agents": [{"id": "...", "name": "供应链助手", "description": "...", "status": "published", ...}]}

result = skill.run(mode="list", keyword="供应链", status="published")

# 模式 2: detail -- Agent 详情
result = skill.run(mode="detail", agent_id="agent_01")
# 或按名称查找
result = skill.run(mode="detail", agent_name="供应链助手")
# {
#     "agent": {
#         "name": "供应链助手",
#         "description": "...",
#         "knowledge_networks": [{"id": "kn_01", "name": "供应链"}],
#         "prompts": {"system_prompt_preview": "..."},
#         "capabilities": [...],
#     }
# }
```

### 6. ChatAgentSkill -- 与 Agent 对话

向 Decision Agent 发送消息并获取回复。

```python
from kweaver.skills import ChatAgentSkill

skill = ChatAgentSkill(client=client)

# 模式 1: ask -- 发送消息（自动创建会话）
result = skill.run(
    mode="ask",
    agent_id="agent_01",             # 或 agent_name="供应链助手"
    question="华东仓库库存情况如何？",
)
# {
#     "answer": "华东仓库当前库存充足，共有1200件...",
#     "conversation_id": "",          # 首次对话由后端分配
#     "references": [{"source": "库存表", "content": "1200件", "score": 0.95}]
# }

# 多轮对话：传入 conversation_id 保持上下文
result = skill.run(
    mode="ask",
    agent_id="agent_01",
    question="和上个月相比呢？",
    conversation_id=result["conversation_id"],
)

# 流式输出
result = skill.run(
    mode="ask",
    agent_id="agent_01",
    question="总结一下",
    stream=True,
)
```

## 直接使用 SDK 资源

除了 Skill，也可以直接调用底层资源 API：

```python
# 知识网络
kns = client.knowledge_networks.list()
kn = client.knowledge_networks.get("kn_01")

# 对象类型 & 关系类型
ots = client.object_types.list("kn_01")
rts = client.relation_types.list("kn_01")

# 查询
result = client.query.semantic_search(kn_id="kn_01", query="库存不足")
result = client.query.instances("kn_01", "ot_01", limit=10)

# Agent
agents = client.agents.list(status="published")
agent = client.agents.get("agent_01")

# 对话
conv = client.conversations.create("agent_01")
reply = client.conversations.send_message(
    conv.id, "你好", agent_id="agent_01",
)
```

## 错误处理

所有 Skill 自动捕获错误并返回 `{"error": True, "message": "..."}` 格式。

直接使用资源 API 时，会抛出具体异常：

```python
from kweaver import ADPError, AuthenticationError, NotFoundError, ServerError

try:
    agent = client.agents.get("not_exist")
except NotFoundError:
    print("Agent 不存在")
except AuthenticationError:
    print("Token 已过期")
except ServerError as e:
    print(f"服务端异常: {e.message} (trace: {e.trace_id})")
except ADPError as e:
    print(f"其他错误: {e.message}")
```

## 测试

```bash
# 单元测试 + 集成测试（默认）
pytest

# E2E 测试（需要配置 ~/.env.secrets）
pytest tests/e2e/ --run-destructive

# E2E 所需环境变量（写入 ~/.env.secrets）:
# export ADP_BASE_URL="https://your-adp-instance.com"
# export ADP_USERNAME="user@example.com"      # 自动刷新 Token
# export ADP_PASSWORD="your_password"
# export ADP_BUSINESS_DOMAIN="bd_public"
```

E2E 测试会自动通过 Playwright 登录 ADP 获取新 Token，无需手动更新。

## 项目结构

```
src/kweaver/
  _client.py              # ADPClient 入口
  _http.py                # HTTP 传输层
  _auth.py                # Token / OAuth2 认证
  _errors.py              # 异常类型
  types.py                # Pydantic 数据模型
  resources/              # 底层资源 API
    agents.py             #   Agent 列表、详情
    conversations.py      #   对话（chat/completion）
    knowledge_networks.py #   知识网络 CRUD
    object_types.py       #   对象类型
    relation_types.py     #   关系类型
    datasources.py        #   数据源
    dataviews.py          #   数据视图
    query.py              #   查询（语义搜索、实例、子图）
  skills/                 # 高层 Skill（面向 AI Agent）
    connect_db.py         #   ConnectDbSkill
    build_kn.py           #   BuildKnSkill
    load_kn_context.py    #   LoadKnContextSkill
    query_kn.py           #   QueryKnSkill
    discover_agents.py    #   DiscoverAgentsSkill
    chat_agent.py         #   ChatAgentSkill
```

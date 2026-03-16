# KWeaver SDK

Give AI agents (Claude Code, GPT, custom agents, etc.) access to KWeaver knowledge networks and Decision Agents via the `kweaver` CLI. Also provides Python and TypeScript SDKs for programmatic integration.

[中文文档](README.zh.md)

## Installation

### TypeScript CLI (recommended — includes interactive agent chat TUI)

```bash
npm install -g kweaver-sdk
```

Requires Node.js 22+. After installation, use the `kweaver` command.

### TypeScript SDK (programmatic)

```bash
npm install kweaver-sdk
```

```typescript
import { KWeaverClient } from "kweaver-sdk";

// Zero-config: reads credentials saved by `kweaver auth login`
const client = new KWeaverClient();

// Or pass credentials explicitly
const client = new KWeaverClient({
  baseUrl: "https://your-kweaver.com",
  accessToken: "your-token",
});

const kns   = await client.knowledgeNetworks.list();
const reply = await client.agents.chat("agent-id", "Hello");
console.log(reply.text);
```

### Python CLI (alternative — for testing or Node-free environments)

```bash
pip install kweaver-sdk[cli]
```

Requires Python >= 3.10. After installation, use the same `kweaver` command.

### Python SDK (programmatic)

```bash
pip install kweaver-sdk
```

```python
from kweaver import KWeaverClient, ConfigAuth

client = KWeaverClient(auth=ConfigAuth(), business_domain="bd_public")
kns = client.knowledge_networks.list()
```

## Overview

| Entry point | Install | Purpose |
|-------------|---------|---------|
| **TS CLI** | `npm install -g kweaver-sdk` | Primary CLI with Ink TUI and streaming agent chat |
| **TS SDK** | `npm install kweaver-sdk` | Programmatic API — `import { KWeaverClient } from "kweaver-sdk"` |
| **Python CLI** | `pip install kweaver-sdk[cli]` | Alternative CLI, feature-parity with TS CLI |
| **Python SDK** | `pip install kweaver-sdk` | Programmatic API — `from kweaver import KWeaverClient` |

Both CLIs share the same command structure (`kweaver auth`, `kweaver bkn`, `kweaver agent`, `kweaver context-loader`, …) and credentials stored in `~/.kweaver/`.

## Authentication

```bash
kweaver auth login https://your-kweaver-instance.com
kweaver auth login https://your-kweaver-instance.com --alias prod
```

Or use environment variables: `KWEAVER_BASE_URL`, `KWEAVER_BUSINESS_DOMAIN`, `KWEAVER_TOKEN`.

## TypeScript SDK Usage

```typescript
import { KWeaverClient } from "kweaver-sdk";

const client = new KWeaverClient();   // reads ~/.kweaver/ credentials

// Knowledge networks
const kns = await client.knowledgeNetworks.list({ limit: 10 });
const ots = await client.knowledgeNetworks.listObjectTypes("kn-id");
const rts = await client.knowledgeNetworks.listRelationTypes("kn-id");

// Agent chat (single-shot)
const reply = await client.agents.chat("agent-id", "Hello");
console.log(reply.text, reply.conversationId);

// Agent chat (streaming)
await client.agents.stream("agent-id", "Hello", {
  onTextDelta: (chunk) => process.stdout.write(chunk),
});

// BKN engine — instance queries, subgraph, action execution
const instances = await client.bkn.queryInstances("kn-id", "ot-id", { limit: 20 });
const graph     = await client.bkn.querySubgraph("kn-id", { /* path spec */ });
await client.bkn.executeAction("kn-id", "at-id", { /* params */ });
const logs      = await client.bkn.listActionLogs("kn-id");

// Context Loader (semantic search over a knowledge network)
const cl      = client.contextLoader(mcpUrl, "kn-id");
const results = await cl.search({ query: "hypertension treatment" });
```

## Python SDK Usage

```python
from kweaver import KWeaverClient, ConfigAuth

client = KWeaverClient(auth=ConfigAuth())   # reads ~/.kweaver/ credentials

# Knowledge networks
kns = client.knowledge_networks.list()
ots = client.object_types.list("kn-id")

# Agent chat
conv = client.conversations.create("agent-id")
msg  = conv.send("Hello")
print(msg.text)

# BKN engine
instances = client.query.instances("kn-id", "ot-id", limit=20)
result    = client.action_types.execute("kn-id", "at-id", params={})
```

## CLI Quick Reference

```bash
kweaver auth login/status/list/use/delete/logout
kweaver token
kweaver bkn list/get/stats/export/create/update/delete
kweaver bkn object-type list/query/properties
kweaver bkn relation-type list
kweaver bkn action-type list/query/execute
kweaver bkn subgraph
kweaver bkn action-execution get
kweaver bkn action-log list/get/cancel
kweaver agent list/chat/sessions/history
kweaver context-loader config set/use/list/show
kweaver context-loader kn-search/query-object-instance/...
kweaver call <path> [-X METHOD] [-d BODY] [-H header] [-bd domain]
```

Python CLI also provides: `kweaver ds` (data sources), `kweaver query` (semantic search, instances, subgraph), `kweaver action` (orchestration).

## Repository Structure (Monorepo)

```
kweaver-sdk/
├── packages/
│   ├── python/                  # Python SDK + CLI
│   │   ├── src/kweaver/
│   │   │   ├── _client.py       # KWeaverClient
│   │   │   ├── resources/       # knowledge_networks, agents, …
│   │   │   └── cli/             # kweaver commands
│   │   └── tests/
│   └── typescript/              # TypeScript SDK + CLI
│       ├── src/
│       │   ├── client.ts        # KWeaverClient
│       │   ├── resources/       # knowledge-networks, agents, bkn, …
│       │   ├── api/             # low-level HTTP functions
│       │   └── commands/        # CLI command implementations
│       └── test/
├── skills/kweaver-core/         # AI agent skill (SKILL.md)
├── docs/
├── README.md                    # English (this file)
└── README.zh.md                 # 中文
```

## Development & Testing

```bash
# Python
make -C packages/python test

# TypeScript
make -C packages/typescript test
```

## Using with AI Agents

```bash
npx skills add kweaver-ai/kweaver-sdk --skill kweaver-core
```

See [skills/kweaver-core/SKILL.md](skills/kweaver-core/SKILL.md) for details.

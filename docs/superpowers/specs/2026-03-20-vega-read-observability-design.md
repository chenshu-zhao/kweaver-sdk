# Vega Read Operations & Observability Design

## Overview

Enhance kweaver-sdk (Python + TypeScript) with comprehensive read operations and observability capabilities for the Vega data management platform. All Vega resources are accessed through a `client.vega.*` namespace, and CLI commands live under `kweaver vega *`.

## Target Users

- **Platform operators** — daily health checks, fault diagnosis, capacity monitoring
- **Data engineers/developers** — programmatic data querying, metadata management
- **AI Agents** — tool-based data discovery and querying (via CLI + JSON output)

## Architecture

Vega capabilities are added as an extension within kweaver-sdk, reusing existing Auth, HTTP, and CLI infrastructure. A single `vega_url` configuration points to vega-backend (unified entry point for all Vega services).

```
KWeaverClient
├── agents               (existing)
├── knowledge_networks   (existing)
├── query                (existing)
└── vega                 (new — VegaNamespace)
    ├── catalogs         (CatalogsResource)
    ├── resources        (ResourcesResource)
    ├── connector_types  (ConnectorTypesResource)
    ├── metric_models    (MetricModelsResource)
    ├── event_models     (EventModelsResource)
    ├── trace_models     (TraceModelsResource)
    ├── data_views       (DataViewsResource)
    ├── data_dicts       (DataDictsResource)
    ├── objective_models (ObjectiveModelsResource)
    ├── query            (VegaQueryResource)
    ├── tasks            (TasksResource — unified: discover/metric/event)
    └── health / stats / inspect (methods on VegaNamespace)
```

### VegaNamespace Class

The `vega` attribute on `KWeaverClient` is a `VegaNamespace` instance that owns a **separate `HttpClient`** pointing at `vega_url`. This is necessary because Vega services use a different base URL than the main KWeaver platform.

```python
# Python
class VegaNamespace:
    """Namespace for all Vega resources. Owns its own HttpClient."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http
        self.catalogs = VegaCatalogsResource(http)
        self.resources = VegaResourcesResource(http)
        self.connector_types = VegaConnectorTypesResource(http)
        self.metric_models = VegaMetricModelsResource(http)
        self.event_models = VegaEventModelsResource(http)
        self.trace_models = VegaTraceModelsResource(http)
        self.data_views = VegaDataViewsResource(http)
        self.data_dicts = VegaDataDictsResource(http)
        self.objective_models = VegaObjectiveModelsResource(http)
        self.query = VegaQueryResource(http)
        self.tasks = VegaTasksResource(http)

    def health(self) -> VegaServerInfo: ...
    def stats(self) -> VegaPlatformStats: ...
    def inspect(self, full: bool = False) -> VegaInspectReport: ...
```

```typescript
// TypeScript — uses VegaContext (parallel to ClientContext)
interface VegaContext {
  base(): { baseUrl: string; accessToken: string; businessDomain: string };
}
```

### Configuration

```python
# Explicit — vega_url is optional, vega features unavailable if not set
client = KWeaverClient(
    base_url="https://kweaver.example.com",
    token="...",
    vega_url="http://vega-backend:13014",
)
# client.vega is available

# Without vega_url — client.vega raises ValueError("vega_url not configured")
client = KWeaverClient(base_url="...", token="...")
client.vega  # → ValueError

# Environment variable
# KWEAVER_VEGA_URL=http://vega-backend:13014

# ~/.kweaver/<platform>/config.json
# { "vega_url": "http://vega-backend:13014" }

# ConfigAuth — reads vega_url from stored config
client = KWeaverClient(auth=ConfigAuth())
```

**Auth model**: Vega uses the same Hydra OAuth tokens as KWeaver. The separate `HttpClient` for vega reuses the same `AuthProvider` instance but with a different `base_url`.

### CLI helper

`make_client()` in CLI is extended to accept `--vega-url` and read `KWEAVER_VEGA_URL`. No separate `make_vega_client()` needed.

## Type Definitions

### Python (Pydantic models in `types.py`)

```python
# ── Vega entity types ────────────────────────────────────────────────

class VegaServerInfo(BaseModel):
    server_name: str
    server_version: str
    language: str
    go_version: str
    go_arch: str

class VegaCatalog(BaseModel):
    id: str
    name: str
    type: str                          # "physical" | "logical"
    connector_type: str                # "mysql" | "opensearch" | ...
    status: str                        # "active" | "disabled"
    health_status: str | None = None   # "healthy" | "degraded" | "unhealthy" | "offline" | "disabled"
    health_check_time: str | None = None
    health_error: str | None = None
    description: str | None = None
    config: dict[str, Any] | None = None

class VegaResource(BaseModel):
    id: str
    name: str
    catalog_id: str
    category: str              # "table" | "index" | "dataset" | "metric" | "topic" | "file" | "fileset" | "api" | "logicview"
    status: str                # "active" | "disabled" | "deprecated" | "stale"
    database: str | None = None
    schema_name: str | None = None
    properties: list[dict[str, Any]] = []
    description: str | None = None

class VegaConnectorType(BaseModel):
    type: str
    name: str
    enabled: bool = True
    description: str | None = None

class VegaMetricModel(BaseModel):
    id: str
    name: str
    group_id: str | None = None
    data_connection_id: str | None = None
    status: str | None = None
    description: str | None = None

class VegaEventModel(BaseModel):
    id: str
    name: str
    status: str | None = None
    level: str | None = None
    description: str | None = None

class VegaTraceModel(BaseModel):
    id: str
    name: str
    status: str | None = None
    description: str | None = None

class VegaDataView(BaseModel):
    id: str
    name: str
    group_id: str | None = None
    status: str | None = None
    description: str | None = None

class VegaDataDict(BaseModel):
    id: str
    name: str
    description: str | None = None

class VegaDataDictItem(BaseModel):
    id: str
    dict_id: str
    key: str
    value: str
    sort_order: int = 0

class VegaObjectiveModel(BaseModel):
    id: str
    name: str
    description: str | None = None

class VegaDiscoverTask(BaseModel):
    id: str
    catalog_id: str
    status: str             # "pending" | "running" | "completed" | "failed"
    progress: float | None = None
    error: str | None = None
    created_at: str | None = None
    completed_at: str | None = None

class VegaMetricTask(BaseModel):
    id: str
    status: str
    plan_time: str | None = None

class VegaSpan(BaseModel):
    span_id: str
    trace_id: str
    parent_span_id: str | None = None
    operation_name: str | None = None
    service_name: str | None = None
    duration_ms: float | None = None
    start_time: str | None = None
    status: str | None = None
    attributes: dict[str, Any] = {}

# ── Vega result types ────────────────────────────────────────────────

class VegaQueryResult(BaseModel):
    entries: list[dict[str, Any]] = []
    total_count: int | None = None

class VegaDslResult(BaseModel):
    """Result from DSL search."""
    hits: list[dict[str, Any]] = []
    total: int = 0
    took_ms: int | None = None
    scroll_id: str | None = None

class VegaPromqlResult(BaseModel):
    status: str = "success"
    result_type: str | None = None   # "matrix" | "vector" | "scalar"
    result: list[dict[str, Any]] = []

class VegaHealthReport(BaseModel):
    catalogs: list[VegaCatalog] = []
    healthy_count: int = 0
    degraded_count: int = 0
    unhealthy_count: int = 0
    offline_count: int = 0

class VegaPlatformStats(BaseModel):
    catalogs_total: int = 0
    resources_by_category: dict[str, int] = {}
    models: dict[str, int] = {}        # {metric: 5, event: 3, trace: 2, ...}
    tasks_summary: dict[str, int] = {}  # {running: 2, pending: 1, ...}

class VegaInspectReport(BaseModel):
    server_info: VegaServerInfo
    catalog_health: VegaHealthReport
    resource_summary: dict[str, int] = {}
    active_tasks: list[VegaDiscoverTask] = []
```

### TypeScript (interfaces)

TypeScript mirrors the same types as interfaces in `types/vega.ts`.

## REST Endpoint Mapping

Every SDK method maps to a concrete HTTP call. Base paths by service:

- **vega-backend**: `/api/vega-backend/v1`
- **mdl-data-model**: `/api/mdl-data-model/v1`
- **mdl-uniquery**: `/api/mdl-uniquery/v1`

Since all requests will route through vega-backend as a unified entry point, the SDK always sends to `vega_url`. Vega-backend will proxy requests to other services internally.

### Catalogs (vega-backend)

| SDK Method | HTTP | Endpoint |
|-----------|------|----------|
| `catalogs.list()` | `GET` | `/api/vega-backend/v1/catalogs` |
| `catalogs.get(ids)` | `GET` | `/api/vega-backend/v1/catalogs/{ids}` |
| `catalogs.health_status(ids)` | `GET` | `/api/vega-backend/v1/catalogs/{ids}/health-status` |
| `catalogs.health_report()` | composite | `list()` → `health_status()` for all |
| `catalogs.test_connection(id)` | `POST` | `/api/vega-backend/v1/catalogs/{id}/test-connection` |
| `catalogs.discover(id)` | `POST` | `/api/vega-backend/v1/catalogs/{id}/discover` |
| `catalogs.resources(ids)` | `GET` | `/api/vega-backend/v1/catalogs/{ids}/resources` |

### Resources (vega-backend)

| SDK Method | HTTP | Endpoint |
|-----------|------|----------|
| `resources.list()` | `GET` | `/api/vega-backend/v1/resources` |
| `resources.get(ids)` | `GET` | `/api/vega-backend/v1/resources/{ids}` |
| `resources.data(id, body)` | `POST` | `/api/vega-backend/v1/resources/{id}/data` |

### Connector Types (vega-backend)

| SDK Method | HTTP | Endpoint |
|-----------|------|----------|
| `connector_types.list()` | `GET` | `/api/vega-backend/v1/connector-types` |
| `connector_types.get(type)` | `GET` | `/api/vega-backend/v1/connector-types/{type}` |

### Discover Tasks (vega-backend)

| SDK Method | HTTP | Endpoint |
|-----------|------|----------|
| `tasks.list_discover()` | `GET` | `/api/vega-backend/v1/discover-tasks` |
| `tasks.get_discover(id)` | `GET` | `/api/vega-backend/v1/discover-tasks/{id}` |
| `tasks.wait_discover(id)` | composite | poll `get_discover()` until terminal |

### Query Execute (vega-backend)

| SDK Method | HTTP | Endpoint |
|-----------|------|----------|
| `query.execute(body)` | `POST` | `/api/vega-backend/v1/query/execute` |

### Metric Models (mdl-data-model)

| SDK Method | HTTP | Endpoint |
|-----------|------|----------|
| `metric_models.list()` | `GET` | `/api/mdl-data-model/v1/metric-models` |
| `metric_models.get(ids)` | `GET` | `/api/mdl-data-model/v1/metric-models/{ids}` |
| `metric_models.fields(ids)` | `GET` | `/api/mdl-data-model/v1/metric-models/{ids}/fields` |
| `metric_models.order_fields(ids)` | `GET` | `/api/mdl-data-model/v1/metric-models/{ids}/order_fields` |

### Metric Tasks (mdl-data-model)

| SDK Method | HTTP | Endpoint |
|-----------|------|----------|
| `tasks.get_metric(task_id)` | `GET` | `/api/mdl-data-model/v1/metric-tasks/{task_id}` |

### Event Models (mdl-data-model)

| SDK Method | HTTP | Endpoint |
|-----------|------|----------|
| `event_models.list()` | `GET` | `/api/mdl-data-model/v1/event-models` |
| `event_models.get(ids)` | `GET` | `/api/mdl-data-model/v1/event-models/{ids}` |
| `event_models.levels()` | `GET` | `/api/mdl-data-model/v1/event-level` |

### Trace Models (mdl-data-model)

| SDK Method | HTTP | Endpoint |
|-----------|------|----------|
| `trace_models.list()` | `GET` | `/api/mdl-data-model/v1/trace-models` |
| `trace_models.get(ids)` | `GET` | `/api/mdl-data-model/v1/trace-models/{ids}` |
| `trace_models.field_info(ids)` | `GET` | `/api/mdl-data-model/v1/trace-models/{ids}/field-info` |

### Data Views (mdl-data-model)

| SDK Method | HTTP | Endpoint |
|-----------|------|----------|
| `data_views.list()` | `GET` | `/api/mdl-data-model/v1/data-views` |
| `data_views.get(ids)` | `GET` | `/api/mdl-data-model/v1/data-views/{ids}` |
| `data_views.groups()` | `GET` | `/api/mdl-data-model/v1/data-view-groups` |

### Data Dicts (mdl-data-model)

| SDK Method | HTTP | Endpoint |
|-----------|------|----------|
| `data_dicts.list()` | `GET` | `/api/mdl-data-model/v1/data-dicts` |
| `data_dicts.get(id)` | `GET` | `/api/mdl-data-model/v1/data-dicts/{id}` |
| `data_dicts.items(id)` | `GET` | `/api/mdl-data-model/v1/data-dicts/{id}/items` |

### Objective Models (mdl-data-model)

| SDK Method | HTTP | Endpoint |
|-----------|------|----------|
| `objective_models.list()` | `GET` | `/api/mdl-data-model/v1/objective-models` |
| `objective_models.get(ids)` | `GET` | `/api/mdl-data-model/v1/objective-models/{ids}` |

### DSL Query (mdl-uniquery)

| SDK Method | HTTP | Endpoint |
|-----------|------|----------|
| `query.dsl(index, body)` | `POST` | `/api/mdl-uniquery/v1/dsl/{index}/_search` |
| `query.dsl(body)` | `POST` | `/api/mdl-uniquery/v1/dsl/_search` |
| `query.dsl_count(index, body)` | `POST` | `/api/mdl-uniquery/v1/dsl/{index}/_count` |
| `query.dsl_scroll(body)` | `POST` | `/api/mdl-uniquery/v1/dsl/_search/scroll` |

### PromQL Query (mdl-uniquery)

Note: PromQL endpoints require `Content-Type: application/x-www-form-urlencoded`.

| SDK Method | HTTP | Endpoint |
|-----------|------|----------|
| `query.promql(query, start, end, step)` | `POST` | `/api/mdl-uniquery/v1/promql/query_range` |
| `query.promql_instant(query)` | `POST` | `/api/mdl-uniquery/v1/promql/query` |
| `query.promql_series(match)` | `POST` | `/api/mdl-uniquery/v1/promql/series` |

### Metric Model Data Query (mdl-uniquery)

| SDK Method | HTTP | Endpoint |
|-----------|------|----------|
| `query.metric_model(ids, body)` | `POST` | `/api/mdl-uniquery/v1/metric-models/{ids}` |
| `query.metric_model_fields(ids)` | `GET` | `/api/mdl-uniquery/v1/metric-models/{ids}/fields` |
| `query.metric_model_labels(ids)` | `GET` | `/api/mdl-uniquery/v1/metric-models/{ids}/labels` |

### Data View Query (mdl-uniquery)

| SDK Method | HTTP | Endpoint |
|-----------|------|----------|
| `query.data_view(ids, body)` | `POST` | `/api/mdl-uniquery/v1/data-views/{ids}` |

### Trace Query (mdl-uniquery)

| SDK Method | HTTP | Endpoint |
|-----------|------|----------|
| `query.trace(tm_id, trace_id)` | `POST` | `/api/mdl-uniquery/v1/trace-models/{tm_id}/traces/{trace_id}` |
| `trace_models.spans(tm_id, trace_id)` | `POST` | `/api/mdl-uniquery/v1/trace-models/{tm_id}/traces/{trace_id}/spans` |
| `trace_models.span(tm_id, trace_id, span_id)` | `GET` | `/api/mdl-uniquery/v1/trace-models/{tm_id}/traces/{trace_id}/spans/{span_id}` |
| `trace_models.related_logs(tm_id, trace_id, span_id)` | `POST` | `/api/mdl-uniquery/v1/trace-models/{tm_id}/traces/{trace_id}/spans/{span_id}/related-logs` |

### Event Query (mdl-uniquery)

| SDK Method | HTTP | Endpoint |
|-----------|------|----------|
| `query.events(body)` | `POST` | `/api/mdl-uniquery/v1/events` |
| `query.event(em_id, event_id)` | `GET` | `/api/mdl-uniquery/v1/event-models/{em_id}/events/{event_id}` |

### Health (vega-backend)

| SDK Method | HTTP | Endpoint |
|-----------|------|----------|
| `health()` | `GET` | `/health` |

## SDK Resource APIs

### Catalogs

```python
client.vega.catalogs.list(status="healthy", limit=20, offset=0)
client.vega.catalogs.get("cat-1")
client.vega.catalogs.health_status(["cat-1", "cat-2"])
client.vega.catalogs.health_report()   # composite: list all → batch health_status → aggregate into VegaHealthReport
client.vega.catalogs.test_connection("cat-1")
client.vega.catalogs.discover("cat-1")
client.vega.catalogs.resources("cat-1", category="table")
```

### Resources

```python
client.vega.resources.list(catalog_id="cat-1", category="table", status="active", limit=20, offset=0)
client.vega.resources.get("res-1")
client.vega.resources.data("res-1", body={...})  # query resource data
```

### Connector Types

```python
client.vega.connector_types.list()
client.vega.connector_types.get("mysql")
```

### Metric Models

```python
client.vega.metric_models.list(limit=20, offset=0)
client.vega.metric_models.get("mm-1")
client.vega.metric_models.fields("mm-1")
client.vega.metric_models.order_fields("mm-1")
```

### Event Models

```python
client.vega.event_models.list(limit=20, offset=0)
client.vega.event_models.get("em-1")
client.vega.event_models.levels()
```

### Trace Models

```python
client.vega.trace_models.list(limit=20, offset=0)
client.vega.trace_models.get("tm-1")
client.vega.trace_models.field_info("tm-1")
client.vega.trace_models.spans("tm-1", "trace-id", body={...})
client.vega.trace_models.span("tm-1", "trace-id", "span-id")
client.vega.trace_models.related_logs("tm-1", "trace-id", "span-id")
```

### Data Views

```python
client.vega.data_views.list(limit=20, offset=0)
client.vega.data_views.get("dv-1")
client.vega.data_views.groups()
```

### Data Dicts

```python
client.vega.data_dicts.list(limit=20, offset=0)
client.vega.data_dicts.get("dd-1")
client.vega.data_dicts.items("dd-1", limit=20, offset=0)
```

### Objective Models

```python
client.vega.objective_models.list(limit=20, offset=0)
client.vega.objective_models.get("om-1")
```

### Query

```python
# DSL (OpenSearch-compatible)
client.vega.query.dsl(index="my-index", body={...})
client.vega.query.dsl(body={...})              # global search, no index
client.vega.query.dsl_count(index="my-index", body={...})
client.vega.query.dsl_scroll(scroll_id="...")

# PromQL
client.vega.query.promql(query="up", start="2026-03-20T00:00:00Z", end="2026-03-20T01:00:00Z", step="15s")
client.vega.query.promql_instant(query="up")
client.vega.query.promql_series(match=["up"])

# Metric model data
client.vega.query.metric_model(ids="mm-1", body={...})
client.vega.query.metric_model_fields(ids="mm-1")
client.vega.query.metric_model_labels(ids="mm-1")

# Data view query
client.vega.query.data_view(ids="dv-1", body={...})

# Trace
client.vega.query.trace(trace_model_id="tm-1", trace_id="abc")

# Events
client.vega.query.events(body={...})
client.vega.query.event(event_model_id="em-1", event_id="evt-1")

# Execute (vega-backend unified query)
client.vega.query.execute(tables=[...], filter_condition={...}, output_fields=[...], sort=[...], offset=0, limit=20)
```

### Tasks (unified namespace)

SDK uses a single `tasks` resource with type-prefixed methods, matching the CLI's unified `task` command:

```python
# Discover tasks
client.vega.tasks.list_discover(status="running")
client.vega.tasks.get_discover("task-1")
client.vega.tasks.wait_discover("task-1", timeout=300)  # poll until terminal state

# Metric tasks
client.vega.tasks.get_metric("task-1")

# Event tasks — status update only (no list endpoint)
```

### Health, Stats, Inspect

```python
# Service health
info = client.vega.health()
# → VegaServerInfo(server_name="VEGA Manager", server_version="1.0.0", ...)

# Platform statistics — composite: calls list on catalogs, resources, models, tasks
stats = client.vega.stats()
# → VegaPlatformStats(catalogs_total=6, resources_by_category={table: 42, ...}, ...)

# Aggregated inspection — composite: health + stats + active tasks
# Parallelized internally. Returns partial results if a sub-call fails.
report = client.vega.inspect(full=False)
# → VegaInspectReport(server_info=..., catalog_health=..., ...)
```

## CLI Layer

All commands under `kweaver vega`. Default output is **Markdown**. Use `--format json` for programmatic consumption, `--format yaml` as alternative. All list commands support `--limit` and `--offset` for pagination.

### Metadata

```bash
kweaver vega catalog list [--status healthy|degraded|unhealthy|offline|disabled] [--limit 20]
kweaver vega catalog get <id>
kweaver vega catalog health [<id...>] [--all]
kweaver vega catalog test-connection <id>
kweaver vega catalog discover <id> [--wait]
kweaver vega catalog resources <id> [--category table|index|...]

kweaver vega resource list [--catalog-id X] [--category table] [--status active] [--limit 20]
kweaver vega resource get <id>
kweaver vega resource data <id> -d '<body>'

kweaver vega connector-type list
kweaver vega connector-type get <type>
```

### Data Models

```bash
kweaver vega metric-model list [--limit 20]
kweaver vega metric-model get <id>
kweaver vega metric-model fields <id>

kweaver vega event-model list [--limit 20]
kweaver vega event-model get <id>
kweaver vega event-model levels

kweaver vega trace-model list [--limit 20]
kweaver vega trace-model get <id>
kweaver vega trace-model fields <id>

kweaver vega data-view list [--limit 20]
kweaver vega data-view get <id>
kweaver vega data-view groups

kweaver vega data-dict list [--limit 20]
kweaver vega data-dict get <id>
kweaver vega data-dict items <id>

kweaver vega objective-model list [--limit 20]
kweaver vega objective-model get <id>
```

### Query

```bash
kweaver vega query dsl [<index>] -d '<body>'
kweaver vega query dsl-count [<index>] -d '<body>'
kweaver vega query promql '<expr>' --start X --end Y --step 15s
kweaver vega query promql-instant '<expr>'
kweaver vega query promql-series --match '<selector>'
kweaver vega query metric-model <ids> -d '<body>'
kweaver vega query data-view <ids> -d '<body>'
kweaver vega query trace <trace-model-id> <trace-id>
kweaver vega query events -d '<body>'
kweaver vega query event <event-model-id> <event-id>
kweaver vega query execute -d '<request-body>'
kweaver vega query bench [<index>] -d '<body>' --count 10
```

Note: `query bench` is CLI-only — it's an interactive benchmarking tool (runs N iterations, reports p50/p95/p99), not an SDK-level abstraction.

### Observability — Status

```bash
kweaver vega health
kweaver vega stats
kweaver vega inspect [--full]

kweaver vega task list [--type discover|metric|event] [--status running|pending|completed|failed]
kweaver vega task get <task-id> [--type discover|metric]
```

### Observability — Diagnostics

```bash
kweaver vega trace show <trace-model-id> <trace-id>
kweaver vega trace spans <trace-model-id> <trace-id>
kweaver vega trace span <trace-model-id> <trace-id> <span-id>
kweaver vega trace related-logs <trace-model-id> <trace-id> <span-id>
```

### Output Format

All commands support `--format md|json|yaml` (default: `md`).

`kweaver vega inspect` example output:

```markdown
## Service

- VEGA Manager v1.0.0 (go1.22.0 linux/amd64)

## Catalog Health

| Name       | Type     | Connector | Status   | Last Check          |
|------------|----------|-----------|----------|---------------------|
| prod-mysql | physical | mysql     | healthy  | 2026-03-20 10:30:00 |
| staging-os | physical | opensearch| degraded | 2026-03-20 10:28:12 |

## Resources Summary

| Category | Count |
|----------|-------|
| table    | 42    |
| index    | 15    |
| dataset  | 8     |
| metric   | 3     |
| total    | 68    |

## Active Tasks

- discover cat-1 — running (60%)
- metric-sync mm-3 — pending
```

## Error Handling

Vega-specific errors extend the existing SDK error hierarchy:

```python
class VegaError(KWeaverError):
    """Base for all Vega errors."""

class VegaConnectionError(VegaError):
    """Catalog connection test or health check failure."""
    catalog_id: str
    connector_type: str

class VegaQueryError(VegaError):
    """Query execution failure (DSL, PromQL, etc.)."""
    query_type: str  # "dsl" | "promql" | "execute"

class VegaDiscoverError(VegaError):
    """Resource discovery failure."""
    catalog_id: str
    task_id: str
```

HTTP errors from vega-backend follow the same `rest.HTTPError` pattern with error codes. The SDK maps vega error codes (e.g., `VegaBackend.InvalidRequestHeader.ContentType`) to appropriate Python/TS exceptions.

## Project Structure

### Python

This introduces `resources/vega/` as a **sub-package** — a new pattern in the codebase. This is intentional: Vega has ~12 resource files, and keeping them flat in `resources/` alongside existing KWeaver resources would create namespace confusion. The `vega/` sub-package clearly scopes Vega-specific code.

```
packages/python/src/kweaver/
├── resources/vega/           # NEW sub-package
│   ├── __init__.py           # exports VegaNamespace
│   ├── catalogs.py
│   ├── resources.py
│   ├── connector_types.py
│   ├── metric_models.py
│   ├── event_models.py
│   ├── trace_models.py
│   ├── data_views.py
│   ├── data_dicts.py
│   ├── objective_models.py
│   ├── query.py
│   ├── tasks.py              # unified: discover + metric + event tasks
│   └── inspect.py            # health, stats, inspect logic
├── cli/vega/                 # NEW sub-package
│   ├── __init__.py
│   ├── main.py               # `kweaver vega` group
│   ├── catalog.py
│   ├── resource.py
│   ├── connector_type.py
│   ├── model.py              # metric/event/trace/objective/data-view
│   ├── data_dict.py
│   ├── query.py
│   ├── task.py
│   ├── trace.py
│   ├── inspect.py            # health, stats, inspect commands
│   └── formatters.py         # md/json/yaml output formatting
├── types.py                  # extended with Vega* types
└── _client.py                # extended with self.vega: VegaNamespace
```

### TypeScript

The existing TS SDK uses `resources/` for resource classes and `api/` for lower-level API functions. Vega follows the same split:

```
packages/typescript/src/
├── resources/vega/           # NEW sub-directory
│   ├── index.ts              # exports VegaNamespace
│   ├── catalogs.ts
│   ├── resources.ts
│   ├── connector-types.ts
│   ├── metric-models.ts
│   ├── event-models.ts
│   ├── trace-models.ts
│   ├── data-views.ts
│   ├── data-dicts.ts
│   ├── objective-models.ts
│   ├── query.ts
│   ├── tasks.ts
│   └── inspect.ts
├── api/vega/                 # NEW — low-level API functions
│   ├── catalogs.ts
│   ├── resources.ts
│   ├── query.ts
│   └── ...
├── commands/vega/            # NEW sub-directory
│   ├── index.ts
│   ├── catalog.ts
│   ├── resource.ts
│   ├── connector-type.ts
│   ├── model.ts
│   ├── data-dict.ts
│   ├── query.ts
│   ├── task.ts
│   ├── trace.ts
│   └── inspect.ts
├── types/vega.ts             # Vega type interfaces
└── client.ts                 # extended with vega: VegaNamespace
```

## Capability Matrix

| Domain | Capability | SDK | CLI |
|--------|-----------|-----|-----|
| **Metadata** | Catalog list/get/health/test/discover | `vega.catalogs.*` | `vega catalog *` |
| | Resource list/get/data | `vega.resources.*` | `vega resource *` |
| | Connector-Type list/get | `vega.connector_types.*` | `vega connector-type *` |
| **Models** | Metric-Model list/get/fields | `vega.metric_models.*` | `vega metric-model *` |
| | Event-Model list/get/levels | `vega.event_models.*` | `vega event-model *` |
| | Trace-Model list/get/fields/spans | `vega.trace_models.*` | `vega trace-model *` |
| | Data-View list/get/groups | `vega.data_views.*` | `vega data-view *` |
| | Data-Dict list/get/items | `vega.data_dicts.*` | `vega data-dict *` |
| | Objective-Model list/get | `vega.objective_models.*` | `vega objective-model *` |
| **Query** | DSL search/count/scroll | `vega.query.dsl*()` | `vega query dsl*` |
| | PromQL range/instant/series | `vega.query.promql*()` | `vega query promql*` |
| | Metric model data | `vega.query.metric_model()` | `vega query metric-model` |
| | Data view query | `vega.query.data_view()` | `vega query data-view` |
| | Trace query | `vega.query.trace()` | `vega query trace` |
| | Event query | `vega.query.events()` | `vega query events` |
| | Execute unified query | `vega.query.execute()` | `vega query execute` |
| **Observe-Status** | Catalog health report | `vega.catalogs.health_report()` | `vega catalog health --all` |
| | Discover task wait | `vega.tasks.wait_discover()` | `vega catalog discover --wait` |
| | Task monitoring | `vega.tasks.*()` | `vega task list/get` |
| | Service health | `vega.health()` | `vega health` |
| **Observe-Diag** | Query benchmark | — | `vega query bench` |
| | Trace spans/detail | `vega.trace_models.spans()` | `vega trace show/spans` |
| | Related logs | `vega.trace_models.related_logs()` | `vega trace related-logs` |
| | Platform stats | `vega.stats()` | `vega stats` |
| | Aggregated inspect | `vega.inspect()` | `vega inspect` |
| **Output** | Markdown / JSON / YAML | — | `--format md\|json\|yaml` |

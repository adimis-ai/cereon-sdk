# API Reference

Complete API documentation for Cereon SDK classes, methods, and utilities.

## Core Classes

### BaseCard

The abstract base class for all dashboard cards. Provides type-safe card definition and automatic route generation.

```python
from cereon_sdk import BaseCard, ChartCardRecord

class MyCard(BaseCard[ChartCardRecord]):
    kind: ClassVar[str] = "line"
    card_id: ClassVar[str] = "my_card"
    report_id: ClassVar[str] = "dashboard"
    route_prefix: ClassVar[str] = "/api/cards"
    response_model: ClassVar[Type[RecordType]] = ChartCardRecord
    transport: ClassVar[Literal["http", "websocket", "streaming-http"]] = "http"
```

#### Class Variables

| Variable | Type | Description | Required |
|----------|------|-------------|----------|
| `kind` | `str` | Card type identifier (e.g., "line", "bar", "table") | ✅ |
| `card_id` | `str` | Unique identifier for the card | ✅ |
| `report_id` | `str` | Report/dashboard identifier | ✅ |
| `route_prefix` | `str` | API route prefix | ✅ |
| `response_model` | `Type[RecordType]` | Pydantic response model class | ✅ |
| `transport` | `Literal` | Transport protocol ("http", "websocket", "streaming-http") | ✅ |

#### Methods

##### `handler(ctx: Optional[HandlerContext]) -> Union[List[RecordType], AsyncIterable[RecordType]]`

**Abstract method** that implements the card's data logic.

**Parameters:**
- `ctx` (Optional[HandlerContext]): Context containing request data, parameters, and metadata

**Returns:**
- For HTTP: `List[RecordType]` - List of card records
- For WebSocket/Streaming: `AsyncIterable[RecordType]` - Async generator yielding records

**Example:**
```python
@classmethod
async def handler(cls, ctx):
    params = ctx.get("params", {})
    data = await fetch_data(params)
    
    return [ChartCardRecord(
        kind=cls.kind,
        report_id=cls.report_id,
        card_id=cls.card_id,
        data=ChartCardData(data=data)
    )]
```

##### `as_route(app: Optional[FastAPI], **kwargs) -> FastAPI`

Registers the card as a FastAPI route.

**Parameters:**
- `app` (Optional[FastAPI]): FastAPI application instance
- `**kwargs`: Transport-specific configuration options

**HTTP Options:**
- `methods` (tuple): HTTP methods to support (default: `("GET",)`)

**WebSocket Options:**
- `heartbeat_ms` (int): WebSocket heartbeat interval (default: 30000)
- `ack_policy` (str): Acknowledgment policy - "auto" or "manual" (default: "auto")

**Streaming HTTP Options:**
- `format` (str): Stream format - "sse", "ndjson", "delimited", "json" (default: "ndjson")
- `delimiter` (str): Custom delimiter for delimited format (default: "\n")
- `media_type` (str): Response media type
- `stream_error_policy` (str): Error handling - "fail", "skip", "log" (default: "skip")

**Returns:** FastAPI application instance

**Example:**
```python
# Basic registration
MyCard(app).as_route(app=app)

# With options
MyCard(app).as_route(
    app=app,
    format="sse",
    heartbeat_ms=60000
)
```

## Data Models

### BaseCardRecord[T]

Generic base class for all card record types.

```python
class BaseCardRecord(BaseModel, Generic[T]):
    kind: str
    report_id: str  
    card_id: str
    data: Optional[T] = None
    meta: Optional[QueryMetadata] = None
```

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| `kind` | `str` | Card type identifier |
| `report_id` | `str` | Report identifier |
| `card_id` | `str` | Card identifier |
| `data` | `Optional[T]` | Typed payload data |
| `meta` | `Optional[QueryMetadata]` | Execution metadata |

#### Methods

##### `to_record() -> Dict[str, Any]`

Converts the record to a dictionary format for JSON serialization.

**Returns:** Dictionary representation of the record

### ChartCardRecord

Chart card record containing visualization data.

```python
class ChartCardRecord(BaseCardRecord[ChartCardData]):
    pass

class ChartCardData(BaseModel):
    data: List[Dict[str, Any]]
```

**Example:**
```python
record = ChartCardRecord(
    kind="line",
    report_id="dashboard",
    card_id="sales_chart",
    data=ChartCardData(data=[
        {"month": "Jan", "sales": 1000},
        {"month": "Feb", "sales": 1200}
    ])
)
```

### NumberCardRecord

Number/KPI card record with trend information.

```python
class NumberCardRecord(BaseCardRecord[NumberCardData]):
    kind: Literal["number"] = "number"
    meta: Optional[NumberCardMetadata] = None

class NumberCardData(BaseModel):
    value: float
    previousValue: Optional[float] = None
    trend: Optional[Literal["up", "down", "neutral"]] = None
    trendPercentage: Optional[float] = None
    label: Optional[str] = None

class NumberCardMetadata(QueryMetadata):
    unit: Optional[str] = None
    format: Optional[str] = None
```

**Example:**
```python
record = NumberCardRecord(
    kind="number",
    report_id="dashboard", 
    card_id="revenue_kpi",
    data=NumberCardData(
        value=125000.0,
        previousValue=118000.0,
        trend="up",
        trendPercentage=5.93,
        label="Monthly Revenue"
    ),
    meta=NumberCardMetadata(
        unit="USD",
        format="currency"
    )
)
```

### TableCardRecord

Table card record containing tabular data.

```python
class TableCardRecord(BaseCardRecord[TableCardData]):
    kind: Literal["table"] = "table"

class TableCardData(BaseModel):
    rows: List[Dict[str, Any]]
    columns: List[str]
    totalCount: Optional[int] = None
```

**Example:**
```python
record = TableCardRecord(
    kind="table",
    report_id="dashboard",
    card_id="users_table",
    data=TableCardData(
        rows=[
            {"id": 1, "name": "Alice", "email": "alice@example.com"},
            {"id": 2, "name": "Bob", "email": "bob@example.com"}
        ],
        columns=["id", "name", "email"],
        totalCount=2
    )
)
```

### MarkdownCardRecord

Markdown card record for rich text content.

```python
class MarkdownCardRecord(BaseCardRecord[MarkdownCardData]):
    kind: Literal["markdown"] = "markdown"

class MarkdownCardData(BaseModel):
    content: Optional[str] = None
    rawMarkdown: Optional[str] = None
    styles: Optional[str] = None
```

### HtmlCardRecord

HTML card record for custom HTML content.

```python
class HtmlCardRecord(BaseCardRecord[HtmlCardData]):
    kind: Literal["html"] = "html"

class HtmlCardData(BaseModel):
    content: Optional[str] = None
    rawHtml: Optional[str] = None
    styles: Optional[str] = None
```

### IframeCardRecord

Iframe card record for embedding external content.

```python
class IframeCardRecord(BaseCardRecord[IframeCardData]):
    kind: Literal["iframe"] = "iframe"

class IframeCardData(BaseModel):
    url: str
    title: Optional[str] = None
    width: Optional[Union[str, int]] = None
    height: Optional[Union[str, int]] = None
```

## Context Types

### HttpHandlerContext

Context provided to HTTP card handlers.

```python
class HttpHandlerContext(TypedDict):
    request: NotRequired[Request]  # FastAPI Request object
    params: NotRequired[Dict[str, Any]]  # Query parameters
    filters: NotRequired[Dict[str, Any]]  # Filter parameters
```

### WebSocketHandlerContext

Context provided to WebSocket card handlers.

```python
class WebSocketHandlerContext(TypedDict):
    websocket: NotRequired[WebSocket]  # FastAPI WebSocket object
    params: NotRequired[Dict[str, Any]]  # Connection parameters
    filters: NotRequired[Dict[str, Any]]  # Filter parameters
```

## Route Functions

### make_http_route_typed()

Creates a typed HTTP route for card endpoints.

```python
def make_http_route_typed(
    app: FastAPI,
    path: str,
    handler: Handler,
    *,
    response_model: Type[RecordType],
    methods: tuple = ("GET",)
) -> FastAPI
```

**Parameters:**
- `app`: FastAPI application
- `path`: Route path
- `handler`: Handler function
- `response_model`: Pydantic response model
- `methods`: Supported HTTP methods

### make_websocket_route_typed()

Creates a typed WebSocket route for real-time cards.

```python
def make_websocket_route_typed(
    app: FastAPI,
    path: str,
    handler: WebsocketHandler,
    *,
    response_model: Type[RecordType],
    heartbeat_ms: int = 30000,
    ack_policy: Literal["auto", "manual"] = "auto",
    stream_error_policy: Literal["fail", "skip", "log"] = "skip"
) -> FastAPI
```

### make_streaming_route_typed()

Creates a typed streaming HTTP route for live data feeds.

```python
def make_streaming_route_typed(
    app: FastAPI,
    path: str,
    handler: Handler,
    *,
    response_model: Type[RecordType],
    format: Literal["sse", "ndjson", "delimited", "json"] = "ndjson",
    delimiter: str = "\n",
    media_type: Optional[str] = None,
    packet_size: int = 1000,
    stream_error_policy: Literal["fail", "skip", "log"] = "skip",
    methods: tuple = ("GET",)
) -> FastAPI
```

## Utility Functions

### parse_http_params()

Parses HTTP request parameters from query string and body.

```python
async def parse_http_params(request: Request) -> Dict[str, Any]
```

**Parameters:**
- `request`: FastAPI Request object

**Returns:** Dictionary of parsed parameters

### parse_websocket_params()

Parses WebSocket connection parameters.

```python
async def parse_websocket_params(websocket: WebSocket) -> Dict[str, Any]
```

**Parameters:**
- `websocket`: FastAPI WebSocket object

**Returns:** Dictionary of parsed parameters

## Type Definitions

### RecordType

Type variable bound to BaseCardRecord for generic card definitions.

```python
RecordType = TypeVar("RecordType", bound=BaseCardRecord)
```

### Handler

Type alias for card handler functions.

```python
Handler = Callable[
    [Dict[str, Any]],
    Union[
        List[RecordType],
        Iterable[RecordType], 
        AsyncIterable[RecordType],
        Awaitable[Union[List[RecordType], Iterable[RecordType], AsyncIterable[RecordType]]]
    ]
]
```

### WebsocketHandler

Type alias for WebSocket handler functions.

```python
WebsocketHandler = Callable[
    [Dict[str, Any]],
    Union[
        None,
        Awaitable[None],
        List[RecordType],
        Iterable[RecordType],
        AsyncIterable[RecordType],
        Awaitable[Union[List[RecordType], Iterable[RecordType], AsyncIterable[RecordType]]]
    ]
]
```

## Usage Examples

### Basic HTTP Card

```python
from cereon_sdk import BaseCard, ChartCardRecord, ChartCardData

class SalesChart(BaseCard[ChartCardRecord]):
    kind = "line"
    card_id = "sales_chart"
    report_id = "dashboard"
    route_prefix = "/api/cards"
    response_model = ChartCardRecord
    transport = "http"
    
    @classmethod
    async def handler(cls, ctx):
        return [ChartCardRecord(
            kind=cls.kind,
            report_id=cls.report_id,
            card_id=cls.card_id,
            data=ChartCardData(data=[{"x": 1, "y": 2}])
        )]

# Register route
app = FastAPI()
SalesChart(app).as_route(app=app)
```

### WebSocket Real-time Card

```python
import asyncio

class LiveMetrics(BaseCard[NumberCardRecord]):
    kind = "number"
    transport = "websocket"
    
    @classmethod
    async def handler(cls, ctx):
        counter = 0
        while True:
            counter += 1
            yield NumberCardRecord(
                kind=cls.kind,
                report_id=cls.report_id,
                card_id=cls.card_id,
                data=NumberCardData(
                    value=float(counter),
                    label="Live Counter"
                )
            )
            await asyncio.sleep(1)

# Register with WebSocket options
LiveMetrics(app).as_route(
    app=app,
    heartbeat_ms=60000,
    ack_policy="manual"
)
```

### Streaming HTTP Card

```python
class LogStream(BaseCard[TableCardRecord]):
    kind = "table"
    transport = "streaming-http"
    
    @classmethod
    async def handler(cls, ctx):
        async for log_line in tail_logs():
            yield TableCardRecord(
                kind=cls.kind,
                report_id=cls.report_id,
                card_id=cls.card_id,
                data=TableCardData(
                    rows=[{"timestamp": "now", "message": log_line}],
                    columns=["timestamp", "message"]
                )
            )

# Register with SSE format
LogStream(app).as_route(
    app=app,
    format="sse",
    stream_error_policy="skip"
)
```

## Error Handling

### ValidationError

Raised when Pydantic model validation fails.

```python
from pydantic import ValidationError

try:
    record = ChartCardRecord(kind="invalid")
except ValidationError as e:
    print(e.errors())
```

### Runtime Errors

Card handlers should handle errors gracefully:

```python
@classmethod
async def handler(cls, ctx):
    try:
        data = await risky_operation()
        return [ChartCardRecord(...)]
    except Exception as e:
        # Log error and return empty data
        logging.error(f"Error in {cls.card_id}: {e}")
        return [ChartCardRecord(
            kind=cls.kind,
            report_id=cls.report_id,
            card_id=cls.card_id,
            data=ChartCardData(data=[])
        )]
```

## Configuration

### Environment Variables

The SDK respects these environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `CEREON_LOG_LEVEL` | `INFO` | Logging level |
| `CEREON_MAX_CONNECTIONS` | `100` | Max WebSocket connections |
| `CEREON_HEARTBEAT_MS` | `30000` | Default WebSocket heartbeat |
| `CEREON_STREAM_BUFFER_SIZE` | `1000` | Streaming buffer size |

### Custom Configuration

```python
from cereon_sdk.config import settings

settings.max_websocket_connections = 500
settings.default_heartbeat_ms = 60000
```

## Version Information

```python
from cereon_sdk import __version__
print(f"Cereon SDK version: {__version__}")
```

The SDK follows semantic versioning (SemVer). Current version: `0.1.0`

## Migration Guide

### From 0.1.0-alpha to 0.1.0

No breaking changes in the stable 0.1.0 release.

## Next Steps

- [Card Types Reference](card-types.md) - Available card types and usage
- [Transport Protocols](transport.md) - HTTP, WebSocket, and streaming details
- [Examples](examples/) - Real-world implementation examples
- [Deployment Guide](deployment.md) - Production deployment strategies
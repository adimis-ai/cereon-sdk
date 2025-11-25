# Transport Protocols

Cereon SDK supports three transport protocols for delivering dashboard card data. Each protocol serves different use cases and performance requirements.

## Protocol Overview

| Protocol | Use Case | Connection Type | Data Flow | Latency | Complexity |
|----------|----------|----------------|-----------|---------|------------|
| **HTTP** | Static/periodic data | Request-Response | One-time | Low | Simple |
| **WebSocket** | Real-time bidirectional | Persistent | Continuous | Very Low | Medium |
| **Streaming HTTP** | Live data feeds | Long-lived HTTP | Server-to-Client | Low | Medium |

## HTTP Transport

HTTP is the simplest transport protocol, ideal for cards that display relatively static data or data that updates periodically.

### Basic HTTP Card

```python
from cereon_sdk import BaseCard, ChartCardRecord, ChartCardData

class SalesReportCard(BaseCard[ChartCardRecord]):
    kind = "line"
    card_id = "sales_report"
    report_id = "dashboard"
    route_prefix = "/api/cards"
    response_model = ChartCardRecord
    transport = "http"  # HTTP transport
    
    @classmethod
    async def handler(cls, ctx):
        # Handler must return a List[RecordType]
        data = await fetch_sales_data()
        
        return [ChartCardRecord(
            kind=cls.kind,
            report_id=cls.report_id,
            card_id=cls.card_id,
            data=ChartCardData(data=data)
        )]
```

### HTTP with Query Parameters

```python
class FilterableRevenueCard(BaseCard[ChartCardRecord]):
    transport = "http"
    
    @classmethod
    async def handler(cls, ctx):
        # Access query parameters and request data
        params = ctx.get("params", {})
        request = ctx.get("request")
        
        # Parse parameters
        start_date = params.get("start_date", "2024-01-01")
        end_date = params.get("end_date", "2024-12-31")
        region = params.get("region", "all")
        
        # Fetch filtered data
        revenue_data = await get_revenue_data(
            start_date=start_date,
            end_date=end_date,
            region=region
        )
        
        return [ChartCardRecord(
            kind=cls.kind,
            report_id=cls.report_id,
            card_id=cls.card_id,
            data=ChartCardData(data=revenue_data)
        )]
```

### HTTP POST Support

Enable POST requests for complex payloads:

```python
class AnalyticsQueryCard(BaseCard[TableCardRecord]):
    transport = "http"
    
    # Register with POST method support
    @classmethod
    def register_route(cls, app):
        return cls().as_route(app=app, methods=("GET", "POST"))
    
    @classmethod
    async def handler(cls, ctx):
        request = ctx.get("request")
        
        if request.method == "POST":
            # Handle POST request with JSON body
            body = await request.json()
            query = body.get("query", {})
            filters = body.get("filters", {})
        else:
            # Handle GET request with query parameters
            query = ctx.get("params", {})
            filters = {}
        
        # Process query and return results
        results = await execute_analytics_query(query, filters)
        
        return [TableCardRecord(
            kind=cls.kind,
            report_id=cls.report_id,
            card_id=cls.card_id,
            data=TableCardData(
                rows=results,
                columns=list(results[0].keys()) if results else [],
                totalCount=len(results)
            )
        )]
```

### HTTP Caching

Implement caching for better performance:

```python
from functools import lru_cache
from datetime import datetime, timedelta

class CachedMetricsCard(BaseCard[NumberCardRecord]):
    transport = "http"
    
    @staticmethod
    @lru_cache(maxsize=128, ttl=300)  # Cache for 5 minutes
    async def get_metrics_data():
        # Expensive computation or database query
        return await calculate_complex_metrics()
    
    @classmethod
    async def handler(cls, ctx):
        metrics = await cls.get_metrics_data()
        
        return [NumberCardRecord(
            kind=cls.kind,
            report_id=cls.report_id,
            card_id=cls.card_id,
            data=NumberCardData(
                value=metrics["total"],
                label="System Metrics"
            )
        )]
```

## WebSocket Transport

WebSocket provides real-time, bidirectional communication perfect for live dashboards and interactive applications.

### Basic WebSocket Card

```python
import asyncio
import random
from datetime import datetime

class LiveUserCountCard(BaseCard[NumberCardRecord]):
    kind = "number"
    card_id = "live_user_count"
    report_id = "dashboard"
    route_prefix = "/api/cards"
    response_model = NumberCardRecord
    transport = "websocket"  # WebSocket transport
    
    @classmethod
    async def handler(cls, ctx):
        # Handler must be an async generator (yield records)
        user_count = 1000
        
        while True:
            # Simulate user activity
            user_count += random.randint(-10, 25)
            user_count = max(0, user_count)
            
            # Yield a single record
            yield NumberCardRecord(
                kind=cls.kind,
                report_id=cls.report_id,
                card_id=cls.card_id,
                data=NumberCardData(
                    value=float(user_count),
                    label="Active Users",
                    previousValue=None  # Can track previous for trends
                )
            )
            
            # Wait before next update
            await asyncio.sleep(2)  # Update every 2 seconds
```

### WebSocket with Client Parameters

```python
class CustomizableStockCard(BaseCard[ChartCardRecord]):
    kind = "line"
    transport = "websocket"
    
    @classmethod
    async def handler(cls, ctx):
        # Get WebSocket connection and parameters
        websocket = ctx.get("websocket")
        params = ctx.get("params", {})
        
        # Parse client-provided parameters
        symbols = params.get("symbols", ["AAPL", "GOOGL", "MSFT"])
        update_interval = float(params.get("interval", 1.0))
        
        # Validate parameters
        symbols = symbols[:10]  # Limit to 10 symbols
        update_interval = max(0.1, min(update_interval, 10.0))  # 0.1-10 seconds
        
        while True:
            try:
                # Generate or fetch real stock data
                stock_data = []
                for symbol in symbols:
                    price = random.uniform(100, 200)  # Replace with real data
                    stock_data.append({
                        "symbol": symbol,
                        "price": round(price, 2),
                        "timestamp": datetime.utcnow().isoformat()
                    })
                
                yield ChartCardRecord(
                    kind=cls.kind,
                    report_id=cls.report_id,
                    card_id=cls.card_id,
                    data=ChartCardData(data=stock_data)
                )
                
                await asyncio.sleep(update_interval)
                
            except Exception as e:
                # Handle errors gracefully
                error_data = [{
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }]
                
                yield ChartCardRecord(
                    kind=cls.kind,
                    report_id=cls.report_id,
                    card_id=cls.card_id,
                    data=ChartCardData(data=error_data)
                )
                
                await asyncio.sleep(5)  # Wait longer on error
```

### WebSocket Connection Management

Advanced WebSocket configuration:

```python
class AdvancedWebSocketCard(BaseCard[ChartCardRecord]):
    transport = "websocket"
    
    # Configure WebSocket options
    @classmethod
    def register_route(cls, app):
        return cls().as_route(
            app=app,
            heartbeat_ms=30000,  # 30-second heartbeat
            ack_policy="manual"  # Manual acknowledgment
        )
    
    @classmethod
    async def handler(cls, ctx):
        websocket = ctx.get("websocket")
        
        try:
            while True:
                # Check if client is still connected
                if websocket and websocket.client_state.name != "CONNECTED":
                    break
                
                # Generate data
                data = await generate_real_time_data()
                
                yield ChartCardRecord(
                    kind=cls.kind,
                    report_id=cls.report_id,
                    card_id=cls.card_id,
                    data=ChartCardData(data=data)
                )
                
                await asyncio.sleep(1)
                
        except Exception as e:
            # Log disconnection or errors
            import logging
            logging.info(f"WebSocket client disconnected: {e}")
```

### WebSocket Subscription Model

Implement a subscription-based pattern:

```python
class SubscriptionBasedCard(BaseCard[ChartCardRecord]):
    transport = "websocket"
    
    # Class-level subscribers registry
    subscribers = {}
    
    @classmethod
    async def handler(cls, ctx):
        websocket = ctx.get("websocket")
        params = ctx.get("params", {})
        
        # Get subscription parameters
        channels = params.get("channels", ["general"])
        client_id = params.get("client_id", id(websocket))
        
        # Register this client
        cls.subscribers[client_id] = {
            "websocket": websocket,
            "channels": channels,
            "last_seen": datetime.utcnow()
        }
        
        try:
            while True:
                # Send data for subscribed channels
                for channel in channels:
                    data = await get_channel_data(channel)
                    
                    yield ChartCardRecord(
                        kind=cls.kind,
                        report_id=cls.report_id,
                        card_id=cls.card_id,
                        data=ChartCardData(data=data)
                    )
                
                await asyncio.sleep(1)
                
        finally:
            # Clean up on disconnect
            if client_id in cls.subscribers:
                del cls.subscribers[client_id]
```

## Streaming HTTP Transport

Streaming HTTP uses Server-Sent Events (SSE) or NDJSON for one-way real-time data streaming over HTTP.

### Server-Sent Events (SSE)

```python
class SSEMetricsCard(BaseCard[NumberCardRecord]):
    kind = "number"
    card_id = "sse_metrics"
    report_id = "dashboard"
    route_prefix = "/api/cards"
    response_model = NumberCardRecord
    transport = "streaming-http"  # Streaming HTTP transport
    
    @classmethod
    def register_route(cls, app):
        return cls().as_route(
            app=app,
            format="sse",  # Server-Sent Events format
            heartbeat_ms=30000
        )
    
    @classmethod
    async def handler(cls, ctx):
        # Handler must be an async generator
        while True:
            # Fetch current metrics
            cpu_usage = await get_cpu_usage()
            memory_usage = await get_memory_usage()
            
            # Yield CPU usage
            yield NumberCardRecord(
                kind=cls.kind,
                report_id=cls.report_id,
                card_id=cls.card_id + "_cpu",
                data=NumberCardData(
                    value=cpu_usage,
                    label="CPU Usage %"
                )
            )
            
            # Yield memory usage
            yield NumberCardRecord(
                kind=cls.kind,
                report_id=cls.report_id,
                card_id=cls.card_id + "_memory", 
                data=NumberCardData(
                    value=memory_usage,
                    label="Memory Usage %"
                )
            )
            
            await asyncio.sleep(5)  # Update every 5 seconds
```

### NDJSON Streaming

```python
class NDJSONLogStreamCard(BaseCard[TableCardRecord]):
    transport = "streaming-http"
    
    @classmethod
    def register_route(cls, app):
        return cls().as_route(
            app=app,
            format="ndjson",  # Newline-delimited JSON
            delimiter="\n"
        )
    
    @classmethod
    async def handler(cls, ctx):
        # Stream log entries as they arrive
        async for log_entry in tail_log_file("/var/log/app.log"):
            parsed_log = parse_log_entry(log_entry)
            
            yield TableCardRecord(
                kind=cls.kind,
                report_id=cls.report_id,
                card_id=cls.card_id,
                data=TableCardData(
                    rows=[parsed_log],
                    columns=["timestamp", "level", "message", "source"],
                    totalCount=1
                )
            )
```

### Custom Delimiter Streaming

```python
class CustomDelimiterCard(BaseCard[ChartCardRecord]):
    transport = "streaming-http"
    
    @classmethod
    def register_route(cls, app):
        return cls().as_route(
            app=app,
            format="delimited",
            delimiter="|||",  # Custom delimiter
            media_type="application/x-custom-stream"
        )
    
    @classmethod
    async def handler(cls, ctx):
        while True:
            batch_data = await get_batch_sensor_data()
            
            yield ChartCardRecord(
                kind=cls.kind,
                report_id=cls.report_id,
                card_id=cls.card_id,
                data=ChartCardData(data=batch_data)
            )
            
            await asyncio.sleep(0.5)  # High-frequency updates
```

## Protocol Selection Guide

### Choose HTTP When:

- ✅ **Data updates infrequently** (every minute or longer)
- ✅ **Simple request-response pattern** is sufficient
- ✅ **Caching** can improve performance significantly
- ✅ **Load balancing** and **CDN** support is important
- ✅ **Client controls** when to fetch data

**Examples**: Daily reports, configuration dashboards, historical data

### Choose WebSocket When:

- ✅ **Real-time updates** are critical (sub-second)
- ✅ **Bidirectional communication** is needed
- ✅ **Interactive features** require client-server communication
- ✅ **Low latency** is more important than simplicity
- ✅ **Persistent connection** can be maintained

**Examples**: Live trading dashboards, real-time monitoring, interactive applications

### Choose Streaming HTTP When:

- ✅ **One-way data flow** from server to client
- ✅ **Continuous data streams** need to be processed
- ✅ **HTTP infrastructure** must be preserved
- ✅ **Firewall/proxy compatibility** is required
- ✅ **Reconnection handling** should be automatic

**Examples**: Log streaming, metrics feeds, event streams

## Error Handling

### HTTP Error Handling

```python
class RobustHTTPCard(BaseCard[ChartCardRecord]):
    transport = "http"
    
    @classmethod
    async def handler(cls, ctx):
        try:
            data = await risky_data_operation()
            return [ChartCardRecord(...)]
            
        except DatabaseError as e:
            # Log error and return empty data
            logging.error(f"Database error in {cls.card_id}: {e}")
            return [ChartCardRecord(
                kind=cls.kind,
                report_id=cls.report_id,
                card_id=cls.card_id,
                data=ChartCardData(data=[])
            )]
            
        except ValidationError as e:
            # Return error information
            raise HTTPException(status_code=400, detail=str(e))
```

### WebSocket Error Handling

```python
class RobustWebSocketCard(BaseCard[NumberCardRecord]):
    transport = "websocket"
    
    @classmethod
    async def handler(cls, ctx):
        retry_count = 0
        max_retries = 3
        
        while retry_count < max_retries:
            try:
                data = await fetch_live_data()
                retry_count = 0  # Reset on success
                
                yield NumberCardRecord(
                    kind=cls.kind,
                    report_id=cls.report_id,
                    card_id=cls.card_id,
                    data=NumberCardData(value=data, label="Live Data")
                )
                
                await asyncio.sleep(1)
                
            except TemporaryError as e:
                retry_count += 1
                logging.warning(f"Temporary error (retry {retry_count}): {e}")
                await asyncio.sleep(5)  # Wait before retry
                
            except PermanentError as e:
                logging.error(f"Permanent error in {cls.card_id}: {e}")
                break  # Exit the loop
```

### Streaming Error Handling

```python
class RobustStreamingCard(BaseCard[ChartCardRecord]):
    transport = "streaming-http"
    
    @classmethod
    def register_route(cls, app):
        return cls().as_route(
            app=app,
            stream_error_policy="skip"  # Skip errors, continue streaming
        )
    
    @classmethod
    async def handler(cls, ctx):
        while True:
            try:
                stream_data = await get_streaming_data()
                
                yield ChartCardRecord(
                    kind=cls.kind,
                    report_id=cls.report_id,
                    card_id=cls.card_id,
                    data=ChartCardData(data=stream_data)
                )
                
            except Exception as e:
                # Log error but continue streaming
                logging.error(f"Stream error: {e}")
                
                # Yield error indicator (optional)
                yield ChartCardRecord(
                    kind=cls.kind,
                    report_id=cls.report_id,
                    card_id=cls.card_id,
                    data=ChartCardData(data=[{"error": str(e)}])
                )
            
            await asyncio.sleep(1)
```

## Performance Optimization

### Connection Pooling

```python
import aiohttp
import asyncio

class OptimizedHTTPCard(BaseCard[ChartCardRecord]):
    # Shared connection pool
    _session = None
    
    @classmethod
    async def get_session(cls):
        if cls._session is None or cls._session.closed:
            cls._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10),
                connector=aiohttp.TCPConnector(limit=100)
            )
        return cls._session
    
    @classmethod
    async def handler(cls, ctx):
        session = await cls.get_session()
        
        async with session.get("https://api.example.com/data") as response:
            data = await response.json()
            
        return [ChartCardRecord(
            kind=cls.kind,
            report_id=cls.report_id,
            card_id=cls.card_id,
            data=ChartCardData(data=data)
        )]
```

### Memory Management for Streaming

```python
class MemoryEfficientStreamCard(BaseCard[ChartCardRecord]):
    transport = "streaming-http"
    
    @classmethod
    async def handler(cls, ctx):
        # Process data in chunks to avoid memory buildup
        async for chunk in process_large_dataset_in_chunks():
            # Yield immediately to free memory
            yield ChartCardRecord(
                kind=cls.kind,
                report_id=cls.report_id,
                card_id=cls.card_id,
                data=ChartCardData(data=chunk)
            )
            
            # Allow other tasks to run
            await asyncio.sleep(0)
```

## Security Considerations

### Authentication

```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

class SecureCard(BaseCard[ChartCardRecord]):
    transport = "http"
    
    @classmethod
    async def handler(cls, ctx, token: str = Depends(security)):
        # Validate token
        user = await validate_jwt_token(token.credentials)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Filter data based on user permissions
        data = await get_user_specific_data(user.id)
        
        return [ChartCardRecord(
            kind=cls.kind,
            report_id=cls.report_id,
            card_id=cls.card_id,
            data=ChartCardData(data=data)
        )]
```

### Rate Limiting

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

class RateLimitedCard(BaseCard[ChartCardRecord]):
    @classmethod
    def register_route(cls, app):
        # Apply rate limiting
        route = cls().as_route(app=app)
        
        # Add rate limit decorator
        endpoint = getattr(app, f"get_{cls.card_id}")
        endpoint = limiter.limit("10/minute")(endpoint)
        
        return route
```

## Next Steps

- [API Reference](api-reference.md) - Complete SDK documentation
- [Deployment Guide](deployment.md) - Production deployment strategies
- [Examples](examples/) - Real-world implementation examples
- [Card Types Reference](card-types.md) - Available card types
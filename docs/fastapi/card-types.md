# Card Types Reference

Cereon SDK supports multiple card types for different data visualization needs. Each card type has specific data structures and rendering capabilities.

## Overview

| Card Type | Use Case | Data Structure | Transport Support |
|-----------|----------|----------------|-------------------|
| **Chart** | Data visualizations (line, bar, pie, etc.) | Array of data points | HTTP, WebSocket, Streaming |
| **Number** | KPIs and metrics | Single numeric value with trend | HTTP, WebSocket, Streaming |
| **Table** | Tabular data display | Rows and columns | HTTP, WebSocket, Streaming |
| **Markdown** | Rich text content | Markdown string | HTTP |
| **HTML** | Custom HTML content | HTML string | HTTP |
| **Iframe** | Embedded external content | URL and configuration | HTTP |

## Chart Cards

Chart cards display data visualizations using various chart types.

### Basic Structure

```python
from cereon_sdk import BaseCard, ChartCardRecord, ChartCardData

class MyChartCard(BaseCard[ChartCardRecord]):
    kind = "line"  # Chart type: line, bar, area, pie, radar, radial
    card_id = "my_chart"
    report_id = "dashboard"
    route_prefix = "/api/cards"
    response_model = ChartCardRecord
    transport = "http"
    
    @classmethod
    async def handler(cls, ctx):
        data = [
            {"x": "Jan", "y": 100, "series": "Sales"},
            {"x": "Feb", "y": 150, "series": "Sales"},
            {"x": "Mar", "y": 130, "series": "Sales"}
        ]
        
        return [ChartCardRecord(
            kind=cls.kind,
            report_id=cls.report_id,
            card_id=cls.card_id,
            data=ChartCardData(data=data)
        )]
```

### Supported Chart Types

#### Line Chart (`kind = "line"`)

Perfect for time series data and trends.

```python
class SalesLineChart(BaseCard[ChartCardRecord]):
    kind = "line"
    
    @classmethod
    async def handler(cls, ctx):
        data = [
            {"date": "2024-01-01", "sales": 1200, "target": 1000},
            {"date": "2024-01-02", "sales": 1350, "target": 1100},
            {"date": "2024-01-03", "sales": 1180, "target": 1200}
        ]
        
        return [ChartCardRecord(
            kind=cls.kind,
            report_id=cls.report_id,
            card_id=cls.card_id,
            data=ChartCardData(data=data)
        )]
```

#### Bar Chart (`kind = "bar"`)

Ideal for categorical comparisons.

```python
class RegionBarChart(BaseCard[ChartCardRecord]):
    kind = "bar"
    
    @classmethod
    async def handler(cls, ctx):
        data = [
            {"region": "North", "sales": 25000, "orders": 150},
            {"region": "South", "sales": 18000, "orders": 120},
            {"region": "East", "sales": 22000, "orders": 140},
            {"region": "West", "sales": 20000, "orders": 130}
        ]
        
        return [ChartCardRecord(
            kind=cls.kind,
            report_id=cls.report_id,
            card_id=cls.card_id,
            data=ChartCardData(data=data)
        )]
```

#### Area Chart (`kind = "area"`)

Great for showing volume and cumulative data.

```python
class VolumeAreaChart(BaseCard[ChartCardRecord]):
    kind = "area"
    
    @classmethod
    async def handler(cls, ctx):
        data = [
            {"time": "09:00", "volume": 1200, "price": 150.5},
            {"time": "10:00", "volume": 1800, "price": 152.3},
            {"time": "11:00", "volume": 2200, "price": 151.8}
        ]
        
        return [ChartCardRecord(
            kind=cls.kind,
            report_id=cls.report_id,
            card_id=cls.card_id,
            data=ChartCardData(data=data)
        )]
```

#### Pie Chart (`kind = "pie"`)

Perfect for showing proportions and percentages.

```python
class MarketSharePieChart(BaseCard[ChartCardRecord]):
    kind = "pie"
    
    @classmethod
    async def handler(cls, ctx):
        data = [
            {"label": "Product A", "value": 35, "percentage": 35.0},
            {"label": "Product B", "value": 25, "percentage": 25.0},
            {"label": "Product C", "value": 20, "percentage": 20.0},
            {"label": "Others", "value": 20, "percentage": 20.0}
        ]
        
        return [ChartCardRecord(
            kind=cls.kind,
            report_id=cls.report_id,
            card_id=cls.card_id,
            data=ChartCardData(data=data)
        )]
```

#### Radar Chart (`kind = "radar"`)

Ideal for multi-dimensional comparisons.

```python
class PerformanceRadarChart(BaseCard[ChartCardRecord]):
    kind = "radar"
    
    @classmethod
    async def handler(cls, ctx):
        data = [
            {"metric": "Speed", "current": 85, "target": 90, "competitor": 75},
            {"metric": "Quality", "current": 92, "target": 95, "competitor": 88},
            {"metric": "Cost", "current": 78, "target": 85, "competitor": 82},
            {"metric": "Innovation", "current": 88, "target": 90, "competitor": 70}
        ]
        
        return [ChartCardRecord(
            kind=cls.kind,
            report_id=cls.report_id,
            card_id=cls.card_id,
            data=ChartCardData(data=data)
        )]
```

#### Radial Chart (`kind = "radial"`)

Great for progress indicators and circular metrics.

```python
class GoalProgressRadialChart(BaseCard[ChartCardRecord]):
    kind = "radial"
    
    @classmethod
    async def handler(cls, ctx):
        data = [
            {"name": "Sales Goal", "value": 75, "max": 100, "color": "#10B981"},
            {"name": "User Acquisition", "value": 88, "max": 100, "color": "#3B82F6"},
            {"name": "Revenue Target", "value": 62, "max": 100, "color": "#F59E0B"}
        ]
        
        return [ChartCardRecord(
            kind=cls.kind,
            report_id=cls.report_id,
            card_id=cls.card_id,
            data=ChartCardData(data=data)
        )]
```

### Real-time Chart Streaming

Charts support real-time updates via WebSocket:

```python
class LiveMetricsChart(BaseCard[ChartCardRecord]):
    kind = "line"
    transport = "websocket"
    
    @classmethod
    async def handler(cls, ctx):
        import time
        import random
        
        while True:
            current_time = time.strftime("%H:%M:%S")
            data = [{
                "time": current_time,
                "cpu": random.randint(20, 80),
                "memory": random.randint(30, 90),
                "network": random.randint(10, 60)
            }]
            
            yield ChartCardRecord(
                kind=cls.kind,
                report_id=cls.report_id,
                card_id=cls.card_id,
                data=ChartCardData(data=data)
            )
            
            await asyncio.sleep(1)  # Update every second
```

## Number Cards

Number cards display key performance indicators (KPIs) with optional trend information.

### Basic Structure

```python
from cereon_sdk import BaseCard, NumberCardRecord, NumberCardData

class RevenueKPI(BaseCard[NumberCardRecord]):
    kind = "number"
    card_id = "revenue_kpi"
    report_id = "dashboard"
    route_prefix = "/api/cards"
    response_model = NumberCardRecord
    transport = "http"
    
    @classmethod
    async def handler(cls, ctx):
        current_revenue = 125000.0
        previous_revenue = 118000.0
        
        # Calculate trend
        trend = "up" if current_revenue > previous_revenue else "down"
        trend_percentage = ((current_revenue - previous_revenue) / previous_revenue) * 100
        
        return [NumberCardRecord(
            kind=cls.kind,
            report_id=cls.report_id,
            card_id=cls.card_id,
            data=NumberCardData(
                value=current_revenue,
                previousValue=previous_revenue,
                trend=trend,
                trendPercentage=trend_percentage,
                label="Monthly Revenue"
            )
        )]
```

### Number Card Features

- **Value**: Main numeric value to display
- **Previous Value**: For comparison and trend calculation
- **Trend**: Direction (`"up"`, `"down"`, `"neutral"`)
- **Trend Percentage**: Percentage change from previous value
- **Label**: Descriptive text for the metric
- **Unit**: Optional unit specification (via metadata)

### Advanced Number Card Example

```python
class ConversionRateCard(BaseCard[NumberCardRecord]):
    kind = "number"
    
    @classmethod
    async def handler(cls, ctx):
        # Get parameters
        params = ctx.get("params", {})
        time_period = params.get("period", "month")  # day, week, month
        
        # Calculate conversion rate based on period
        if time_period == "day":
            current_rate = 0.035  # 3.5%
            previous_rate = 0.032
        elif time_period == "week":
            current_rate = 0.041
            previous_rate = 0.038
        else:  # month
            current_rate = 0.045
            previous_rate = 0.042
        
        return [NumberCardRecord(
            kind=cls.kind,
            report_id=cls.report_id,
            card_id=cls.card_id,
            data=NumberCardData(
                value=current_rate,
                previousValue=previous_rate,
                trend="up" if current_rate > previous_rate else "down",
                trendPercentage=((current_rate - previous_rate) / previous_rate) * 100,
                label=f"Conversion Rate ({time_period.title()})"
            ),
            meta=NumberCardMetadata(
                unit="%",
                format="percentage"
            )
        )]
```

### Real-time Number Updates

```python
class LiveUserCount(BaseCard[NumberCardRecord]):
    kind = "number"
    transport = "websocket"
    
    @classmethod
    async def handler(cls, ctx):
        user_count = 1245  # Starting count
        
        while True:
            # Simulate user activity
            user_count += random.randint(-5, 15)
            user_count = max(0, user_count)  # Never go negative
            
            yield NumberCardRecord(
                kind=cls.kind,
                report_id=cls.report_id,
                card_id=cls.card_id,
                data=NumberCardData(
                    value=float(user_count),
                    label="Active Users"
                )
            )
            
            await asyncio.sleep(3)  # Update every 3 seconds
```

## Table Cards

Table cards display structured tabular data with support for sorting and pagination.

### Basic Structure

```python
from cereon_sdk import BaseCard, TableCardRecord, TableCardData

class UsersTable(BaseCard[TableCardRecord]):
    kind = "table"
    card_id = "users_table"
    report_id = "dashboard"
    route_prefix = "/api/cards"
    response_model = TableCardRecord
    transport = "http"
    
    @classmethod
    async def handler(cls, ctx):
        users_data = [
            {"id": 1, "name": "Alice Smith", "email": "alice@example.com", "role": "Admin", "last_login": "2024-01-15"},
            {"id": 2, "name": "Bob Johnson", "email": "bob@example.com", "role": "User", "last_login": "2024-01-14"},
            {"id": 3, "name": "Carol Williams", "email": "carol@example.com", "role": "Manager", "last_login": "2024-01-13"}
        ]
        
        columns = ["id", "name", "email", "role", "last_login"]
        
        return [TableCardRecord(
            kind=cls.kind,
            report_id=cls.report_id,
            card_id=cls.card_id,
            data=TableCardData(
                rows=users_data,
                columns=columns,
                totalCount=len(users_data)
            )
        )]
```

### Table with Pagination

```python
class PaginatedOrdersTable(BaseCard[TableCardRecord]):
    kind = "table"
    
    @classmethod
    async def handler(cls, ctx):
        # Get pagination parameters
        params = ctx.get("params", {})
        page = int(params.get("page", 1))
        limit = int(params.get("limit", 10))
        offset = (page - 1) * limit
        
        # Simulate database query with pagination
        all_orders = []  # Your data source here
        total_count = len(all_orders)
        
        # Apply pagination
        paginated_orders = all_orders[offset:offset + limit]
        
        return [TableCardRecord(
            kind=cls.kind,
            report_id=cls.report_id,
            card_id=cls.card_id,
            data=TableCardData(
                rows=paginated_orders,
                columns=["order_id", "customer", "amount", "status", "date"],
                totalCount=total_count
            )
        )]
```

### Filterable Table

```python
class FilterableProductsTable(BaseCard[TableCardRecord]):
    kind = "table"
    
    @classmethod
    async def handler(cls, ctx):
        params = ctx.get("params", {})
        
        # Filter parameters
        category = params.get("category")
        min_price = params.get("min_price", type=float)
        search = params.get("search", "").lower()
        
        # Sample data (replace with database query)
        all_products = [
            {"id": 1, "name": "Laptop", "category": "Electronics", "price": 999.99, "stock": 15},
            {"id": 2, "name": "Desk Chair", "category": "Furniture", "price": 299.99, "stock": 8},
            {"id": 3, "name": "Coffee Mug", "category": "Kitchen", "price": 12.99, "stock": 50}
        ]
        
        # Apply filters
        filtered_products = all_products
        
        if category:
            filtered_products = [p for p in filtered_products if p["category"] == category]
        
        if min_price is not None:
            filtered_products = [p for p in filtered_products if p["price"] >= min_price]
        
        if search:
            filtered_products = [p for p in filtered_products if search in p["name"].lower()]
        
        return [TableCardRecord(
            kind=cls.kind,
            report_id=cls.report_id,
            card_id=cls.card_id,
            data=TableCardData(
                rows=filtered_products,
                columns=["id", "name", "category", "price", "stock"],
                totalCount=len(filtered_products)
            )
        )]
```

## Markdown Cards

Markdown cards render rich text content using Markdown syntax.

### Basic Structure

```python
from cereon_sdk import BaseCard, MarkdownCardRecord, MarkdownCardData

class DocumentationCard(BaseCard[MarkdownCardRecord]):
    kind = "markdown"
    card_id = "documentation"
    report_id = "dashboard"
    route_prefix = "/api/cards"
    response_model = MarkdownCardRecord
    transport = "http"
    
    @classmethod
    async def handler(cls, ctx):
        markdown_content = """
# Dashboard Overview

This dashboard provides real-time insights into your business metrics.

## Key Features

- **Real-time Updates**: Live data streaming via WebSocket
- **Interactive Charts**: Multiple chart types for data visualization  
- **Filtering**: Advanced filtering and search capabilities
- **Export**: Download data in various formats

## Usage Instructions

1. Select the desired time period using the date picker
2. Apply filters to focus on specific data segments
3. Hover over charts for detailed tooltips
4. Use the export button to download reports

> **Note**: Data is updated every 5 minutes automatically.

### Support

For questions or issues, contact: [support@example.com](mailto:support@example.com)
        """
        
        return [MarkdownCardRecord(
            kind=cls.kind,
            report_id=cls.report_id,
            card_id=cls.card_id,
            data=MarkdownCardData(content=markdown_content.strip())
        )]
```

### Dynamic Markdown with Data

```python
class StatusReportCard(BaseCard[MarkdownCardRecord]):
    kind = "markdown"
    
    @classmethod
    async def handler(cls, ctx):
        # Fetch current system status
        uptime_hours = 168  # Example: 7 days
        error_count = 3
        last_deployment = "2024-01-14 15:30:00"
        
        status_icon = "🟢" if error_count < 5 else "🟡" if error_count < 20 else "🔴"
        
        markdown_content = f"""
# System Status {status_icon}

## Current Status: {"Healthy" if error_count < 5 else "Warning" if error_count < 20 else "Critical"}

### Metrics
- **Uptime**: {uptime_hours} hours
- **Error Count**: {error_count} (last 24h)
- **Last Deployment**: {last_deployment}

### Recent Activity
- ✅ Database backup completed
- ✅ SSL certificates renewed
- ⚠️ High memory usage detected on server-2
- ✅ Load balancer configuration updated

---
*Last updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC*
        """
        
        return [MarkdownCardRecord(
            kind=cls.kind,
            report_id=cls.report_id,
            card_id=cls.card_id,
            data=MarkdownCardData(content=markdown_content.strip())
        )]
```

## HTML Cards

HTML cards render custom HTML content for maximum flexibility.

### Basic Structure

```python
from cereon_sdk import BaseCard, HtmlCardRecord, HtmlCardData

class CustomHtmlCard(BaseCard[HtmlCardRecord]):
    kind = "html"
    card_id = "custom_html"
    report_id = "dashboard"
    route_prefix = "/api/cards"
    response_model = HtmlCardRecord
    transport = "http"
    
    @classmethod
    async def handler(cls, ctx):
        html_content = """
        <div class="custom-widget">
            <h3 style="color: #2563eb; margin-bottom: 16px;">Custom Widget</h3>
            <div style="display: flex; gap: 12px; margin-bottom: 16px;">
                <div style="background: #f0f9ff; padding: 12px; border-radius: 8px; flex: 1;">
                    <div style="font-size: 24px; font-weight: bold; color: #0369a1;">$12.5K</div>
                    <div style="color: #64748b; font-size: 14px;">Revenue</div>
                </div>
                <div style="background: #f0fdf4; padding: 12px; border-radius: 8px; flex: 1;">
                    <div style="font-size: 24px; font-weight: bold; color: #059669;">+8.2%</div>
                    <div style="color: #64748b; font-size: 14px;">Growth</div>
                </div>
            </div>
            <div style="height: 100px; background: linear-gradient(45deg, #3b82f6, #06b6d4); border-radius: 8px; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold;">
                Custom Chart Area
            </div>
        </div>
        """
        
        custom_styles = """
        .custom-widget {
            padding: 20px;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            background: white;
        }
        """
        
        return [HtmlCardRecord(
            kind=cls.kind,
            report_id=cls.report_id,
            card_id=cls.card_id,
            data=HtmlCardData(
                content=html_content,
                styles=custom_styles
            )
        )]
```

## Iframe Cards

Iframe cards embed external content or applications.

### Basic Structure

```python
from cereon_sdk import BaseCard, IframeCardRecord, IframeCardData

class EmbeddedAppCard(BaseCard[IframeCardRecord]):
    kind = "iframe"
    card_id = "embedded_app"
    report_id = "dashboard"
    route_prefix = "/api/cards"
    response_model = IframeCardRecord
    transport = "http"
    
    @classmethod
    async def handler(cls, ctx):
        return [IframeCardRecord(
            kind=cls.kind,
            report_id=cls.report_id,
            card_id=cls.card_id,
            data=IframeCardData(
                url="https://example.com/analytics-widget",
                title="Analytics Widget",
                width="100%",
                height="400px"
            )
        )]
```

### Dynamic Iframe with Parameters

```python
class ConfigurableMapCard(BaseCard[IframeCardRecord]):
    kind = "iframe"
    
    @classmethod
    async def handler(cls, ctx):
        params = ctx.get("params", {})
        
        # Default values
        latitude = params.get("lat", 37.7749)  # San Francisco
        longitude = params.get("lng", -122.4194)
        zoom = params.get("zoom", 10)
        
        # Build map URL with parameters
        map_url = f"https://maps.example.com/embed?lat={latitude}&lng={longitude}&zoom={zoom}"
        
        return [IframeCardRecord(
            kind=cls.kind,
            report_id=cls.report_id,
            card_id=cls.card_id,
            data=IframeCardData(
                url=map_url,
                title=f"Location Map ({latitude}, {longitude})",
                width="100%",
                height="300px"
            )
        )]
```

## Error Handling

All card types should include proper error handling:

```python
class RobustCard(BaseCard[ChartCardRecord]):
    @classmethod
    async def handler(cls, ctx):
        try:
            # Your data logic here
            data = await fetch_data_from_api()
            
            return [ChartCardRecord(
                kind=cls.kind,
                report_id=cls.report_id,
                card_id=cls.card_id,
                data=ChartCardData(data=data)
            )]
            
        except Exception as e:
            # Log the error
            import logging
            logging.error(f"Error in {cls.card_id}: {str(e)}")
            
            # Return empty data with error metadata
            return [ChartCardRecord(
                kind=cls.kind,
                report_id=cls.report_id,
                card_id=cls.card_id,
                data=ChartCardData(data=[]),
                meta=QueryMetadata(
                    startedAt=datetime.utcnow().isoformat() + "Z",
                    finishedAt=datetime.utcnow().isoformat() + "Z",
                    elapsedMs=0,
                    error=str(e)  # If supported by your metadata model
                )
            )]
```

## Best Practices

### 1. **Consistent Data Structures**
Ensure your data follows consistent patterns across similar cards.

### 2. **Parameter Validation**
Always validate and sanitize input parameters:

```python
@classmethod
async def handler(cls, ctx):
    params = ctx.get("params", {})
    
    # Validate parameters
    try:
        limit = max(1, min(int(params.get("limit", 10)), 100))  # 1-100 range
        page = max(1, int(params.get("page", 1)))
    except (ValueError, TypeError):
        limit, page = 10, 1
    
    # Continue with validated parameters
```

### 3. **Performance Optimization**
- Use async/await for I/O operations
- Implement caching for expensive computations
- Limit data size for large datasets

### 4. **Metadata Population**
Always populate metadata for observability:

```python
start_time = time.perf_counter()
# ... your logic ...
end_time = time.perf_counter()

meta = QueryMetadata(
    startedAt=datetime.utcnow().isoformat() + "Z",
    finishedAt=datetime.utcnow().isoformat() + "Z", 
    elapsedMs=int((end_time - start_time) * 1000)
)
```

## Next Steps

- [Transport Protocols](transport.md) - Learn about HTTP, WebSocket, and streaming
- [API Reference](api-reference.md) - Complete SDK documentation
- [Examples](examples/) - More real-world examples
- [Deployment Guide](deployment.md) - Production deployment strategies
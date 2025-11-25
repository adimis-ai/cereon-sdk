# Quick Start Tutorial

Build your first interactive dashboard backend in 10 minutes using Cereon SDK.

## What We'll Build

A real-time sales dashboard with:
- 📊 **Sales Chart**: Line chart showing monthly sales trends
- 📈 **KPI Card**: Total revenue with growth percentage  
- 📋 **Sales Table**: Top-performing products
- 🔄 **Live Updates**: Real-time sales counter via WebSocket

## Prerequisites

- Python 3.10+
- Basic FastAPI knowledge (helpful but not required)

## Step 1: Install Cereon SDK

```bash
pip install cereon-sdk fastapi uvicorn
```

## Step 2: Create the Basic App Structure

Create `main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Sales Dashboard API",
    description="Real-time sales analytics dashboard",
    version="1.0.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Sales Dashboard API", "status": "running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
```

## Step 3: Create Your First Chart Card

Create `cards.py`:

```python
import asyncio
import random
from datetime import datetime, timedelta
from cereon_sdk import (
    BaseCard, 
    ChartCardRecord, 
    ChartCardData,
    NumberCardRecord,
    NumberCardData, 
    TableCardRecord,
    TableCardData,
    QueryMetadata
)

# Sample data generator
def generate_sales_data():
    """Generate sample monthly sales data"""
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
    return [
        {
            "month": month,
            "sales": random.randint(10000, 25000),
            "target": random.randint(15000, 20000),
            "profit": random.randint(2000, 5000)
        }
        for month in months
    ]

class MonthlySalesCard(BaseCard[ChartCardRecord]):
    """Monthly sales trend chart"""
    kind = "line"
    card_id = "monthly_sales"
    report_id = "sales_dashboard" 
    route_prefix = "/api/cards"
    response_model = ChartCardRecord
    transport = "http"
    
    @classmethod
    async def handler(cls, ctx):
        # Simulate database query delay
        await asyncio.sleep(0.1)
        
        sales_data = generate_sales_data()
        
        return [ChartCardRecord(
            kind=cls.kind,
            report_id=cls.report_id,
            card_id=cls.card_id,
            data=ChartCardData(data=sales_data),
            meta=QueryMetadata(
                startedAt=datetime.utcnow().isoformat() + "Z",
                finishedAt=datetime.utcnow().isoformat() + "Z",
                elapsedMs=100
            )
        )]
```

## Step 4: Add a KPI Number Card

Add to `cards.py`:

```python
class TotalRevenueCard(BaseCard[NumberCardRecord]):
    """Total revenue KPI with trend"""
    kind = "number"
    card_id = "total_revenue"
    report_id = "sales_dashboard"
    route_prefix = "/api/cards" 
    response_model = NumberCardRecord
    transport = "http"
    
    @classmethod
    async def handler(cls, ctx):
        # Calculate current and previous revenue
        current_revenue = random.randint(80000, 120000)
        previous_revenue = random.randint(70000, 110000)
        
        # Calculate trend
        trend = "up" if current_revenue > previous_revenue else "down"
        trend_percentage = ((current_revenue - previous_revenue) / previous_revenue) * 100
        
        return [NumberCardRecord(
            kind=cls.kind,
            report_id=cls.report_id,
            card_id=cls.card_id,
            data=NumberCardData(
                value=float(current_revenue),
                previousValue=float(previous_revenue),
                trend=trend,
                trendPercentage=trend_percentage,
                label="Total Revenue"
            )
        )]
```

## Step 5: Add a Data Table Card

Add to `cards.py`:

```python
class TopProductsCard(BaseCard[TableCardRecord]):
    """Top performing products table"""
    kind = "table"
    card_id = "top_products"
    report_id = "sales_dashboard"
    route_prefix = "/api/cards"
    response_model = TableCardRecord
    transport = "http"
    
    @classmethod
    async def handler(cls, ctx):
        # Sample product data
        products = [
            {"product": "Laptop Pro", "sales": 1250, "revenue": 875000, "growth": "+12%"},
            {"product": "Wireless Mouse", "sales": 3450, "revenue": 172500, "growth": "+8%"}, 
            {"product": "Mechanical Keyboard", "sales": 890, "revenue": 133500, "growth": "+15%"},
            {"product": "Monitor 4K", "sales": 650, "revenue": 325000, "growth": "+5%"},
            {"product": "USB-C Hub", "sales": 2100, "revenue": 147000, "growth": "+22%"}
        ]
        
        return [TableCardRecord(
            kind=cls.kind,
            report_id=cls.report_id,
            card_id=cls.card_id,
            data=TableCardData(
                rows=products,
                columns=["product", "sales", "revenue", "growth"],
                totalCount=len(products)
            )
        )]
```

## Step 6: Add Real-time WebSocket Card

Add to `cards.py`:

```python
class LiveSalesCounterCard(BaseCard[NumberCardRecord]):
    """Real-time sales counter via WebSocket"""
    kind = "number"
    card_id = "live_sales_counter"
    report_id = "sales_dashboard"
    route_prefix = "/api/cards"
    response_model = NumberCardRecord
    transport = "websocket"
    
    @classmethod
    async def handler(cls, ctx):
        """Stream live sales updates every 2 seconds"""
        sales_counter = random.randint(1000, 5000)
        
        while True:
            # Simulate new sales
            sales_counter += random.randint(1, 10)
            
            yield NumberCardRecord(
                kind=cls.kind,
                report_id=cls.report_id,
                card_id=cls.card_id,
                data=NumberCardData(
                    value=float(sales_counter),
                    label="Live Sales Count"
                )
            )
            
            # Wait 2 seconds before next update
            await asyncio.sleep(2)
```

## Step 7: Register All Cards

Update `main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from cards import (
    MonthlySalesCard,
    TotalRevenueCard, 
    TopProductsCard,
    LiveSalesCounterCard
)

app = FastAPI(
    title="Sales Dashboard API",
    description="Real-time sales analytics dashboard", 
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all dashboard cards
cards = [
    MonthlySalesCard,
    TotalRevenueCard,
    TopProductsCard, 
    LiveSalesCounterCard
]

for CardClass in cards:
    CardClass(app).as_route(app=app)
    print(f"✅ Registered {CardClass.card_id} ({CardClass.transport})")

@app.get("/")
async def root():
    return {
        "message": "Sales Dashboard API",
        "status": "running",
        "cards": [card.card_id for card in cards]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
```

## Step 8: Test Your Dashboard API

Start the server:

```bash
python main.py
```

You should see:

```
✅ Registered monthly_sales (http)
✅ Registered total_revenue (http)  
✅ Registered top_products (http)
✅ Registered live_sales_counter (websocket)
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Test HTTP Endpoints

```bash
# Test the monthly sales chart
curl http://localhost:8000/api/cards/monthly_sales

# Test the revenue KPI
curl http://localhost:8000/api/cards/total_revenue

# Test the products table
curl http://localhost:8000/api/cards/top_products
```

### Test WebSocket Endpoint

For WebSocket testing, use a WebSocket client or the auto-generated docs at `http://localhost:8000/docs`.

## Step 9: Explore Auto-Generated API Docs

Visit `http://localhost:8000/docs` to see your interactive API documentation:

- 📊 All card endpoints are automatically documented
- 🧪 Test endpoints directly in the browser
- 📋 View request/response schemas
- 🔌 WebSocket connections are documented

## Step 10: Add Query Parameters (Advanced)

Make cards configurable with query parameters:

```python
class MonthlySalesCard(BaseCard[ChartCardRecord]):
    # ... previous code ...
    
    @classmethod
    async def handler(cls, ctx):
        # Access query parameters
        params = ctx.get("params", {})
        months_count = int(params.get("months", 6))  # Default 6 months
        
        # Generate data based on parameters
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug"][:months_count]
        sales_data = [
            {
                "month": month,
                "sales": random.randint(10000, 25000),
                "target": random.randint(15000, 20000)
            }
            for month in months
        ]
        
        return [ChartCardRecord(
            kind=cls.kind,
            report_id=cls.report_id,
            card_id=cls.card_id,
            data=ChartCardData(data=sales_data)
        )]
```

Test with parameters:

```bash
curl "http://localhost:8000/api/cards/monthly_sales?months=3"
```

## 🎉 Congratulations!

You've successfully created a complete dashboard backend with:

- ✅ **4 different card types** (chart, number, table, real-time)
- ✅ **Multiple transport protocols** (HTTP and WebSocket)
- ✅ **Query parameters** for customization
- ✅ **Auto-generated API documentation**
- ✅ **Type safety** with Pydantic validation

## Next Steps

### 🚀 Enhanced Features

1. **Add Database Integration**:
   ```python
   # Use SQLAlchemy or your preferred ORM
   async def handler(cls, ctx):
       async with get_db() as db:
           sales = await db.execute("SELECT * FROM sales")
           return [ChartCardRecord(...)]
   ```

2. **Add Authentication**:
   ```python
   from fastapi import Depends
   from fastapi.security import HTTPBearer
   
   # Add to handler
   @classmethod
   async def handler(cls, ctx, user=Depends(get_current_user)):
       # Access authenticated user data
       pass
   ```

3. **Add Caching**:
   ```python
   from functools import lru_cache
   
   @lru_cache(maxsize=100)
   async def get_sales_data():
       # Expensive computation
       return data
   ```

### 📚 Learn More

- [Card Types Reference](card-types.md) - All available card types
- [Transport Protocols](transport.md) - Advanced WebSocket and streaming
- [API Reference](api-reference.md) - Complete SDK documentation
- [Deployment Guide](deployment.md) - Production deployment
- [Examples](examples/) - More real-world examples

### 🎯 Integration with Frontend

To connect this backend with a React dashboard, use [@cereon/dashboard](https://www.npmjs.com/package/@cereon/dashboard):

```tsx
import { Dashboard } from '@cereon/dashboard';

const dashboardSpec = {
  id: "sales_dashboard",
  reports: [{
    id: "sales_dashboard", 
    title: "Sales Analytics",
    reportCards: [
      {
        id: "monthly_sales",
        kind: "line",
        query: {
          variant: "http",
          payload: { url: "http://localhost:8000/api/cards/monthly_sales" }
        }
      },
      {
        id: "live_counter",
        kind: "number", 
        query: {
          variant: "websocket",
          payload: { 
            url: "ws://localhost:8000/api/cards/live_sales_counter",
            topic: "live_sales_counter"
          }
        }
      }
    ]
  }]
};

<Dashboard state={{ spec: dashboardSpec }} />
```

Happy dashboard building! 🚀
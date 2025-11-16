# Installation & Setup

This guide covers the complete installation and setup process for Cereon SDK.

## Requirements

- **Python**: 3.10 or higher
- **FastAPI**: 0.110.0 or higher (automatically installed)
- **Pydantic**: 2.6.0 or higher (automatically installed)

## Installation

### Using pip

```bash
pip install cereon-sdk
```

### Using uv (recommended)

```bash
uv add cereon-sdk
```

### Development Installation

For contributing or development:

```bash
git clone https://github.com/adimis-ai/cereon-sdk.git
cd cereon/packages/cereon-sdk
pip install -e ".[dev]"
```

## Basic Setup

### 1. Create a FastAPI Application

```python
# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="My Dashboard API")

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 2. Create Your First Card

```python
# cards.py
from cereon_sdk import BaseCard, ChartCardRecord, ChartCardData

class SalesCard(BaseCard[ChartCardRecord]):
    kind = "line"
    card_id = "sales_overview"
    report_id = "dashboard"
    route_prefix = "/api/cards"
    response_model = ChartCardRecord
    transport = "http"
    
    @classmethod
    async def handler(cls, ctx):
        # Sample data - replace with your logic
        sales_data = [
            {"month": "Jan", "sales": 12000, "target": 10000},
            {"month": "Feb", "sales": 15000, "target": 12000},
            {"month": "Mar", "sales": 13500, "target": 13000},
        ]
        
        return [ChartCardRecord(
            kind=cls.kind,
            report_id=cls.report_id,
            card_id=cls.card_id,
            data=ChartCardData(data=sales_data)
        )]
```

### 3. Register Cards and Start Server

```python
# main.py (continued)
from cards import SalesCard

# Register the card route
SalesCard(app).as_route(app=app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 4. Test Your Setup

Start the server:

```bash
python main.py
```

Test the endpoint:

```bash
curl http://localhost:8000/api/cards/sales_overview
```

Expected response:

```json
[
  {
    "kind": "line",
    "cardId": "sales_overview",
    "reportId": "dashboard",
    "data": [
      {"month": "Jan", "sales": 12000, "target": 10000},
      {"month": "Feb", "sales": 15000, "target": 12000},
      {"month": "Mar", "sales": 13500, "target": 13000}
    ],
    "meta": "{\"startedAt\":\"2024-01-01T12:00:00Z\",\"finishedAt\":\"2024-01-01T12:00:01Z\",\"elapsedMs\":100}"
  }
]
```

## Environment Configuration

### Database Integration

```python
# config.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql+asyncpg://user:password@localhost/dashboard"

engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
```

### Environment Variables

Create a `.env` file:

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost/dashboard
REDIS_URL=redis://localhost:6379/0
LOG_LEVEL=INFO
DEBUG=false
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

Load environment variables:

```python
# settings.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    redis_url: str = "redis://localhost:6379/0"
    log_level: str = "INFO"
    debug: bool = False
    cors_origins: list[str] = ["*"]
    
    class Config:
        env_file = ".env"

settings = Settings()
```

## Project Structure

Recommended project structure for larger applications:

```
my-dashboard-api/
├── main.py                 # FastAPI app and startup
├── settings.py            # Configuration
├── requirements.txt       # Dependencies
├── .env                   # Environment variables
├── cards/
│   ├── __init__.py
│   ├── sales.py          # Sales-related cards
│   ├── users.py          # User analytics cards  
│   └── system.py         # System metrics cards
├── models/
│   ├── __init__.py
│   └── database.py       # Database models
├── services/
│   ├── __init__.py
│   ├── analytics.py      # Business logic
│   └── external_api.py   # External API clients
└── tests/
    ├── test_cards.py
    └── test_services.py
```

## Docker Setup

Create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Create a `docker-compose.yml`:

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:password@db:5432/dashboard
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
      
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: dashboard
      POSTGRES_USER: postgres  
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

Run with Docker:

```bash
docker-compose up -d
```

## Verification

After setup, verify your installation works correctly:

### 1. Health Check Endpoint

```python
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}
```

### 2. API Documentation

FastAPI automatically generates interactive docs at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### 3. Test Card Endpoint

Your card should be accessible at:
`http://localhost:8000/api/cards/sales_overview`

## Next Steps

- [Quick Start Tutorial](quickstart.md) - Build your first complete dashboard
- [Card Types Reference](card-types.md) - Learn about different card types
- [Transport Protocols](transport.md) - Understand HTTP, WebSocket, and streaming
- [API Reference](api-reference.md) - Complete SDK documentation

## Troubleshooting

### Common Issues

**Import Error**: `ModuleNotFoundError: No module named 'cereon_sdk'`
```bash
# Ensure proper installation
pip install cereon-sdk --upgrade
```

**Port Already in Use**: 
```bash
# Use a different port
uvicorn main:app --port 8001
```

**CORS Errors**: 
```python
# Add proper CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Your frontend URL
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

### Getting Help

- Check the [API Reference](api-reference.md) for detailed documentation
- Browse [examples](examples/) for common patterns
- Open an issue on [GitHub](https://github.com/adimis-ai/cereon-sdk/issues)
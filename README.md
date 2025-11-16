# Cereon SDK

> ⚠️ CONSTRUCTION / BETA NOTICE: The official beta release of these packages is scheduled for 1st December 2025. Expect breaking changes until the beta is published. If you plan to depend on this library for production, please wait until the official beta.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) [![Python](https://img.shields.io/badge/Python-3.11-blue.svg?logo=python&logoColor=white)](https://www.python.org/) [![FastAPI](https://img.shields.io/badge/FastAPI-Ready-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)

**Cereon SDK** is a high-performance, typed FastAPI framework for building real-time dashboard backends. Create interactive dashboard cards with support for HTTP, WebSocket, and Server-Sent Events (SSE) transport protocols.

## 🚀 Quick Start

### Installation

```bash
pip install cereon-sdk
```

### Basic Example

Create your first dashboard card in minutes:

```python
from fastapi import FastAPI
from cereon_sdk import BaseCard, ChartCardRecord

app = FastAPI()

class SalesCard(BaseCard[ChartCardRecord]):
    kind = "line"
    card_id = "sales_overview"
    report_id = "dashboard"
    route_prefix = "/api/cards"
    response_model = ChartCardRecord
    transport = "http"

    @classmethod
    async def handler(cls, ctx):
        # Your data logic here
        data = [
            {"date": "2024-01-01", "sales": 1200},
            {"date": "2024-01-02", "sales": 1350},
        ]

        return [ChartCardRecord(
            kind=cls.kind,
            report_id=cls.report_id,
            card_id=cls.card_id,
            data=ChartCardData(data=data)
        )]

# Register the card
SalesCard(app).as_route(app=app)
```

Access your card at: `GET /api/cards/sales_overview`

## ✨ Key Features

### 🏗️ **Multiple Transport Protocols**

- **HTTP**: Traditional REST endpoints for static data
- **WebSocket**: Real-time bidirectional communication
- **Streaming HTTP**: Server-Sent Events for live data feeds

### 📊 **Rich Card Types**

- **Chart Cards**: Line, bar, area, pie, radar, and radial charts
- **Table Cards**: Sortable, filterable data tables
- **Number Cards**: KPIs with trend indicators
- **Markdown Cards**: Rich text and documentation
- **HTML/Iframe Cards**: Custom content embedding

### 🔧 **Developer Experience**

- **Type Safety**: Full Pydantic validation and type hints
- **Auto-Generated Routes**: Minimal boilerplate code
- **Flexible Data Sources**: Database, API, or custom integrations
- **Error Handling**: Built-in resilience and graceful degradation

## 📖 Documentation

| Guide                                        | Description                                   |
| -------------------------------------------- | --------------------------------------------- |
| [Installation & Setup](docs/installation.md) | Complete installation and configuration guide |
| [Quick Start Tutorial](docs/quickstart.md)   | Build your first dashboard in 10 minutes      |
| [Card Types Reference](docs/card-types.md)   | Complete guide to all supported card types    |
| [Transport Protocols](docs/transport.md)     | HTTP, WebSocket, and streaming patterns       |
| [API Reference](docs/api-reference.md)       | Complete SDK API documentation                |
| [Deployment Guide](docs/deployment.md)       | Production deployment strategies              |
| [Examples](docs/examples/)                   | Real-world implementation examples            |

## 🏃‍♂️ Quick Examples

### Real-time WebSocket Card

```python
class LivePricesCard(BaseCard[ChartCardRecord]):
    transport = "websocket"

    @classmethod
    async def handler(cls, ctx):
        while True:
            price_data = await fetch_live_prices()
            yield ChartCardRecord(...)
            await asyncio.sleep(1)
```

### Streaming HTTP Card

```python
class MetricsStreamCard(BaseCard[NumberCardRecord]):
    transport = "streaming-http"

    @classmethod
    async def handler(cls, ctx):
        async for metric in metrics_generator():
            yield NumberCardRecord(...)
```

### Database Integration

```python
class UserStatsCard(BaseCard[TableCardRecord]):
    @classmethod
    async def handler(cls, ctx):
        async with database.transaction():
            users = await User.fetch_analytics()

        return [TableCardRecord(
            data=TableCardData(
                rows=[u.dict() for u in users],
                columns=["name", "signup_date", "activity"]
            )
        )]
```

## 🏗️ Architecture

Cereon SDK follows a **card-based architecture** where each card represents a self-contained data visualization component:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Dashboard     │◄───│   Cereon SDK    │◄───│  Data Sources   │
│   Frontend      │    │   (FastAPI)     │    │  (DB/APIs/etc)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
        │                       │                       │
        │                       │                       │
    React Components       Card Classes            Your Logic
```

### Core Components

- **BaseCard**: Abstract base class for all dashboard cards
- **Transport Protocols**: HTTP, WebSocket, and streaming support
- **Type System**: Pydantic models for validation and serialization
- **Route Generation**: Automatic FastAPI route creation

## 🔌 Integration with Cereon Dashboard

Cereon SDK is designed to work seamlessly with [@cereon/dashboard](https://www.npmjs.com/package/@cereon/dashboard):

**Backend (Python)**:

```python
# Your FastAPI card
class RevenueCard(BaseCard[ChartCardRecord]):
    # ... implementation
```

**Frontend (React)**:

```tsx
import { Dashboard } from "@cereon/dashboard";

const spec = {
  reports: [
    {
      reportCards: [
        {
          kind: "line",
          query: {
            variant: "http",
            payload: { url: "/api/cards/revenue" },
          },
        },
      ],
    },
  ],
};

<Dashboard state={{ spec }} />;
```

## 🧪 Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=cereon_sdk

# Integration tests
pytest tests/integration/
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support & Community

- 📚 **Documentation**: [Full documentation](docs/)
- 🐛 **Issues**: [GitHub Issues](https://github.com/adimis-ai/cereon/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/adimis-ai/cereon/discussions)
- 🚀 **Examples**: [Live Examples](docs/examples/)

---

_Need help getting started? Check out our [Quick Start Guide](docs/quickstart.md) or browse the [examples](docs/examples/)._

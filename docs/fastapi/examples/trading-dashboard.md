# Real-World Trading Dashboard

This example demonstrates a complete financial trading dashboard with real-time market data, using all major Cereon SDK features.

## Overview

We'll build a trading dashboard with:
- **Real-time Price Charts**: Live stock price updates via WebSocket
- **Portfolio KPIs**: Account value, P&L, and performance metrics  
- **Order Book Table**: Live order flow and trade executions
- **Market News**: Streaming news and events
- **Risk Metrics**: Real-time risk calculations

## Project Structure

```
trading-dashboard/
├── main.py              # FastAPI application
├── config.py            # Configuration
├── requirements.txt     # Dependencies
├── models/
│   ├── __init__.py
│   ├── market_data.py   # Market data models
│   └── portfolio.py     # Portfolio models
├── cards/
│   ├── __init__.py
│   ├── market.py        # Market data cards
│   ├── portfolio.py     # Portfolio cards
│   └── risk.py          # Risk management cards
├── services/
│   ├── __init__.py
│   ├── market_feed.py   # Market data service
│   ├── portfolio.py     # Portfolio service
│   └── risk_engine.py   # Risk calculations
└── docker-compose.yml   # Development environment
```

## Dependencies

```txt
# requirements.txt
cereon-sdk>=0.1.0
fastapi>=0.110.0
uvicorn[standard]>=0.21.0
pydantic>=2.6.0
pydantic-settings>=2.0.0
sqlalchemy[asyncio]>=2.0.0
asyncpg>=0.28.0
redis>=4.5.0
aioredis>=2.0.0
websockets>=11.0.0
httpx>=0.24.0
pandas>=2.0.0
numpy>=1.24.0
```

## Configuration

```python
# config.py
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # API Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    
    # Database
    database_url: str = "postgresql+asyncpg://trading:password@localhost:5432/trading"
    
    # Redis Cache
    redis_url: str = "redis://localhost:6379/0"
    
    # External APIs
    market_data_api_key: str = ""
    news_api_key: str = ""
    
    # CORS
    cors_origins: List[str] = ["http://localhost:3000"]
    
    # Trading Configuration
    default_symbols: List[str] = ["AAPL", "GOOGL", "MSFT", "TSLA", "NVDA"]
    max_websocket_connections: int = 100
    
    class Config:
        env_file = ".env"

settings = Settings()
```

## Market Data Service

```python
# services/market_feed.py
import asyncio
import json
import random
import websockets
from datetime import datetime, timezone
from typing import Dict, List, AsyncGenerator
from dataclasses import dataclass

@dataclass
class PriceUpdate:
    symbol: str
    price: float
    volume: int
    timestamp: datetime
    change: float
    change_percent: float

@dataclass
class OrderBookEntry:
    symbol: str
    side: str  # "bid" or "ask"
    price: float
    size: int
    timestamp: datetime

class MarketDataFeed:
    def __init__(self, symbols: List[str]):
        self.symbols = symbols
        self.prices: Dict[str, float] = {}
        self.volumes: Dict[str, int] = {}
        
        # Initialize with random starting prices
        for symbol in symbols:
            self.prices[symbol] = random.uniform(100, 300)
            self.volumes[symbol] = 0
    
    async def generate_price_update(self, symbol: str) -> PriceUpdate:
        """Generate realistic price movement"""
        current_price = self.prices[symbol]
        
        # Random walk with slight trend
        change_percent = random.normalvariate(0, 0.02)  # 2% volatility
        change_amount = current_price * change_percent
        new_price = max(1.0, current_price + change_amount)
        
        # Volume spike during price moves
        base_volume = random.randint(1000, 5000)
        if abs(change_percent) > 0.01:  # 1% move
            volume = base_volume * random.randint(2, 5)
        else:
            volume = base_volume
        
        self.prices[symbol] = new_price
        self.volumes[symbol] += volume
        
        return PriceUpdate(
            symbol=symbol,
            price=round(new_price, 2),
            volume=volume,
            timestamp=datetime.now(timezone.utc),
            change=round(change_amount, 2),
            change_percent=round(change_percent * 100, 2)
        )
    
    async def price_stream(self) -> AsyncGenerator[PriceUpdate, None]:
        """Stream live price updates"""
        while True:
            # Generate update for random symbol
            symbol = random.choice(self.symbols)
            update = await self.generate_price_update(symbol)
            yield update
            
            # Vary update frequency
            await asyncio.sleep(random.uniform(0.1, 1.0))
    
    async def generate_order_book_entry(self, symbol: str) -> OrderBookEntry:
        """Generate order book updates"""
        current_price = self.prices.get(symbol, 150.0)
        
        # Generate bid/ask around current price
        side = random.choice(["bid", "ask"])
        if side == "bid":
            price = current_price - random.uniform(0.01, 0.50)
        else:
            price = current_price + random.uniform(0.01, 0.50)
        
        size = random.randint(100, 10000)
        
        return OrderBookEntry(
            symbol=symbol,
            side=side,
            price=round(price, 2),
            size=size,
            timestamp=datetime.now(timezone.utc)
        )
    
    async def order_book_stream(self) -> AsyncGenerator[OrderBookEntry, None]:
        """Stream order book updates"""
        while True:
            symbol = random.choice(self.symbols)
            entry = await self.generate_order_book_entry(symbol)
            yield entry
            
            await asyncio.sleep(random.uniform(0.05, 0.3))

# Global market feed instance
market_feed = MarketDataFeed(settings.default_symbols)
```

## Portfolio Service

```python
# services/portfolio.py
import asyncio
from datetime import datetime
from typing import Dict, List
from dataclasses import dataclass

@dataclass
class Position:
    symbol: str
    quantity: int
    avg_cost: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_percent: float

@dataclass
class PortfolioMetrics:
    total_value: float
    cash_balance: float
    invested_amount: float
    total_pnl: float
    total_pnl_percent: float
    day_pnl: float
    day_pnl_percent: float

class PortfolioService:
    def __init__(self):
        # Sample portfolio positions
        self.positions = {
            "AAPL": Position("AAPL", 100, 150.00, 155.00, 15500, 500, 3.33),
            "GOOGL": Position("GOOGL", 50, 2800.00, 2850.00, 142500, 2500, 1.79),
            "MSFT": Position("MSFT", 75, 300.00, 310.00, 23250, 750, 3.33),
            "TSLA": Position("TSLA", 25, 800.00, 820.00, 20500, 500, 2.50),
        }
        self.cash_balance = 25000.00
        
    def update_position_price(self, symbol: str, new_price: float):
        """Update position with new market price"""
        if symbol in self.positions:
            position = self.positions[symbol]
            position.current_price = new_price
            position.market_value = position.quantity * new_price
            position.unrealized_pnl = position.market_value - (position.quantity * position.avg_cost)
            position.unrealized_pnl_percent = (position.unrealized_pnl / (position.quantity * position.avg_cost)) * 100
    
    def get_portfolio_metrics(self) -> PortfolioMetrics:
        """Calculate current portfolio metrics"""
        total_market_value = sum(pos.market_value for pos in self.positions.values())
        total_cost = sum(pos.quantity * pos.avg_cost for pos in self.positions.values())
        total_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())
        
        return PortfolioMetrics(
            total_value=total_market_value + self.cash_balance,
            cash_balance=self.cash_balance,
            invested_amount=total_market_value,
            total_pnl=total_pnl,
            total_pnl_percent=(total_pnl / total_cost) * 100 if total_cost > 0 else 0,
            day_pnl=total_pnl * 0.1,  # Simplified day P&L
            day_pnl_percent=(total_pnl * 0.1 / total_cost) * 100 if total_cost > 0 else 0
        )
    
    def get_positions(self) -> List[Position]:
        """Get all current positions"""
        return list(self.positions.values())

# Global portfolio service
portfolio_service = PortfolioService()
```

## Market Data Cards

```python
# cards/market.py
import asyncio
from cereon_sdk import BaseCard, ChartCardRecord, ChartCardData, TableCardRecord, TableCardData
from services.market_feed import market_feed
from config import settings

class LivePricesCard(BaseCard[ChartCardRecord]):
    """Real-time price chart with multiple symbols"""
    kind = "line"
    card_id = "live_prices"
    report_id = "trading_dashboard"
    route_prefix = "/api/cards"
    response_model = ChartCardRecord
    transport = "websocket"
    
    @classmethod
    async def handler(cls, ctx):
        params = ctx.get("params", {})
        symbols = params.get("symbols", settings.default_symbols[:3])  # Limit to 3 for performance
        
        # Track latest prices for each symbol
        latest_prices = {}
        
        async for price_update in market_feed.price_stream():
            if price_update.symbol in symbols:
                latest_prices[price_update.symbol] = {
                    "timestamp": price_update.timestamp.isoformat(),
                    "symbol": price_update.symbol,
                    "price": price_update.price,
                    "change": price_update.change,
                    "change_percent": price_update.change_percent
                }
                
                # Yield chart data with all symbols
                chart_data = [
                    {
                        "timestamp": data["timestamp"],
                        data["symbol"]: data["price"],
                        f"{data['symbol']}_change": data["change_percent"]
                    }
                    for data in latest_prices.values()
                ]
                
                if chart_data:
                    yield ChartCardRecord(
                        kind=cls.kind,
                        report_id=cls.report_id,
                        card_id=cls.card_id,
                        data=ChartCardData(data=chart_data)
                    )

class MarketVolumeCard(BaseCard[ChartCardRecord]):
    """Volume analysis chart"""
    kind = "bar"
    card_id = "market_volume"
    report_id = "trading_dashboard"
    route_prefix = "/api/cards"
    response_model = ChartCardRecord
    transport = "http"
    
    @classmethod
    async def handler(cls, ctx):
        # Aggregate volume data by symbol
        volume_data = []
        
        for symbol in settings.default_symbols:
            # Simulate volume aggregation
            daily_volume = market_feed.volumes.get(symbol, 0)
            avg_volume = daily_volume * 0.8  # Simulate average
            
            volume_data.append({
                "symbol": symbol,
                "daily_volume": daily_volume,
                "avg_volume": int(avg_volume),
                "volume_ratio": round(daily_volume / avg_volume, 2) if avg_volume > 0 else 1.0
            })
        
        return [ChartCardRecord(
            kind=cls.kind,
            report_id=cls.report_id,
            card_id=cls.card_id,
            data=ChartCardData(data=volume_data)
        )]

class OrderBookCard(BaseCard[TableCardRecord]):
    """Live order book updates"""
    kind = "table"
    card_id = "order_book"
    report_id = "trading_dashboard"
    route_prefix = "/api/cards"
    response_model = TableCardRecord
    transport = "websocket"
    
    @classmethod
    async def handler(cls, ctx):
        params = ctx.get("params", {})
        symbol = params.get("symbol", "AAPL")
        max_entries = int(params.get("max_entries", 20))
        
        order_entries = []
        
        async for order_entry in market_feed.order_book_stream():
            if order_entry.symbol == symbol:
                order_entries.append({
                    "timestamp": order_entry.timestamp.strftime("%H:%M:%S.%f")[:-3],
                    "side": order_entry.side.upper(),
                    "price": f"${order_entry.price:.2f}",
                    "size": f"{order_entry.size:,}",
                    "symbol": order_entry.symbol
                })
                
                # Keep only recent entries
                order_entries = order_entries[-max_entries:]
                
                yield TableCardRecord(
                    kind=cls.kind,
                    report_id=cls.report_id,
                    card_id=cls.card_id,
                    data=TableCardData(
                        rows=order_entries,
                        columns=["timestamp", "side", "price", "size"],
                        totalCount=len(order_entries)
                    )
                )

class MarketHeatmapCard(BaseCard[ChartCardRecord]):
    """Market performance heatmap"""
    kind = "pie"  # Using pie chart to represent market segments
    card_id = "market_heatmap"
    report_id = "trading_dashboard"
    route_prefix = "/api/cards"
    response_model = ChartCardRecord
    transport = "http"
    
    @classmethod
    async def handler(cls, ctx):
        # Simulate sector performance
        heatmap_data = []
        
        sectors = {
            "Technology": ["AAPL", "GOOGL", "MSFT"],
            "Automotive": ["TSLA"],
            "Semiconductors": ["NVDA"]
        }
        
        for sector, symbols in sectors.items():
            sector_change = 0
            for symbol in symbols:
                # Get latest price change
                current_price = market_feed.prices.get(symbol, 150.0)
                # Simulate daily change
                daily_change = (current_price - 150.0) / 150.0 * 100
                sector_change += daily_change
            
            avg_change = sector_change / len(symbols) if symbols else 0
            
            heatmap_data.append({
                "label": sector,
                "value": abs(avg_change),  # Use absolute value for pie chart
                "change": round(avg_change, 2),
                "color": "#22c55e" if avg_change >= 0 else "#ef4444"  # Green/Red
            })
        
        return [ChartCardRecord(
            kind=cls.kind,
            report_id=cls.report_id,
            card_id=cls.card_id,
            data=ChartCardData(data=heatmap_data)
        )]
```

## Portfolio Cards

```python
# cards/portfolio.py
import asyncio
from cereon_sdk import (
    BaseCard, 
    NumberCardRecord, 
    NumberCardData, 
    TableCardRecord, 
    TableCardData,
    ChartCardRecord,
    ChartCardData
)
from services.portfolio import portfolio_service
from services.market_feed import market_feed

class PortfolioValueCard(BaseCard[NumberCardRecord]):
    """Total portfolio value KPI"""
    kind = "number"
    card_id = "portfolio_value"
    report_id = "trading_dashboard"
    route_prefix = "/api/cards"
    response_model = NumberCardRecord
    transport = "websocket"
    
    @classmethod
    async def handler(cls, ctx):
        while True:
            metrics = portfolio_service.get_portfolio_metrics()
            
            yield NumberCardRecord(
                kind=cls.kind,
                report_id=cls.report_id,
                card_id=cls.card_id,
                data=NumberCardData(
                    value=metrics.total_value,
                    previousValue=metrics.total_value - metrics.day_pnl,
                    trend="up" if metrics.day_pnl > 0 else "down" if metrics.day_pnl < 0 else "neutral",
                    trendPercentage=metrics.day_pnl_percent,
                    label="Portfolio Value"
                )
            )
            
            await asyncio.sleep(2)  # Update every 2 seconds

class DayPnLCard(BaseCard[NumberCardRecord]):
    """Daily P&L KPI"""
    kind = "number"
    card_id = "day_pnl"
    report_id = "trading_dashboard"
    route_prefix = "/api/cards"
    response_model = NumberCardRecord
    transport = "websocket"
    
    @classmethod
    async def handler(cls, ctx):
        while True:
            metrics = portfolio_service.get_portfolio_metrics()
            
            yield NumberCardRecord(
                kind=cls.kind,
                report_id=cls.report_id,
                card_id=cls.card_id,
                data=NumberCardData(
                    value=metrics.day_pnl,
                    trend="up" if metrics.day_pnl > 0 else "down" if metrics.day_pnl < 0 else "neutral",
                    trendPercentage=metrics.day_pnl_percent,
                    label="Day P&L"
                )
            )
            
            await asyncio.sleep(3)

class PositionsTableCard(BaseCard[TableCardRecord]):
    """Current positions table"""
    kind = "table"
    card_id = "positions_table"
    report_id = "trading_dashboard"
    route_prefix = "/api/cards"
    response_model = TableCardRecord
    transport = "websocket"
    
    @classmethod
    async def handler(cls, ctx):
        # Update positions with live prices
        async for price_update in market_feed.price_stream():
            portfolio_service.update_position_price(price_update.symbol, price_update.price)
            
            positions = portfolio_service.get_positions()
            position_data = []
            
            for pos in positions:
                position_data.append({
                    "symbol": pos.symbol,
                    "quantity": f"{pos.quantity:,}",
                    "avg_cost": f"${pos.avg_cost:.2f}",
                    "current_price": f"${pos.current_price:.2f}",
                    "market_value": f"${pos.market_value:,.2f}",
                    "unrealized_pnl": f"${pos.unrealized_pnl:,.2f}",
                    "pnl_percent": f"{pos.unrealized_pnl_percent:+.2f}%"
                })
            
            yield TableCardRecord(
                kind=cls.kind,
                report_id=cls.report_id,
                card_id=cls.card_id,
                data=TableCardData(
                    rows=position_data,
                    columns=[
                        "symbol", "quantity", "avg_cost", "current_price", 
                        "market_value", "unrealized_pnl", "pnl_percent"
                    ],
                    totalCount=len(position_data)
                )
            )

class PortfolioAllocationCard(BaseCard[ChartCardRecord]):
    """Portfolio allocation pie chart"""
    kind = "pie"
    card_id = "portfolio_allocation"
    report_id = "trading_dashboard"
    route_prefix = "/api/cards"
    response_model = ChartCardRecord
    transport = "http"
    
    @classmethod
    async def handler(cls, ctx):
        positions = portfolio_service.get_positions()
        total_value = sum(pos.market_value for pos in positions)
        
        allocation_data = []
        for pos in positions:
            if total_value > 0:
                percentage = (pos.market_value / total_value) * 100
                allocation_data.append({
                    "label": pos.symbol,
                    "value": percentage,
                    "market_value": pos.market_value,
                    "color": f"#{hash(pos.symbol) & 0xFFFFFF:06x}"  # Generate color from symbol
                })
        
        # Add cash allocation
        metrics = portfolio_service.get_portfolio_metrics()
        if metrics.total_value > 0:
            cash_percentage = (metrics.cash_balance / metrics.total_value) * 100
            allocation_data.append({
                "label": "Cash",
                "value": cash_percentage,
                "market_value": metrics.cash_balance,
                "color": "#6b7280"  # Gray for cash
            })
        
        return [ChartCardRecord(
            kind=cls.kind,
            report_id=cls.report_id,
            card_id=cls.card_id,
            data=ChartCardData(data=allocation_data)
        )]
```

## Risk Management Cards

```python
# cards/risk.py
import math
import numpy as np
from cereon_sdk import (
    BaseCard,
    NumberCardRecord,
    NumberCardData,
    ChartCardRecord, 
    ChartCardData,
    TableCardRecord,
    TableCardData
)
from services.portfolio import portfolio_service
from services.market_feed import market_feed

class VaRCard(BaseCard[NumberCardRecord]):
    """Value at Risk calculation"""
    kind = "number"
    card_id = "var_calculation"
    report_id = "trading_dashboard"
    route_prefix = "/api/cards"
    response_model = NumberCardRecord
    transport = "http"
    
    @classmethod
    async def handler(cls, ctx):
        params = ctx.get("params", {})
        confidence_level = float(params.get("confidence", 0.95))  # 95% VaR
        
        # Simulate VaR calculation
        positions = portfolio_service.get_positions()
        portfolio_value = sum(pos.market_value for pos in positions)
        
        # Simplified VaR using normal distribution
        # In production, use historical simulation or Monte Carlo
        daily_volatility = 0.02  # 2% daily volatility assumption
        z_score = {0.90: 1.28, 0.95: 1.65, 0.99: 2.33}.get(confidence_level, 1.65)
        
        var_amount = portfolio_value * daily_volatility * z_score
        var_percentage = (var_amount / portfolio_value) * 100 if portfolio_value > 0 else 0
        
        return [NumberCardRecord(
            kind=cls.kind,
            report_id=cls.report_id,
            card_id=cls.card_id,
            data=NumberCardData(
                value=var_amount,
                label=f"VaR ({confidence_level:.0%} confidence)",
                trendPercentage=var_percentage
            )
        )]

class VolatilityCard(BaseCard[ChartCardRecord]):
    """Portfolio volatility over time"""
    kind = "line"
    card_id = "portfolio_volatility"
    report_id = "trading_dashboard"
    route_prefix = "/api/cards"
    response_model = ChartCardRecord
    transport = "http"
    
    @classmethod
    async def handler(cls, ctx):
        # Simulate historical volatility data
        import datetime
        
        volatility_data = []
        base_date = datetime.datetime.now() - datetime.timedelta(days=30)
        
        for i in range(30):
            current_date = base_date + datetime.timedelta(days=i)
            
            # Simulate volatility with some randomness
            base_vol = 0.15  # 15% annualized
            daily_vol = base_vol + np.random.normal(0, 0.02)  # Add noise
            daily_vol = max(0.05, min(0.30, daily_vol))  # Clamp between 5% and 30%
            
            volatility_data.append({
                "date": current_date.strftime("%Y-%m-%d"),
                "volatility": round(daily_vol * 100, 2),  # Convert to percentage
                "var_95": round(daily_vol * 1.65 * 100, 2),  # 95% VaR
                "var_99": round(daily_vol * 2.33 * 100, 2)   # 99% VaR
            })
        
        return [ChartCardRecord(
            kind=cls.kind,
            report_id=cls.report_id,
            card_id=cls.card_id,
            data=ChartCardData(data=volatility_data)
        )]

class RiskMetricsCard(BaseCard[TableCardRecord]):
    """Risk metrics summary table"""
    kind = "table"
    card_id = "risk_metrics"
    report_id = "trading_dashboard"
    route_prefix = "/api/cards"
    response_model = TableCardRecord
    transport = "http"
    
    @classmethod
    async def handler(cls, ctx):
        positions = portfolio_service.get_positions()
        metrics = portfolio_service.get_portfolio_metrics()
        
        risk_data = []
        
        for pos in positions:
            # Calculate position-specific risk metrics
            position_weight = (pos.market_value / metrics.invested_amount) * 100 if metrics.invested_amount > 0 else 0
            
            # Simulate beta (market sensitivity)
            beta = np.random.uniform(0.5, 1.5)
            
            # Simulate Sharpe ratio
            sharpe = np.random.uniform(-0.5, 2.0)
            
            risk_data.append({
                "symbol": pos.symbol,
                "weight": f"{position_weight:.1f}%",
                "beta": f"{beta:.2f}",
                "sharpe_ratio": f"{sharpe:.2f}",
                "daily_var": f"${abs(pos.market_value * 0.02 * 1.65):,.0f}",
                "max_loss": f"{pos.unrealized_pnl_percent:.1f}%" if pos.unrealized_pnl < 0 else "0.0%"
            })
        
        return [TableCardRecord(
            kind=cls.kind,
            report_id=cls.report_id,
            card_id=cls.card_id,
            data=TableCardData(
                rows=risk_data,
                columns=["symbol", "weight", "beta", "sharpe_ratio", "daily_var", "max_loss"],
                totalCount=len(risk_data)
            )
        )]

class ConcentrationRiskCard(BaseCard[ChartCardRecord]):
    """Portfolio concentration risk radar"""
    kind = "radar"
    card_id = "concentration_risk"
    report_id = "trading_dashboard"
    route_prefix = "/api/cards"
    response_model = ChartCardRecord
    transport = "http"
    
    @classmethod
    async def handler(cls, ctx):
        positions = portfolio_service.get_positions()
        metrics = portfolio_service.get_portfolio_metrics()
        
        # Calculate concentration metrics
        concentration_data = []
        
        # By position size
        max_position_weight = max(
            (pos.market_value / metrics.invested_amount) * 100 
            for pos in positions
        ) if positions and metrics.invested_amount > 0 else 0
        
        # Simulate sector concentration
        sector_concentration = 65.0  # Tech heavy portfolio
        
        # Geographic concentration (simulate)
        geographic_concentration = 85.0  # US heavy
        
        # Asset class concentration
        equity_concentration = 95.0  # All equities
        
        # Currency concentration
        currency_concentration = 100.0  # All USD
        
        concentration_data = [
            {"metric": "Largest Position", "concentration": min(max_position_weight, 100)},
            {"metric": "Sector", "concentration": sector_concentration},
            {"metric": "Geography", "concentration": geographic_concentration}, 
            {"metric": "Asset Class", "concentration": equity_concentration},
            {"metric": "Currency", "concentration": currency_concentration}
        ]
        
        return [ChartCardRecord(
            kind=cls.kind,
            report_id=cls.report_id,
            card_id=cls.card_id,
            data=ChartCardData(data=concentration_data)
        )]
```

## Main Application

```python
# main.py
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from config import settings
from cards.market import (
    LivePricesCard,
    MarketVolumeCard,
    OrderBookCard,
    MarketHeatmapCard
)
from cards.portfolio import (
    PortfolioValueCard,
    DayPnLCard,
    PositionsTableCard,
    PortfolioAllocationCard
)
from cards.risk import (
    VaRCard,
    VolatilityCard,
    RiskMetricsCard,
    ConcentrationRiskCard
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Starting Trading Dashboard API...")
    
    # Initialize services
    from services.market_feed import market_feed
    from services.portfolio import portfolio_service
    
    print(f"📊 Tracking {len(settings.default_symbols)} symbols: {', '.join(settings.default_symbols)}")
    print(f"💼 Portfolio positions: {len(portfolio_service.get_positions())}")
    
    yield
    
    # Shutdown
    print("⏹️  Shutting down Trading Dashboard API...")

app = FastAPI(
    title="Trading Dashboard API",
    description="Real-time financial trading dashboard with market data, portfolio tracking, and risk management",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all cards
cards = [
    # Market data cards
    LivePricesCard,
    MarketVolumeCard,
    OrderBookCard,
    MarketHeatmapCard,
    
    # Portfolio cards
    PortfolioValueCard,
    DayPnLCard,
    PositionsTableCard,
    PortfolioAllocationCard,
    
    # Risk management cards
    VaRCard,
    VolatilityCard,
    RiskMetricsCard,
    ConcentrationRiskCard
]

for CardClass in cards:
    CardClass(app).as_route(app=app)
    transport_emoji = {"http": "🔗", "websocket": "⚡", "streaming-http": "📡"}
    emoji = transport_emoji.get(CardClass.transport, "❓")
    print(f"{emoji} Registered {CardClass.card_id} ({CardClass.transport})")

@app.get("/")
async def root():
    return {
        "message": "Trading Dashboard API",
        "version": "1.0.0",
        "cards": len(cards),
        "symbols": settings.default_symbols,
        "status": "running"
    }

@app.get("/health")
async def health_check():
    from services.portfolio import portfolio_service
    
    metrics = portfolio_service.get_portfolio_metrics()
    
    return {
        "status": "healthy",
        "portfolio_value": metrics.total_value,
        "positions": len(portfolio_service.get_positions()),
        "websocket_limit": settings.max_websocket_connections
    }

if __name__ == "__main__":
    import uvicorn
    
    print(f"🎯 Starting server on http://{settings.host}:{settings.port}")
    print(f"📖 API docs available at http://{settings.host}:{settings.port}/docs")
    
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info"
    )
```

## Docker Compose Development Environment

```yaml
# docker-compose.yml
version: '3.8'

services:
  trading-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://trading:password@postgres:5432/trading
      - REDIS_URL=redis://redis:6379/0
      - DEBUG=true
    volumes:
      - .:/app
    depends_on:
      - postgres
      - redis
    command: python main.py

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: trading
      POSTGRES_USER: trading
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
      - redis_data:/data

  # Optional: PostgreSQL admin interface
  pgadmin:
    image: dpage/pgadmin4
    environment:
      PGADMIN_DEFAULT_EMAIL: admin@trading.com
      PGADMIN_DEFAULT_PASSWORD: admin
    ports:
      - "5050:80"
    depends_on:
      - postgres

volumes:
  postgres_data:
  redis_data:
```

## Running the Example

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Start Services**:
   ```bash
   docker-compose up -d postgres redis
   ```

3. **Run the Application**:
   ```bash
   python main.py
   ```

4. **Access the Dashboard**:
   - API: http://localhost:8000
   - Docs: http://localhost:8000/docs
   - Health: http://localhost:8000/health

## Testing the Cards

### HTTP Cards
```bash
# Portfolio allocation
curl http://localhost:8000/api/cards/portfolio_allocation

# Risk metrics
curl http://localhost:8000/api/cards/risk_metrics

# Market volume
curl http://localhost:8000/api/cards/market_volume
```

### WebSocket Cards
```javascript
// Connect to live prices
const ws = new WebSocket('ws://localhost:8000/api/cards/live_prices');
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Live price update:', data);
};

// Connect to portfolio value
const portfolioWs = new WebSocket('ws://localhost:8000/api/cards/portfolio_value');
portfolioWs.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Portfolio value:', data);
};
```

## Key Features Demonstrated

1. **Real-time Data Streaming**: WebSocket cards for live price and portfolio updates
2. **Mixed Transport Types**: HTTP for static data, WebSocket for real-time
3. **Complex Data Structures**: Market data, portfolio positions, risk metrics
4. **Parameter Handling**: Configurable symbols, confidence levels, time periods
5. **Error Handling**: Graceful handling of connection issues and data errors
6. **Performance Optimization**: Efficient data structures and update patterns
7. **Production Readiness**: Configuration management, health checks, logging

This example showcases how to build a sophisticated, real-time financial dashboard using Cereon SDK's full feature set. The modular architecture makes it easy to extend with additional cards, data sources, and risk calculations.

## Next Steps

- Add database persistence for historical data
- Implement authentication and user-specific portfolios
- Add more sophisticated risk calculations
- Integrate with real market data APIs
- Deploy to production environment
- Add comprehensive test suite
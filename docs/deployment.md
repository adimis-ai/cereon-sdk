# Production Deployment Guide

This guide covers deploying Cereon SDK applications to production environments with best practices for performance, security, and reliability.

## Quick Deployment Checklist

- [ ] **Environment Configuration**: Set up production environment variables
- [ ] **Security**: Configure authentication, CORS, and HTTPS
- [ ] **Database**: Set up connection pooling and migrations  
- [ ] **Caching**: Implement Redis or in-memory caching
- [ ] **Monitoring**: Set up logging, metrics, and health checks
- [ ] **Load Balancing**: Configure reverse proxy and load balancing
- [ ] **Scaling**: Plan for horizontal scaling and WebSocket session management
- [ ] **Backup**: Set up automated backups and disaster recovery

## Environment Configuration

### Production Settings

Create a production configuration file:

```python
# config/production.py
import os
from pydantic_settings import BaseSettings

class ProductionSettings(BaseSettings):
    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4
    reload: bool = False
    debug: bool = False
    
    # Database
    database_url: str
    database_pool_size: int = 20
    database_max_overflow: int = 30
    
    # Redis Cache
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl: int = 300  # 5 minutes
    
    # Security
    secret_key: str
    allowed_hosts: list[str] = ["yourdomain.com"]
    cors_origins: list[str] = ["https://yourdomain.com"]
    
    # Monitoring
    log_level: str = "INFO"
    sentry_dsn: str = ""
    
    # Performance
    max_websocket_connections: int = 1000
    heartbeat_interval: int = 30000
    
    class Config:
        env_file = ".env.production"
        case_sensitive = False

settings = ProductionSettings()
```

### Environment Variables

Create `.env.production`:

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:password@db-host:5432/dashboard_prod
DATABASE_POOL_SIZE=20

# Redis
REDIS_URL=redis://redis-host:6379/0

# Security
SECRET_KEY=your-super-secret-key-here
ALLOWED_HOSTS=yourdomain.com,api.yourdomain.com
CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com

# Monitoring
LOG_LEVEL=INFO
SENTRY_DSN=https://your-sentry-dsn-here

# Performance
MAX_WEBSOCKET_CONNECTIONS=1000
WORKERS=4
```

## Docker Deployment

### Multi-stage Dockerfile

```dockerfile
# Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11-slim

WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local

# Create non-root user
RUN groupadd -r dashboard && useradd -r -g dashboard dashboard

# Copy application code
COPY --chown=dashboard:dashboard . .

# Switch to non-root user
USER dashboard

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start command
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### Docker Compose Production

```yaml
version: '3.8'

services:
  dashboard-api:
    build: .
    restart: unless-stopped
    environment:
      - DATABASE_URL=postgresql+asyncpg://dashboard:${DB_PASSWORD}@postgres:5432/dashboard
      - REDIS_URL=redis://redis:6379/0
      - SECRET_KEY=${SECRET_KEY}
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - dashboard-network
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.api.rule=Host(`api.yourdomain.com`)"
      - "traefik.http.routers.api.tls=true"
      - "traefik.http.routers.api.tls.certresolver=letsencrypt"

  postgres:
    image: postgres:15-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: dashboard
      POSTGRES_USER: dashboard
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U dashboard"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - dashboard-network

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    command: redis-server --appendonly yes --maxmemory 512mb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 3s
      retries: 3
    networks:
      - dashboard-network

  nginx:
    image: nginx:alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - dashboard-api
    networks:
      - dashboard-network

volumes:
  postgres_data:
  redis_data:

networks:
  dashboard-network:
    driver: bridge
```

## Load Balancing & Reverse Proxy

### Nginx Configuration

```nginx
# nginx.conf
upstream dashboard_backend {
    least_conn;
    server dashboard-api-1:8000 max_fails=3 fail_timeout=30s;
    server dashboard-api-2:8000 max_fails=3 fail_timeout=30s;
    server dashboard-api-3:8000 max_fails=3 fail_timeout=30s;
}

upstream dashboard_websocket {
    ip_hash;  # Sticky sessions for WebSocket
    server dashboard-api-1:8000;
    server dashboard-api-2:8000;  
    server dashboard-api-3:8000;
}

server {
    listen 80;
    server_name api.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;
    
    # SSL Configuration
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    
    # Security Headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload";
    
    # Gzip Compression
    gzip on;
    gzip_vary on;
    gzip_types text/plain application/json application/javascript text/css;
    
    # Rate Limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=websocket:10m rate=5r/s;
    
    # API Routes
    location /api/ {
        limit_req zone=api burst=20 nodelay;
        
        proxy_pass http://dashboard_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # WebSocket Routes
    location /api/cards/ {
        limit_req zone=websocket burst=10 nodelay;
        
        # Check for WebSocket upgrade
        if ($http_upgrade = "websocket") {
            proxy_pass http://dashboard_websocket;
        }
        if ($http_upgrade != "websocket") {
            proxy_pass http://dashboard_backend;
        }
        
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket timeouts
        proxy_read_timeout 7d;
        proxy_send_timeout 7d;
    }
    
    # Health Check
    location /health {
        proxy_pass http://dashboard_backend;
        access_log off;
    }
}
```

### Traefik Configuration (Alternative)

```yaml
# traefik.yml
version: '3.8'

services:
  traefik:
    image: traefik:v3.0
    command:
      - "--api.dashboard=true"
      - "--providers.docker=true"
      - "--providers.docker.exposedbydefault=false"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
      - "--certificatesresolvers.letsencrypt.acme.email=admin@yourdomain.com"
      - "--certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json"
      - "--certificatesresolvers.letsencrypt.acme.httpchallenge.entrypoint=web"
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./letsencrypt:/letsencrypt
    networks:
      - traefik

  dashboard-api:
    image: your-registry/dashboard-api:latest
    deploy:
      replicas: 3
      update_config:
        parallelism: 1
        delay: 10s
      restart_policy:
        condition: on-failure
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.api.rule=Host(`api.yourdomain.com`)"
      - "traefik.http.routers.api.entrypoints=websecure"
      - "traefik.http.routers.api.tls.certresolver=letsencrypt"
      - "traefik.http.services.api.loadbalancer.server.port=8000"
      - "traefik.http.services.api.loadbalancer.sticky.cookie=true"
    networks:
      - traefik
      - backend

networks:
  traefik:
    external: true
  backend:
    driver: overlay
```

## Database Configuration

### Connection Pooling

```python
# database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool, QueuePool
from config import settings

# Production engine with connection pooling
engine = create_async_engine(
    settings.database_url,
    
    # Connection pooling
    poolclass=QueuePool,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_pre_ping=True,
    pool_recycle=3600,  # 1 hour
    
    # Performance
    echo=False,
    future=True,
    
    # Connection parameters
    connect_args={
        "server_settings": {
            "jit": "off",  # Disable JIT for consistent performance
            "application_name": "dashboard-api",
        },
        "command_timeout": 60,
    }
)

AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# Health check
async def check_db_health():
    try:
        async with AsyncSessionLocal() as session:
            await session.execute("SELECT 1")
        return {"status": "healthy"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

### Database Migrations

Using Alembic for database migrations:

```python
# alembic/env.py
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context
from config import settings
import asyncio

config = context.config

# Set database URL from settings
config.set_main_option("sqlalchemy.url", settings.database_url.replace("+asyncpg", ""))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations() -> None:
    connectable = create_async_engine(
        settings.database_url,
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

## Caching Strategy

### Redis Configuration

```python
# cache.py
import redis.asyncio as redis
import json
import pickle
from typing import Any, Optional
from config import settings

# Redis connection pool
redis_pool = redis.ConnectionPool.from_url(
    settings.redis_url,
    max_connections=20,
    retry_on_timeout=True,
    socket_connect_timeout=5,
    socket_timeout=5,
    health_check_interval=30
)

redis_client = redis.Redis(connection_pool=redis_pool)

class CacheManager:
    def __init__(self, ttl: int = settings.cache_ttl):
        self.ttl = ttl
        
    async def get(self, key: str) -> Optional[Any]:
        try:
            value = await redis_client.get(key)
            if value:
                return pickle.loads(value)
        except Exception as e:
            print(f"Cache get error: {e}")
        return None
        
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        try:
            serialized = pickle.dumps(value)
            await redis_client.set(key, serialized, ex=ttl or self.ttl)
            return True
        except Exception as e:
            print(f"Cache set error: {e}")
            return False
            
    async def delete(self, key: str) -> bool:
        try:
            await redis_client.delete(key)
            return True
        except Exception as e:
            print(f"Cache delete error: {e}")
            return False
            
    async def health_check(self) -> dict:
        try:
            await redis_client.ping()
            return {"status": "healthy"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

cache = CacheManager()

# Decorator for caching card results
def cached_card(ttl: int = 300):
    def decorator(handler_func):
        async def wrapper(cls, ctx):
            # Generate cache key from card_id and parameters
            params = ctx.get("params", {})
            cache_key = f"card:{cls.card_id}:{hash(str(sorted(params.items())))}"
            
            # Try to get from cache
            cached_result = await cache.get(cache_key)
            if cached_result:
                return cached_result
                
            # Execute handler and cache result
            result = await handler_func(cls, ctx)
            await cache.set(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator
```

### Caching Implementation

```python
# Example cached card
class CachedAnalyticsCard(BaseCard[ChartCardRecord]):
    kind = "line"
    transport = "http"
    
    @cached_card(ttl=600)  # Cache for 10 minutes
    @classmethod
    async def handler(cls, ctx):
        # Expensive analytics computation
        data = await compute_complex_analytics()
        
        return [ChartCardRecord(
            kind=cls.kind,
            report_id=cls.report_id,
            card_id=cls.card_id,
            data=ChartCardData(data=data)
        )]
```

## Monitoring & Observability

### Logging Configuration

```python
# logging_config.py
import logging
import sys
from config import settings

def setup_logging():
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('/var/log/dashboard/app.log') if settings.debug else logging.NullHandler()
        ]
    )
    
    # Set specific logger levels
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    
    return logging.getLogger(__name__)

logger = setup_logging()
```

### Health Checks

```python
# health.py
from fastapi import APIRouter, HTTPException
from database import check_db_health
from cache import cache
import asyncio
import time

router = APIRouter()

@router.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {"status": "healthy", "timestamp": time.time()}

@router.get("/health/detailed")
async def detailed_health_check():
    """Comprehensive health check with dependencies"""
    checks = {}
    overall_status = "healthy"
    
    # Database check
    try:
        db_result = await asyncio.wait_for(check_db_health(), timeout=5.0)
        checks["database"] = db_result
        if db_result["status"] != "healthy":
            overall_status = "unhealthy"
    except asyncio.TimeoutError:
        checks["database"] = {"status": "timeout"}
        overall_status = "unhealthy"
    except Exception as e:
        checks["database"] = {"status": "error", "error": str(e)}
        overall_status = "unhealthy"
    
    # Redis check
    try:
        redis_result = await asyncio.wait_for(cache.health_check(), timeout=3.0)
        checks["redis"] = redis_result
        if redis_result["status"] != "healthy":
            overall_status = "degraded" if overall_status == "healthy" else overall_status
    except Exception as e:
        checks["redis"] = {"status": "error", "error": str(e)}
        overall_status = "degraded" if overall_status == "healthy" else overall_status
    
    if overall_status != "healthy":
        raise HTTPException(status_code=503, detail={
            "status": overall_status,
            "checks": checks,
            "timestamp": time.time()
        })
    
    return {
        "status": overall_status,
        "checks": checks,
        "timestamp": time.time()
    }

@router.get("/metrics")
async def metrics_endpoint():
    """Prometheus-compatible metrics endpoint"""
    # Implement Prometheus metrics collection
    # This is a basic example - use prometheus_client for production
    return {
        "active_connections": 0,  # WebSocket connections
        "cache_hit_rate": 0.95,   # Cache performance
        "response_time_avg": 0.1,  # Average response time
        "error_rate": 0.01        # Error rate percentage
    }
```

### Error Tracking with Sentry

```python
# main.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from config import settings

if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        integrations=[
            FastApiIntegration(auto_enabling_integrations=False),
            SqlalchemyIntegration(),
        ],
        traces_sample_rate=0.1,  # 10% of transactions for performance monitoring
        profiles_sample_rate=0.1,  # 10% of transactions for profiling
        environment="production",
        release=settings.version,
    )
```

## Security

### HTTPS and SSL

```python
# main.py - SSL configuration
import ssl
from fastapi import FastAPI
import uvicorn

app = FastAPI()

if __name__ == "__main__":
    # SSL configuration for direct HTTPS (if not using reverse proxy)
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain("/path/to/cert.pem", "/path/to/key.pem")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=443,
        ssl_keyfile="/path/to/key.pem",
        ssl_certfile="/path/to/cert.pem",
        ssl_version=ssl.PROTOCOL_TLS_SERVER,
        ssl_ciphers="ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS"
    )
```

### Authentication Middleware

```python
# auth.py
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from config import settings

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.secret_key,
            algorithms=["HS256"]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Apply to protected cards
class ProtectedCard(BaseCard[ChartCardRecord]):
    @classmethod
    async def handler(cls, ctx, user=Depends(verify_token)):
        # Access user information from token
        user_id = user.get("user_id")
        
        # Filter data based on user permissions
        data = await get_user_data(user_id)
        
        return [ChartCardRecord(
            kind=cls.kind,
            report_id=cls.report_id,
            card_id=cls.card_id,
            data=ChartCardData(data=data)
        )]
```

### CORS Configuration

```python
# main.py
from fastapi.middleware.cors import CORSMiddleware
from config import settings

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
    max_age=600,  # Cache preflight requests for 10 minutes
)
```

## Performance Optimization

### WebSocket Session Management

```python
# websocket_manager.py
import asyncio
from typing import Dict, Set
from fastapi import WebSocket

class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.connection_metadata: Dict[WebSocket, dict] = {}
    
    async def connect(self, websocket: WebSocket, card_id: str):
        await websocket.accept()
        
        if card_id not in self.active_connections:
            self.active_connections[card_id] = set()
        
        self.active_connections[card_id].add(websocket)
        self.connection_metadata[websocket] = {
            "card_id": card_id,
            "connected_at": asyncio.get_event_loop().time()
        }
    
    def disconnect(self, websocket: WebSocket):
        metadata = self.connection_metadata.pop(websocket, {})
        card_id = metadata.get("card_id")
        
        if card_id and card_id in self.active_connections:
            self.active_connections[card_id].discard(websocket)
            
            # Clean up empty sets
            if not self.active_connections[card_id]:
                del self.active_connections[card_id]
    
    async def broadcast_to_card(self, card_id: str, data: dict):
        """Broadcast data to all connections for a specific card"""
        if card_id not in self.active_connections:
            return
        
        dead_connections = []
        
        for websocket in self.active_connections[card_id]:
            try:
                await websocket.send_json(data)
            except Exception:
                dead_connections.append(websocket)
        
        # Clean up dead connections
        for websocket in dead_connections:
            self.disconnect(websocket)
    
    def get_connection_count(self, card_id: str = None) -> int:
        if card_id:
            return len(self.active_connections.get(card_id, set()))
        return sum(len(connections) for connections in self.active_connections.values())

ws_manager = WebSocketManager()
```

### Connection Limits

```python
# middleware/connection_limit.py
from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from collections import defaultdict
import time

class ConnectionLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_connections_per_ip: int = 10):
        super().__init__(app)
        self.max_connections = max_connections_per_ip
        self.connections = defaultdict(int)
        self.last_cleanup = time.time()
    
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        
        # Clean up old connections periodically
        if time.time() - self.last_cleanup > 60:  # Every minute
            self.connections.clear()
            self.last_cleanup = time.time()
        
        # Check connection limit
        if self.connections[client_ip] >= self.max_connections:
            raise HTTPException(
                status_code=429,
                detail="Too many concurrent connections"
            )
        
        self.connections[client_ip] += 1
        
        try:
            response = await call_next(request)
            return response
        finally:
            self.connections[client_ip] -= 1
            if self.connections[client_ip] <= 0:
                del self.connections[client_ip]

# Apply middleware
app.add_middleware(ConnectionLimitMiddleware, max_connections_per_ip=20)
```

## Scaling Strategies

### Horizontal Scaling with Docker Swarm

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  dashboard-api:
    image: your-registry/dashboard-api:latest
    deploy:
      replicas: 5
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
      update_config:
        parallelism: 2
        delay: 10s
        failure_action: rollback
        monitor: 60s
      rollback_config:
        parallelism: 1
        delay: 0s
        monitor: 60s
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
        window: 120s
    networks:
      - dashboard-network
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - WORKERS=1  # Single worker per container in swarm mode

  nginx:
    image: nginx:alpine
    deploy:
      replicas: 2
      placement:
        constraints:
          - node.role == manager
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    networks:
      - dashboard-network
```

### Kubernetes Deployment

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dashboard-api
  labels:
    app: dashboard-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: dashboard-api
  template:
    metadata:
      labels:
        app: dashboard-api
    spec:
      containers:
      - name: dashboard-api
        image: your-registry/dashboard-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: dashboard-secrets
              key: database-url
        - name: REDIS_URL
          value: "redis://redis-service:6379/0"
        resources:
          limits:
            cpu: 1000m
            memory: 1Gi
          requests:
            cpu: 500m
            memory: 512Mi
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5

---
apiVersion: v1
kind: Service
metadata:
  name: dashboard-api-service
spec:
  selector:
    app: dashboard-api
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8000
  type: ClusterIP

---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: dashboard-api-ingress
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    cert-manager.io/cluster-issuer: "letsencrypt"
spec:
  tls:
  - hosts:
    - api.yourdomain.com
    secretName: dashboard-api-tls
  rules:
  - host: api.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: dashboard-api-service
            port:
              number: 80
```

## Backup and Disaster Recovery

### Database Backups

```bash
#!/bin/bash
# backup.sh - Automated database backup script

# Configuration
DB_HOST="your-db-host"
DB_NAME="dashboard"
DB_USER="dashboard"
BACKUP_DIR="/backups"
RETENTION_DAYS=30

# Create backup
BACKUP_FILE="$BACKUP_DIR/dashboard_$(date +%Y%m%d_%H%M%S).sql"
pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME > $BACKUP_FILE

# Compress backup
gzip $BACKUP_FILE

# Upload to S3 (optional)
aws s3 cp $BACKUP_FILE.gz s3://your-backup-bucket/database/

# Clean up old backups
find $BACKUP_DIR -name "dashboard_*.sql.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup completed: $BACKUP_FILE.gz"
```

### Disaster Recovery Plan

```yaml
# disaster-recovery/docker-compose.yml
# Emergency deployment configuration

version: '3.8'

services:
  dashboard-api:
    image: your-registry/dashboard-api:stable
    environment:
      - DATABASE_URL=${BACKUP_DATABASE_URL}
      - REDIS_URL=${BACKUP_REDIS_URL}
      - DEBUG=false
      - LOG_LEVEL=ERROR
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '0.5'
          memory: 512M

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: dashboard
      POSTGRES_USER: dashboard
      POSTGRES_PASSWORD: ${BACKUP_DB_PASSWORD}
    volumes:
      - ./restore_backup.sql:/docker-entrypoint-initdb.d/restore.sql:ro
```

## Maintenance

### Rolling Updates

```bash
#!/bin/bash
# rolling-update.sh

# Build new image
docker build -t your-registry/dashboard-api:$NEW_VERSION .

# Push to registry
docker push your-registry/dashboard-api:$NEW_VERSION

# Update docker-compose with zero downtime
docker service update --image your-registry/dashboard-api:$NEW_VERSION dashboard_dashboard-api

# Verify deployment
sleep 30
curl -f http://localhost/health || echo "Health check failed!"

echo "Rolling update completed to version $NEW_VERSION"
```

### Database Migrations in Production

```bash
#!/bin/bash
# migrate.sh - Safe database migration

# Backup before migration
./backup.sh

# Run migrations
alembic upgrade head

# Verify application starts
docker-compose up -d dashboard-api
sleep 10

# Health check
curl -f http://localhost/health/detailed || {
    echo "Migration failed, rolling back..."
    alembic downgrade -1
    exit 1
}

echo "Migration completed successfully"
```

## Troubleshooting

### Common Issues

**WebSocket Connection Drops**
```python
# Add connection monitoring
class MonitoredWebSocketCard(BaseCard[NumberCardRecord]):
    @classmethod
    async def handler(cls, ctx):
        websocket = ctx.get("websocket")
        
        try:
            while True:
                # Send ping to keep connection alive
                await websocket.ping()
                
                # Your card logic here
                yield NumberCardRecord(...)
                
                await asyncio.sleep(1)
        except Exception as e:
            logging.warning(f"WebSocket connection lost: {e}")
            raise
```

**Database Connection Pool Exhaustion**
```python
# Monitor pool status
@app.get("/debug/db-pool")
async def db_pool_status():
    pool = engine.pool
    return {
        "size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "invalid": pool.invalidated()
    }
```

**Memory Leaks in Streaming**
```python
# Implement memory monitoring
import psutil
import os

@app.middleware("http")
async def monitor_memory(request: Request, call_next):
    process = psutil.Process(os.getpid())
    memory_before = process.memory_info().rss / 1024 / 1024  # MB
    
    response = await call_next(request)
    
    memory_after = process.memory_info().rss / 1024 / 1024  # MB
    memory_diff = memory_after - memory_before
    
    if memory_diff > 10:  # Alert if > 10MB increase
        logging.warning(f"High memory usage: +{memory_diff:.2f}MB")
    
    return response
```

This comprehensive deployment guide covers all aspects of taking your Cereon SDK application from development to production. Follow the checklist at the beginning and adapt the configurations to your specific infrastructure requirements.

## Next Steps

- [Examples](examples/) - Real-world deployment examples
- [API Reference](api-reference.md) - Complete API documentation
- [Card Types Reference](card-types.md) - Available card types
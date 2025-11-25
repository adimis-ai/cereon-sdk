# Cereon SDK

> ⚠️ CONSTRUCTION / BETA NOTICE: The official beta release of these packages is scheduled for 1st December 2025. Expect breaking changes until the beta is published. If you plan to depend on this library for production, please wait until the official beta.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) [![Python](https://img.shields.io/badge/Python-3.11-blue.svg?logo=python&logoColor=white)](https://www.python.org/) [![FastAPI](https://img.shields.io/badge/FastAPI-Ready-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)

**Cereon SDK** is a lightweight, framework-agnostic Python SDK for building typed, real-time dashboard backends. It provides strongly-typed helpers and transport adapters for FastAPI and Django to create interactive dashboard cards, and supports HTTP, WebSocket, Server-Sent Events (SSE), and NDJSON streaming with validation, batching, and configurable error policies.

## 🚀 Quick Start

### Installation

Install the core SDK (no web framework):

```bash
pip install cereon-sdk
```

Install with FastAPI support:

```bash
pip install "cereon-sdk[fastapi]"
```

Install with Django support:

```bash
pip install "cereon-sdk[django]"
```

Install both extras:

```bash
pip install "cereon-sdk[fastapi,django]"
```

## Usage examples

Below are minimal examples showing how to integrate Cereon SDK with FastAPI and Django. These are meant to be quick-start snippets — refer to the code in `cereon_sdk/fastapi` and `cereon_sdk/django` for full feature details.

### FastAPI (HTTP + streaming)

```py
from fastapi import FastAPI
from pydantic import BaseModel
from cereon_sdk.fastapi.routes import make_streaming_route_typed

app = FastAPI()

class Record(BaseModel):
	id: int
	value: float

def handler(ctx):
	# return an iterable or async iterable of items matching Record
	for i in range(5):
		yield {"id": i, "value": i * 1.5}

make_streaming_route_typed(app, "/stream", handler, response_model=Record, format="ndjson")

if __name__ == "__main__":
	import uvicorn

	uvicorn.run(app, host="127.0.0.1", port=8000)
```

### FastAPI (WebSocket)

```py
from fastapi import FastAPI
from pydantic import BaseModel
from cereon_sdk.fastapi.routes import make_websocket_route_typed

app = FastAPI()

class Record(BaseModel):
	id: int
	value: float

async def ws_handler(ctx):
	# ctx['websocket'] is a FastAPI WebSocket
	# yield/return messages or push directly using websocket
	for i in range(3):
		yield {"id": i, "value": i * 2.0}

make_websocket_route_typed(app, "/ws", ws_handler, response_model=Record)
```

### FastAPI (HTTP plain)

If you only need a simple HTTP endpoint that returns a JSON list (no streaming), use the regular FastAPI route helpers and return serializable data. The SDK helpers provide typed validation and convenience wrappers when desired.

```py
from fastapi import FastAPI
from pydantic import BaseModel
from cereon_sdk.fastapi.routes import make_route_typed

app = FastAPI()

class Record(BaseModel):
    id: int
    value: float

def http_handler(ctx):
    return [{"id": i, "value": i * 1.5} for i in range(3)]

make_route_typed(app, "/http", http_handler, response_model=Record)
```

### FastAPI (NDJSON / Server Sent Events)

The `make_streaming_route_typed` helper supports several streaming formats. Use `format="ndjson"` for newline-delimited JSON or `format="sse"` for Server-Sent Events. The handler may be an iterator or async iterator.

```py
make_streaming_route_typed(app, "/ndjson", handler, response_model=Record, format="ndjson")
make_streaming_route_typed(app, "/sse", handler, response_model=Record, format="sse")
```

### Django (DRF APIView)

Create a DRF view by subclassing `BaseCardAPIView` in `cereon_sdk/django/views.py`.

Subclasses must implement an instance method `handle(self, ctx)` (can be sync or async) and set
`response_serializer` to a DRF `Serializer` class used to validate outgoing records.

```py
from rest_framework import serializers
from cereon_sdk.django.views import BaseCardAPIView

class RecordSerializer(serializers.Serializer):
	id = serializers.IntegerField()
	value = serializers.FloatField()

class MyCardView(BaseCardAPIView):
	response_serializer = RecordSerializer

	def handle(self, ctx):
		# return a list or iterable (or a single record)
		return [{"id": 1, "value": 3.14}]
```

Add the view to your `urls.py` as you would any DRF view.

### Django (WebSocket - Channels)

If you're using Django Channels for WebSocket support, implement a consumer that uses the SDK helpers to validate and emit messages. The SDK provides utilities in `cereon_sdk.django.utils` to assist integration.

```py
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from cereon_sdk.django.utils import validate_and_send

class CardConsumer(AsyncJsonWebsocketConsumer):
	async def connect(self):
		await self.accept()

	async def receive_json(self, content):
		# handle incoming message and optionally send back typed records
		records = [{"id": 1, "value": 2.5}]
		await validate_and_send(self.send_json, records)

	async def disconnect(self, close_code):
		pass
```

Add the view to your `urls.py` as you would any DRF view.

## Development

To run tests and linters locally after installing dev extras:

```bash
source .venv/bin/activate
pip install -e .[dev]
pytest -q
ruff check .
black .
```

Pre-commit hooks are configured — run them before pushing:

```bash
pre-commit install
pre-commit run --all-files
```

## Contributing

See `CONTRIBUTING.md` for full guidelines on contributing, testing, and the release process.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.

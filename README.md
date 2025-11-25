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

```python
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

```python
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

### Django (DRF view)

Create a DRF view by subclassing `BaseCardAPIView` in `cereon_sdk/django/views.py`.

Subclasses must implement an instance method `handle(self, ctx)` (can be sync or async) and set
`response_serializer` to a DRF `Serializer` class used to validate outgoing records.

```python
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

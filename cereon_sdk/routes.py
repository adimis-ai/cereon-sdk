# cereon_sdk/cereon_sdk/core/routes.py
from __future__ import annotations
import json
import asyncio
import inspect
from typing import (
    Any,
    AsyncIterable,
    Awaitable,
    Callable,
    Dict,
    Iterable,
    Optional,
    Type,
    TypeVar,
    Union,
    Literal,
    List,
    TypedDict,
    NotRequired,
)
from datetime import datetime

from pydantic import ValidationError
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder

from .types import BaseCardRecord
from .utils import parse_http_params, parse_websocket_params

RecordType = TypeVar("RecordType", bound=BaseCardRecord)


class BaseContext(TypedDict):
    params: NotRequired[Dict[str, Any]]
    filters: NotRequired[Dict[str, Any]]


class HttpHandlerContext(BaseContext):
    request: NotRequired[Request]


class WebSocketHandlerContext(BaseContext):
    websocket: NotRequired[WebSocket]


def now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def is_async_callable(fn: Callable[..., Any]) -> bool:
    return inspect.iscoroutinefunction(fn)


def ensure_async_iter(obj: Any) -> AsyncIterable[Any]:
    """Wrap iterable/single into async iterable."""
    if obj is None:

        async def _empty():
            if False:
                yield None

        return _empty()
    if hasattr(obj, "__aiter__"):
        return obj  # type: ignore
    if isinstance(obj, Iterable) and not isinstance(obj, (str, bytes, dict)):

        async def _aiter_from_iter():
            for v in obj:
                yield v

        return _aiter_from_iter()

    # single value
    async def _single():
        yield obj

    return _single()


def validate_item(
    item: Any, model: Type[RecordType], raise_on_error: bool = True
) -> Optional[dict]:
    """
    Validate a single item against Pydantic model.
    Returns model.model_dump() on success.
    If validation fails:
      - raise_on_error True => raises ValidationError
      - else returns None
    """
    try:
        validated = model.model_validate(item)
        return validated.to_record()
    except ValidationError as ve:
        if raise_on_error:
            raise ve
        return None


Handler = Callable[
    [Dict[str, Any]],
    Union[
        List[RecordType],
        Iterable[RecordType],
        AsyncIterable[RecordType],
        Awaitable[Union[List[RecordType], Iterable[RecordType], AsyncIterable[RecordType]]],
    ],
]

WebsocketHandler = Callable[
    [Dict[str, Any]],
    Union[
        None,
        Awaitable[None],
        List[RecordType],
        Iterable[RecordType],
        AsyncIterable[RecordType],
        Awaitable[Union[List[RecordType], Iterable[RecordType], AsyncIterable[RecordType]]],
    ],
]


def make_http_route_typed(
    app: FastAPI,
    path: str,
    handler: Handler,
    *,
    response_model: Type[RecordType],
    methods=("GET",),
):
    """
    Register typed HTTP route.
    - handler receives `ctx` dict: { "request": Request, "params": ... }
    - handler may be sync/async and return JSON-serializable or dict matching response_model.
    """

    async def endpoint(request: Request):
        params = await parse_http_params(request)
        ctx = {
            "request": request,
            "params": params,
            "filters": params.get("filters", None),
        }
        result = handler(ctx) if not is_async_callable(handler) else await handler(ctx)

        # If iterable/async iterable returned -- materialize (HTTP endpoints should not stream)
        if hasattr(result, "__aiter__") or (
            isinstance(result, Iterable) and not isinstance(result, (str, bytes, dict))
        ):
            # Consume async iterable or sync iterable
            if hasattr(result, "__aiter__"):
                collected = [x async for x in result]  # type: ignore
            else:
                collected = list(result)
            validated = [validate_item(x, response_model, raise_on_error=True) for x in collected]
            return JSONResponse(content=jsonable_encoder(validated))
        # Single object: validate against model
        validated = validate_item(result, response_model, raise_on_error=True)
        return JSONResponse(content=jsonable_encoder(validated))

    app.add_api_route(path, endpoint, methods=list(methods))

    return app


def make_streaming_route_typed(
    app: FastAPI,
    path: str,
    handler: Handler,
    *,
    response_model: Type[RecordType],
    format: Literal["sse", "ndjson", "delimited", "json"] = "ndjson",
    delimiter: str = "\n",
    media_type: Optional[str] = None,
    methods=("GET",),
    stream_error_policy: Literal["fail", "skip", "log"] = "skip",
    packet_size: int = 1000,
):
    """
    Typed streaming route. Each yielded item is validated against `response_model`.
    stream_error_policy:
      - "fail": raise and close stream on first validation error
      - "skip": ignore invalid items and continue
      - "log": include error payload with {"__validation_error": "..."} in stream

    packet_size: number of validated items to buffer and send as a single chunk.
    """
    if format not in ("sse", "ndjson", "delimited", "json"):
        raise ValueError("unsupported format")

    if media_type is None:
        media_type = {
            "sse": "text/event-stream",
            "ndjson": "application/x-ndjson",
            "delimited": "text/plain; charset=utf-8",
            "json": "application/json; charset=utf-8",
        }[format]

    async def endpoint(request: Request):
        params = await parse_http_params(request)
        ctx = {
            "request": request,
            "params": params,
            "filters": params.get("filters", None),
        }
        # call handler
        result = handler(ctx) if not is_async_callable(handler) else await handler(ctx)
        # If not iterable: return JSON (non-stream)
        if not hasattr(result, "__aiter__") and not (
            isinstance(result, Iterable) and not isinstance(result, (str, bytes, dict))
        ):
            validated = validate_item(result, response_model, raise_on_error=True)
            return JSONResponse(content=jsonable_encoder(validated))

        async_iter = ensure_async_iter(result)

        # Helper: validate a raw item applying stream_error_policy and return:
        # - None => item skipped
        # - dict => validated payload or error-object (if log)
        async def _validate_for_stream(raw) -> Optional[dict]:
            try:
                validated = validate_item(
                    raw, response_model, raise_on_error=(stream_error_policy == "fail")
                )
                if validated is None:
                    # invalid item but raise_on_error==False
                    if stream_error_policy == "log":
                        return {"__validation_error": "invalid item"}
                    return None
                return validated
            except ValidationError as ve:
                if stream_error_policy == "fail":
                    # bubble up to abort stream
                    raise
                if stream_error_policy == "log":
                    return {"__validation_error": ve.errors()}
                # skip
                return None

        # Generator implementations per format with batching
        if format == "sse":

            async def gen_sse():
                buffer: List[str] = []
                async for raw in async_iter:
                    validated = await _validate_for_stream(raw)
                    if validated is None:
                        continue
                    # each SSE event is "data: <json>\n\n"
                    buffer.append(f"data: {json.dumps(validated, default=str)}\n\n")
                    if len(buffer) >= packet_size:
                        yield "".join(buffer).encode()
                        buffer.clear()
                if buffer:
                    yield "".join(buffer).encode()
                    buffer.clear()
                # final sentinel - client SSE parser understands event + data block
                yield b"event: end\ndata: {}\n\n"

            return StreamingResponse(gen_sse(), media_type=media_type)

        if format == "ndjson":

            async def gen_ndjson():
                buffer: List[str] = []
                async for raw in async_iter:
                    validated = await _validate_for_stream(raw)
                    if validated is None:
                        continue
                    buffer.append(json.dumps(validated, default=str))
                    if len(buffer) >= packet_size:
                        # join with newline, ensure trailing newline
                        yield (("\n".join(buffer) + "\n").encode())
                        buffer.clear()
                if buffer:
                    yield (("\n".join(buffer) + "\n").encode())
                    buffer.clear()
                # end: do nothing special (connection close signals end)

            return StreamingResponse(gen_ndjson(), media_type=media_type)

        if format == "delimited":
            # preserve historical behavior expected by CardExecutionProvider:
            # client historically split by delimiter+delimiter
            dd = delimiter + delimiter

            async def gen_delim():
                buffer: List[str] = []
                async for raw in async_iter:
                    validated = await _validate_for_stream(raw)
                    if validated is None:
                        continue
                    buffer.append(json.dumps(validated, default=str))
                    if len(buffer) >= packet_size:
                        yield (dd.join(buffer) + dd).encode()
                        buffer.clear()
                if buffer:
                    yield (dd.join(buffer) + dd).encode()
                    buffer.clear()

            return StreamingResponse(gen_delim(), media_type=media_type)

        # json: stream as JSON array (chunked)
        async def gen_json_array():
            first = True
            # For JSON array we need to place commas correctly even when flushing packets
            yield b"["
            buffer: List[str] = []
            async for raw in async_iter:
                validated = await _validate_for_stream(raw)
                if validated is None:
                    continue
                buffer.append(json.dumps(validated, default=str))
                if len(buffer) >= packet_size:
                    # flush buffer
                    if not first:
                        # prefix comma between previous output and current packet
                        # join with ',' and prefix with ','
                        yield (b"," + ",".join(buffer).encode())
                    else:
                        yield (",".join(buffer).encode())
                    first = False
                    buffer.clear()
            if buffer:
                if not first:
                    yield (b"," + ",".join(buffer).encode())
                else:
                    yield (",".join(buffer).encode())
                buffer.clear()
            yield b"]"

        return StreamingResponse(gen_json_array(), media_type=media_type)

    app.add_api_route(path, endpoint, methods=list(methods))

    return app


def make_websocket_route_typed(
    app: FastAPI,
    path: str,
    handler: WebsocketHandler,
    *,
    response_model: Type[RecordType],
    ack_policy: Literal["auto", "manual"] = "auto",
    heartbeat_ms: int = 30000,
    stream_error_policy: Literal["fail", "skip", "log"] = "skip",
):
    """
    Typed websocket factory:
    - handler receives ctx: { "websocket": WebSocket, "params": ..., "filters": ...}
    - handler may:
      - push using websocket directly
      - return an async iterable of items to be sent (each item validated)
    Control messages processed: subscribe/unsubscribe/ping/ack
    """

    connections: Dict[str, WebSocket] = {}
    subscriptions: Dict[str, set] = {}

    async def endpoint(ws: WebSocket):
        await ws.accept()
        cid = f"cid-{id(ws)}"
        connections[cid] = ws
        
        # Track subscriptions for this connection
        active_subscriptions: Dict[str, Dict[str, Any]] = {}
        heartbeat_task: Optional[asyncio.Task] = None
        handler_task: Optional[asyncio.Task] = None
        
        try:
            # Parse initial connection params
            params = await parse_websocket_params(ws)
            ctx = {
                "websocket": ws,
                "params": params,
                "filters": params.get("filters", None),
            }

            async def send_message(message: Dict[str, Any]) -> None:
                """Send a message with validation against response_model"""
                try:
                    # Validate outgoing message against response model
                    validated = validate_item(message, response_model, raise_on_error=(stream_error_policy == "fail"))
                    if validated is None and stream_error_policy == "skip":
                        return  # Skip invalid messages
                    
                    if validated is None and stream_error_policy == "log":
                        # Send error message instead
                        error_msg = {
                            "action": "error",
                            "message": "Validation failed for outgoing message",
                            "timestamp": now_iso(),
                            "__validation_error": "Message failed response model validation"
                        }
                        await ws.send_json(error_msg)
                        return
                    
                    # Send the validated message
                    await ws.send_json(validated)
                    
                except ValidationError as ve:
                    if stream_error_policy == "fail":
                        raise ve
                    elif stream_error_policy == "log":
                        error_msg = {
                            "action": "error", 
                            "message": f"Validation error: {str(ve)}",
                            "timestamp": now_iso(),
                            "__validation_error": str(ve)
                        }
                        await ws.send_json(error_msg)
                except Exception as e:
                    await ws.send_json({
                        "action": "error",
                        "message": f"Failed to send message: {str(e)}",
                        "timestamp": now_iso()
                    })

            async def heartbeat_loop():
                """Send periodic ping messages"""
                if heartbeat_ms <= 0:
                    return
                    
                while True:
                    await asyncio.sleep(heartbeat_ms / 1000.0)
                    try:
                        await ws.send_json({
                            "action": "ping",
                            "timestamp": now_iso()
                        })
                    except Exception:
                        break  # Connection closed

            # Start heartbeat if configured
            if heartbeat_ms > 0:
                heartbeat_task = asyncio.create_task(heartbeat_loop())

            # Message handling loop
            async for data in ws.iter_json():
                try:
                    action = data.get("action", "")
                    
                    if action == "subscribe":
                        # Handle subscription request
                        subscription_id = data.get("subscriptionId", f"sub-{cid}-{len(active_subscriptions)}")
                        topic = data.get("topic", "")
                        ack_policy_override = data.get("ackPolicy", ack_policy)
                        
                        # Store subscription info
                        active_subscriptions[subscription_id] = {
                            "topic": topic,
                            "ackPolicy": ack_policy_override,
                            "clientInfo": data.get("clientInfo", {}),
                            "resumeSeq": data.get("resumeSeq", 0),
                            "timestamp": now_iso()
                        }
                        
                        # Send subscription confirmation
                        await ws.send_json({
                            "action": "subscribed",
                            "subscriptionId": subscription_id,
                            "topic": topic,
                            "timestamp": now_iso()
                        })
                        
                        # Update context with subscription info
                        ctx.update({
                            "subscription_id": subscription_id,
                            "topic": topic,
                            "active_subscriptions": active_subscriptions
                        })
                        
                        # Start handler task if not already running
                        if handler_task is None or handler_task.done():
                            async def run_handler():
                                """Run the user handler and send results"""
                                try:
                                    # Call the user handler 
                                    result = handler(ctx) if not is_async_callable(handler) else await handler(ctx)
                                    
                                    if result is not None:
                                        # Convert result to async iterable
                                        async_iter = ensure_async_iter(result)
                                        
                                        # Send each item from the handler
                                        async for item in async_iter:
                                            # Add metadata for each message
                                            message = {
                                                "data": item,
                                                "timestamp": now_iso(),
                                                "subscriptionIds": list(active_subscriptions.keys())
                                            }
                                            
                                            # Add message ID for manual ack policy
                                            if any(sub.get("ackPolicy") == "manual" for sub in active_subscriptions.values()):
                                                message["id"] = f"msg-{cid}-{int(datetime.utcnow().timestamp() * 1000)}"
                                            
                                            await send_message(message)
                                            
                                except Exception as e:
                                    await ws.send_json({
                                        "action": "error",
                                        "message": f"Handler error: {str(e)}",
                                        "timestamp": now_iso()
                                    })
                            
                            handler_task = asyncio.create_task(run_handler())
                            
                    elif action == "unsubscribe":
                        # Handle unsubscription
                        subscription_id = data.get("subscriptionId")
                        if subscription_id in active_subscriptions:
                            del active_subscriptions[subscription_id]
                            await ws.send_json({
                                "action": "unsubscribed", 
                                "subscriptionId": subscription_id,
                                "timestamp": now_iso()
                            })
                            
                    elif action == "ping":
                        # Respond to ping with pong
                        await ws.send_json({
                            "action": "pong",
                            "timestamp": now_iso()
                        })
                        
                    elif action == "ack":
                        # Handle message acknowledgment
                        message_id = data.get("messageId")
                        # Could store ack state or forward to handler
                        pass
                        
                    elif action == "pong":
                        # Handle pong response (heartbeat response)
                        pass
                        
                    else:
                        # Forward other messages to handler if available
                        if active_subscriptions:
                            ctx.update({"message": data})
                            # Handler will process this in its async iteration
                            
                except json.JSONDecodeError:
                    await ws.send_json({
                        "action": "error",
                        "message": "Invalid JSON message",
                        "timestamp": now_iso()
                    })
                except Exception as e:
                    await ws.send_json({
                        "action": "error", 
                        "message": str(e),
                        "timestamp": now_iso()
                    })


                    
        except WebSocketDisconnect:
            pass  # Client disconnected normally
        except Exception as e:
            try:
                await ws.send_json({
                    "action": "error",
                    "message": f"WebSocket error: {str(e)}",
                    "timestamp": now_iso()
                })
            except:
                pass  # Connection may already be closed
        finally:
            # Cleanup
            if heartbeat_task and not heartbeat_task.done():
                heartbeat_task.cancel()
            if handler_task and not handler_task.done():
                handler_task.cancel()
            if cid in connections:
                del connections[cid]
            # Clear subscriptions
            active_subscriptions.clear()

    app.add_websocket_route(path, endpoint)
    return app

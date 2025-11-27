# cereon_sdk/django/consumers.py
from __future__ import annotations
import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Iterable, Callable, Type


from rest_framework import serializers
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .utils import parse_websocket_params_from_scope


def _now_iso() -> str:
    from datetime import datetime

    return datetime.utcnow().isoformat() + "Z"


def _ensure_async_iter(obj):
    """Normalize sync iterables and single values into async iterable."""
    if obj is None:

        async def _empty():
            if False:
                yield None

        return _empty()

    if hasattr(obj, "__aiter__"):
        return obj

    if isinstance(obj, Iterable) and not isinstance(obj, (str, bytes, dict)):

        async def _aiter():
            for v in obj:
                yield v

        return _aiter()

    async def _single():
        yield obj

    return _single()


class BaseCardConsumer(AsyncJsonWebsocketConsumer, ABC):
    """
    Channels consumer implementing the websocket transport contract.

    Subclasses MUST set:
      - response_model: pydantic model for outgoing messages (optional)
      - handler: callable(ctx) -> async iterable or coroutine that returns async iterable
    """

    response_serializer: Optional[Type[serializers.Serializer]] = None

    @abstractmethod
    async def handle(self, ctx: Dict[str, Any]):
        """
        Subclasses must implement `async def handle(self, ctx)` which may:
            - return an async iterable
            - yield/return values directly
        """
        raise NotImplementedError()

    ack_policy: str = "auto"
    heartbeat_interval_sec: int = 30
    stream_error_policy: str = "skip"  # 'fail'|'skip'|'log'

    async def connect(self):
        await self.accept()
        # parse params from scope querystring (non-blocking)
        params = await parse_websocket_params_from_scope(self.scope)
        if isinstance(params, dict) and "params" in params and isinstance(params["params"], dict):
            self.params = params["params"]
        else:
            self.params = params if isinstance(params, dict) else {}
        self.active_subscriptions: Dict[str, Dict[str, Any]] = {}
        self.handler_task = None
        self.heartbeat_task = None
        if self.heartbeat_interval_sec > 0:
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def disconnect(self, code):
        if self.handler_task and not self.handler_task.done():
            self.handler_task.cancel()
        if self.heartbeat_task and not self.heartbeat_task.done():
            self.heartbeat_task.cancel()

    async def _heartbeat_loop(self):
        try:
            while True:
                await asyncio.sleep(self.heartbeat_interval_sec)
                await self.send_json({"action": "ping", "timestamp": _now_iso()})
        except asyncio.CancelledError:
            return

    async def receive_json(self, content: Dict[str, Any], **kwargs):
        action = content.get("action", "")
        if action == "subscribe":
            subscription_id = content.get(
                "subscriptionId", f"sub-{id(self)}-{len(self.active_subscriptions)}"
            )
            topic = content.get("topic", "")
            ack_policy = content.get("ackPolicy", self.ack_policy)
            self.active_subscriptions[subscription_id] = {
                "topic": topic,
                "ackPolicy": ack_policy,
                "clientInfo": content.get("clientInfo", {}),
            }
            await self.send_json(
                {
                    "action": "subscribed",
                    "subscriptionId": subscription_id,
                    "topic": topic,
                    "timestamp": _now_iso(),
                }
            )

            # ensure handler is running
            if (self.handler_task is None) or self.handler_task.done():
                self.handler_task = asyncio.create_task(self._run_handler())

        elif action == "unsubscribe":
            sid = content.get("subscriptionId")
            if sid in self.active_subscriptions:
                del self.active_subscriptions[sid]
                await self.send_json(
                    {"action": "unsubscribed", "subscriptionId": sid, "timestamp": _now_iso()}
                )
        elif action == "ping":
            await self.send_json({"action": "pong", "timestamp": _now_iso()})
        elif action == "ack":
            # Override in subclass to track ack state
            pass
        else:
            # forward arbitrary messages into last_message; handler may inspect context if needed
            self.last_message = content

    async def _run_handler(self):
        """
        Run the user handler and send validated messages to client.
        """
        try:
            ctx = {
                "websocket": self,
                "params": self.params,
                "filters": self.params.get("filters"),
                "active_subscriptions": self.active_subscriptions,
            }
            result = self.handle(ctx)
            if asyncio.iscoroutine(result):
                result = await result
            if result is None:
                return
            async_iter = _ensure_async_iter(result)
            async for item in async_iter:
                message = {
                    "data": item,
                    "timestamp": _now_iso(),
                    "subscriptionIds": list(self.active_subscriptions.keys()),
                }
                if any(s.get("ackPolicy") == "manual" for s in self.active_subscriptions.values()):
                    message["id"] = f"msg-{id(self)}-{int(asyncio.get_event_loop().time() * 1000)}"
                await self._send_validated(message)
        except Exception as e:
            await self.send_json(
                {"action": "error", "message": f"Handler error: {str(e)}", "timestamp": _now_iso()}
            )

    async def _send_validated(self, message: Dict[str, Any]):
        """
        Validate outgoing message with DRF `response_serializer` (if present) and send.
        Honors `stream_error_policy`.
        """
        if self.response_serializer is None:
            await self.send_json(message)
            return

        try:
            serializer_cls = self.response_serializer
            ser = serializer_cls(data=message)
            ser.is_valid(raise_exception=True)
            # If serializer has `to_record`, prefer its output, else use representation
            if hasattr(ser, "to_record"):
                out = ser.to_record()
            else:
                out = ser.data
            await self.send_json(out)
        except serializers.ValidationError as ve:
            if self.stream_error_policy == "fail":
                await self.send_json(
                    {"action": "error", "message": str(ve), "timestamp": _now_iso()}
                )
                await self.close()
            elif self.stream_error_policy == "log":
                await self.send_json(
                    {"action": "error", "__validation_error": ve.detail, "timestamp": _now_iso()}
                )
            # skip on 'skip'

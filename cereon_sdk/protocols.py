# cereon_sdk/cereon_sdk/core/protocols.py
from __future__ import annotations
from pydantic import BaseModel
from abc import ABC, abstractmethod
from fastapi import FastAPI, Request, WebSocket
from typing import (
    Any,
    Dict,
    Optional,
    Generic,
    Type,
    ClassVar,
    Literal,
    TypedDict,
    NotRequired,
    AsyncIterable,
    Union,
    Awaitable,
    List,
)
import inspect

from .routes import (
    RecordType,
    HttpHandlerContext,
    make_http_route_typed,
    WebSocketHandlerContext,
    make_streaming_route_typed,
    make_websocket_route_typed,
)


class BaseCard(ABC, Generic[RecordType]):
    """
    Protocol for dashboard card handlers.

    See original file for usage notes.
    """

    app: ClassVar[Optional[FastAPI]] = None

    kind: ClassVar[str]
    card_id: ClassVar[str]
    report_id: ClassVar[str]
    route_prefix: ClassVar[str]
    response_model: ClassVar[Type[RecordType]]
    transport: ClassVar[Literal["http", "websocket", "streaming-http"]]

    def __init__(self, app: FastAPI) -> None:
        self.__class__.app = app
        super().__init__()

    @classmethod
    def _validator(cls) -> bool:
        """
        Validate handler signature according to the transport contract.

        - http: handler MUST be an async coroutine (not async-generator) that returns a list[RecordType]
        - streaming-http: handler MUST be an async-generator yielding RecordType values
        - websocket: handler MUST be an async-generator yielding RecordType values OR an async coroutine returning an async generator
        """
        if not hasattr(cls, "transport"):
            return False

        transport = getattr(cls, "transport", None)
        handler = getattr(cls, "handler", None)

        if handler is None or not callable(handler):
            return False

        is_coro = inspect.iscoroutinefunction(handler)
        is_asyncgen = inspect.isasyncgenfunction(handler)

        if transport == "http":
            # Require coroutine (not asyncgen). We cannot check return type at definition time,
            # but runtime will enforce the coroutine returns a list.
            return is_coro and not is_asyncgen
        elif transport == "streaming-http":
            # Must be an async generator that yields one RecordType at a time.
            return is_asyncgen
        elif transport == "websocket":
            # Websocket handler must be an async generator function OR an async coroutine function
            # (the latter is expected to return an async generator when called)
            return is_asyncgen or is_coro
        else:
            return False

    @classmethod
    async def _http_handler(cls, request: Request) -> List[RecordType]:
        """
        Call the handler and enforce it returns a list of RecordType (materialized).
        """
        if cls.app is None:
            raise RuntimeError("FastAPI `app` is not registered on the Card class.")
        if not cls._validator():
            raise RuntimeError(
                f"Handler signature invalid for transport '{getattr(cls, 'transport', None)}'"
            )

        ctx: HttpHandlerContext = {"request": request, "meta": {}, "params": {}}
        result = await cls.handler(ctx)  # type: ignore

        # Strict contract: HTTP handlers must return a list.
        if not isinstance(result, list):
            raise RuntimeError("HTTP handler must return a list[RecordType].")
        return result  # type: ignore

    @classmethod
    async def _stream_handler(cls, request: Request) -> AsyncIterable[RecordType]:
        """
        streaming-http must be provided as an async-generator (yields RecordType).
        Validator already enforces handler is async-generator, so just call and return the generator.
        """
        if cls.app is None:
            raise RuntimeError("FastAPI `app` is not registered on the Card class.")
        if not cls._validator():
            raise RuntimeError(
                f"Handler signature invalid for transport '{getattr(cls, 'transport', None)}'"
            )

        ctx: HttpHandlerContext = {"request": request, "meta": {}, "params": {}}
        gen = cls.handler(ctx)
        if inspect.isasyncgen(gen):
            return gen  # type: ignore
        # If we reached here, the validator should have prevented it; surface an explicit error.
        raise RuntimeError(
            "streaming-http handler must be an async-generator yielding RecordType items."
        )

    @classmethod
    async def _websocket_handler(cls, ctx: WebSocketHandlerContext) -> AsyncIterable[RecordType]:
        """
        websocket handlers must be async-generators yielding single RecordType values.
        This method is called by the WebSocket route implementation in routes.py.
        """
        if cls.app is None:
            raise RuntimeError("FastAPI `app` is not registered on the Card class.")
        if not cls._validator():
            raise RuntimeError(
                f"Handler signature invalid for transport '{getattr(cls, 'transport', None)}'"
            )

        # Check if handler is an async generator function or async function
        if inspect.isasyncgenfunction(cls.handler):
            # Handler is an async generator, call it directly
            return cls.handler(ctx)  # type: ignore
        elif inspect.iscoroutinefunction(cls.handler):
            # Handler is an async function, await it to get the generator
            handler_result = await cls.handler(ctx)  # type: ignore
            if inspect.isasyncgen(handler_result):
                return handler_result  # type: ignore
            else:
                raise RuntimeError(
                    "Websocket handler async function must return an async generator."
                )
        else:
            raise RuntimeError(
                "Websocket handler must be an async generator function or async function returning async generator."
            )

    @classmethod
    @abstractmethod
    async def handler(
        cls, ctx: Optional[Union[HttpHandlerContext, WebSocketHandlerContext]] = None
    ) -> Union[Awaitable[List[RecordType]], AsyncIterable[RecordType]]:
        """
        Implementations should obey transport-specific contract:
         - http: async def handler(...) -> list[RecordType]
         - streaming-http: async def handler(...) -> AsyncGenerator[RecordType, None] (yield items)
         - websocket: async def handler(...) -> AsyncGenerator[RecordType, None] (yield items)
        """
        raise NotImplementedError

    @classmethod
    def as_route(
        cls,
        *,
        app: Optional[FastAPI] = None,
        # allowed streaming-http options
        delimiter: str = "\n",
        packet_size: int = 1000,
        media_type: Optional[str] = None,
        stream_error_policy: Literal["fail", "skip", "log"] = "skip",
        format: Literal["sse", "ndjson", "delimited", "json"] = "ndjson",
        # allowed websocket options
        heartbeat_ms: int = 30000,
        ack_policy: Literal["auto", "manual"] = "auto",
        # http options
        methods: tuple = ("GET",),
        **kwargs,
    ) -> FastAPI:
        """
        Unified route factory. Strictly validates that only parameters relevant
        to the declared transport are provided.

        Raises TypeError on unexpected args for the transport.
        """
        # If caller passed extra kwargs, include them in validation (explicitly reject)
        extra_args = set(kwargs.keys())
        use_app = app or cls.app
        if use_app is None:
            raise RuntimeError("No FastAPI app registered on this Card class (or passed as `app`).")

        # Store the app instance on the class for later use by handlers
        cls.app = use_app

        if not cls._validator():
            raise RuntimeError(
                f"Handler signature invalid for transport '{getattr(cls, 'transport', None)}'"
            )

        transport = getattr(cls, "transport", None)

        # Define allowed args per transport (excluding 'app' which is explicit)
        allowed_for_transport = {
            "http": {"methods"},
            "streaming-http": {
                "delimiter",
                "media_type",
                "stream_error_policy",
                "format",
                "methods",
            },
            "websocket": {"heartbeat_ms", "ack_policy", "stream_error_policy"},
        }

        if transport not in allowed_for_transport:
            raise RuntimeError(f"Unsupported transport: {transport}")

        if extra_args:
            invalid = extra_args - allowed_for_transport[transport]
            if invalid:
                raise TypeError(
                    f"Invalid argument(s) for transport '{transport}': {sorted(invalid)}. "
                    f"Allowed arguments: {sorted(allowed_for_transport[transport])}."
                )

        path = f"{cls.route_prefix}/{cls.card_id}"

        # Dispatch to proper route builder using the explicit parameters (defaults preserved)
        if transport == "http":
            return make_http_route_typed(
                path=path,
                app=use_app,
                methods=methods,
                handler=cls._http_handler,
                response_model=cls.response_model,
            )
        if transport == "streaming-http":
            return make_streaming_route_typed(
                path=path,
                app=use_app,
                format=format,
                methods=methods,
                delimiter=delimiter,
                media_type=media_type,
                packet_size=packet_size,
                handler=cls._stream_handler,
                response_model=cls.response_model,
                stream_error_policy=stream_error_policy,
            )
        # websocket - create a handler wrapper that calls the class handler
        async def websocket_handler_wrapper(ctx: WebSocketHandlerContext):
            return await cls._websocket_handler(ctx)
        
        return make_websocket_route_typed(
            path=path,
            app=use_app,
            ack_policy=ack_policy,
            heartbeat_ms=heartbeat_ms,
            handler=websocket_handler_wrapper,
            response_model=cls.response_model,
            stream_error_policy=stream_error_policy,
        )

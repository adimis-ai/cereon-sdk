# cereon_sdk/django/views.py
from __future__ import annotations
import asyncio
from typing import Any, Dict, Iterable, List, Optional, Type, Union, Callable

from abc import ABC, abstractmethod
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers
from rest_framework.request import Request as DRFRequest

from .utils import parse_http_params

RecordSerializer = Type[serializers.Serializer]


def _get_filters_from_ctx(ctx: Any) -> Optional[Dict[str, Any]]:
    """Normalize and return the filters dict from various ctx shapes used in handlers.

    Mirrors the helper defined in the FastAPI protocols module so handler implementations
    can rely on a predictable `filters` dict regardless of how the view/route constructed ctx.
    """
    if not ctx:
        return None
    if isinstance(ctx, dict):
        if "filters" in ctx and isinstance(ctx.get("filters"), dict):
            return ctx.get("filters")
        if "params" in ctx and isinstance(ctx.get("params"), dict):
            params = ctx.get("params")
            if "filters" in params and isinstance(params.get("filters"), dict):
                return params.get("filters")
            # If params is empty, prefer checking nested 'request' dict for filters
            if params:
                return params
        req = ctx.get("request")
        if isinstance(req, dict):
            if "filters" in req and isinstance(req.get("filters"), dict):
                return req.get("filters")
            if "params" in req and isinstance(req.get("params"), dict):
                params = req.get("params")
                if "filters" in params and isinstance(params.get("filters"), dict):
                    return params.get("filters")
                # Only return non-empty params; otherwise continue searching
                if params:
                    return params
    return None


class BaseCardAPIView(APIView, ABC):
    """
    Abstract DRF view that implements the 'http' transport contract.

        Subclasses MUST set:
            - response_serializer: DRF Serializer class used to validate responses
            - handler: callable(ctx) -> sync/async result
                * Handler receives ctx: {"request": HttpRequest, "params": {...}, "filters": ...}
                * Handler may return:
                    - a list/iterable of payloads (will be materialized and validated)
                    - a single payload (will be validated)
    """

    response_serializer: Optional[RecordSerializer] = None

    @classmethod
    def _get_filters_from_ctx(cls, ctx: Any) -> Optional[Dict[str, Any]]:
        """Classmethod wrapper to expose the module-level helper to subclasses.

        Subclasses and external callers can call `MyView._get_filters_from_ctx(ctx)`
        to normalize filter extraction from various handler contexts.
        """
        return _get_filters_from_ctx(ctx)

    @abstractmethod
    def handle(self, ctx: Dict[str, Any]) -> Union[List[Any], Iterable[Any], Any]:
        """
        Subclasses must implement `handle(self, ctx)` which may return:
            - a list/iterable of payloads (will be materialized and validated)
            - a single payload (will be validated)
        """
        raise NotImplementedError()

    @classmethod
    def _validate_contract(cls) -> None:
        if not hasattr(cls, "handle") or not callable(getattr(cls, "handle", None)):
            raise RuntimeError("subclass must implement `handle(self, ctx)` on the view subclass.")
        if cls.response_serializer is None:
            raise RuntimeError(
                "response_serializer (DRF Serializer) must be provided on the view subclass."
            )

    async def _call_handler(self, ctx: Dict[str, Any]) -> Any:
        result = self.handle(ctx)
        if asyncio.iscoroutine(result):
            return await result
        return result

    def _validate_item(self, item: Any) -> Optional[Dict[str, Any]]:
        """
        Validate a single item with the configured DRF `response_serializer`.
        Returns the validated data dict or raises `serializers.ValidationError`.
        """
        if self.response_serializer is None:
            return item  # no validation requested
        serializer_cls = self.response_serializer
        serializer = serializer_cls(data=item)
        if not serializer.is_valid():
            raise serializers.ValidationError(serializer.errors)
        return serializer.validated_data

    async def _get_ctx(self, request: DRFRequest) -> Dict[str, Any]:
        params = await parse_http_params(request._request)
        if isinstance(params, dict) and "params" in params and isinstance(params["params"], dict):
            resolved_params = params["params"]
        else:
            resolved_params = params if isinstance(params, dict) else {}

        return {
            "request": request._request,
            "params": resolved_params,
            "filters": resolved_params.get("filters"),
        }

    async def get(self, request: DRFRequest, *args, **kwargs):
        """
        Handle GET requests. Mirrors FastAPI http handler contract.
        """
        self._validate_contract()
        try:
            ctx = await self._get_ctx(request)
            result = await self._call_handler(ctx)
        except serializers.ValidationError as ve:
            return Response({"detail": ve.detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # materialize iterables -> list of validated records
        try:
            if hasattr(result, "__aiter__") or (
                isinstance(result, Iterable) and not isinstance(result, (str, bytes, dict))
            ):
                if hasattr(result, "__aiter__"):
                    collected = [x async for x in result]  # type: ignore
                else:
                    collected = list(result)
                validated = [self._validate_item(x) for x in collected]
                return Response(validated)
            validated = self._validate_item(result)
            return Response(validated)
        except serializers.ValidationError as ve:
            return Response({"detail": ve.detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    async def post(self, request: DRFRequest, *args, **kwargs):
        """
        Handle POST requests mapped to the same contract as GET (body preferred).
        """
        self._validate_contract()
        try:
            ctx = await self._get_ctx(request)
            result = await self._call_handler(ctx)
        except serializers.ValidationError as ve:
            return Response({"detail": ve.detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            if hasattr(result, "__aiter__") or (
                isinstance(result, Iterable) and not isinstance(result, (str, bytes, dict))
            ):
                if hasattr(result, "__aiter__"):
                    collected = [x async for x in result]  # type: ignore
                else:
                    collected = list(result)
                validated = [self._validate_item(x) for x in collected]
                return Response(validated)
            validated = self._validate_item(result)
            return Response(validated)
        except serializers.ValidationError as ve:
            return Response({"detail": ve.detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# cereon_sdk/django/utils.py
from __future__ import annotations
import json
import urllib.parse
from typing import Any, Dict, Optional, Union

from asgiref.typing import Scope
from django.core.exceptions import BadRequest
from django.http import HttpRequest, QueryDict
from rest_framework.request import Request as DRFRequest


def _maybe_decode_json_str(value: Any) -> Any:
    """
    Same heuristic as FastAPI utils: decode JSON strings or double-encoded JSON.
    """
    if isinstance(value, str):
        v = value.strip()
        if v.startswith(("{", "[", '"')) or v in ("true", "false", "null") or (v and v[0].isdigit()):
            try:
                return json.loads(v)
            except Exception:
                try:
                    return json.loads(json.loads(v))
                except Exception:
                    return value
    return value


def _normalize_querydict(qs: Union[str, bytes, QueryDict]) -> Dict[str, Any]:
    """
    Convert raw query string or Django QueryDict into a simple dict where single-values are strings.
    """
    if isinstance(qs, (bytes, bytearray)):
        qs = qs.decode("utf-8")
    if isinstance(qs, str):
        parsed = urllib.parse.parse_qs(qs, keep_blank_values=True)
    else:  # QueryDict (DRF/Django)
        parsed = {}
        for k in qs:
            v = qs.getlist(k)
            parsed[k] = v
    normalized: Dict[str, Any] = {}
    for k, v in parsed.items():
        if isinstance(v, list) and len(v) == 1:
            normalized[k] = v[0]
        else:
            normalized[k] = v
    return normalized


async def parse_http_params(request: Union[DRFRequest, HttpRequest]) -> Dict[str, Any]:
    """
    Normalize parameters from Django/DRF request similar to FastAPI variant.

    Behavior:
      - Prefer top-level 'params' querystring or body when present (and decode JSON).
      - For POST/PUT/PATCH/DELETE, prefer JSON body; accept form-encoded bodies.
      - Return plain dict; raise BadRequest on parse errors.
    """
    # Extract query string
    if hasattr(request, "query_params"):  # DRF Request
        qp = request._request.META.get("QUERY_STRING", "")
    else:
        qp = getattr(request, "META", {}).get("QUERY_STRING", "")
    normalized_query = _normalize_querydict(qp)

    # If params in querystring
    if "params" in normalized_query:
        try:
            decoded = _maybe_decode_json_str(normalized_query["params"])
            if isinstance(decoded, dict):
                return decoded
            return {"params": decoded}
        except Exception as e:
            raise BadRequest(f"Invalid JSON in query param 'params': {e}")

    # For mutating methods, try reading body
    method = getattr(request, "method", "GET").upper()
    if method in ("POST", "PUT", "PATCH", "DELETE"):
        # Try DRF .data first (handles form/json)
        try:
            data = getattr(request, "data", None)
            # If .data is empty and underlying request has body, try body
            if data in (None, {}):
                try:
                    body_raw = request.body  # may be bytes
                    if body_raw:
                        decoded = body_raw.decode("utf-8")
                        data = json.loads(decoded)
                    else:
                        data = {}
                except Exception:
                    data = {}
        except Exception:
            data = {}

        if not data:
            return normalized_query

        if isinstance(data, dict) and "params" in data:
            maybe = _maybe_decode_json_str(data["params"])
            if isinstance(maybe, dict):
                return maybe
            return {"params": maybe}

        if isinstance(data, dict):
            return data

        return {"params": _maybe_decode_json_str(data)}

    # fallback: return query params dict
    return normalized_query


async def parse_websocket_params_from_scope(scope: Scope, initial_message: Optional[str] = None) -> Dict[str, Any]:
    """
    Parse websocket params from ASGI scope['query_string'] (Channels scope).
    If `initial_message` provided use that as received initial payload (already decoded).
    Mirrors the FastAPI websocket parser.
    """
    qs_bytes = scope.get("query_string", b"")
    qs = qs_bytes.decode("utf-8") if isinstance(qs_bytes, (bytes, bytearray)) else str(qs_bytes)
    query = urllib.parse.parse_qs(qs, keep_blank_values=True)

    def _single(v):
        return v[0] if isinstance(v, list) and v else v

    payload: Dict[str, Any] = {}

    if "params" in query:
        raw = _single(query["params"])
        decoded = _maybe_decode_json_str(raw)
        if isinstance(decoded, dict):
            return decoded
        return {"params": decoded}

    mapping_keys = [
        "url",
        "topic",
        "resumeSeq",
        "subscriptionId",
        "ackPolicy",
        "compression",
        "protocols",
        "reconnectDelay",
        "maxReconnectAttempts",
        "heartbeatInterval",
    ]
    for key in mapping_keys:
        if key in query:
            v = _single(query[key])
            if key in ("resumeSeq", "reconnectDelay", "maxReconnectAttempts", "heartbeatInterval"):
                try:
                    payload[key] = int(v)
                except Exception:
                    try:
                        payload[key] = float(v)
                    except Exception:
                        payload[key] = v
            else:
                payload[key] = _maybe_decode_json_str(v)

    # headers.<name> support
    headers = {}
    for qk, qv in query.items():
        if qk.startswith("headers.") and qv:
            headers[qk.split(".", 1)[1]] = _single(qv)
    if headers:
        payload["headers"] = headers

    if payload:
        return payload

    # fallback to initial_message if provided
    if initial_message:
        try:
            parsed = json.loads(initial_message)
        except Exception:
            return {"initialMessage": initial_message}
        if isinstance(parsed, dict):
            if "params" in parsed:
                return _maybe_decode_json_str(parsed["params"]) if isinstance(parsed["params"], str) else parsed["params"]
            return parsed
        return {"initialMessage": parsed}

    return {}

# file: fastapi_card_helpers.py
import json
import urllib.parse
from typing import Any, Dict

from fastapi import Request, WebSocket, WebSocketDisconnect, HTTPException


def _maybe_decode_json_str(value: Any) -> Any:
    """
    If value is a JSON string (possibly double-encoded), decode it into Python object.
    Otherwise return value unchanged.
    """
    if isinstance(value, str):
        v = value.strip()
        # quick heuristic: starts with { or [ or " or digits/true/false/null
        if v.startswith(("{", "[", '"')) or v in ("true", "false", "null") or v[:1].isdigit():
            try:
                parsed = json.loads(v)
            except Exception:
                # fallback: sometimes encoded as a JSON string of a JSON string (double-encoded)
                try:
                    parsed = json.loads(json.loads(v))
                except Exception:
                    return value
            return parsed
    return value


async def parse_http_params(request: Request) -> Dict[str, Any]:
    """
    Parse params from a REST request into a normalized dict.

    Handling rules (based on CardExecutionProvider client-side patterns):
    - GET: if query param "params" exists, it's expected to be JSON-encoded string => decode.
      Also include any other query params (they are added to final dict, but 'params' wins for complex payload).
    - POST/PUT/PATCH: attempt to read JSON body. Body may be:
        - {"params": "<json-string>"}  (client wraps paramsJson in "params")
        - {"params": {...}}            (already object)
        - {...}                        (direct params)
      Also accept application/x-www-form-urlencoded (form).
    - Always attempt robust decoding (double-encoded JSON) and return a plain Dict[str, Any].
    - On parse failure, raises HTTPException(400).
    """
    # Start with query params (they are always available)
    qs_bytes = request.scope.get("query_string", b"")
    qs = qs_bytes.decode("utf-8") if isinstance(qs_bytes, (bytes, bytearray)) else str(qs_bytes)
    query = urllib.parse.parse_qs(qs, keep_blank_values=True)

    # Normalize single-value query params to plain strings (if multivalue, keep list)
    normalized_query: Dict[str, Any] = {}
    for k, v in query.items():
        if len(v) == 1:
            normalized_query[k] = v[0]
        else:
            normalized_query[k] = v

    # If there's a "params" query param, prefer that (it's JSON encoded by client)
    if "params" in normalized_query:
        try:
            decoded = _maybe_decode_json_str(normalized_query["params"])
            if isinstance(decoded, dict):
                return decoded
            # if params is something else (like list) put under key "params"
            return {"params": decoded}
        except Exception as e:
            raise HTTPException(
                status_code=400, detail=f"Invalid JSON in query param 'params': {e}"
            )

    # For non-GET: try to parse body
    if request.method and request.method.upper() in ("POST", "PUT", "PATCH", "DELETE"):
        # Fast path: try json
        try:
            body = await request.json()
        except Exception:
            # maybe form-encoded or empty
            try:
                form = await request.form()
                body = {k: v for k, v in form.items()}
            except Exception:
                body = None

        if body is None:
            # fallback to query string only
            return normalized_query

        # if body contains "params"
        if isinstance(body, dict) and "params" in body:
            params_val = body["params"]
            # the client sometimes sends {"params": "<json-string>"}
            maybe = _maybe_decode_json_str(params_val)
            if isinstance(maybe, dict):
                return maybe
            return {"params": maybe}

        # if body looks already like a params dict
        if isinstance(body, dict):
            return body

        # other types (list, string) -> wrap
        return {"params": _maybe_decode_json_str(body)}

    # Fallback: return normalized query dict (no 'params' found)
    return normalized_query


async def parse_websocket_params(
    websocket: WebSocket, wait_for_initial_message: bool = False
) -> Dict[str, Any]:
    """
    Parse parameters for a WebSocket connection. Returns a dict of params suitable
    for the CardExecutionProvider executeWebsocketQueryImpl payload.

    Strategy:
    1. Parse query-string on the WebSocket scope. If 'params' present -> decode JSON and return.
    2. Map common top-level expected keys if present in query-string: topic, subscriptionId, url, protocols, ackPolicy, resumeSeq, compression, reconnectDelay, maxReconnectAttempts, heartbeatInterval.
    3. If not enough info and wait_for_initial_message is True, attempt to receive the first websocket message (consumes it).
       - Accept a JSON message that contains the payload (common server/client patterns).
    4. Return a payload dict (possibly empty) — caller should validate required fields like 'url'.
    """
    # parse query string
    qs_bytes = websocket.scope.get("query_string", b"")
    qs = qs_bytes.decode("utf-8") if isinstance(qs_bytes, (bytes, bytearray)) else str(qs_bytes)
    query = urllib.parse.parse_qs(qs, keep_blank_values=True)

    def _single(v):
        return v[0] if isinstance(v, list) and v else v

    payload: Dict[str, Any] = {}

    # If a top-level 'params' exists in querystring, decode and return it
    if "params" in query:
        raw = _single(query["params"])
        decoded = _maybe_decode_json_str(raw)
        if isinstance(decoded, dict):
            return decoded
        return {"params": decoded}

    # Map common websocket payload keys (strings come from querystring)
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
            # try to coerce numeric fields
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

    # Handle potential header-like query params (headers.<name>=value)
    headers = {}
    for qk, qv in query.items():
        if qk.startswith("headers.") and qv:
            header_name = qk.split(".", 1)[1]
            headers[header_name] = _single(qv)
    if headers:
        payload["headers"] = headers

    # If we already found meaningful fields, return
    if payload:
        return payload

    # Optional: consume first JSON message from client to extract params (only when explicitly requested)
    if wait_for_initial_message:
        try:
            message = await websocket.receive_text()
            try:
                parsed = json.loads(message)
            except Exception:
                # not JSON -> return as raw string under 'initialMessage'
                return {"initialMessage": message}
            # If parsed has 'params' or is dict, process same as HTTP
            if isinstance(parsed, dict):
                if "params" in parsed:
                    return (
                        _maybe_decode_json_str(parsed["params"])
                        if isinstance(parsed["params"], str)
                        else parsed["params"]
                    )
                # Map keys directly
                return parsed
            # otherwise wrap
            return {"initialMessage": parsed}
        except WebSocketDisconnect:
            raise
        except Exception:
            # unable to read; return empty payload
            return {}

    # Nothing found
    return {}

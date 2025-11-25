# cereon_sdk/django/serializers.py
from __future__ import annotations
from typing import Any, Dict, List, Optional, Type

from rest_framework import serializers


# ---------------------------------------------------------------------------
# Core serializers
# ---------------------------------------------------------------------------
class QueryMetadataSerializer(serializers.Serializer):
    """
    Generic query/card metadata. Allows arbitrary extra fields.
    Mirrors pydantic.Config(extra="allow") by accepting an open JSON object.
    """

    startedAt = serializers.CharField(required=False, allow_null=True)
    finishedAt = serializers.CharField(required=False, allow_null=True)
    elapsedMs = serializers.IntegerField(required=False, allow_null=True)
    # Accept arbitrary extra keys
    extra = serializers.DictField(child=serializers.JSONField(), required=False)

    def to_representation(self, instance: Any) -> Dict[str, Any]:
        # instance expected to be dict-like; return as-is but preserve known keys
        if isinstance(instance, dict):
            out = dict(instance)  # shallow copy
            # keep only known keys at top-level (others stay)
            return out
        return super().to_representation(instance)

    def to_internal_value(self, data: Any) -> Dict[str, Any]:
        # Accept any mapping or JSON; ensure it's a dict
        if data is None:
            return {}
        if isinstance(data, dict):
            return data
        raise serializers.ValidationError("QueryMetadata must be a mapping")


class BaseCardRecordSerializer(serializers.Serializer):
    """
    Generic wrapper for dashboard card records.

    - kind: str
    - report_id: str
    - card_id: str
    - data: optional object (can be a nested serializer via `data_serializer_class`)
    - meta: optional metadata object (QueryMetadataSerializer)

    Usage:
      class MyRecord(BaseCardRecordSerializer):
          data_serializer_class = MyDataSerializer
    """

    kind = serializers.CharField()
    report_id = serializers.CharField(source="report_id", required=True)
    card_id = serializers.CharField(source="card_id", required=True)
    data = serializers.JSONField(required=False, allow_null=True)
    meta = QueryMetadataSerializer(required=False, allow_null=True)

    # Allow subclasses to supply a DRF Serializer class used to validate/serialize `data`
    data_serializer_class: Optional[Type[serializers.Serializer]] = None

    def to_internal_value(self, data: Any) -> Dict[str, Any]:
        """
        Validate incoming payload. If `data_serializer_class` provided, validate `data` using it.
        Accepts both camelCase keys from external clients or snake_case keys.
        """
        if not isinstance(data, dict):
            raise serializers.ValidationError("Record payload must be an object")

        # Normalize camelCase keys to snake_case used internally
        normalized = dict(data)
        # support client sending cardId/reportId
        if "cardId" in normalized and "card_id" not in normalized:
            normalized["card_id"] = normalized.pop("cardId")
        if "reportId" in normalized and "report_id" not in normalized:
            normalized["report_id"] = normalized.pop("reportId")

        # Validate meta using QueryMetadataSerializer if present
        meta = normalized.get("meta")
        if meta is not None:
            meta_ser = QueryMetadataSerializer(data=meta)
            meta_ser.is_valid(raise_exception=True)
            normalized["meta"] = meta_ser.validated_data

        # Validate data using nested serializer if supplied
        if self.data_serializer_class and "data" in normalized and normalized["data"] is not None:
            nested = self.data_serializer_class(data=normalized["data"])
            nested.is_valid(raise_exception=True)
            normalized["data"] = nested.validated_data

        # Run base field validation
        ret = super().to_internal_value(normalized)
        return ret

    def to_representation(self, instance: Any) -> Dict[str, Any]:
        """
        Produce JSON-friendly representation. If a nested data serializer is provided,
        use it to render `data`. Keep outgoing keys in camelCase to match original SDK.
        """
        if isinstance(instance, dict):
            out = dict(instance)
        else:
            out = super().to_representation(instance)

        # Render nested meta
        meta = out.get("meta")
        if meta is not None and not isinstance(meta, dict):
            try:
                meta_ser = QueryMetadataSerializer(meta)
                out["meta"] = meta_ser.data
            except Exception:
                out["meta"] = meta

        # Render nested data using data_serializer_class if provided
        if self.data_serializer_class and out.get("data") is not None:
            try:
                ser = self.data_serializer_class(out["data"])
                out["data"] = ser.data
            except Exception:
                pass

        # Keep canonical snake_case internally but also provide flattened record via to_record
        return out

    def to_record(self) -> Dict[str, Any]:
        """
        Flatten to a record dict resembling original pydantic `.to_record()`:
          - includes kind
          - meta JSON-stringified if present
          - merges data dict into top-level (if data is mapping)
        """
        validated = getattr(self, "validated_data", None)
        if validated is None:
            # if serializer not validated, fallback to serialized representation
            validated = self.data if hasattr(self, "data") else {}

        kind = validated.get("kind")
        card_id = validated.get("card_id") or validated.get("cardId")
        report_id = validated.get("report_id") or validated.get("reportId")
        meta = validated.get("meta")
        data = validated.get("data")

        base = {
            "kind": kind,
            "cardId": card_id,
            "reportId": report_id,
            "meta": None,
        }

        if meta is not None:
            # meta should be a dict -> JSON string
            try:
                import json

                base["meta"] = json.dumps(meta)
            except Exception:
                base["meta"] = str(meta)

        # merge data dict into top-level (if mapping)
        if isinstance(data, dict):
            base.update(data)
        else:
            # keep data under 'data' key otherwise
            base["data"] = data

        return base


# ---------------------------------------------------------------------------
# Chart models
# ---------------------------------------------------------------------------
class ChartCardDataSerializer(serializers.Serializer):
    data = serializers.ListField(child=serializers.DictField(child=serializers.JSONField()))


class ChartCardRecordSerializer(BaseCardRecordSerializer):
    data_serializer_class = ChartCardDataSerializer


# ---------------------------------------------------------------------------
# Table models
# ---------------------------------------------------------------------------
class TableCardDataSerializer(serializers.Serializer):
    rows = serializers.ListField(child=serializers.DictField(child=serializers.JSONField()))
    columns = serializers.ListField(child=serializers.CharField())
    totalCount = serializers.IntegerField(required=False, allow_null=True)

    def to_internal_value(self, data: Any) -> Dict[str, Any]:
        # Accept both totalCount and total_count keys
        if isinstance(data, dict) and "total_count" in data and "totalCount" not in data:
            data = dict(data)
            data["totalCount"] = data.pop("total_count")
        return super().to_internal_value(data)


class TableCardRecordSerializer(BaseCardRecordSerializer):
    data_serializer_class = TableCardDataSerializer

    def to_internal_value(self, data: Any) -> Dict[str, Any]:
        # Ensure 'kind' default for Table is "table" if not provided
        if isinstance(data, dict) and "kind" not in data:
            data = dict(data)
            data["kind"] = "table"
        return super().to_internal_value(data)


# ---------------------------------------------------------------------------
# Number / KPI models
# ---------------------------------------------------------------------------
class NumberCardDataSerializer(serializers.Serializer):
    value = serializers.FloatField()
    previousValue = serializers.FloatField(required=False, allow_null=True)
    trend = serializers.ChoiceField(
        choices=["up", "down", "neutral"], required=False, allow_null=True
    )
    trendPercentage = serializers.FloatField(required=False, allow_null=True)
    label = serializers.CharField(required=False, allow_null=True)


class NumberCardMetadataSerializer(QueryMetadataSerializer):
    # inherits flexible behavior, add number-specific keys
    unit = serializers.CharField(required=False, allow_null=True)
    format = serializers.CharField(required=False, allow_null=True)

    def to_internal_value(self, data: Any) -> Dict[str, Any]:
        if data is None:
            return {}
        if isinstance(data, dict):
            return data
        raise serializers.ValidationError("NumberCardMetadata must be a mapping")


class NumberCardRecordSerializer(BaseCardRecordSerializer):
    data_serializer_class = NumberCardDataSerializer
    meta = NumberCardMetadataSerializer(required=False, allow_null=True)

    def to_internal_value(self, data: Any) -> Dict[str, Any]:
        # enforce default kind if missing
        if isinstance(data, dict) and "kind" not in data:
            data = dict(data)
            data["kind"] = "number"
        return super().to_internal_value(data)


# ---------------------------------------------------------------------------
# Html models
# ---------------------------------------------------------------------------
class HtmlCardDataSerializer(serializers.Serializer):
    content = serializers.CharField(required=False, allow_null=True)
    rawHtml = serializers.CharField(required=False, allow_null=True)
    styles = serializers.CharField(required=False, allow_null=True)


class HtmlCardRecordSerializer(BaseCardRecordSerializer):
    data_serializer_class = HtmlCardDataSerializer

    def to_internal_value(self, data: Any) -> Dict[str, Any]:
        if isinstance(data, dict) and "kind" not in data:
            data = dict(data)
            data["kind"] = "html"
        return super().to_internal_value(data)


# ---------------------------------------------------------------------------
# Iframe models
# ---------------------------------------------------------------------------
class IframeCardDataSerializer(serializers.Serializer):
    url = serializers.CharField()
    title = serializers.CharField(required=False, allow_null=True)
    width = serializers.CharField(required=False, allow_null=True)
    height = serializers.CharField(required=False, allow_null=True)

    def to_internal_value(self, data: Any) -> Dict[str, Any]:
        # Accept numeric width/height
        if isinstance(data, dict):
            d = dict(data)
            if "width" in d and not isinstance(d["width"], str):
                d["width"] = str(d["width"])
            if "height" in d and not isinstance(d["height"], str):
                d["height"] = str(d["height"])
            data = d
        return super().to_internal_value(data)


class IframeCardRecordSerializer(BaseCardRecordSerializer):
    data_serializer_class = IframeCardDataSerializer

    def to_internal_value(self, data: Any) -> Dict[str, Any]:
        if isinstance(data, dict) and "kind" not in data:
            data = dict(data)
            data["kind"] = "iframe"
        return super().to_internal_value(data)


# ---------------------------------------------------------------------------
# Markdown models
# ---------------------------------------------------------------------------
class MarkdownCardDataSerializer(serializers.Serializer):
    content = serializers.CharField(required=False, allow_null=True)
    rawMarkdown = serializers.CharField(required=False, allow_null=True)
    styles = serializers.CharField(required=False, allow_null=True)


class MarkdownCardRecordSerializer(BaseCardRecordSerializer):
    data_serializer_class = MarkdownCardDataSerializer

    def to_internal_value(self, data: Any) -> Dict[str, Any]:
        if isinstance(data, dict) and "kind" not in data:
            data = dict(data)
            data["kind"] = "markdown"
        return super().to_internal_value(data)

# cereon_sdk/cereon_sdk/core/types.py
from typing import Any, Dict, Generic, List, Optional, TypeVar, Union, Literal

from pydantic import BaseModel, Field, ConfigDict

T = TypeVar("T", bound=BaseModel)


# ---------------------------------------------------------------------------
# Core models
# ---------------------------------------------------------------------------
class QueryMetadata(BaseModel):
    """
    Generic query/card metadata. Allows arbitrary extra fields (backwards compatible).
    """

    model_config = ConfigDict(extra="allow")

    startedAt: Optional[str] = Field(None)
    finishedAt: Optional[str] = Field(None)
    elapsedMs: Optional[int] = Field(None)


class BaseCardRecord(BaseModel, Generic[T]):
    """
    Generic wrapper for dashboard card records.

    - kind: card type identifier
    - data: typed payload (specific card data model)
    - meta: query/card metadata (may be specialized per-card)
    """

    kind: str = Field(..., description="Type of the dashboard card")
    report_id: str = Field(..., description="Identifier for the report this card belongs to")
    card_id: str = Field(..., description="Identifier for the dashboard card")
    data: Optional[T] = Field(None, description="Typed payload for the card")
    meta: Optional[QueryMetadata] = Field(None, description="Metadata for the dashboard card")

    def to_record(self) -> Dict[str, Any]:
        """
        Flatten to a record dict:
        - includes kind
        - meta is serialized to JSON string (original behavior preserved)
        - merges data.model_dump() into top-level if data present
        """
        return {
            "kind": self.kind,
            "cardId": self.card_id,
            "reportId": self.report_id,
            "meta": self.meta.model_dump_json() if self.meta else None,
            **(self.data.model_dump() if self.data else {}),
        }


# ---------------------------------------------------------------------------
# Chart models
# ---------------------------------------------------------------------------
class ChartCardData(BaseModel):
    """
    Chart payload: list of data points and optional metadata.
    """

    data: List[Dict[str, Any]] = Field(..., description="Data points for the chart")


class ChartCardRecord(BaseCardRecord[ChartCardData]):
    """
    Concrete card record for charts. Keeps generic `kind` so other chart variants can exist.
    """

    pass


# ---------------------------------------------------------------------------
# Table models
# ---------------------------------------------------------------------------
class TableCardData(BaseModel):
    """
    Table payload: rows, columns and optional total count.
    """

    rows: List[Dict[str, Any]] = Field(..., description="Rows of the table")
    columns: List[str] = Field(..., description="Column names of the table")
    totalCount: Optional[int] = Field(None, description="Total number of rows available")


class TableCardRecord(BaseCardRecord[TableCardData]):
    """
    Table card record. `kind` is constrained to literal "table" for clarity.
    """

    kind: Literal["table"] = Field("table", description="Type of the dashboard card")


# ---------------------------------------------------------------------------
# Number / KPI models
# ---------------------------------------------------------------------------
class NumberCardData(BaseModel):
    """
    Numeric KPI/card payload.
    """

    value: float = Field(..., description="Numeric value to be displayed")
    previousValue: Optional[float] = Field(
        None, description="Previous numeric value for comparison"
    )
    trend: Optional[Literal["up", "down", "neutral"]] = Field(
        None, description="Trend indicator (e.g., 'up', 'down', 'neutral')"
    )
    trendPercentage: Optional[float] = Field(None, description="Percentage change for the trend")
    label: Optional[str] = Field(None, description="Label for the numeric value")


class NumberCardMetadata(QueryMetadata):
    """
    Number-specific metadata (formatting/unit info).
    """

    model_config = ConfigDict(extra="allow")

    unit: Optional[str] = Field(None, description="Unit of the numeric value")
    format: Optional[str] = Field(None, description="Format of the numeric value")


class NumberCardRecord(BaseCardRecord[NumberCardData]):
    """
    Number card record. `kind` constrained to literal "number".
    """

    kind: Literal["number"] = Field("number", description="Type of the dashboard card")
    meta: Optional[NumberCardMetadata] = Field(None, description="Metadata for the number card")


# ---------------------------------------------------------------------------
# Html models
# ---------------------------------------------------------------------------
class HtmlCardData(BaseModel):
    """
    HTML content payload for a card.
    """

    content: Optional[str] = Field(None, description="HTML content to be rendered in the card")
    rawHtml: Optional[str] = Field(
        None, description="Raw HTML string for the card without sanitization (use with caution)"
    )
    styles: Optional[str] = Field(
        None,
        description="Inject custom styles if provided in <style dangerouslySetInnerHTML={{ __html: record.styles }} />",
    )


class HtmlCardRecord(BaseCardRecord[HtmlCardData]):
    """
    HTML card record. `kind` constrained to literal "html".
    """

    kind: Literal["html"] = Field("html", description="Type of the dashboard card")


# ---------------------------------------------------------------------------
# Iframe models
# ---------------------------------------------------------------------------
class IframeCardData(BaseModel):
    """
    Iframe payload for embedding external content.
    """

    url: str = Field(..., description="URL of the content to be embedded in the iframe")
    title: Optional[str] = Field(None, description="Title of the iframe content")
    width: Optional[Union[str, int]] = Field(
        None, description="Width of the iframe (e.g., '100%', 600)"
    )
    height: Optional[Union[str, int]] = Field(
        None, description="Height of the iframe (e.g., '400px', 800)"
    )


class IframeCardRecord(BaseCardRecord[IframeCardData]):
    """
    Iframe card record. `kind` constrained to literal "iframe".
    """

    kind: Literal["iframe"] = Field("iframe", description="Type of the dashboard card")


# ---------------------------------------------------------------------------
# Markdown models
# ---------------------------------------------------------------------------
class MarkdownCardData(BaseModel):
    """
    Markdown content payload for a card.
    """

    content: Optional[str] = Field(None, description="Markdown content to be rendered in the card")
    rawMarkdown: Optional[str] = Field(
        None, description="Raw markdown string for the card without sanitization (use with caution)"
    )
    styles: Optional[str] = Field(
        None,
        description="Inject custom styles if provided in <style dangerouslySetInnerHTML={{ __html: record.styles }} />",
    )


class MarkdownCardRecord(BaseCardRecord[MarkdownCardData]):
    """
    Markdown card record. `kind` constrained to literal "markdown".
    """

    kind: Literal["markdown"] = Field("markdown", description="Type of the dashboard card")

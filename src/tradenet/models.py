"""Shared data models for trade flows."""

from __future__ import annotations

from pydantic import BaseModel, Field


class TradeFlow(BaseModel):
    """A single bilateral trade record normalised for storage and Neo4j export."""

    year: int
    flow: str = Field(description="import or export from the reporter's perspective")
    supply_category: str
    commodity_code: str
    commodity_description: str | None = None
    reporter_iso: str
    reporter_name: str | None = None
    partner_iso: str
    partner_name: str | None = None
    trade_value_usd: float | None = None
    net_weight_kg: float | None = None
    quantity: float | None = None
    quantity_unit: str | None = None
    source: str = "un_comtrade"

    @property
    def flow_id(self) -> str:
        return (
            f"{self.year}:{self.reporter_iso}:{self.partner_iso}:"
            f"{self.flow}:{self.supply_category}:{self.commodity_code}"
        )

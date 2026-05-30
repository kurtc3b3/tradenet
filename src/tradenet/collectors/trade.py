"""Collect bilateral trade flows from UN Comtrade."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from rich.console import Console
from rich.progress import Progress

from tradenet.comtrade.categories import SupplyCategory, comtrade_cmd_code, resolve_categories
from tradenet.comtrade.client import FLOW_EXPORT, FLOW_IMPORT, ComtradeClient
from tradenet.models import TradeFlow
from tradenet.settings import Settings, get_settings

console = Console()
FlowDirection = Literal["import", "export", "both"]


def collect_trade_flows(
    *,
    reporters: list[str],
    partners: list[str] | None = None,
    years: list[int],
    categories: list[str] | None = None,
    flow: FlowDirection = "both",
    preview: bool = False,
    output_dir: Path | None = None,
    settings: Settings | None = None,
) -> Path:
    """Fetch trade data and persist normalised flows as JSONL."""

    settings = settings or get_settings()
    output_root = output_dir or settings.data_dir / "trade"
    output_root.mkdir(parents=True, exist_ok=True)
    output_path = output_root / "flows.jsonl"

    supply_categories = resolve_categories(categories)
    flow_codes = _resolve_flow_codes(flow)

    total_written = 0
    with ComtradeClient(settings) as client, output_path.open("w", encoding="utf-8") as handle:
        reporter_codes = [_resolve_country(client, reporter) for reporter in reporters]
        partner_codes = [_resolve_country(client, partner) for partner in partners] if partners else [None]

        tasks = [
            (reporter_code, partner_code, year, category, flow_code)
            for reporter_code in reporter_codes
            for partner_code in partner_codes
            for year in years
            for category in supply_categories
            for flow_code in flow_codes
        ]

        with Progress() as progress:
            task_id = progress.add_task("Collecting trade flows", total=len(tasks))
            for reporter_code, partner_code, year, category, flow_code in tasks:
                rows = client.fetch_trade_data(
                    reporter_code=reporter_code,
                    period=str(year),
                    cmd_code=comtrade_cmd_code(category),
                    flow_code=flow_code,
                    partner_code=partner_code,
                    preview=preview,
                )
                for row in rows:
                    trade_flow = _normalise_row(row, category, flow_code)
                    handle.write(trade_flow.model_dump_json())
                    handle.write("\n")
                    total_written += 1
                progress.advance(task_id)

    console.print(
        f"[green]Wrote {total_written} trade flows[/green] to [bold]{output_path}[/bold]"
    )
    return output_path


def _resolve_flow_codes(flow: FlowDirection) -> list[str]:
    if flow == "import":
        return [FLOW_IMPORT]
    if flow == "export":
        return [FLOW_EXPORT]
    return [FLOW_EXPORT, FLOW_IMPORT]


def _resolve_country(client: ComtradeClient, country: str) -> str:
    if country.isdigit():
        return country
    return client.resolve_reporter_code(country)


def _normalise_row(row: dict, category: SupplyCategory, flow_code: str) -> TradeFlow:
    flow = "export" if flow_code == FLOW_EXPORT else "import"
    return TradeFlow(
        year=int(str(row.get("period", "0"))[:4]),
        flow=flow,
        supply_category=category.id,
        commodity_code=str(row.get("cmdCode", category.hs_codes[0])),
        commodity_description=row.get("cmdDesc"),
        reporter_iso=str(row.get("reporterISO") or row.get("reporterCode")),
        reporter_name=row.get("reporterDesc"),
        partner_iso=str(row.get("partnerISO") or row.get("partnerCode")),
        partner_name=row.get("partnerDesc"),
        trade_value_usd=_to_float(row.get("primaryValue")),
        net_weight_kg=_to_float(row.get("netWgt")),
        quantity=_to_float(row.get("qty")),
        quantity_unit=row.get("qtyUnitAbbr"),
    )


def _to_float(value: object) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def load_trade_flows(path: Path) -> list[TradeFlow]:
    flows: list[TradeFlow] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            flows.append(TradeFlow.model_validate(json.loads(line)))
    return flows

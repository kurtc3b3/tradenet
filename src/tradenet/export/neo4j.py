"""Export collected trade flows for Neo4j bulk import."""

from __future__ import annotations

import csv
from pathlib import Path

from rich.console import Console

from tradenet.collectors.trade import load_trade_flows
from tradenet.models import TradeFlow

console = Console()


def export_neo4j(
    *,
    input_path: Path,
    output_dir: Path,
) -> Path:
    """Write country nodes and TRADES_WITH relationships as CSV files."""

    flows = load_trade_flows(input_path)
    if not flows:
        raise ValueError(f"No trade flows found in {input_path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    countries_path = output_dir / "nodes_countries.csv"
    categories_path = output_dir / "nodes_categories.csv"
    flows_path = output_dir / "rels_trades_with.csv"

    countries = _collect_countries(flows)
    categories = _collect_categories(flows)

    _write_countries(countries_path, countries)
    _write_categories(categories_path, categories)
    _write_relationships(flows_path, flows)

    console.print(
        "[green]Neo4j import files written:[/green]\n"
        f"  countries: {countries_path}\n"
        f"  categories: {categories_path}\n"
        f"  relationships: {flows_path}"
    )
    return output_dir


def _collect_countries(flows: list[TradeFlow]) -> dict[str, str | None]:
    countries: dict[str, str | None] = {}
    for flow in flows:
        countries.setdefault(flow.reporter_iso, flow.reporter_name)
        countries.setdefault(flow.partner_iso, flow.partner_name)
    return countries


def _collect_categories(flows: list[TradeFlow]) -> dict[str, str]:
    return {flow.supply_category: flow.supply_category.replace("_", " ").title() for flow in flows}


def _write_countries(path: Path, countries: dict[str, str | None]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["countryId:ID(Country)", "iso3", "name"])
        for iso3, name in sorted(countries.items()):
            writer.writerow([iso3, iso3, name or iso3])


def _write_categories(path: Path, categories: dict[str, str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["categoryId:ID(Category)", "id", "name"])
        for category_id, name in sorted(categories.items()):
            writer.writerow([category_id, category_id, name])


def _write_relationships(path: Path, flows: list[TradeFlow]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                ":START_ID(Country)",
                ":END_ID(Country)",
                ":TYPE",
                "flowId",
                "year",
                "flow",
                "supplyCategory",
                "commodityCode",
                "commodityDescription",
                "tradeValueUsd",
                "netWeightKg",
                "quantity",
                "quantityUnit",
            ]
        )
        for flow in flows:
            start_id, end_id = _relationship_endpoints(flow)
            writer.writerow(
                [
                    start_id,
                    end_id,
                    "TRADES_WITH",
                    flow.flow_id,
                    flow.year,
                    flow.flow,
                    flow.supply_category,
                    flow.commodity_code,
                    flow.commodity_description or "",
                    flow.trade_value_usd if flow.trade_value_usd is not None else "",
                    flow.net_weight_kg if flow.net_weight_kg is not None else "",
                    flow.quantity if flow.quantity is not None else "",
                    flow.quantity_unit or "",
                ]
            )


def _relationship_endpoints(flow: TradeFlow) -> tuple[str, str]:
    if flow.flow == "export":
        return flow.reporter_iso, flow.partner_iso
    return flow.partner_iso, flow.reporter_iso

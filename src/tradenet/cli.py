"""Argparse CLI for tradenet data collection."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table

from tradenet import __version__
from tradenet.collectors.trade import collect_trade_flows
from tradenet.comtrade.categories import SUPPLY_CATEGORIES
from tradenet.comtrade.client import ComtradeClient
from tradenet.export.neo4j import export_neo4j
from tradenet.settings import get_settings

console = Console()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tradenet",
        description="Collect bilateral trade data for Neo4j network visualisation.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    collect = subparsers.add_parser(
        "collect",
        help="Fetch import/export flows from UN Comtrade.",
    )
    collect.add_argument(
        "--reporter",
        dest="reporters",
        action="append",
        required=True,
        metavar="COUNTRY",
        help="Reporting country (ISO3, name, or numeric Comtrade code). Repeatable.",
    )
    collect.add_argument(
        "--partner",
        dest="partners",
        action="append",
        metavar="COUNTRY",
        help="Partner country filter. Omit for all partners.",
    )
    collect.add_argument(
        "--year",
        dest="years",
        action="append",
        type=int,
        required=True,
        metavar="YYYY",
        help="Trade year. Repeatable.",
    )
    collect.add_argument(
        "--category",
        dest="categories",
        action="append",
        metavar="CATEGORY",
        help=(
            "Supply category (energy, food, metals, chemicals, textiles, machinery, "
            "transport, wood, minerals, all). Default: all except 'all'."
        ),
    )
    collect.add_argument(
        "--flow",
        choices=("import", "export", "both"),
        default="both",
        help="Trade direction from the reporter's perspective.",
    )
    collect.add_argument(
        "--preview",
        action="store_true",
        help="Use the free preview API (max 500 records, no subscription key).",
    )
    collect.add_argument(
        "--output-dir",
        type=Path,
        help="Directory for flows.jsonl (default: DATA_DIR/trade).",
    )

    export = subparsers.add_parser(
        "export-neo4j",
        help="Convert collected flows into Neo4j bulk-import CSV files.",
    )
    export.add_argument(
        "--input",
        type=Path,
        help="Path to flows.jsonl (default: DATA_DIR/trade/flows.jsonl).",
    )
    export.add_argument(
        "--output-dir",
        type=Path,
        help="Directory for Neo4j CSV output (default: DATA_DIR/neo4j).",
    )

    categories = subparsers.add_parser(
        "categories",
        help="List supply categories and HS code mappings.",
    )

    countries = subparsers.add_parser(
        "countries",
        help="Search UN Comtrade reporter countries.",
    )
    countries.add_argument(
        "--search",
        help="Filter countries by name, ISO code, or Comtrade numeric code.",
    )

    return parser


def cmd_collect(args: argparse.Namespace) -> int:
    settings = get_settings()
    collect_trade_flows(
        reporters=args.reporters,
        partners=args.partners,
        years=args.years,
        categories=args.categories,
        flow=args.flow,
        preview=args.preview,
        output_dir=args.output_dir,
        settings=settings,
    )
    return 0


def cmd_export_neo4j(args: argparse.Namespace) -> int:
    settings = get_settings()
    input_path = args.input or settings.data_dir / "trade" / "flows.jsonl"
    output_dir = args.output_dir or settings.data_dir / "neo4j"
    export_neo4j(input_path=input_path, output_dir=output_dir)
    return 0


def cmd_categories(_: argparse.Namespace) -> int:
    table = Table(title="Supply categories")
    table.add_column("ID")
    table.add_column("Name")
    table.add_column("HS chapters")
    table.add_column("Description")

    for category in SUPPLY_CATEGORIES.values():
        hs = category.hs_codes[0] if len(category.hs_codes) == 1 else f"{len(category.hs_codes)} chapters"
        table.add_row(category.id, category.name, hs, category.description)

    console.print(table)
    return 0


def cmd_countries(args: argparse.Namespace) -> int:
    with ComtradeClient() as client:
        rows = client.lookup_reporters(args.search)

    if not rows:
        console.print("[yellow]No countries matched your search.[/yellow]")
        return 0

    table = Table(title="UN Comtrade reporters")
    table.add_column("Code")
    table.add_column("ISO")
    table.add_column("Name")

    for row in rows[:100]:
        table.add_row(row.get("id", ""), row.get("isoCode", ""), row.get("text", ""))

    console.print(table)
    if len(rows) > 100:
        console.print(f"[dim]Showing 100 of {len(rows)} matches.[/dim]")
    return 0


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    handlers = {
        "collect": cmd_collect,
        "export-neo4j": cmd_export_neo4j,
        "categories": cmd_categories,
        "countries": cmd_countries,
    }

    try:
        exit_code = handlers[args.command](args)
    except (ValueError, RuntimeError) as exc:
        console.print(f"[red]Error:[/red] {exc}")
        exit_code = 1

    sys.exit(exit_code)


if __name__ == "__main__":
    main()

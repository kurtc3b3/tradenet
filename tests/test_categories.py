from tradenet.comtrade.categories import comtrade_cmd_code, resolve_categories
from tradenet.export.neo4j import _relationship_endpoints
from tradenet.models import TradeFlow


def test_resolve_categories_defaults_exclude_all():
    categories = resolve_categories(None)
    ids = {category.id for category in categories}
    assert "energy" in ids
    assert "all" not in ids


def test_comtrade_cmd_code_joins_chapters():
    categories = resolve_categories(["food"])
    assert comtrade_cmd_code(categories[0]).startswith("01,")


def test_relationship_endpoints_follow_flow_direction():
    export_flow = TradeFlow(
        year=2022,
        flow="export",
        supply_category="energy",
        commodity_code="27",
        reporter_iso="DEU",
        partner_iso="USA",
    )
    import_flow = export_flow.model_copy(update={"flow": "import"})

    assert _relationship_endpoints(export_flow) == ("DEU", "USA")
    assert _relationship_endpoints(import_flow) == ("USA", "DEU")

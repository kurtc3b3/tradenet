"""Supply-type categories mapped to UN Comtrade HS commodity codes."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SupplyCategory:
    id: str
    name: str
    description: str
    hs_codes: tuple[str, ...]


SUPPLY_CATEGORIES: dict[str, SupplyCategory] = {
    "energy": SupplyCategory(
        id="energy",
        name="Energy",
        description="Mineral fuels, oils, and related products",
        hs_codes=("27",),
    ),
    "food": SupplyCategory(
        id="food",
        name="Food & Agriculture",
        description="Live animals, crops, prepared food, and beverages",
        hs_codes=tuple(f"{chapter:02d}" for chapter in range(1, 25)),
    ),
    "metals": SupplyCategory(
        id="metals",
        name="Metals",
        description="Base metals and articles thereof",
        hs_codes=tuple(f"{chapter:02d}" for chapter in range(72, 84)),
    ),
    "chemicals": SupplyCategory(
        id="chemicals",
        name="Chemicals",
        description="Organic and inorganic chemicals, plastics, and rubber",
        hs_codes=tuple(f"{chapter:02d}" for chapter in range(28, 40)),
    ),
    "textiles": SupplyCategory(
        id="textiles",
        name="Textiles",
        description="Textiles, apparel, and footwear",
        hs_codes=tuple(f"{chapter:02d}" for chapter in range(50, 68)),
    ),
    "machinery": SupplyCategory(
        id="machinery",
        name="Machinery & Electronics",
        description="Machinery, electrical equipment, and precision instruments",
        hs_codes=("84", "85", "90", "91", "92"),
    ),
    "transport": SupplyCategory(
        id="transport",
        name="Transport Equipment",
        description="Vehicles, aircraft, ships, and related parts",
        hs_codes=("86", "87", "88", "89"),
    ),
    "wood": SupplyCategory(
        id="wood",
        name="Wood & Paper",
        description="Wood products, pulp, and paper",
        hs_codes=("44", "45", "46", "47", "48", "49"),
    ),
    "minerals": SupplyCategory(
        id="minerals",
        name="Minerals & Ores",
        description="Ores, slag, ash, and mineral products (excluding fuels)",
        hs_codes=("25", "26"),
    ),
    "all": SupplyCategory(
        id="all",
        name="All Commodities",
        description="Aggregate trade across all commodity groups",
        hs_codes=("TOTAL",),
    ),
}


def resolve_categories(category_ids: list[str] | None) -> list[SupplyCategory]:
    if not category_ids:
        return [cat for cat_id, cat in SUPPLY_CATEGORIES.items() if cat_id != "all"]

    resolved: list[SupplyCategory] = []
    for category_id in category_ids:
        key = category_id.strip().lower()
        if key not in SUPPLY_CATEGORIES:
            valid = ", ".join(sorted(SUPPLY_CATEGORIES))
            raise ValueError(f"Unknown supply category '{category_id}'. Valid options: {valid}")
        resolved.append(SUPPLY_CATEGORIES[key])
    return resolved


def comtrade_cmd_code(category: SupplyCategory) -> str:
    return ",".join(category.hs_codes)

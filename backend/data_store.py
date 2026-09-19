"""Read-only reference data used by the stateless scoring service."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent / "data" / "csv"
_SEPARATOR = re.compile(r"[/,，、;；]+")


def _tokens(value: str | None) -> tuple[str, ...]:
    return tuple(token.strip() for token in _SEPARATOR.split(value or "") if token.strip())


def _read_csv(filename: str) -> list[dict[str, str]]:
    path = DATA_DIR / filename
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


@dataclass(frozen=True)
class AdditiveRecord:
    name: str
    aliases: tuple[str, ...]
    type: str
    risk_level: str
    forbidden_groups: tuple[str, ...]
    reason: str
    standard: str


@dataclass(frozen=True)
class GroupWarningRecord:
    group_type: str
    warning_type: str
    nutrient: str
    level: str
    warning_msg: str
    suggestion: str


@dataclass(frozen=True)
class AvoidOptionRecord:
    id: int
    name: str
    keywords: tuple[str, ...]
    warning_msg: str
    suggestion: str


@dataclass(frozen=True)
class BeneficialIngredientRecord:
    group_type: str
    nutrient: str
    benefit_category: str
    benefit: str
    suggestion: str


@dataclass(frozen=True)
class ReferenceData:
    additives: tuple[AdditiveRecord, ...]
    group_warnings: tuple[GroupWarningRecord, ...]
    avoid_options: tuple[AvoidOptionRecord, ...]
    beneficial_ingredients: tuple[BeneficialIngredientRecord, ...]


@lru_cache(maxsize=1)
def _load_reference_data() -> ReferenceData:
    additives = tuple(
        AdditiveRecord(
            name=row["name"].strip(),
            aliases=_tokens(row.get("alias")),
            type=(row.get("type") or "").strip(),
            risk_level=(row.get("risk_level") or "").strip(),
            forbidden_groups=_tokens(row.get("forbidden_group")),
            reason=(row.get("reason") or "").strip(),
            standard=(row.get("standard") or "").strip(),
        )
        for row in _read_csv("additives.csv")
        if row.get("name")
    )
    group_warnings = tuple(
        GroupWarningRecord(
            group_type=(row.get("group_type") or "").strip(),
            warning_type=(row.get("warning_type") or "").strip(),
            nutrient=(row.get("nutrient") or "").strip(),
            level=(row.get("level") or "").strip(),
            warning_msg=(row.get("warning_msg") or "").strip(),
            suggestion=(row.get("suggestion") or "").strip(),
        )
        for row in _read_csv("group_warnings.csv")
        if row.get("group_type")
    )
    avoid_options = tuple(
        AvoidOptionRecord(
            id=index,
            name=row["name"].strip(),
            keywords=_tokens(row.get("keywords")),
            warning_msg=(row.get("warning_msg") or "").strip(),
            suggestion=(row.get("suggestion") or "").strip(),
        )
        for index, row in enumerate(_read_csv("avoid_options.csv"), start=1)
        if row.get("name")
    )
    beneficial_ingredients = tuple(
        BeneficialIngredientRecord(
            group_type=(row.get("group_type") or "").strip(),
            nutrient=(row.get("nutrient") or "").strip(),
            benefit_category=(row.get("benefit_category") or "").strip(),
            benefit=(row.get("benefit") or "").strip(),
            suggestion=(row.get("suggestion") or "").strip(),
        )
        for row in _read_csv("beneficial_ingredients.csv")
        if row.get("group_type")
    )
    return ReferenceData(additives, group_warnings, avoid_options, beneficial_ingredients)


def load_reference_data(force_reload: bool = False) -> ReferenceData:
    """Return cached CSV reference data, optionally forcing a development reload."""
    if force_reload:
        _load_reference_data.cache_clear()
    return _load_reference_data()

"""Markdown estimate table parser."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Iterable, List, Optional

from .config import ParserConfig
from .volume import evaluate_formula, extract_formula, parse_number

LOGGER = logging.getLogger(__name__)
_SKIP_RE = re.compile(
    r"(итого|всего|накладн|сметн\w* прибыл|зарплат|затрат\w* труда|\bОТ\b|НР\s*=|СП\s*=)",
    re.IGNORECASE,
)
_UNIT_HINT_RE = re.compile(r"^(шт\.?|м2|м3|м|кг|т|компл\.?|100\s*\w+|1\s*\w+|ед\.?|маш\.?-?ч|чел\.?-?ч)$", re.IGNORECASE)


@dataclass
class EstimateItem:
    number: str
    code: str
    name: str
    unit: str
    quantity: float
    note: str = ""

    def as_dict(self) -> dict:
        return {
            "№ п/п": self.number,
            "Код расценки": self.code,
            "Наименование работ": self.name,
            "Единица измерения": self.unit,
            "Количество": self.quantity,
            "Примечание": self.note,
        }


def parse_estimate_markdown(text: str, config: Optional[ParserConfig] = None) -> List[EstimateItem]:
    """Extract work volume statement rows from Markdown-like estimate text."""
    cfg = config or ParserConfig()
    code_re = re.compile(cfg.code_regex, re.IGNORECASE)
    rows = _normalize_rows(text)
    items: List[EstimateItem] = []
    last_item: Optional[EstimateItem] = None

    for row in rows:
        formula = extract_formula(row)
        if formula and last_item is not None:
            try:
                value = evaluate_formula(formula)
            except Exception as exc:  # keep parsing other positions
                LOGGER.warning("Не удалось вычислить формулу '%s': %s", formula, exc)
                continue
            if not last_item.quantity:
                last_item.quantity = value
            last_item.note = f"Объем={formula}"
            continue

        cells = split_table_row(row)
        if not cells or _is_separator(cells) or _should_skip(row):
            continue

        code_index = _find_code_cell(cells, code_re)
        if code_index is None:
            if last_item and _looks_like_continuation(cells):
                last_item.name = " ".join([last_item.name, _clean(" ".join(cells))]).strip()
            continue

        item = _item_from_cells(cells, code_index, cfg)
        if item is None:
            LOGGER.debug("Пропущена строка с кодом из-за неполных данных: %s", row)
            continue
        items.append(item)
        last_item = item

    LOGGER.info("Найдено позиций: %s", len(items))
    return items


def split_table_row(row: str) -> List[str]:
    """Split a Markdown pipe table row into trimmed cells."""
    stripped = row.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [_clean(cell) for cell in stripped.split("|")]


def _normalize_rows(text: str) -> List[str]:
    rows: List[str] = []
    current = ""
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("|"):
            if current:
                rows.append(current)
            current = line
        elif current:
            current = f"{current} {line}"
        else:
            rows.append(line)
    if current:
        rows.append(current)
    return rows


def _item_from_cells(cells: List[str], code_index: int, cfg: ParserConfig) -> Optional[EstimateItem]:
    number = _cell_at(cells, code_index + cfg.number_offset) or _guess_number(cells[:code_index])
    code = _cell_at(cells, code_index)
    name = _cell_at(cells, code_index + cfg.name_offset)
    unit = _cell_at(cells, code_index + cfg.unit_offset)
    quantity_cell = _cell_at(cells, code_index + cfg.quantity_offset)

    if not unit or not _UNIT_HINT_RE.match(unit):
        unit, quantity_cell = _guess_unit_and_quantity(cells, code_index, unit, quantity_cell)

    quantity = parse_number(quantity_cell or "")
    if not code or not name or not unit:
        return None
    return EstimateItem(
        number=number or str(len(cells)),
        code=code,
        name=name,
        unit=unit,
        quantity=quantity if quantity is not None else 0.0,
    )


def _guess_unit_and_quantity(cells: List[str], code_index: int, unit: Optional[str], quantity: Optional[str]) -> tuple[str, Optional[str]]:
    for idx in range(code_index + 2, min(len(cells), code_index + 8)):
        cell = cells[idx]
        next_cell = _cell_at(cells, idx + 1)
        if cell and _UNIT_HINT_RE.match(cell) and parse_number(next_cell or "") is not None:
            return cell, next_cell
    return unit or "", quantity


def _find_code_cell(cells: Iterable[str], code_re: re.Pattern) -> Optional[int]:
    for index, cell in enumerate(cells):
        if code_re.search(cell):
            return index
    return None


def _cell_at(cells: List[str], index: int) -> Optional[str]:
    if 0 <= index < len(cells):
        return cells[index].strip()
    return None


def _guess_number(cells: List[str]) -> str:
    for cell in reversed(cells):
        if re.fullmatch(r"\d+", cell):
            return cell
    return ""


def _looks_like_continuation(cells: List[str]) -> bool:
    joined = " ".join(cells).strip()
    return bool(joined and not _should_skip(joined) and not _is_separator(cells))


def _is_separator(cells: List[str]) -> bool:
    return all(re.fullmatch(r":?-{2,}:?", cell.replace(" ", "")) for cell in cells if cell)


def _should_skip(text: str) -> bool:
    return bool(_SKIP_RE.search(text))


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\u00a0", " ")).strip()

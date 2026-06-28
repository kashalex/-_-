"""Export utilities for extracted estimate items."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd

from .parser import EstimateItem

COLUMNS = ["№ п/п", "Код расценки", "Наименование работ", "Единица измерения", "Количество", "Примечание"]


def items_to_dataframe(items: Iterable[EstimateItem]) -> pd.DataFrame:
    return pd.DataFrame([item.as_dict() for item in items], columns=COLUMNS)


def export_items(items: Iterable[EstimateItem], output_path: str, output_format: str = "csv") -> Path:
    path = Path(output_path)
    df = items_to_dataframe(items)
    if output_format == "xlsx" or path.suffix.lower() == ".xlsx":
        df.to_excel(path, index=False)
    elif output_format == "csv" or path.suffix.lower() == ".csv":
        df.to_csv(path, index=False, encoding="utf-8-sig")
    else:
        raise ValueError("Поддерживаются только форматы csv и xlsx")
    return path

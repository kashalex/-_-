"""Configuration objects for estimate extraction."""

from dataclasses import dataclass


DEFAULT_CODE_REGEX = r"(ГЭСНп|ГЭСН|ФЕРр|ФЕРм|ФЕР|ТЕРр|ТЕРм|ТЕР)[^|]*"


@dataclass
class ParserConfig:
    """Column hints and matching rules for Markdown estimate tables."""

    code_regex: str = DEFAULT_CODE_REGEX
    number_offset: int = -1
    name_offset: int = 1
    unit_offset: int = 2
    quantity_offset: int = 3

"""End-to-end document pipeline: source file -> Markdown -> extracted table."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .config import ParserConfig
from .export import export_items, items_to_dataframe
from .mineru_client import MinerUClient
from .parser import parse_estimate_markdown


@dataclass
class PipelineResult:
    markdown: str
    dataframe: object
    markdown_path: Optional[Path] = None
    output_path: Optional[Path] = None


def process_markdown_text(markdown: str, code_regex: Optional[str] = None) -> PipelineResult:
    config = ParserConfig(code_regex=code_regex) if code_regex else ParserConfig()
    items = parse_estimate_markdown(markdown, config=config)
    return PipelineResult(markdown=markdown, dataframe=items_to_dataframe(items))


def process_document(
    input_path: str,
    mineru_client: MinerUClient,
    mode: str,
    output_path: Optional[str] = None,
    output_format: str = "csv",
    markdown_output: Optional[str] = None,
    code_regex: Optional[str] = None,
    model_version: str = "vlm",
    language: str = "ru",
) -> PipelineResult:
    markdown = mineru_client.convert_file(input_path, mode=mode, model_version=model_version, language=language)
    markdown_path = None
    if markdown_output:
        markdown_path = Path(markdown_output)
        markdown_path.write_text(markdown, encoding="utf-8")
    config = ParserConfig(code_regex=code_regex) if code_regex else ParserConfig()
    items = parse_estimate_markdown(markdown, config=config)
    dataframe = items_to_dataframe(items)
    saved_output = None
    if output_path:
        saved_output = export_items(items, output_path, output_format=output_format)
    return PipelineResult(markdown=markdown, dataframe=dataframe, markdown_path=markdown_path, output_path=saved_output)

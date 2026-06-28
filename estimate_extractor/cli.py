"""Command-line interface for estimate extraction."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from .export import export_items, items_to_dataframe
from .mineru_client import MinerUClient, MinerUError
from .config import ParserConfig
from .parser import parse_estimate_markdown
from .pipeline import process_document


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Извлечь ведомость объёмов работ из сметного документа")
    parser.add_argument("-i", "--input", required=True, help="Путь к исходному документу или готовому Markdown")
    parser.add_argument("-o", "--output", help="Путь к выходному CSV/XLSX")
    parser.add_argument("--format", choices=["csv", "xlsx"], default="csv", help="Формат результата")
    parser.add_argument("--encoding", default="utf-8", help="Кодировка для чтения готового Markdown")
    parser.add_argument("--code-regex", help="Регулярное выражение для поиска кода норматива")
    parser.add_argument("--markdown-output", help="Куда сохранить промежуточный Markdown")
    parser.add_argument("--from-md", action="store_true", help="Вход уже является Markdown, MinerU не вызывать")
    parser.add_argument("--mineru-mode", choices=["accurate", "agent"], default="accurate", help="Режим MinerU")
    parser.add_argument("--mineru-api-key", default=os.getenv("MINERU_API_KEY"), help="API key MinerU для accurate режима")
    parser.add_argument("--model-version", choices=["pipeline", "vlm", "MinerU-HTML"], default="vlm")
    parser.add_argument("--language", default="ru")
    parser.add_argument("--verbose", action="store_true", help="Подробное логирование")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING, format="%(levelname)s: %(message)s")
    try:
        input_path = Path(args.input)
        if not input_path.exists():
            raise FileNotFoundError(f"Файл не найден: {input_path}")

        if args.from_md:
            markdown = input_path.read_text(encoding=args.encoding)
            if args.markdown_output:
                Path(args.markdown_output).write_text(markdown, encoding="utf-8")
            items = parse_estimate_markdown(markdown, ParserConfig(code_regex=args.code_regex) if args.code_regex else None)
            df = items_to_dataframe(items)
            if args.output:
                export_items(items, args.output, args.format)
                print(f"Готово: {args.output}")
            else:
                print(df.to_string(index=False))
            return 0

        client = MinerUClient(api_key=args.mineru_api_key)
        result = process_document(
            str(input_path),
            mineru_client=client,
            mode=args.mineru_mode,
            output_path=args.output,
            output_format=args.format,
            markdown_output=args.markdown_output,
            code_regex=args.code_regex,
            model_version=args.model_version,
            language=args.language,
        )
        if args.output:
            print(f"Готово: {args.output}")
        else:
            print(result.dataframe.to_string(index=False))
        if result.markdown_path:
            print(f"Markdown сохранён: {result.markdown_path}")
        return 0
    except (FileNotFoundError, MinerUError, ValueError) as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

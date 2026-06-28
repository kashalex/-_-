from pathlib import Path

from estimate_extractor.parser import parse_estimate_markdown
from estimate_extractor.volume import evaluate_formula, extract_formula


def test_extracts_positions_and_skips_cost_rows():
    text = Path("tests/fixtures/sample_estimate.md").read_text(encoding="utf-8")
    items = parse_estimate_markdown(text)

    assert len(items) == 3
    assert [item.number for item in items] == ["1", "2", "3"]
    assert all("зарплата" not in item.name.lower() for item in items)
    assert items[1].quantity == 0.03
    assert items[1].note == "Объем=3 / 100"
    assert items[2].quantity == 15.5


def test_continues_multiline_name():
    text = Path("tests/fixtures/continued_name.md").read_text(encoding="utf-8")
    items = parse_estimate_markdown(text)

    assert len(items) == 2
    assert "из щебня с уплотнением" in items[0].name


def test_safe_volume_formula():
    assert extract_formula("Объем=3 / 100") == "3 / 100"
    assert evaluate_formula("(3 + 2) / 10") == 0.5

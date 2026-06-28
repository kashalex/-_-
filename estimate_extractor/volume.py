"""Volume formula parsing and safe arithmetic evaluation."""

from __future__ import annotations

import ast
import operator
import re
from typing import Optional

_VOLUME_RE = re.compile(r"(?:Объ[её]м|Volume)\s*=\s*([^|;]+)", re.IGNORECASE)
_ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


class VolumeFormulaError(ValueError):
    """Raised when a volume formula cannot be parsed safely."""


def parse_number(value: str) -> Optional[float]:
    """Parse a Russian/English formatted decimal number from text."""
    if value is None:
        return None
    text = str(value).strip().replace("\u00a0", " ")
    if not text or text in {"-", "—"}:
        return None
    text = text.replace(" ", "").replace(",", ".")
    match = re.search(r"[-+]?\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def extract_formula(text: str) -> Optional[str]:
    """Return the expression part from a line like 'Объем=3 / 100'."""
    match = _VOLUME_RE.search(text or "")
    if not match:
        return None
    expression = match.group(1).strip()
    expression = re.split(r"\s{2,}|\|", expression, maxsplit=1)[0].strip()
    return expression or None


def evaluate_formula(expression: str) -> float:
    """Safely evaluate a basic arithmetic expression without using eval()."""
    normalized = expression.replace(",", ".")
    if not re.fullmatch(r"[\d\s+\-*/().]+", normalized):
        raise VolumeFormulaError(f"Формула содержит неподдерживаемые символы: {expression}")
    try:
        tree = ast.parse(normalized, mode="eval")
    except SyntaxError as exc:
        raise VolumeFormulaError(f"Некорректная формула объёма: {expression}") from exc
    return float(_eval_node(tree.body))


def _eval_node(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    ast_num = getattr(ast, "Num", None)
    if ast_num is not None and isinstance(node, ast_num):  # pragma: no cover - old Python compatibility
        return float(node.n)
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_OPERATORS:
        return _ALLOWED_OPERATORS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_OPERATORS:
        return _ALLOWED_OPERATORS[type(node.op)](_eval_node(node.operand))
    raise VolumeFormulaError("Формула объёма содержит неподдерживаемую операцию")

"""WP-7: silent degradation is banned on data paths (conventions.md §12).

Precedents this guard exists for: lunar_context was silently null for
months (an ImportError swallowed at import time), planet.house returned
null while the house computation worked elsewhere, and two stub packages
squatted real dependency names. All three are the same defect class —
a failure indistinguishable from an honest "nothing found".

The AST scan walks the CALCULATION modules and fails CI on:
- `except …: pass` (any handler whose body is only pass/…),
- an exception handler that returns None / a bare `return`,

unless the handler either re-raises, logs AND records the degradation
explicitly (a `degraded` ledger append), or the site is listed in the
ALLOWLIST below with a written justification. The allowlist is part of
the audit trail: every entry is a reviewed decision, not an escape hatch.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

CALC_ROOTS = [
    REPO / "backend" / "services" / "astrology",
    REPO / "backend" / "services" / "lunar",
    REPO / "backend" / "services" / "dreams",
    REPO / "backend" / "services" / "strategic",
]

# path::function — reviewed sites where a swallowed exception is the
# documented contract. Keep justifications honest and short.
ALLOWLIST: dict[str, str] = {
    # Optional per-call context: failure lands in the `degraded` ledger the
    # caller passes in — the None return is paired with an explicit record.
    "dreams/service.py::_get_lunar_context": "records reason in degraded[]",
    "dreams/service.py::_compare_to_norms": "records reason in degraded[]",
    # AI narrative layer: LLM unavailability degrades to labelled template
    # prose by product design (Key Design Decisions: Fallback Logic).
    "dreams/ai/interpreter.py": "labelled product fallback (LLM tier)",
    "astrology/ai/interpreter.py": "labelled product fallback (LLM tier)",
    "astrology/interpreter.py": "labelled product fallback (LLM tier)",
    # Geocoder network retry ladder: every step logs and the final failure
    # raises to the caller; intermediate Nones feed the next provider.
    "astrology/geocoder.py": "provider chain, terminal failure raises",
}


def _allowed(rel_path: str, func_name: str | None) -> bool:
    for key in ALLOWLIST:
        if "::" in key:
            path_part, fn_part = key.split("::")
            if rel_path.endswith(path_part) and func_name == fn_part:
                return True
        elif rel_path.endswith(key):
            return True
    return False


def _handler_only_passes(handler: ast.ExceptHandler) -> bool:
    return all(isinstance(s, (ast.Pass,)) for s in handler.body) or (
        len(handler.body) == 1
        and isinstance(handler.body[0], ast.Expr)
        and isinstance(handler.body[0].value, ast.Constant)
        and handler.body[0].value.value is Ellipsis
    )


def _handler_returns_none(handler: ast.ExceptHandler) -> bool:
    """True when the handler's terminal action is `return`/`return None`
    and nothing in the body appends to a degraded ledger or re-raises."""
    body_src_flags = {"raise": False, "degraded": False}
    for node in ast.walk(handler):
        if isinstance(node, ast.Raise):
            body_src_flags["raise"] = True
        if isinstance(node, ast.Attribute) and node.attr == "append":
            value = node.value
            if isinstance(value, ast.Name) and value.id == "degraded":
                body_src_flags["degraded"] = True
    if body_src_flags["raise"] or body_src_flags["degraded"]:
        return False
    for stmt in handler.body:
        if isinstance(stmt, ast.Return):
            if stmt.value is None or (
                isinstance(stmt.value, ast.Constant) and stmt.value.value is None
            ):
                return True
    return False


def _enclosing_function(tree: ast.AST, lineno: int) -> str | None:
    best = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.lineno <= lineno <= max(
                getattr(node, "end_lineno", node.lineno), node.lineno
            ):
                if best is None or node.lineno > best[0]:
                    best = (node.lineno, node.name)
    return best[1] if best else None


def test_no_swallowed_exceptions_in_calculation_modules():
    violations = []
    for root in CALC_ROOTS:
        for path in sorted(root.rglob("*.py")):
            rel = str(path.relative_to(REPO / "backend" / "services"))
            src = path.read_text(encoding="utf-8")
            tree = ast.parse(src)
            for node in ast.walk(tree):
                if not isinstance(node, ast.ExceptHandler):
                    continue
                func = _enclosing_function(tree, node.lineno)
                if _allowed(rel, func):
                    continue
                if _handler_only_passes(node):
                    violations.append(f"{rel}:{node.lineno} ({func}): except-pass")
                elif _handler_returns_none(node):
                    violations.append(
                        f"{rel}:{node.lineno} ({func}): swallows exception, returns None "
                        "without raise/degraded-record"
                    )
    assert not violations, (
        "Silent degradation on data paths (conventions.md §12). Fix the "
        "handler (raise, or record in the degraded ledger) or add a "
        "justified ALLOWLIST entry:\n" + "\n".join(violations)
    )

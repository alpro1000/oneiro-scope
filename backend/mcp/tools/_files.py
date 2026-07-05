"""Shared safe file-output helpers for MCP tools that write reports.

Hardened across PR #136–#139 bot reviews: path confinement (CWE-22),
anchor-root exclusion, project-root anchoring of relative paths,
collision-proof default names. Any MCP tool that writes a file MUST go
through these helpers — the MCP server can run as a remote HTTP
endpoint, so caller-supplied paths are a security boundary.
"""

from __future__ import annotations

import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional


def _safe_roots(*candidates: Path) -> tuple[Path, ...]:
    """Drop any candidate that IS a filesystem anchor: if a root
    resolves to '/', is_relative_to() passes for everything and the
    confinement silently dies (deployment with cwd='/')."""
    return tuple(p for p in candidates if p != Path(p.anchor))


# Project root from code location, NOT runtime cwd — cwd is
# deployment-dependent and may be '/'.
_PROJECT_ROOT = Path(__file__).resolve().parents[3]

# Report files may only land under these roots.
_ALLOWED_REPORT_ROOTS = _safe_roots(
    Path(tempfile.gettempdir()).resolve(),
    _PROJECT_ROOT,
)

# Reading user-supplied local files (photos) is likewise confined; home
# covers the local-desktop use case (files in ~/...).
_ALLOWED_READ_ROOTS = _safe_roots(
    Path.home().resolve(),
    Path(tempfile.gettempdir()).resolve(),
    _PROJECT_ROOT,
)


def _resolve_user_path(raw: str) -> Path:
    """Relative paths are anchored to the PROJECT root, not runtime cwd:
    'report.html' must mean the same thing regardless of start dir."""
    p = Path(raw)
    return (p if p.is_absolute() else _PROJECT_ROOT / p).resolve()


def _safe_report_path(output_path: Optional[str], prefix: str) -> Path:
    """Validated output location for a report file.

    None/"" → unique file in the system temp dir. Anything else must
    resolve under an allowed root and must not be a directory.
    """
    if not output_path:
        # %f + uuid suffix: concurrent calls must never collide.
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        name = f"{prefix}_{stamp}_{uuid.uuid4().hex[:8]}.html"
        return Path(tempfile.gettempdir()) / name
    path = _resolve_user_path(output_path)
    if not any(path.is_relative_to(root) for root in _ALLOWED_REPORT_ROOTS):
        allowed = ", ".join(str(r) for r in _ALLOWED_REPORT_ROOTS)
        raise ValueError(
            f"output_path must stay under: {allowed} (got {path})"
        )
    if path.is_dir():
        raise ValueError(f"output_path is a directory: {path}")
    return path


def _safe_read_path(raw: str, what: str = "path") -> Path:
    """Validated location for reading a user-supplied local file."""
    resolved = _resolve_user_path(raw)
    if not any(resolved.is_relative_to(r) for r in _ALLOWED_READ_ROOTS):
        raise ValueError(
            f"{what} must stay under the home, temp or project directory"
        )
    return resolved


def write_report(html: str, output_path: Optional[str], prefix: str) -> Path:
    path = _safe_report_path(output_path, prefix)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    return path

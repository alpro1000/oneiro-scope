"""MCP Apps — interactive views the chat host renders next to the answer.

Implements the server half of the `io.modelcontextprotocol/ui` extension
(ext-apps specification 2026-01-26, folded into the extensions framework of the
2026-07-28 MCP specification):

- a **UI resource** under the reserved `ui://` scheme, whose body is a
  self-contained HTML document with mime type `text/html;profile=mcp-app`;
- a **tool** that points at it through `_meta.ui.resourceUri`.

The host fetches the resource, renders it in a sandboxed iframe, and speaks
JSON-RPC to it over `postMessage`. Hosts that do not implement the extension
ignore the metadata and get exactly the response they got before — which is
why this is additive and needs no capability gate to stay safe.

**Why these views need no permissions at all.** Everything a view draws is
derived from the `chart_core` the host already handed it, locally, by
`packages/chart-kit`. No fetch, no XHR, no WebSocket, no external font or
image. So no `csp` block is declared, the host applies its default
`default-src 'none'; connect-src 'none'`, and there is no domain for it to
warn the user about. A view that cannot open a socket cannot leak a birth
time even if its code were tampered with — a property worth more than a
webfont, which is why the Google Fonts import is stripped at build time.

The HTML is built by `packages/mcp-app` and committed under `dist/`, because
the backend deploys with pip and no Node step. `npm run check` in that package
fails when the committed file drifts from its source; CI runs it.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("oneiro.mcp.apps")

# Reserved by the specification for UI resources.
UI_SCHEME = "ui://"
# The mime type hosts match on to know this resource is an app, not a document.
UI_MIME = "text/html;profile=mcp-app"
# Extension identifier, reserved by the specification.
UI_EXTENSION = "io.modelcontextprotocol/ui"

_DIST = Path(__file__).resolve().parent / "dist"


class View:
    """One renderable view: a `ui://` URI and the HTML behind it."""

    def __init__(self, slug: str, filename: str, title: str, description: str):
        self.slug = slug
        self.uri = f"{UI_SCHEME}oneiroscope/{slug}"
        self.title = title
        self.description = description
        self._path = _DIST / filename

    def html(self) -> str:
        """The view's document.

        Raises rather than serving a placeholder: a host that asked for a view
        and got an empty page has no way to tell that apart from a broken app,
        and conventions.md §12 forbids the silent degradation.
        """
        try:
            return self._path.read_text(encoding="utf-8")
        except OSError as exc:
            raise RuntimeError(
                f"MCP App bundle missing: {self._path}. Run `npm run build` in "
                f"packages/mcp-app and commit the result."
            ) from exc

    def exists(self) -> bool:
        return self._path.is_file()


NATAL_WHEEL = View(
    slug="natal-wheel",
    filename="natal-wheel.html",
    title="Natal wheel",
    description=(
        "Interactive natal wheel: positions to the arcminute, aspects with orb "
        "and applying/separating, house cusps, and the timezone actually "
        "applied. Rendered from the chart payload with no further network."
    ),
)

ACG_MAP = View(
    slug="acg-map",
    filename="acg-map.html",
    title="Astrocartography",
    description=(
        "World map of the astrocartography line set — MC/IC meridians and "
        "Asc/Desc horizon curves per planet, with the birth place marked. "
        "Drawn from the GeoJSON the tool returned."
    ),
)

LUNAR_MONTH = View(
    slug="lunar-month",
    filename="lunar-month.html",
    title="Lunar calendar",
    description=(
        "Grid of lunar days over the requested period: day number, drawn phase, "
        "illumination as a figure, Moon sign, and when the lunar day begins."
    ),
)

DREAM_EVIDENCE = View(
    slug="dream-evidence",
    filename="dream-evidence.html",
    title="Dream coding",
    description=(
        "Hall/Van de Castle coding with its evidence: the dream text with every "
        "coded clause marked, and a ledger tying each count back to the phrase "
        "it came from. Model prose, if any, is shown last and labelled."
    ),
)

VIEWS: tuple[View, ...] = (NATAL_WHEEL, ACG_MAP, LUNAR_MONTH, DREAM_EVIDENCE)


def tool_ui_meta(view: View, *, visibility: list[str] | None = None) -> dict[str, Any]:
    """The `_meta` a tool carries to declare its view.

    `visibility` defaults to the specification's own default — the tool stays
    callable by the model AND by the app. Restricting it to `["app"]` would
    hide the tool from the model entirely, which is wrong for every tool here:
    the chart is useful as data even where no view is rendered.
    """
    ui: dict[str, Any] = {"resourceUri": view.uri}
    if visibility is not None:
        ui["visibility"] = visibility
    return {"ui": ui}


def register(mcp: Any) -> int:
    """Register every built view as a `ui://` resource. Returns how many.

    Never fatal. A missing bundle skips that view and logs it — the tools
    themselves keep working and simply render as text, which is exactly the
    degradation a host without the extension already gets.
    """
    registered = 0
    for view in VIEWS:
        if not view.exists():
            logger.warning(
                "MCP App view %s has no built bundle — skipping (run "
                "`npm run build` in packages/mcp-app)", view.slug,
            )
            continue

        def _make(v: View):
            # Bound per view: a late-binding closure would serve the last
            # view's HTML under every URI.
            def _read() -> str:
                return v.html()
            _read.__name__ = f"ui_{v.slug.replace('-', '_')}"
            _read.__doc__ = v.description
            return _read

        mcp.resource(
            view.uri,
            name=view.slug,
            title=view.title,
            description=view.description,
            mime_type=UI_MIME,
        )(_make(view))
        registered += 1

    logger.info("MCP Apps: %d view(s) registered", registered)
    return registered

"""Shared test fixtures.

Isolation for process-global state that the app keeps between requests. A test
suite is one "client" to anything keyed by IP, so without this the tests
interfere with each other in an order-dependent way — the symptom is a 429 in
whichever test happens to run past the limit, which moves as tests are added.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Give every test a fresh rate-limit budget.

    `RateLimitMiddleware` counts requests per client IP in a process-global
    dict, and under `TestClient` every request in the suite shares one IP. The
    counter is real behaviour worth keeping in production, but between tests it
    is just shared state.
    """
    try:
        from backend.app.main import api_app
    except Exception:  # app not importable in this environment — nothing to do
        yield
        return

    # Starlette instantiates middleware lazily inside the built stack, so walk
    # it to reach the live object holding the counters.
    node = getattr(api_app, "middleware_stack", None)
    for _ in range(20):
        if node is None:
            break
        if type(node).__name__ == "RateLimitMiddleware":
            node.rate_limits.clear()
            break
        node = getattr(node, "app", None)

    yield

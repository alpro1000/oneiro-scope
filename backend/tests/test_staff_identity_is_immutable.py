"""Staff status is matched on an identity the account cannot change.

`is_staff` compares `STAFF_ACCOUNTS` against `user.email` and
`user.oauth_subject`. That is only safe while a user cannot edit either. Today
they cannot: `email` is written once, at registration, and no endpoint updates
it — verified below by walking the source rather than by remembering.

The risk is latent rather than present, which is exactly why it needs a test.
The day someone adds an ordinary "change your email" form — a feature no
reviewer would question — every account gains a path to staff privileges by
typing the owner's address, and nothing anywhere would fail. Staff resolve to
PRO in `current_tier`, so the blast radius is the paywall and the funnel
report, not just a flag.

Two ways out when that day comes, both fine, neither automatic:
  - match `oauth_subject` only (it comes from the identity provider), or
  - match a verified claim (`email` with `email_verified`), never a profile
    column the account owns.
This test exists to make sure the choice is made deliberately at that moment,
instead of the guarantee quietly evaporating.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]


def _assignments_to(attribute: str) -> list[str]:
    """Every `<something>.<attribute> = ...` in backend source, as 'file:line'."""
    hits: list[str] = []
    for path in (REPO / "backend").rglob("*.py"):
        if "tests" in path.parts:
            continue
        try:
            tree = ast.parse(path.read_text())
        except SyntaxError:  # pragma: no cover - not our problem here
            continue
        for node in ast.walk(tree):
            targets = []
            if isinstance(node, ast.Assign):
                targets = node.targets
            elif isinstance(node, (ast.AugAssign, ast.AnnAssign)):
                targets = [node.target]
            for target in targets:
                if isinstance(target, ast.Attribute) and target.attr == attribute:
                    hits.append(f"{path.relative_to(REPO)}:{node.lineno}")
    return sorted(hits)


def test_nothing_reassigns_a_user_email():
    """The property `is_staff` silently depends on."""
    hits = _assignments_to("email")
    assert not hits, (
        "something now assigns `.email` on an object: "
        f"{hits}. If that is a User, staff matching by email became "
        "user-controlled — switch `is_staff` to `oauth_subject` or a verified "
        "claim before shipping it. See this file's docstring."
    )


def test_nothing_reassigns_an_oauth_subject():
    """The other half of the same match. `oauth_subject` comes from the
    identity provider; a code path that sets it from a request body would be
    the same escalation by a different door."""
    hits = _assignments_to("oauth_subject")
    assert not hits, f"`.oauth_subject` is assigned at: {hits}"


def test_staff_matching_reads_only_those_two_fields():
    """If the match ever widens to a field the user does edit — a display
    name, a company, anything from a profile form — the guarantee above stops
    covering it."""
    import inspect

    from backend.services.billing import quotas

    source = inspect.getsource(quotas.is_staff)
    assert '("email", "oauth_subject")' in source, (
        "is_staff no longer matches exactly email + oauth_subject; re-check "
        "that every field it reads is server-controlled"
    )


def test_an_empty_allowlist_grants_nothing():
    """The default must be closed: an unset `STAFF_ACCOUNTS` cannot make
    everyone staff, and an empty string must not match an empty field."""
    from types import SimpleNamespace

    from backend.core import config
    from backend.services.billing.quotas import is_staff, staff_identities

    original = getattr(config.settings, "STAFF_ACCOUNTS", "")
    try:
        config.settings.STAFF_ACCOUNTS = ""
        assert staff_identities() == frozenset()
        assert is_staff(SimpleNamespace(email="", oauth_subject=None)) is False
        assert is_staff(SimpleNamespace(email="a@b.c", oauth_subject=None)) is False

        # And a list of separators only must not produce an empty-string entry
        # that then matches an account with no email.
        config.settings.STAFF_ACCOUNTS = " , ,, "
        assert staff_identities() == frozenset()
        assert is_staff(SimpleNamespace(email=None, oauth_subject="")) is False
    finally:
        config.settings.STAFF_ACCOUNTS = original


def test_the_allowlist_is_a_deployment_artefact_not_a_role():
    """Recorded, not enforced: `STAFF_ACCOUNTS` lives in an environment
    variable, so adding a colleague needs a redeploy and removing one who left
    is invisible to code review. That is acceptable for one operator and stops
    being acceptable the moment there are several — at which point it belongs
    in a database role. Nothing else should be built on top of it meanwhile.
    """
    from backend.core.config import Settings

    assert "STAFF_ACCOUNTS" in Settings.model_fields, (
        "if staff moved out of settings, delete this test and its note in "
        "next-session.md rather than leaving both to rot"
    )

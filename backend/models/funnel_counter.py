"""Funnel counters — the only analytics this product has, by design.

The owner's constraint, and the reason this file looks the way it does: the
privacy policy says nothing is stored by default. That is an obligation, not
marketing copy, and four conversion numbers are not worth breaking it. So
what is stored is a COUNT, and nothing that could name, follow or re-identify
the person it counted:

- no user id, no session id, no device id, no cookie;
- no IP address (the endpoint never reads one, and nothing here has a column
  that could hold one);
- no timestamps finer than a calendar day;
- no third party — the row lives in this service's own Postgres, and the
  browser talks only to this service's own origin.

A row is `(event, day) → two integers`. That is the entire schema, and it is
the entire privacy story: from a row you can learn "on 3 August, 41 people
saw a face reading and 12 of them had been here before", and nothing else.
There is no join that recovers a person, because no column refers to one.

`returning` is counted without identifying anybody: the browser keeps its own
"I was here on day X" note in localStorage, compares it locally, and sends a
single boolean. The server never learns which visitor, only how many.
"""

from sqlalchemy import BigInteger, Column, Date, DateTime, String
from sqlalchemy.sql import func

from backend.core.database import Base


class FunnelCounter(Base):
    """One event, one day, two tallies.

    Per-day rather than a single running total because the question the owner
    actually needs answered a month from now is "did the funnel stop working
    or did the traffic stop", and one cumulative number cannot tell those
    apart.
    """

    __tablename__ = "funnel_counters"

    #: Event name, from `backend.services.metrics.funnel.FUNNEL_EVENTS`.
    #: A closed list — the endpoint refuses anything else rather than
    #: creating a row, so a typo or an injected string cannot grow the table.
    event = Column(String(40), primary_key=True)

    #: UTC calendar day. The coarsest useful bucket; deliberately not a
    #: timestamp, which would start to describe individual visits.
    day = Column(Date, primary_key=True)

    #: Times the event happened at all.
    total = Column(BigInteger, nullable=False, server_default="0")

    #: Of those, how many came from a browser that had been here on an
    #: earlier day. Self-reported by the browser; see the module docstring.
    #: Named `returning_count`, not `returning`: RETURNING is a reserved SQL
    #: word and the bare name fails at CREATE TABLE on SQLite and Postgres
    #: alike — caught by a test before it could break a production migration.
    returning_count = Column(BigInteger, nullable=False, server_default="0")

    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(),
        onupdate=func.now(), nullable=False,
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<FunnelCounter({self.event} {self.day}: {self.total})>"

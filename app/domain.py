"""Pure business rules: application statuses and the allowed transitions between them."""

from __future__ import annotations

from enum import Enum


class Status(str, Enum):
    WISHLIST = "wishlist"
    APPLIED = "applied"
    SCREENING = "screening"
    INTERVIEW = "interview"
    OFFER = "offer"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


TRANSITIONS: dict[Status, frozenset[Status]] = {
    Status.WISHLIST: frozenset({Status.APPLIED, Status.WITHDRAWN}),
    Status.APPLIED: frozenset({Status.SCREENING, Status.INTERVIEW, Status.REJECTED, Status.WITHDRAWN}),
    Status.SCREENING: frozenset({Status.INTERVIEW, Status.REJECTED, Status.WITHDRAWN}),
    Status.INTERVIEW: frozenset({Status.OFFER, Status.REJECTED, Status.WITHDRAWN}),
    Status.OFFER: frozenset({Status.ACCEPTED, Status.REJECTED, Status.WITHDRAWN}),
    Status.ACCEPTED: frozenset(),
    Status.REJECTED: frozenset(),
    Status.WITHDRAWN: frozenset(),
}

# Statuses that count as the employer having responded to an application.
RESPONDED = frozenset({Status.SCREENING, Status.INTERVIEW, Status.OFFER, Status.ACCEPTED, Status.REJECTED})
INTERVIEWED = frozenset({Status.INTERVIEW, Status.OFFER, Status.ACCEPTED})


def can_transition(current: Status, new: Status) -> bool:
    return new in TRANSITIONS[current]


def allowed_next(current: Status) -> list[Status]:
    return sorted(TRANSITIONS[current], key=lambda s: s.value)

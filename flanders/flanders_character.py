"""Flanders' personality: how the character frames a task.

This module is pure text. It holds the phrasing and the coarse classification
used by the ``/flanders delegate`` command, and it deliberately knows nothing
about voices, Slack, or the filesystem.

Two things are kept apart on purpose:

* ``headline`` — what is worth saying out loud, short enough to listen to.
* ``detail``  — the fuller guidance worth reading on screen.

Mixing the two is how "---" and a bulleted checklist end up read aloud, which is
exactly the sort of thing nobody wants to hear on a Tuesday.
"""

from __future__ import annotations

from dataclasses import dataclass

# Ordered task families and the words that suggest them. Order matters: the
# first family with a matching word wins, so the more specific ones lead.
_FAMILIES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("pr", ("pull request", "pr", "review", "merge")),
    ("bug", ("bug", "fix", "repair", "error", "broken")),
    ("feature", ("feature", "implement", "code", "build")),
)

_RESPONSES: dict[str, tuple[str, str]] = {
    "feature": (
        "Okily dokily! Let me help you think through implementing that feature.",
        "We could ship this as a no-mistakes PR, or take the quicker ship path, "
        "depending on your posture preference.",
    ),
    "bug": (
        "Thank you! Bugs are quite the predicament, but fear not: I will help you "
        "work out what needs fixing.",
        "We will patch this up right proper-like, and the Lord willing, it will be good as new.",
    ),
    "pr": (
        "Praise the Lord! A pull request ready for review. Let me think through the "
        "merge posture and delivery mode.",
        "Whether we go no-mistakes or direct-PR, I will make sure the merge is shipshape.",
    ),
    "default": (
        "Okily dokily! I am your faithful task delegate, here to help you offload "
        "your godly tasks.",
        "Tell me what you are working on and I will help you think through the "
        "best way to delegate it.",
    ),
}

_DELIVERY_NOTE = (
    "I can help you classify the work as ship or scout, consider the merge posture, "
    "choose a delivery mode (no-mistakes, direct-PR, or local-only), and write a "
    "proper brief from the scaffold."
)


@dataclass(frozen=True)
class TaskResponse:
    """The spoken line and the on-screen guidance for one task."""

    headline: str
    detail: str
    family: str

    def render(self) -> str:
        """The full text for a terminal."""
        return f"{self.headline}\n\n{self.detail}\n\n---\n\n{_DELIVERY_NOTE}"


def _family_for(task_description: str) -> str:
    lowered = task_description.lower()
    for family, words in _FAMILIES:
        if any(word in lowered for word in words):
            return family
    return "default"


def task_response(task_description: str) -> TaskResponse:
    """Frame `task_description` in Flanders' voice."""
    family = _family_for(task_description)
    headline, detail = _RESPONSES[family]
    return TaskResponse(headline=headline, detail=detail, family=family)


def flanders_response(task_description: str) -> str:
    """Backwards-compatible full response text, as a single string."""
    return task_response(task_description).render()


def classify_task(task_description: str) -> str:
    """Coarse delivery-mode suggestion for a task.

    This is a hint, not a decision: the project's registry entry and the
    captain's own instruction always win.
    """
    lowered = task_description.lower()
    if any(word in lowered for word in ("safety-critical", "production", "no-mistakes")):
        return "no-mistakes"
    if any(word in lowered for word in ("quick", "fast", "direct")):
        return "direct-PR"
    return "local-only"

"""Handler registry for the Adaptive Cover pipeline.

Handlers are stored sorted by descending priority so the chain always
runs highest-priority handlers first.
"""

from __future__ import annotations

import logging
from typing import Protocol, runtime_checkable

from .types import PipelineSnapshot

_LOGGER = logging.getLogger(__name__)


@runtime_checkable
class PipelineHandler(Protocol):
    """Protocol that every pipeline handler must satisfy."""

    priority: int

    def handle(self, snapshot: PipelineSnapshot) -> PipelineSnapshot:
        """Process the snapshot and return it (possibly modified)."""
        ...


class PipelineRegistry:
    """Ordered registry of pipeline handlers.

    Usage::

        registry = PipelineRegistry()
        registry.register(SecurityHandler())
        snapshot = registry.run(snapshot)
    """

    def __init__(self) -> None:  # noqa: D107
        self._handlers: list[PipelineHandler] = []

    # ------------------------------------------------------------------ #
    # Registration                                                          #
    # ------------------------------------------------------------------ #

    def register(self, handler: PipelineHandler) -> None:
        """Add *handler* to the registry (sorted by descending priority)."""
        if not isinstance(handler, PipelineHandler):
            raise TypeError(
                f"{handler!r} does not satisfy the PipelineHandler protocol "
                "(needs a 'priority' attribute and a 'handle' method)"
            )
        self._handlers.append(handler)
        self._handlers.sort(key=lambda h: h.priority, reverse=True)
        _LOGGER.debug(
            "PipelineRegistry: registered %s (priority=%d)",
            type(handler).__name__,
            handler.priority,
        )

    def unregister(self, handler_type: type) -> None:
        """Remove all handlers of *handler_type* from the registry."""
        before = len(self._handlers)
        self._handlers = [
            h for h in self._handlers if not isinstance(h, handler_type)
        ]
        _LOGGER.debug(
            "PipelineRegistry: removed %d handler(s) of type %s",
            before - len(self._handlers),
            handler_type.__name__,
        )

    # ------------------------------------------------------------------ #
    # Execution                                                             #
    # ------------------------------------------------------------------ #

    def run(self, snapshot: PipelineSnapshot) -> PipelineSnapshot:
        """Run every registered handler in priority order.

        Each handler receives the (possibly modified) snapshot from the
        previous handler.  The final snapshot is returned.
        """
        for handler in self._handlers:
            _LOGGER.debug(
                "PipelineRegistry: running %s (priority=%d)",
                type(handler).__name__,
                handler.priority,
            )
            snapshot = handler.handle(snapshot)
            if snapshot.skip_move:
                _LOGGER.debug(
                    "PipelineRegistry: %s set skip_move=True — stopping chain",
                    type(handler).__name__,
                )
                break
        return snapshot

    # ------------------------------------------------------------------ #
    # Introspection                                                         #
    # ------------------------------------------------------------------ #

    @property
    def handlers(self) -> list[PipelineHandler]:
        """Ordered (descending priority) snapshot of registered handlers."""
        return list(self._handlers)

    def __len__(self) -> int:  # noqa: D105
        return len(self._handlers)

    def __repr__(self) -> str:  # noqa: D105
        names = ", ".join(
            f"{type(h).__name__}(p={h.priority})" for h in self._handlers
        )
        return f"PipelineRegistry([{names}])"

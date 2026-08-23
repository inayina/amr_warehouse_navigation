from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ReadyResult:
    ready: bool
    reason: str


@dataclass(frozen=True)
class NavigationResult:
    succeeded: bool
    status: str
    reason: str


class RobotExecutionContext(Protocol):
    """Vendor-neutral execution contract consumed by the haul controller."""

    def check_ready_gate(self) -> ReadyResult:
        ...

    def navigate_to_pose(self, *, simulate_failure: bool = False) -> NavigationResult:
        ...

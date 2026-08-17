from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .assignment import AssignmentStatus
from .robot_state import FleetError


class InvalidLifecycleTransitionError(FleetError):
    """Raised when a haul-task lifecycle transition is not allowed."""


class WmsTaskStatus(str, Enum):
    """Business-level WMS haul task status. Not a robot or assignment state."""

    PENDING = 'pending'
    ASSIGNED = 'assigned'
    IN_PROGRESS = 'in_progress'
    SUCCEEDED = 'succeeded'
    FAILED = 'failed'
    CANCELED = 'canceled'
    REQUEUED = 'requeued'


class HaulExecutionPhase(str, Enum):
    """Per-robot haul execution phase. Not a WMS or assignment state."""

    IDLE = 'idle'
    NAVIGATING_TO_PICKUP = 'navigating_to_pickup'
    PICKUP = 'pickup'
    NAVIGATING_TO_DROPOFF = 'navigating_to_dropoff'
    DROPOFF = 'dropoff'
    SUCCEEDED = 'succeeded'
    FAILED = 'failed'
    CANCELED = 'canceled'
    REQUEUED = 'requeued'


WMS_TASK_STATUSES = tuple(status.value for status in WmsTaskStatus)
HAUL_EXECUTION_PHASES = tuple(phase.value for phase in HaulExecutionPhase)

TERMINAL_WMS_STATUSES = frozenset(
    {
        WmsTaskStatus.SUCCEEDED,
        WmsTaskStatus.FAILED,
        WmsTaskStatus.CANCELED,
    }
)

TERMINAL_EXECUTION_PHASES = frozenset(
    {
        HaulExecutionPhase.SUCCEEDED,
        HaulExecutionPhase.FAILED,
        HaulExecutionPhase.CANCELED,
        HaulExecutionPhase.REQUEUED,
    }
)

ALLOWED_WMS_TRANSITIONS: dict[WmsTaskStatus, frozenset[WmsTaskStatus]] = {
    WmsTaskStatus.PENDING: frozenset(
        {WmsTaskStatus.ASSIGNED, WmsTaskStatus.CANCELED}
    ),
    WmsTaskStatus.ASSIGNED: frozenset(
        {
            WmsTaskStatus.IN_PROGRESS,
            WmsTaskStatus.CANCELED,
            WmsTaskStatus.REQUEUED,
            WmsTaskStatus.FAILED,
        }
    ),
    WmsTaskStatus.IN_PROGRESS: frozenset(
        {
            WmsTaskStatus.SUCCEEDED,
            WmsTaskStatus.FAILED,
            WmsTaskStatus.CANCELED,
            WmsTaskStatus.REQUEUED,
        }
    ),
    WmsTaskStatus.REQUEUED: frozenset(
        {WmsTaskStatus.ASSIGNED, WmsTaskStatus.CANCELED}
    ),
    WmsTaskStatus.SUCCEEDED: frozenset(),
    WmsTaskStatus.FAILED: frozenset(),
    WmsTaskStatus.CANCELED: frozenset(),
}

ALLOWED_EXECUTION_TRANSITIONS: dict[HaulExecutionPhase, frozenset[HaulExecutionPhase]] = {
    HaulExecutionPhase.IDLE: frozenset(
        {
            HaulExecutionPhase.NAVIGATING_TO_PICKUP,
            HaulExecutionPhase.FAILED,
            HaulExecutionPhase.CANCELED,
            HaulExecutionPhase.REQUEUED,
        }
    ),
    HaulExecutionPhase.NAVIGATING_TO_PICKUP: frozenset(
        {
            HaulExecutionPhase.PICKUP,
            HaulExecutionPhase.FAILED,
            HaulExecutionPhase.CANCELED,
            HaulExecutionPhase.REQUEUED,
        }
    ),
    HaulExecutionPhase.PICKUP: frozenset(
        {
            HaulExecutionPhase.NAVIGATING_TO_DROPOFF,
            HaulExecutionPhase.FAILED,
            HaulExecutionPhase.CANCELED,
        }
    ),
    HaulExecutionPhase.NAVIGATING_TO_DROPOFF: frozenset(
        {
            HaulExecutionPhase.DROPOFF,
            HaulExecutionPhase.FAILED,
            HaulExecutionPhase.CANCELED,
        }
    ),
    HaulExecutionPhase.DROPOFF: frozenset(
        {
            HaulExecutionPhase.SUCCEEDED,
            HaulExecutionPhase.FAILED,
            HaulExecutionPhase.CANCELED,
        }
    ),
    HaulExecutionPhase.SUCCEEDED: frozenset(),
    HaulExecutionPhase.FAILED: frozenset(),
    HaulExecutionPhase.CANCELED: frozenset(),
    HaulExecutionPhase.REQUEUED: frozenset({HaulExecutionPhase.IDLE}),
}

COARSE_MOCK_WMS_STATUS = {
    WmsTaskStatus.PENDING: 'pending',
    WmsTaskStatus.ASSIGNED: 'running',
    WmsTaskStatus.IN_PROGRESS: 'running',
    WmsTaskStatus.SUCCEEDED: 'succeeded',
    WmsTaskStatus.FAILED: 'failed',
    WmsTaskStatus.CANCELED: 'canceled',
    WmsTaskStatus.REQUEUED: 'pending',
}


def assert_wms_transition_allowed(current: WmsTaskStatus, target: WmsTaskStatus) -> None:
    allowed = ALLOWED_WMS_TRANSITIONS.get(current, frozenset())
    if target not in allowed:
        raise InvalidLifecycleTransitionError(
            f'WMS task status transition {current.value} -> {target.value} is not allowed.'
        )


def assert_execution_transition_allowed(
    current: HaulExecutionPhase,
    target: HaulExecutionPhase,
) -> None:
    allowed = ALLOWED_EXECUTION_TRANSITIONS.get(current, frozenset())
    if target not in allowed:
        raise InvalidLifecycleTransitionError(
            f'Haul execution transition {current.value} -> {target.value} is not allowed.'
        )


@dataclass(frozen=True)
class HaulTaskSnapshot:
    task_id: int
    pickup_station: str
    dropoff_station: str
    priority: str
    wms_status: WmsTaskStatus
    assignment_status: AssignmentStatus | None
    execution_phase: HaulExecutionPhase
    robot_id: str | None
    pickup_completed: bool
    reason: str | None = None

    @property
    def is_terminal(self) -> bool:
        return self.wms_status in TERMINAL_WMS_STATUSES

    @property
    def coarse_mock_wms_status(self) -> str:
        return COARSE_MOCK_WMS_STATUS[self.wms_status]

    def to_dict(self) -> dict[str, object]:
        return {
            'task_id': self.task_id,
            'pickup_station': self.pickup_station,
            'dropoff_station': self.dropoff_station,
            'priority': self.priority,
            'wms_status': self.wms_status.value,
            'assignment_status': (
                None if self.assignment_status is None else self.assignment_status.value
            ),
            'execution_phase': self.execution_phase.value,
            'robot_id': self.robot_id,
            'pickup_completed': self.pickup_completed,
            'reason': self.reason,
            'coarse_mock_wms_status': self.coarse_mock_wms_status,
        }

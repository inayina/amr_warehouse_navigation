from __future__ import annotations

from enum import Enum


class RobotState(str, Enum):
    IDLE = 'IDLE'
    ASSIGNED = 'ASSIGNED'
    BUSY = 'BUSY'
    OFFLINE = 'OFFLINE'
    ERROR = 'ERROR'


ROBOT_STATES = tuple(state.value for state in RobotState)

ACTIVE_TASK_STATES = frozenset({RobotState.ASSIGNED, RobotState.BUSY})

DISPATCHABLE_STATES = frozenset({RobotState.IDLE})

ALLOWED_TRANSITIONS: dict[RobotState, frozenset[RobotState]] = {
    RobotState.IDLE: frozenset(
        {
            RobotState.ASSIGNED,
            RobotState.OFFLINE,
            RobotState.ERROR,
        }
    ),
    RobotState.ASSIGNED: frozenset(
        {
            RobotState.BUSY,
            RobotState.IDLE,
            RobotState.OFFLINE,
            RobotState.ERROR,
        }
    ),
    RobotState.BUSY: frozenset(
        {
            RobotState.IDLE,
            RobotState.OFFLINE,
            RobotState.ERROR,
        }
    ),
    RobotState.OFFLINE: frozenset({RobotState.IDLE, RobotState.ERROR}),
    RobotState.ERROR: frozenset({RobotState.IDLE, RobotState.OFFLINE}),
}


def assert_transition_allowed(current: RobotState, target: RobotState) -> None:
    allowed = ALLOWED_TRANSITIONS.get(current, frozenset())
    if target not in allowed:
        raise InvalidRobotTransitionError(
            f'Robot state transition {current.value} -> {target.value} is not allowed.'
        )


class FleetError(Exception):
    """Base error for fleet registry operations."""


class RobotNotFoundError(FleetError):
    """Raised when a robot_id is unknown to the registry."""


class InvalidRobotTransitionError(FleetError):
    """Raised when a robot state transition violates the state machine."""


class RobotNotAvailableError(FleetError):
    """Raised when a robot cannot accept a task assignment."""


class RobotActiveTaskConflictError(FleetError):
    """Raised when a robot already holds an active task."""

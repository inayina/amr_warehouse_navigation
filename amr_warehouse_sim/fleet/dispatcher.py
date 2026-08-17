from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .assignment import (
    ACTIVE_ASSIGNMENT_STATUSES,
    AssignmentRecord,
    AssignmentStatus,
    load_assignments_from_db,
    persist_assignment,
)
from .registry import RobotRegistry, now_timestamp
from .robot_state import FleetError
from .stations import StationNotFoundError, static_station_distance


class DispatcherError(FleetError):
    """Base error for fleet dispatcher operations."""


class TaskAlreadyAssignedError(DispatcherError):
    """Raised when a task already has an active fleet assignment."""


class NoAvailableRobotError(DispatcherError):
    """Raised when no robot can accept a task."""


TASK_PRIORITIES = ('normal', 'high')
PRIORITY_ORDER = {'high': 0, 'normal': 1}


@dataclass(frozen=True)
class DispatchTask:
    """Fleet view of a pending WMS task."""

    task_id: int
    pickup_station: str
    dropoff_station: str | None = None
    priority: str = 'normal'

    def __post_init__(self) -> None:
        if self.priority not in TASK_PRIORITIES:
            raise ValueError(
                f'Unsupported task priority {self.priority!r}. '
                f'Allowed values: {", ".join(TASK_PRIORITIES)}.'
            )


@dataclass(frozen=True)
class DispatchCandidate:
    robot_id: str
    cost: float
    dispatch_reason: str


@dataclass(frozen=True)
class DispatchDecision:
    task_id: int
    robot_id: str
    pickup_station: str
    cost: float
    dispatch_reason: str


@dataclass(frozen=True)
class FleetEvent:
    timestamp: str
    event: str
    task_id: int | None = None
    robot_id: str | None = None
    reason: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            'timestamp': self.timestamp,
            'event': self.event,
            'task_id': self.task_id,
            'robot_id': self.robot_id,
            'reason': self.reason,
        }


def dispatch_task_from_wms_row(task: dict[str, object]) -> DispatchTask:
    raw_task_id = task.get('id')
    raw_target = task.get('target_name')
    if not isinstance(raw_task_id, int):
        raise ValueError('WMS task field "id" must be an integer.')
    if not isinstance(raw_target, str) or not raw_target.strip():
        raise ValueError('WMS task field "target_name" must be a non-blank string.')
    return DispatchTask(
        task_id=raw_task_id,
        pickup_station=raw_target.strip(),
        priority='normal',
    )


def compute_assignment_cost(
    *,
    robot_station: str | None,
    pickup_station: str,
    priority: str = 'normal',
    workload_penalty: float = 0.0,
    task_points_path: Path | None = None,
) -> tuple[float, str]:
    distance = static_station_distance(
        robot_station,
        pickup_station,
        task_points_path=task_points_path,
    )
    priority_penalty = 0.0
    if priority == 'high':
        priority_penalty = -0.5

    cost = distance + workload_penalty + priority_penalty
    reason = (
        f'distance={distance:.3f} from {robot_station} to {pickup_station}; '
        f'workload_penalty={workload_penalty:.3f}; '
        f'priority_penalty={priority_penalty:.3f}'
    )
    return cost, reason


class FleetDispatcher:
    """Minimal fleet task assigner over RobotRegistry."""

    def __init__(
        self,
        registry: RobotRegistry,
        *,
        db_path: Path | None = None,
        task_points_path: Path | None = None,
        event_sink: list[FleetEvent] | None = None,
    ):
        self.registry = registry
        self._db_path = Path(db_path) if db_path is not None else registry.db_path
        self._task_points_path = Path(task_points_path) if task_points_path is not None else None
        self._event_sink = event_sink if event_sink is not None else []

        if self._db_path is not None:
            self._assignments = load_assignments_from_db(self._db_path)
        else:
            self._assignments = {}

    @property
    def assignments(self) -> list[AssignmentRecord]:
        return [self._assignments[task_id] for task_id in sorted(self._assignments)]

    def get_assignment_for_task(self, task_id: int) -> AssignmentRecord | None:
        assignment = self._assignments.get(task_id)
        if assignment is None or not assignment.is_active:
            return None
        return assignment

    def get_assignment_record(self, task_id: int) -> AssignmentRecord | None:
        return self._assignments.get(task_id)

    def set_assignment_status(
        self,
        task_id: int,
        status: AssignmentStatus,
        *,
        timestamp: str | None = None,
    ) -> AssignmentRecord:
        assignment = self._assignments.get(task_id)
        if assignment is None:
            raise KeyError(f'Assignment for task {task_id} was not found.')

        updated = AssignmentRecord(
            id=assignment.id,
            task_id=assignment.task_id,
            robot_id=assignment.robot_id,
            pickup_station=assignment.pickup_station,
            cost=assignment.cost,
            dispatch_reason=assignment.dispatch_reason,
            status=status,
            assigned_at=assignment.assigned_at,
            updated_at=timestamp or now_timestamp(),
        )
        if self._db_path is not None:
            updated = persist_assignment(updated, self._db_path)
        self._assignments[task_id] = updated
        return updated

    def emit_event(
        self,
        event: str,
        *,
        task_id: int | None = None,
        robot_id: str | None = None,
        reason: str | None = None,
        timestamp: str | None = None,
    ) -> FleetEvent:
        return self._emit_event(
            event,
            task_id=task_id,
            robot_id=robot_id,
            reason=reason,
            timestamp=timestamp,
        )

    def list_active_assignments(self) -> list[AssignmentRecord]:
        return [
            assignment
            for assignment in self.assignments
            if assignment.status in ACTIVE_ASSIGNMENT_STATUSES
        ]

    def _emit_event(
        self,
        event: str,
        *,
        task_id: int | None = None,
        robot_id: str | None = None,
        reason: str | None = None,
        timestamp: str | None = None,
    ) -> FleetEvent:
        fleet_event = FleetEvent(
            timestamp=timestamp or now_timestamp(),
            event=event,
            task_id=task_id,
            robot_id=robot_id,
            reason=reason,
        )
        self._event_sink.append(fleet_event)
        print(json.dumps(fleet_event.to_dict()), file=sys.stderr)
        return fleet_event

    def list_candidates(
        self,
        task: DispatchTask,
        *,
        now: datetime,
        heartbeat_timeout_sec: float = 30.0,
        workload_penalty_by_robot: dict[str, float] | None = None,
    ) -> list[DispatchCandidate]:
        penalties = workload_penalty_by_robot or {}
        candidates: list[DispatchCandidate] = []

        for robot in self.registry.list_robots():
            if not self.registry.can_accept_task(
                robot.robot_id,
                now=now,
                heartbeat_timeout_sec=heartbeat_timeout_sec,
            ):
                continue

            try:
                cost, reason = compute_assignment_cost(
                    robot_station=robot.current_station,
                    pickup_station=task.pickup_station,
                    priority=task.priority,
                    workload_penalty=penalties.get(robot.robot_id, 0.0),
                    task_points_path=self._task_points_path,
                )
            except StationNotFoundError:
                continue

            candidates.append(
                DispatchCandidate(
                    robot_id=robot.robot_id,
                    cost=cost,
                    dispatch_reason=reason,
                )
            )

        candidates.sort(key=lambda candidate: (candidate.cost, candidate.robot_id))
        return candidates

    def select_robot(
        self,
        task: DispatchTask,
        *,
        now: datetime,
        heartbeat_timeout_sec: float = 30.0,
        workload_penalty_by_robot: dict[str, float] | None = None,
    ) -> DispatchDecision | None:
        candidates = self.list_candidates(
            task,
            now=now,
            heartbeat_timeout_sec=heartbeat_timeout_sec,
            workload_penalty_by_robot=workload_penalty_by_robot,
        )
        if not candidates:
            return None

        best = candidates[0]
        return DispatchDecision(
            task_id=task.task_id,
            robot_id=best.robot_id,
            pickup_station=task.pickup_station,
            cost=best.cost,
            dispatch_reason=best.dispatch_reason,
        )

    def assign_task(
        self,
        task: DispatchTask,
        *,
        now: datetime,
        heartbeat_timeout_sec: float = 30.0,
        workload_penalty_by_robot: dict[str, float] | None = None,
    ) -> AssignmentRecord:
        existing = self.get_assignment_for_task(task.task_id)
        if existing is not None:
            raise TaskAlreadyAssignedError(
                f'Task {task.task_id} is already assigned to robot {existing.robot_id}.'
            )

        decision = self.select_robot(
            task,
            now=now,
            heartbeat_timeout_sec=heartbeat_timeout_sec,
            workload_penalty_by_robot=workload_penalty_by_robot,
        )
        if decision is None:
            raise NoAvailableRobotError(
                f'No available robot can accept task {task.task_id} '
                f'to {task.pickup_station}.'
            )

        self.registry.assign_task(decision.robot_id, task.task_id)
        timestamp = now.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace(
            '+00:00', 'Z'
        )
        assignment = AssignmentRecord(
            id=0,
            task_id=task.task_id,
            robot_id=decision.robot_id,
            pickup_station=task.pickup_station,
            cost=decision.cost,
            dispatch_reason=decision.dispatch_reason,
            status=AssignmentStatus.ASSIGNED,
            assigned_at=timestamp,
            updated_at=timestamp,
        )

        if self._db_path is not None:
            assignment = persist_assignment(assignment, self._db_path)

        self._assignments[task.task_id] = assignment
        self._emit_event(
            'TASK_ASSIGNED',
            task_id=task.task_id,
            robot_id=decision.robot_id,
            reason=decision.dispatch_reason,
            timestamp=timestamp,
        )
        return assignment

    def dispatch_tasks(
        self,
        tasks: Iterable[DispatchTask],
        *,
        now: datetime,
        heartbeat_timeout_sec: float = 30.0,
        workload_penalty_by_robot: dict[str, float] | None = None,
    ) -> list[AssignmentRecord]:
        ordered_tasks = sorted(
            tasks,
            key=lambda task: (PRIORITY_ORDER[task.priority], task.task_id),
        )
        results: list[AssignmentRecord] = []

        for task in ordered_tasks:
            if self.get_assignment_for_task(task.task_id) is not None:
                continue
            try:
                results.append(
                    self.assign_task(
                        task,
                        now=now,
                        heartbeat_timeout_sec=heartbeat_timeout_sec,
                        workload_penalty_by_robot=workload_penalty_by_robot,
                    )
                )
            except NoAvailableRobotError:
                break

        return results

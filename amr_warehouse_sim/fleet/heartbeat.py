from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping

from .dispatcher import FleetDispatcher
from .haul_executor import HaulTaskController
from .registry import DEFAULT_HEARTBEAT_TIMEOUT_SEC, RobotRegistry, is_heartbeat_valid
from .robot_state import RobotState
from .task_lifecycle import HaulTaskSnapshot, WmsTaskStatus


@dataclass(frozen=True)
class HeartbeatSweepItem:
    robot_id: str
    timed_out: bool
    went_offline: bool
    requeued_task_id: int | None
    reassignment_blocked: bool
    reason: str


class HeartbeatMonitor:
    """Mark stale robots OFFLINE and requeue tasks that are still reversible."""

    def __init__(self, dispatcher: FleetDispatcher):
        self.dispatcher = dispatcher
        self.registry: RobotRegistry = dispatcher.registry

    def sweep(
        self,
        *,
        now: datetime,
        timeout_sec: float = DEFAULT_HEARTBEAT_TIMEOUT_SEC,
        haul_tasks: Mapping[int, HaulTaskController] | None = None,
    ) -> list[HeartbeatSweepItem]:
        hauls = haul_tasks or {}
        results: list[HeartbeatSweepItem] = []

        for robot in self.registry.list_robots():
            if robot.state == RobotState.OFFLINE:
                continue
            if is_heartbeat_valid(robot, now=now, timeout_sec=timeout_sec):
                continue

            timeout_reason = (
                f'Heartbeat timeout after {timeout_sec:.1f}s; '
                f'last_heartbeat={robot.last_heartbeat}.'
            )
            self.dispatcher.emit_event(
                'HEARTBEAT_TIMEOUT',
                robot_id=robot.robot_id,
                task_id=robot.current_task_id,
                reason=timeout_reason,
            )

            requeued_task_id = None
            reassignment_blocked = False
            haul = hauls.get(robot.current_task_id) if robot.current_task_id is not None else None

            if haul is not None and not haul.snapshot.pickup_completed:
                haul.requeue(timeout_reason)
                requeued_task_id = haul.snapshot.task_id
            elif haul is not None and haul.snapshot.pickup_completed:
                reassignment_blocked = True

            self.registry.mark_offline(robot.robot_id)
            offline_reason = timeout_reason
            if reassignment_blocked:
                offline_reason = (
                    f'{timeout_reason} Task {robot.current_task_id} is past pickup; '
                    'demo-level reassignment is blocked.'
                )
            self.dispatcher.emit_event(
                'ROBOT_OFFLINE',
                robot_id=robot.robot_id,
                task_id=requeued_task_id or robot.current_task_id,
                reason=offline_reason,
            )

            results.append(
                HeartbeatSweepItem(
                    robot_id=robot.robot_id,
                    timed_out=True,
                    went_offline=True,
                    requeued_task_id=requeued_task_id,
                    reassignment_blocked=reassignment_blocked,
                    reason=offline_reason,
                )
            )

        return results

    def reassign_requeued(
        self,
        haul_tasks: Mapping[int, HaulTaskController],
        *,
        now: datetime,
        timeout_sec: float = DEFAULT_HEARTBEAT_TIMEOUT_SEC,
    ) -> list[HaulTaskSnapshot]:
        reassigned: list[HaulTaskSnapshot] = []
        for haul in haul_tasks.values():
            if haul.snapshot.wms_status != WmsTaskStatus.REQUEUED:
                continue
            reassigned.append(
                haul.assign(now=now, heartbeat_timeout_sec=timeout_sec)
            )
        return reassigned

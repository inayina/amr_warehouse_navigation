from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .registry import RobotRegistry
from .robot_state import RobotState


@dataclass(frozen=True)
class SimulatedReadyResult:
    ready: bool
    reason: str


@dataclass(frozen=True)
class SimulatedNavigationResult:
    succeeded: bool
    status: str
    reason: str


class SimulatedRobotContext:
    """Per-robot execution context for fleet-layer tests without Nav2."""

    def __init__(self, robot_id: str, registry: RobotRegistry):
        self.robot_id = robot_id
        self.registry = registry

    def check_ready_gate(self) -> SimulatedReadyResult:
        robot = self.registry.get_robot(self.robot_id)
        if robot.state == RobotState.OFFLINE:
            return SimulatedReadyResult(
                ready=False,
                reason=f'{self.robot_id} is OFFLINE.',
            )
        if robot.state == RobotState.ERROR:
            return SimulatedReadyResult(
                ready=False,
                reason=f'{self.robot_id} is in ERROR.',
            )
        if robot.current_task_id is None:
            return SimulatedReadyResult(
                ready=False,
                reason=f'{self.robot_id} has no assigned task.',
            )
        if robot.state not in {RobotState.ASSIGNED, RobotState.BUSY}:
            return SimulatedReadyResult(
                ready=False,
                reason=f'{self.robot_id} state is {robot.state.value}.',
            )
        return SimulatedReadyResult(
            ready=True,
            reason='simulated ready gate satisfied',
        )

    def navigate_to_pose(self, *, simulate_failure: bool = False) -> SimulatedNavigationResult:
        ready = self.check_ready_gate()
        if not ready.ready:
            return SimulatedNavigationResult(
                succeeded=False,
                status='failed',
                reason=ready.reason,
            )

        robot = self.registry.get_robot(self.robot_id)
        if robot.state == RobotState.ASSIGNED:
            self.registry.mark_busy(self.robot_id)

        if simulate_failure:
            return SimulatedNavigationResult(
                succeeded=False,
                status='failed',
                reason='simulated navigation failure',
            )

        return SimulatedNavigationResult(
            succeeded=True,
            status='succeeded',
            reason='simulated NavigateToPose SUCCEEDED',
        )

    def complete_assigned_task(self) -> None:
        robot = self.registry.get_robot(self.robot_id)
        if robot.state in {RobotState.ASSIGNED, RobotState.BUSY}:
            self.registry.release_task(self.robot_id)


class SimulatedExecutorRuntime(Protocol):
    def check_ready_gate(self) -> SimulatedReadyResult:
        ...

    def navigate_to_pose(self, *, simulate_failure: bool = False) -> SimulatedNavigationResult:
        ...

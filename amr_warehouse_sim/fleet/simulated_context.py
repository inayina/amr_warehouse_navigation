from __future__ import annotations

from .execution_context import NavigationResult, ReadyResult, RobotExecutionContext
from .registry import RobotRegistry
from .robot_state import RobotState

# Backward-compatible names for callers that imported the Stage 1-5 result types.
SimulatedReadyResult = ReadyResult
SimulatedNavigationResult = NavigationResult


class SimulatedRobotContext:
    """Per-robot execution context for fleet-layer tests without Nav2."""

    def __init__(self, robot_id: str, registry: RobotRegistry):
        self.robot_id = robot_id
        self.registry = registry

    def check_ready_gate(self) -> ReadyResult:
        robot = self.registry.get_robot(self.robot_id)
        if robot.state == RobotState.OFFLINE:
            return ReadyResult(
                ready=False,
                reason=f'{self.robot_id} is OFFLINE.',
            )
        if robot.state == RobotState.ERROR:
            return ReadyResult(
                ready=False,
                reason=f'{self.robot_id} is in ERROR.',
            )
        if robot.current_task_id is None:
            return ReadyResult(
                ready=False,
                reason=f'{self.robot_id} has no assigned task.',
            )
        if robot.state not in {RobotState.ASSIGNED, RobotState.BUSY}:
            return ReadyResult(
                ready=False,
                reason=f'{self.robot_id} state is {robot.state.value}.',
            )
        return ReadyResult(
            ready=True,
            reason='simulated ready gate satisfied',
        )

    def navigate_to_pose(self, *, simulate_failure: bool = False) -> NavigationResult:
        ready = self.check_ready_gate()
        if not ready.ready:
            return NavigationResult(
                succeeded=False,
                status='failed',
                reason=ready.reason,
            )

        robot = self.registry.get_robot(self.robot_id)
        if robot.state == RobotState.ASSIGNED:
            self.registry.mark_busy(self.robot_id)

        if simulate_failure:
            return NavigationResult(
                succeeded=False,
                status='failed',
                reason='simulated navigation failure',
            )

        return NavigationResult(
            succeeded=True,
            status='succeeded',
            reason='simulated NavigateToPose SUCCEEDED',
        )

    def complete_assigned_task(self) -> None:
        robot = self.registry.get_robot(self.robot_id)
        if robot.state in {RobotState.ASSIGNED, RobotState.BUSY}:
            self.registry.release_task(self.robot_id)
# Backward-compatible Protocol alias; new code should use RobotExecutionContext.
SimulatedExecutorRuntime = RobotExecutionContext

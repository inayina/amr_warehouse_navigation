from datetime import datetime, timezone

from amr_warehouse_sim.fleet import (
    FleetDispatcher,
    HaulTaskController,
    NavigationResult,
    ReadyResult,
    RobotRegistry,
    seed_default_robots,
)


FIXED_NOW = datetime(2026, 8, 23, 9, 0, 0, tzinfo=timezone.utc)
FIXED_HEARTBEAT = '2026-08-23T09:00:00Z'


class FakeRobotExecutionContext:
    def __init__(self):
        self.ready_checks = 0
        self.navigation_calls = 0

    def check_ready_gate(self) -> ReadyResult:
        self.ready_checks += 1
        return ReadyResult(ready=True, reason='fake context ready')

    def navigate_to_pose(self, *, simulate_failure: bool = False) -> NavigationResult:
        self.navigation_calls += 1
        return NavigationResult(
            succeeded=not simulate_failure,
            status='failed' if simulate_failure else 'succeeded',
            reason='fake navigation result',
        )


def test_haul_controller_accepts_vendor_neutral_execution_context(repo_root):
    registry = RobotRegistry(robots=seed_default_robots(timestamp=FIXED_HEARTBEAT))
    dispatcher = FleetDispatcher(
        registry,
        task_points_path=repo_root / 'config' / 'task_points.yaml',
        event_sink=[],
    )
    fake_context = FakeRobotExecutionContext()
    controller = HaulTaskController(
        task_id=701,
        pickup_station='station_a',
        dropoff_station='station_b',
        dispatcher=dispatcher,
        contexts={'robot_01': fake_context},
    )

    assigned = controller.assign(now=FIXED_NOW)
    assert assigned.robot_id == 'robot_01'
    controller.start()
    at_pickup = controller.complete_navigation_to_pickup()

    assert at_pickup.robot_id == 'robot_01'
    assert fake_context.navigation_calls == 1
    assert controller._context_for('robot_01') is fake_context


def test_injected_execution_context_failure_keeps_existing_failure_semantics(repo_root):
    registry = RobotRegistry(robots=seed_default_robots(timestamp=FIXED_HEARTBEAT))
    dispatcher = FleetDispatcher(
        registry,
        task_points_path=repo_root / 'config' / 'task_points.yaml',
        event_sink=[],
    )
    fake_context = FakeRobotExecutionContext()
    controller = HaulTaskController(
        task_id=702,
        pickup_station='station_a',
        dropoff_station='station_b',
        dispatcher=dispatcher,
        contexts={'robot_01': fake_context},
    )

    controller.assign(now=FIXED_NOW)
    controller.start()
    failed = controller.complete_navigation_to_pickup(simulate_failure=True)

    assert failed.is_terminal
    assert failed.reason == 'fake navigation result'
    assert fake_context.navigation_calls == 1

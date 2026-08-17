from datetime import datetime, timezone

import pytest

from amr_warehouse_sim.fleet import (
    AssignmentStatus,
    DispatchTask,
    FleetDispatcher,
    NoAvailableRobotError,
    RobotRegistry,
    RobotState,
    TaskAlreadyAssignedError,
    build_default_robot,
    seed_default_robots,
)


FIXED_NOW = datetime(2026, 8, 17, 9, 0, 0, tzinfo=timezone.utc)
FIXED_HEARTBEAT = '2026-08-17T09:00:00Z'


def _registry_with_two_idle_robots() -> RobotRegistry:
    robots = seed_default_robots(timestamp=FIXED_HEARTBEAT)
    return RobotRegistry(robots=robots)


def _dispatcher(
    registry: RobotRegistry | None = None,
    *,
    repo_root=None,
    db_path=None,
) -> FleetDispatcher:
    registry = registry or _registry_with_two_idle_robots()
    task_points_path = repo_root / 'config' / 'task_points.yaml' if repo_root else None
    return FleetDispatcher(
        registry,
        db_path=db_path,
        task_points_path=task_points_path,
        event_sink=[],
    )


def test_scenario_a_two_idle_robots_one_task_assigns_exactly_one_robot(repo_root):
    registry = _registry_with_two_idle_robots()
    dispatcher = _dispatcher(registry, repo_root=repo_root)
    task = DispatchTask(task_id=1, pickup_station='station_a')

    assignment = dispatcher.assign_task(task, now=FIXED_NOW)

    assert assignment.robot_id in {'robot_01', 'robot_02'}
    assert assignment.task_id == 1
    assert assignment.pickup_station == 'station_a'
    assert assignment.status == AssignmentStatus.ASSIGNED
    assert assignment.cost >= 0.0
    assert 'distance=' in assignment.dispatch_reason

    assigned_robots = [
        robot
        for robot in registry.list_robots()
        if robot.current_task_id == 1
    ]
    assert len(assigned_robots) == 1
    assert assigned_robots[0].state == RobotState.ASSIGNED


def test_scenario_b_busy_robot_01_assigns_task_to_robot_02(repo_root):
    registry = _registry_with_two_idle_robots()
    registry.assign_task('robot_01', task_id=999)
    registry.mark_busy('robot_01')
    dispatcher = _dispatcher(registry, repo_root=repo_root)

    assignment = dispatcher.assign_task(
        DispatchTask(task_id=1, pickup_station='station_b'),
        now=FIXED_NOW,
    )

    assert assignment.robot_id == 'robot_02'
    assert registry.get_robot('robot_02').current_task_id == 1


def test_scenario_c_offline_robot_01_is_never_selected(repo_root):
    registry = _registry_with_two_idle_robots()
    registry.mark_offline('robot_01')
    dispatcher = _dispatcher(registry, repo_root=repo_root)

    candidates = dispatcher.list_candidates(
        DispatchTask(task_id=1, pickup_station='station_a'),
        now=FIXED_NOW,
    )
    assert [candidate.robot_id for candidate in candidates] == ['robot_02']

    assignment = dispatcher.assign_task(
        DispatchTask(task_id=1, pickup_station='station_a'),
        now=FIXED_NOW,
    )

    assert assignment.robot_id == 'robot_02'


def test_scenario_d_two_tasks_two_robots_no_duplicate_active_assignment(repo_root):
    registry = _registry_with_two_idle_robots()
    dispatcher = _dispatcher(registry, repo_root=repo_root)

    assignments = dispatcher.dispatch_tasks(
        [
            DispatchTask(task_id=1, pickup_station='station_a'),
            DispatchTask(task_id=2, pickup_station='station_b'),
        ],
        now=FIXED_NOW,
    )

    assert len(assignments) == 2
    assert assignments[0].robot_id != assignments[1].robot_id
    assert {assignment.task_id for assignment in assignments} == {1, 2}

    active_task_ids = [
        robot.current_task_id
        for robot in registry.list_robots()
        if robot.current_task_id is not None
    ]
    assert len(active_task_ids) == 2
    assert len(set(active_task_ids)) == 2


def test_select_robot_prefers_closer_station(repo_root):
    robots = {
        'robot_01': build_default_robot(
            'robot_01',
            timestamp=FIXED_HEARTBEAT,
            current_station='station_a',
        ),
        'robot_02': build_default_robot(
            'robot_02',
            timestamp=FIXED_HEARTBEAT,
            current_station='station_b',
        ),
    }
    registry = RobotRegistry(robots=robots)
    dispatcher = _dispatcher(registry, repo_root=repo_root)

    decision = dispatcher.select_robot(
        DispatchTask(task_id=10, pickup_station='station_a'),
        now=FIXED_NOW,
    )

    assert decision is not None
    assert decision.robot_id == 'robot_01'


def test_assign_task_rejects_duplicate_active_assignment(repo_root):
    registry = _registry_with_two_idle_robots()
    dispatcher = _dispatcher(registry, repo_root=repo_root)
    task = DispatchTask(task_id=1, pickup_station='station_a')

    dispatcher.assign_task(task, now=FIXED_NOW)

    with pytest.raises(TaskAlreadyAssignedError):
        dispatcher.assign_task(task, now=FIXED_NOW)


def test_assign_task_raises_when_no_robot_is_available(repo_root):
    registry = _registry_with_two_idle_robots()
    registry.mark_offline('robot_01')
    registry.mark_offline('robot_02')
    dispatcher = _dispatcher(registry, repo_root=repo_root)

    with pytest.raises(NoAvailableRobotError):
        dispatcher.assign_task(
            DispatchTask(task_id=1, pickup_station='station_a'),
            now=FIXED_NOW,
        )


def test_dispatch_tasks_stops_when_no_robot_remains(repo_root):
    registry = _registry_with_two_idle_robots()
    dispatcher = _dispatcher(registry, repo_root=repo_root)

    results = dispatcher.dispatch_tasks(
        [
            DispatchTask(task_id=1, pickup_station='station_a'),
            DispatchTask(task_id=2, pickup_station='station_b'),
            DispatchTask(task_id=3, pickup_station='shelf_1'),
        ],
        now=FIXED_NOW,
    )

    assert len(results) == 2


def test_dispatcher_persists_assignments_to_sqlite(tmp_path, repo_root):
    db_path = tmp_path / 'data' / 'fleet.db'
    registry = RobotRegistry(db_path=db_path, auto_seed=True)
    registry.record_heartbeat('robot_01', timestamp=FIXED_HEARTBEAT)
    registry.record_heartbeat('robot_02', timestamp=FIXED_HEARTBEAT)
    dispatcher = _dispatcher(registry, repo_root=repo_root, db_path=db_path)

    assignment = dispatcher.assign_task(
        DispatchTask(task_id=42, pickup_station='station_a'),
        now=FIXED_NOW,
    )

    reloaded = FleetDispatcher(
        registry,
        db_path=db_path,
        task_points_path=repo_root / 'config' / 'task_points.yaml',
    )
    stored = reloaded.get_assignment_for_task(42)

    assert stored is not None
    assert stored.robot_id == assignment.robot_id
    assert stored.cost == assignment.cost


def test_task_assigned_event_is_recorded(repo_root):
    registry = _registry_with_two_idle_robots()
    events: list = []
    dispatcher = FleetDispatcher(
        registry,
        task_points_path=repo_root / 'config' / 'task_points.yaml',
        event_sink=events,
    )

    dispatcher.assign_task(
        DispatchTask(task_id=7, pickup_station='station_a'),
        now=FIXED_NOW,
    )

    assert len(events) == 1
    assert events[0].event == 'TASK_ASSIGNED'
    assert events[0].task_id == 7
    assert events[0].robot_id in {'robot_01', 'robot_02'}

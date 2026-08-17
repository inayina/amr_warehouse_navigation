from datetime import datetime, timedelta, timezone

import pytest

from amr_warehouse_sim.fleet import (
    InvalidRobotTransitionError,
    RobotActiveTaskConflictError,
    RobotNotAvailableError,
    RobotNotFoundError,
    RobotRegistry,
    RobotState,
    SimulatedRobotContext,
    build_default_robot,
    is_heartbeat_valid,
    seed_default_robots,
)


def test_seed_default_robots_creates_robot_01_and_robot_02():
    registry = RobotRegistry(auto_seed=True)

    robots = registry.list_robots()
    assert [robot.robot_id for robot in robots] == ['robot_01', 'robot_02']
    assert all(robot.state == RobotState.IDLE for robot in robots)
    assert all(robot.current_station == 'start_zone' for robot in robots)
    assert all(robot.current_task_id is None for robot in robots)
    assert all(robot.battery == 100.0 for robot in robots)


def test_assign_task_moves_idle_robot_to_assigned():
    registry = RobotRegistry(robots=seed_default_robots())

    updated = registry.assign_task('robot_01', task_id=101)

    assert updated.state == RobotState.ASSIGNED
    assert updated.current_task_id == 101


def test_mark_busy_and_release_task_round_trip():
    registry = RobotRegistry(robots=seed_default_robots())
    registry.assign_task('robot_01', task_id=101)

    busy = registry.mark_busy('robot_01')
    assert busy.state == RobotState.BUSY
    assert busy.current_task_id == 101

    idle = registry.release_task('robot_01')
    assert idle.state == RobotState.IDLE
    assert idle.current_task_id is None


def test_offline_robot_cannot_accept_task():
    registry = RobotRegistry(robots=seed_default_robots())
    registry.mark_offline('robot_01')

    assert registry.can_accept_task('robot_01') is False

    with pytest.raises(RobotNotAvailableError):
        registry.assign_task('robot_01', task_id=101)


def test_robot_with_active_task_cannot_accept_second_task():
    registry = RobotRegistry(robots=seed_default_robots())
    registry.assign_task('robot_01', task_id=101)

    assert registry.can_accept_task('robot_01') is False

    with pytest.raises(RobotActiveTaskConflictError):
        registry.assign_task('robot_01', task_id=102)


def test_busy_robot_cannot_accept_second_task():
    registry = RobotRegistry(robots=seed_default_robots())
    registry.assign_task('robot_01', task_id=101)
    registry.mark_busy('robot_01')

    with pytest.raises(RobotActiveTaskConflictError):
        registry.assign_task('robot_01', task_id=102)


def test_mark_busy_requires_assigned_task():
    registry = RobotRegistry(robots=seed_default_robots())

    with pytest.raises(RobotNotAvailableError):
        registry.mark_busy('robot_01')


def test_release_task_requires_active_task_state():
    registry = RobotRegistry(robots=seed_default_robots())

    with pytest.raises(InvalidRobotTransitionError):
        registry.release_task('robot_01')


def test_invalid_transition_is_rejected():
    registry = RobotRegistry(robots=seed_default_robots())

    with pytest.raises(InvalidRobotTransitionError):
        registry._transition('robot_01', RobotState.BUSY)


def test_record_heartbeat_updates_last_seen_and_station():
    registry = RobotRegistry(robots=seed_default_robots())
    timestamp = '2026-08-17T09:30:00Z'

    updated = registry.record_heartbeat(
        'robot_02',
        timestamp=timestamp,
        current_station='station_b',
        battery=88.5,
    )

    assert updated.last_heartbeat == timestamp
    assert updated.current_station == 'station_b'
    assert updated.battery == 88.5


def test_heartbeat_from_offline_with_active_task_stays_offline():
    registry = RobotRegistry(robots=seed_default_robots())
    registry.assign_task('robot_02', task_id=202)
    registry.mark_offline('robot_02')

    updated = registry.record_heartbeat('robot_02', timestamp='2026-08-17T09:31:00Z')

    assert updated.state == RobotState.OFFLINE
    assert updated.current_task_id == 202


def test_heartbeat_from_offline_recovers_to_idle_when_no_active_task():
    registry = RobotRegistry(robots=seed_default_robots())
    registry.mark_offline('robot_02')

    recovered = registry.record_heartbeat('robot_02', timestamp='2026-08-17T09:31:00Z')

    assert recovered.state == RobotState.IDLE


def test_is_heartbeat_valid_respects_timeout():
    robot = build_default_robot('robot_01', timestamp='2026-08-17T09:00:00Z')
    now = datetime(2026, 8, 17, 9, 0, 20, tzinfo=timezone.utc)

    assert is_heartbeat_valid(robot, now=now, timeout_sec=30.0) is True

    stale_now = datetime(2026, 8, 17, 9, 0, 31, tzinfo=timezone.utc)
    assert is_heartbeat_valid(robot, now=stale_now, timeout_sec=30.0) is False


def test_can_accept_task_requires_fresh_heartbeat():
    registry = RobotRegistry(
        robots=seed_default_robots(timestamp='2026-08-17T09:00:00+00:00'),
    )
    stale_time = datetime(2026, 8, 17, 10, 0, 0, tzinfo=timezone.utc)

    assert registry.can_accept_task('robot_01', now=stale_time, heartbeat_timeout_sec=30.0) is False


def test_can_accept_task_allows_idle_robot_with_fresh_heartbeat():
    registry = RobotRegistry(
        robots=seed_default_robots(timestamp='2026-08-17T09:00:00+00:00'),
    )
    fresh_time = datetime(2026, 8, 17, 9, 0, 10, tzinfo=timezone.utc)

    assert registry.can_accept_task('robot_01', now=fresh_time, heartbeat_timeout_sec=30.0) is True


def test_recover_to_idle_requires_no_active_task_reference():
    registry = RobotRegistry(robots=seed_default_robots())
    registry.mark_error('robot_01')

    idle = registry.recover_to_idle('robot_01')
    assert idle.state == RobotState.IDLE


def test_recover_to_idle_rejects_robot_still_holding_task():
    registry = RobotRegistry(robots=seed_default_robots())
    registry.assign_task('robot_01', task_id=101)
    registry.mark_offline('robot_01')

    with pytest.raises(RobotActiveTaskConflictError):
        registry.recover_to_idle('robot_01')


def test_get_robot_raises_for_unknown_id():
    registry = RobotRegistry(robots=seed_default_robots())

    with pytest.raises(RobotNotFoundError):
        registry.get_robot('robot_99')


def test_registry_persists_to_sqlite_and_reloads(tmp_path):
    db_path = tmp_path / 'fleet.db'
    registry = RobotRegistry(db_path=db_path, auto_seed=True)
    registry.assign_task('robot_01', task_id=501)
    registry.mark_busy('robot_01')

    reloaded = RobotRegistry(db_path=db_path, auto_seed=False)

    robot = reloaded.get_robot('robot_01')
    assert robot.state == RobotState.BUSY
    assert robot.current_task_id == 501


def test_simulated_context_ready_gate_requires_assigned_task():
    registry = RobotRegistry(robots=seed_default_robots())
    context = SimulatedRobotContext('robot_01', registry)

    not_ready = context.check_ready_gate()
    assert not_ready.ready is False

    registry.assign_task('robot_01', task_id=301)
    ready = context.check_ready_gate()
    assert ready.ready is True


def test_simulated_context_navigation_marks_busy_and_can_complete():
    registry = RobotRegistry(robots=seed_default_robots())
    context = SimulatedRobotContext('robot_01', registry)
    registry.assign_task('robot_01', task_id=301)

    nav_result = context.navigate_to_pose()
    assert nav_result.succeeded is True
    assert registry.get_robot('robot_01').state == RobotState.BUSY

    context.complete_assigned_task()
    assert registry.get_robot('robot_01').state == RobotState.IDLE
    assert registry.get_robot('robot_01').current_task_id is None


def test_simulated_context_offline_robot_is_not_ready():
    registry = RobotRegistry(robots=seed_default_robots())
    registry.mark_offline('robot_02')
    context = SimulatedRobotContext('robot_02', registry)

    result = context.navigate_to_pose()
    assert result.succeeded is False
    assert 'OFFLINE' in result.reason

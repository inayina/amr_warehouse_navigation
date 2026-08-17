from datetime import datetime, timedelta, timezone

from amr_warehouse_sim.fleet import (
    AssignmentStatus,
    FleetDispatcher,
    HaulExecutionPhase,
    HaulTaskController,
    HeartbeatMonitor,
    RobotRegistry,
    RobotState,
    WmsTaskStatus,
    seed_default_robots,
)


FIXED_NOW = datetime(2026, 8, 17, 9, 0, 0, tzinfo=timezone.utc)
FIXED_HEARTBEAT = '2026-08-17T09:00:00Z'
TIMEOUT_NOW = FIXED_NOW + timedelta(seconds=31)
TIMEOUT_HEARTBEAT = '2026-08-17T09:00:31Z'


def _setup(repo_root, *, task_id: int = 3):
    events = []
    registry = RobotRegistry(robots=seed_default_robots(timestamp=FIXED_HEARTBEAT))
    dispatcher = FleetDispatcher(
        registry,
        task_points_path=repo_root / 'config' / 'task_points.yaml',
        event_sink=events,
    )
    haul = HaulTaskController(
        task_id=task_id,
        pickup_station='station_a',
        dropoff_station='station_b',
        dispatcher=dispatcher,
        event_sink=events,
    )
    monitor = HeartbeatMonitor(dispatcher)
    return haul, registry, dispatcher, monitor, events


def test_scenario_e_heartbeat_timeout_requeues_then_reassigns_to_robot_02(repo_root):
    haul, registry, dispatcher, monitor, events = _setup(repo_root, task_id=3)

    assigned = haul.assign(now=FIXED_NOW)
    assert assigned.robot_id == 'robot_01'
    haul.start()

    registry.record_heartbeat('robot_02', timestamp=TIMEOUT_HEARTBEAT)

    sweep = monitor.sweep(
        now=TIMEOUT_NOW,
        timeout_sec=30.0,
        haul_tasks={3: haul},
    )

    assert len(sweep) == 1
    assert sweep[0].robot_id == 'robot_01'
    assert sweep[0].requeued_task_id == 3
    assert sweep[0].reassignment_blocked is False
    assert registry.get_robot('robot_01').state == RobotState.OFFLINE
    assert haul.snapshot.wms_status == WmsTaskStatus.REQUEUED
    assert haul.snapshot.robot_id is None
    assert dispatcher.get_assignment_for_task(3) is None

    reassigned = monitor.reassign_requeued({3: haul}, now=TIMEOUT_NOW, timeout_sec=30.0)

    assert len(reassigned) == 1
    assert reassigned[0].robot_id == 'robot_02'
    assert reassigned[0].wms_status == WmsTaskStatus.ASSIGNED
    assert reassigned[0].execution_phase == HaulExecutionPhase.IDLE
    assert registry.get_robot('robot_02').state == RobotState.ASSIGNED
    assert dispatcher.get_assignment_for_task(3).robot_id == 'robot_02'

    event_names = [event.event for event in events]
    assert 'HEARTBEAT_TIMEOUT' in event_names
    assert 'ROBOT_OFFLINE' in event_names
    assert 'TASK_REQUEUED' in event_names
    assert 'TASK_REASSIGNED' in event_names


def test_idle_robot_timeout_goes_offline_without_task(repo_root):
    haul, registry, _, monitor, events = _setup(repo_root)
    del haul

    registry.record_heartbeat('robot_02', timestamp=TIMEOUT_HEARTBEAT)
    sweep = monitor.sweep(now=TIMEOUT_NOW, timeout_sec=30.0, haul_tasks={})

    assert [item.robot_id for item in sweep] == ['robot_01']
    assert sweep[0].requeued_task_id is None
    assert registry.get_robot('robot_01').state == RobotState.OFFLINE
    assert registry.get_robot('robot_02').state == RobotState.IDLE
    assert 'HEARTBEAT_TIMEOUT' in [event.event for event in events]
    assert 'ROBOT_OFFLINE' in [event.event for event in events]


def test_timeout_after_pickup_does_not_requeue(repo_root):
    haul, registry, dispatcher, monitor, _ = _setup(repo_root, task_id=5)
    assigned = haul.assign(now=FIXED_NOW)
    assert assigned.robot_id == 'robot_01'
    haul.start()
    haul.complete_navigation_to_pickup()
    haul.complete_pickup()

    registry.record_heartbeat('robot_02', timestamp=TIMEOUT_HEARTBEAT)
    sweep = monitor.sweep(
        now=TIMEOUT_NOW,
        timeout_sec=30.0,
        haul_tasks={5: haul},
    )

    assert sweep[0].reassignment_blocked is True
    assert sweep[0].requeued_task_id is None
    assert haul.snapshot.wms_status == WmsTaskStatus.IN_PROGRESS
    assert haul.snapshot.pickup_completed is True
    assert haul.snapshot.robot_id == 'robot_01'
    assert registry.get_robot('robot_01').state == RobotState.OFFLINE
    assert registry.get_robot('robot_01').current_task_id == 5
    assert dispatcher.get_assignment_for_task(5) is not None

    reassigned = monitor.reassign_requeued({5: haul}, now=TIMEOUT_NOW)
    assert reassigned == []


def test_assigned_but_not_started_task_is_still_reversible(repo_root):
    haul, registry, _, monitor, _ = _setup(repo_root, task_id=6)
    haul.assign(now=FIXED_NOW)
    registry.record_heartbeat('robot_02', timestamp=TIMEOUT_HEARTBEAT)

    sweep = monitor.sweep(
        now=TIMEOUT_NOW,
        timeout_sec=30.0,
        haul_tasks={6: haul},
    )

    assert sweep[0].requeued_task_id == 6
    assert haul.snapshot.wms_status == WmsTaskStatus.REQUEUED
    assert registry.get_robot('robot_01').state == RobotState.OFFLINE
    assert registry.get_robot('robot_01').current_task_id is None

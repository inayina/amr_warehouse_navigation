from datetime import datetime, timezone

import pytest

from amr_warehouse_sim.fleet import (
    AssignmentStatus,
    DispatchTask,
    FleetDispatcher,
    HaulExecutionPhase,
    HaulTaskController,
    InvalidLifecycleTransitionError,
    RobotRegistry,
    RobotState,
    WmsTaskStatus,
    seed_default_robots,
)


FIXED_NOW = datetime(2026, 8, 17, 9, 0, 0, tzinfo=timezone.utc)
FIXED_HEARTBEAT = '2026-08-17T09:00:00Z'


def _make_controller(repo_root, *, task_id: int = 1):
    events = []
    registry = RobotRegistry(robots=seed_default_robots(timestamp=FIXED_HEARTBEAT))
    dispatcher = FleetDispatcher(
        registry,
        task_points_path=repo_root / 'config' / 'task_points.yaml',
        event_sink=events,
    )
    controller = HaulTaskController(
        task_id=task_id,
        pickup_station='station_a',
        dropoff_station='station_b',
        dispatcher=dispatcher,
        event_sink=events,
    )
    return controller, registry, dispatcher, events


def test_haul_happy_path_keeps_three_state_machines_separate(repo_root):
    controller, registry, dispatcher, events = _make_controller(repo_root)

    created = controller.snapshot
    assert created.wms_status == WmsTaskStatus.PENDING
    assert created.assignment_status is None
    assert created.execution_phase == HaulExecutionPhase.IDLE

    assigned = controller.assign(now=FIXED_NOW)
    assert assigned.wms_status == WmsTaskStatus.ASSIGNED
    assert assigned.assignment_status == AssignmentStatus.ASSIGNED
    assert assigned.execution_phase == HaulExecutionPhase.IDLE
    assert assigned.robot_id in {'robot_01', 'robot_02'}
    assert registry.get_robot(assigned.robot_id).state == RobotState.ASSIGNED

    started = controller.start()
    assert started.wms_status == WmsTaskStatus.IN_PROGRESS
    assert started.assignment_status == AssignmentStatus.EXECUTING
    assert started.execution_phase == HaulExecutionPhase.NAVIGATING_TO_PICKUP
    assert registry.get_robot(started.robot_id).state == RobotState.BUSY

    at_pickup = controller.complete_navigation_to_pickup()
    assert at_pickup.execution_phase == HaulExecutionPhase.PICKUP
    assert at_pickup.wms_status == WmsTaskStatus.IN_PROGRESS
    assert at_pickup.assignment_status == AssignmentStatus.EXECUTING
    assert at_pickup.pickup_completed is False
    assert registry.get_robot(at_pickup.robot_id).current_station == 'station_a'

    after_pickup = controller.complete_pickup()
    assert after_pickup.execution_phase == HaulExecutionPhase.NAVIGATING_TO_DROPOFF
    assert after_pickup.pickup_completed is True
    assert after_pickup.wms_status == WmsTaskStatus.IN_PROGRESS

    at_dropoff = controller.complete_navigation_to_dropoff()
    assert at_dropoff.execution_phase == HaulExecutionPhase.DROPOFF
    assert registry.get_robot(at_dropoff.robot_id).current_station == 'station_b'

    done = controller.complete_dropoff()
    assert done.wms_status == WmsTaskStatus.SUCCEEDED
    assert done.assignment_status == AssignmentStatus.COMPLETED
    assert done.execution_phase == HaulExecutionPhase.SUCCEEDED
    assert done.coarse_mock_wms_status == 'succeeded'
    assert registry.get_robot(done.robot_id).state == RobotState.IDLE
    assert registry.get_robot(done.robot_id).current_task_id is None

    event_names = [event.event for event in events]
    assert event_names.count('TASK_CREATED') == 1
    assert 'TASK_ASSIGNED' in event_names
    assert 'ROBOT_BUSY' in event_names
    assert event_names.count('NAV_STARTED') == 2
    assert event_names.count('NAV_SUCCEEDED') == 2
    assert 'TASK_SUCCEEDED' in event_names


def test_simulated_run_until_success_helper(repo_root):
    controller, registry, _, _ = _make_controller(repo_root, task_id=8)
    done = controller.run_simulated_success(now=FIXED_NOW)

    assert done.is_terminal
    assert done.wms_status == WmsTaskStatus.SUCCEEDED
    robot = registry.get_robot(done.robot_id)
    assert robot.state == RobotState.IDLE
    assert robot.current_station == 'station_b'


def test_navigation_failure_before_pickup_marks_failed(repo_root):
    controller, registry, _, _ = _make_controller(repo_root)
    assigned = controller.assign(now=FIXED_NOW)
    controller.start()

    failed = controller.complete_navigation_to_pickup(simulate_failure=True)

    assert failed.wms_status == WmsTaskStatus.FAILED
    assert failed.assignment_status == AssignmentStatus.FAILED
    assert failed.execution_phase == HaulExecutionPhase.FAILED
    assert failed.pickup_completed is False
    assert registry.get_robot(assigned.robot_id).state == RobotState.IDLE


def test_cancel_before_pickup_releases_robot(repo_root):
    controller, registry, _, _ = _make_controller(repo_root)
    assigned = controller.assign(now=FIXED_NOW)

    canceled = controller.cancel('operator canceled')

    assert canceled.wms_status == WmsTaskStatus.CANCELED
    assert canceled.assignment_status == AssignmentStatus.CANCELED
    assert canceled.execution_phase == HaulExecutionPhase.CANCELED
    assert registry.get_robot(assigned.robot_id).state == RobotState.IDLE


def test_requeue_before_pickup_clears_robot_binding(repo_root):
    controller, registry, dispatcher, events = _make_controller(repo_root)
    assigned = controller.assign(now=FIXED_NOW)
    robot_id = assigned.robot_id
    controller.start()

    requeued = controller.requeue('heartbeat timeout preview')

    assert requeued.wms_status == WmsTaskStatus.REQUEUED
    assert requeued.assignment_status == AssignmentStatus.RELEASED
    assert requeued.execution_phase == HaulExecutionPhase.REQUEUED
    assert requeued.robot_id is None
    assert requeued.coarse_mock_wms_status == 'pending'
    assert registry.get_robot(robot_id).state == RobotState.IDLE
    assert dispatcher.get_assignment_for_task(1) is None
    assert 'TASK_REQUEUED' in [event.event for event in events]


def test_requeue_after_pickup_is_rejected(repo_root):
    controller, _, _, _ = _make_controller(repo_root)
    controller.assign(now=FIXED_NOW)
    controller.start()
    controller.complete_navigation_to_pickup()
    controller.complete_pickup()

    with pytest.raises(InvalidLifecycleTransitionError):
        controller.requeue()


def test_cancel_after_pickup_is_rejected(repo_root):
    controller, _, _, _ = _make_controller(repo_root)
    controller.assign(now=FIXED_NOW)
    controller.start()
    controller.complete_navigation_to_pickup()
    controller.complete_pickup()

    with pytest.raises(InvalidLifecycleTransitionError):
        controller.cancel()


def test_illegal_phase_skip_is_rejected(repo_root):
    controller, _, _, _ = _make_controller(repo_root)
    controller.assign(now=FIXED_NOW)
    controller.start()

    with pytest.raises(InvalidLifecycleTransitionError):
        controller.complete_pickup()


def test_single_point_dispatch_task_still_works_without_haul_fsm(repo_root):
    registry = RobotRegistry(robots=seed_default_robots(timestamp=FIXED_HEARTBEAT))
    dispatcher = FleetDispatcher(
        registry,
        task_points_path=repo_root / 'config' / 'task_points.yaml',
        event_sink=[],
    )

    assignment = dispatcher.assign_task(
        DispatchTask(task_id=99, pickup_station='station_a'),
        now=FIXED_NOW,
    )

    assert assignment.task_id == 99
    assert assignment.status == AssignmentStatus.ASSIGNED
    assert dispatcher.get_assignment_for_task(99) is not None

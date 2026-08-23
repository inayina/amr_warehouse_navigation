from dataclasses import fields

import pytest

from amr_warehouse_sim.inspection import (
    EvidenceReference,
    FindingOutcome,
    InspectionExecutionPhase,
    InspectionItem,
    InspectionPoint,
    InspectionRunController,
    InspectionTask,
    InvalidInspectionTransitionError,
    MockObservation,
    ObservationQuality,
    PointAttemptSnapshot,
)


EVIDENCE_A = EvidenceReference(
    uri='artifact://run-1/point-a/attempt-1.json',
    sha256='a' * 64,
)
EVIDENCE_B = EvidenceReference(
    uri='artifact://run-1/point-a/attempt-2.json',
    sha256='b' * 64,
)


def make_controller() -> InspectionRunController:
    task = InspectionTask(
        task_id='inspection-task-1',
        route_id='inspection-route-1',
        priority='normal',
        point=InspectionPoint(
            point_id='point-a',
            frame_id='map',
            x=1.0,
            y=2.0,
            yaw=0.0,
            maximum_observation_age_ms=500,
            item=InspectionItem(
                item_id='temperature-a',
                kind='temperature',
                maximum_value=65.0,
            ),
        ),
    )
    return InspectionRunController(run_id='run-1', robot_id='robot-1', task=task)


def advance_to_acquiring(controller: InspectionRunController) -> None:
    controller.start_navigation()
    controller.record_navigation_result(succeeded=True)
    controller.confirm_arrival(accepted=True)
    controller.complete_stabilization(succeeded=True)


def record_valid_observation(
    controller: InspectionRunController,
    *,
    value: float = 60.0,
    observation_id: str = 'observation-1',
) -> None:
    controller.record_observation(
        MockObservation(
            observation_id=observation_id,
            item_id='temperature-a',
            robot_id='robot-1',
            point_id='point-a',
            sensor_id='mock-temperature-sensor',
            frame_id='map',
            captured_at_ms=1_000,
            received_at_ms=1_050,
            value=value,
        )
    )
    result = controller.validate_observation(now_ms=1_100)
    assert result.quality is ObservationQuality.PASS


def test_navigation_success_only_enters_arrived() -> None:
    controller = make_controller()

    controller.start_navigation()
    controller.record_navigation_result(succeeded=True)

    assert controller.phase is InspectionExecutionPhase.ARRIVED
    assert not controller.snapshot.succeeded
    with pytest.raises(InvalidInspectionTransitionError):
        controller.complete_point()


@pytest.mark.parametrize(
    ('observation', 'now_ms', 'expected_quality'),
    [
        (
            MockObservation(
                observation_id='stale',
                item_id='temperature-a',
                robot_id='robot-1',
                point_id='point-a',
                sensor_id='mock-temperature-sensor',
                frame_id='map',
                captured_at_ms=100,
                received_at_ms=200,
                value=60.0,
            ),
            1_000,
            ObservationQuality.STALE,
        ),
        (
            MockObservation(
                observation_id='incomplete',
                item_id='temperature-a',
                robot_id='robot-1',
                point_id='point-a',
                sensor_id='mock-temperature-sensor',
                frame_id='map',
                captured_at_ms=900,
                received_at_ms=950,
                value=60.0,
                complete=False,
            ),
            1_000,
            ObservationQuality.INCOMPLETE,
        ),
        (
            MockObservation(
                observation_id='wrong-item',
                item_id='temperature-b',
                robot_id='robot-1',
                point_id='point-a',
                sensor_id='mock-temperature-sensor',
                frame_id='map',
                captured_at_ms=900,
                received_at_ms=950,
                value=60.0,
            ),
            1_000,
            ObservationQuality.INVALID,
        ),
    ],
)
def test_invalid_observation_fails_closed(
    observation: MockObservation,
    now_ms: int,
    expected_quality: ObservationQuality,
) -> None:
    controller = make_controller()
    advance_to_acquiring(controller)
    controller.record_observation(observation)

    result = controller.validate_observation(now_ms=now_ms)

    assert result.quality is expected_quality
    assert controller.phase is InspectionExecutionPhase.DATA_INVALID
    with pytest.raises(InvalidInspectionTransitionError):
        controller.evaluate()


def test_anomaly_finding_can_coexist_with_successful_execution() -> None:
    controller = make_controller()
    advance_to_acquiring(controller)
    record_valid_observation(controller, value=72.0)

    evaluation = controller.evaluate()
    controller.persist_evidence(EVIDENCE_A)
    controller.complete_point()

    assert evaluation.finding.outcome is FindingOutcome.ANOMALOUS
    assert controller.phase is InspectionExecutionPhase.POINT_SUCCEEDED

    controller.complete_run()
    assert controller.phase is InspectionExecutionPhase.SUCCEEDED
    assert controller.snapshot.succeeded


def test_point_cannot_succeed_before_evidence_is_persisted() -> None:
    controller = make_controller()
    advance_to_acquiring(controller)
    record_valid_observation(controller)
    controller.evaluate()

    with pytest.raises(InvalidInspectionTransitionError, match='evidence'):
        controller.complete_point()

    assert controller.phase is InspectionExecutionPhase.EVALUATING


def test_retry_creates_new_attempt_and_preserves_failed_attempt_evidence() -> None:
    controller = make_controller()
    advance_to_acquiring(controller)
    controller.record_observation(
        MockObservation(
            observation_id='stale-observation',
            item_id='temperature-a',
            robot_id='robot-1',
            point_id='point-a',
            sensor_id='mock-temperature-sensor',
            frame_id='map',
            captured_at_ms=0,
            received_at_ms=100,
            value=60.0,
        )
    )
    controller.validate_observation(now_ms=1_000)
    controller.persist_evidence(EVIDENCE_A)

    controller.retry_point()

    retry_snapshot = controller.snapshot
    assert len(retry_snapshot.attempts) == 2
    assert retry_snapshot.attempts[0].attempt_number == 1
    assert retry_snapshot.attempts[0].evidence_reference == EVIDENCE_A
    assert retry_snapshot.current_attempt.attempt_number == 2
    assert retry_snapshot.current_attempt.evidence_reference is None
    assert retry_snapshot.current_attempt.execution_phase == 'idle'

    advance_to_acquiring(controller)
    record_valid_observation(
        controller,
        value=60.0,
        observation_id='retry-observation',
    )
    controller.evaluate()
    controller.persist_evidence(EVIDENCE_B)
    controller.complete_point()

    completed_snapshot = controller.snapshot
    assert completed_snapshot.attempts[0].evidence_reference == EVIDENCE_A
    assert completed_snapshot.attempts[1].evidence_reference == EVIDENCE_B
    assert completed_snapshot.attempts[0].attempt_id != completed_snapshot.attempts[1].attempt_id


def test_attempt_rejects_evidence_overwrite() -> None:
    controller = make_controller()
    advance_to_acquiring(controller)
    record_valid_observation(controller)
    controller.evaluate()
    controller.persist_evidence(EVIDENCE_A)

    with pytest.raises(InvalidInspectionTransitionError, match='already has'):
        controller.persist_evidence(EVIDENCE_B)


def test_execution_snapshot_does_not_mix_business_or_assignment_state() -> None:
    field_names = {field.name for field in fields(PointAttemptSnapshot)}

    assert 'business_status' not in field_names
    assert 'wms_status' not in field_names
    assert 'assignment_status' not in field_names
    assert 'robot_id' not in field_names


def test_navigation_failure_is_retryable_with_new_attempt_identity() -> None:
    controller = make_controller()
    controller.start_navigation()
    controller.record_navigation_result(succeeded=False, reason='planner_failed')

    failed_attempt_id = controller.snapshot.current_attempt.attempt_id
    controller.retry_point()

    assert controller.phase is InspectionExecutionPhase.IDLE
    assert len(controller.snapshot.attempts) == 2
    assert controller.snapshot.attempts[0].reason == 'planner_failed'
    assert controller.snapshot.current_attempt.attempt_id != failed_attempt_id

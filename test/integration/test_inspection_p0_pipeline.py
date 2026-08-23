from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
from urllib.parse import unquote, urlparse

import pytest

from amr_warehouse_sim.inspection import (
    DeterministicMockAcquisition,
    EvidenceConflictError,
    FindingOutcome,
    InspectionExecutionPhase,
    InspectionItem,
    InspectionPoint,
    InspectionPointProcessor,
    InspectionRunController,
    InspectionTask,
    LocalJsonEvidenceStore,
    MaximumThresholdRule,
    MockReading,
    ReportCompletion,
)


def make_task() -> InspectionTask:
    return InspectionTask(
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


def make_controller() -> InspectionRunController:
    return InspectionRunController(
        run_id='run-1',
        robot_id='robot-1',
        task=make_task(),
    )


def advance_to_acquiring(controller: InspectionRunController) -> None:
    controller.start_navigation()
    controller.record_navigation_result(succeeded=True)
    controller.confirm_arrival(accepted=True)
    controller.complete_stabilization(succeeded=True)


def make_processor(
    tmp_path: Path,
    readings: tuple[MockReading, ...],
) -> InspectionPointProcessor:
    return InspectionPointProcessor(
        acquisition=DeterministicMockAcquisition(readings=readings),
        evaluator=MaximumThresholdRule(
            evaluator_id='temperature-maximum-rule',
            version='1.0.0',
            maximum_value=65.0,
        ),
        evidence_store=LocalJsonEvidenceStore(tmp_path / 'evidence'),
    )


def evidence_path(uri: str) -> Path:
    parsed = urlparse(uri)
    assert parsed.scheme == 'file'
    return Path(unquote(parsed.path))


def test_mock_pipeline_produces_hashed_evidence_and_success_report(
    tmp_path: Path,
) -> None:
    controller = make_controller()
    advance_to_acquiring(controller)
    processor = make_processor(
        tmp_path,
        (MockReading(value=60.0, captured_at_ms=1_000),),
    )

    report = processor.process_current_attempt(controller=controller, now_ms=1_100)

    assert controller.phase is InspectionExecutionPhase.SUCCEEDED
    assert report.completion is ReportCompletion.SUCCEEDED
    assert report.robot_id == 'robot-1'
    assert report.point['frame_id'] == 'map'
    assert report.retry_count == 0

    attempt = report.attempts[0]
    assert attempt.quality == {'quality': 'pass', 'reason': 'observation_valid'}
    assert attempt.evaluation is not None
    assert attempt.evaluation['evaluator_id'] == 'temperature-maximum-rule'
    assert attempt.evaluation['evaluator_version'] == '1.0.0'
    assert attempt.finding is not None
    assert attempt.finding['outcome'] == 'normal'
    assert attempt.evidence is not None

    artifact = evidence_path(str(attempt.evidence['uri']))
    encoded = artifact.read_bytes()
    assert sha256(encoded).hexdigest() == attempt.evidence['sha256']
    payload = json.loads(encoded)
    assert payload['run_id'] == 'run-1'
    assert payload['attempt']['observation']['sensor_id'] == 'mock-temperature-sensor'


def test_anomaly_finding_remains_a_successful_execution_report(tmp_path: Path) -> None:
    controller = make_controller()
    advance_to_acquiring(controller)
    processor = make_processor(
        tmp_path,
        (MockReading(value=72.0, captured_at_ms=1_000),),
    )

    report = processor.process_current_attempt(controller=controller, now_ms=1_100)

    assert report.completion is ReportCompletion.SUCCEEDED
    assert report.attempts[0].finding is not None
    assert report.attempts[0].finding['outcome'] == FindingOutcome.ANOMALOUS
    assert report.attempts[0].finding['severity'] == 'warning'
    assert report.attempts[0].system_fault is None


def test_stale_sample_is_reported_as_data_fault_with_evidence(tmp_path: Path) -> None:
    controller = make_controller()
    advance_to_acquiring(controller)
    processor = make_processor(
        tmp_path,
        (MockReading(value=60.0, captured_at_ms=0),),
    )

    report = processor.process_current_attempt(controller=controller, now_ms=1_000)

    assert controller.phase is InspectionExecutionPhase.DATA_INVALID
    assert report.completion is ReportCompletion.FAILED
    attempt = report.attempts[0]
    assert attempt.evaluation is None
    assert attempt.finding is None
    assert attempt.system_fault == {
        'code': 'data_invalid',
        'reason': 'observation_stale',
    }
    assert attempt.evidence is not None
    assert evidence_path(str(attempt.evidence['uri'])).is_file()


def test_mock_acquisition_exhaustion_is_a_sensor_fault(tmp_path: Path) -> None:
    controller = make_controller()
    advance_to_acquiring(controller)
    processor = make_processor(tmp_path, ())

    report = processor.process_current_attempt(controller=controller, now_ms=1_000)

    assert controller.phase is InspectionExecutionPhase.SENSOR_FAILED
    assert report.completion is ReportCompletion.FAILED
    assert report.attempts[0].observation is None
    assert report.attempts[0].system_fault == {
        'code': 'sensor_failed',
        'reason': 'mock_reading_exhausted',
    }
    assert report.attempts[0].evidence is not None


def test_retry_report_preserves_failed_and_successful_attempts(tmp_path: Path) -> None:
    controller = make_controller()
    advance_to_acquiring(controller)
    processor = make_processor(
        tmp_path,
        (
            MockReading(value=60.0, captured_at_ms=0),
            MockReading(value=60.0, captured_at_ms=1_900),
        ),
    )

    first_report = processor.process_current_attempt(controller=controller, now_ms=1_000)
    first_evidence = first_report.attempts[0].evidence
    controller.retry_point()
    advance_to_acquiring(controller)
    final_report = processor.process_current_attempt(controller=controller, now_ms=2_000)

    assert final_report.completion is ReportCompletion.SUCCEEDED
    assert final_report.retry_count == 1
    assert len(final_report.attempts) == 2
    assert final_report.attempts[0].system_fault is not None
    assert final_report.attempts[0].evidence == first_evidence
    assert final_report.attempts[1].system_fault is None
    assert final_report.attempts[1].evidence is not None
    assert final_report.attempts[0].evidence != final_report.attempts[1].evidence


def test_report_json_is_deterministic_and_contains_artifact_reference(
    tmp_path: Path,
) -> None:
    controller = make_controller()
    advance_to_acquiring(controller)
    processor = make_processor(
        tmp_path,
        (MockReading(value=60.0, captured_at_ms=1_000),),
    )
    report = processor.process_current_attempt(controller=controller, now_ms=1_100)

    first = report.to_json()
    second = report.to_json()

    assert first == second
    parsed = json.loads(first)
    assert parsed['completion'] == 'succeeded'
    assert parsed['attempts'][0]['evidence']['sha256']


def test_local_evidence_store_is_idempotent_but_rejects_conflicting_content(
    tmp_path: Path,
) -> None:
    store = LocalJsonEvidenceStore(tmp_path / 'evidence')
    controller = make_controller()
    controller.start_navigation()
    controller.record_navigation_result(succeeded=False, reason='planner_failed')
    attempt = controller.snapshot.current_attempt

    first = store.persist_attempt(run_id='run-1', attempt=attempt)
    second = store.persist_attempt(run_id='run-1', attempt=attempt)

    assert first == second
    with pytest.raises(EvidenceConflictError):
        store.persist_attempt(
            run_id='run-1',
            attempt=replace(attempt, reason='different_failure'),
        )


def test_processor_rejects_execution_before_acquisition_phase(tmp_path: Path) -> None:
    controller = make_controller()
    processor = make_processor(
        tmp_path,
        (MockReading(value=60.0, captured_at_ms=1_000),),
    )

    with pytest.raises(ValueError, match='ACQUIRING'):
        processor.process_current_attempt(controller=controller, now_ms=1_100)

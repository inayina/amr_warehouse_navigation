import json
from pathlib import Path

from amr_warehouse_sim.inspection import (
    DeterministicMockAcquisition,
    InspectionPointProcessor,
    LocalJsonEvidenceStore,
    MaximumThresholdRule,
    MockReading,
    ReportCompletion,
)
from amr_warehouse_sim.inspection.nav_executor import (
    DeterministicArrivalVerifier,
    DeterministicStabilizer,
    build_inspection_task,
    result_to_dict,
    run_inspection_nav_once,
)
from amr_warehouse_sim.mock_wms_executor import NavigationResult, ReadyGateResult


class FakeRuntime:
    def __init__(
        self,
        ready_results: ReadyGateResult | tuple[ReadyGateResult, ...],
        navigation_result: NavigationResult | None = None,
    ) -> None:
        self._ready_results = (
            ready_results if isinstance(ready_results, tuple) else (ready_results,)
        )
        self._navigation_result = navigation_result
        self.ready_calls = 0
        self.navigate_calls = 0
        self.last_pose = None
        self.last_timeout = None
        self.closed = False

    def check_ready_gate(self) -> ReadyGateResult:
        index = min(self.ready_calls, len(self._ready_results) - 1)
        self.ready_calls += 1
        return self._ready_results[index]

    def navigate_to_pose(
        self,
        pose: dict[str, object],
        *,
        timeout_sec: float,
    ) -> NavigationResult:
        self.navigate_calls += 1
        self.last_pose = pose
        self.last_timeout = timeout_sec
        assert self._navigation_result is not None
        return self._navigation_result

    def close(self) -> None:
        self.closed = True


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += max(seconds, 0.0)


def make_task(repo_root: Path):
    task, pose = build_inspection_task(
        task_id='inspection-task-1',
        target_name='station_a',
        task_points_path=repo_root / 'config' / 'task_points.yaml',
        maximum_observation_age_ms=500,
        maximum_value=65.0,
    )
    return task, pose


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


def nav_succeeded() -> NavigationResult:
    return NavigationResult(
        succeeded=True,
        status='succeeded',
        reason='NavigateToPose result: SUCCEEDED.',
    )


def nav_failed() -> NavigationResult:
    return NavigationResult(
        succeeded=False,
        status='failed',
        reason='NavigateToPose result: ABORTED.',
    )


def ready() -> ReadyGateResult:
    return ReadyGateResult(ready=True, reason='ready gate satisfied')


def run_execute(
    *,
    repo_root: Path,
    tmp_path: Path,
    runtime: FakeRuntime,
    readings: tuple[MockReading, ...],
    arrival_verifier=None,
    stabilizer=None,
    now_ms: int = 1_100,
):
    task, _ = make_task(repo_root)
    return run_inspection_nav_once(
        task=task,
        run_id='inspection-run-1',
        robot_id='amr-1',
        processor=make_processor(tmp_path, readings),
        execute=True,
        runtime=runtime,
        arrival_verifier=arrival_verifier,
        stabilizer=stabilizer,
        navigation_timeout_sec=45.0,
        now_ms=now_ms,
    )


def test_build_task_reuses_current_fixed_task_point(repo_root: Path) -> None:
    task, pose = make_task(repo_root)

    assert task.point.point_id == 'station_a'
    assert task.point.frame_id == 'map'
    assert task.point.x == pose['x'] == -5.3
    assert task.point.y == pose['y'] == -5.8


def test_dry_run_checks_ready_gate_without_navigation_or_inspection(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    task, _ = make_task(repo_root)
    runtime = FakeRuntime(ready())

    result = run_inspection_nav_once(
        task=task,
        run_id='inspection-run-1',
        robot_id='amr-1',
        processor=make_processor(
            tmp_path,
            (MockReading(value=60.0, captured_at_ms=1_000),),
        ),
        execute=False,
        runtime=runtime,
        now_ms=1_100,
    )

    assert result['outcome'] == 'dry-run-ready'
    assert result['goal_sent'] is False
    assert result['inspection_report'].completion is ReportCompletion.IN_PROGRESS
    assert runtime.ready_calls == 1
    assert runtime.navigate_calls == 0
    assert runtime.closed is False


def test_execute_waits_for_ready_then_runs_nav_and_inspection(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    runtime = FakeRuntime(
        (
            ReadyGateResult(ready=False, reason='amcl inactive'),
            ready(),
        ),
        nav_succeeded(),
    )
    clock = FakeClock()
    task, _ = make_task(repo_root)

    result = run_inspection_nav_once(
        task=task,
        run_id='inspection-run-1',
        robot_id='amr-1',
        processor=make_processor(
            tmp_path,
            (MockReading(value=60.0, captured_at_ms=1_000),),
        ),
        execute=True,
        runtime=runtime,
        ready_timeout_sec=5.0,
        ready_poll_interval_sec=1.0,
        navigation_timeout_sec=45.0,
        now_ms=1_100,
        sleep_fn=clock.sleep,
        monotonic_fn=clock.monotonic,
    )

    assert result['outcome'] == 'succeeded'
    assert result['goal_sent'] is True
    assert result['inspection_report'].completion is ReportCompletion.SUCCEEDED
    assert result['ready_wait'].attempts == 2
    assert runtime.ready_calls == 2
    assert runtime.navigate_calls == 1
    assert runtime.last_pose['frame_id'] == 'map'
    assert runtime.last_timeout == 45.0


def test_nav_success_does_not_override_stale_inspection_failure(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    runtime = FakeRuntime(ready(), nav_succeeded())

    result = run_execute(
        repo_root=repo_root,
        tmp_path=tmp_path,
        runtime=runtime,
        readings=(MockReading(value=60.0, captured_at_ms=0),),
        now_ms=1_100,
    )

    assert result['navigation_result'].succeeded is True
    assert result['outcome'] == 'failed'
    report = result['inspection_report']
    assert report.completion is ReportCompletion.FAILED
    assert report.attempts[0].system_fault['code'] == 'data_invalid'
    assert report.attempts[0].evidence is not None


def test_failed_navigation_stops_before_arrival_and_records_fault_evidence(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    runtime = FakeRuntime(ready(), nav_failed())

    result = run_execute(
        repo_root=repo_root,
        tmp_path=tmp_path,
        runtime=runtime,
        readings=(MockReading(value=60.0, captured_at_ms=1_000),),
    )

    assert result['outcome'] == 'failed'
    assert 'arrival_result' not in result
    attempt = result['inspection_report'].attempts[0]
    assert attempt.execution_phase == 'navigation_failed'
    assert attempt.observation is None
    assert attempt.evidence is not None
    assert runtime.navigate_calls == 1


def test_arrival_rejection_prevents_stabilization_and_acquisition(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    runtime = FakeRuntime(ready(), nav_succeeded())

    result = run_execute(
        repo_root=repo_root,
        tmp_path=tmp_path,
        runtime=runtime,
        readings=(MockReading(value=60.0, captured_at_ms=1_000),),
        arrival_verifier=DeterministicArrivalVerifier(
            accepted=False,
            reason='pose_outside_tolerance',
        ),
    )

    assert result['outcome'] == 'failed'
    assert result['arrival_result'].passed is False
    assert 'stabilization_result' not in result
    attempt = result['inspection_report'].attempts[0]
    assert attempt.execution_phase == 'inspection_failed'
    assert attempt.system_fault['reason'] == 'pose_outside_tolerance'
    assert attempt.observation is None


def test_stabilization_failure_prevents_acquisition(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    runtime = FakeRuntime(ready(), nav_succeeded())

    result = run_execute(
        repo_root=repo_root,
        tmp_path=tmp_path,
        runtime=runtime,
        readings=(MockReading(value=60.0, captured_at_ms=1_000),),
        stabilizer=DeterministicStabilizer(
            succeeded=False,
            reason='motion_not_stable',
        ),
    )

    assert result['outcome'] == 'failed'
    assert result['arrival_result'].passed is True
    assert result['stabilization_result'].passed is False
    attempt = result['inspection_report'].attempts[0]
    assert attempt.system_fault['reason'] == 'motion_not_stable'
    assert attempt.observation is None


def test_execute_not_ready_never_sends_goal(repo_root: Path, tmp_path: Path) -> None:
    runtime = FakeRuntime(ReadyGateResult(ready=False, reason='bt_navigator inactive'))
    clock = FakeClock()
    task, _ = make_task(repo_root)

    result = run_inspection_nav_once(
        task=task,
        run_id='inspection-run-1',
        robot_id='amr-1',
        processor=make_processor(tmp_path, ()),
        execute=True,
        runtime=runtime,
        ready_timeout_sec=0.0,
        now_ms=1_100,
        sleep_fn=clock.sleep,
        monotonic_fn=clock.monotonic,
    )

    assert result['outcome'] == 'execute-not-ready-timeout'
    assert result['goal_sent'] is False
    assert result['exit_code'] == 1
    assert runtime.navigate_calls == 0
    assert result['inspection_report'].completion is ReportCompletion.IN_PROGRESS


def test_result_can_be_serialized_for_cli_output(repo_root: Path, tmp_path: Path) -> None:
    runtime = FakeRuntime(ready(), nav_succeeded())
    result = run_execute(
        repo_root=repo_root,
        tmp_path=tmp_path,
        runtime=runtime,
        readings=(MockReading(value=72.0, captured_at_ms=1_000),),
    )

    encoded = json.dumps(result_to_dict(result), sort_keys=True)

    assert 'NavigateToPose result: SUCCEEDED.' in encoded
    assert 'value_above_maximum' in encoded
    assert 'file://' in encoded

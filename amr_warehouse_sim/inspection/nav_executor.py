from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import time
from typing import Protocol

from ..mock_wms_db_common import default_task_points_path, resolve_target_pose
from ..mock_wms_executor import (
    DEFAULT_ACTION_NAME,
    DEFAULT_NAVIGATION_TIMEOUT_SEC,
    DEFAULT_READY_GATE_TIMEOUT_SEC,
    DEFAULT_READY_POLL_INTERVAL_SEC,
    DEFAULT_READY_TIMEOUT_SEC,
    ExecutorRuntime,
    NavigationResult,
    RosNav2Runtime,
    wait_for_execute_ready_gate,
)
from .acquisition import DeterministicMockAcquisition, MockReading
from .evidence import LocalJsonEvidenceStore
from .lifecycle import InspectionRunController
from .models import InspectionItem, InspectionPoint, InspectionTask
from .pipeline import InspectionPointProcessor
from .report import InspectionReport, ReportCompletion, build_inspection_report
from .rules import MaximumThresholdRule


@dataclass(frozen=True)
class StageCheckResult:
    passed: bool
    reason: str


class ArrivalVerifier(Protocol):
    def verify_arrival(
        self,
        *,
        task: InspectionTask,
        navigation_result: NavigationResult,
    ) -> StageCheckResult:
        ...


class Stabilizer(Protocol):
    def stabilize(self, *, task: InspectionTask) -> StageCheckResult:
        ...


@dataclass(frozen=True)
class DeterministicArrivalVerifier:
    """P0 mock seam; this is not pose-tolerance or freshness verification."""

    accepted: bool = True
    reason: str = 'mock_arrival_accepted'

    def verify_arrival(
        self,
        *,
        task: InspectionTask,
        navigation_result: NavigationResult,
    ) -> StageCheckResult:
        del task, navigation_result
        return StageCheckResult(passed=self.accepted, reason=self.reason)


@dataclass(frozen=True)
class DeterministicStabilizer:
    """P0 mock seam; this does not measure real robot or sensor motion."""

    succeeded: bool = True
    reason: str = 'mock_stabilization_succeeded'

    def stabilize(self, *, task: InspectionTask) -> StageCheckResult:
        del task
        return StageCheckResult(passed=self.succeeded, reason=self.reason)


def build_inspection_task(
    *,
    task_id: str,
    target_name: str,
    task_points_path: Path | None,
    maximum_observation_age_ms: int,
    maximum_value: float,
) -> tuple[InspectionTask, dict[str, object]]:
    resolved_name, pose = resolve_target_pose(target_name, task_points_path)
    point = InspectionPoint(
        point_id=resolved_name,
        frame_id=str(pose['frame_id']),
        x=float(pose['x']),
        y=float(pose['y']),
        yaw=float(pose['yaw']),
        maximum_observation_age_ms=maximum_observation_age_ms,
        item=InspectionItem(
            item_id=f'{resolved_name}-temperature',
            kind='temperature',
            maximum_value=maximum_value,
        ),
    )
    return (
        InspectionTask(
            task_id=task_id,
            route_id=f'p0-single-point:{resolved_name}',
            priority='normal',
            point=point,
        ),
        pose,
    )


def run_inspection_nav_once(
    *,
    task: InspectionTask,
    run_id: str,
    robot_id: str,
    processor: InspectionPointProcessor,
    execute: bool = False,
    runtime: ExecutorRuntime | None = None,
    arrival_verifier: ArrivalVerifier | None = None,
    stabilizer: Stabilizer | None = None,
    action_name: str = DEFAULT_ACTION_NAME,
    ready_gate_timeout_sec: float = DEFAULT_READY_GATE_TIMEOUT_SEC,
    ready_timeout_sec: float = DEFAULT_READY_TIMEOUT_SEC,
    ready_poll_interval_sec: float = DEFAULT_READY_POLL_INTERVAL_SEC,
    navigation_timeout_sec: float = DEFAULT_NAVIGATION_TIMEOUT_SEC,
    now_ms: int | None = None,
    sleep_fn=time.sleep,
    monotonic_fn=time.monotonic,
) -> dict[str, object]:
    timestamp_ms = int(time.time() * 1000) if now_ms is None else now_ms
    controller = InspectionRunController(
        run_id=run_id,
        robot_id=robot_id,
        task=task,
    )
    result: dict[str, object] = {
        'mode': 'execute' if execute else 'dry-run',
        'run_id': run_id,
        'task_id': task.task_id,
        'robot_id': robot_id,
        'target_name': task.point.point_id,
        'resolved_pose': {
            'frame_id': task.point.frame_id,
            'x': task.point.x,
            'y': task.point.y,
            'yaw': task.point.yaw,
        },
        'goal_sent': False,
        'exit_code': 0,
    }

    owns_runtime = runtime is None
    runtime_instance = runtime or RosNav2Runtime(
        action_name=action_name,
        ready_gate_timeout_sec=ready_gate_timeout_sec,
    )
    try:
        if execute:
            ready_wait = wait_for_execute_ready_gate(
                runtime_instance,
                ready_timeout_sec=ready_timeout_sec,
                ready_poll_interval_sec=ready_poll_interval_sec,
                sleep_fn=sleep_fn,
                monotonic_fn=monotonic_fn,
            )
            ready_gate = ready_wait.ready_gate
            result['ready_wait'] = ready_wait
        else:
            ready_gate = runtime_instance.check_ready_gate()
        result['ready_gate'] = ready_gate

        if not ready_gate.ready:
            result['outcome'] = (
                'execute-not-ready-timeout' if execute else 'dry-run-not-ready'
            )
            result['message'] = f'Nav2 ready gate not satisfied: {ready_gate.reason}'
            result['exit_code'] = 1 if execute else 0
            report = build_inspection_report(
                task=task,
                run=controller.snapshot,
                generated_at_ms=timestamp_ms,
            )
            result['inspection_report'] = report
            return result

        if not execute:
            result['outcome'] = 'dry-run-ready'
            result['message'] = (
                'Dry-run only: ready gate satisfied; navigation and inspection not run.'
            )
            result['inspection_report'] = build_inspection_report(
                task=task,
                run=controller.snapshot,
                generated_at_ms=timestamp_ms,
            )
            return result

        controller.start_navigation()
        result['goal_sent'] = True
        navigation_result = runtime_instance.navigate_to_pose(
            result['resolved_pose'],
            timeout_sec=navigation_timeout_sec,
        )
        result['navigation_result'] = navigation_result
        controller.record_navigation_result(
            succeeded=navigation_result.succeeded,
            reason=navigation_result.reason,
        )
        if not navigation_result.succeeded:
            report = processor.finalize_current_failure(
                controller=controller,
                now_ms=timestamp_ms,
            )
            return _finish_result(result, report, navigation_result.reason)

        active_arrival_verifier = arrival_verifier or DeterministicArrivalVerifier()
        arrival_result = active_arrival_verifier.verify_arrival(
            task=task,
            navigation_result=navigation_result,
        )
        result['arrival_result'] = arrival_result
        controller.confirm_arrival(
            accepted=arrival_result.passed,
            reason=arrival_result.reason,
        )
        if not arrival_result.passed:
            report = processor.finalize_current_failure(
                controller=controller,
                now_ms=timestamp_ms,
            )
            return _finish_result(result, report, arrival_result.reason)

        active_stabilizer = stabilizer or DeterministicStabilizer()
        stabilization_result = active_stabilizer.stabilize(task=task)
        result['stabilization_result'] = stabilization_result
        controller.complete_stabilization(
            succeeded=stabilization_result.passed,
            reason=stabilization_result.reason,
        )
        if not stabilization_result.passed:
            report = processor.finalize_current_failure(
                controller=controller,
                now_ms=timestamp_ms,
            )
            return _finish_result(result, report, stabilization_result.reason)

        report = processor.process_current_attempt(
            controller=controller,
            now_ms=timestamp_ms,
        )
        return _finish_result(result, report, 'Inspection processing completed.')
    finally:
        if owns_runtime:
            runtime_instance.close()


def _finish_result(
    result: dict[str, object],
    report: InspectionReport,
    message: str,
) -> dict[str, object]:
    result['inspection_report'] = report
    result['outcome'] = report.completion.value
    result['message'] = message
    result['exit_code'] = 0 if report.completion is ReportCompletion.SUCCEEDED else 1
    return result


def result_to_dict(result: dict[str, object]) -> dict[str, object]:
    converted = dict(result)
    for key in (
        'ready_gate',
        'ready_wait',
        'navigation_result',
        'arrival_result',
        'stabilization_result',
    ):
        value = converted.get(key)
        if value is not None:
            converted[key] = asdict(value)
    report = converted.get('inspection_report')
    if isinstance(report, InspectionReport):
        converted['inspection_report'] = report.to_dict()
    return converted


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            'Run the opt-in P0 inspection executor using the existing single-robot '
            'Nav2 runtime. Dry-run is the default.'
        )
    )
    parser.add_argument('--task-id', default='inspection-task-p0')
    parser.add_argument('--run-id', default='inspection-run-p0')
    parser.add_argument('--robot-id', default='amr-1')
    parser.add_argument('--target-name', default='station_a')
    parser.add_argument('--task-points', type=Path, default=default_task_points_path())
    parser.add_argument('--mock-value', type=float, default=60.0)
    parser.add_argument('--maximum-value', type=float, default=65.0)
    parser.add_argument('--maximum-observation-age-ms', type=int, default=500)
    parser.add_argument(
        '--evidence-dir',
        type=Path,
        default=Path('/tmp/amr_warehouse_inspection_evidence'),
    )
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--action-name', default=DEFAULT_ACTION_NAME)
    parser.add_argument('--ready-gate-timeout', type=float, default=2.0)
    parser.add_argument('--ready-timeout', type=float, default=60.0)
    parser.add_argument('--ready-poll-interval', type=float, default=2.0)
    parser.add_argument('--navigation-timeout', type=float, default=180.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    timestamp_ms = int(time.time() * 1000)
    task, _ = build_inspection_task(
        task_id=args.task_id,
        target_name=args.target_name,
        task_points_path=args.task_points,
        maximum_observation_age_ms=args.maximum_observation_age_ms,
        maximum_value=args.maximum_value,
    )
    processor = InspectionPointProcessor(
        acquisition=DeterministicMockAcquisition(
            readings=(
                MockReading(value=args.mock_value, captured_at_ms=timestamp_ms),
            )
        ),
        evaluator=MaximumThresholdRule(
            evaluator_id='p0-temperature-maximum-rule',
            version='1.0.0',
            maximum_value=args.maximum_value,
        ),
        evidence_store=LocalJsonEvidenceStore(args.evidence_dir),
    )
    result = run_inspection_nav_once(
        task=task,
        run_id=args.run_id,
        robot_id=args.robot_id,
        processor=processor,
        execute=args.execute,
        action_name=args.action_name,
        ready_gate_timeout_sec=args.ready_gate_timeout,
        ready_timeout_sec=args.ready_timeout,
        ready_poll_interval_sec=args.ready_poll_interval,
        navigation_timeout_sec=args.navigation_timeout,
        now_ms=timestamp_ms,
    )
    print(json.dumps(result_to_dict(result), ensure_ascii=False, indent=2, sort_keys=True))
    return int(result['exit_code'])


if __name__ == '__main__':
    raise SystemExit(main())

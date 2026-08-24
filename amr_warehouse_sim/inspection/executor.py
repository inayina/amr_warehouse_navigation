from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time
from typing import Callable, Protocol

import yaml

from ..mock_wms_executor import (
    DEFAULT_ACTION_NAME,
    ExecutorRuntime,
    RosNav2Runtime,
    wait_for_execute_ready_gate,
)
from .image_capture import (
    CameraUnavailableError,
    CapturedImageFrame,
    ImageTimeoutError,
    RosImageCapture,
)
from .runtime_models import (
    ImageObservation,
    InspectionFaultCode,
    InspectionPointSpec,
    InspectionPointStatus,
    PointExecutionState,
)
from .store import InspectionStore
from .visual_evaluator import (
    InvalidImageError,
    decode_rgb_bytes,
    evaluate_red_ratio,
    write_rgb_png,
)


class ImageCaptureRuntime(Protocol):
    topic: str

    def check_ready(self, *, timeout_sec: float) -> tuple[bool, str]: ...

    def capture_fresh(self, *, timeout_sec: float) -> CapturedImageFrame: ...

    def close(self) -> None: ...


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def default_inspection_points_path() -> Path:
    from ament_index_python.packages import get_package_share_directory

    return Path(get_package_share_directory('amr_warehouse_sim')) / 'config' / 'inspection_points.yaml'


def load_inspection_points(path: Path) -> tuple[InspectionPointSpec, ...]:
    payload = yaml.safe_load(path.read_text(encoding='utf-8'))
    if not isinstance(payload, dict) or not payload:
        raise ValueError('Inspection points config must be a non-empty mapping.')

    points = []
    for point_id, raw in payload.items():
        if not isinstance(point_id, str) or not isinstance(raw, dict):
            raise ValueError('Inspection point entries must map names to objects.')
        if raw.get('inspection_item') != 'rgb':
            raise ValueError(f'{point_id}: only inspection_item rgb is supported.')
        points.append(
            InspectionPointSpec(
                point_id=point_id,
                sequence=int(raw['sequence']),
                frame_id=str(raw['frame_id']),
                x=float(raw['x']),
                y=float(raw['y']),
                yaw=float(raw['yaw']),
                image_topic=str(raw['image_topic']),
                stabilization_sec=float(raw['stabilization_sec']),
                red_ratio_threshold=float(raw['red_ratio_threshold']),
            )
        )
    points.sort(key=lambda point: point.sequence)
    sequences = [point.sequence for point in points]
    if sequences != list(range(1, len(points) + 1)):
        raise ValueError('Inspection point sequence must be contiguous and start at 1.')
    topics = {point.image_topic for point in points}
    if len(topics) != 1:
        raise ValueError('The RGB MVP requires one shared image_topic for the route.')
    return tuple(points)


def _write_json(path: Path, payload: dict[str, object]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + '\n',
        encoding='utf-8',
    )
    return path.resolve().as_uri()


def _summary(point_results: list[dict[str, object]], total_points: int) -> dict[str, object]:
    completed = sum(result['status'] == 'succeeded' for result in point_results)
    passed = sum(result.get('evaluation') == 'pass' for result in point_results)
    warnings = sum(result.get('evaluation') == 'warning' for result in point_results)
    failures = sum(result['status'] != 'succeeded' for result in point_results)
    return {
        'total_points': total_points,
        'completed_points': completed,
        'pass': passed,
        'warning': warnings,
        'execution_failures': failures,
    }


def _failed_point_result(
    *,
    run_id: str,
    point: InspectionPointSpec,
    state: PointExecutionState,
    navigation_result: dict[str, object],
    fault_code: InspectionFaultCode,
    reason: str,
) -> dict[str, object]:
    return {
        'run_id': run_id,
        'point_id': point.point_id,
        'sequence': point.sequence,
        'status': state.status.value,
        'navigation_result': navigation_result,
        'finding': None,
        'evaluation': None,
        'severity': None,
        'execution_fault': {'code': fault_code.value, 'reason': reason},
        'reason': reason,
        'artifact_ref': None,
        'result_ref': None,
        'transitions': list(state.transitions),
    }


def run_inspection_route(
    *,
    points: tuple[InspectionPointSpec, ...],
    run_id: str,
    robot_id: str,
    execute: bool,
    navigation_runtime: ExecutorRuntime,
    image_capture: ImageCaptureRuntime,
    artifact_root: Path,
    store: InspectionStore | None,
    ready_timeout_sec: float = 60.0,
    ready_poll_interval_sec: float = 2.0,
    navigation_timeout_sec: float = 180.0,
    image_timeout_sec: float = 5.0,
    sleep_fn: Callable[[float], None] = time.sleep,
    log_fn: Callable[[str], None] | None = None,
) -> dict[str, object]:
    if not points:
        raise ValueError('Inspection route must contain at least one point.')
    if execute and store is None:
        raise ValueError('Execute mode requires an InspectionStore.')
    logger = log_fn or (lambda message: None)
    route_id = 'default_route'
    started_at = _utc_now()
    run_dir = artifact_root / run_id

    if execute:
        store.start_run(
            run_id=run_id,
            robot_id=robot_id,
            route_id=route_id,
            started_at=started_at,
        )
        ready_wait = wait_for_execute_ready_gate(
            navigation_runtime,
            ready_timeout_sec=ready_timeout_sec,
            ready_poll_interval_sec=ready_poll_interval_sec,
        )
        ready_gate = ready_wait.ready_gate
    else:
        ready_wait = None
        ready_gate = navigation_runtime.check_ready_gate()

    camera_ready, camera_reason = image_capture.check_ready(timeout_sec=2.0)
    preflight = {
        'nav2': asdict(ready_gate),
        'camera': {
            'ready': camera_ready,
            'reason': camera_reason,
            'topic': image_capture.topic,
        },
    }
    if ready_wait is not None:
        preflight['nav2_wait'] = asdict(ready_wait)

    report: dict[str, object] = {
        'schema_version': 'gazebo-inspection-run-v1',
        'mode': 'execute' if execute else 'dry-run',
        'run_id': run_id,
        'robot_id': robot_id,
        'route_id': route_id,
        'started_at': started_at,
        'finished_at': None,
        'status': 'pending' if not execute else 'running',
        'goal_sent': False,
        'preflight': preflight,
        'points': [],
        'summary': _summary([], len(points)),
        'evidence_boundary': (
            'Gazebo RGB simulated visual stimulus; not real hardware evidence.'
        ),
    }

    if not execute:
        report['status'] = 'ready' if ready_gate.ready and camera_ready else 'not_ready'
        report['exit_code'] = 0 if report['status'] == 'ready' else 1
        return report

    if not ready_gate.ready or not camera_ready:
        reason = ready_gate.reason if not ready_gate.ready else camera_reason
        report['status'] = 'failed'
        report['execution_fault'] = {
            'code': (
                InspectionFaultCode.ROBOT_NOT_READY.value
                if not ready_gate.ready
                else InspectionFaultCode.CAMERA_UNAVAILABLE.value
            ),
            'reason': reason,
        }
        report['finished_at'] = _utc_now()
        report['exit_code'] = 1
        report['report_ref'] = _write_json(run_dir / 'report.json', report)
        store.finish_run(
            run_id=run_id,
            status='failed',
            finished_at=str(report['finished_at']),
            summary=report['summary'],
        )
        return report

    point_results: list[dict[str, object]] = []
    for point in points:
        state = PointExecutionState(point.point_id)
        state.transition(InspectionPointStatus.NAVIGATING, at_ns=time.time_ns())
        logger(f'{point.point_id}: NAVIGATING')
        report['goal_sent'] = True
        nav = navigation_runtime.navigate_to_pose(
            point.pose,
            timeout_sec=navigation_timeout_sec,
        )
        nav_payload = asdict(nav)
        if not nav.succeeded:
            state.transition(
                InspectionPointStatus.NAVIGATION_FAILED,
                at_ns=time.time_ns(),
                reason=nav.reason,
            )
            point_result = _failed_point_result(
                run_id=run_id,
                point=point,
                state=state,
                navigation_result=nav_payload,
                fault_code=InspectionFaultCode.NAVIGATION_FAILED,
                reason=nav.reason,
            )
            point_results.append(point_result)
            break

        state.transition(InspectionPointStatus.ARRIVED, at_ns=time.time_ns())
        logger(f'{point.point_id}: ARRIVED')
        state.transition(InspectionPointStatus.STABILIZING, at_ns=time.time_ns())
        sleep_fn(point.stabilization_sec)
        state.transition(InspectionPointStatus.ACQUIRING, at_ns=time.time_ns())
        logger(f'{point.point_id}: ACQUIRING fresh image')

        try:
            frame = image_capture.capture_fresh(timeout_sec=image_timeout_sec)
        except CameraUnavailableError as error:
            state.transition(
                InspectionPointStatus.ACQUISITION_FAILED,
                at_ns=time.time_ns(),
                reason=str(error),
            )
            point_result = _failed_point_result(
                run_id=run_id,
                point=point,
                state=state,
                navigation_result=nav_payload,
                fault_code=InspectionFaultCode.CAMERA_UNAVAILABLE,
                reason=str(error),
            )
            point_results.append(point_result)
            break
        except ImageTimeoutError as error:
            state.transition(
                InspectionPointStatus.ACQUISITION_FAILED,
                at_ns=time.time_ns(),
                reason=str(error),
            )
            point_result = _failed_point_result(
                run_id=run_id,
                point=point,
                state=state,
                navigation_result=nav_payload,
                fault_code=InspectionFaultCode.IMAGE_TIMEOUT,
                reason=str(error),
            )
            point_results.append(point_result)
            break

        state.transition(InspectionPointStatus.VALIDATING, at_ns=time.time_ns())
        try:
            if frame.captured_at_ns <= frame.acquisition_started_at_ns:
                raise InvalidImageError('stale_image_not_newer_than_acquisition_start')
            rgb = decode_rgb_bytes(
                width=frame.width,
                height=frame.height,
                encoding=frame.encoding,
                step=frame.step,
                data=frame.data,
            )
        except InvalidImageError as error:
            state.transition(
                InspectionPointStatus.DATA_INVALID,
                at_ns=time.time_ns(),
                reason=str(error),
            )
            point_result = _failed_point_result(
                run_id=run_id,
                point=point,
                state=state,
                navigation_result=nav_payload,
                fault_code=InspectionFaultCode.DATA_INVALID,
                reason=str(error),
            )
            point_results.append(point_result)
            break

        point_dir = run_dir / point.point_id
        image_path = point_dir / 'rgb.png'
        image_sha256 = write_rgb_png(
            image_path,
            width=frame.width,
            height=frame.height,
            rgb=rgb,
        )
        artifact_ref = image_path.resolve().as_uri()
        state.transition(InspectionPointStatus.EVALUATING, at_ns=time.time_ns())
        try:
            evaluation = evaluate_red_ratio(
                rgb,
                threshold=point.red_ratio_threshold,
            )
        except Exception as error:
            state.transition(
                InspectionPointStatus.EVALUATION_FAILED,
                at_ns=time.time_ns(),
                reason=str(error),
            )
            point_result = _failed_point_result(
                run_id=run_id,
                point=point,
                state=state,
                navigation_result=nav_payload,
                fault_code=InspectionFaultCode.EVALUATION_FAILED,
                reason=str(error),
            )
            point_result['artifact_ref'] = artifact_ref
            point_results.append(point_result)
            break

        observation = ImageObservation(
            run_id=run_id,
            point_id=point.point_id,
            robot_id=robot_id,
            captured_at_ns=frame.captured_at_ns,
            received_at_ns=frame.received_at_ns,
            acquisition_started_at_ns=frame.acquisition_started_at_ns,
            image_topic=frame.topic,
            image_width=frame.width,
            image_height=frame.height,
            encoding=frame.encoding,
            artifact_ref=artifact_ref,
            red_ratio=evaluation.red_ratio,
        )
        state.transition(InspectionPointStatus.SUCCEEDED, at_ns=time.time_ns())
        point_result = {
            'run_id': run_id,
            'point_id': point.point_id,
            'sequence': point.sequence,
            'status': state.status.value,
            'navigation_result': nav_payload,
            'arrival_accepted': True,
            'observation': observation.to_dict(),
            'captured_at_ns': frame.captured_at_ns,
            'fresh_after_acquisition': True,
            'evaluation': evaluation.finding,
            'finding': {
                'level': evaluation.finding,
                'red_ratio': evaluation.red_ratio,
                'threshold': evaluation.threshold,
                'reason': evaluation.reason,
            },
            'severity': evaluation.severity,
            'execution_fault': None,
            'reason': evaluation.reason,
            'artifact_ref': artifact_ref,
            'artifact_sha256': image_sha256,
            'result_ref': (point_dir / 'result.json').resolve().as_uri(),
            'transitions': list(state.transitions),
        }
        _write_json(point_dir / 'result.json', point_result)
        point_results.append(point_result)
        logger(
            f'{point.point_id}: {evaluation.finding.upper()} '
            f'(red_ratio={evaluation.red_ratio:.4f})'
        )

    for result in point_results:
        point_dir = run_dir / str(result['point_id'])
        if result.get('result_ref') is None:
            result['result_ref'] = (point_dir / 'result.json').resolve().as_uri()
            _write_json(point_dir / 'result.json', result)
        store.persist_point_result(result)

    report['points'] = point_results
    report['summary'] = _summary(point_results, len(points))
    run_succeeded = (
        len(point_results) == len(points)
        and all(result['status'] == 'succeeded' for result in point_results)
    )
    report['status'] = 'succeeded' if run_succeeded else 'failed'
    report['finished_at'] = _utc_now()
    report['exit_code'] = 0 if run_succeeded else 1
    report['report_ref'] = (run_dir / 'report.json').resolve().as_uri()
    _write_json(run_dir / 'report.json', report)
    store.finish_run(
        run_id=run_id,
        status=str(report['status']),
        finished_at=str(report['finished_at']),
        summary=report['summary'],
    )
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Run the single-robot Gazebo RGB inspection reference route.'
    )
    parser.add_argument('--route', default='default_route', choices=('default_route',))
    parser.add_argument('--points-config', type=Path, default=default_inspection_points_path())
    parser.add_argument('--run-id')
    parser.add_argument('--robot-id', default='my_robot')
    parser.add_argument('--db', type=Path, default=Path('data/inspection.db'))
    parser.add_argument(
        '--artifact-root',
        type=Path,
        default=Path('artifacts/inspection/runs'),
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--dry-run', action='store_true')
    mode.add_argument('--execute', action='store_true')
    parser.add_argument('--action-name', default=DEFAULT_ACTION_NAME)
    parser.add_argument('--ready-gate-timeout', type=float, default=2.0)
    parser.add_argument('--ready-timeout', type=float, default=60.0)
    parser.add_argument('--ready-poll-interval', type=float, default=2.0)
    parser.add_argument('--navigation-timeout', type=float, default=180.0)
    parser.add_argument('--image-timeout', type=float, default=5.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    points = load_inspection_points(args.points_config)
    run_id = args.run_id or datetime.now(timezone.utc).strftime(
        'inspection-run-%Y%m%dT%H%M%SZ'
    )
    nav_runtime = RosNav2Runtime(
        action_name=args.action_name,
        ready_gate_timeout_sec=args.ready_gate_timeout,
    )
    image_capture = RosImageCapture(topic=points[0].image_topic, use_sim_time=True)
    store = InspectionStore(args.db) if args.execute else None
    try:
        report = run_inspection_route(
            points=points,
            run_id=run_id,
            robot_id=args.robot_id,
            execute=args.execute,
            navigation_runtime=nav_runtime,
            image_capture=image_capture,
            artifact_root=args.artifact_root,
            store=store,
            ready_timeout_sec=args.ready_timeout,
            ready_poll_interval_sec=args.ready_poll_interval,
            navigation_timeout_sec=args.navigation_timeout,
            image_timeout_sec=args.image_timeout,
            log_fn=lambda message: print(message, file=sys.stderr, flush=True),
        )
    finally:
        image_capture.close()
        nav_runtime.close()
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return int(report['exit_code'])


if __name__ == '__main__':
    raise SystemExit(main())

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
from typing import Callable

try:
    from ament_index_python.packages import PackageNotFoundError, get_package_share_directory
except ImportError:
    PackageNotFoundError = None
    get_package_share_directory = None

EXECUTOR_SCRIPT_NAME = 'run_mock_wms_executor.py'
CONSUMING_OUTCOMES = {
    'invalid-target',
    'failed',
    'succeeded',
}


def _package_share_directory() -> Path | None:
    if get_package_share_directory is None:
        return None

    try:
        return Path(get_package_share_directory('amr_warehouse_sim'))
    except Exception as exc:
        if PackageNotFoundError is not None and isinstance(exc, PackageNotFoundError):
            return None
        raise


def _nonnegative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError('Value must be >= 0.')
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            'Run the current-mainline Mock WMS task runner. '
            'Dry-run inspects only the earliest pending task; execute mode can '
            'drain a sequential pending-task queue.'
        )
    )
    parser.add_argument(
        '--db',
        '--db-path',
        type=Path,
        default=None,
        dest='db_path',
        help='SQLite database path. Defaults to the executor script default.',
    )
    parser.add_argument(
        '--task-points',
        type=Path,
        default=None,
        help='Task point YAML path. Defaults to the executor script default.',
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        '--dry-run',
        action='store_true',
        help='Explicitly keep dry-run mode. This is already the default behavior.',
    )
    mode_group.add_argument(
        '--execute',
        action='store_true',
        help='Actually send NavigateToPose goals and consume the pending queue.',
    )
    parser.add_argument(
        '--action-name',
        default='/navigate_to_pose',
        help='NavigateToPose action name. Defaults to /navigate_to_pose.',
    )
    parser.add_argument(
        '--ready-gate-timeout',
        type=float,
        default=2.0,
        help='Seconds to wait for each ready-gate check before marking it unavailable.',
    )
    parser.add_argument(
        '--ready-timeout',
        type=float,
        default=60.0,
        help='Seconds to wait for execute-mode ready gate success before giving up.',
    )
    parser.add_argument(
        '--ready-poll-interval',
        type=float,
        default=2.0,
        help='Seconds to wait between execute-mode ready gate checks.',
    )
    parser.add_argument(
        '--navigation-timeout',
        type=float,
        default=180.0,
        help='Seconds to wait for each NavigateToPose result in execute mode.',
    )
    parser.add_argument(
        '--max-tasks',
        type=_nonnegative_int,
        default=0,
        help=(
            'Maximum number of pending tasks to consume in execute mode. '
            '0 means keep going until the queue is empty. Dry-run always stops '
            'after the earliest pending task.'
        ),
    )
    parser.add_argument(
        '--continue-on-failure',
        action='store_true',
        help='In execute mode, continue to later pending tasks after a failed or invalid task.',
    )
    return parser


def resolve_executor_script_path() -> Path:
    candidates = [
        Path(__file__).resolve().parents[1] / 'scripts' / EXECUTOR_SCRIPT_NAME,
    ]

    package_share = _package_share_directory()

    if package_share is not None:
        candidates.append(package_share / 'scripts' / EXECUTOR_SCRIPT_NAME)

    for candidate in candidates:
        if candidate.is_file():
            return candidate

    candidate_list = ', '.join(str(candidate) for candidate in candidates)
    raise FileNotFoundError(
        f'Could not locate {EXECUTOR_SCRIPT_NAME}. Checked: {candidate_list}'
    )


def load_executor_module(script_path: Path):
    spec = importlib.util.spec_from_file_location('mock_wms_executor_script', script_path)
    if spec is None or spec.loader is None:
        raise ImportError(f'Could not load executor module from {script_path}')

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    run_once = getattr(module, 'run_executor_once', None)
    if not callable(run_once):
        raise AttributeError(f'{script_path} does not expose a callable run_executor_once().')

    return module


def run_task_queue(
    *,
    db_path: Path | None = None,
    task_points_path: Path | None = None,
    execute: bool = False,
    action_name: str = '/navigate_to_pose',
    ready_gate_timeout_sec: float = 2.0,
    ready_timeout_sec: float = 60.0,
    ready_poll_interval_sec: float = 2.0,
    navigation_timeout_sec: float = 180.0,
    max_tasks: int = 0,
    continue_on_failure: bool = False,
    executor_module=None,
    run_once_fn: Callable[..., dict[str, object]] | None = None,
) -> dict[str, object]:
    if max_tasks < 0:
        raise ValueError('max_tasks must be >= 0.')

    module = executor_module
    if run_once_fn is None:
        if module is None:
            module = load_executor_module(resolve_executor_script_path())
        run_once_fn = getattr(module, 'run_executor_once')

    runs: list[dict[str, object]] = []
    consumed_tasks = 0
    succeeded_tasks = 0
    failed_tasks = 0
    exit_code = 0
    stop_reason = 'queue-empty'

    while True:
        if execute and max_tasks > 0 and consumed_tasks >= max_tasks:
            stop_reason = 'max-tasks-reached'
            break

        result = run_once_fn(
            db_path=db_path,
            task_points_path=task_points_path,
            execute=execute,
            action_name=action_name,
            ready_gate_timeout_sec=ready_gate_timeout_sec,
            ready_timeout_sec=ready_timeout_sec,
            ready_poll_interval_sec=ready_poll_interval_sec,
            navigation_timeout_sec=navigation_timeout_sec,
        )
        runs.append(result)
        exit_code = max(exit_code, int(result.get('exit_code', 0)))

        outcome = str(result.get('outcome', 'unknown'))
        if outcome == 'no-pending-task':
            stop_reason = 'queue-empty'
            break

        if not execute:
            stop_reason = 'dry-run-single-pass'
            break

        if outcome == 'succeeded':
            consumed_tasks += 1
            succeeded_tasks += 1
            continue

        if outcome in {'failed', 'invalid-target'}:
            consumed_tasks += 1
            failed_tasks += 1
            if continue_on_failure:
                continue
            stop_reason = 'terminal-failure'
            break

        if outcome == 'execute-not-ready-timeout':
            stop_reason = 'ready-gate-timeout'
            exit_code = max(exit_code, 1)
            break

        if outcome not in CONSUMING_OUTCOMES:
            stop_reason = 'task-not-consumed'
            exit_code = max(exit_code, 1 if execute else 0)
            break

        stop_reason = 'unexpected-outcome'
        exit_code = max(exit_code, 1)
        break

    task_runs = sum(1 for run in runs if run.get('task_before') is not None)
    return {
        'mode': 'execute' if execute else 'dry-run',
        'runs': runs,
        'executor_runs': len(runs),
        'task_runs': task_runs,
        'consumed_tasks': consumed_tasks,
        'succeeded_tasks': succeeded_tasks,
        'failed_tasks': failed_tasks,
        'stop_reason': stop_reason,
        'exit_code': exit_code,
        'last_result': runs[-1] if runs else None,
    }


def format_queue_result_message(result: dict[str, object]) -> str:
    last_result = result.get('last_result') or {}
    last_outcome = str(last_result.get('outcome', 'n/a'))
    return (
        '[mock_wms_task_runner] '
        f'mode={result["mode"]}, '
        f'executor_runs={result["executor_runs"]}, '
        f'task_runs={result["task_runs"]}, '
        f'consumed_tasks={result["consumed_tasks"]}, '
        f'succeeded_tasks={result["succeeded_tasks"]}, '
        f'failed_tasks={result["failed_tasks"]}, '
        f'stop_reason={result["stop_reason"]}, '
        f'last_outcome={last_outcome}.'
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    executor_module = load_executor_module(resolve_executor_script_path())
    result = run_task_queue(
        db_path=args.db_path,
        task_points_path=args.task_points,
        execute=args.execute,
        action_name=args.action_name,
        ready_gate_timeout_sec=args.ready_gate_timeout,
        ready_timeout_sec=args.ready_timeout,
        ready_poll_interval_sec=args.ready_poll_interval,
        navigation_timeout_sec=args.navigation_timeout,
        max_tasks=args.max_tasks,
        continue_on_failure=args.continue_on_failure,
        executor_module=executor_module,
    )

    formatter = getattr(executor_module, 'format_result_message', None)
    if callable(formatter):
        for run_result in result['runs']:
            print(formatter(run_result))

    print(format_queue_result_message(result))
    return int(result['exit_code'])


if __name__ == '__main__':
    raise SystemExit(main())

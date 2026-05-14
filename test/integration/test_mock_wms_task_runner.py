import importlib.util


def _fake_result(
    outcome: str,
    *,
    task_id: int | None = 1,
    exit_code: int = 0,
) -> dict[str, object]:
    task_before = None if task_id is None else {'id': task_id, 'target_name': f'target_{task_id}'}
    return {
        'mode': 'execute',
        'task_before': task_before,
        'task_after': None,
        'goal_sent': outcome == 'succeeded',
        'outcome': outcome,
        'exit_code': exit_code,
    }


def _fake_run_once_factory(results: list[dict[str, object]]):
    calls: list[dict[str, object]] = []
    pending = list(results)

    def _run_once(**kwargs):
        calls.append(kwargs)
        if not pending:
            raise AssertionError('run_once called more times than expected')
        return pending.pop(0)

    return _run_once, calls


def _load_module(module_path, module_name):
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_dry_run_stops_after_the_first_pending_task_check(repo_root):
    runner = _load_module(
        repo_root / 'amr_warehouse_sim' / 'mock_wms_task_runner.py',
        'mock_wms_task_runner',
    )
    run_once, calls = _fake_run_once_factory(
        [
            _fake_result('dry-run-ready', task_id=1),
            _fake_result('no-pending-task', task_id=None),
        ]
    )

    result = runner.run_task_queue(execute=False, run_once_fn=run_once)

    assert len(calls) == 1
    assert result['task_runs'] == 1
    assert result['consumed_tasks'] == 0
    assert result['stop_reason'] == 'dry-run-single-pass'
    assert result['exit_code'] == 0


def test_execute_drains_multiple_succeeded_tasks_until_the_queue_is_empty(repo_root):
    runner = _load_module(
        repo_root / 'amr_warehouse_sim' / 'mock_wms_task_runner.py',
        'mock_wms_task_runner',
    )
    run_once, calls = _fake_run_once_factory(
        [
            _fake_result('succeeded', task_id=1),
            _fake_result('succeeded', task_id=2),
            _fake_result('no-pending-task', task_id=None),
        ]
    )

    result = runner.run_task_queue(execute=True, run_once_fn=run_once)

    assert len(calls) == 3
    assert result['task_runs'] == 2
    assert result['consumed_tasks'] == 2
    assert result['succeeded_tasks'] == 2
    assert result['failed_tasks'] == 0
    assert result['stop_reason'] == 'queue-empty'
    assert result['exit_code'] == 0


def test_execute_stops_when_ready_gate_timeout_keeps_the_task_pending(repo_root):
    runner = _load_module(
        repo_root / 'amr_warehouse_sim' / 'mock_wms_task_runner.py',
        'mock_wms_task_runner',
    )
    run_once, calls = _fake_run_once_factory(
        [
            _fake_result('execute-not-ready-timeout', task_id=1),
        ]
    )

    result = runner.run_task_queue(execute=True, run_once_fn=run_once)

    assert len(calls) == 1
    assert result['task_runs'] == 1
    assert result['consumed_tasks'] == 0
    assert result['stop_reason'] == 'ready-gate-timeout'
    assert result['exit_code'] == 1


def test_execute_stops_on_the_first_terminal_failure_by_default(repo_root):
    runner = _load_module(
        repo_root / 'amr_warehouse_sim' / 'mock_wms_task_runner.py',
        'mock_wms_task_runner',
    )
    run_once, calls = _fake_run_once_factory(
        [
            _fake_result('failed', task_id=1, exit_code=1),
            _fake_result('succeeded', task_id=2),
        ]
    )

    result = runner.run_task_queue(execute=True, run_once_fn=run_once)

    assert len(calls) == 1
    assert result['task_runs'] == 1
    assert result['consumed_tasks'] == 1
    assert result['succeeded_tasks'] == 0
    assert result['failed_tasks'] == 1
    assert result['stop_reason'] == 'terminal-failure'
    assert result['exit_code'] == 1


def test_execute_can_continue_past_a_terminal_failure_when_requested(repo_root):
    runner = _load_module(
        repo_root / 'amr_warehouse_sim' / 'mock_wms_task_runner.py',
        'mock_wms_task_runner',
    )
    run_once, calls = _fake_run_once_factory(
        [
            _fake_result('failed', task_id=1, exit_code=1),
            _fake_result('succeeded', task_id=2),
            _fake_result('no-pending-task', task_id=None),
        ]
    )

    result = runner.run_task_queue(
        execute=True,
        continue_on_failure=True,
        run_once_fn=run_once,
    )

    assert len(calls) == 3
    assert result['task_runs'] == 2
    assert result['consumed_tasks'] == 2
    assert result['succeeded_tasks'] == 1
    assert result['failed_tasks'] == 1
    assert result['stop_reason'] == 'queue-empty'
    assert result['exit_code'] == 1

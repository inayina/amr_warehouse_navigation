import importlib.util
import sqlite3


def _load_module(module_path, module_name):
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class FakeRuntime:
    def __init__(self, executor_module, ready_gate_result, navigation_result=None):
        self._executor_module = executor_module
        if isinstance(ready_gate_result, (list, tuple)):
            self._ready_gate_results = list(ready_gate_result)
        else:
            self._ready_gate_results = [ready_gate_result]
        self._navigation_result = navigation_result
        self.ready_calls = 0
        self.navigate_calls = 0
        self.closed = False
        self.last_pose = None
        self.last_timeout = None

    def check_ready_gate(self):
        self.ready_calls += 1
        index = min(self.ready_calls - 1, len(self._ready_gate_results) - 1)
        return self._ready_gate_results[index]

    def navigate_to_pose(self, pose, *, timeout_sec):
        self.navigate_calls += 1
        self.last_pose = pose
        self.last_timeout = timeout_sec
        return self._navigation_result

    def close(self):
        self.closed = True


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.now += max(seconds, 0.0)


def _http_task_payload(*tasks):
    return {
        'count': len(tasks),
        'tasks': list(tasks),
    }


class FakeHttpResponse:
    def __init__(self, body: str):
        self._body = body.encode('utf-8')

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self._body


def _http_task(
    *,
    task_id: int,
    task_name: str,
    target_name: str,
    status: str,
    status_reason=None,
    created_at: str = '2026-05-14T10:00:00Z',
    updated_at: str = '2026-05-14T10:00:00Z',
    x: float = 1.0,
    y: float = 2.0,
    yaw: float = 0.0,
):
    return {
        'id': task_id,
        'task_name': task_name,
        'target_name': target_name,
        'frame_id': 'map',
        'x': x,
        'y': y,
        'yaw': yaw,
        'status': status,
        'status_reason': status_reason,
        'created_at': created_at,
        'updated_at': updated_at,
    }


def _recording_patch_status_fn(calls, *, task_name='pending-http-task', target_name='station_a'):
    def _patch(api_base_url, task_id, *, status, status_reason, timeout_sec):
        calls.append(
            {
                'api_base_url': api_base_url,
                'task_id': task_id,
                'status': status,
                'status_reason': status_reason,
                'timeout_sec': timeout_sec,
            }
        )
        return _http_task(
            task_id=task_id,
            task_name=task_name,
            target_name=target_name,
            status=status,
            status_reason=status_reason,
        )

    return _patch


def test_executor_returns_no_pending_task_without_touching_runtime(tmp_path, repo_root):
    scripts_dir = repo_root / 'scripts'
    common = _load_module(scripts_dir / 'mock_wms_db_common.py', 'mock_wms_db_common')
    executor = _load_module(
        scripts_dir / 'run_mock_wms_executor.py',
        'run_mock_wms_executor',
    )

    db_path = tmp_path / 'mock_wms.db'
    common.initialize_database(db_path)
    runtime = FakeRuntime(
        executor,
        executor.ReadyGateResult(ready=True, reason='ready gate satisfied'),
    )

    result = executor.run_executor_once(
        db_path=db_path,
        task_points_path=repo_root / 'config' / 'task_points.yaml',
        runtime=runtime,
    )

    assert result['outcome'] == 'no-pending-task'
    assert result['task_before'] is None
    assert runtime.ready_calls == 0
    assert runtime.navigate_calls == 0


def test_executor_marks_unknown_target_as_failed_without_calling_runtime(
    tmp_path,
    repo_root,
):
    scripts_dir = repo_root / 'scripts'
    common = _load_module(scripts_dir / 'mock_wms_db_common.py', 'mock_wms_db_common')
    executor = _load_module(
        scripts_dir / 'run_mock_wms_executor.py',
        'run_mock_wms_executor',
    )

    db_path = tmp_path / 'mock_wms.db'
    common.initialize_database(db_path)
    timestamp = common.now_timestamp()

    with sqlite3.connect(db_path) as connection:
        connection.execute(
            '''
            INSERT INTO tasks (
                task_name,
                target_name,
                frame_id,
                x,
                y,
                yaw,
                status,
                status_reason,
                created_at,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                'manual-bad-task',
                'unknown_target',
                'map',
                0.0,
                0.0,
                0.0,
                'pending',
                None,
                timestamp,
                timestamp,
            ),
        )
        connection.commit()

    runtime = FakeRuntime(
        executor,
        executor.ReadyGateResult(ready=True, reason='ready gate satisfied'),
    )

    result = executor.run_executor_once(
        db_path=db_path,
        task_points_path=repo_root / 'config' / 'task_points.yaml',
        runtime=runtime,
    )

    assert result['outcome'] == 'invalid-target'
    assert result['task_after']['status'] == 'failed'
    assert 'unknown_target' in result['task_after']['status_reason']
    assert runtime.ready_calls == 0
    assert runtime.navigate_calls == 0


def test_dry_run_keeps_task_pending_when_ready_gate_is_false(tmp_path, repo_root):
    scripts_dir = repo_root / 'scripts'
    common = _load_module(scripts_dir / 'mock_wms_db_common.py', 'mock_wms_db_common')
    executor = _load_module(
        scripts_dir / 'run_mock_wms_executor.py',
        'run_mock_wms_executor',
    )

    db_path = tmp_path / 'mock_wms.db'
    common.create_task('station_a', db_path=db_path, task_points_path=repo_root / 'config' / 'task_points.yaml')
    runtime = FakeRuntime(
        executor,
        executor.ReadyGateResult(
            ready=False,
            reason='/map_server lifecycle state is inactive',
        ),
    )

    result = executor.run_executor_once(
        db_path=db_path,
        task_points_path=repo_root / 'config' / 'task_points.yaml',
        execute=False,
        runtime=runtime,
    )

    assert result['outcome'] == 'ready-gate-not-ready'
    assert result['goal_sent'] is False
    assert result['task_after']['status'] == 'pending'
    assert '/map_server lifecycle state is inactive' in result['task_after']['status_reason']
    assert runtime.ready_calls == 1
    assert runtime.navigate_calls == 0


def test_execute_waits_for_ready_gate_and_succeeds_after_retry(tmp_path, repo_root):
    scripts_dir = repo_root / 'scripts'
    common = _load_module(scripts_dir / 'mock_wms_db_common.py', 'mock_wms_db_common')
    executor = _load_module(
        scripts_dir / 'run_mock_wms_executor.py',
        'run_mock_wms_executor',
    )

    db_path = tmp_path / 'mock_wms.db'
    common.create_task(
        'station_a',
        db_path=db_path,
        task_points_path=repo_root / 'config' / 'task_points.yaml',
    )
    clock = FakeClock()
    runtime = FakeRuntime(
        executor,
        [
            executor.ReadyGateResult(
                ready=False,
                reason='/map_server lifecycle state is unavailable',
            ),
            executor.ReadyGateResult(ready=True, reason='ready gate satisfied'),
        ],
        executor.NavigationResult(
            succeeded=True,
            status='succeeded',
            reason='NavigateToPose result: SUCCEEDED.',
        ),
    )

    result = executor.run_executor_once(
        db_path=db_path,
        task_points_path=repo_root / 'config' / 'task_points.yaml',
        execute=True,
        ready_timeout_sec=10.0,
        ready_poll_interval_sec=2.0,
        runtime=runtime,
        sleep_fn=clock.sleep,
        monotonic_fn=clock.monotonic,
    )

    assert result['outcome'] == 'succeeded'
    assert result['goal_sent'] is True
    assert result['task_running']['status'] == 'running'
    assert result['task_after']['status'] == 'succeeded'
    assert result['ready_wait'].attempts == 2
    assert result['ready_wait'].timed_out is False
    assert runtime.ready_calls == 2
    assert runtime.navigate_calls == 1


def test_execute_timeout_keeps_task_pending_and_records_last_ready_failure(
    tmp_path,
    repo_root,
):
    scripts_dir = repo_root / 'scripts'
    common = _load_module(scripts_dir / 'mock_wms_db_common.py', 'mock_wms_db_common')
    executor = _load_module(
        scripts_dir / 'run_mock_wms_executor.py',
        'run_mock_wms_executor',
    )

    db_path = tmp_path / 'mock_wms.db'
    common.create_task(
        'station_a',
        db_path=db_path,
        task_points_path=repo_root / 'config' / 'task_points.yaml',
    )
    clock = FakeClock()
    runtime = FakeRuntime(
        executor,
        [
            executor.ReadyGateResult(
                ready=False,
                reason='/map_server lifecycle state is unavailable',
            ),
            executor.ReadyGateResult(
                ready=False,
                reason='/amcl lifecycle state is unavailable',
            ),
            executor.ReadyGateResult(
                ready=False,
                reason='/navigate_to_pose action server is unavailable',
            ),
        ],
    )

    result = executor.run_executor_once(
        db_path=db_path,
        task_points_path=repo_root / 'config' / 'task_points.yaml',
        execute=True,
        ready_timeout_sec=4.0,
        ready_poll_interval_sec=2.0,
        runtime=runtime,
        sleep_fn=clock.sleep,
        monotonic_fn=clock.monotonic,
    )

    assert result['outcome'] == 'execute-not-ready-timeout'
    assert result['goal_sent'] is False
    assert result['task_after']['status'] == 'pending'
    assert (
        result['task_after']['status_reason']
        == 'Nav2 ready gate not satisfied: /navigate_to_pose action server is unavailable'
    )
    assert 'did not become ready within 4.0s' in result['message']
    assert result['ready_wait'].attempts == 3
    assert result['ready_wait'].timed_out is True
    assert runtime.ready_calls == 3
    assert runtime.navigate_calls == 0


def test_executor_marks_task_succeeded_after_successful_navigation(tmp_path, repo_root):
    scripts_dir = repo_root / 'scripts'
    common = _load_module(scripts_dir / 'mock_wms_db_common.py', 'mock_wms_db_common')
    executor = _load_module(
        scripts_dir / 'run_mock_wms_executor.py',
        'run_mock_wms_executor',
    )

    db_path = tmp_path / 'mock_wms.db'
    common.create_task('station_b', db_path=db_path, task_points_path=repo_root / 'config' / 'task_points.yaml')
    runtime = FakeRuntime(
        executor,
        executor.ReadyGateResult(ready=True, reason='ready gate satisfied'),
        executor.NavigationResult(
            succeeded=True,
            status='succeeded',
            reason='NavigateToPose result: SUCCEEDED.',
        ),
    )

    result = executor.run_executor_once(
        db_path=db_path,
        task_points_path=repo_root / 'config' / 'task_points.yaml',
        execute=True,
        navigation_timeout_sec=45.0,
        runtime=runtime,
    )

    assert result['outcome'] == 'succeeded'
    assert result['goal_sent'] is True
    assert result['task_after']['status'] == 'succeeded'
    assert result['task_after']['status_reason'] == 'NavigateToPose result: SUCCEEDED.'
    assert runtime.ready_calls == 1
    assert runtime.navigate_calls == 1
    assert runtime.last_pose['frame_id'] == 'map'
    assert runtime.last_timeout == 45.0


def test_executor_marks_task_failed_after_failed_navigation(tmp_path, repo_root):
    scripts_dir = repo_root / 'scripts'
    common = _load_module(scripts_dir / 'mock_wms_db_common.py', 'mock_wms_db_common')
    executor = _load_module(
        scripts_dir / 'run_mock_wms_executor.py',
        'run_mock_wms_executor',
    )

    db_path = tmp_path / 'mock_wms.db'
    common.create_task('shelf_1', db_path=db_path, task_points_path=repo_root / 'config' / 'task_points.yaml')
    runtime = FakeRuntime(
        executor,
        executor.ReadyGateResult(ready=True, reason='ready gate satisfied'),
        executor.NavigationResult(
            succeeded=False,
            status='failed',
            reason='NavigateToPose result: ABORTED.',
        ),
    )

    result = executor.run_executor_once(
        db_path=db_path,
        task_points_path=repo_root / 'config' / 'task_points.yaml',
        execute=True,
        runtime=runtime,
    )

    assert result['outcome'] == 'failed'
    assert result['goal_sent'] is True
    assert result['task_after']['status'] == 'failed'
    assert result['task_after']['status_reason'] == 'NavigateToPose result: ABORTED.'
    assert result['exit_code'] == 1
    assert runtime.ready_calls == 1
    assert runtime.navigate_calls == 1


def test_dry_run_does_not_move_task_into_running(tmp_path, repo_root):
    scripts_dir = repo_root / 'scripts'
    common = _load_module(scripts_dir / 'mock_wms_db_common.py', 'mock_wms_db_common')
    executor = _load_module(
        scripts_dir / 'run_mock_wms_executor.py',
        'run_mock_wms_executor',
    )

    db_path = tmp_path / 'mock_wms.db'
    common.create_task('shelf_2', db_path=db_path, task_points_path=repo_root / 'config' / 'task_points.yaml')
    runtime = FakeRuntime(
        executor,
        executor.ReadyGateResult(ready=True, reason='ready gate satisfied'),
    )

    result = executor.run_executor_once(
        db_path=db_path,
        task_points_path=repo_root / 'config' / 'task_points.yaml',
        execute=False,
        runtime=runtime,
    )

    assert result['outcome'] == 'dry-run-ready'
    assert result['goal_sent'] is False
    assert result['task_after']['status'] == 'pending'
    assert 'Dry-run only' in result['task_after']['status_reason']
    assert runtime.ready_calls == 1
    assert runtime.navigate_calls == 0


def test_http_mode_returns_no_pending_task_without_touching_runtime(tmp_path, repo_root):
    scripts_dir = repo_root / 'scripts'
    executor = _load_module(
        scripts_dir / 'run_mock_wms_executor.py',
        'run_mock_wms_executor',
    )

    runtime = FakeRuntime(
        executor,
        executor.ReadyGateResult(ready=True, reason='ready gate satisfied'),
    )

    result = executor.run_executor_once(
        api_base_url='http://127.0.0.1:8000',
        runtime=runtime,
        fetch_json_fn=lambda url, *, timeout_sec: _http_task_payload(
            _http_task(
                task_id=1,
                task_name='done-task',
                target_name='station_a',
                status='succeeded',
                status_reason='already done',
                updated_at='2026-05-14T10:05:00Z',
            )
        ),
    )

    assert result['outcome'] == 'no-pending-task'
    assert result['task_before'] is None
    assert result['mode'] == 'http-dry-run'
    assert runtime.ready_calls == 0
    assert runtime.navigate_calls == 0


def test_http_mode_fetches_earliest_pending_task_and_simulates_locally(tmp_path, repo_root):
    scripts_dir = repo_root / 'scripts'
    executor = _load_module(
        scripts_dir / 'run_mock_wms_executor.py',
        'run_mock_wms_executor',
    )

    runtime = FakeRuntime(
        executor,
        executor.ReadyGateResult(ready=True, reason='ready gate satisfied'),
    )

    result = executor.run_executor_once(
        api_base_url='http://127.0.0.1:8000/',
        runtime=runtime,
        fetch_json_fn=lambda url, *, timeout_sec: _http_task_payload(
            _http_task(
                task_id=9,
                task_name='latest-pending',
                target_name='station_b',
                status='pending',
                created_at='2026-05-14T11:00:00Z',
                updated_at='2026-05-14T11:00:00Z',
                x=3.0,
                y=4.0,
                yaw=1.57,
            ),
            _http_task(
                task_id=3,
                task_name='earliest-pending',
                target_name='station_a',
                status='pending',
            ),
        ),
        patch_status_fn=lambda api_base_url, task_id, *, status, status_reason, timeout_sec: _http_task(
            task_id=task_id,
            task_name='earliest-pending',
            target_name='station_a',
            status=status,
            status_reason=status_reason,
        ),
    )

    assert result['outcome'] == 'http-task-simulated'
    assert result['task_before']['id'] == 3
    assert result['task_running']['status'] == 'running'
    assert result['task_after']['status'] == 'succeeded'
    assert result['task_after']['status_reason'] == 'HTTP dry-run simulation completed; Nav2 goal not sent.'
    assert result['resolved_target_name'] == 'station_a'
    assert result['resolved_pose'] == {
        'frame_id': 'map',
        'x': 1.0,
        'y': 2.0,
        'yaw': 0.0,
    }
    assert runtime.ready_calls == 0
    assert runtime.navigate_calls == 0


def test_http_mode_reports_api_unreachable(tmp_path, repo_root):
    scripts_dir = repo_root / 'scripts'
    executor = _load_module(
        scripts_dir / 'run_mock_wms_executor.py',
        'run_mock_wms_executor',
    )

    result = executor.run_executor_once(
        api_base_url='http://127.0.0.1:8000',
        fetch_json_fn=lambda url, *, timeout_sec: (_ for _ in ()).throw(
            executor.HttpTaskSourceUnavailableError('mock api is down')
        ),
    )

    assert result['outcome'] == 'api-unreachable'
    assert result['exit_code'] == 1
    assert result['message'] == 'mock api is down'


def test_http_mode_reports_invalid_task_payload(tmp_path, repo_root):
    scripts_dir = repo_root / 'scripts'
    executor = _load_module(
        scripts_dir / 'run_mock_wms_executor.py',
        'run_mock_wms_executor',
    )

    result = executor.run_executor_once(
        api_base_url='http://127.0.0.1:8000',
        fetch_json_fn=lambda url, *, timeout_sec: _http_task_payload(
            _http_task(
                task_id=1,
                task_name='bad-pending',
                target_name='   ',
                status='pending',
            )
        ),
    )

    assert result['outcome'] == 'invalid-task-payload'
    assert result['exit_code'] == 1
    assert 'target_name' in result['message']


def test_http_mode_reports_writeback_failure_after_fetch(repo_root):
    scripts_dir = repo_root / 'scripts'
    executor = _load_module(
        scripts_dir / 'run_mock_wms_executor.py',
        'run_mock_wms_executor',
    )

    result = executor.run_executor_once(
        api_base_url='http://127.0.0.1:8000',
        fetch_json_fn=lambda url, *, timeout_sec: _http_task_payload(
            _http_task(
                task_id=7,
                task_name='pending-http-task',
                target_name='station_a',
                status='pending',
            )
        ),
        patch_status_fn=lambda api_base_url, task_id, *, status, status_reason, timeout_sec: (_ for _ in ()).throw(
            executor.HttpTaskSourceUnavailableError('status patch failed')
        ),
    )

    assert result['outcome'] == 'api-unreachable'
    assert result['task_before']['id'] == 7
    assert result['exit_code'] == 1
    assert 'running status' in result['message']


def test_http_execute_waits_for_ready_gate_and_marks_task_succeeded(repo_root):
    scripts_dir = repo_root / 'scripts'
    executor = _load_module(
        scripts_dir / 'run_mock_wms_executor.py',
        'run_mock_wms_executor',
    )

    clock = FakeClock()
    runtime = FakeRuntime(
        executor,
        [
            executor.ReadyGateResult(
                ready=False,
                reason='/map_server lifecycle state is unavailable',
            ),
            executor.ReadyGateResult(ready=True, reason='ready gate satisfied'),
        ],
        executor.NavigationResult(
            succeeded=True,
            status='succeeded',
            reason='NavigateToPose result: SUCCEEDED.',
        ),
    )
    patch_calls = []

    result = executor.run_executor_once(
        api_base_url='http://127.0.0.1:8000',
        execute=True,
        ready_timeout_sec=10.0,
        ready_poll_interval_sec=2.0,
        navigation_timeout_sec=45.0,
        runtime=runtime,
        fetch_json_fn=lambda url, *, timeout_sec: _http_task_payload(
            _http_task(
                task_id=11,
                task_name='pending-http-task',
                target_name='station_a',
                status='pending',
            )
        ),
        patch_status_fn=_recording_patch_status_fn(patch_calls),
        sleep_fn=clock.sleep,
        monotonic_fn=clock.monotonic,
    )

    assert result['outcome'] == 'succeeded'
    assert result['goal_sent'] is True
    assert result['task_running']['status'] == 'running'
    assert result['task_after']['status'] == 'succeeded'
    assert result['task_after']['status_reason'] == 'NavigateToPose result: SUCCEEDED.'
    assert result['ready_wait'].attempts == 2
    assert result['ready_wait'].timed_out is False
    assert runtime.ready_calls == 2
    assert runtime.navigate_calls == 1
    assert runtime.last_timeout == 45.0
    assert [call['status'] for call in patch_calls] == ['running', 'succeeded']


def test_http_execute_timeout_keeps_task_pending_and_records_last_ready_failure(repo_root):
    scripts_dir = repo_root / 'scripts'
    executor = _load_module(
        scripts_dir / 'run_mock_wms_executor.py',
        'run_mock_wms_executor',
    )

    clock = FakeClock()
    runtime = FakeRuntime(
        executor,
        [
            executor.ReadyGateResult(
                ready=False,
                reason='/map_server lifecycle state is unavailable',
            ),
            executor.ReadyGateResult(
                ready=False,
                reason='/amcl lifecycle state is unavailable',
            ),
            executor.ReadyGateResult(
                ready=False,
                reason='/navigate_to_pose action server is unavailable',
            ),
        ],
    )
    patch_calls = []

    result = executor.run_executor_once(
        api_base_url='http://127.0.0.1:8000',
        execute=True,
        ready_timeout_sec=4.0,
        ready_poll_interval_sec=2.0,
        runtime=runtime,
        fetch_json_fn=lambda url, *, timeout_sec: _http_task_payload(
            _http_task(
                task_id=12,
                task_name='pending-http-task',
                target_name='station_a',
                status='pending',
            )
        ),
        patch_status_fn=_recording_patch_status_fn(patch_calls),
        sleep_fn=clock.sleep,
        monotonic_fn=clock.monotonic,
    )

    assert result['outcome'] == 'execute-not-ready-timeout'
    assert result['goal_sent'] is False
    assert result['task_after']['status'] == 'pending'
    assert (
        result['task_after']['status_reason']
        == 'Nav2 ready gate not satisfied: /navigate_to_pose action server is unavailable'
    )
    assert 'did not become ready within 4.0s' in result['message']
    assert result['ready_wait'].attempts == 3
    assert result['ready_wait'].timed_out is True
    assert runtime.ready_calls == 3
    assert runtime.navigate_calls == 0
    assert [call['status'] for call in patch_calls] == ['pending']


def test_http_execute_failed_navigation_writes_failed_status(repo_root):
    scripts_dir = repo_root / 'scripts'
    executor = _load_module(
        scripts_dir / 'run_mock_wms_executor.py',
        'run_mock_wms_executor',
    )

    runtime = FakeRuntime(
        executor,
        executor.ReadyGateResult(ready=True, reason='ready gate satisfied'),
        executor.NavigationResult(
            succeeded=False,
            status='failed',
            reason='NavigateToPose result: ABORTED.',
        ),
    )
    patch_calls = []

    result = executor.run_executor_once(
        api_base_url='http://127.0.0.1:8000',
        execute=True,
        runtime=runtime,
        fetch_json_fn=lambda url, *, timeout_sec: _http_task_payload(
            _http_task(
                task_id=13,
                task_name='pending-http-task',
                target_name='station_b',
                status='pending',
                x=3.0,
                y=4.0,
                yaw=1.57,
            )
        ),
        patch_status_fn=_recording_patch_status_fn(
            patch_calls,
            target_name='station_b',
        ),
    )

    assert result['outcome'] == 'failed'
    assert result['goal_sent'] is True
    assert result['task_after']['status'] == 'failed'
    assert result['task_after']['status_reason'] == 'NavigateToPose result: ABORTED.'
    assert result['exit_code'] == 1
    assert runtime.ready_calls == 1
    assert runtime.navigate_calls == 1
    assert [call['status'] for call in patch_calls] == ['running', 'failed']


def test_fetch_http_json_bypasses_proxy_for_loopback_url(repo_root, monkeypatch):
    scripts_dir = repo_root / 'scripts'
    executor = _load_module(
        scripts_dir / 'run_mock_wms_executor.py',
        'run_mock_wms_executor',
    )

    calls = {}

    class FakeOpener:
        def open(self, url, *, timeout):
            calls['open'] = (url, timeout)
            return FakeHttpResponse('{"count": 0, "tasks": []}')

    def fake_build_opener(proxy_handler):
        calls['proxy_handler'] = proxy_handler
        return FakeOpener()

    def fake_urlopen(url, *, timeout):
        raise AssertionError('loopback URL should bypass urlopen proxy path')

    monkeypatch.setattr(executor, 'build_opener', fake_build_opener)
    monkeypatch.setattr(executor, 'urlopen', fake_urlopen)

    payload = executor.fetch_http_json('http://127.0.0.1:8000/tasks')

    assert payload == {'count': 0, 'tasks': []}
    assert calls['open'][0] == 'http://127.0.0.1:8000/tasks'


def test_fetch_http_json_keeps_default_urlopen_for_non_loopback_url(repo_root, monkeypatch):
    scripts_dir = repo_root / 'scripts'
    executor = _load_module(
        scripts_dir / 'run_mock_wms_executor.py',
        'run_mock_wms_executor',
    )

    calls = {}

    def fake_build_opener(proxy_handler):
        raise AssertionError('non-loopback URL should keep default urlopen path')

    def fake_urlopen(url, *, timeout):
        calls['urlopen'] = (url, timeout)
        return FakeHttpResponse('{"count": 1, "tasks": []}')

    monkeypatch.setattr(executor, 'build_opener', fake_build_opener)
    monkeypatch.setattr(executor, 'urlopen', fake_urlopen)

    payload = executor.fetch_http_json('http://example.com/tasks')

    assert payload == {'count': 1, 'tasks': []}
    assert calls['urlopen'][0] == 'http://example.com/tasks'

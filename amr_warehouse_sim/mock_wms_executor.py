from __future__ import annotations

import argparse
import ipaddress
import json
import math
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import ProxyHandler, Request, build_opener, urlopen

from .mock_wms_db_common import (
    TASK_STATUSES,
    default_db_path,
    default_task_points_path,
    get_next_pending_task,
    initialize_database,
    resolve_target_pose,
    update_task_status,
)

DEFAULT_ACTION_NAME = '/navigate_to_pose'
DEFAULT_READY_GATE_TIMEOUT_SEC = 2.0
DEFAULT_READY_TIMEOUT_SEC = 60.0
DEFAULT_READY_POLL_INTERVAL_SEC = 2.0
DEFAULT_NAVIGATION_TIMEOUT_SEC = 180.0
DEFAULT_HTTP_TIMEOUT_SEC = 5.0
REQUIRED_LIFECYCLE_NODES = (
    '/map_server',
    '/amcl',
    '/planner_server',
    '/controller_server',
    '/bt_navigator',
)


@dataclass(frozen=True)
class ReadyGateResult:
    ready: bool
    reason: str
    details: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class NavigationResult:
    succeeded: bool
    status: str
    reason: str


@dataclass(frozen=True)
class ReadyWaitResult:
    ready_gate: ReadyGateResult
    attempts: int
    elapsed_sec: float
    timed_out: bool


class ExecutorRuntime(Protocol):
    def check_ready_gate(self) -> ReadyGateResult:
        ...

    def navigate_to_pose(
        self,
        pose: dict[str, object],
        *,
        timeout_sec: float,
    ) -> NavigationResult:
        ...

    def close(self) -> None:
        ...


class HttpTaskSourceUnavailableError(RuntimeError):
    pass


class InvalidHttpTaskPayloadError(RuntimeError):
    pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            'Run the minimal V3.1 Mock WMS executor. '
            'Dry-run is the default; use --execute to send NavigateToPose goals.'
        )
    )
    parser.add_argument(
        '--db',
        '--db-path',
        type=Path,
        default=default_db_path(),
        dest='db_path',
        help='SQLite database path. Defaults to data/mock_wms.db under the repo root.',
    )
    parser.add_argument(
        '--task-points',
        type=Path,
        default=default_task_points_path(),
        help='Task point YAML path. Defaults to config/task_points.yaml under the repo root.',
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
        help='Actually send a NavigateToPose goal after the ready gate succeeds.',
    )
    parser.add_argument(
        '--action-name',
        default=DEFAULT_ACTION_NAME,
        help=f'NavigateToPose action name. Defaults to {DEFAULT_ACTION_NAME}.',
    )
    parser.add_argument(
        '--ready-gate-timeout',
        type=float,
        default=DEFAULT_READY_GATE_TIMEOUT_SEC,
        help='Seconds to wait for each ready-gate check before marking it unavailable.',
    )
    parser.add_argument(
        '--ready-timeout',
        type=float,
        default=DEFAULT_READY_TIMEOUT_SEC,
        help='Seconds to wait for execute-mode ready gate success before giving up.',
    )
    parser.add_argument(
        '--ready-poll-interval',
        type=float,
        default=DEFAULT_READY_POLL_INTERVAL_SEC,
        help='Seconds to wait between execute-mode ready gate checks.',
    )
    parser.add_argument(
        '--navigation-timeout',
        type=float,
        default=DEFAULT_NAVIGATION_TIMEOUT_SEC,
        help='Seconds to wait for a NavigateToPose result in execute mode.',
    )
    parser.add_argument(
        '--api-base-url',
        default=os.environ.get('MOCK_WMS_API_BASE_URL'),
        help=(
            'Optional Mock WMS HTTP API base URL for V3.2 HTTP task polling and '
            'status writeback, for example http://127.0.0.1:8000. When set, the '
            'executor consumes tasks over HTTP and writes status updates back over HTTP.'
        ),
    )
    parser.add_argument(
        '--http-timeout',
        type=float,
        default=DEFAULT_HTTP_TIMEOUT_SEC,
        help='Seconds to wait for V3.2 HTTP requests before treating the API as unreachable.',
    )
    return parser


def _build_tasks_endpoint(api_base_url: str) -> str:
    normalized = api_base_url.strip().rstrip('/')
    return f'{normalized}/tasks'


def _request_url(request_or_url: str | Request) -> str:
    if isinstance(request_or_url, Request):
        return str(request_or_url.full_url)
    return request_or_url


def _url_targets_loopback_host(url_or_request: str | Request) -> bool:
    hostname = urlparse(_request_url(url_or_request)).hostname
    if hostname is None:
        return False
    if hostname == 'localhost':
        return True

    try:
        return ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        return False


def _open_http_url(
    url_or_request: str | Request,
    *,
    timeout_sec: float = DEFAULT_HTTP_TIMEOUT_SEC,
):
    timeout = max(timeout_sec, 0.1)
    if _url_targets_loopback_host(url_or_request):
        # Local API calls should not be routed through ambient shell proxies.
        return build_opener(ProxyHandler({})).open(url_or_request, timeout=timeout)
    return urlopen(url_or_request, timeout=timeout)


def fetch_http_json(url: str, *, timeout_sec: float = DEFAULT_HTTP_TIMEOUT_SEC) -> object:
    try:
        with _open_http_url(url, timeout_sec=timeout_sec) as response:
            body = response.read().decode('utf-8')
    except HTTPError as exc:
        raise HttpTaskSourceUnavailableError(
            f'HTTP {exc.code} while requesting {url}.'
        ) from exc
    except URLError as exc:
        raise HttpTaskSourceUnavailableError(
            f'Could not reach {url}: {exc.reason}.'
        ) from exc
    except OSError as exc:
        raise HttpTaskSourceUnavailableError(
            f'Could not reach {url}: {exc}.'
        ) from exc

    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise InvalidHttpTaskPayloadError(
            f'HTTP response from {url} was not valid JSON.'
        ) from exc


def patch_http_json(
    url: str,
    payload: dict[str, object],
    *,
    timeout_sec: float = DEFAULT_HTTP_TIMEOUT_SEC,
) -> object:
    request = Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='PATCH',
    )
    try:
        with _open_http_url(request, timeout_sec=timeout_sec) as response:
            body = response.read().decode('utf-8')
    except HTTPError as exc:
        raise HttpTaskSourceUnavailableError(
            f'HTTP {exc.code} while requesting {url}.'
        ) from exc
    except URLError as exc:
        raise HttpTaskSourceUnavailableError(
            f'Could not reach {url}: {exc.reason}.'
        ) from exc
    except OSError as exc:
        raise HttpTaskSourceUnavailableError(
            f'Could not reach {url}: {exc}.'
        ) from exc

    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise InvalidHttpTaskPayloadError(
            f'HTTP response from {url} was not valid JSON.'
        ) from exc


def _coerce_http_task(
    task: object,
    *,
    expected_status: str | None = None,
) -> dict[str, object]:
    if not isinstance(task, dict):
        raise InvalidHttpTaskPayloadError('Task entries returned by HTTP must be JSON objects.')

    raw_task_id = task.get('id')
    if not isinstance(raw_task_id, int):
        raise InvalidHttpTaskPayloadError('HTTP task payload field "id" must be an integer.')

    raw_task_name = task.get('task_name')
    if not isinstance(raw_task_name, str) or not raw_task_name.strip():
        raise InvalidHttpTaskPayloadError(
            'HTTP task payload field "task_name" must be a non-blank string.'
        )

    raw_target_name = task.get('target_name')
    if not isinstance(raw_target_name, str) or not raw_target_name.strip():
        raise InvalidHttpTaskPayloadError(
            'HTTP task payload field "target_name" must be a non-blank string.'
        )

    raw_status = task.get('status')
    if raw_status not in TASK_STATUSES:
        raise InvalidHttpTaskPayloadError(
            'HTTP task payload field "status" must be one of the supported task states.'
        )
    if expected_status is not None and raw_status != expected_status:
        raise InvalidHttpTaskPayloadError(
            f'HTTP task payload must use status "{expected_status}".'
        )

    raw_frame_id = task.get('frame_id')
    if raw_frame_id != 'map':
        raise InvalidHttpTaskPayloadError(
            'HTTP pending-task payload must use frame_id "map".'
        )

    raw_created_at = task.get('created_at')
    if not isinstance(raw_created_at, str) or not raw_created_at.strip():
        raise InvalidHttpTaskPayloadError(
            'HTTP task payload field "created_at" must be a non-blank string.'
        )

    raw_updated_at = task.get('updated_at')
    if not isinstance(raw_updated_at, str) or not raw_updated_at.strip():
        raise InvalidHttpTaskPayloadError(
            'HTTP task payload field "updated_at" must be a non-blank string.'
        )

    raw_status_reason = task.get('status_reason')
    if raw_status_reason is not None and not isinstance(raw_status_reason, str):
        raise InvalidHttpTaskPayloadError(
            'HTTP task payload field "status_reason" must be a string or null.'
        )

    normalized_task = dict(task)
    normalized_task['task_name'] = raw_task_name.strip()
    normalized_task['target_name'] = raw_target_name.strip()
    normalized_task['frame_id'] = raw_frame_id
    normalized_task['created_at'] = raw_created_at.strip()
    normalized_task['updated_at'] = raw_updated_at.strip()

    for field_name in ('x', 'y', 'yaw'):
        value = normalized_task.get(field_name)
        if not isinstance(value, (int, float)):
            raise InvalidHttpTaskPayloadError(
                f'HTTP task payload field "{field_name}" must be numeric.'
            )
        normalized_task[field_name] = float(value)

    return normalized_task


def get_next_pending_task_via_http(
    api_base_url: str,
    *,
    timeout_sec: float = DEFAULT_HTTP_TIMEOUT_SEC,
    fetch_json_fn=fetch_http_json,
) -> dict[str, object] | None:
    payload = fetch_json_fn(
        _build_tasks_endpoint(api_base_url),
        timeout_sec=timeout_sec,
    )
    if not isinstance(payload, dict):
        raise InvalidHttpTaskPayloadError(
            'HTTP /tasks payload must be a JSON object.'
        )

    tasks = payload.get('tasks')
    if not isinstance(tasks, list):
        raise InvalidHttpTaskPayloadError(
            'HTTP /tasks payload must include a "tasks" list.'
        )

    pending_tasks: list[dict[str, object]] = []
    for task in tasks:
        if not isinstance(task, dict):
            raise InvalidHttpTaskPayloadError(
                'Task entries returned by HTTP must be JSON objects.'
            )
        raw_status = task.get('status')
        if not isinstance(raw_status, str) or raw_status not in TASK_STATUSES:
            raise InvalidHttpTaskPayloadError(
                'HTTP task payload field "status" must be one of the supported task states.'
            )
        if raw_status == 'pending':
            pending_tasks.append(_coerce_http_task(task, expected_status='pending'))

    if not pending_tasks:
        return None

    pending_tasks.sort(key=lambda task: (str(task['created_at']), int(task['id'])))
    return pending_tasks[0]


def _build_task_status_endpoint(api_base_url: str, task_id: int) -> str:
    normalized = api_base_url.strip().rstrip('/')
    return f'{normalized}/tasks/{task_id}/status'


def update_task_status_via_http(
    api_base_url: str,
    task_id: int,
    *,
    status: str,
    status_reason: str | None = None,
    timeout_sec: float = DEFAULT_HTTP_TIMEOUT_SEC,
    patch_json_fn=patch_http_json,
) -> dict[str, object]:
    payload: dict[str, object] = {'status': status}
    if status_reason is not None:
        payload['status_reason'] = status_reason

    response_payload = patch_json_fn(
        _build_task_status_endpoint(api_base_url, task_id),
        payload,
        timeout_sec=timeout_sec,
    )
    return _coerce_http_task(response_payload, expected_status=status)


def _update_http_task_status_or_fail(
    result: dict[str, object],
    *,
    api_base_url: str,
    task_id: int,
    status: str,
    status_reason: str,
    http_timeout_sec: float,
    patch_status_fn,
    unavailable_message: str,
    invalid_payload_message: str,
) -> dict[str, object] | None:
    try:
        return patch_status_fn(
            api_base_url,
            task_id,
            status=status,
            status_reason=status_reason,
            timeout_sec=http_timeout_sec,
        )
    except HttpTaskSourceUnavailableError as exc:
        result['outcome'] = 'api-unreachable'
        result['message'] = f'{unavailable_message}: {exc}'
        result['exit_code'] = 1
        return None
    except InvalidHttpTaskPayloadError as exc:
        result['outcome'] = 'invalid-task-payload'
        result['message'] = f'{invalid_payload_message}: {exc}'
        result['exit_code'] = 1
        return None


def run_http_executor_once(
    *,
    api_base_url: str,
    execute: bool = False,
    http_timeout_sec: float = DEFAULT_HTTP_TIMEOUT_SEC,
    action_name: str = DEFAULT_ACTION_NAME,
    ready_gate_timeout_sec: float = DEFAULT_READY_GATE_TIMEOUT_SEC,
    ready_timeout_sec: float = DEFAULT_READY_TIMEOUT_SEC,
    ready_poll_interval_sec: float = DEFAULT_READY_POLL_INTERVAL_SEC,
    navigation_timeout_sec: float = DEFAULT_NAVIGATION_TIMEOUT_SEC,
    runtime: ExecutorRuntime | None = None,
    fetch_json_fn=fetch_http_json,
    patch_status_fn=update_task_status_via_http,
    sleep_fn=time.sleep,
    monotonic_fn=time.monotonic,
) -> dict[str, object]:
    result: dict[str, object] = {
        'mode': 'http-execute' if execute else 'http-dry-run',
        'task_source': 'http',
        'api_base_url': api_base_url,
        'task_before': None,
        'task_after': None,
        'goal_sent': False,
        'exit_code': 0,
    }

    try:
        task = get_next_pending_task_via_http(
            api_base_url,
            timeout_sec=http_timeout_sec,
            fetch_json_fn=fetch_json_fn,
        )
    except HttpTaskSourceUnavailableError as exc:
        result['outcome'] = 'api-unreachable'
        result['message'] = str(exc)
        result['exit_code'] = 1
        return result
    except InvalidHttpTaskPayloadError as exc:
        result['outcome'] = 'invalid-task-payload'
        result['message'] = str(exc)
        result['exit_code'] = 1
        return result

    result['task_before'] = task
    if task is None:
        result['outcome'] = 'no-pending-task'
        result['message'] = 'No pending tasks found via HTTP.'
        return result

    result['resolved_target_name'] = str(task['target_name'])
    result['resolved_pose'] = {
        'frame_id': str(task['frame_id']),
        'x': float(task['x']),
        'y': float(task['y']),
        'yaw': float(task['yaw']),
    }

    task_id = int(task['id'])

    if not execute:
        running_task = _update_http_task_status_or_fail(
            result,
            api_base_url=api_base_url,
            task_id=task_id,
            status='running',
            status_reason='HTTP executor claimed task for local simulation.',
            http_timeout_sec=http_timeout_sec,
            patch_status_fn=patch_status_fn,
            unavailable_message='Failed to write running status via HTTP',
            invalid_payload_message='Invalid running-status response from HTTP API',
        )
        if running_task is None:
            return result

        result['task_running'] = running_task

        updated_task = _update_http_task_status_or_fail(
            result,
            api_base_url=api_base_url,
            task_id=task_id,
            status='succeeded',
            status_reason='HTTP dry-run simulation completed; Nav2 goal not sent.',
            http_timeout_sec=http_timeout_sec,
            patch_status_fn=patch_status_fn,
            unavailable_message='Failed to write succeeded status via HTTP',
            invalid_payload_message='Invalid succeeded-status response from HTTP API',
        )
        if updated_task is None:
            return result

        result['task_after'] = updated_task
        result['outcome'] = 'http-task-simulated'
        result['message'] = (
            'Fetched the earliest pending task via HTTP, wrote running -> succeeded, '
            'and simulated local handling only.'
        )
        return result

    owns_runtime = False
    runtime_instance = runtime
    if runtime_instance is None:
        runtime_instance = RosNav2Runtime(
            action_name=action_name,
            ready_gate_timeout_sec=ready_gate_timeout_sec,
        )
        owns_runtime = True

    try:
        ready_wait = wait_for_execute_ready_gate(
            runtime_instance,
            ready_timeout_sec=ready_timeout_sec,
            ready_poll_interval_sec=ready_poll_interval_sec,
            sleep_fn=sleep_fn,
            monotonic_fn=monotonic_fn,
        )
        ready_gate = ready_wait.ready_gate
        result['ready_wait'] = ready_wait
        result['ready_gate'] = ready_gate

        if not ready_gate.ready:
            reason = f'Nav2 ready gate not satisfied: {ready_gate.reason}'
            updated_task = _update_http_task_status_or_fail(
                result,
                api_base_url=api_base_url,
                task_id=task_id,
                status='pending',
                status_reason=reason,
                http_timeout_sec=http_timeout_sec,
                patch_status_fn=patch_status_fn,
                unavailable_message='Failed to write pending status via HTTP',
                invalid_payload_message='Invalid pending-status response from HTTP API',
            )
            if updated_task is None:
                return result

            result['task_after'] = updated_task
            result['outcome'] = 'execute-not-ready-timeout'
            result['message'] = (
                f'Nav2 ready gate did not become ready within '
                f'{max(ready_timeout_sec, 0.0):.1f}s. Last failure: {ready_gate.reason}'
            )
            return result

        running_task = _update_http_task_status_or_fail(
            result,
            api_base_url=api_base_url,
            task_id=task_id,
            status='running',
            status_reason='Ready gate satisfied; NavigateToPose goal dispatched.',
            http_timeout_sec=http_timeout_sec,
            patch_status_fn=patch_status_fn,
            unavailable_message='Failed to write running status via HTTP',
            invalid_payload_message='Invalid running-status response from HTTP API',
        )
        if running_task is None:
            return result

        result['goal_sent'] = True
        result['task_running'] = running_task

        navigation_result = runtime_instance.navigate_to_pose(
            result['resolved_pose'],
            timeout_sec=navigation_timeout_sec,
        )
        result['navigation_result'] = navigation_result

        final_status = 'succeeded' if navigation_result.succeeded else 'failed'
        updated_task = _update_http_task_status_or_fail(
            result,
            api_base_url=api_base_url,
            task_id=task_id,
            status=final_status,
            status_reason=navigation_result.reason,
            http_timeout_sec=http_timeout_sec,
            patch_status_fn=patch_status_fn,
            unavailable_message=f'Failed to write {final_status} status via HTTP',
            invalid_payload_message=f'Invalid {final_status}-status response from HTTP API',
        )
        if updated_task is None:
            return result

        result['task_after'] = updated_task
        result['outcome'] = final_status
        result['message'] = navigation_result.reason
        if not navigation_result.succeeded:
            result['exit_code'] = 1
        return result
    finally:
        if owns_runtime:
            runtime_instance.close()


def quaternion_from_yaw(yaw: float) -> tuple[float, float, float, float]:
    half_yaw = yaw / 2.0
    return (
        0.0,
        0.0,
        math.sin(half_yaw),
        math.cos(half_yaw),
    )


class RosNav2Runtime:
    def __init__(
        self,
        *,
        action_name: str,
        ready_gate_timeout_sec: float,
    ):
        ros_log_dir = Path(os.environ.get('ROS_LOG_DIR', '/tmp/amr_warehouse_sim_ros_logs'))
        ros_log_dir.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault('ROS_LOG_DIR', str(ros_log_dir))

        import rclpy
        from action_msgs.msg import GoalStatus
        from lifecycle_msgs.srv import GetState
        from nav2_msgs.action import NavigateToPose
        from rclpy.action import ActionClient
        from rclpy.node import Node
        from rclpy.time import Time
        from tf2_ros import Buffer, TransformListener

        self._rclpy = rclpy
        self._goal_status = GoalStatus
        self._get_state_service = GetState
        self._navigate_to_pose = NavigateToPose
        self._action_client_cls = ActionClient
        self._time_cls = Time
        self._buffer_cls = Buffer
        self._transform_listener_cls = TransformListener
        self._action_name = action_name
        self._ready_gate_timeout_sec = max(ready_gate_timeout_sec, 0.0)
        self._initialized_here = False

        if not self._rclpy.ok():
            self._rclpy.init(args=None)
            self._initialized_here = True

        self._node = Node('mock_wms_executor')
        self._tf_buffer = self._buffer_cls()
        self._tf_listener = self._transform_listener_cls(
            self._tf_buffer,
            self._node,
            spin_thread=False,
        )
        self._navigate_client = self._action_client_cls(
            self._node,
            self._navigate_to_pose,
            self._action_name,
        )

    def _get_lifecycle_state(self, node_name: str) -> str:
        client = self._node.create_client(
            self._get_state_service,
            f'{node_name}/get_state',
        )
        if not client.wait_for_service(timeout_sec=self._ready_gate_timeout_sec):
            return 'unavailable'

        future = client.call_async(self._get_state_service.Request())
        self._rclpy.spin_until_future_complete(
            self._node,
            future,
            timeout_sec=self._ready_gate_timeout_sec,
        )
        if not future.done():
            return 'timeout'

        response = future.result()
        if response is None:
            return 'unknown'

        return str(response.current_state.label or response.current_state.id)

    def _map_to_odom_available(self) -> bool:
        deadline = time.monotonic() + self._ready_gate_timeout_sec
        while time.monotonic() <= deadline:
            self._rclpy.spin_once(self._node, timeout_sec=0.1)
            if self._tf_buffer.can_transform(
                'map',
                'odom',
                self._time_cls(),
            ):
                return True
        return False

    def check_ready_gate(self) -> ReadyGateResult:
        lifecycle_states: dict[str, str] = {}
        for node_name in REQUIRED_LIFECYCLE_NODES:
            state = self._get_lifecycle_state(node_name)
            lifecycle_states[node_name] = state
            if state != 'active':
                return ReadyGateResult(
                    ready=False,
                    reason=f'{node_name} lifecycle state is {state}',
                    details={'lifecycle_states': lifecycle_states},
                )

        if not self._map_to_odom_available():
            return ReadyGateResult(
                ready=False,
                reason='map -> odom transform is unavailable',
                details={'lifecycle_states': lifecycle_states},
            )

        if not self._navigate_client.wait_for_server(timeout_sec=self._ready_gate_timeout_sec):
            return ReadyGateResult(
                ready=False,
                reason=f'{self._action_name} action server is unavailable',
                details={'lifecycle_states': lifecycle_states},
            )

        return ReadyGateResult(
            ready=True,
            reason='ready gate satisfied',
            details={
                'lifecycle_states': lifecycle_states,
                'transform_available': True,
                'action_server_available': True,
                'action_name': self._action_name,
            },
        )

    def navigate_to_pose(
        self,
        pose: dict[str, object],
        *,
        timeout_sec: float,
    ) -> NavigationResult:
        goal_msg = self._navigate_to_pose.Goal()
        goal_msg.pose.header.frame_id = str(pose['frame_id'])
        goal_msg.pose.header.stamp = self._node.get_clock().now().to_msg()
        goal_msg.pose.pose.position.x = float(pose['x'])
        goal_msg.pose.pose.position.y = float(pose['y'])
        goal_msg.pose.pose.position.z = 0.0

        qx, qy, qz, qw = quaternion_from_yaw(float(pose['yaw']))
        goal_msg.pose.pose.orientation.x = qx
        goal_msg.pose.pose.orientation.y = qy
        goal_msg.pose.pose.orientation.z = qz
        goal_msg.pose.pose.orientation.w = qw

        send_future = self._navigate_client.send_goal_async(goal_msg)
        self._rclpy.spin_until_future_complete(
            self._node,
            send_future,
            timeout_sec=self._ready_gate_timeout_sec,
        )
        if not send_future.done():
            return NavigationResult(
                succeeded=False,
                status='failed',
                reason='NavigateToPose goal dispatch timed out before acceptance.',
            )

        goal_handle = send_future.result()
        if goal_handle is None or not goal_handle.accepted:
            return NavigationResult(
                succeeded=False,
                status='failed',
                reason='NavigateToPose goal was rejected.',
            )

        result_future = goal_handle.get_result_async()
        self._rclpy.spin_until_future_complete(
            self._node,
            result_future,
            timeout_sec=max(timeout_sec, 0.0),
        )
        if not result_future.done():
            cancel_future = goal_handle.cancel_goal_async()
            self._rclpy.spin_until_future_complete(
                self._node,
                cancel_future,
                timeout_sec=self._ready_gate_timeout_sec,
            )
            return NavigationResult(
                succeeded=False,
                status='failed',
                reason=f'NavigateToPose timed out after {timeout_sec:.1f}s.',
            )

        result = result_future.result()
        status_code = None if result is None else result.status

        if status_code == self._goal_status.STATUS_SUCCEEDED:
            return NavigationResult(
                succeeded=True,
                status='succeeded',
                reason='NavigateToPose result: SUCCEEDED.',
            )
        if status_code == self._goal_status.STATUS_ABORTED:
            return NavigationResult(
                succeeded=False,
                status='failed',
                reason='NavigateToPose result: ABORTED.',
            )
        if status_code == self._goal_status.STATUS_CANCELED:
            return NavigationResult(
                succeeded=False,
                status='failed',
                reason='NavigateToPose result: CANCELED.',
            )

        return NavigationResult(
            succeeded=False,
            status='failed',
            reason=f'NavigateToPose result status code: {status_code}.',
        )

    def close(self) -> None:
        self._node.destroy_node()
        if self._initialized_here and self._rclpy.ok():
            self._rclpy.shutdown()


def wait_for_execute_ready_gate(
    runtime: ExecutorRuntime,
    *,
    ready_timeout_sec: float,
    ready_poll_interval_sec: float,
    sleep_fn=time.sleep,
    monotonic_fn=time.monotonic,
) -> ReadyWaitResult:
    start_time = monotonic_fn()
    ready_gate = runtime.check_ready_gate()
    attempts = 1

    if ready_gate.ready:
        return ReadyWaitResult(
            ready_gate=ready_gate,
            attempts=attempts,
            elapsed_sec=max(monotonic_fn() - start_time, 0.0),
            timed_out=False,
        )

    deadline = start_time + max(ready_timeout_sec, 0.0)
    poll_interval_sec = max(ready_poll_interval_sec, 0.0)

    while monotonic_fn() < deadline:
        remaining_sec = deadline - monotonic_fn()
        if remaining_sec <= 0.0:
            break

        if poll_interval_sec > 0.0:
            sleep_fn(min(poll_interval_sec, remaining_sec))
        else:
            sleep_fn(remaining_sec)

        ready_gate = runtime.check_ready_gate()
        attempts += 1
        if ready_gate.ready:
            return ReadyWaitResult(
                ready_gate=ready_gate,
                attempts=attempts,
                elapsed_sec=max(monotonic_fn() - start_time, 0.0),
                timed_out=False,
            )

    return ReadyWaitResult(
        ready_gate=ready_gate,
        attempts=attempts,
        elapsed_sec=max(monotonic_fn() - start_time, 0.0),
        timed_out=not ready_gate.ready,
    )


def run_executor_once(
    *,
    db_path: Path | None = None,
    task_points_path: Path | None = None,
    execute: bool = False,
    action_name: str = DEFAULT_ACTION_NAME,
    ready_gate_timeout_sec: float = DEFAULT_READY_GATE_TIMEOUT_SEC,
    ready_timeout_sec: float = DEFAULT_READY_TIMEOUT_SEC,
    ready_poll_interval_sec: float = DEFAULT_READY_POLL_INTERVAL_SEC,
    navigation_timeout_sec: float = DEFAULT_NAVIGATION_TIMEOUT_SEC,
    api_base_url: str | None = None,
    http_timeout_sec: float = DEFAULT_HTTP_TIMEOUT_SEC,
    runtime: ExecutorRuntime | None = None,
    fetch_json_fn=fetch_http_json,
    patch_status_fn=update_task_status_via_http,
    sleep_fn=time.sleep,
    monotonic_fn=time.monotonic,
) -> dict[str, object]:
    if api_base_url:
        return run_http_executor_once(
            api_base_url=api_base_url,
            execute=execute,
            http_timeout_sec=http_timeout_sec,
            action_name=action_name,
            ready_gate_timeout_sec=ready_gate_timeout_sec,
            ready_timeout_sec=ready_timeout_sec,
            ready_poll_interval_sec=ready_poll_interval_sec,
            navigation_timeout_sec=navigation_timeout_sec,
            runtime=runtime,
            fetch_json_fn=fetch_json_fn,
            patch_status_fn=patch_status_fn,
            sleep_fn=sleep_fn,
            monotonic_fn=monotonic_fn,
        )

    db_file = initialize_database(db_path)
    task = get_next_pending_task(db_file)

    result: dict[str, object] = {
        'mode': 'execute' if execute else 'dry-run',
        'db_path': str(db_file),
        'task_before': task,
        'task_after': None,
        'goal_sent': False,
        'exit_code': 0,
    }

    if task is None:
        result['outcome'] = 'no-pending-task'
        result['message'] = 'No pending tasks found.'
        return result

    try:
        resolved_target_name, pose = resolve_target_pose(
            str(task['target_name']),
            task_points_path,
        )
    except (KeyError, ValueError) as exc:
        reason = f'Target resolution failed: {exc}'
        updated_task = update_task_status(
            int(task['id']),
            status='failed',
            db_path=db_file,
            status_reason=reason,
        )
        result['outcome'] = 'invalid-target'
        result['task_after'] = updated_task
        result['message'] = reason
        result['exit_code'] = 1
        return result

    result['resolved_target_name'] = resolved_target_name
    result['resolved_pose'] = pose

    owns_runtime = False
    runtime_instance = runtime
    if runtime_instance is None:
        runtime_instance = RosNav2Runtime(
            action_name=action_name,
            ready_gate_timeout_sec=ready_gate_timeout_sec,
        )
        owns_runtime = True

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
            reason = f'Nav2 ready gate not satisfied: {ready_gate.reason}'
            updated_task = update_task_status(
                int(task['id']),
                status='pending',
                db_path=db_file,
                status_reason=reason,
            )
            result['task_after'] = updated_task
            if execute:
                timeout_reason = (
                    f'Nav2 ready gate did not become ready within '
                    f'{max(ready_timeout_sec, 0.0):.1f}s. Last failure: {ready_gate.reason}'
                )
                result['outcome'] = 'execute-not-ready-timeout'
                result['message'] = timeout_reason
            else:
                result['outcome'] = 'ready-gate-not-ready'
                result['message'] = reason
            return result

        if not execute:
            reason = 'Dry-run only: ready gate satisfied; NavigateToPose goal not sent.'
            updated_task = update_task_status(
                int(task['id']),
                status='pending',
                db_path=db_file,
                status_reason=reason,
            )
            result['outcome'] = 'dry-run-ready'
            result['task_after'] = updated_task
            result['message'] = reason
            return result

        running_task = update_task_status(
            int(task['id']),
            status='running',
            db_path=db_file,
            status_reason='Ready gate satisfied; NavigateToPose goal dispatched.',
        )
        result['goal_sent'] = True
        result['task_running'] = running_task

        navigation_result = runtime_instance.navigate_to_pose(
            pose,
            timeout_sec=navigation_timeout_sec,
        )
        result['navigation_result'] = navigation_result

        final_status = 'succeeded' if navigation_result.succeeded else 'failed'
        updated_task = update_task_status(
            int(task['id']),
            status=final_status,
            db_path=db_file,
            status_reason=navigation_result.reason,
        )
        result['task_after'] = updated_task
        result['outcome'] = final_status
        result['message'] = navigation_result.reason
        if not navigation_result.succeeded:
            result['exit_code'] = 1
        return result
    finally:
        if owns_runtime:
            runtime_instance.close()


def format_result_message(result: dict[str, object]) -> str:
    task_before = result.get('task_before')
    task_id = 'n/a'
    target_name = 'n/a'
    if isinstance(task_before, dict):
        task_id = str(task_before.get('id', 'n/a'))
        target_name = str(task_before.get('target_name', 'n/a'))

    outcome = result.get('outcome', 'unknown')
    message = result.get('message', '')
    return (
        f'[mock_wms_executor] outcome={outcome}, mode={result["mode"]}, '
        f'task_id={task_id}, target_name={target_name}. {message}'
    ).strip()


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_executor_once(
        db_path=args.db_path,
        task_points_path=args.task_points,
        execute=args.execute,
        action_name=args.action_name,
        ready_gate_timeout_sec=args.ready_gate_timeout,
        ready_timeout_sec=args.ready_timeout,
        ready_poll_interval_sec=args.ready_poll_interval,
        navigation_timeout_sec=args.navigation_timeout,
        api_base_url=args.api_base_url,
        http_timeout_sec=args.http_timeout,
    )
    print(format_result_message(result))
    return int(result['exit_code'])


if __name__ == '__main__':
    raise SystemExit(main())

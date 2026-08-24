from pathlib import Path

import pytest

from amr_warehouse_sim.inspection.executor import run_inspection_route
from amr_warehouse_sim.inspection.image_capture import (
    CameraUnavailableError,
    CapturedImageFrame,
)
from amr_warehouse_sim.inspection.runtime_models import (
    InspectionPointSpec,
    InspectionPointStatus,
    PointExecutionState,
)
from amr_warehouse_sim.inspection.store import InspectionStore
from amr_warehouse_sim.mock_wms_executor import NavigationResult, ReadyGateResult


def _point(point_id='point_a', sequence=1, threshold=0.2):
    return InspectionPointSpec(
        point_id=point_id,
        sequence=sequence,
        frame_id='map',
        x=float(sequence),
        y=0.0,
        yaw=0.0,
        image_topic='/inspection/camera/image_raw',
        stabilization_sec=0.0,
        red_ratio_threshold=threshold,
    )


def _frame(color=(0, 255, 0), *, captured=200, started=100, data=None):
    width = 4
    height = 3
    raw = bytes(color) * width * height if data is None else data
    return CapturedImageFrame(
        topic='/inspection/camera/image_raw',
        frame_id='camera',
        captured_at_ns=captured,
        received_at_ns=300,
        acquisition_started_at_ns=started,
        width=width,
        height=height,
        encoding='rgb8',
        step=width * 3,
        data=raw,
    )


class FakeNav:
    def __init__(self, results=None, ready=True):
        self.results = list(results or [NavigationResult(True, 'succeeded', 'ok')])
        self.calls = []
        self.ready = ready

    def check_ready_gate(self):
        return ReadyGateResult(self.ready, 'ready' if self.ready else 'not ready')

    def navigate_to_pose(self, pose, *, timeout_sec):
        self.calls.append((pose, timeout_sec))
        return self.results.pop(0)

    def close(self):
        pass


class FakeCapture:
    topic = '/inspection/camera/image_raw'

    def __init__(self, frames=None, error=None, ready=True):
        self.frames = list(frames or [])
        self.error = error
        self.ready = ready

    def check_ready(self, *, timeout_sec):
        return self.ready, 'ready' if self.ready else 'missing'

    def capture_fresh(self, *, timeout_sec):
        if self.error is not None:
            raise self.error
        return self.frames.pop(0)

    def close(self):
        pass


def _run(tmp_path, *, points=None, nav=None, capture=None):
    return run_inspection_route(
        points=tuple(points or [_point()]),
        run_id='run-1',
        robot_id='my_robot',
        execute=True,
        navigation_runtime=nav or FakeNav(),
        image_capture=capture or FakeCapture([_frame()]),
        artifact_root=tmp_path / 'artifacts',
        store=InspectionStore(tmp_path / 'inspection.db'),
        ready_timeout_sec=0.0,
        ready_poll_interval_sec=0.0,
        sleep_fn=lambda _: None,
    )


def test_point_state_transition_contract():
    state = PointExecutionState('p')
    for status in (
        InspectionPointStatus.NAVIGATING,
        InspectionPointStatus.ARRIVED,
        InspectionPointStatus.STABILIZING,
        InspectionPointStatus.ACQUIRING,
        InspectionPointStatus.VALIDATING,
        InspectionPointStatus.EVALUATING,
        InspectionPointStatus.SUCCEEDED,
    ):
        state.transition(status, at_ns=1)
    assert state.status is InspectionPointStatus.SUCCEEDED


def test_navigation_success_is_not_point_success():
    state = PointExecutionState('p')
    state.transition(InspectionPointStatus.NAVIGATING, at_ns=1)
    state.transition(InspectionPointStatus.ARRIVED, at_ns=2)
    assert state.status is InspectionPointStatus.ARRIVED
    assert state.status is not InspectionPointStatus.SUCCEEDED


def test_stale_image_is_rejected(tmp_path):
    report = _run(tmp_path, capture=FakeCapture([_frame(captured=100, started=100)]))
    assert report['status'] == 'failed'
    assert report['points'][0]['status'] == 'data_invalid'
    assert report['points'][0]['execution_fault']['code'] == 'data_invalid'


def test_missing_camera_becomes_acquisition_failure(tmp_path):
    report = _run(
        tmp_path,
        capture=FakeCapture(error=CameraUnavailableError('camera disappeared')),
    )
    assert report['points'][0]['status'] == 'acquisition_failed'
    assert report['points'][0]['execution_fault']['code'] == 'camera_unavailable'


def test_invalid_image_becomes_data_invalid(tmp_path):
    report = _run(tmp_path, capture=FakeCapture([_frame(data=b'bad')]))
    assert report['points'][0]['status'] == 'data_invalid'
    assert 'truncated' in report['points'][0]['reason']


def test_red_ratio_above_threshold_is_warning(tmp_path):
    report = _run(tmp_path, capture=FakeCapture([_frame((255, 0, 0))]))
    assert report['points'][0]['evaluation'] == 'warning'
    assert report['points'][0]['execution_fault'] is None


def test_normal_image_is_pass(tmp_path):
    report = _run(tmp_path, capture=FakeCapture([_frame((0, 255, 0))]))
    assert report['points'][0]['evaluation'] == 'pass'


def test_warning_still_allows_run_success(tmp_path):
    report = _run(tmp_path, capture=FakeCapture([_frame((255, 0, 0))]))
    assert report['status'] == 'succeeded'
    assert report['summary']['warning'] == 1
    assert report['summary']['execution_failures'] == 0


def test_one_point_execution_failure_fails_route_and_stops(tmp_path):
    nav = FakeNav(
        [
            NavigationResult(True, 'succeeded', 'ok'),
            NavigationResult(False, 'failed', 'aborted'),
        ]
    )
    points = [_point('a', 1), _point('b', 2), _point('c', 3)]
    report = _run(tmp_path, points=points, nav=nav, capture=FakeCapture([_frame()]))
    assert report['status'] == 'failed'
    assert [point['point_id'] for point in report['points']] == ['a', 'b']
    assert report['points'][1]['status'] == 'navigation_failed'


def test_sqlite_run_and_point_results_are_persisted(tmp_path):
    _run(tmp_path)
    store = InspectionStore(tmp_path / 'inspection.db')
    assert store.get_run('run-1')['status'] == 'succeeded'
    assert store.list_point_results('run-1')[0]['evaluation'] == 'pass'


def test_artifact_reference_and_png_are_persisted(tmp_path):
    report = _run(tmp_path)
    point = report['points'][0]
    assert point['artifact_ref'].startswith('file://')
    assert (tmp_path / 'artifacts/run-1/point_a/rgb.png').read_bytes().startswith(
        b'\x89PNG\r\n\x1a\n'
    )
    stored = InspectionStore(tmp_path / 'inspection.db').list_point_results('run-1')[0]
    assert stored['artifact_ref'] == point['artifact_ref']


def test_invalid_transition_is_rejected():
    state = PointExecutionState('p')
    with pytest.raises(ValueError, match='Invalid inspection point transition'):
        state.transition(InspectionPointStatus.SUCCEEDED, at_ns=1)

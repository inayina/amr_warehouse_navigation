import importlib.util
import json

import pytest


def _load_module(module_path, module_name):
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope='module')
def wms_dispatcher(repo_root):
    module_path = (
        repo_root
        / 'future_extensions'
        / 'wms_integration'
        / 'task_manager'
        / 'wms_dispatcher.py'
    )
    return _load_module(module_path, 'wms_dispatcher')


def test_mock_wms_default_assets_are_loadable(repo_root, wms_dispatcher):
    wms_root = repo_root / 'future_extensions' / 'wms_integration'
    paths = wms_dispatcher.default_paths()

    assert paths['root_dir'] == wms_root
    assert paths['waypoints'].is_file()
    assert paths['tasks'].is_file()
    assert paths['report'].parent == wms_root / 'reports'

    waypoint_bundle = wms_dispatcher.normalize_waypoints(paths['waypoints'])
    task_bundle = wms_dispatcher.normalize_task_queue(
        paths['tasks'],
        waypoint_bundle['waypoints'].keys(),
    )

    assert waypoint_bundle['frame_id'] == 'map'
    assert waypoint_bundle['waypoints']
    assert task_bundle['queue_name']
    assert task_bundle['robot_name']
    assert task_bundle['tasks']


def test_mock_wms_dry_run_writes_consistent_report(tmp_path, wms_dispatcher):
    waypoint_path = tmp_path / 'waypoints.json'
    task_path = tmp_path / 'tasks.json'
    report_path = tmp_path / 'last_run.json'

    waypoint_path.write_text(
        json.dumps(
            {
                'frame_id': 'map',
                'waypoints': {
                    'dock_a': {'x': 1, 'y': 2, 'yaw': 0},
                    'staging_1': {
                        'x': 3.5,
                        'y': -1.25,
                        'yaw': 1.57,
                        'description': 'Synthetic staging pose for tests.',
                    },
                },
            },
            indent=2,
        )
        + '\n',
        encoding='utf-8',
    )
    task_path.write_text(
        json.dumps(
            {
                'queue_name': 'test_queue',
                'robot_name': 'test_robot',
                'tasks': [
                    {
                        'task_id': 'TASK-SMOKE',
                        'type': 'move_mock',
                        'description': 'Synthetic two-step task.',
                        'steps': [
                            {'waypoint': 'dock_a', 'action': 'pickup'},
                            {'waypoint': 'staging_1', 'action': 'dropoff', 'pause_sec': 1.5},
                        ],
                    }
                ],
            },
            indent=2,
        )
        + '\n',
        encoding='utf-8',
    )

    waypoint_bundle = wms_dispatcher.normalize_waypoints(waypoint_path)
    task_bundle = wms_dispatcher.normalize_task_queue(
        task_path,
        waypoint_bundle['waypoints'].keys(),
    )

    wms_dispatcher.run_dry_run(waypoint_bundle, task_bundle, report_path)

    report = json.loads(report_path.read_text(encoding='utf-8'))

    assert report['mode'] == 'dry-run'
    assert report['frame_id'] == 'map'
    assert report['queue_name'] == 'test_queue'
    assert report['robot_name'] == 'test_robot'
    assert report['summary'] == {
        'task_count': 1,
        'step_count': 2,
        'status': 'validated',
    }
    assert [task['task_id'] for task in report['tasks']] == ['TASK-SMOKE']
    assert [step['step_id'] for step in report['tasks'][0]['steps']] == [
        'TASK-SMOKE-S01',
        'TASK-SMOKE-S02',
    ]
    assert report['tasks'][0]['steps'][0]['pose'] == {
        'x': 1.0,
        'y': 2.0,
        'yaw': 0.0,
        'description': '',
    }
    assert report['tasks'][0]['steps'][1]['pause_sec'] == 1.5


def test_mock_wms_rejects_unknown_waypoint_reference(tmp_path, wms_dispatcher):
    task_path = tmp_path / 'tasks.json'
    task_path.write_text(
        json.dumps(
            {
                'tasks': [
                    {
                        'task_id': 'TASK-BAD',
                        'steps': [{'waypoint': 'missing_waypoint'}],
                    }
                ]
            },
            indent=2,
        )
        + '\n',
        encoding='utf-8',
    )

    with pytest.raises(ValueError, match='unknown waypoint "missing_waypoint"'):
        wms_dispatcher.normalize_task_queue(task_path, {'dock_a'})


def test_mock_wms_rejects_waypoint_without_required_pose_fields(tmp_path, wms_dispatcher):
    waypoint_path = tmp_path / 'waypoints.json'
    waypoint_path.write_text(
        json.dumps(
            {
                'waypoints': {
                    'dock_a': {'x': 0.0, 'y': 0.0},
                }
            },
            indent=2,
        )
        + '\n',
        encoding='utf-8',
    )

    with pytest.raises(ValueError, match='missing "yaw"'):
        wms_dispatcher.normalize_waypoints(waypoint_path)

import importlib.util
import sqlite3

import pytest


def _load_module(module_path, module_name):
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope='module')
def mock_wms_modules(repo_root):
    scripts_dir = repo_root / 'scripts'
    return {
        'common': _load_module(scripts_dir / 'mock_wms_db_common.py', 'mock_wms_db_common'),
        'init_db': _load_module(scripts_dir / 'init_mock_wms_db.py', 'init_mock_wms_db'),
        'create_task': _load_module(scripts_dir / 'create_mock_task.py', 'create_mock_task'),
        'list_tasks': _load_module(scripts_dir / 'list_mock_tasks.py', 'list_mock_tasks'),
    }


def test_init_mock_wms_db_creates_tasks_table(tmp_path, mock_wms_modules):
    db_path = tmp_path / 'mock_wms.db'
    exit_code = mock_wms_modules['init_db'].main(['--db-path', str(db_path)])

    assert exit_code == 0
    assert db_path.is_file()

    with sqlite3.connect(db_path) as connection:
        row = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'tasks'"
        ).fetchone()

    assert row == ('tasks',)


def test_candidate_dock_a_can_be_created_as_pending_map_task(
    tmp_path,
    repo_root,
    mock_wms_modules,
):
    db_path = tmp_path / 'mock_wms.db'
    common = mock_wms_modules['common']
    create_task = mock_wms_modules['create_task']

    task_points = common.load_task_points(repo_root / 'config' / 'task_points.yaml')
    expected_pose = task_points['candidate_dock_a']

    exit_code = create_task.main(
        [
            '--db-path',
            str(db_path),
            '--task-points',
            str(repo_root / 'config' / 'task_points.yaml'),
            '--target',
            'candidate_dock_a',
        ]
    )

    assert exit_code == 0

    rows = common.list_tasks(db_path)
    assert len(rows) == 1

    task = rows[0]
    assert task['target_name'] == 'candidate_dock_a'
    assert task['frame_id'] == 'map'
    assert task['status'] == 'pending'
    assert task['x'] == pytest.approx(expected_pose['x'])
    assert task['y'] == pytest.approx(expected_pose['y'])
    assert task['yaw'] == pytest.approx(expected_pose['yaw'])


def test_dock_a_alias_creates_pending_task_and_can_be_listed(
    tmp_path,
    repo_root,
    mock_wms_modules,
    capsys,
):
    db_path = tmp_path / 'mock_wms.db'
    common = mock_wms_modules['common']
    create_task = mock_wms_modules['create_task']
    list_tasks = mock_wms_modules['list_tasks']

    exit_code = create_task.main(
        [
            '--db-path',
            str(db_path),
            '--task-points',
            str(repo_root / 'config' / 'task_points.yaml'),
            '--target',
            'dock_a',
        ]
    )

    assert exit_code == 0

    rows = common.list_tasks(db_path)
    assert len(rows) == 1
    assert rows[0]['target_name'] == 'candidate_dock_a'
    assert rows[0]['frame_id'] == 'map'
    assert rows[0]['status'] == 'pending'

    list_exit_code = list_tasks.main(['--db-path', str(db_path)])
    assert list_exit_code == 0

    output = capsys.readouterr().out
    assert 'target_name' in output
    assert 'candidate_dock_a' in output
    assert 'pending' in output


@pytest.mark.parametrize(
    'target_name',
    (
        'station_a',
        'station_b',
        'shelf_1',
        'shelf_2',
    ),
)
def test_validated_business_points_can_be_created_as_pending_map_tasks(
    target_name,
    tmp_path,
    repo_root,
    mock_wms_modules,
):
    db_path = tmp_path / 'mock_wms.db'
    common = mock_wms_modules['common']
    create_task = mock_wms_modules['create_task']

    task_points = common.load_task_points(repo_root / 'config' / 'task_points.yaml')
    expected_pose = task_points[target_name]

    exit_code = create_task.main(
        [
            '--db-path',
            str(db_path),
            '--task-points',
            str(repo_root / 'config' / 'task_points.yaml'),
            '--target',
            target_name,
        ]
    )

    assert exit_code == 0

    rows = common.list_tasks(db_path)
    assert len(rows) == 1

    task = rows[0]
    assert task['target_name'] == target_name
    assert task['frame_id'] == 'map'
    assert task['status'] == 'pending'
    assert task['x'] == pytest.approx(expected_pose['x'])
    assert task['y'] == pytest.approx(expected_pose['y'])
    assert task['yaw'] == pytest.approx(expected_pose['yaw'])


def test_start_zone_is_rejected_for_v3_mock_wms_tasks(
    tmp_path,
    repo_root,
    mock_wms_modules,
):
    db_path = tmp_path / 'mock_wms.db'
    common = mock_wms_modules['common']
    create_task = mock_wms_modules['create_task']

    with pytest.raises(
        ValueError,
        match='validated task targets',
    ):
        create_task.main(
            [
                '--db-path',
                str(db_path),
                '--task-points',
                str(repo_root / 'config' / 'task_points.yaml'),
                '--target',
                'start_zone',
            ]
        )

    assert not db_path.exists()

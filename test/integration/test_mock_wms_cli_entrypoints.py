import importlib
import subprocess
import sys

import pytest


@pytest.mark.parametrize(
    ('module_name', 'help_fragment'),
    (
        (
            'amr_warehouse_sim.init_mock_wms_db',
            'Initialize the minimal SQLite database for the V3.0 Mock WMS data layer.',
        ),
        (
            'amr_warehouse_sim.create_mock_task',
            'Create one pending Mock WMS task from config/task_points.yaml.',
        ),
        (
            'amr_warehouse_sim.list_mock_tasks',
            'List tasks from the minimal SQLite database for the V3.0 Mock WMS data layer.',
        ),
        (
            'amr_warehouse_sim.mock_wms_api',
            'Run the minimal Mock WMS HTTP API backed by SQLite.',
        ),
        (
            'amr_warehouse_sim.mock_wms_executor',
            'Run the minimal V3.1 Mock WMS executor.',
        ),
        (
            'amr_warehouse_sim.mock_wms_task_runner',
            'Run the current-mainline Mock WMS task runner.',
        ),
    ),
)
def test_module_entrypoints_support_help(module_name, help_fragment, repo_root, capsys):
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    module = importlib.import_module(module_name)

    with pytest.raises(SystemExit) as exc_info:
        module.main(['--help'])

    assert exc_info.value.code == 0

    output = capsys.readouterr().out
    assert 'usage:' in output
    assert help_fragment in output


def test_mock_wms_task_runner_supports_python_module_help(repo_root):
    completed = subprocess.run(
        [sys.executable, '-m', 'amr_warehouse_sim.mock_wms_task_runner', '--help'],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert 'usage:' in completed.stdout
    assert '--max-tasks' in completed.stdout


def test_mock_wms_executor_help_mentions_http_mode(repo_root, capsys):
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    module = importlib.import_module('amr_warehouse_sim.mock_wms_executor')

    with pytest.raises(SystemExit) as exc_info:
        module.main(['--help'])

    assert exc_info.value.code == 0

    output = capsys.readouterr().out
    assert '--api-base-url' in output
    assert '--http-timeout' in output

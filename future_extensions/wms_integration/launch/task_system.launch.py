import os
from pathlib import Path

from ament_index_python.packages import PackageNotFoundError, get_package_share_directory
from launch import LaunchDescription
from launch.actions import ExecuteProcess


def resolve_extension_root():
    source_candidate = Path(__file__).resolve().parents[1]
    if (source_candidate / 'task_manager' / 'wms_dispatcher.py').is_file():
        return source_candidate

    try:
        package_share = Path(get_package_share_directory('amr_warehouse_sim'))
    except PackageNotFoundError as exc:
        raise FileNotFoundError('Could not locate amr_warehouse_sim package share path.') from exc

    installed_candidate = package_share / 'future_extensions' / 'wms_integration'
    if (installed_candidate / 'task_manager' / 'wms_dispatcher.py').is_file():
        return installed_candidate

    raise FileNotFoundError('Could not locate installed mock WMS assets.')


def generate_launch_description():
    extension_root = resolve_extension_root()
    runner_path = os.path.join(str(extension_root), 'scripts', 'mock_wms_runner.py')
    waypoint_path = os.path.join(str(extension_root), 'config', 'waypoints.json')
    task_path = os.path.join(str(extension_root), 'tasks', 'demo_tasks.json')

    return LaunchDescription([
        ExecuteProcess(
            cmd=[
                'python3',
                runner_path,
                '--mode',
                'dry-run',
                '--waypoints',
                waypoint_path,
                '--tasks',
                task_path,
            ],
            output='screen',
        )
    ])

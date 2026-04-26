import importlib.util

import pytest


def _load_launch_module(module_path, module_name):
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_simulation_launch_generates_description(repo_root, tmp_path, monkeypatch):
    pytest.importorskip('ament_index_python')
    pytest.importorskip('launch')
    pytest.importorskip('launch_ros')
    monkeypatch.setenv('ROS_LOG_DIR', str(tmp_path / 'ros_logs'))

    module = _load_launch_module(
        repo_root / 'launch' / 'simulation.launch.py',
        'simulation_launch',
    )

    def fake_get_package_share_directory(package_name):
        if package_name == 'amr_warehouse_sim':
            return str(repo_root)
        raise RuntimeError(f'Unexpected package lookup: {package_name}')

    monkeypatch.setattr(module, 'get_package_share_directory', fake_get_package_share_directory)

    launch_description = module.generate_launch_description()
    argument_names = {
        entity.name
        for entity in launch_description.entities
        if type(entity).__name__ == 'DeclareLaunchArgument'
    }

    assert {'use_gz_gui', 'start_delay'}.issubset(argument_names)
    assert any(type(entity).__name__ == 'TimerAction' for entity in launch_description.entities)


def test_navigation_launch_generates_description(repo_root, tmp_path, monkeypatch):
    pytest.importorskip('ament_index_python')
    pytest.importorskip('launch')
    pytest.importorskip('launch_ros')
    monkeypatch.setenv('ROS_LOG_DIR', str(tmp_path / 'ros_logs'))

    fake_nav2_bringup = tmp_path / 'nav2_bringup'
    (fake_nav2_bringup / 'launch').mkdir(parents=True)
    (fake_nav2_bringup / 'launch' / 'bringup_launch.py').write_text(
        'from launch import LaunchDescription\n'
        'def generate_launch_description():\n'
        '    return LaunchDescription()\n',
        encoding='utf-8',
    )

    module = _load_launch_module(
        repo_root / 'launch' / 'navigation.launch.py',
        'navigation_launch',
    )

    def fake_get_package_share_directory(package_name):
        if package_name == 'amr_warehouse_sim':
            return str(repo_root)
        if package_name == 'nav2_bringup':
            return str(fake_nav2_bringup)
        raise RuntimeError(f'Unexpected package lookup: {package_name}')

    monkeypatch.setattr(module, 'get_package_share_directory', fake_get_package_share_directory)

    launch_description = module.generate_launch_description()
    argument_names = {
        entity.name
        for entity in launch_description.entities
        if type(entity).__name__ == 'DeclareLaunchArgument'
    }

    assert {'use_gz_gui', 'use_rviz', 'nav2_delay', 'map', 'params_file'}.issubset(
        argument_names
    )
    assert any(type(entity).__name__ == 'TimerAction' for entity in launch_description.entities)

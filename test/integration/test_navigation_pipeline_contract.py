def _parse_simple_yaml(path):
    data = {}
    for raw_line in path.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#'):
            continue
        key, value = line.split(':', 1)
        data[key.strip()] = value.strip()
    return data


def test_v2_navigation_pipeline_keeps_scan_and_odom_contract(repo_root):
    simulation_launch = (repo_root / 'launch' / 'simulation.launch.py').read_text(
        encoding='utf-8'
    )
    navigation_launch = (repo_root / 'launch' / 'navigation.launch.py').read_text(
        encoding='utf-8'
    )
    nav2_params = (repo_root / 'config' / 'nav2_params.yaml').read_text(encoding='utf-8')

    assert '/scan@sensor_msgs/msg/LaserScan@gz.msgs.LaserScan' in simulation_launch
    assert '/odom@nav_msgs/msg/Odometry@gz.msgs.Odometry' in simulation_launch
    assert "executable='odom_tf_node'" in simulation_launch

    assert "package='laser_filters'" in navigation_launch
    assert "('scan', '/scan')" in navigation_launch
    assert "('scan_filtered', '/scan_filtered')" in navigation_launch

    assert 'scan_topic: /scan_filtered' in nav2_params
    assert nav2_params.count('topic: /scan_filtered') >= 3
    assert 'odom_topic: /odom' in nav2_params


def test_v2_navigation_pipeline_keeps_map_and_frame_contract(repo_root):
    navigation_launch = (repo_root / 'launch' / 'navigation.launch.py').read_text(
        encoding='utf-8'
    )
    simulation_launch = (repo_root / 'launch' / 'simulation.launch.py').read_text(
        encoding='utf-8'
    )
    nav2_params = (repo_root / 'config' / 'nav2_params.yaml').read_text(encoding='utf-8')
    map_yaml = repo_root / 'maps' / 'warehouse.yaml'
    metadata = _parse_simple_yaml(map_yaml)

    assert "default_map = os.path.join(pkg_share, 'maps', 'warehouse.yaml')" in navigation_launch
    assert "default_params = os.path.join(pkg_share, 'config', 'nav2_params.yaml')" in navigation_launch

    assert metadata['image'] == 'warehouse_slam.pgm'
    assert (map_yaml.parent / metadata['image']).is_file()

    for expected_text in (
        'global_frame_id: "map"',
        'odom_frame_id: "odom"',
        'base_frame_id: "base_link"',
        'global_frame: map',
        'robot_base_frame: base_link',
    ):
        assert expected_text in nav2_params

    assert "executable='static_transform_publisher'" in simulation_launch
    assert 'my_robot/lidar_link/lidar' in simulation_launch
    assert "executable='robot_state_publisher'" in navigation_launch

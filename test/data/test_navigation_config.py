FOOTPRINT = 'footprint: "[[0.28, 0.21], [0.28, -0.21], [-0.28, -0.21], [-0.28, 0.21]]"'


def test_nav2_params_define_core_navigation_servers(repo_root):
    nav2_params = (repo_root / 'config' / 'nav2_params.yaml').read_text(encoding='utf-8')

    for section in (
        'amcl:',
        'bt_navigator:',
        'controller_server:',
        'planner_server:',
        'behavior_server:',
        'velocity_smoother:',
        'collision_monitor:',
    ):
        assert section in nav2_params, f'Missing Nav2 section: {section}'


def test_nav2_params_keep_filtered_scan_pipeline(repo_root):
    nav2_params = (repo_root / 'config' / 'nav2_params.yaml').read_text(encoding='utf-8')

    assert 'scan_topic: /scan_filtered' in nav2_params
    assert nav2_params.count('topic: /scan_filtered') >= 3
    assert 'observation_sources: scan' in nav2_params


def test_nav2_params_keep_documented_stable_baseline_markers(repo_root):
    nav2_params = (repo_root / 'config' / 'nav2_params.yaml').read_text(encoding='utf-8')

    assert FOOTPRINT in nav2_params
    assert nav2_params.count(FOOTPRINT) == 2
    assert 'save_pose_rate: -1.0' in nav2_params
    assert 'always_reset_initial_pose: true' in nav2_params
    assert 'required_movement_radius: 0.10' in nav2_params
    assert 'plugin: "nav2_mppi_controller::MPPIController"' in nav2_params
    assert 'plugin: "nav2_navfn_planner::NavfnPlanner"' in nav2_params
    assert 'use_astar: true' in nav2_params
    assert 'consider_footprint: true' in nav2_params
    assert nav2_params.count('inflation_radius: 0.40') >= 2

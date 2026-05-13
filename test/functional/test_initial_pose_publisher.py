import importlib.util
import math


def _load_module(module_path, module_name):
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_initial_pose_parser_defaults(repo_root):
    module = _load_module(
        repo_root / 'amr_warehouse_sim' / 'initial_pose_publisher.py',
        'initial_pose_publisher',
    )

    parser = module.create_parser()
    args = module.resolve_pose_args(
        parser.parse_args(['--x', '1.0', '--y', '2.0', '--yaw', '0.5']),
        parser,
    )

    assert args.preset is None
    assert args.topic == '/initialpose'
    assert args.frame_id == 'map'
    assert args.covariance_xy == module.DEFAULT_COVARIANCE_XY
    assert args.covariance_yaw == module.DEFAULT_COVARIANCE_YAW
    assert args.count == 10
    assert math.isclose(args.interval, 0.2)
    assert math.isclose(args.wait_for_subscribers, 5.0)


def test_initial_pose_preset_resolves_to_start_zone(repo_root):
    module = _load_module(
        repo_root / 'amr_warehouse_sim' / 'initial_pose_publisher.py',
        'initial_pose_publisher',
    )

    parser = module.create_parser()
    args = module.resolve_pose_args(
        parser.parse_args(['--preset', 'start_zone']),
        parser,
    )

    assert math.isclose(args.x, 0.0)
    assert math.isclose(args.y, 0.0)
    assert math.isclose(args.yaw, 0.0)


def test_build_initial_pose_message_sets_pose_and_covariance(repo_root):
    module = _load_module(
        repo_root / 'amr_warehouse_sim' / 'initial_pose_publisher.py',
        'initial_pose_publisher',
    )

    msg = module.build_initial_pose_message(
        x=1.25,
        y=-0.75,
        yaw=math.pi / 2.0,
        frame_id='map',
        covariance_xy=0.5,
        covariance_yaw=0.25,
    )

    assert msg.header.frame_id == 'map'
    assert math.isclose(msg.pose.pose.position.x, 1.25)
    assert math.isclose(msg.pose.pose.position.y, -0.75)
    assert math.isclose(msg.pose.pose.orientation.z, math.sin(math.pi / 4.0))
    assert math.isclose(msg.pose.pose.orientation.w, math.cos(math.pi / 4.0))
    assert math.isclose(msg.pose.covariance[0], 0.5)
    assert math.isclose(msg.pose.covariance[7], 0.5)
    assert math.isclose(msg.pose.covariance[35], 0.25)

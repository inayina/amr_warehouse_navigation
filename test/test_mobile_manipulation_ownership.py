from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DESCRIPTION = ROOT / 'mobile_manipulation' / 'amr_mm_description'
BRINGUP = ROOT / 'mobile_manipulation' / 'amr_mm_bringup'


def test_arm_gripper_controller_config_excludes_wheels():
    config = (DESCRIPTION / 'config' / 'arm_gripper_controllers.yaml').read_text()
    assert 'arm_trajectory_controller:' in config
    assert 'gripper_controller:' in config
    assert 'left_wheel_joint' not in config
    assert 'right_wheel_joint' not in config


def test_gate1_bringup_is_opt_in_and_server_only_by_default():
    launch = (BRINGUP / 'launch' / 'mobile_manipulation_sim.launch.py').read_text()
    assert "default_value='-s -r -v 2 empty.sdf'" in launch
    assert 'navigation.launch.py' not in launch
    assert 'simulation.launch.py' not in launch


def test_combined_description_uses_official_ur_macro_and_flange_mount():
    description = (DESCRIPTION / 'urdf' / 'mobile_manipulator.urdf.xacro').read_text()
    assert 'ur_macro.xacro' in description
    assert 'parent="arm_flange"' in description
    ros2_control = description.split('<ros2_control', maxsplit=1)[1].split('</ros2_control>', maxsplit=1)[0]
    assert 'wheel' not in ros2_control

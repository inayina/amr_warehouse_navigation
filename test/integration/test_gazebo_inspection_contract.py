from pathlib import Path
import xml.etree.ElementTree as ET

from amr_warehouse_sim.inspection.executor import load_inspection_points


def test_inspection_robot_preserves_drive_lidar_and_adds_rgb_camera(repo_root: Path):
    root = ET.parse(repo_root / 'models/my_robot_inspection/model.sdf').getroot()
    assert root.find(".//plugin[@name='gz::sim::systems::DiffDrive']") is not None
    assert root.find(".//sensor[@type='gpu_lidar']/topic").text == '/scan'
    camera = root.find(".//sensor[@type='camera']")
    assert camera is not None
    assert camera.find('topic').text == '/inspection/camera/image_raw'
    assert camera.find('update_rate').text == '10'
    assert camera.find('camera/image/width').text == '640'
    assert camera.find('camera/image/height').text == '480'


def test_inspection_targets_are_visual_only(repo_root: Path):
    root = ET.parse(repo_root / 'worlds/warehouse_inspection.world').getroot()
    for name in ('inspection_cabinet_a', 'inspection_pump_b', 'inspection_panel_c'):
        model = root.find(f".//model[@name='{name}']")
        assert model is not None
        assert model.findall('.//visual')
        assert not model.findall('.//collision')


def test_inspection_world_uses_variant_without_changing_world_name(repo_root: Path):
    root = ET.parse(repo_root / 'worlds/warehouse_inspection.world').getroot()
    assert root.find("world[@name='warehouse_world']") is not None
    include = root.find(".//include[uri='model://my_robot_inspection']")
    assert include is not None
    assert include.find('name').text == 'my_robot'


def test_inspection_launch_has_real_image_bridge_and_existing_nav_authority(repo_root: Path):
    launch = (repo_root / 'launch/inspection_navigation.launch.py').read_text(
        encoding='utf-8'
    )
    assert "package='ros_gz_image'" in launch
    assert "arguments=['/inspection/camera/image_raw']" in launch
    assert "'warehouse_inspection.world'" in launch
    assert "'warehouse.yaml'" in launch
    assert "'nav2_params.yaml'" in launch
    assert "'bringup_launch.py'" in launch


def test_inspection_camera_tf_contract_is_explicit(repo_root: Path):
    root = ET.parse(repo_root / 'models/my_robot_inspection_visual.urdf').getroot()
    camera_joint = root.find("joint[@name='front_camera_joint']")
    optical_joint = root.find("joint[@name='front_camera_optical_joint']")
    assert camera_joint.find('parent').attrib['link'] == 'base_link'
    assert camera_joint.find('child').attrib['link'] == 'front_camera_link'
    assert optical_joint.find('parent').attrib['link'] == 'front_camera_link'
    assert optical_joint.find('child').attrib['link'] == 'front_camera_optical_frame'


def test_inspection_route_is_separate_and_ordered(repo_root: Path):
    points = load_inspection_points(repo_root / 'config/inspection_points.yaml')
    assert [point.point_id for point in points] == ['cabinet_a', 'pump_b', 'panel_c']
    assert [point.sequence for point in points] == [1, 2, 3]
    assert {point.image_topic for point in points} == {
        '/inspection/camera/image_raw'
    }

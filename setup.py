import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'amr_warehouse_sim'
data_files = [
    ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
    ('share/' + package_name, ['package.xml']),
    (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
]

asset_patterns = [
    ('config', 'config/*.yaml'),
    ('rviz', 'rviz/*.rviz'),
    ('worlds', 'worlds/*.world'),
    ('maps', 'maps/*'),
    ('scripts', 'scripts/*.py'),
]

for install_dir, pattern in asset_patterns:
    files = sorted(glob(pattern))
    if files:
        data_files.append((os.path.join('share', package_name, install_dir), files))

wms_asset_patterns = [
    ('launch', 'future_extensions/wms_integration/launch/*.py'),
    (
        'future_extensions/wms_integration',
        'future_extensions/wms_integration/README.md',
    ),
    (
        'future_extensions/wms_integration/config',
        'future_extensions/wms_integration/config/*.json',
    ),
    (
        'future_extensions/wms_integration/scripts',
        'future_extensions/wms_integration/scripts/*.py',
    ),
    (
        'future_extensions/wms_integration/scripts',
        'future_extensions/wms_integration/scripts/*.sh',
    ),
    (
        'future_extensions/wms_integration/task_manager',
        'future_extensions/wms_integration/task_manager/*.py',
    ),
    (
        'future_extensions/wms_integration/tasks',
        'future_extensions/wms_integration/tasks/*.json',
    ),
]

for install_dir, pattern in wms_asset_patterns:
    files = sorted(glob(pattern))
    if files:
        data_files.append((os.path.join('share', package_name, install_dir), files))

for path in sorted(glob('models/**/*', recursive=True)):
    if os.path.isfile(path):
        data_files.append((os.path.join('share', package_name, os.path.dirname(path)), [path]))

setup(
    name=package_name,
    version='0.0.1',
    packages=find_packages(exclude=['test', 'archive*', 'future_extensions*']),
    data_files=data_files,
    install_requires=['setuptools', 'fastapi', 'uvicorn'],
    zip_safe=True,
    maintainer='ina',
    description='AMR Warehouse Simulation for ROS 2 Jazzy',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'odom_tf_node = amr_warehouse_sim.odom_tf_node:main',
            'publish_initial_pose = amr_warehouse_sim.initial_pose_publisher:main',
            'init_mock_wms_db = amr_warehouse_sim.init_mock_wms_db:main',
            'create_mock_task = amr_warehouse_sim.create_mock_task:main',
            'list_mock_tasks = amr_warehouse_sim.list_mock_tasks:main',
            'mock_wms_api = amr_warehouse_sim.mock_wms_api:main',
            'mock_wms_executor = amr_warehouse_sim.mock_wms_executor:main',
            'mock_wms_task_runner = amr_warehouse_sim.mock_wms_task_runner:main',
            'deep_robotics_state_adapter = amr_warehouse_sim.integrations.deep_robotics.state_adapter:main',
            'unitree_state_adapter = amr_warehouse_sim.integrations.unitree.state_adapter:main',
            'agibot_state_adapter = amr_warehouse_sim.integrations.agibot.state_adapter:main',
        ],
    },
)

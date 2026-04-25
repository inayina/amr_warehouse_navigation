import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_share = get_package_share_directory('amr_warehouse_sim')
    nav2_bringup_dir = get_package_share_directory('nav2_bringup')

    use_gz_gui = LaunchConfiguration('use_gz_gui')
    use_rviz = LaunchConfiguration('use_rviz')
    nav2_delay = LaunchConfiguration('nav2_delay')
    map_file = LaunchConfiguration('map')
    params_file = LaunchConfiguration('params_file')

    default_map = os.path.join(pkg_share, 'maps', 'warehouse.yaml')
    default_params = os.path.join(pkg_share, 'config', 'nav2_params.yaml')
    laser_filters_params_file = os.path.join(pkg_share, 'config', 'laser_filters.yaml')
    rviz_config = os.path.join(pkg_share, 'rviz', 'nav2.rviz')
    urdf_path = os.path.join(pkg_share, 'models', 'my_robot_visual.urdf')

    simulation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_share, 'launch', 'simulation.launch.py')
        ),
        launch_arguments={
            'use_gz_gui': use_gz_gui,
        }.items(),
    )

    nav2 = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_bringup_dir, 'launch', 'bringup_launch.py')
        ),
        launch_arguments={
            'slam': 'False',
            'map': map_file,
            'use_sim_time': 'True',
            'params_file': params_file,
            'autostart': 'True',
            'use_composition': 'False',
        }.items(),
    )

    scan_filter = Node(
        package='laser_filters',
        executable='scan_to_scan_filter_chain',
        name='scan_to_scan_filter_chain',
        parameters=[
            laser_filters_params_file,
            {'use_sim_time': True},
        ],
        remappings=[
            ('scan', '/scan'),
            ('scan_filtered', '/scan_filtered'),
        ],
        output='screen',
    )

    with open(urdf_path, 'r', encoding='utf-8') as urdf_file:
        robot_description = urdf_file.read()

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[
            {
                'use_sim_time': True,
                'robot_description': robot_description,
            }
        ],
        output='screen',
    )

    rviz = Node(
        package='rviz2',
        executable='rviz2',
        arguments=['-d', rviz_config],
        condition=IfCondition(use_rviz),
        parameters=[{'use_sim_time': True}],
        output='screen',
    )

    delayed_nav2 = TimerAction(
        period=nav2_delay,
        actions=[
            scan_filter,
            robot_state_publisher,
            nav2,
            rviz,
        ],
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_gz_gui',
            default_value='true',
            description='Start Gazebo with GUI. Set to false for headless server-only mode.',
        ),
        DeclareLaunchArgument(
            'use_rviz',
            default_value='true',
            description='Start RViz after Nav2 starts.',
        ),
        DeclareLaunchArgument(
            'nav2_delay',
            default_value='6.0',
            description='Seconds to wait before starting Nav2 after simulation starts.',
        ),
        DeclareLaunchArgument(
            'map',
            default_value=default_map,
            description='Full path to the map YAML file used by Nav2 map_server.',
        ),
        DeclareLaunchArgument(
            'params_file',
            default_value=default_params,
            description='Full path to the Nav2 parameter file.',
        ),
        simulation,
        delayed_nav2,
    ])

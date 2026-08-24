import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription, SetEnvironmentVariable, TimerAction
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_share = get_package_share_directory('amr_warehouse_sim')
    nav2_bringup_dir = get_package_share_directory('nav2_bringup')

    use_gz_gui = LaunchConfiguration('use_gz_gui')
    use_rviz = LaunchConfiguration('use_rviz')
    bridge_delay = LaunchConfiguration('bridge_delay')
    nav2_delay = LaunchConfiguration('nav2_delay')
    map_file = LaunchConfiguration('map')
    params_file = LaunchConfiguration('params_file')

    models_dir = os.path.join(pkg_share, 'models')
    world_path = os.path.join(pkg_share, 'worlds', 'warehouse_inspection.world')
    default_map = os.path.join(pkg_share, 'maps', 'warehouse.yaml')
    default_params = os.path.join(pkg_share, 'config', 'nav2_params.yaml')
    laser_filters_params_file = os.path.join(pkg_share, 'config', 'laser_filters.yaml')
    rviz_config = os.path.join(pkg_share, 'rviz', 'nav2.rviz')
    urdf_path = os.path.join(pkg_share, 'models', 'my_robot_inspection_visual.urdf')

    set_resource_path = SetEnvironmentVariable(
        name='GZ_SIM_RESOURCE_PATH',
        value=[models_dir, ':', os.path.join(pkg_share, 'worlds')],
    )
    set_sdf_path = SetEnvironmentVariable(name='SDF_PATH', value=models_dir)

    gazebo_with_gui = ExecuteProcess(
        cmd=['gz', 'sim', '-r', world_path],
        condition=IfCondition(use_gz_gui),
        output='screen',
    )
    gazebo_headless = ExecuteProcess(
        cmd=['gz', 'sim', '-r', '-s', world_path],
        condition=UnlessCondition(use_gz_gui),
        output='screen',
    )

    transport_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            '/cmd_vel@geometry_msgs/msg/Twist@gz.msgs.Twist',
            '/odom@nav_msgs/msg/Odometry@gz.msgs.Odometry',
            '/scan@sensor_msgs/msg/LaserScan@gz.msgs.LaserScan',
            '/clock@rosgraph_msgs/msg/Clock@gz.msgs.Clock',
        ],
        parameters=[{'use_sim_time': True}],
        output='screen',
    )
    image_bridge = Node(
        package='ros_gz_image',
        executable='image_bridge',
        name='inspection_image_bridge',
        arguments=['/inspection/camera/image_raw'],
        parameters=[{'use_sim_time': True}],
        output='screen',
    )
    lidar_tf = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        arguments=[
            '0.20', '0', '0.32',
            '0', '0', '0',
            'base_link',
            'my_robot/lidar_link/lidar',
        ],
        parameters=[{'use_sim_time': True}],
        output='screen',
    )
    odom_tf = Node(
        package='amr_warehouse_sim',
        executable='odom_tf_node',
        parameters=[{'use_sim_time': True}],
        output='screen',
    )
    delayed_bridges = TimerAction(
        period=bridge_delay,
        actions=[transport_bridge, image_bridge, lidar_tf, odom_tf],
    )

    scan_filter = Node(
        package='laser_filters',
        executable='scan_to_scan_filter_chain',
        name='scan_to_scan_filter_chain',
        parameters=[laser_filters_params_file, {'use_sim_time': True}],
        remappings=[('scan', '/scan'), ('scan_filtered', '/scan_filtered')],
        output='screen',
    )

    with open(urdf_path, 'r', encoding='utf-8') as urdf_file:
        robot_description = urdf_file.read()

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{'use_sim_time': True, 'robot_description': robot_description}],
        output='screen',
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
        actions=[scan_filter, robot_state_publisher, nav2, rviz],
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_gz_gui',
            default_value='true',
            description='Start the inspection world with Gazebo GUI.',
        ),
        DeclareLaunchArgument(
            'use_rviz',
            default_value='true',
            description='Start RViz after the inspection Nav2 stack starts.',
        ),
        DeclareLaunchArgument(
            'bridge_delay',
            default_value='4.0',
            description='Seconds to wait before starting Gazebo-to-ROS bridges.',
        ),
        DeclareLaunchArgument(
            'nav2_delay',
            default_value='6.0',
            description='Seconds to wait before starting Nav2.',
        ),
        DeclareLaunchArgument(
            'map',
            default_value=default_map,
            description='Existing warehouse map used as navigation authority.',
        ),
        DeclareLaunchArgument(
            'params_file',
            default_value=default_params,
            description='Existing stable Nav2 parameter file.',
        ),
        set_resource_path,
        set_sdf_path,
        gazebo_with_gui,
        gazebo_headless,
        delayed_bridges,
        delayed_nav2,
    ])

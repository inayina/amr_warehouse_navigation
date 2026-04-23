import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, SetEnvironmentVariable, TimerAction
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_share = get_package_share_directory('amr_warehouse_sim')
    models_dir = os.path.join(pkg_share, 'models')

    use_gz_gui = LaunchConfiguration('use_gz_gui')
    start_delay = LaunchConfiguration('start_delay')

    world_path = os.path.join(pkg_share, 'worlds', 'warehouse_full.world')

    set_env = SetEnvironmentVariable(
        name='GZ_SIM_RESOURCE_PATH',
        value=[models_dir, ':', os.path.join(pkg_share, 'worlds')],
    )
    set_sdf_path = SetEnvironmentVariable(
        name='SDF_PATH',
        value=models_dir,
    )

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

    bridge = Node(
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

    delayed_start = TimerAction(
        period=start_delay,
        actions=[
            bridge,
            lidar_tf,
            odom_tf,
        ],
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_gz_gui',
            default_value='true',
            description='Start Gazebo with GUI. Set to false for headless server-only mode.',
        ),
        DeclareLaunchArgument(
            'start_delay',
            default_value='4.0',
            description='Seconds to wait before starting bridge nodes.',
        ),
        set_env,
        set_sdf_path,
        gazebo_with_gui,
        gazebo_headless,
        delayed_start,
    ])

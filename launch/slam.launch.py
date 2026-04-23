import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    EmitEvent,
    ExecuteProcess,
    LogInfo,
    RegisterEventHandler,
    SetEnvironmentVariable,
    TimerAction,
)
from launch.conditions import IfCondition, UnlessCondition
from launch.events import matches_action
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import LifecycleNode, Node
from launch_ros.event_handlers import OnStateTransition
from launch_ros.events.lifecycle import ChangeState
from lifecycle_msgs.msg import Transition


def generate_launch_description():
    pkg_share = get_package_share_directory('amr_warehouse_sim')
    models_dir = os.path.join(pkg_share, 'models')

    use_gz_gui = LaunchConfiguration('use_gz_gui')
    use_rviz = LaunchConfiguration('use_rviz')
    start_delay = LaunchConfiguration('start_delay')

    world_path = os.path.join(pkg_share, 'worlds', 'warehouse_full.world')
    urdf_path = os.path.join(models_dir, 'my_robot_visual.urdf')
    slam_params_file = os.path.join(pkg_share, 'config', 'slam_toolbox.yaml')
    rviz_config = os.path.join(pkg_share, 'rviz', 'slam.rviz')

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

    slam = LifecycleNode(
        package='slam_toolbox',
        executable='async_slam_toolbox_node',
        name='slam_toolbox',
        parameters=[
            slam_params_file,
            {
                'use_sim_time': True,
                'scan_topic': '/scan',
                'base_frame': 'base_link',
                'odom_frame': 'odom',
                'map_frame': 'map',
            },
        ],
        output='screen',
        namespace='',
    )

    configure_slam = EmitEvent(
        event=ChangeState(
            lifecycle_node_matcher=matches_action(slam),
            transition_id=Transition.TRANSITION_CONFIGURE,
        ),
    )

    activate_slam = RegisterEventHandler(
        OnStateTransition(
            target_lifecycle_node=slam,
            start_state='configuring',
            goal_state='inactive',
            entities=[
                LogInfo(msg='Activating slam_toolbox.'),
                EmitEvent(
                    event=ChangeState(
                        lifecycle_node_matcher=matches_action(slam),
                        transition_id=Transition.TRANSITION_ACTIVATE,
                    )
                ),
            ],
        )
    )

    rviz = Node(
        package='rviz2',
        executable='rviz2',
        arguments=['-d', rviz_config],
        condition=IfCondition(use_rviz),
        parameters=[{'use_sim_time': True}],
        output='screen',
    )

    delayed_start = TimerAction(
        period=start_delay,
        actions=[
            bridge,
            lidar_tf,
            odom_tf,
            robot_state_publisher,
            slam,
            activate_slam,
            configure_slam,
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
            description='Start RViz with the SLAM verification config.',
        ),
        DeclareLaunchArgument(
            'start_delay',
            default_value='4.0',
            description='Seconds to wait before starting bridge and ROS nodes.',
        ),
        set_env,
        set_sdf_path,
        gazebo_with_gui,
        gazebo_headless,
        delayed_start,
    ])

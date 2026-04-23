import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, SetEnvironmentVariable, TimerAction
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_share = get_package_share_directory('amr_warehouse_sim')
    description_dir = os.path.join(pkg_share, 'description')
    use_gz_gui = LaunchConfiguration('use_gz_gui')
    use_rviz = LaunchConfiguration('use_rviz')
    spawn_delay = LaunchConfiguration('spawn_delay')
    nav2_delay = LaunchConfiguration('nav2_delay')
    spawn_x = LaunchConfiguration('spawn_x')
    spawn_y = LaunchConfiguration('spawn_y')
    spawn_z = LaunchConfiguration('spawn_z')

    world_path = os.path.join(pkg_share, 'worlds', 'warehouse_full.world')
    sdf_path = os.path.join(description_dir, 'sdf', 'my_robot.sdf')
    urdf_path = os.path.join(description_dir, 'urdf', 'my_robot_visual.urdf')
    slam_params_file = os.path.join(pkg_share, 'config', 'mapper_params_online_async.yaml')
    nav2_params_file = os.path.join(pkg_share, 'config', 'nav2_slam_params.yaml')
    rviz_config = os.path.join(pkg_share, 'rviz', 'slam.rviz')

    set_env = SetEnvironmentVariable(
        name='GZ_SIM_RESOURCE_PATH',
        value=[description_dir, ':', os.path.join(pkg_share, 'worlds')],
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

    spawn_robot = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-name', 'my_robot',
            '-file', sdf_path,
            '-x', spawn_x,
            '-y', spawn_y,
            '-z', spawn_z,
        ],
        output='screen',
    )

    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            '/model/my_robot/cmd_vel@geometry_msgs/msg/Twist@gz.msgs.Twist',
            '/model/my_robot/odometry@nav_msgs/msg/Odometry@gz.msgs.Odometry',
            '/model/my_robot/tf@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V',
            '/scan@sensor_msgs/msg/LaserScan@gz.msgs.LaserScan',
            '/clock@rosgraph_msgs/msg/Clock@gz.msgs.Clock',
        ],
        parameters=[{'use_sim_time': True}],
        remappings=[
            ('/model/my_robot/cmd_vel', '/cmd_vel'),
            ('/model/my_robot/tf', '/tf'),
        ],
        output='screen',
    )

    lidar_tf = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        arguments=[
            '0.15', '0', '0.15',
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

    slam = Node(
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
                'publish_map': True,
                'publish_period': 2.0,
            },
        ],
        output='screen',
    )

    nav2_remappings = [
        ('/tf', 'tf'),
        ('/tf_static', 'tf_static'),
    ]

    controller = Node(
        package='nav2_controller',
        executable='controller_server',
        name='controller_server',
        output='screen',
        parameters=[nav2_params_file],
        remappings=nav2_remappings,
    )

    planner = Node(
        package='nav2_planner',
        executable='planner_server',
        name='planner_server',
        output='screen',
        parameters=[nav2_params_file],
        remappings=nav2_remappings,
    )

    smoother = Node(
        package='nav2_smoother',
        executable='smoother_server',
        name='smoother_server',
        output='screen',
        parameters=[nav2_params_file],
        remappings=nav2_remappings,
    )

    behaviors = Node(
        package='nav2_behaviors',
        executable='behavior_server',
        name='behavior_server',
        output='screen',
        parameters=[nav2_params_file],
        remappings=nav2_remappings,
    )

    bt_navigator = Node(
        package='nav2_bt_navigator',
        executable='bt_navigator',
        name='bt_navigator',
        output='screen',
        parameters=[nav2_params_file],
        remappings=nav2_remappings,
    )

    lifecycle_manager = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_navigation',
        output='screen',
        parameters=[{
            'use_sim_time': True,
            'autostart': True,
            'node_names': [
                'controller_server',
                'planner_server',
                'smoother_server',
                'behavior_server',
                'bt_navigator',
            ],
        }],
    )

    rviz = Node(
        package='rviz2',
        executable='rviz2',
        arguments=['-d', rviz_config],
        condition=IfCondition(use_rviz),
        parameters=[{'use_sim_time': True}],
        output='screen',
    )

    simulation_start = TimerAction(
        period=spawn_delay,
        actions=[
            spawn_robot,
            bridge,
            lidar_tf,
            odom_tf,
            robot_state_publisher,
            slam,
        ],
    )

    nav2_start = TimerAction(
        period=nav2_delay,
        actions=[
            controller,
            planner,
            smoother,
            behaviors,
            bt_navigator,
            lifecycle_manager,
            rviz,
        ],
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_gz_gui',
            default_value='true',
            description='Start Gazebo with its GUI. Set to false for headless server-only mode.',
        ),
        DeclareLaunchArgument(
            'use_rviz',
            default_value='true',
            description='Start RViz with the saved SLAM/Nav2 config.',
        ),
        DeclareLaunchArgument(
            'spawn_delay',
            default_value='2.0',
            description='Seconds to wait before spawning the robot and bridge/SLAM nodes.',
        ),
        DeclareLaunchArgument(
            'nav2_delay',
            default_value='6.0',
            description='Seconds to wait before starting Nav2 and RViz.',
        ),
        DeclareLaunchArgument(
            'spawn_x',
            default_value='0.0',
            description='Initial robot x position in the warehouse world.',
        ),
        DeclareLaunchArgument(
            'spawn_y',
            default_value='-6.0',
            description='Initial robot y position in the warehouse world.',
        ),
        DeclareLaunchArgument(
            'spawn_z',
            default_value='0.2',
            description='Initial robot z position in the warehouse world.',
        ),
        set_env,
        gazebo_with_gui,
        gazebo_headless,
        simulation_start,
        nav2_start,
    ])

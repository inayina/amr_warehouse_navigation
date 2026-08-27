"""Gate 1-only mobile-manipulator Gazebo bringup.

This launch does not include the repository's navigation/simulation launches.
It creates one robot_state_publisher and one Gazebo controller manager.  The
native Gazebo DiffDrive plugin owns wheel joints; gz_ros2_control owns only
the arm and gripper joints declared by amr_mm_description.
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, FindExecutable, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time')
    gz_args = LaunchConfiguration('gz_args')
    robot_description = {
        'robot_description': Command([
            FindExecutable(name='xacro'), ' ',
            PathJoinSubstitution([
                FindPackageShare('amr_mm_description'),
                'urdf',
                'mobile_manipulator.urdf.xacro',
            ]),
        ])
    }

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[robot_description, {'use_sim_time': use_sim_time}],
        output='screen',
    )
    spawn = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=['-topic', 'robot_description', '-name', 'mobile_manipulator', '-z', '0.16'],
        output='screen',
    )
    joint_state_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['joint_state_broadcaster', '--controller-manager', '/controller_manager'],
        output='screen',
    )
    arm_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['arm_trajectory_controller', '--controller-manager', '/controller_manager'],
        output='screen',
    )
    gripper_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['gripper_controller', '--controller-manager', '/controller_manager'],
        output='screen',
    )
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=['/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock'],
        output='screen',
    )

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        # -s keeps Gate 1 automation server-only; operators can override gz_args
        # explicitly when they need a Gazebo client.
        DeclareLaunchArgument('gz_args', default_value='-s -r -v 2 empty.sdf'),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(PathJoinSubstitution([
                FindPackageShare('ros_gz_sim'), 'launch', 'gz_sim.launch.py',
            ])),
            launch_arguments={'gz_args': gz_args}.items(),
        ),
        bridge,
        robot_state_publisher,
        spawn,
        RegisterEventHandler(OnProcessExit(target_action=spawn, on_exit=[joint_state_spawner])),
        RegisterEventHandler(OnProcessExit(target_action=joint_state_spawner, on_exit=[arm_spawner])),
        RegisterEventHandler(OnProcessExit(target_action=arm_spawner, on_exit=[gripper_spawner])),
    ])

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import ExecuteProcess, IncludeLaunchDescription, SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node

def generate_launch_description():
    pkg_name = 'amr_warehouse_sim'
    pkg_share = get_package_share_directory(pkg_name)
    nav2_bringup_dir = get_package_share_directory('nav2_bringup')
    description_dir = os.path.join(pkg_share, 'description')
    
    # 路径定义
    world_path = os.path.join(pkg_share, 'worlds', 'warehouse_full.world')
    sdf_path = os.path.join(description_dir, 'sdf', 'my_robot.sdf')
    nav2_params_file = os.path.join(pkg_share, 'config', 'nav2_params.yaml')
    # 指向你建图保存后的地图文件
    map_yaml_file = os.path.join(pkg_share, 'maps', 'warehouse_map.yaml')

    # 环境路径配置
    set_gz_resource = SetEnvironmentVariable(
        name='GZ_SIM_RESOURCE_PATH',
        value=[description_dir, ':', os.path.join(pkg_share, 'worlds')]
    )

    # 1. 启动 Gazebo
    gazebo = ExecuteProcess(cmd=['gz', 'sim', '-r', world_path], output='screen')

    # 2. 生成机器人
    spawn_robot = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=['-name', 'my_robot', '-file', sdf_path, '-z', '0.1'],
        output='screen'
    )

    # 3. 桥接器
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            '/cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist',
            '/odom@nav_msgs/msg/Odometry[gz.msgs.Odometry',
            '/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan',
            '/tf@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V',
            '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock'
        ],
        output='screen'
    )

    # 4. 静态 TF (必须与 SDF 保持一致)
    static_tf = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        arguments=['0.1', '0', '0.1', '0', '0', '0', 'base_link', 'my_robot/base_link/gpu_lidar']
    )

    # 5. 启动 Nav2 Bringup (包含地图服务器和定位)
    start_nav2 = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(nav2_bringup_dir, 'launch', 'bringup_launch.py')),
        launch_arguments={
            'use_sim_time': 'True',
            'params_file': nav2_params_file,
            'map': map_yaml_file,
            'autostart': 'True'
        }.items()
    )

    return LaunchDescription([
        set_gz_resource,
        gazebo,
        spawn_robot,
        bridge,
        static_tf,
        start_nav2
    ])

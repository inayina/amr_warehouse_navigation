import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import ExecuteProcess, SetEnvironmentVariable, DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    # 1. 获取包路径
    pkg_share = get_package_share_directory('amr_warehouse_sim')
    
    # 2. 定义资源路径
    # 确保你的 .world 和 .sdf 文件在对应的文件夹下
    world_path = os.path.join(pkg_share, 'worlds', 'narrow_aisle.world')
    models_path = os.path.join(pkg_share, 'models')

    # 3. 环境变量配置：解决 Gazebo 找不到模型和纹理的问题
    # GZ_SIM_RESOURCE_PATH 是 Gazebo Harmonic 的核心资源搜索路径
    set_gz_resource_path = SetEnvironmentVariable(
        name='GZ_SIM_RESOURCE_PATH',
        value=[os.path.join(pkg_share, 'worlds'), ':', models_path]
    )

    # 4. 启动 Gazebo Harmonic (-r 表示启动后立即开始仿真)
    gazebo = ExecuteProcess(
        cmd=['gz', 'sim', '-r', world_path],
        output='screen'
    )

    # 5. 生成机器人 (Spawn)
    # 对应你计划中的 my_robot.sdf
    spawn_robot = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-name', 'my_robot',
            '-file', os.path.join(models_path, 'my_robot.sdf'),
            '-x', '0.0', '-y', '0.0', '-z', '0.1'
        ],
        output='screen'
    )

    # 6. ROS 与 Gazebo 的桥接器 (Bridge)
    # 将 Gazebo 的扫描数据和图像数据传回 ROS 2，这样你的 YOLO 节点才能收到图
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            '/model/my_robot/cmd_vel@geometry_msgs/msg/Twist@gz.msgs.Twist',
            '/model/my_robot/odometry@nav_msgs/msg/Odometry@gz.msgs.Odometry',
            # 💡 核心修正：必须与 gz topic -l 抓到的名字完全一致
            '/model/my_robot/camera/image_raw@sensor_msgs/msg/Image[gz.msgs.Image',
            '/model/my_robot/camera/camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo',
            '/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan'
        ],
        output='screen'
    )   
    # 7. RViz2 (可选，如果没有配置文件建议先保持默认打开)
    rviz = Node(
        package='rviz2',
        executable='rviz2',
        output='screen'
    )

    return LaunchDescription([
        set_gz_resource_path,
        gazebo,
        spawn_robot,
        bridge,
        rviz
    ])
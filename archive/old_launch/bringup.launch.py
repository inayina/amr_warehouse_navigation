import os
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource

def generate_launch_description():
    launch_dir = '/ros2_ws/src/amr_sim/launch'
    
    return LaunchDescription([
        # 1. 启动仿真和桥接
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(launch_dir, 'simulation.launch.py'))
        ),
        # 2. 启动导航
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(launch_dir, 'navigation.launch.py'))
        ),
        # 3. 启动 AI 诊断
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(launch_dir, 'diagnosis.launch.py'))
        ),
        # 4. 启动 任务调度
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(launch_dir, 'task_system.launch.py'))
        )
    ])

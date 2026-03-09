from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='amr_sim',
            executable='/ros2_ws/src/amr_sim/src/amr_sim/ai_diagnosis/ai_diagnostic_agent.py',
            name='ai_diagnostic_agent',
            output='screen'
        )
    ])

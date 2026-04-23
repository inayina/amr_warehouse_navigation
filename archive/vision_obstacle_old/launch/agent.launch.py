from launch import LaunchDescription
from launch_ros.actions import Node
import os
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    pkg_share = get_package_share_directory('amr_warehouse_sim')
    return LaunchDescription([
        Node(
            package='amr_warehouse_sim',
            executable='agent_node',
            name='agent_node',
            parameters=[os.path.join(pkg_share, 'config', 'agent_params.yaml')],
            output='screen'
        )
    ])
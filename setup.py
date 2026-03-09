from setuptools import setup, find_packages
import os
from glob import glob

package_name = 'amr_warehouse_sim'

setup(
    name=package_name,
    version='0.0.1',
    # 修正点 1：直接在当前目录下寻找包，不再去 'src' 目录下找
    packages=find_packages(), 
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        # 修正点 2：建议使用更稳健的路径获取方式
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
        (os.path.join('share', package_name, 'worlds'), glob('worlds/*.world')),
        (os.path.join('share', package_name, 'models'), glob('models/*.sdf')),
        (os.path.join('share', package_name, 'maps'), glob('maps/*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='ina',
    description='AMR Warehouse Simulation',
    license='MIT',
    entry_points={
        'console_scripts': [
            'detection_node = amr_warehouse_sim.detector_node:main',
            'auto_navigator = amr_warehouse_sim.auto_navigator:main',
            'agent_node = amr_warehouse_sim.agent_node:main',
        ],
    },
)
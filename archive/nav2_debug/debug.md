# Debug Log

记录 2026-04-15 调试 SLAM / Nav2 / Gazebo 的问题和解决过程。

## 当前结论

当前推荐启动方式：

```bash
cd ~/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-select amr_warehouse_sim
source install/setup.bash
ros2 launch amr_warehouse_sim nav2_slam.launch.py
```

当前目标 TF 链：

```text
map -> odom -> base_link -> my_robot/lidar_link/lidar
```

当前关键节点：

```text
/slam_toolbox
/controller_server
/planner_server
/behavior_server
/bt_navigator
/odom_tf_publisher
```

## 1. `/scan` 有 topic 但没有数据

现象：

```bash
ros2 topic list | grep scan
```

能看到：

```text
/scan
```

但：

```bash
ros2 topic echo /scan --once
```

一直没有输出。

排查：

- `description/sdf/my_robot.sdf` 中 lidar sensor 存在。
- `launch/slam_launch.py` bridge 中 `/scan` 存在。
- `worlds/narrow_aisle.world` 有 `gz-sim-sensors-system`。
- `worlds/warehouse_full.world` 缺少 `gz-sim-sensors-system`。

根因：

Gazebo world 没有加载 Sensors system，GPU lidar 不会更新。

修复：

在 `worlds/warehouse_full.world` 顶部加入：

```xml
<plugin filename="gz-sim-sensors-system" name="gz::sim::systems::Sensors">
  <render_engine>ogre2</render_engine>
</plugin>
```

同时补齐：

```xml
<plugin filename="gz-sim-physics-system" name="gz::sim::systems::Physics" />
<plugin filename="gz-sim-user-commands-system" name="gz::sim::systems::UserCommands" />
<plugin filename="gz-sim-scene-broadcaster-system" name="gz::sim::systems::SceneBroadcaster" />
```

验证：

```bash
gz sdf -k worlds/warehouse_full.world
colcon build --symlink-install --packages-select amr_warehouse_sim
ros2 topic hz /scan
```

## 2. RViz 打开后像是没有配置

现象：

`slam_launch.py` 会尝试加载：

```text
rviz/slam.rviz
```

但项目里原来没有这个文件，RViz 以默认空配置启动。

修复：

新增 `rviz/slam.rviz`，显示：

- Grid
- Map `/map`
- LaserScan `/scan`
- Odometry `/model/my_robot/odometry`
- TF
- RobotModel
- Nav2 Navigation 面板
- Nav2 Goal 工具

同时在 `setup.py` 中安装 `.rviz`：

```python
(os.path.join('share', package_name, 'rviz'), glob('rviz/*.rviz')),
```

验证：

```bash
test -f ~/ros2_ws/install/amr_warehouse_sim/share/amr_warehouse_sim/rviz/slam.rviz
```

## 3. 有 SLAM 但想直接用 RViz 发 Nav2 目标

现状：

本机 Nav2 包存在：

```text
nav2_bringup
nav2_map_server
nav2_controller
nav2_planner
nav2_bt_navigator
nav2_amcl
```

但项目原来的 `auto_nav.py` 不能直接用：

- `maps/warehouse.yaml` 是空文件。
- `auto_nav.py` 指向不存在的 `maps/warehouse_map.yaml`。
- bridge 语法和 topic 与当前 Gazebo 模型不一致。
- `bringup.launch.py` 仍包含旧容器路径 `/ros2_ws/src/amr_sim/launch`。

解决：

新增 `launch/nav2_slam.launch.py`，不依赖已有地图，直接在 SLAM 的 `/map` 上启动 Nav2 核心节点：

- `controller_server`
- `planner_server`
- `behavior_server`
- `bt_navigator`
- `lifecycle_manager_navigation`

新增 `config/nav2_slam_params.yaml`，使用当前机器人：

```yaml
robot_base_frame: base_link
odom_topic: /model/my_robot/odometry
scan topic: /scan
```

验证：

```bash
ros2 node list | grep -E 'slam|controller|planner|behavior|bt_navigator'
ros2 action list | grep navigate
ros2 topic list | grep -E '^/map$|scan|odom|cmd_vel'
```

期望看到：

```text
/slam_toolbox
/controller_server
/planner_server
/behavior_server
/bt_navigator
/navigate_to_pose
/cmd_vel
/map
/scan
```

## 4. RViz 和 Gazebo 里肉眼看不到小车

现象：

- Gazebo 里小车很难找。
- RViz 里只能看到地图和 scan，看不到车体。

原因：

- Gazebo 模型本体只有 `0.4 x 0.3 x 0.15m`，在仓库里非常小。
- RViz 不会直接显示 SDF，需要 URDF / `robot_description`。

修复：

Gazebo：

- 在 `description/sdf/my_robot.sdf` 中加了一个红黄小旗杆 `visibility_marker`，只用于视觉定位。

RViz：

- 新增 `description/urdf/my_robot_visual.urdf`。
- 在 `nav2_slam.launch.py` 中启动 `robot_state_publisher`。
- 在 `slam.rviz` 中加入 `RobotModel`。
- 在 `setup.py` 中安装 `urdf/*.urdf`。

验证：

```bash
ros2 topic echo /robot_description --once
```

Gazebo 中可在 Entity Tree 里找 `my_robot` 并 Follow。

## 5. 点目标后小车不动

现象：

RViz 中发送目标后，小车不动。

检查：

```bash
ros2 action info /navigate_to_pose
ros2 topic info /goal_pose -v
ros2 topic echo /cmd_vel --once
```

观察到：

- `/navigate_to_pose` 有 server：`/bt_navigator`
- `/goal_pose` 有 publisher：`/rviz`
- `/goal_pose` 有 subscriber：`/bt_navigator`
- `/cmd_vel` 3 秒内没有实际速度输出

Nav2 日志：

```text
Timed out waiting for transform from base_link to odom to become available
Invalid frame ID "odom" passed to canTransform
```

根因一：

Gazebo `/model/my_robot/tf` 实际消息类型是：

```text
gz.msgs.Pose_V
```

之前 bridge 错写成：

```text
gz.msgs.TFMessage
```

修复：

```python
'/model/my_robot/tf@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V'
```

并 remap：

```python
remappings=[
    ('/model/my_robot/tf', '/tf'),
]
```

根因二：

Gazebo 发布的 TF frame 带模型前缀，和 Nav2 期望不一致。实际看到：

```text
my_robot/odom -> my_robot/base_link
```

而 Nav2 期望：

```text
odom -> base_link
```

同时 `/scan` 的 frame 是：

```text
my_robot/lidar_link/lidar
```

修复：

新增 `amr_warehouse_sim/odom_tf_node.py`：

- 订阅 `/model/my_robot/odometry`
- 发布标准 TF：`odom -> base_link`

修改静态 TF：

```text
base_link -> my_robot/lidar_link/lidar
```

验证：

```bash
ros2 run tf2_ros tf2_echo odom base_link
ros2 run tf2_ros tf2_echo base_link my_robot/lidar_link/lidar
```

这两条成功后，再点 RViz 中的 Nav2 Goal。

## 6. 重启清理命令

调试过程中经常会残留旧 bridge 或旧 Nav2 节点。重启前建议清理：

```bash
pkill -f "gz sim"
pkill -f slam_toolbox
pkill -f rviz2
pkill -f parameter_bridge
pkill -f controller_server
pkill -f planner_server
pkill -f bt_navigator
pkill -f behavior_server
pkill -f odom_tf_node
```

重新启动：

```bash
cd ~/ros2_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 launch amr_warehouse_sim nav2_slam.launch.py
```

## 7. 今日新增/修改文件

新增：

```text
docs/debug.md
amr_warehouse_sim/odom_tf_node.py
config/nav2_slam_params.yaml
rviz/slam.rviz
launch/nav2_slam.launch.py
description/urdf/my_robot_visual.urdf
```

修改：

```text
README.md
description/sdf/my_robot.sdf
package.xml
setup.py
worlds/warehouse_full.world
launch/slam_launch.py
```

## 8. 后续建议

- 把 SDF / URDF 的 frame 命名统一，减少 TF 修正节点。
- 修正 `package.xml` 中 `ros_gz_bridge` 的依赖位置。
- 生成并保存稳定地图后，再做 AMCL + Nav2 的纯导航 launch。
- 如果要正式展示，建议整理一个 `scripts/run_nav2_slam.sh`，避免手动输入长命令。

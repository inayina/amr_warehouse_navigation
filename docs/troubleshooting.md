# V1 Troubleshooting

本文件只记录当前 V1 主线的排障顺序：Gazebo、机器人模型、运动控制、`/scan`、TF、SLAM。

## 1. 确认机器人加载

检查模型路径：

```bash
ros2 pkg prefix amr_warehouse_sim
test -f ~/ros2_ws/install/amr_warehouse_sim/share/amr_warehouse_sim/models/my_robot/model.sdf
test -f ~/ros2_ws/install/amr_warehouse_sim/share/amr_warehouse_sim/models/my_robot/model.config
```

Gazebo 启动后，在 Entity Tree 中确认存在 `my_robot`。当前机器人由 `worlds/warehouse_full.world` 直接 include，不再依赖 launch 启动后的动态 spawn。

## 2. 确认机器人可见

默认生成位置：

```text
x = 0.0, y = 0.0, z = 0.0
```

如果画面里找不到，先在 Entity Tree 里选中 `my_robot` 并 Follow。模型顶部有红黄可视标记，便于在仓库场景中定位。

## 3. 确认机器人可运动

检查 `/cmd_vel`：

```bash
ros2 topic info /cmd_vel
ros2 topic info /cmd_vel -v
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.2}, angular: {z: 0.0}}"
```

如果机器人不动，优先检查：

- Gazebo 中是否真的存在 `my_robot`
- `models/my_robot/model.sdf` 中 diff drive 插件是否加载
- bridge 是否在 ROS 和 Gazebo 之间桥接了 `/cmd_vel`
- 是否有旧的 `ros2 topic pub -r ... /cmd_vel` 进程持续发布速度，覆盖键盘控制
- `teleop_twist_keyboard` 所在终端是否获得键盘焦点

如果键盘控制无反应，先停掉持续速度发布者：

```bash
pkill -f "ros2 topic pub.*cmd_vel"
```

## 4. 确认 `/scan`

```bash
ros2 topic list | grep '^/scan$'
ros2 topic echo /scan --once
ros2 topic hz /scan
```

如果 `/scan` 有 topic 但没有数据，检查 `worlds/warehouse_full.world` 是否加载了 Sensors system：

```xml
<plugin filename="gz-sim-sensors-system" name="gz::sim::systems::Sensors">
  <render_engine>ogre2</render_engine>
</plugin>
```

## 5. 确认 TF

```bash
ros2 run tf2_ros tf2_echo odom base_link
ros2 run tf2_ros tf2_echo base_link my_robot/lidar_link/lidar
```

期望链路：

```text
map -> odom -> base_link -> my_robot/lidar_link/lidar
```

如果 `odom -> base_link` 不存在，检查 `odom_tf_node` 是否启动，以及 `/odom` 是否有数据。

## 6. 确认 SLAM

```bash
ros2 node list | grep slam
ros2 lifecycle get /slam_toolbox
ros2 node info /slam_toolbox | grep -E '/scan|/map'
ros2 topic list | grep '^/map$'
```

`slam_toolbox` 应为 `active [3]`，并且应订阅 `/scan`、发布 `/map`。

如果是 `unconfigured [1]`，当前 launch 没有正确激活 SLAM。可临时手动激活：

```bash
ros2 lifecycle set /slam_toolbox configure
ros2 lifecycle set /slam_toolbox activate
```

RViz Fixed Frame 使用 `map`。机器人运动后，地图应随 `/scan` 数据逐步更新。

## 7. 地图杂乱

地图杂乱时，优先排除运行状态污染：

```bash
pkill -f "gz sim"
pkill -f "ros2 launch amr_warehouse_sim"
pkill -f "ros2 topic pub.*cmd_vel"
pkill -f slam_toolbox
pkill -f rviz2
pkill -f parameter_bridge
pkill -f odom_tf_node
pkill -f robot_state_publisher
pkill -f static_transform_publisher
pkill -f teleop_twist_keyboard
pkill -f smoother_server
```

重新启动后，按小范围闭环建图：

1. 原地慢速转一圈。
2. 前进约 1m。
3. 慢速转向并回到起点附近。
4. 地图稳定后再沿货架通道扩展。

避免高速直冲、贴墙行驶、连续大角速度乱转。当前仓库货架比较对称，太快扫全图容易让 SLAM 匹配到错误通道。

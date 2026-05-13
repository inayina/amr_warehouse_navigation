# AMR Warehouse Troubleshooting

本文件记录当前 V1 建图链路和 V2 Nav2 主线链路的排障顺序：Gazebo、机器人模型、运动控制、`/scan`、`/scan_filtered`、TF、SLAM、地图文件、Nav2 localization、planner / controller / goal 执行。

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

## 5. 确认 `/scan_filtered`

当前建图使用 ROS 现成包 `laser_filters` 过滤 LaserScan：

```text
/scan -> scan_to_scan_filter_chain -> /scan_filtered -> slam_toolbox
```

检查滤波输出：

```bash
ros2 node list | grep scan_to_scan_filter_chain
ros2 topic list | grep '^/scan_filtered$'
ros2 topic echo /scan_filtered --once
ros2 topic hz /scan_filtered
```

如果 `/scan` 正常但 `/scan_filtered` 不存在，优先检查：

- 是否安装 `ros-jazzy-laser-filters`
- `config/laser_filters.yaml` 是否安装到 share 目录
- `launch/slam.launch.py` 是否启动了 `laser_filters/scan_to_scan_filter_chain`
- 终端是否有 filter plugin 加载失败日志

## 6. 确认 TF

```bash
ros2 run tf2_ros tf2_echo odom base_link
ros2 run tf2_ros tf2_echo base_link my_robot/lidar_link/lidar
```

期望链路：

```text
map -> odom -> base_link -> my_robot/lidar_link/lidar
```

如果 `odom -> base_link` 不存在，检查 `odom_tf_node` 是否启动，以及 `/odom` 是否有数据。

## 7. 确认 SLAM

```bash
ros2 node list | grep slam
ros2 lifecycle get /slam_toolbox
ros2 node info /slam_toolbox | grep -E '/scan_filtered|/map'
ros2 topic list | grep '^/map$'
```

`slam_toolbox` 应为 `active [3]`，并且应订阅 `/scan_filtered`、发布 `/map`。

如果是 `unconfigured [1]`，当前 launch 没有正确激活 SLAM。可临时手动激活：

```bash
ros2 lifecycle set /slam_toolbox configure
ros2 lifecycle set /slam_toolbox activate
```

RViz Fixed Frame 使用 `map`。机器人运动后，地图应随 `/scan_filtered` 数据逐步更新。

## 8. 确认已保存地图

当前 Nav2 推荐使用：

```text
maps/warehouse.yaml
```

确认文件存在：

```bash
test -f ~/ros2_ws/src/amr_warehouse_sim/maps/warehouse.yaml
test -f ~/ros2_ws/src/amr_warehouse_sim/maps/warehouse_slam.pgm
```

确认 `warehouse.yaml` 指向正确图像：

```bash
cat ~/ros2_ws/src/amr_warehouse_sim/maps/warehouse.yaml
```

期望包含：

```yaml
image: warehouse_slam.pgm
resolution: 0.050
origin: [-8.008, -8.174, 0]
```

## 9. Nav2 localization 前置检查

先单独验证 `map_server` 和 localization 是否能读取地图，命令要使用当前主线参数文件：

```bash
ros2 launch nav2_bringup localization_launch.py \
  map:=$HOME/ros2_ws/src/amr_warehouse_sim/maps/warehouse.yaml \
  params_file:=$HOME/ros2_ws/src/amr_warehouse_sim/config/nav2_params.yaml \
  use_sim_time:=true
```

检查：

```bash
ros2 lifecycle get /map_server
ros2 topic echo /map --once
ros2 run tf2_ros tf2_echo map odom
```

当前完整 Nav2 主线入口：

```bash
ros2 launch amr_warehouse_sim navigation.launch.py
```

如果使用脚本：

```bash
cd ~/ros2_ws/src/amr_warehouse_sim
./scripts/run_navigation.sh
```

建议再做一次最小闭环验证：

```bash
ros2 lifecycle get /map_server
ros2 lifecycle get /amcl
ros2 lifecycle get /planner_server
ros2 lifecycle get /controller_server
ros2 lifecycle get /bt_navigator
ros2 topic echo /scan_filtered --once
ros2 run tf2_ros tf2_echo map odom
```

如果你希望把 initial pose 设置也做成可复用的命令，而不是只依赖 RViz 点击，仓库现在提供：

```bash
ros2 run amr_warehouse_sim publish_initial_pose --preset start_zone
```

这个工具会向 `/initialpose` 发布 `PoseWithCovarianceStamped`，适合用于无人值守复测、重复排障或在 RViz 不方便操作时替代 `2D Pose Estimate`。

如果是 fresh session / headless 复测，当前更推荐：

```bash
ros2 run amr_warehouse_sim publish_initial_pose --preset start_zone --wait-for-subscribers 30
```

这样可以减少“订阅者尚未就绪就已经开始发布”的偶发波动。

如果已经通过多次短距离 goal 测试，建议把当前版本视为一版稳定基线，并优先固定这版 `config/nav2_params.yaml`，不要在接 WMS 时同时继续改导航参数。

如果 lifecycle nodes 没有进入 `active [3]`：

- 检查 `navigation.launch.py` 是否正常启动 Nav2 bringup
- 检查 `config/nav2_params.yaml` 是否可被读取
- 检查终端里是否有 controller / planner plugin 加载失败日志

如果 RViz 中 RobotModel 不显示：

- 检查 `/robot_description` 是否存在
- 检查 `launch/navigation.launch.py` 是否启动 `robot_state_publisher`
- 检查 `rviz/nav2.rviz` 是否仍在订阅错误的旧 topic

如果 short goal 发出后机器人不动：

- 检查 RViz 是否已执行 `2D Pose Estimate`
- 或直接执行：
  `ros2 run amr_warehouse_sim publish_initial_pose --preset start_zone`
- 检查 `map -> odom -> base_link` 是否连通
- 检查 `/cmd_vel` 是否有输出
- 检查 local/global costmap 是否把通道整段判成障碍
- 检查 footprint 是否与当前机器人外廓一致
- 检查 `collision_monitor` 的 `scan.enabled` 和 `FootprintApproach.enabled` 是否还在误拦车

如果路径能动但明显切角、贴货架、或频繁报 `Failed to make progress`：

- 检查 `progress_checker.required_movement_radius` 是否仍为当前稳定值 `0.10`
- 检查 `CostCritic.consider_footprint` 是否为 `true`
- 检查 local/global `inflation_radius` 是否仍为 `0.40`
- 检查全局规划是否为 `NavfnPlanner + A*`，并且 `allow_unknown: false`
- 先固定当前导航参数，再继续做重复测试，不要一边接任务层一边继续大改导航

如果准备试开 `collision_monitor`：

- 不要直接改当前稳定基线 `config/nav2_params.yaml`
- 先使用 `config/nav2_params_collision_monitor_stage1.yaml` 做第一轮仿真验证
- 先观察是否正常生成 `collision_monitor_state`，以及 goal 发出后是否仍能及时输出 `/cmd_vel`
- 如果在正常通道内出现频繁误停，再继续缩小 stop polygon 或延后启用 `FootprintApproach`

如果 `/map` 没有数据：

- 检查 `maps/warehouse.yaml` 的 `image` 路径
- 确认 `warehouse_slam.pgm` 和 YAML 在同一目录
- 确认 `nav2_map_server` 已安装

如果 `map -> odom` 不存在：

- 确认 AMCL 已启动
- 确认 RViz 已设置 initial pose
- 或直接发布：
  `ros2 run amr_warehouse_sim publish_initial_pose --preset start_zone`
- 确认 `/scan` 正常
- 确认 `odom -> base_link` 正常

## 10. 确认固定任务点配置

当前主线固定任务点入口是：

```text
config/task_points.yaml
```

快速检查：

```bash
sed -n '1,220p' ~/ros2_ws/src/amr_warehouse_sim/config/task_points.yaml
```

当前期望：

- `start_zone` 存在，且与 `publish_initial_pose --preset start_zone` 对齐
- `station_a`、`station_b`、`shelf_1`、`shelf_2` 已有实际数值，不再是 `TBD`
- 所有主线点位都使用 `frame_id: map`

如果你是在排查最小 Mock WMS 数据层，而不是 Nav2 本身，可额外做一个不启动 Gazebo 的数据层 smoke test：

```bash
python3 ~/ros2_ws/src/amr_warehouse_sim/scripts/init_mock_wms_db.py --db-path /tmp/mock_wms_smoke.db
python3 ~/ros2_ws/src/amr_warehouse_sim/scripts/create_mock_task.py --db-path /tmp/mock_wms_smoke.db --target station_a
python3 ~/ros2_ws/src/amr_warehouse_sim/scripts/list_mock_tasks.py --db-path /tmp/mock_wms_smoke.db
```

如果 `create_mock_task.py` 报目标点不存在或字段仍是 `TBD`，优先检查 `config/task_points.yaml` 是否与当前主线文档一致。

如果 `map -> odom` 存在，但冷启动后 LaserScan 和地图要经过 2 到 3 次修正才逐步对齐：

- 先把问题优先归类为 localization / map alignment，不要继续直接调 `collision_monitor`
- 当前已观察到：保存地图与 Gazebo 世界可能存在约 90 度朝向差异，导致 initial pose 按地图方向设置时，AMCL 需要通过运动后再逐步收敛
- 如果只是在做演示或短距离验证，优先回退到当前稳定基线 `maps/warehouse.yaml` + `config/nav2_params.yaml`
- `maps/warehouse_gazebo_aligned_candidate.yaml` 和 `maps/warehouse_slam_gazebo_aligned_candidate.pgm` 当前只作为实验候选，不应视为主线基线
- 在 localization 冷启动一致性没有收稳前，不建议继续推进 `collision_monitor stage1`、多任务 runtime flow 或更复杂的任务调度验证

## 10. 当前稳定化结论

当前已经验证有效的 Nav2 稳定化结论如下：

- `odom_tf_node` 需要尽早提供 `odom -> base_link`，避免 controller 在启动阶段因缺 TF 卡住
- 当前机器人外廓应按矩形 footprint 配置，而不是继续按偏小半径处理
- `progress_checker.required_movement_radius` 使用 `0.10` 更适合当前仓库短距离 goal
- `CostCritic.consider_footprint` 需要开启，减少切角和贴障碍
- local/global `inflation_radius` 收敛到 `0.40` 后，通道可行域更接近当前仓库布局
- 全局规划使用 `NavfnPlanner + A*` 且 `allow_unknown: false`，路径更适合作为任务点导航基础
- 当前稳定基线中，`collision_monitor` 的 `scan` 和 `FootprintApproach` 监测项处于关闭状态；后续进入 WMS 或真机前，需要把安全策略单独收口

## 11. 地图杂乱

地图杂乱时，优先排除运行状态污染：

```bash
pkill -f "gz sim"
pkill -f "ros2 launch amr_warehouse_sim"
pkill -f "ros2 topic pub.*cmd_vel"
pkill -f slam_toolbox
pkill -f rviz2
pkill -f parameter_bridge
pkill -f scan_to_scan_filter_chain
pkill -f odom_tf_node
pkill -f robot_state_publisher
pkill -f static_transform_publisher
pkill -f teleop_twist_keyboard
pkill -f smoother_server
pkill -f behavior_server
pkill -f bt_navigator
pkill -f waypoint_follower
pkill -f velocity_smoother
pkill -f map_server
pkill -f amcl
pkill -f controller_server
pkill -f planner_server
```

重新启动后，按小范围闭环建图：

1. 原地慢速转一圈。
2. 前进约 1m。
3. 慢速转向并回到起点附近。
4. 地图稳定后再沿货架通道扩展。

避免高速直冲、贴墙行驶、连续大角速度乱转。当前仓库货架比较对称，太快扫全图容易让 SLAM 匹配到错误通道。

# SLAM And Nav2 Notes

日期：`2026-05-27`

## 1. Purpose

本文件整理当前 AMR 仿真导航子系统中 SLAM、Nav2、AMCL、`map_server`、planner 和 controller 的配置关系。它只描述当前主线文件之间的职责边界，不提出本轮参数修改。

## 2. Main Files

| 文件 | 角色 |
| --- | --- |
| `launch/slam.launch.py` | V1 建图入口，启动仿真、雷达滤波、SLAM Toolbox 和 RViz 建图视图 |
| `launch/navigation.launch.py` | V2 / V3 导航主入口，启动 Gazebo、bridge、TF、Nav2、AMCL、RViz |
| `config/laser_filters.yaml` | 将 `/scan` 过滤为 `/scan_filtered`，供 SLAM 与 Nav2 使用 |
| `config/slam_toolbox.yaml` | SLAM Toolbox 参数入口 |
| `config/nav2_params.yaml` | 当前 Nav2 稳定基线参数入口 |
| `maps/warehouse.yaml` | Nav2 `map_server` 读取的稳定地图入口 |
| `config/task_points.yaml` | 固定 initial pose 和业务目标点入口 |

## 3. Data Relationship

```text
Gazebo
  -> /scan
  -> laser_filters
  -> /scan_filtered
  -> SLAM Toolbox
  -> maps/warehouse.yaml + maps/warehouse_slam.pgm
  -> map_server
  -> AMCL
  -> map -> odom -> base_link
  -> Nav2 planner / controller / bt_navigator
  -> /cmd_vel
  -> Gazebo AMR
```

当前地图由 V1 SLAM 链路生成，V2 / V3 导航链路通过 `maps/warehouse.yaml` 复用该地图。任务层不直接生成地图，也不直接改写 Nav2 参数。

## 4. SLAM Relationship

SLAM 侧的核心关系是：

- Gazebo 提供 `/scan`、`/odom` 和 robot TF。
- `laser_filters` 输出 `/scan_filtered`，用于减少雷达噪声对建图和定位的影响。
- SLAM Toolbox 使用仿真时间、滤波后的 LaserScan 和 odom / TF 生成 `/map`。
- 保存后的地图文件进入 `maps/warehouse.yaml`，成为 Nav2 的长期入口。

当前 V1 已完成，后续除非明确处理建图问题，否则不应随意改动 `slam.launch.py`、`laser_filters.yaml`、`slam_toolbox.yaml` 或已保存地图。

## 5. Nav2 And AMCL Relationship

Nav2 导航侧的核心关系是：

- `map_server` 读取 `maps/warehouse.yaml` 并发布 `/map`。
- AMCL 订阅地图、LaserScan 和 TF，通过 `/initialpose` 建立 `map -> odom`。
- `publish_initial_pose --preset start_zone` 是当前主线推荐的 initial pose 脚本化入口。
- `planner_server` 使用 global costmap 和地图生成全局路径。
- `controller_server` 使用 local costmap、机器人 footprint 和控制器参数输出 `/cmd_vel`。
- `bt_navigator` 对外暴露 `/navigate_to_pose` action，是 executor / task runner 的执行目标。

fresh session 下，`map -> odom`、lifecycle active 状态和 `/navigate_to_pose` action server 可见性需要一起确认，不能只看单个信号。

## 6. Map Server And AMCL Checklist

启动 `navigation.launch.py` 后，建议检查：

```bash
ros2 lifecycle get /map_server
ros2 lifecycle get /amcl
ros2 topic echo /map --once
ros2 topic echo /scan_filtered --once
ros2 run tf2_ros tf2_echo map odom
```

若 `map -> odom` 尚未建立，先发布 initial pose：

```bash
ros2 run amr_warehouse_sim publish_initial_pose --preset start_zone --wait-for-subscribers 30
```

## 7. Planner And Controller Checklist

goal 执行前建议确认：

```bash
ros2 lifecycle get /planner_server
ros2 lifecycle get /controller_server
ros2 lifecycle get /bt_navigator
ros2 action info /navigate_to_pose
```

通过标准：

- `map_server`、`amcl`、`planner_server`、`controller_server`、`bt_navigator` 均为 `active [3]`
- `/navigate_to_pose` 至少有 1 个 action server
- `map -> odom -> base_link` TF 连通
- RViz 中 Map、LaserScan、RobotModel、global/local costmap 对齐

## 8. Task Layer Boundary

Mock WMS 任务层只消费 `config/task_points.yaml` 和 Nav2 action：

- 不直接修改 `navigation.launch.py`
- 不直接修改 `config/nav2_params.yaml`
- 不直接控制 `/cmd_vel`
- 不重新生成地图
- 不把历史 `future_extensions/` 逻辑接回主线默认入口

任务执行结果应通过 SQLite 或 HTTP API 写回任务状态，作为 Robot Ops Dashboard 可读取的数据来源。

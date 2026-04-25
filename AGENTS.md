# AI 协作约束

本文件用于约束 AI / Coding Agent 在本仓库中的修改范围和工作方式。项目状态与路线图以 `docs/design.md` 为准。

## 当前项目阶段

当前状态：

- **V1：AMR 仿真建图最小闭环已完成**
- 已保存 Nav2 可用地图：`maps/warehouse.yaml`
- 当前阶段为 **V2：Nav2 导航与路径执行**

V1 稳定链路：

```text
Gazebo
→ /scan
→ laser_filters / /scan_filtered
→ odom + TF
→ slam_toolbox
→ /map
→ maps/warehouse.yaml
```

V2 预期链路：

```text
maps/warehouse.yaml
→ nav2_map_server
→ AMCL / localization
→ map -> odom -> base_link
→ Nav2 planner / controller
→ /cmd_vel
→ Gazebo robot
```

## 必须遵守的约束

### 1. 一次只解决一个明确问题

每轮修改只处理一个主问题，例如：

- 修复 SLAM 链路
- 调整 LaserScan 滤波
- 验证地图文件
- 接入 Nav2 localization
- 调整 Nav2 planner / controller

不得在同一轮中同时重写多个模块或混合处理多个主问题。

### 2. 修改前必须先说明判断

在修改代码或配置前，必须先说明：

1. 当前判断的问题点是什么
2. 准备修改哪些文件
3. 每个修改的目的是什么
4. 修改后预期看到什么现象

### 3. 不要破坏已完成的 V1

V1 已经可以建图并保存地图，后续修改不得破坏：

- `launch/slam.launch.py`
- `config/laser_filters.yaml`
- `config/slam_toolbox.yaml`
- `maps/warehouse.yaml`
- `maps/warehouse_slam.pgm`
- `amr_warehouse_sim/odom_tf_node.py`

如果需要改动以上文件，必须说明原因和回退方式。

### 4. Nav2 只按阶段推进

当前 V2 主线文件：

- `launch/navigation.launch.py`
- `config/nav2_params.yaml`
- `scripts/run_navigation.sh`
- `maps/warehouse.yaml`
- `rviz/nav2.rviz`

不得在非相关任务中擅自：

- 混入完整 WMS / 调度系统
- 引入 CAD 路径控制
- 引入多车协同
- 重构机器人模型或 Gazebo 世界
- 把 `archive/` 或 `future_extensions/` 接回当前主线

### 5. 优先最小改动

优先使用最小、可验证的改动修复问题；不做无必要重构，不改无关文件。

## 推荐排障顺序

### V1：建图链路

1. 确认 Gazebo 中存在 `my_robot`
2. 确认 `/cmd_vel` 可控制机器人
3. 确认 `/scan` 正常
4. 确认 `/scan_filtered` 正常
5. 确认 TF：`odom -> base_link -> my_robot/lidar_link/lidar`
6. 确认 `slam_toolbox` 输出 `/map`
7. 确认地图保存到 `maps/warehouse.yaml`

### V2：Nav2 链路

1. 确认 `maps/warehouse.yaml` 可被 `map_server` 读取
2. 确认 `/map` 正常发布
3. 确认 AMCL / localization 可启动
4. 确认 TF：`map -> odom -> base_link`
5. 确认 Nav2 lifecycle nodes 为 active
6. 设置 initial pose
7. 发送短距离 goal 验证 `/cmd_vel`

## 当前允许优先修改的文件范围

通用文档与配置：

- `README.md`
- `AGENTS.md`
- `docs/design.md`
- `docs/troubleshooting.md`
- `package.xml`
- `setup.py`

V1 维护文件：

- `launch/slam.launch.py`
- `launch/simulation.launch.py`
- `config/laser_filters.yaml`
- `config/slam_toolbox.yaml`
- `rviz/slam.rviz`
- `maps/warehouse.yaml`

V2 主线文件：

- `launch/navigation.launch.py`
- `config/nav2_params.yaml`
- `scripts/run_navigation.sh`
- `rviz/nav2.rviz`

## 当前禁止操作

- 不要大规模重构整个项目
- 不要同时重写 launch、world、model、config 多个层级
- 不要修改 `build/`、`install/`、`log/` 生成目录
- 不要删除已保存地图，除非用户明确要求重新建图
- 不要把历史 Nav2 / 旧 TF / 旧 launch 逻辑直接接回当前主线

## 文档入口

- 当前设计说明：`docs/design.md`
- 排障记录：`docs/troubleshooting.md`
- 项目入口说明：`README.md`
- Nav2 地图入口：`maps/warehouse.yaml`

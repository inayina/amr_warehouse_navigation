# Mock WMS Task Runner Live Validation

日期：`2026-05-13`

## 1. 结论

本轮**真正执行了 live ROS / Nav2 验证**，并且使用了 fresh session：

- 已重新执行 `colcon build --packages-select amr_warehouse_sim`
- 已在后续 live 命令中显式 `source /opt/ros/jazzy/setup.bash` 与 `source /home/ina/ros2_ws/install/setup.bash`
- 实际 launch 命令为：
  `ros2 launch amr_warehouse_sim navigation.launch.py use_gz_gui:=false use_rviz:=false`
- 本轮**未修改** `navigation.launch.py`
- 本轮**未修改** `config/nav2_params.yaml`
- 本轮**未修改** 地图、world、robot model

V3.1 `mock_wms_task_runner` 本轮 live 结果为：

- `--dry-run`：ready gate 通过，但**未发送** `/navigate_to_pose` goal
- `--execute --max-tasks 1`：成功发送 goal，action result 为 `SUCCEEDED`
- `--execute --max-tasks 2`：顺序执行 `station_a`、`station_b`，两条都 `SUCCEEDED`

## 2. 修改前判断

本轮主问题是验证 `mock_wms_task_runner` 在真实 Nav2 会话中的顺序执行闭环，而不是新增功能或调整导航参数。

本轮唯一新增文件：

- `docs/wms/reports/mock_wms_task_runner_live_validation_2026_05_13.md`

目的：

- 记录真实 CLI 输出
- 记录 ready gate、goal 发送、action result、SQLite 最终状态
- 明确声明本轮没有改 Nav2 / 地图 / world / 机器人模型

## 3. 验证流程

本轮按下面顺序执行：

1. 清理旧 Gazebo / Nav2 / bridge / RViz / TF 相关进程。
2. 重新 build 当前包：
   `colcon build --packages-select amr_warehouse_sim`
3. 启动 headless navigation：
   `ros2 launch amr_warehouse_sim navigation.launch.py use_gz_gui:=false use_rviz:=false`
4. 发布 initial pose：
   `ros2 run amr_warehouse_sim publish_initial_pose --preset start_zone --wait-for-subscribers 30`
5. 初始化 Mock WMS SQLite DB 并创建任务。
6. 分别执行 dry-run、单任务 execute、双任务顺序 execute。

## 4. 执行命令摘要

```bash
ros2 run amr_warehouse_sim init_mock_wms_db --db data/mock_wms.db
ros2 run amr_warehouse_sim create_mock_task --db data/mock_wms.db --target station_a
ros2 run amr_warehouse_sim mock_wms_task_runner --db data/mock_wms.db --dry-run
```

```bash
ros2 run amr_warehouse_sim mock_wms_task_runner \
  --db data/mock_wms.db \
  --execute \
  --max-tasks 1 \
  --ready-timeout 60
```

```bash
ros2 run amr_warehouse_sim create_mock_task --db data/mock_wms.db --target station_a
ros2 run amr_warehouse_sim create_mock_task --db data/mock_wms.db --target station_b
ros2 run amr_warehouse_sim mock_wms_task_runner \
  --db data/mock_wms.db \
  --execute \
  --max-tasks 2 \
  --ready-timeout 60
```

## 5. 结果摘要

| 验证项 | 预期 | 实际结果 | 结论 |
| --- | --- | --- | --- |
| dry-run | 只检查 ready gate，不发送 goal | ready gate 通过，未发送 `/navigate_to_pose` | 通过 |
| `--execute --max-tasks 1` | 消费 1 条 pending task | `station_a` goal 发送成功，结果 `SUCCEEDED` | 通过 |
| `--execute --max-tasks 2` | 顺序消费 2 条 pending task | `station_a -> station_b` 均 `SUCCEEDED` | 通过 |
| SQLite 状态回写 | 成功任务最终为 `succeeded` | 两条任务最终均为 `succeeded`，`status_reason` 记录 Nav2 result | 通过 |

## 6. 边界说明

- 本轮验证的是当前主线最小任务执行链，不是完整 WMS / 调度系统。
- `mock_wms_task_runner` 不直接控制 `/cmd_vel`，只在 ready gate 满足后通过 Nav2 `NavigateToPose` action 发送目标。
- dry-run 不会假装消费队列，也不会发送 goal。
- 本轮没有改 `navigation.launch.py`、`config/nav2_params.yaml`、地图、world 或 robot model。

## 7. 后续建议

- 保持 `navigation.launch.py` + `config/nav2_params.yaml` 作为稳定基线。
- 继续追加更多 business-point execute 重复验证，尤其是 `shelf_1`、`shelf_2`。
- 后续如要推进常驻服务或调度层，应另开阶段，不与 Nav2 参数调优混在同一轮。

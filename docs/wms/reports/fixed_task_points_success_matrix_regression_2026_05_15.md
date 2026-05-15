# Fixed Task-Point Success Matrix Regression

日期：`2026-05-15`

## 1. 结论

本轮已经完成当前主线四个固定任务点的 fresh-session 矩阵回归，结论为：`Pass`。

本轮计入结果的点位：

- `station_a`
- `station_b`
- `shelf_1`
- `shelf_2`

本轮结果：

- 四个点位都在独立 fresh session 中拿到了真实 `SUCCEEDED` 证据
- 四条任务的 SQLite 最终状态都回写为 `succeeded`
- `shelf_2` 虽然最终成功，但执行过程中出现了多次 `Failed to make progress`、costmap clear 和 recovery 行为，应继续保留为当前主线的运行时边界信息

## 2. 修改前判断

本轮主问题不是新增功能，而是把“固定任务点矩阵回归”从场景定义推进到真实运行报告，方便后续做验收、简历展示和面试讲解。

本轮文档改动文件：

- `docs/wms/reports/fixed_task_points_success_matrix_regression_2026_05_15.md`
- `docs/acceptance_checklist.md`

本轮未修改：

- `launch/navigation.launch.py`
- `config/nav2_params.yaml`
- `config/task_points.yaml`
- 地图、world、robot model

## 3. 范围与方法

提交版本：

```text
f679732
```

本轮执行方法：

1. 每个点位都使用独立 fresh headless Nav2 会话：
   `ros2 launch amr_warehouse_sim navigation.launch.py use_gz_gui:=false use_rviz:=false`
2. 每个会话都发布统一 initial pose：
   `python3 scripts/publish_initial_pose.py --preset start_zone --wait-for-subscribers 30`
3. 只有在以下证据都出现后才执行：
   `Managed nodes are active`
   `ros2 lifecycle nodes` 已发现 `/map_server`、`/amcl`、`/planner_server`、`/controller_server`、`/bt_navigator`
   `tf2_echo map odom` 返回有效变换
   `ros2 action info /navigate_to_pose` 显示 `Action servers: 1`
4. 每个点位都使用独立 SQLite DB 创建单条 pending task，再用 `mock_wms_executor --execute` 触发 Nav2 执行。

日志根目录：

```text
/tmp/mock_wms_executor_validation_ros_logs
```

说明：

- 本报告日期使用本地日期 `2026-05-15`。
- SQLite `created_at` / `updated_at` 使用 UTC，因此表内时间显示为 `2026-05-14T16:xx:xxZ`，这与本地时区相差 8 小时，属于正常现象。

## 4. 执行命令摘要

```bash
ros2 launch amr_warehouse_sim navigation.launch.py use_gz_gui:=false use_rviz:=false
python3 scripts/publish_initial_pose.py --preset start_zone --wait-for-subscribers 30
ros2 lifecycle nodes
timeout 4s ros2 run tf2_ros tf2_echo map odom
ros2 action info /navigate_to_pose
```

```bash
ros2 run amr_warehouse_sim init_mock_wms_db --db /tmp/fixed_task_matrix_<point>_2026_05_15.db
ros2 run amr_warehouse_sim create_mock_task --db /tmp/fixed_task_matrix_<point>_2026_05_15.db --target <point>
ros2 run amr_warehouse_sim mock_wms_executor --db /tmp/fixed_task_matrix_<point>_2026_05_15.db --execute --ready-timeout 60 --navigation-timeout 180
```

## 5. 矩阵结果

| Run ID | Point | Ready 证据 | Executor 结果 | SQLite 最终状态 | 完成耗时 | 运动证据 | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `FTM-01` | `station_a` | 满足 | `NavigateToPose result: SUCCEEDED.` | `succeeded` | `113s` | `Received a goal`、Gazebo Twist bridge、`Reached the goal!`、`Goal succeeded` | 首条基准点稳定通过。 |
| `FTM-02` | `station_b` | 满足 | `NavigateToPose result: SUCCEEDED.` | `succeeded` | `37s` | `Received a goal`、Gazebo Twist bridge、`Reached the goal!`、`Goal succeeded` | 计入结果的尝试稳定通过。 |
| `FTM-03` | `shelf_1` | 满足 | `NavigateToPose result: SUCCEEDED.` | `succeeded` | `38s` | `Received a goal`、Gazebo Twist bridge、`Reached the goal!`、`Goal succeeded` | 本轮单次 fresh session 即通过。 |
| `FTM-04` | `shelf_2` | 满足 | `NavigateToPose result: SUCCEEDED.` | `succeeded` | `88s` | `Received a goal`、Gazebo Twist bridge、最终 `Goal succeeded` | 中途多次 `Failed to make progress`，触发 clear / recovery / spin 后恢复成功。 |

## 6. 关键运行证据

`station_a`：

- `Begin navigating from current location (0.01, 0.02) to (-5.30, -5.80)`
- `Received a goal, begin computing control effort.`
- `Passing message from ROS geometry_msgs/msg/Twist to Gazebo gz.msgs.Twist`
- `Reached the goal!`
- `Goal succeeded`

`station_b`：

- `Begin navigating from current location (0.02, 0.02) to (5.00, -4.80)`
- `Received a goal, begin computing control effort.`
- `Reached the goal!`
- `Goal succeeded`

`shelf_1`：

- `Begin navigating from current location (0.02, 0.03) to (-2.75, 2.50)`
- `Received a goal, begin computing control effort.`
- `Reached the goal!`
- `Goal succeeded`

`shelf_2`：

- `Begin navigating from current location (0.02, 0.02) to (2.75, 2.50)`
- 多次 `Failed to make progress`
- `Received request to clear entirely the local_costmap`
- `Received request to clear entirely the global_costmap`
- `behavior_server: spin completed successfully`
- 最终 `Reached the goal!` 与 `Goal succeeded`

这说明 `shelf_2` 当前并不是“无条件稳定点”，而是“经过恢复行为后本轮完成成功”的点位。

## 7. SQLite 状态回写结果

本轮四个临时数据库的最终状态如下：

| Point | DB Path | Final Status | Status Reason |
| --- | --- | --- | --- |
| `station_a` | `/tmp/fixed_task_matrix_station_a_2026_05_15.db` | `succeeded` | `NavigateToPose result: SUCCEEDED.` |
| `station_b` | `/tmp/fixed_task_matrix_station_b_2026_05_15.db` | `succeeded` | `NavigateToPose result: SUCCEEDED.` |
| `shelf_1` | `/tmp/fixed_task_matrix_shelf_1_2026_05_15.db` | `succeeded` | `NavigateToPose result: SUCCEEDED.` |
| `shelf_2` | `/tmp/fixed_task_matrix_shelf_2_2026_05_15.db` | `succeeded` | `NavigateToPose result: SUCCEEDED.` |

## 8. 过程说明

- `station_b` 过程中有一次本地测试操作失误：我把 DB `init` 和 `create` 并行触发，导致 executor 看到的是空库并返回 `no-pending-task`。
- 这个结果不是 Nav2 或任务点失败，而是测试准备错误，因此没有计入本报告矩阵结果。
- 计入本轮报告的 `station_b` 结果，是随后在同一会话里重新按顺序建库、建任务后得到的真实 `SUCCEEDED` 结果。

## 9. 结论与边界

本轮可以确认：

- 当前主线四个固定任务点都具备 fresh-session 的真实成功证据
- 这四个点位可以继续作为“最小 Mock WMS 任务执行闭环”的主线业务点使用
- 当前项目已经具备“固定任务点 -> 单任务执行 -> Nav2 导航成功 -> 状态回写”的可复核矩阵证据

同时仍需保持以下口径：

- 这些点位仍然是当前主线候选业务点，不应直接表述为最终仓库业务坐标
- `shelf_2` 仍存在明显运行时波动，应继续保留为“通过，但边界明确”的点位
- 历史 `SKIPPED / ABORTED` 证据仍以 [wms_task_points_readiness_report_2026_05_13.md](./wms_task_points_readiness_report_2026_05_13.md) 为准，本轮重点是补一轮 fresh-session 全成功回归

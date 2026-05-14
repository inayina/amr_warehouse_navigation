# WMS 任务点就绪性报告

日期：`2026-05-13`

本报告基于 [repeat_navigation_test_report_2026_05_13.md](../../reports/repeat_navigation_test_report_2026_05_13.md)，补充记录主要业务任务点的最终 WMS 就绪性验证结果：

- `station_a`
- `station_b`
- `shelf_1`
- `shelf_2`

站点 / 货架坐标仍然来自 [task_points_coordinate_plan.md](../../task_points_coordinate_plan.md) 中的候选坐标。本报告只记录真实 fresh-session 结果，并不代表仓库业务坐标已经最终定稿。

## 范围

- 本轮未修改 `launch/navigation.launch.py`。
- 本轮未修改 `config/nav2_params.yaml`。
- 本轮未修改地图、world 或机器人模型。
- 本轮未修改 `config/task_points.yaml`。
- 只有在全部前置条件确认满足后，才发送 Nav2 goal：
  `5/5 lifecycle active`、`map -> odom` 可用、`/navigate_to_pose` action server 数量为 `1`，并且 `start_zone` initial pose 已发布。
- 导航成功后，最小化扩展了 Mock WMS allowlist，使这些已验证点位可以被创建为 `pending` 任务。

## 验证流程

每一次计入结果的导航尝试都使用独立 fresh session：

1. 清理遗留的 Nav2 / Gazebo / bridge / robot-state / odom-TF 进程，并停止 ROS daemon。
2. 启动 headless navigation：
   `ros2 launch amr_warehouse_sim navigation.launch.py use_gz_gui:=false use_rviz:=false`
3. 在启动后约 `T+10s` 发布 initial pose：
   `ros2 run amr_warehouse_sim publish_initial_pose --preset start_zone --wait-for-subscribers 30`
4. 按需在 `T35`、`T55`、`T75`、`T95`、`T120` 采样前置条件。
5. 仅在所有前置条件满足后发送 `/navigate_to_pose`。

日志目录：

```text
/tmp/amr_wms_point_readiness_2026_05_13_confirm
```

## 导航结果

| Run ID | 点位名称 | Goal X / Y / Yaw | Initial Pose | 发 goal 前 Lifecycle / TF / Action 状态 | Goal 结果 | `/cmd_vel` | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `WMS-RUN-01` | `station_a` | `-5.3 / -5.8 / 3.14` | `10/10` published | `T55`：5 个 lifecycle nodes 全部 `active [3]`，`map -> odom` 可用，action servers 数量为 `1` | `SUCCEEDED` | `yes` | 更早的 `T35` 采样中 `/map_server` 和 `/amcl` 仍存在 discovery gap；只有在 `T55` 完整确认后才发送 goal。 |
| `WMS-RUN-02` | `station_b` | `5.0 / -4.8 / 0.0` | `10/10` published | `T120`：`/map_server inactive [2]`、`/amcl unconfigured [1]`、`/planner_server inactive [2]`、`/controller_server active [3]`、`/bt_navigator inactive [2]`，`map -> odom` 不可用，action servers 数量为 `1` | `SKIPPED` | `no` | 前置条件未 ready，因此没有发送 goal。 |
| `WMS-RUN-03` | `station_b` | `5.0 / -4.8 / 0.0` | `10/10` published | `T55`：5 个 lifecycle nodes 全部 `active [3]`，`map -> odom` 可用，action servers 数量为 `1` | `SUCCEEDED` | `yes` | 第二次 fresh session 达到完整 ready 状态并完成 goal。 |
| `WMS-RUN-04` | `shelf_1` | `-2.75 / 2.5 / 0.0` | `10/10` published | `T55`：5 个 lifecycle nodes 全部 `active [3]`，`map -> odom` 可用，action servers 数量为 `1` | `ABORTED` | `yes` | 这是前置条件有效后的真实 goal 结果；保留为运行时波动证据。 |
| `WMS-RUN-05` | `shelf_1` | `-2.75 / 2.5 / 0.0` | `10/10` published | `T55`：5 个 lifecycle nodes 全部 `active [3]`，`map -> odom` 可用，action servers 数量为 `1` | `SUCCEEDED` | `yes` | 第二次 fresh session 成功完成。 |
| `WMS-RUN-06` | `shelf_2` | `2.75 / 2.5 / 3.14` | `10/10` published | `T55`：5 个 lifecycle nodes 全部 `active [3]`，`map -> odom` 可用，action servers 数量为 `1` | `ABORTED` | `no` | 这是前置条件有效后的真实 goal 结果；本轮未捕获到 `/cmd_vel` sample。 |
| `WMS-RUN-07` | `shelf_2` | `2.75 / 2.5 / 3.14` | `10/10` published | `T55`：5 个 lifecycle nodes 全部 `active [3]`，`map -> odom` 可用，action servers 数量为 `1` | `SUCCEEDED` | `yes` | 第二次 fresh session 成功完成。 |

## WMS 数据层结果

在四个业务点都至少获得一次真实 `SUCCEEDED` 导航结果后，Mock WMS 被最小化更新，以接受这些已验证目标点：

- `scripts/mock_wms_db_common.py`：扩展 `SUPPORTED_V3_TARGET_NAMES`。
- `test/integration/test_mock_wms_db.py`：增加 `station_a`、`station_b`、`shelf_1`、`shelf_2` 创建为 pending map task 的覆盖。
- `docs/designs/mock_wms_design.md`：更新数据层范围和任务点关系说明。

验证命令：

```bash
pytest test/data/test_task_points.py test/integration/test_mock_wms_db.py
```

结果：

```text
9 passed
```

CLI smoke test：

```bash
python3 scripts/init_mock_wms_db.py --db-path /tmp/mock_wms_ready_points_2026_05_13.db
python3 scripts/create_mock_task.py --db-path /tmp/mock_wms_ready_points_2026_05_13.db --target station_a
python3 scripts/create_mock_task.py --db-path /tmp/mock_wms_ready_points_2026_05_13.db --target station_b
python3 scripts/create_mock_task.py --db-path /tmp/mock_wms_ready_points_2026_05_13.db --target shelf_1
python3 scripts/create_mock_task.py --db-path /tmp/mock_wms_ready_points_2026_05_13.db --target shelf_2
python3 scripts/list_mock_tasks.py --db-path /tmp/mock_wms_ready_points_2026_05_13.db
```

观察结果：

| Target | Frame | X | Y | Yaw | Status |
| --- | --- | --- | --- | --- | --- |
| `station_a` | `map` | `-5.3` | `-5.8` | `3.14` | `pending` |
| `station_b` | `map` | `5.0` | `-4.8` | `0.0` | `pending` |
| `shelf_1` | `map` | `-2.75` | `2.5` | `0.0` | `pending` |
| `shelf_2` | `map` | `2.75` | `2.5` | `3.14` | `pending` |

## 总结

| 类别 | 点位 |
| --- | --- |
| 已具备 WMS 就绪性导航成功证据 | `station_a`、`station_b`、`shelf_1`、`shelf_2` |
| 真实 skipped 尝试 | `station_b` 第 1 次尝试 |
| 真实 aborted 尝试 | `shelf_1` 第 1 次尝试、`shelf_2` 第 1 次尝试 |
| 仍没有任何成功记录的业务点 | `none` |
| Mock WMS pending-task 创建验证 | `station_a`、`station_b`、`shelf_1`、`shelf_2` 均已验证 |

## 建议

这四个业务点已经可以用于 Mock WMS 数据层 intake 和 task-executor 集成实验。它们仍应被视为候选坐标，而不是最终仓库坐标。

在将其称为生产稳定点位之前，建议先处理或明确约束 startup lifecycle instability，再执行重复验证。`shelf_1` 和 `shelf_2` 尤其值得继续复测，因为它们都曾在前置条件有效的情况下先出现一次 `ABORTED`，随后才在后续尝试中得到 `SUCCEEDED`。

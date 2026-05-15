# Scenario: Fixed Task-Point Success Matrix Regression

这个场景用于把当前主线的固定任务点导航验证，整理成一份可重复执行的矩阵回归案例。

它属于当前主线的关键运行时验证场景，因为 `station_a`、`station_b`、`shelf_1`、`shelf_2` 已经是最小 Mock WMS 任务闭环的主线业务点。

## 场景目标

- 验证 `config/task_points.yaml` 中主线业务点的导航可达性
- 验证只有在 ready gate 满足后才发送 goal
- 验证 `station_a`、`station_b`、`shelf_1`、`shelf_2` 的 `SUCCEEDED / SKIPPED / ABORTED` 结果可以被一致记录

## 适用范围

- 当前主线：V2.2 固定任务点与 V3 最小任务执行闭环
- 任务点入口：`config/task_points.yaml`
- 参考历史结果：
  `docs/wms/reports/wms_task_points_readiness_report_2026_05_13.md`

## 不在本场景内

- 不验证完整 WMS HTTP 闭环
- 不在同一轮里改导航参数
- 不把点位 candidate coordinates 直接宣称为最终仓库业务坐标

## 前置条件

- 已完成 `test/scenarios/headless_nav2_ready_integration.md` 或同等 ready 验证
- 使用 fresh session 执行每一次计入结果的尝试
- 已准备好统一的起点：
  `publish_initial_pose --preset start_zone`
- 建议固定本轮验证点位集合：
  `station_a`、`station_b`、`shelf_1`、`shelf_2`

## 执行步骤

1. 为每个点位使用 fresh session 启动 headless navigation。
2. 发布 `start_zone` initial pose。
3. 仅在以下条件全部满足后才发送 goal：
   `5/5 lifecycle active`
   `map -> odom` 可用
   `/navigate_to_pose` action server 数量为 `1`
4. 发送对应点位 goal，并记录：
   是否真正发出 goal
   是否出现 `/cmd_vel`
   goal 最终结果
5. 如果前置条件在本轮超时内始终未满足，则记为：
   `SKIPPED`
6. 对每个点位至少记录一次有效尝试。
7. 如果某个点位在 ready 前提下出现 `ABORTED`，建议在独立 fresh session 中补做一次复测。

## 建议记录的指标

- `point_name`
- `fresh_session_id`
- `time_to_ready_gate`
- `goal_sent`
- `goal_result`
- `cmd_vel_observed`
- `completion_time`
- `notes`

## 最低通过标准

- `station_a` 至少获得一次真实 `SUCCEEDED`
- `station_b` 至少获得一次真实 `SUCCEEDED`
- `shelf_1` 至少获得一次真实 `SUCCEEDED`
- `shelf_2` 至少获得一次真实 `SUCCEEDED`
- 所有 `SKIPPED` 结果都必须明确写出未 ready 原因
- 所有 `ABORTED` 结果都必须保留为运行时波动证据，不得直接删除

## 结果判定建议

- `Pass`
  四个点位都至少有一条真实 `SUCCEEDED` 证据，本轮记录完整
- `Needs Investigation`
  大部分点位成功，但 `shelf_1` / `shelf_2` 仍存在 ready 后 `ABORTED`
- `Fail`
  某个主线点位在本轮没有任何 `SUCCEEDED` 结果，或记录缺失导致无法复核

## 建议保留的证据

- ready gate 采样输出
- `ros2 action info /navigate_to_pose`
- goal result 输出
- `/cmd_vel` 是否出现的观察记录
- 可选：RViz / Gazebo 截图、屏幕录制

## 结果记录模板

| Run ID | Point Name | Goal Sent | Goal Result | `/cmd_vel` | Time to Ready | Completion Time | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 001 | `station_a` |  |  |  |  |  |  |
| 002 | `station_b` |  |  |  |  |  |  |
| 003 | `shelf_1` |  |  |  |  |  |  |
| 004 | `shelf_2` |  |  |  |  |  |  |

## 常见失败归因方向

- `SKIPPED`
  优先归因为 headless startup / lifecycle / TF / action readiness 未满足
- `ABORTED`
  优先归因为路径局部波动、环境状态、局部规划或控制阶段运行时不稳定
- 某个点连续失败
  优先检查该点位坐标合理性、通道障碍、局部 costmap 与 goal 朝向

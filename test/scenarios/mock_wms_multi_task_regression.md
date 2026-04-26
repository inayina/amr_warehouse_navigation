# Scenario: Mock WMS Multi-Task Regression

这个场景用于验证轻量 `mock WMS` 是否能稳定驱动一条最小多任务队列，并把结果沉淀成可复查的 JSON 报告。

它的意义不在于把当前系统包装成完整 WMS，而是验证下面这条最小链路是否成立：

```text
waypoints.json
→ demo_tasks.json
→ mock_wms_runner.py
→ dry-run / execute
→ last_run.json
```

## 场景目标

- 验证 `future_extensions/wms_integration/` 中的 waypoint 和 task 定义能被一致解析
- 验证 mock WMS 可以按顺序组织一条多 step、多 task 队列
- 验证执行结束后会产出结构化报告，便于接测试记录和项目展示

## 适用范围

- 当前阶段：V2 Nav2 稳定基线之上的轻量任务层验证
- 任务驱动器：`ros2 run amr_warehouse_sim mock_wms_runner`
- waypoint 配置：`future_extensions/wms_integration/config/waypoints.json`
- task 配置：`future_extensions/wms_integration/tasks/demo_tasks.json`
- 输出报告：`future_extensions/wms_integration/reports/last_run.json`

当前默认 demo 队列是：

```text
dock_a
→ buffer_1
→ staging_1
→ inspection_point
→ dock_a
```

## 不在本场景内

- 不验证订单系统、库存系统、数据库或正式 WMS API
- 不验证多机器人调度
- 不在本场景里同时改 `config/nav2_params.yaml`
- 不把 `config/nav2_params_collision_monitor_stage1.yaml` 和当前稳定基线混在同一轮结论里

如果要验证 `collision_monitor` 阶段 1 候选参数，建议单独立一轮安全策略测试，不要和本场景混跑。

## 前置条件

- 已完成编译并 `source install/setup.bash`
- 当前 V2 导航稳定基线可正常启动
- `pytest test -q` 当前通过
- 如果执行 `execute` 模式，`/navigate_to_pose` 已可用，且已经完成 initial pose 设置

## 执行步骤

### A. Dry Run 验证

1. 运行：
   `ros2 run amr_warehouse_sim mock_wms_runner --mode dry-run`
2. 确认终端输出包含：
   `Dry run validated ... tasks / ... steps`
3. 打开：
   `future_extensions/wms_integration/reports/last_run.json`
4. 确认报告里至少包含：
   `mode`、`generated_at`、`frame_id`、`queue_name`、`robot_name`、`summary`、`tasks`
5. 确认每个 step 都带有：
   `step_id`、`waypoint`、`action`、`pause_sec`、`pose`

### B. Execute 模式验证

1. 启动当前主线导航：
   `ros2 launch amr_warehouse_sim navigation.launch.py`
2. 确认 `map_server`、`amcl`、`planner_server`、`controller_server`、`bt_navigator` 为 `active`
3. 在 RViz 中设置 initial pose
4. 运行：
   `ros2 run amr_warehouse_sim mock_wms_runner --mode execute`
5. 观察机器人是否按 task / step 顺序发送 goal
6. 检查报告中的 task 状态是否为：
   `succeeded` 或 `failed`
7. 检查 summary 中是否生成：
   `task_count`、`step_count`、`failed_tasks`、`completed_tasks`、`status`

## 建议记录的指标

- `dry_run_task_count`
  dry-run 模式识别出的任务数
- `dry_run_step_count`
  dry-run 模式识别出的总 step 数
- `default_route_consistency`
  默认队列是否仍保持 `dock_a -> buffer_1 -> staging_1 -> inspection_point -> dock_a`
- `time_to_first_goal_dispatch`
  execute 开始到第一个 goal 发出的时间
- `task_success_rate`
  成功 task 数 / 总 task 数
- `step_success_rate`
  成功 step 数 / 总 step 数
- `report_integrity`
  报告字段是否完整、结构是否一致

## 通过标准

- dry-run 能成功解析 waypoint 和 task，不报格式错误
- `last_run.json` 成功生成，且字段结构完整
- execute 模式下至少能顺序处理一条多 step task
- 报告中的 `summary.status` 与实际任务结果一致
- 单个 step 失败时，报告中能看出失败位置和状态，而不是静默丢失

## 失败分级建议

- `Blocker`
  dry-run 无法解析配置，或 execute 无法连接 `NavigateToPose` action server
- `Major`
  task 被执行但顺序错乱、报告字段缺失、结果状态与真实行为不一致
- `Minor`
  报告可生成，但字段命名、说明文案、失败原因表达不够清晰

## 建议保留的证据

- dry-run 终端输出截图
- execute 终端输出截图
- `future_extensions/wms_integration/reports/last_run.json`
- RViz 截图
- `ros2 lifecycle get /bt_navigator`
- 可选：屏幕录制、`/cmd_vel` 采样日志、Nav2 action 结果日志

## 结果记录模板

| Run ID | Mode | Task Count | Step Count | Summary Status | Task Success Rate | Evidence | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 001 | dry-run |  |  |  |  |  |  |
| 002 | execute |  |  |  |  |  |  |

## 常见失败归因方向

- dry-run 直接失败
  优先检查 `waypoints.json` 和 `demo_tasks.json` 的字段拼写、必填项和 waypoint 引用关系
- execute 无法开始
  优先检查 `/navigate_to_pose` 是否可用，以及 Nav2 lifecycle 是否进入 `active`
- 报告状态不准确
  优先检查 `mock_wms_runner.py` 与 `wms_dispatcher.py` 的状态流转逻辑
- 多 step task 中途失败
  优先区分是导航链路问题，还是任务配置、goal 顺序或 waypoint 本身不合理

## 推荐结论写法

- `Pass`
  mock WMS 能稳定完成 dry-run 校验，并在 execute 模式下顺序驱动最小多任务队列，报告结构完整
- `Needs Investigation`
  dry-run 正常，但 execute 中存在偶发失败、状态记录不完整或 task 结果不稳定
- `Fail`
  waypoint / task 配置无法解析，或 execute 模式无法形成稳定的多任务闭环

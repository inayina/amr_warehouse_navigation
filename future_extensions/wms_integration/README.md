# Legacy Mock WMS Minimum Viable Version

这个目录提供一个不接入当前 V2 主线的轻量 `mock WMS` 最小可用版本，用来支持测试、演示和求职表达。

截至 `2026-05-14`，这套链路保留在 `future_extensions/` 下作为 legacy 扩展参考：

- 保留 waypoint / task queue / JSON report 这类轻量任务流样例
- 保留多 step 场景回归和展示素材
- 不再作为当前主线推荐的 `ros2 run` 入口

当前主线推荐入口已经切换到：

- `ros2 run amr_warehouse_sim init_mock_wms_db`
- `ros2 run amr_warehouse_sim create_mock_task`
- `ros2 run amr_warehouse_sim list_mock_tasks`
- `ros2 run amr_warehouse_sim mock_wms_executor`
- `ros2 run amr_warehouse_sim mock_wms_task_runner`
- `uvicorn scripts.mock_wms_api:create_app --factory`

它的目标不是做完整 WMS，而是回答这 3 个问题：

- 能不能把单次 Nav2 goal 组织成一个最小任务队列
- 能不能用 waypoint 别名管理任务目标，而不是硬编码坐标
- 能不能在执行后输出一份任务结果记录，体现测试和调度思维

## 边界

当前版本明确只做这些事情：

- 单机器人
- 单队列
- 顺序执行
- waypoint 别名到坐标映射
- 任务状态流转
- 结果落盘到 JSON 报告

当前版本明确不做这些事情：

- 不接数据库
- 不接订单、库存、库位管理
- 不做多机器人调度
- 不做路径优化或冲突解决
- 不接回当前 `navigation.launch.py` 主线

## 目录结构

```text
future_extensions/wms_integration/
├── README.md
├── config/
│   └── waypoints.json
├── launch/
│   └── task_system.launch.py
├── scripts/
│   ├── mock_wms_runner.py
│   └── send_task.sh
├── task_manager/
│   └── wms_dispatcher.py
└── tasks/
    └── demo_tasks.json
```

## 最小数据模型

### 1. Waypoints

`config/waypoints.json` 用名字管理地图点位。

当前默认 demo 使用这 4 个 scene-aligned waypoint：

- `dock_a`
- `buffer_1`
- `staging_1`
- `inspection_point`

当前默认队列会按下面这条路线执行：

```text
dock_a
→ buffer_1
→ staging_1
→ inspection_point
→ dock_a
```

每个点位包含：

- `x`
- `y`
- `yaw`
- `description`

### 2. Tasks

`tasks/demo_tasks.json` 用任务队列表达最小任务流。

每个 task 包含：

- `task_id`
- `type`
- `description`
- `steps`

每个 step 包含：

- `waypoint`
- `action`
- `pause_sec`

## 状态流转

最小版本建议按这个状态理解：

```text
queued
→ validated
→ running
→ succeeded / failed
```

## 运行方式

当前 legacy 链路不再作为主线 `ros2 run amr_warehouse_sim mock_wms_runner` 入口暴露。

如果只是想复核这套旧样例，推荐直接运行源码目录里的脚本：

- `python3 future_extensions/wms_integration/scripts/mock_wms_runner.py --mode dry-run`
- `python3 future_extensions/wms_integration/scripts/mock_wms_runner.py --mode execute`

`launch/task_system.launch.py` 现在可以作为一个轻量 dry-run 入口使用：

```bash
ros2 launch amr_warehouse_sim task_system.launch.py
```

### 1. Dry Run

先验证任务和 waypoint 是否一致，不依赖 ROS action server：

```bash
cd ~/ros2_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
cd ~/ros2_ws/src/amr_warehouse_sim
python3 future_extensions/wms_integration/scripts/mock_wms_runner.py --mode dry-run
```

### 2. Execute Mode

在已经启动 Nav2 并且 `/navigate_to_pose` 可用时，顺序发送任务：

```bash
cd ~/ros2_ws/src/amr_warehouse_sim
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash
python3 future_extensions/wms_integration/scripts/mock_wms_runner.py --mode execute
```

当前默认 `demo_tasks.json` 会执行 2 个 task / 5 个 step：

- `TASK-001`
  `dock_a -> buffer_1 -> staging_1`
- `TASK-002`
  `inspection_point -> dock_a`

其中 `dock_a`、`staging_1`、`inspection_point` 保留了短暂停留，用来模拟 pickup / dropoff / inspection 这类最小任务动作。

如果 action server 名称不是默认值，可以显式指定：

```bash
python3 future_extensions/wms_integration/scripts/mock_wms_runner.py --mode execute --action-name /navigate_to_pose
```

## 输出结果

默认会把运行结果写到当前 mock WMS 目录下的：

```text
future_extensions/wms_integration/reports/last_run.json
```

如果通过安装后的 `ros2 run` 入口执行，终端里会打印实际报告路径。

这个 JSON 报告适合后续接到测试报告、场景回归或简历项目描述里。

## 如何把它用在测试里

最自然的用法不是把它当真正 WMS，而是把它当：

- 场景测试驱动器
- 任务流验证器
- mock 调度层
- 面试展示中的“轻量任务系统”

推荐配合这些材料一起使用：

- `test/scenarios/short_goal_navigation_smoke.md`
- `test/scenarios/restart_relocalization_regression.md`
- `docs/templates/test-report-template.md`

## 下一步如何扩展

如果后续要继续扩，但仍然保持轻量，建议按这个顺序：

1. 补一版带截图、时延和成功率的 execute 结果记录
2. 增加任务执行结果的统计字段，例如总耗时、成功率、失败类型
3. 给任务结果增加更清晰的 defect / failure reason 分类
4. 在 `test/scenarios/` 中继续沉淀“mock WMS 驱动的多任务回归场景”
5. 最后再考虑是否需要接更正式的任务 API

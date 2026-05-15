# 测试目录说明

这个目录按更贴近实际机器人项目的方式，先划分为 4 个层次：`data`、`functional`、`integration`、`scenarios`。

这里的关键点是：

- `测试用例` 是最小执行单位，每个 `test_*.py` 里的每个 `test_xxx()` 都是一个测试用例。
- `data / functional / integration / scenarios` 是分类方式，用来回答“这个测试在验证哪一层风险”。

## 当前目录结构（节选）

```text
test/
├── conftest.py
├── data/
│   └── ...
├── functional/
│   └── ...
├── integration/
│   └── ...
└── scenarios/
    ├── headless_nav2_ready_integration.md
    ├── fixed_task_points_success_matrix_regression.md
    ├── mock_wms_http_executor_end_to_end.md
    └── ...
```

## 各层职责

- `data/`
  适合验证地图、YAML、参数、模型资源、配置约束。
  当前已覆盖 `maps/warehouse.yaml` 和 `config/nav2_params.yaml`。

- `functional/`
  适合验证单个入口或功能是否还能工作。
  当前已覆盖 `simulation.launch.py` 和 `navigation.launch.py` 的 smoke test。

- `integration/`
  适合验证链路级联动是否成立，例如 `/scan -> /scan_filtered`、`map -> odom -> base_link`、Nav2 lifecycle 是否进入 `active`。
  当前已经有多组 focused contract test，包括导航链路、Mock WMS 数据层、单条 executor 和顺序 task runner；后续更适合继续接 `launch_testing` 或仿真集成测试。

- `scenarios/`
  适合验证面向业务场景的端到端表现，例如短距离 goal、狭窄货架通道导航、重复启停回归。
  当前已经有多份可直接执行和记录结果的场景测试 spec，其中主线运行时验证包括 headless ready-gate、固定任务点成功矩阵和 HTTP executor 端到端闭环。

## 运行方式

从项目根目录快速回归：

```bash
cd ~/ros2_ws/src/amr_warehouse_sim
make test
```

说明：

- 这条命令已经在 `2026-05-14` 的当前仓库环境中真实跑通，结果为 `63 passed`
- `make test` 会优先使用项目内 `.venv`，如果 `.venv` 不存在，则使用当前 shell 的 `python3`

按 ROS 2 工作空间方式运行：

```bash
cd ~/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon test --packages-select amr_warehouse_sim
colcon test-result --verbose
```

## 当前已落地的测试

- `test/data/test_map_files.py`
  验证 Nav2 地图入口 `maps/warehouse.yaml` 是否存在、字段是否完整、是否指向真实的地图图像。

- `test/data/test_navigation_config.py`
  验证当前 V2 稳定基线中的关键导航约束是否还在，例如 `/scan_filtered`、矩形 footprint、planner / controller 插件。

- `test/functional/test_launch_smoke.py`
  验证 `simulation.launch.py` 和 `navigation.launch.py` 仍然可以生成 `LaunchDescription`，避免改完 launch 后出现低级回归。

- `test/integration/test_navigation_pipeline_contract.py`
  验证 V2 主线里 scan、odom、map、TF 和 Nav2 参数之间的跨文件链路契约没有断开。

- `test/integration/test_mock_wms_contract.py`
  验证 mock WMS 默认资源是否可加载、dry-run 报告结构是否稳定，以及 waypoint / task 的基本约束是否会被正确拦住。

- `test/integration/test_mock_wms_executor_contract.py`
  验证 V3.1 单条 executor 的状态机、ready gate、dry-run / execute 切换和 SQLite 状态回写约束。

- `test/integration/test_mock_wms_task_runner.py`
  验证 V3.1 顺序 task runner 的队列消费、失败停止和 continue-on-failure 行为。

- `test/scenarios/short_goal_navigation_smoke.md`
  定义一次短距离导航 smoke test 的目标、步骤、指标、通过标准和证据要求。

- `test/scenarios/restart_relocalization_regression.md`
  定义重复启动后 localization 和导航恢复能力的回归验证流程。

- `test/scenarios/mock_wms_multi_task_regression.md`
  定义 mock WMS 驱动的多任务回归流程，覆盖 dry-run、execute 和任务报告检查。

- `test/scenarios/headless_nav2_ready_integration.md`
  定义 fresh session + headless 模式下的 Nav2 ready-gate 运行时集成验证。

- `test/scenarios/fixed_task_points_success_matrix_regression.md`
  定义 `station_a`、`station_b`、`shelf_1`、`shelf_2` 的固定任务点成功矩阵回归。

- `test/scenarios/mock_wms_http_executor_end_to_end.md`
  定义最小 HTTP API -> executor -> Nav2 -> HTTP 状态回写闭环的运行时验证流程。

## 后续建议

- `integration/` 仍可继续补更强的 launch / runtime integration；但当前主线更优先的是把 `scenarios/` 中的关键运行时案例持续执行并沉淀报告。
- `scenarios/` 后续可以继续补更具体的固定坐标 goal、多轮成功率统计和 shelf 点位重复稳定性记录。
- `scenarios/` 也适合继续补 task runner、HTTP executor 与验收报告之间的一致性验证。
- 真机或半实物阶段，再把 bag 回放和传感器回归测试逐步接进来。
- 测试完成后建议配合 `docs/templates/test-report-template.md` 输出一份正式测试报告。

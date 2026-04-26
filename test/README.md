# 测试目录说明

这个目录按更贴近实际机器人项目的方式，先划分为 4 个层次：`data`、`functional`、`integration`、`scenarios`。

这里的关键点是：

- `测试用例` 是最小执行单位，每个 `test_*.py` 里的每个 `test_xxx()` 都是一个测试用例。
- `data / functional / integration / scenarios` 是分类方式，用来回答“这个测试在验证哪一层风险”。

## 当前目录结构

```text
test/
├── conftest.py
├── data/
│   ├── README.md
│   ├── test_map_files.py
│   └── test_navigation_config.py
├── functional/
│   ├── README.md
│   └── test_launch_smoke.py
├── integration/
│   └── README.md
└── scenarios/
    └── README.md
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
  当前已经有两个 focused contract test，后续更适合继续接 `launch_testing` 或仿真集成测试。

- `scenarios/`
  适合验证面向业务场景的端到端表现，例如短距离 goal、狭窄货架通道导航、重复启停回归。
  当前已经有三份可直接执行和记录结果的场景测试 spec。

## 运行方式

快速回归：

```bash
cd ~/ros2_ws/src/amr_warehouse_sim
pytest test -q
```

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

- `test/scenarios/short_goal_navigation_smoke.md`
  定义一次短距离导航 smoke test 的目标、步骤、指标、通过标准和证据要求。

- `test/scenarios/restart_relocalization_regression.md`
  定义重复启动后 localization 和导航恢复能力的回归验证流程。

- `test/scenarios/mock_wms_multi_task_regression.md`
  定义 mock WMS 驱动的多任务回归流程，覆盖 dry-run、execute 和任务报告检查。

## 后续建议

- `integration/` 优先补 TF、topic、lifecycle 和节点启动后的链路检查。
- `scenarios/` 后续可以继续补更具体的固定坐标 goal 和多轮成功率统计。
- `scenarios/` 也适合继续补 mock WMS 驱动的任务回归和报告化验证。
- 真机或半实物阶段，再把 bag 回放和传感器回归测试逐步接进来。
- 测试完成后建议配合 `docs/test-report-template.md` 输出一份正式测试报告。

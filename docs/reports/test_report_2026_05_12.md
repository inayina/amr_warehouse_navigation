# V2 导航基线测试报告

日期：`2026-05-12`

本文件记录当前 V2 Nav2 导航稳定基线在 `2026-05-12` 的实际测试执行结果。记录包含三部分：

- 自动化回归测试
- 无人值守无界面启动复测
- 启动早期加入 `/initialpose` 注入的增强复测

它是在现有 `test/` 测试结构和 `docs/templates/test-report-template.md` 模板基础上的补充记录，不改动现有 launch、Nav2 参数、地图和 Gazebo 世界。

## 1. 测试目标

- 验证当前 V2 稳定基线仍具备可重复执行的自动化回归入口和运行时导航检查入口。
- 为 `launch/navigation.launch.py` + `config/nav2_params.yaml` + `maps/warehouse.yaml` 沉淀一份统一的执行记录。
- 复用仓库现有测试结构，而不是额外创建一套新的测试体系。
- 验证 `/initialpose` 处理是否已经成为 Nav2 无界面复测中的必需步骤。

## 2. 测试环境

| 项目 | 内容 |
| --- | --- |
| 仓库 | `amr_warehouse_navigation` |
| ROS 2 包名 | `amr_warehouse_sim` |
| 包版本 | `0.0.1` |
| 操作系统 | Ubuntu 24.04 |
| ROS 2 | Jazzy |
| 仿真器 | Gazebo Harmonic |
| 基线启动文件 | `launch/navigation.launch.py` |
| 基线参数文件 | `config/nav2_params.yaml` |
| 基线地图文件 | `maps/warehouse.yaml` |
| 测试日期 | `2026-05-12` |
| 复测方式 | 用户关闭旧节点和旧程序后重新干净启动 |
| 本轮实际启动方式 | `ros2 launch amr_warehouse_sim navigation.launch.py use_gz_gui:=false use_rviz:=false` |
| 测试人员 | `Codex（命令行复测）` |

## 3. 测试范围

### 本次范围内

- `test/` 目录下现有自动化 `pytest` 回归测试
- `amr_warehouse_sim` 包现有 `colcon test` 包级测试执行
- V2 导航稳定基线的运行时启动与运行时检查
- `/initialpose` 注入对无界面复测结果的影响
- 仓库中已经建立的测试分层：
  - `test/data/`
  - `test/functional/`
  - `test/integration/`
  - `test/scenarios/`

### 当前覆盖说明

- `test/data/`
  覆盖 `maps/warehouse.yaml` 和 `config/nav2_params.yaml` 的静态回归，包括地图元数据、地图图像引用、Nav2 核心 section、`/scan_filtered` 管线、footprint 标记、planner/controller 插件标记，以及稳定基线关键参数。
- `test/functional/`
  覆盖 `launch/simulation.launch.py` 和 `launch/navigation.launch.py` 的 smoke test，确认它们仍能生成有效的 `LaunchDescription`。
- `test/integration/`
  覆盖 V2 导航主链的跨文件静态契约检查，涉及 `simulation.launch.py`、`navigation.launch.py`、`nav2_params.yaml` 和 `warehouse.yaml` 之间的 `/scan`、`/scan_filtered`、`/odom`、map 入口、TF 相关 frame 命名和 `robot_state_publisher` 一致性。
- 现有额外自动化 integration 覆盖
  `test/integration/test_mock_wms_contract.py` 已存在并可自动执行，但本报告不扩展也不重构该部分。
- `test/scenarios/`
  当前包含短距离导航、重启后 relocalization 回归、mock WMS 多任务回归等场景 spec 和手工执行说明，这部分目前还不是 `pytest` 自动化测试。

### 本次范围外

- 新增 WMS、HTTP、SQLite、MQTT
- launch 或 Nav2 参数重构
- 地图重新生成或地图内容修改
- CI、GitHub Actions 或新的测试依赖

## 4. 测试命令

请在工作空间已完成编译并且已经 `source` ROS 2 环境后执行以下命令。

### 自动化测试命令

```bash
pytest test -q
```

```bash
colcon test --packages-select amr_warehouse_sim
```

```bash
colcon test-result --verbose
```

说明：默认 `colcon test-result --verbose` 会汇总当前工作区里已有的测试结果。如果只想查看 `amr_warehouse_sim` 本包结果，可额外执行：

```bash
colcon test-result --verbose --test-result-base build/amr_warehouse_sim
```

### 运行时启动命令

```bash
ros2 launch amr_warehouse_sim navigation.launch.py
```

本轮为了可重复的命令行复测，实际执行时使用了无界面变体：

```bash
ros2 launch amr_warehouse_sim navigation.launch.py use_gz_gui:=false use_rviz:=false
```

### 运行时检查命令

```bash
ros2 topic echo /map --once
```

```bash
ros2 topic echo /scan_filtered --once
```

```bash
ros2 run tf2_ros tf2_echo map odom
```

```bash
ros2 lifecycle get /map_server
ros2 lifecycle get /amcl
ros2 lifecycle get /planner_server
ros2 lifecycle get /controller_server
ros2 lifecycle get /bt_navigator
```

### 初始位姿注入命令

如果需要把 initial pose 设置纳入更可复现的测试流程，当前仓库已提供：

```bash
ros2 run amr_warehouse_sim publish_initial_pose --preset start_zone
```

该命令会向 `/initialpose` 发布 `PoseWithCovarianceStamped`，可作为 RViz `2D Pose Estimate` 的命令行替代方式。当前 `start_zone` 预设对应实际仿真场景中的机器人出生点和起始区域中心。

## 5. 运行时检查项

| 检查项 | 预期结果 | 实际结果 | 状态 |
| --- | --- | --- | --- |
| `ros2 launch amr_warehouse_sim navigation.launch.py` | 导航基线可以正常启动，且不存在基线路径错误 | 第一次干净复测中，未注入初始位姿时，`gz`、`parameter_bridge`、`odom_tf_node`、`scan_to_scan_filter_chain` 和 Nav2 节点均已拉起，`map_server` 成功加载 `warehouse.yaml`，`amcl` 进入 `active`，但 `planner_server` 在等待 `base_link -> map` 变换超时后激活失败。第二次干净复测中，启动后约 12 秒执行 `publish_initial_pose --preset start_zone`，导航生命周期节点可完整进入 `active` | `通过（需初始位姿步骤）` |
| `ros2 topic echo /map --once` | `/map` 能输出一条有效地图消息 | 成功收到地图信息；`resolution: 0.05`，`width: 321`，`height: 322`，`origin: (-8.008, -8.174, 0.0)` | `通过` |
| `ros2 topic echo /scan_filtered --once` | `/scan_filtered` 能输出一条滤波后的 LaserScan 消息 | 成功收到滤波后的 `LaserScan`；`frame_id: my_robot/lidar_link/lidar` | `通过` |
| `ros2 run tf2_ros tf2_echo map odom` | `map -> odom` TF 可用 | 第一次无人值守复测中持续输出 `Invalid frame ID "map"`；第二次在启动早期执行 `publish_initial_pose --preset start_zone` 后，短暂等待后可输出稳定的 `map -> odom` 变换，平移约 `[0.004, 0.024, 0.000]`，偏航约 `0.093` 度 | `通过（需初始位姿步骤）` |
| `ros2 lifecycle get /map_server` | 节点状态为 `active` | 两轮复测中均为 `active [3]` | `通过` |
| `ros2 lifecycle get /amcl` | 节点状态为 `active` | 两轮复测中均为 `active [3]` | `通过` |
| `ros2 lifecycle get /planner_server` | 节点状态为 `active` | 第一次无人值守复测中为 `inactive [2]`；第二次在启动早期执行 `publish_initial_pose --preset start_zone` 后为 `active [3]` | `通过（需初始位姿步骤）` |
| `ros2 lifecycle get /controller_server` | 节点状态为 `active` | 两轮复测中均为 `active [3]` | `通过` |
| `ros2 lifecycle get /bt_navigator` | 节点状态为 `active` | 第一次无人值守复测中为 `inactive [2]`；第二次在启动早期执行 `publish_initial_pose --preset start_zone` 后为 `active [3]` | `通过（需初始位姿步骤）` |
| `ros2 run amr_warehouse_sim publish_initial_pose --preset start_zone` | 能向 `/initialpose` 发布有效初始位姿 | 已找到 `1` 个 `/initialpose` 订阅者，并连续发布 `10` 条初始位姿。第一次在 planner 已激活失败后补发时，可触发 AMCL `initialPoseReceived` 并最终建立 `map -> odom`，但不会自动让 `planner_server` / `bt_navigator` 从已失败状态恢复；第二次在启动早期执行时，可支撑完整的导航生命周期激活 | `通过` |

## 6. 结果表

| ID | 测试项 | 预期结果 | 实际结果 | 状态 |
| --- | --- | --- | --- | --- |
| `AUT-001` | `pytest test -q` | 当前自动化测试集可以执行完成，并反映当前基线状态 | `16 passed in 0.23s` | `通过` |
| `AUT-002` | `colcon test --packages-select amr_warehouse_sim` | `amr_warehouse_sim` 包级测试执行完成 | 命令已成功执行，`colcon` 已切换到 `python3 -m pytest`，收集 `16` 个测试并全部通过；包级测试阶段结束为 `Finished <<< amr_warehouse_sim [0.81s]` | `通过` |
| `AUT-003` | `colcon test-result --verbose` | 可获得测试结果汇总供复核 | 默认命令输出 `Summary: 19 tests, 0 errors, 0 failures, 1 skipped`；进一步使用 `colcon test-result --verbose --test-result-base build/amr_warehouse_sim` 复核，本包结果为 `Summary: 16 tests, 0 errors, 0 failures, 0 skipped`。默认汇总中的 `1 skipped` 来自工作区内其他包的历史测试结果 | `通过（需注意汇总范围）` |
| `RUN-001` | Nav2 基线启动 | `navigation.launch.py` 启动出预期的基线链路 | 无初始位姿的第一次复测只能把定位侧拉起；在第二次复测中，启动早期执行 `publish_initial_pose --preset start_zone` 后，导航生命周期节点可完整进入 `active` | `通过（需初始位姿步骤）` |
| `RUN-002` | `/map` 运行时检查 | `/map` 正常发布 | 已收到 `OccupancyGrid` 地图消息 | `通过` |
| `RUN-003` | `/scan_filtered` 运行时检查 | `/scan_filtered` 正常发布 | 已收到滤波后的 `LaserScan` 消息 | `通过` |
| `RUN-004` | `map -> odom` TF 检查 | TF 链路可用 | 第一次复测中 `map -> odom` 未建立；第二次在启动早期注入 `start_zone` 初始位姿后，`tf2_echo` 可输出有效变换 | `通过（需初始位姿步骤）` |
| `RUN-005` | Lifecycle 检查 | `map_server`、`amcl`、`planner_server`、`controller_server`、`bt_navigator` 均为 `active` | 第一次复测中 `planner_server` 与 `bt_navigator` 为 `inactive`；第二次在启动早期注入 `start_zone` 初始位姿后，上述节点均为 `active [3]` | `通过（需初始位姿步骤）` |
| `RUN-006` | `/initialpose` 注入检查 | 可以通过命令行注入可用初始位姿 | `publish_initial_pose --preset start_zone` 找到 `/initialpose` 订阅者并连续发布 `10` 条消息；启动早期执行时可支撑完整启动流程 | `通过` |

## 7. 发现的问题

当前已完成自动化测试与两轮运行时检查，`colcon test` 集成问题已修复，另有若干运行时问题继续跟踪。

| 问题 ID | 描述 | 实际结果 | 状态 |
| --- | --- | --- | --- |
| `ISSUE-001` | `colcon test` 未接通现有 `pytest` 测试的问题已修复 | 在 `setup.py` 增加 `tests_require=['pytest']` 后，`colcon test --packages-select amr_warehouse_sim` 已改为执行 `python3 -m pytest`，并收集通过 `16` 个测试；默认 `colcon test-result --verbose` 中出现的 `1 skipped` 来自工作区内其他包的历史结果，不属于本包失败 | `已关闭` |
| `ISSUE-002` | 缺少自动化 AMCL 初始位姿注入 | 第一次无人值守复测没有初始位姿处理，导致 `planner_server` 在等待 `map` TF 超时后激活失败；第二次在启动早期执行 `publish_initial_pose --preset start_zone` 后，该问题消失 | `待处理` |
| `ISSUE-003` | 初始位姿注入的时机影响导航生命周期是否能自动拉齐 | 在第一次复测中，等 `planner_server` 已经激活失败后再补发 `/initialpose`，可以建立 `map -> odom`，但不会自动让 `planner_server` / `bt_navigator` 从 `inactive` 恢复 | `待处理` |
| `ISSUE-004` | 初始代价地图与实际地图存在约 90 度偏差 | 该现象由用户在 RViz 中观察到；本次命令行复测未直接完成视觉确认，但它与 [docs/troubleshooting.md](../troubleshooting.md) 和 [docs/reports/collision_monitor_stage1_test_report.md](./collision_monitor_stage1_test_report.md) 中已记录的“保存地图与 Gazebo 世界可能存在约 90 度朝向差异”一致，更像定位 / 地图对齐问题而非单纯 costmap 参数问题 | `待处理` |

## 8. 人工验证说明

- 第一次无人值守复测没有包含 AMCL 初始位姿设置步骤，因此 `planner_server` / `bt_navigator` 的 `inactive` 结果只代表“未处理初始位姿的自动化复测状态”。
- 用户此前已在 RViz 中手工执行 `2D Pose Estimate`，并确认之后可以正常进行 Nav2 导航。
- 本次命令行复测进一步确认：在第二次干净启动中，如果在启动早期执行 `ros2 run amr_warehouse_sim publish_initial_pose --preset start_zone`，则 `map -> odom` 可建立，且 `map_server`、`amcl`、`planner_server`、`controller_server`、`bt_navigator` 均可进入 `active`。
- 因此，第一次无人值守复测中的 `planner_server` / `bt_navigator` `inactive` 结果，不能单独视为导航主功能失败。
- 另一方面，如果等到 `planner_server` 已经因缺少 `map` TF 激活失败后再补发 `/initialpose`，TF 可能恢复，但导航生命周期不会自动补齐，这说明“是否设置初始位姿”之外，“设置时机”同样重要。

## 9. 结论

- 总体结果：`通过，但流程仍有缺口`
- 置信度：`中高`
- `pytest test -q` 当前稳定通过，结果为 `16 passed in 0.23s`。
- `colcon test --packages-select amr_warehouse_sim` 已接通现有 `pytest` 测试，并成功执行同一批 `16` 个自动化用例。
- `colcon test-result --verbose` 默认会汇总整个工作区已有测试结果；如果只查看本包，`colcon test-result --verbose --test-result-base build/amr_warehouse_sim` 当前结果为 `Summary: 16 tests, 0 errors, 0 failures, 0 skipped`。
- 未注入初始位姿的自动化基线测试是不完整的。
- 当前要完成完整的 Nav2 导航验证，仍需要手工在 RViz 中执行 `2D Pose Estimate`，或在无界面流程中显式注入 `/initialpose`。
- 在手工设置初始位姿后，已确认导航功能可正常使用。
- 本次进一步确认：在无界面复测中，只要在启动早期执行 `ros2 run amr_warehouse_sim publish_initial_pose --preset start_zone`，就可以建立 `map -> odom`，并使 `map_server`、`amcl`、`planner_server`、`controller_server`、`bt_navigator` 全部进入 `active`。
- 因此，更准确的结论不是“导航主功能失败”，而是“自动化测试入口已打通，但标准运行时复测流程仍必须显式包含初始位姿处理”。

## 10. 后续步骤

1. 同时保留 `pytest test -q` 与 `colcon test --packages-select amr_warehouse_sim` 作为自动化回归入口；如果只想查看本包结果，优先使用 `colcon test-result --verbose --test-result-base build/amr_warehouse_sim`。
2. 在文档中补充一条明确的 RViz `2D Pose Estimate` 手工步骤，并说明它与 `/initialpose` 命令行注入之间的对应关系。
3. 把 `ros2 run amr_warehouse_sim publish_initial_pose --preset start_zone` 纳入无界面基线复测的标准步骤，而不是只作为补充说明。
4. 后续可增加一个可选脚本或测试工具，用于发布 `/initialpose`，并把推荐执行时机写清楚，例如启动后约 `10-12` 秒或确认 `/initialpose` 订阅者已就绪后立即执行。
5. 在导航基线测试流程纳入初始位姿处理之前，继续阻塞 WMS 集成相关工作。
6. 在 RViz 中补充一张能同时看到 `Map`、`LaserScan`、local/global costmap 和机器人朝向的截图，用于把“90 度偏差”从用户观察升级为正式测试证据。
7. 后续如需进一步提升自动化程度，可单独评估是否增加“启动导航 + 等待订阅者 + 发布 `start_zone` 初始位姿 + 再执行运行时检查”的最小复测脚本，但这一项应作为后续独立任务处理。

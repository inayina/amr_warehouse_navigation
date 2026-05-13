# AMR Future Architecture

## 1. 文档定位

这份文档描述的是项目的**未来扩展架构方向**，不是当前已经完全实现的主线系统。

当前稳定基线仍以以下内容为准：

- 当前主线设计：`docs/design.md`
- 当前测试与排障：`docs/troubleshooting.md`
- 当前导航入口：`launch/navigation.launch.py`

本文件的目标是说明：

- 当前稳定基线之上，未来最自然的扩展层是什么
- 各扩展层应该放在什么边界内
- 哪些内容适合继续演进，哪些内容暂时不接回主线

## 2. 当前稳定基线

当前项目已经完成并稳定到以下链路：

```text
Gazebo World
→ ros_gz_bridge
→ /scan + /odom + TF
→ laser_filters
→ /scan_filtered
→ slam_toolbox 或 Nav2 localization
→ map -> odom -> base_link
→ planner / controller
→ /cmd_vel
→ Gazebo robot motion
```

当前主线重点仍然是：

- V1 建图链路可复现
- V2 Nav2 导航链路可复现
- `publish_initial_pose --preset start_zone` 作为主线 initial pose 入口可复现
- `config/task_points.yaml` 作为主线固定任务点入口可复现
- 短距离 goal、fixed-goal 验证和 fresh-session 启动记录持续完善
- 测试入口、场景 spec、startup stability 记录和验证材料持续完善

## 3. 架构原则

未来扩展遵循以下原则：

1. 不破坏当前 V2 导航稳定基线
2. 新能力优先以 `future_extensions/` 或 `docs/` 的形式独立演进
3. 先完成验证和可复现，再讨论更大范围的任务系统
4. 先做单机器人、单任务流，再考虑多机器人或复杂调度

## 4. 未来扩展层

### 4.1 Navigation Baseline Layer

这一层是未来所有扩展的基础，当前已经基本具备：

- Gazebo 仿真世界
- 单机器人运动与传感器链路
- SLAM 与地图保存
- Nav2 localization / planning / control
- RViz 可视化与基础验证流程

对应当前主线文件：

- `launch/simulation.launch.py`
- `launch/slam.launch.py`
- `launch/navigation.launch.py`
- `config/nav2_params.yaml`
- `maps/warehouse.yaml`

### 4.2 Validation Layer

这一层负责把“能跑”逐步变成“可验证、可复现、可报告”。

当前已经开始形成：

- `test/data/`
- `test/functional/`
- `test/integration/`
- `test/scenarios/`
- `docs/test-report-template.md`
- `docs/reports/test_report_2026_05_12.md`
- `docs/reports/repeat_navigation_test_report_2026_05_13.md`
- `docs/logs/nav2_startup_stability_notes.md`
- `docs/logs/nav2_startup_stability_log_2026_05_13.md`
- `docs/reports/wms_task_points_readiness_report_2026_05_13.md`

未来这一层会继续补强：

- runtime integration tests
- TF / topic / lifecycle 自动检查
- fresh-session startup readiness 的可重复诊断
- 场景级回归数据
- 更正式的测试报告和 defect 记录

### 4.3 Mock WMS / Task Layer

这一层的目标不是立即扩展完整 WMS，而是在 V2.1 和 V2.2 稳定基线之上，逐步推进一个**测试驱动的轻量任务层**。

截至 `2026-05-13`，当前已经落地的边界：

- 单机器人
- 单队列
- 固定 map frame 任务点
- SQLite 最小任务表
- CLI create / list / init
- 任务状态流转定义

当前仍未进入主线的部分：

- ROS 2 task executor
- Nav2 action 真正消费 pending task
- HTTP / MQTT / 外部调度服务
- 多机器人或复杂调度

当前对应扩展目录：

- `future_extensions/wms_integration/`

它的用途主要是：

- 驱动多步任务场景测试
- 作为 mock 调度层展示系统扩展思路
- 作为求职时的轻量任务系统样例

继续扩大这一层之前，当前主线仍应进一步收口：

- fresh-session startup stability 的波动边界
- business points 的 `3~5` 轮重复成功证据
- 更稳定的运行时基线测试报告和截图材料

### 4.4 Task API / Integration Layer

这一层只有在 mock WMS 数据层和导航侧验证都更稳定后才值得继续推进。

未来可能的方向包括：

- waypoint 配置规范化
- 任务输入接口统一
- 任务执行结果结构化输出
- 更清晰的失败分类和重试策略

当前不建议直接推进到：

- 完整订单系统
- 库位管理
- 数据库持久化
- 多机器人调度

补充说明：

- SQLite 持久化本身已经在最小数据层里存在
- 这里“不建议直接推进”的含义是：不要把“已有最小数据层”直接扩写成完整业务系统

## 5. 推荐未来数据流

如果未来继续沿着“测试驱动的轻量任务层”演进，推荐的数据流如下：

```text
Scenario Spec / Mock Task Queue
→ mock WMS runner
→ waypoint resolution
→ NavigateToPose goals
→ Nav2 execution
→ result JSON / test report
```

这个方向的优点是：

- 不会破坏当前主线
- 非常适合做回归测试和演示
- 也很适合在求职时展示“测试 + 任务流 + 调度边界”的系统思维

## 6. 当前不建议公开宣称已实现的内容

为了避免误导，这些内容当前不应作为“已经完成”的主线能力对外表述：

- 完整 WMS
- 多机器人协作
- AI 诊断主线能力
- 语音调度或 LLM 调度
- 完整生产级任务编排

如果未来要做，建议先以实验或 `future_extensions/` 草稿形式存在。

## 7. 建议展示方式

如果把这个仓库作为作品集或简历项目展示，推荐对外这样描述：

- 当前已经完成：AMR 仿真、SLAM、Nav2、测试分层、自动化测试入口与基线测试报告
- 当前正在推进：fresh-session startup stability 收口、fixed task points 重复验证、Mock WMS readiness 证据整理
- 当前仍在规划：ROS 2 task executor、更正式的任务接口与任务流扩展

# Mobile Manipulation V1 文档索引

日期：`2026-08-27`

设计分支：`feature/mobile-manipulation-mvp`

审计基线：`c8af1cfe992591a572f5e2f51833b76e64f4437f`

状态：**REFERENCE DESIGN + Gate 0/1 scoped runtime evidence**

## 1. 文档定位

本目录定义“感知驱动的移动操作机器人多工位作业参考系统”V1 的需求、边界、接口、状态机、集成顺序与验收方法。它是在现有单车 AMR / Gazebo / Nav2 稳定基线旁新增的 opt-in 设计，不代表仓库已经具备机械臂、MoveIt 2、ros2_control、抓取或放置能力。

当前 `main` 继续代表已有 AMR / Nav2 主线；在 Gate 0 的 U1/U2/U3 upstream baseline通过前，本分支不修改 `navigation.launch.py`、`config/nav2_params.yaml`、现有 world/model、Mock WMS、Fleet 或 inspection runtime。后续 Gate 1 也只允许新增 opt-in variant，不替换这些稳定入口。

## 2. 推荐阅读顺序

1. [CURRENT_REPOSITORY_AUDIT.md](./CURRENT_REPOSITORY_AUDIT.md)：当前 HEAD 的可复用能力、缺口、integration seam 与保护范围。
2. [PRD.md](./PRD.md)：V1 场景、用户价值、范围、成功定义与 non-goals。
3. [ARCHITECTURE.md](./ARCHITECTURE.md)：分层、ROS package boundary、TF authority、control ownership 与 Mermaid 图。
4. [REQUIREMENTS.md](./REQUIREMENTS.md)：可验证的 `MM-REQ-xxx` 需求基线。
5. [INTERFACE_CONTRACTS.md](./INTERFACE_CONTRACTS.md)：Task、Navigation、Manipulation、Perception、Interlock、Fault 与 Evidence 合同。
6. [TASK_STATE_MACHINE.md](./TASK_STATE_MACHINE.md)：V1 FSM、transition trigger、timeout、cancel、retry 与旧结果隔离。
7. [UPSTREAM_REFERENCE_STRATEGY.md](./UPSTREAM_REFERENCE_STRATEGY.md)：官方 upstream、版本快照、baseline reproduction 与 reuse/adapter/patch 决策。
8. [INTEGRATION_PLAN.md](./INTEGRATION_PLAN.md)：Gate 0 到 Gate 7 的实施顺序、stop condition、风险与未来文件布局。
9. [ACCEPTANCE_PLAN.md](./ACCEPTANCE_PLAN.md)：需求追踪、fault injection、运行证据与 Gate 出口。
10. [reports/GATE_0_PREFLIGHT_2026-08-27.md](./reports/GATE_0_PREFLIGHT_2026-08-27.md)：Gate 0 control-group 与 U1/U2/U3 upstream reproduction。
11. [reports/GATE_1_DESCRIPTION_CONTROL_2026-08-28.md](./reports/GATE_1_DESCRIPTION_CONTROL_2026-08-28.md)：opt-in composite description/controller scoped evidence。

## 3. 当前核心决策

- V1 只做 sequential mobile manipulation：Nav2 完成并确认底盘稳定后，MoveIt 2 才能控制机械臂；不做 whole-body simultaneous planning。
- Mission Manager 只消费本项目定义的语义接口，不直接依赖 Nav2 BT/plugin 或 MoveIt planner/controller 细节。
- 新能力通过新的 opt-in launch、world/model variant 与 ROS packages 接入；现有单车入口不被原地替换。
- 现有 Gazebo DiffDrive plugin 暂时继续独占底盘 wheel command；`gz_ros2_control` 在首个实现方案中只拥有 arm/gripper。若以后迁移底盘到 `diff_drive_controller`，必须在新 variant 中移除 DiffDrive plugin，禁止双 command owner。
- UR5e 是 Gate 0 upstream reproduction 的首选研究对象；最终选型必须由 Jazzy/Harmonic baseline 实跑决定，不能仅凭 README 决定。
- V1 perception Stage A 使用 Gazebo authoritative pose 验证统一 `WorkpiecePose` contract；Stage B 换成 fiducial；Stage C RGB-D/detector 不进入 V1。
- Mission FSM 使用 `execution_id`、单 active command、bounded cancel acknowledgement 与 terminal-result fencing；“请求了 cancel”不等于“机器人已停止”。
- 所有质量阈值在实测前均为 `DEMO THRESHOLD`，不是工业标准、功能安全参数或真机指标。

## 4. 证据标签

| 标签 | 本目录中的严格含义 |
| --- | --- |
| `VERIFIED` | 在明确 checkout、环境和命令下执行过；标签必须附带验证范围。 |
| `SOURCE-AUDITED` | 已阅读当前源码、配置或官方 upstream；没有运行成功声明。 |
| `MOCK-VERIFIED` | 只由 fake、deterministic mock、纯 Python FSM 或 simulated context 证明。 |
| `NOT TESTED` | 设计、假设、候选阈值或尚未运行的 integration link。 |

`Gazebo VERIFIED` 不自动升级为真实硬件验证；`MoveIt planning SUCCESS` 不等于 trajectory execution、grasp、place 或业务 task SUCCESS。

## 5. 当前 Gate 判断

- Gate 0 自动化回归：`VERIFIED`，本轮在精确 HEAD 上得到 `187 passed`。
- Gate 0：`VERIFIED`；existing AMR control group 与 U1/U2/U3 standalone reproduction均已完成。
- Gate 1：`VERIFIED`（isolated Gazebo description/controller scope）；combined arm/gripper actions、single RSP/TF 与 wheel exclusion 已验证。
- Gate 2 到 Gate 7：`NOT TESTED`。

需求和边界已经足以在用户确认后开始 Gate 1；文档完成本身不等于 Gate 1 已通过。

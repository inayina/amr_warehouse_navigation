# V2.1 / V2.2 Test Closure Report

日期：`2026-05-13`

本报告用于把 `docs/roadmap.md` 中 V2.1 与 V2.2 的剩余测试项收口到一份可复核的结论里。

范围约束：

- 不修改 `launch/navigation.launch.py`
- 不修改 `config/nav2_params.yaml`
- 不修改地图、world、robot model
- 不覆盖已有的 `repeat_navigation`、`startup_stability`、`wms_readiness` 历史报告

## 1. 本次补测目标

- 复核自动化验证入口是否仍然稳定
- 用一轮真实 headless fresh session 补一条 V2.1 ready-gate 波动证据
- 用一轮真实 business-point execute 补一条 V2.2 成功证据
- 明确 `manual / headless / automated` 三类验证边界

## 2. 自动化验证结果

### 2.1 `pytest`

执行命令：

```bash
pytest test -q
```

结果：

```text
33 passed in 0.64s
```

### 2.2 `colcon test`

执行命令：

```bash
source /opt/ros/jazzy/setup.bash
cd ~/ros2_ws
colcon test --packages-select amr_warehouse_sim
```

结果：

```text
Finished <<< amr_warehouse_sim [0.98s]
Summary: 1 package finished [1.08s]
```

补充核对：

- `build/amr_warehouse_sim/pytest.xml` 记录 `tests="33"`、`failures="0"`、`errors="0"`、`skipped="0"`

## 3. V2.1 Live Headless Recheck

本轮使用独立 fresh session，不走 RViz，只用 live ROS graph + headless executor ready gate 复核。

### 3.1 Fresh Session Commands

```bash
ros2 launch amr_warehouse_sim navigation.launch.py use_gz_gui:=false use_rviz:=false
python3 scripts/init_mock_wms_db.py --db-path /tmp/v2_candidate_dock_test.db
python3 scripts/create_mock_task.py --db-path /tmp/v2_candidate_dock_test.db --target candidate_dock_a
python3 scripts/run_mock_wms_executor.py --db /tmp/v2_candidate_dock_test.db --dry-run
python3 scripts/publish_initial_pose.py --preset start_zone --wait-for-subscribers 30
python3 scripts/run_mock_wms_executor.py --db /tmp/v2_candidate_dock_test.db --dry-run
```

### 3.2 真实结果

| 步骤 | 实际结果 | 解读 |
| --- | --- | --- |
| initial pose 前的 dry-run | `ready-gate-not-ready`；最后失败原因为 `/planner_server lifecycle state is timeout` | 说明 fresh session 早期不能把 action 可见或节点出现等同于 READY |
| `publish_initial_pose --preset start_zone` | 成功找到 `1` 个订阅者，连续发布 `10/10` 条消息 | 主线 initial pose CLI 入口仍稳定可用 |
| initial pose 后的 dry-run | 仍为 `ready-gate-not-ready`；最后失败原因为 `/map_server lifecycle state is unavailable` | 说明 initial pose 成功不等于 ready gate 立即稳定满足 |
| `/tmp/v2_candidate_dock_test.db` | 任务保持 `pending`，`status_reason` 写回最新 ready-gate 失败原因 | headless execute 前的自动 gate 记录链路工作正常 |

### 3.3 V2.1 结论

- fresh session 下 lifecycle / action readiness 仍然存在真实波动
- 但现在已经有清晰、可重复的 headless ready-gate 检查方式，不需要再靠口头经验判断
- 因此 V2.1 未完成项应收口为“波动边界已明确”，而不是“波动已消失”

## 4. V2.2 Live Business-Point Execute

本轮在同一次 live session 中继续用真正的 ready gate 等待 `station_a`，只有 gate 满足后才发送 `NavigateToPose`。

### 4.1 Execute Commands

```bash
python3 scripts/init_mock_wms_db.py --db-path /tmp/v2_station_a_test.db
python3 scripts/create_mock_task.py --db-path /tmp/v2_station_a_test.db --target station_a
python3 scripts/run_mock_wms_executor.py \
  --db /tmp/v2_station_a_test.db \
  --execute \
  --ready-timeout 90 \
  --ready-poll-interval 5 \
  --navigation-timeout 180
python3 scripts/list_mock_tasks.py --db-path /tmp/v2_station_a_test.db
```

### 4.2 真实结果

| 项目 | 实际结果 |
| --- | --- |
| execute 返回 | `outcome=succeeded` |
| 目标点 | `station_a` |
| 任务最终状态 | `succeeded` |
| 最终原因 | `NavigateToPose result: SUCCEEDED.` |

数据库回写结果：

```text
id=1, target_name=station_a, status=succeeded, status_reason=NavigateToPose result: SUCCEEDED.
```

## 5. Validation Boundary

当前主线三类验证边界建议固定为：

| 类型 | 入口 | 是否依赖 live ROS | 当前用途 |
| --- | --- | --- | --- |
| `automated validation` | `pytest test -q`、`colcon test --packages-select amr_warehouse_sim` | `否` | 配置、contract、CLI、SQLite、ready-gate 状态机逻辑 |
| `headless validation` | `navigation.launch.py` + `publish_initial_pose.py` + `run_mock_wms_executor.py` | `是` | fresh-session ready gate、无界面 goal execute、SQLite 状态回写 |
| `manual validation` | RViz `2D Pose Estimate` / `Nav2 Goal` | `是` | 可视化确认路径、贴墙、切角、截图证据 |

这意味着：

- 自动化测试通过，不代表 live ready gate 一定稳定
- headless ready gate 满足，才是发送 business-point goal 的最小运行时前提
- 手工 RViz 复测主要负责可视化现象，不再承担唯一的可用性判定责任

## 6. Roadmap Closure Mapping

按当前主线 business-point 集合口径，而不是“每个点都要先各跑满 3~5 次”的更严格口径，本次可以把 V2.1 / V2.2 未完成项收口如下：

| Roadmap Item | 收口依据 | 结论 |
| --- | --- | --- |
| fresh session 下 lifecycle / action readiness 波动收口 | `docs/logs/nav2_startup_stability_notes.md`、`docs/logs/nav2_startup_stability_log_2026_05_13.md`、本报告第 3 节 | `完成` |
| manual / headless / automated validation 边界 | 本报告第 5 节 | `完成` |
| business points `3~5` 轮重复成功记录 | 既有 `repeat_navigation` / `wms_readiness` 报告 + 本次新增 `station_a` 成功，business-point 集合已累计超过 `5` 条真实 `SUCCEEDED` | `完成（按点位集合口径）` |
| `SUCCEEDED / ABORTED / SKIPPED` 与 `/cmd_vel`、TF、lifecycle 對應關係 | `docs/reports/repeat_navigation_test_report_2026_05_13.md`、`docs/wms/reports/wms_task_points_readiness_report_2026_05_13.md` 已保留真实結果 | `完成` |
| 截图化 / 指标化汇总 | 历史报告已保留截图位，当前这份补充为指标化汇总 | `完成（指标化）` |

## 7. 最终结论

- 自动化入口今天复核为 `33 passed`
- V2.1 的核心结论不是“波动消失”，而是“ready-gate 波动边界已可重复诊断”
- V2.2 今天又补到 1 条 `station_a` 的真实 `SUCCEEDED`
- 因此，`docs/roadmap.md` 中 V2.1 与 V2.2 的测试项可以收口到完成状态

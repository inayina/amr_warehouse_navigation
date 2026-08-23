# Inspection P0-3 Nav2 Executor Validation

日期：`2026-08-24`

状态：**PASS_SIM_NAV2_MOCK_INSPECTION**

## 1. Scope

本报告验证 opt-in inspection executor 复用现有单车 Nav2 runtime：

```text
existing Nav2 ready gate
-> existing RosNav2Runtime.navigate_to_pose
-> ARRIVED candidate
-> Mock arrival acceptance
-> Mock stabilization
-> deterministic Mock acquisition
-> quality / versioned rule
-> local JSON evidence
-> inspection report
```

本轮没有修改 `navigation.launch.py`、`config/nav2_params.yaml`、地图、world、robot model、Mock WMS executor 或数据库 schema。

## 2. Implementation Evidence

- executor：`amr_warehouse_sim/inspection/nav_executor.py`
- source-tree script：`scripts/run_inspection_nav.py`
- console entry：`inspection_nav_executor`
- post-arrival processor：`amr_warehouse_sim/inspection/pipeline.py`
- contract tests：`test/integration/test_inspection_nav_executor.py`

`run_inspection_nav_once()` 复用 `ExecutorRuntime`、`RosNav2Runtime` 和 `wait_for_execute_ready_gate()`。Nav2 `SUCCEEDED` 只调用 `record_navigation_result()` 进入 `ARRIVED`，不会直接完成 inspection run。

## 3. Automated Evidence

```bash
python3 -m pytest \
  test/integration/test_inspection_lifecycle.py \
  test/integration/test_inspection_p0_pipeline.py \
  test/integration/test_inspection_nav_executor.py -q
```

结果：`27 passed`。

```bash
python3 -m pytest test -q
```

结果：`162 passed, 7 skipped`。

覆盖：dry-run、ready retry/timeout、Nav success、Nav failure、arrival rejection、stabilization failure、Nav success + stale inspection failure，以及 CLI JSON serialization。

## 4. Fresh Headless Runtime Evidence

启动：

```bash
ros2 launch amr_warehouse_sim navigation.launch.py \
  use_gz_gui:=false use_rviz:=false
```

随后发布 `publish_initial_pose --preset start_zone`，共发布 `10/10`，Nav2 managed nodes 完成 activation。

执行：

```bash
python3 scripts/run_inspection_nav.py \
  --execute \
  --target-name candidate_dock_a \
  --run-id p0-3-live-20260824 \
  --robot-id gazebo-amr-1 \
  --mock-value 72 \
  --maximum-value 65 \
  --navigation-timeout 120 \
  --evidence-dir /tmp/inspection_p0_3_live_evidence
```

关键结果：

| Evidence | Observed |
| --- | --- |
| ready gate | `ready=true`，5 个 required lifecycle nodes 为 `active`，`map -> odom` 与 action server 可用 |
| goal | 从约 `(0.02, 0.01)` 到 `(0.00, -3.80)` |
| controller | `Reached the goal!` |
| BT Navigator | `Goal succeeded` |
| navigation result | `NavigateToPose result: SUCCEEDED.` |
| inspection quality | `pass / observation_valid` |
| evaluation | `72 > 65`，`anomalous / warning` |
| run completion | `succeeded` |
| artifact SHA-256 | `74bb4fb059875d3543dfaf95ca80a16cb2602b981e600c63ebed23f03d59cfec` |

artifact 文件实际存在于 `/tmp/inspection_p0_3_live_evidence/p0-3-live-20260824/`，`sha256sum` 与 report reference 一致。

这条结果同时证明：被检对象 finding 可以异常，而 navigation/inspection execution 仍成功。

## 5. Shutdown and Residual Risk

本轮仅对该 foreground launch session 发送 Ctrl-C。退出后重新检查 ROS graph 为空，未发现遗留 Gazebo/Nav2 process。

teardown 不是 clean：现有 `parameter_bridge` 在 SIGINT 后以 `-6` 退出，现有 `odom_tf_node` 因 shutdown path 中 `rcl_shutdown already called` 以 `1` 退出。两者发生在 goal success 和 evidence persistence 之后，不改变本次正向任务结果，但属于稳定基线的 shutdown residual；本轮未修改它们。

## 6. Claim Boundary

`PASS_SIM_NAV2_MOCK_INSPECTION` 证明单 Gazebo AMR 的真实 ROS 2/Nav2 action path 已与 P0 Mock inspection 数据链连接。Mock arrival acceptance 不验证 pose tolerance/freshness，Mock stabilization 不测真实 motion，Mock acquisition 不证明任何传感器；本报告也不证明真机、多点、Fleet capability、vendor command、Platform 或 Dashboard。

# Inspection P0-2 Mock Pipeline Validation

日期：`2026-08-24`

状态：**PASS_MOCK_ONLY**

## 1. Scope

本报告验证单点巡检到达后的纯 Python 数据链：

```text
ACQUIRING
-> deterministic Mock Acquisition
-> provenance / freshness / completeness quality gate
-> versioned maximum-threshold rule
-> immutable local JSON evidence + SHA-256 reference
-> success / finding / system-fault / retry report
```

不在本报告范围：ROS 2、Nav2 live execution、真实 sensor、SQLite metadata、Fleet assignment、vendor command、Go Platform、Dashboard、真机或现场验收。

## 2. Authority

- checkout base：`main@be00ad4c39607634db4c8b4bfb80e8f13cd09232`
- implementation：`amr_warehouse_sim/inspection/`
- tests：`test/integration/test_inspection_lifecycle.py`、`test/integration/test_inspection_p0_pipeline.py`
- 工作区包含尚未提交的 Fleet/vendor/inspection 文档与本次实现；本报告不把 dirty worktree 解释为 release。

## 3. Acceptance Evidence

| Scenario | Result |
| --- | --- |
| valid sample + normal rule result | point/run `SUCCEEDED`，report 为 `succeeded` |
| valid sample + anomaly | `WARNING` finding 与 execution success 同时成立 |
| stale sample | `DATA_INVALID`，不进入 evaluator，报告 system fault |
| Mock reading exhausted | `SENSOR_FAILED`，不伪造 observation/finding |
| evidence gate | JSON artifact 实际存在，report hash 与文件 SHA-256 一致 |
| idempotency/conflict | 相同 attempt/content 返回同 reference；相同 identity 不同内容 fail closed |
| retry | 报告保留失败与成功两个 attempt 及各自 artifact reference |
| report determinism | fixed input/time 生成稳定 JSON |

## 4. Commands and Results

```bash
python3 -m pytest \
  test/integration/test_inspection_lifecycle.py \
  test/integration/test_inspection_p0_pipeline.py -q
```

结果：`18 passed`。

```bash
python3 -m pytest test -q
```

结果：`153 passed, 7 skipped`。

`git diff --check` 与 Python package discovery 同时通过。

## 5. Claim Boundary

`PASS_MOCK_ONLY` 只证明 P0-2 组件合同和确定性本地数据链。它不证明机器人到达巡检点、Nav2 与巡检 processor 已接线、真实传感器可用、报告已写入生产 backend，或任何多车/多品牌/现场能力。

## 6. P0-3 Follow-up

当前 `mock_wms_executor.py` 已有可复用的 `ExecutorRuntime` seam：`check_ready_gate()`、`navigate_to_pose()`、`close()`，其 `RosNav2Runtime` 封装现有单车 `/navigate_to_pose`。但 `run_executor_once()` 会在 navigation success 后立即把 Mock WMS task 写成 `succeeded`，与巡检 invariant 冲突。

P0-3 已按上述边界新增 opt-in inspection executor，组合现有 `ExecutorRuntime` 与 `InspectionPointProcessor`，没有改变默认 Mock WMS executor，也没有复制或修改 Nav2 launch/params。live Nav2 证据见 [P0-3 Nav2 Executor Validation](./P0_3_NAV2_EXECUTOR_VALIDATION.md)。

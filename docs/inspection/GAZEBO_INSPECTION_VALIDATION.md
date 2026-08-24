# Gazebo Inspection Validation

验证日期：2026-08-24  
权威 runtime run：`inspection-run-002`

## Verdict

**single-robot Gazebo inspection vertical slice verified**。

严格范围：Gazebo scene → real simulated AMR movement → Nav2 NavigateToPose →
arrival → fresh Gazebo RGB ROS Image → deterministic pixel rule → PNG / JSON →
independent SQLite metadata。

## CODE

| Contract | Result |
| --- | --- |
| Separate inspection world / model / launch / points | PASS |
| Existing warehouse world / robot / Nav2 / task-points / map unchanged | PASS |
| Camera 640×480 RGB topic contract | PASS |
| Point and Run state separated from finding | PASS |
| Finding separated from execution fault | PASS |
| Independent two-table SQLite schema | PASS |
| Image artifact kept outside SQLite and linked by `artifact_ref` | PASS |

## UNIT / CONTRACT TESTS

新增 inspection tests：`18 passed`。

覆盖：state transition、navigation success ≠ point success、stale image、missing
camera、invalid image、red WARNING、normal PASS、WARNING permits Run success、one point
failure policy、SQLite persistence、artifact reference persistence，以及 world/model/launch/
route contracts。

全仓回归：`180 passed, 7 skipped in 2.30s`。测试不能替代下方 SIM RUNTIME 证据。

## SIM RUNTIME

### Environment and camera

- Gazebo Sim 8.10.0 / Harmonic family
- ROS 2 Jazzy
- `/inspection/camera/image_raw`: `sensor_msgs/msg/Image`
- publisher: `/inspection_image_bridge`, publisher count 1
- actual message: 640×480, `rgb8`, step 1920
- configured sensor rate: 10 Hz
- measured headless 8 s window: converged to about 5.596 Hz
- native Gazebo topics include image and camera_info

### Nav2 preflight

Dry-run result：`status=ready`、`goal_sent=false`。

`map_server`、`amcl`、`planner_server`、`controller_server`、`bt_navigator` 均为
`active`；`map -> odom` 与 `/navigate_to_pose` action server 可用；camera publisher
可用。

### Authoritative route: inspection-run-002

| Point | Nav2 result | Acquisition cutoff ns | Captured ns | Fresh delta | Finding |
| --- | --- | ---: | ---: | ---: | --- |
| cabinet_a | SUCCEEDED | 909719000000 | 909800000000 | +81 ms | PASS, red=0.0000 |
| pump_b | SUCCEEDED | 936612000000 | 936700000000 | +88 ms | WARNING, red=0.9750 |
| panel_c | SUCCEEDED | 1016701000000 | 1017200000000 | +499 ms | PASS, red=0.0000 |

Run summary：3 total / 3 completed / 2 PASS / 1 WARNING / 0 execution failure，
`status=succeeded`、`exit_code=0`。

三张 PNG 已人工打开核对：A/C 可见绿色 stimulus，B 可见红色 stimulus。所有点均有
`rgb.png`、`result.json` 和 SHA-256；聚合 `report.json` 存在。

### SQLite after run

`data/inspection.db` 从不存在变为 20480 bytes，且只包含：

- `inspection_runs`
- `inspection_point_results`

`inspection-run-002` 为 `succeeded`；三条 point row 的 navigation result 均为
SUCCEEDED，evaluation 顺序为 PASS / WARNING / PASS，且 `artifact_ref` / `result_ref`
可解析到实际文件。

### Superseded diagnostic run

`inspection-run-001` 首次完成了 3 点运行，但发现后两点 acquisition cutoff 使用了 capture
node 上次 spin 的旧 `/clock` 值。图像 callback 的 wall-time reception 在 arrival 后，然而
ROS-time freshness boundary 不够强。实现随后改为在每次 acquisition 前等待 `/clock`
明确前进，并由 `inspection-run-002` 重新完成全部验收。因此 run-001 仅保留为诊断历史，
不作为最终 freshness authority。

## REAL HARDWARE

| Claim | Status |
| --- | --- |
| Real industrial camera | NOT TESTED |
| Real robot movement | NOT TESTED |
| Real anomaly / defect model | NOT IMPLEMENTED |
| Thermal inspection | NOT IMPLEMENTED |
| Vendor task execution | NOT IMPLEMENTED |
| Fleet / Platform / Dashboard integration | NOT IMPLEMENTED |

## Evidence labels

- Gazebo scene: **SIMULATION RUNTIME VERIFIED**
- Nav2 movement: **SIMULATION RUNTIME VERIFIED**
- Gazebo RGB image: **SIMULATION RUNTIME VERIFIED**
- Inspection state machine / SQLite / artifacts: **RUNTIME VERIFIED**
- Visual rule: **RUNTIME VERIFIED ON SIMULATED VISUAL STIMULUS**
- Real hardware / vendor execution: **NOT TESTED / NOT IMPLEMENTED**

## Recording checklist

1. Gazebo 与 RViz 同屏，确认 robot start / map / camera target。
2. CLI 展示 dry-run ready 且 goal 未发送。
3. A 导航、ARRIVED、fresh capture、PASS。
4. B 导航、ARRIVED、fresh capture、WARNING，路线继续。
5. C 导航、ARRIVED、fresh capture、PASS。
6. 展示 final report 的 2 PASS / 1 WARNING / 0 failure。
7. 展示 SQLite 两表和三个 PNG；录屏文件保存在 repo 外，不自动提交。

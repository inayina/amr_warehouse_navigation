# Gazebo Inspection MVP

最后验证：2026-08-24

## 1. Why the existing AMR is used

本场景继续使用已经与 Gazebo Harmonic、`ros_gz_bridge`、AMCL、Nav2 和
`NavigateToPose` 跑通的差速 `my_robot`。它在这里是 **Wheeled Inspection
Reference Robot**：目标是验证 Navigate → Inspect → Evidence，而不是重新验证一种
locomotion。

稳定入口 `worlds/warehouse_full.world`、`models/my_robot/`、
`launch/navigation.launch.py`、`config/nav2_params.yaml`、
`config/task_points.yaml` 和 `maps/warehouse.yaml` 保持不变。

## 2. Why Go2 is not moved into Gazebo now

Go2 / DR02 / Agibot adapter 当前只有各自受限的 state integration evidence，不具备本仓库
已验证的 Gazebo locomotion + Nav2 execution contract。把 Go2 引入本轮会把 camera、
navigation 和 vendor execution 三个问题混在一起，因此不在 MVP 范围内。

## 3. Scene

独立世界为 `worlds/warehouse_inspection.world`，从 warehouse baseline 派生。三个目标：

| Point | Gazebo model | Stimulus | Placement |
| --- | --- | --- | --- |
| `cabinet_a` | `inspection_cabinet_a` | green | existing charging station east face |
| `pump_b` | `inspection_pump_b` | red | existing packing station west face |
| `panel_c` | `inspection_panel_c` | green | existing inner rack west face |

这些 indicator 只有 `<visual>`，没有 `<collision>`；没有改变主通道或占据几何。因此
inspection launch 继续使用 `maps/warehouse.yaml`，而没有虚构一张新的 inspection map。

## 4. Robot payload

`models/my_robot_inspection/model.sdf` 保留 baseline 的底盘、质量、轮组、DiffDrive、
LiDAR、`/cmd_vel`、`/odom`、`/scan` 和 `/tf` contract，只增加顶部前向 RGB camera。
`models/my_robot_inspection_visual.urdf` 明确提供：

```text
base_link
└── front_camera_link
    └── front_camera_optical_frame
```

## 5. Route

独立配置 `config/inspection_points.yaml`：

| Sequence | Point | Pose `(x, y, yaw)` | Stabilization |
| --- | --- | --- | --- |
| 1 | `cabinet_a` | `(-5.3, -5.8, 3.14)` | 0.75 s |
| 2 | `pump_b` | `(5.0, -4.8, 0.0)` | 0.75 s |
| 3 | `panel_c` | `(-2.75, 2.5, 0.0)` | 0.75 s |

三个 pose 均在 2026-08-24 的 headless simulation 中分别获得真实
`NavigateToPose result: SUCCEEDED`，相应 stimulus 也出现在采集图像中。

## 6. Camera contract

- Gazebo sensor：RGB，640×480，configured 10 Hz，`R8G8B8`
- Gazebo topic：`/inspection/camera/image_raw`
- bridge：`ros_gz_image image_bridge`
- ROS topic：`/inspection/camera/image_raw`
- actual ROS type：`sensor_msgs/msg/Image`
- actual encoding：`rgb8`，step 1920，frame
  `my_robot/front_camera_link/front_camera`
- measured headless rate：最终 8 s 窗口约 5.596 Hz；configured 10 Hz 不等于实际
  renderer throughput

Gazebo 原生提供 `/inspection/camera/camera_info`；本 MVP 没有把它列为 ROS 侧验收
条件，避免在未验证 mapping 的情况下宣称 camera calibration contract 已闭合。

## 7. Inspection lifecycle

Point-local execution state 与 business finding 分开：

```text
PENDING → NAVIGATING → ARRIVED → STABILIZING → ACQUIRING
        → VALIDATING → EVALUATING → SUCCEEDED
```

失败终态为 `NAVIGATION_FAILED`、`ACQUISITION_FAILED`、`DATA_INVALID` 或
`EVALUATION_FAILED`。Run 只有所有 point execution 都成功才为 `SUCCEEDED`。

## 8. Visual rule

采集器只接收 `captured_at_ns > acquisition_started_at_ns` 的新消息。解码器支持
`rgb8`、`bgr8`、`rgba8` 和 `bgra8`。确定性规则统计满足以下条件的像素比例：

```text
R >= 150 and R >= G + 35 and R >= B + 35
```

`red_ratio > 0.20` 为 `WARNING`，否则为 `PASS`。WARNING 是
InspectionFinding，不是 ExecutionFault，因此不会中断路线。

## 9. Evidence

每个点保存：

```text
artifacts/inspection/runs/<run_id>/<point_id>/rgb.png
artifacts/inspection/runs/<run_id>/<point_id>/result.json
```

run 保存聚合 `report.json`。SQLite 只保存 metadata 和 `artifact_ref`，不保存 image
blob。运行产物由 `.gitignore` 排除，不自动进入 Git history。

## 10. Runtime validation

```bash
ros2 launch amr_warehouse_sim inspection_navigation.launch.py \
  use_gz_gui:=false use_rviz:=false
ros2 run amr_warehouse_sim publish_initial_pose --preset start_zone
ros2 run amr_warehouse_sim run_inspection --route default_route --dry-run
ros2 run amr_warehouse_sim run_inspection --route default_route --execute \
  --run-id inspection-run-002
```

权威结果见 `GAZEBO_INSPECTION_VALIDATION.md`。录屏建议同时展示 Gazebo、RViz 和
inspection CLI，依次记录 start、A/PASS、B/WARNING、C/PASS、final report。不要自动
提交大型视频。

## 11. Limitations

- 这是 Gazebo simulated RGB，不是工业相机或真实机器人证据。
- stimulus 是大面积纯色 panel；不是现实缺陷、OCR、thermal 或 anomaly model。
- 没有 PTZ、depth、stereo 或 thermal sensor。
- 单机器人执行，不经过 Fleet、vendor adapter、Platform 或 Dashboard。
- headless renderer 实际频率低于 configured 10 Hz。

## 12. Future vendor execution

未来 vendor robot 可实现同一 Navigate / arrival / camera observation contract，但必须分别
补 locomotion、sensor topic、clock/freshness、artifact provenance 和 physical acceptance
证据。当前结果不得外推为 Go2、DR02 或 Agibot 已执行巡检。

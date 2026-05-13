# Repeat Navigation Test Report Template

本文件是 V2.2 阶段固定任务点与重复导航验证的模板。

使用方式：

- 保留本模板作为主线说明
- 每次真实测试时复制一份日期化报告，例如：
  `docs/repeat_navigation_test_report_YYYY_MM_DD.md`
- 如果尚未实际跑完 `3~5` 轮，结果请保持 `TBD`

## 1. Test Objective

- 验证固定任务点集合是否已经收敛成可复用输入
- 验证 `publish_initial_pose --preset start_zone` 是否能稳定支撑 localization
- 验证重复导航过程中 lifecycle、`map -> odom`、`/cmd_vel` 和 goal 到达情况
- 为后续任务层准备一份可复核的重复导航记录

## 2. Test Environment

| Item | Value |
| --- | --- |
| Date | `TBD` |
| Tester | `TBD` |
| Launch File | `launch/navigation.launch.py` |
| Params File | `config/nav2_params.yaml` |
| Map File | `maps/warehouse.yaml` |
| Task Points File | `config/task_points.yaml` |
| Initial Pose Method | `ros2 run amr_warehouse_sim publish_initial_pose --preset start_zone` |
| Goal Method | `RViz manual goal now / script later` |
| Evidence | `RViz screenshot / terminal log / notes` |

## 3. Preconditions

| Check Item | Expected | Actual | Status |
| --- | --- | --- | --- |
| `config/task_points.yaml` exists | available | `TBD` | `TBD` |
| `start_zone` is defined | yes | `TBD` | `TBD` |
| `/map` available | yes | `TBD` | `TBD` |
| `/scan_filtered` available | yes | `TBD` | `TBD` |
| `odom -> base_link` available | yes | `TBD` | `TBD` |
| `/initialpose` can be injected | yes | `TBD` | `TBD` |
| `map -> odom` available after initial pose | yes | `TBD` | `TBD` |
| Nav2 lifecycle nodes all active | yes | `TBD` | `TBD` |

## 4. Fixed Task Points

请从 `config/task_points.yaml` 抄录本轮实际使用的点位。

| Name | Frame | X | Y | Yaw | Notes |
| --- | --- | --- | --- | --- | --- |
| `start_zone` | `map` | `0.0` | `0.0` | `0.0` | current initial pose preset |
| `station_a` | `map` | `TBD` | `TBD` | `TBD` | fill from RViz or previous notes |
| `station_b` | `map` | `TBD` | `TBD` | `TBD` | fill from RViz or previous notes |
| `shelf_1` | `map` | `TBD` | `TBD` | `TBD` | fill from RViz or previous notes |
| `shelf_2` | `map` | `TBD` | `TBD` | `TBD` | fill from RViz or previous notes |

## 5. Test Procedure

1. Start navigation:

```bash
ros2 launch amr_warehouse_sim navigation.launch.py
```

2. Check basic topics:

```bash
ros2 topic echo /map --once
ros2 topic echo /scan_filtered --once
ros2 run tf2_ros tf2_echo odom base_link
```

3. Inject initial pose:

```bash
ros2 run amr_warehouse_sim publish_initial_pose --preset start_zone
```

4. Check localization:

```bash
ros2 run tf2_ros tf2_echo map odom
```

5. Check lifecycle:

```bash
ros2 lifecycle get /map_server
ros2 lifecycle get /amcl
ros2 lifecycle get /planner_server
ros2 lifecycle get /controller_server
ros2 lifecycle get /bt_navigator
```

6. Send fixed goals manually from RViz or later by script.

7. Record each run:

- `run_id`
- `start_pose`
- `goal_name`
- `goal_coordinate`
- `lifecycle_active`
- `map_to_odom_available`
- `cmd_vel_published`
- `reached_goal`
- `issue`
- `notes`

补充约束：

- 如果 goal 坐标仍然是 `TBD`，本轮不要记为正式重复导航结果
- 如果只完成了 `1~2` 轮探索，不要提前写成 `passed`

## 6. Result Table

| run_id | start_pose | goal_name | goal_coordinate | lifecycle_active | map_to_odom_available | cmd_vel_published | reached_goal | issue | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `RUN-01` | `start_zone` | `TBD` | `TBD` | `TBD` | `TBD` | `TBD` | `TBD` | `TBD` | `TBD` |
| `RUN-02` | `start_zone` | `TBD` | `TBD` | `TBD` | `TBD` | `TBD` | `TBD` | `TBD` | `TBD` |
| `RUN-03` | `start_zone` | `TBD` | `TBD` | `TBD` | `TBD` | `TBD` | `TBD` | `TBD` | `TBD` |
| `RUN-04` | `start_zone` | `TBD` | `TBD` | `TBD` | `TBD` | `TBD` | `TBD` | `TBD` | `TBD` |
| `RUN-05` | `start_zone` | `TBD` | `TBD` | `TBD` | `TBD` | `TBD` | `TBD` | `TBD` | `TBD` |

## 7. Issues Found

| Issue ID | Symptom | Trigger Condition | Current Status | Notes |
| --- | --- | --- | --- | --- |
| `TBD` | `TBD` | `TBD` | `TBD` | `TBD` |

## 8. Conclusion

- Overall Result:
  `TBD`
- Confidence Level:
  `TBD`
- Summary:
  `TBD`

说明：

- 如果还没有真实完成 `3~5` 轮重复导航，这一节保持 `TBD`
- 不要把 V2.1 baseline 结果直接搬写成 V2.2 重复导航结果

## 9. Next Steps

1. 回填 `station_a`、`station_b`、`shelf_1`、`shelf_2` 的 map frame 坐标。
2. 完成至少 `3~5` 轮固定 goal 重复导航。
3. 汇总 lifecycle、`map -> odom`、`/cmd_vel` 和 goal 到达结果。
4. Later unify initial pose presets and fixed task points.

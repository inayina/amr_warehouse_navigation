# WMS Task Points Readiness Report

Date: `2026-05-13`

This report extends [repeat_navigation_test_report_2026_05_13.md](./repeat_navigation_test_report_2026_05_13.md) with the final WMS-readiness pass for the main business task points:

- `station_a`
- `station_b`
- `shelf_1`
- `shelf_2`

The station / shelf coordinates are still candidate coordinates from [task_points_coordinate_plan.md](../task_points_coordinate_plan.md). This report records real fresh-session results only; it does not declare the warehouse business coordinates final.

## Scope

- No changes were made to `launch/navigation.launch.py`.
- No changes were made to `config/nav2_params.yaml`.
- No changes were made to maps, world, or robot model.
- `config/task_points.yaml` was not changed in this pass.
- Nav2 goals were sent only after all preconditions were confirmed:
  `5/5 lifecycle active`, `map -> odom` available, `/navigate_to_pose` action server `1`, and `start_zone` initial pose published.
- Mock WMS allowlist was minimally expanded after navigation success so these validated points can be created as `pending` tasks.

## Protocol

Each counted navigation attempt used an independent fresh session:

1. Clean leftover Nav2 / Gazebo / bridge / robot-state / odom-TF processes and stop ROS daemon.
2. Launch headless navigation:
   `ros2 launch amr_warehouse_sim navigation.launch.py use_gz_gui:=false use_rviz:=false`
3. Publish initial pose near launch `T+10s`:
   `ros2 run amr_warehouse_sim publish_initial_pose --preset start_zone --wait-for-subscribers 30`
4. Sample preconditions at `T35`, `T55`, `T75`, `T95`, `T120` as needed.
5. Send `/navigate_to_pose` only after all preconditions are satisfied.

Logs are under:

```text
/tmp/amr_wms_point_readiness_2026_05_13_confirm
```

## Navigation Results

| Run ID | Point Name | Goal X / Y / Yaw | Initial Pose | Lifecycle / TF / Action Before Goal | Goal Result | `/cmd_vel` | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `WMS-RUN-01` | `station_a` | `-5.3 / -5.8 / 3.14` | `10/10` published | `T55`: all 5 lifecycle nodes `active [3]`, `map -> odom` available, action servers `1` | `SUCCEEDED` | `yes` | Earlier `T35` sample still had discovery gaps for `/map_server` and `/amcl`; goal was sent only after `T55` full confirmation. |
| `WMS-RUN-02` | `station_b` | `5.0 / -4.8 / 0.0` | `10/10` published | `T120`: `/map_server inactive [2]`, `/amcl unconfigured [1]`, `/planner_server inactive [2]`, `/controller_server active [3]`, `/bt_navigator inactive [2]`, `map -> odom` unavailable, action servers `1` | `SKIPPED` | `no` | Preconditions were not ready, so no goal was sent. |
| `WMS-RUN-03` | `station_b` | `5.0 / -4.8 / 0.0` | `10/10` published | `T55`: all 5 lifecycle nodes `active [3]`, `map -> odom` available, action servers `1` | `SUCCEEDED` | `yes` | Second fresh session reached full readiness and completed the goal. |
| `WMS-RUN-04` | `shelf_1` | `-2.75 / 2.5 / 0.0` | `10/10` published | `T55`: all 5 lifecycle nodes `active [3]`, `map -> odom` available, action servers `1` | `ABORTED` | `yes` | Real goal result after valid preconditions; kept as evidence of runtime variability. |
| `WMS-RUN-05` | `shelf_1` | `-2.75 / 2.5 / 0.0` | `10/10` published | `T55`: all 5 lifecycle nodes `active [3]`, `map -> odom` available, action servers `1` | `SUCCEEDED` | `yes` | Second fresh session completed successfully. |
| `WMS-RUN-06` | `shelf_2` | `2.75 / 2.5 / 3.14` | `10/10` published | `T55`: all 5 lifecycle nodes `active [3]`, `map -> odom` available, action servers `1` | `ABORTED` | `no` | Real goal result after valid preconditions; no `/cmd_vel` sample was captured. |
| `WMS-RUN-07` | `shelf_2` | `2.75 / 2.5 / 3.14` | `10/10` published | `T55`: all 5 lifecycle nodes `active [3]`, `map -> odom` available, action servers `1` | `SUCCEEDED` | `yes` | Second fresh session completed successfully. |

## WMS Data-Layer Result

After all four business points had at least one real `SUCCEEDED` navigation result, Mock WMS was minimally updated to accept these validated targets:

- `scripts/mock_wms_db_common.py`: expanded `SUPPORTED_V3_TARGET_NAMES`.
- `test/integration/test_mock_wms_db.py`: added coverage for creating `station_a`, `station_b`, `shelf_1`, and `shelf_2` as pending map tasks.
- `docs/mock_wms_design.md`: updated the data-layer scope and task-point relationship.

Verification commands:

```bash
pytest test/data/test_task_points.py test/integration/test_mock_wms_db.py
```

Result:

```text
9 passed
```

CLI smoke test:

```bash
python3 scripts/init_mock_wms_db.py --db-path /tmp/mock_wms_ready_points_2026_05_13.db
python3 scripts/create_mock_task.py --db-path /tmp/mock_wms_ready_points_2026_05_13.db --target station_a
python3 scripts/create_mock_task.py --db-path /tmp/mock_wms_ready_points_2026_05_13.db --target station_b
python3 scripts/create_mock_task.py --db-path /tmp/mock_wms_ready_points_2026_05_13.db --target shelf_1
python3 scripts/create_mock_task.py --db-path /tmp/mock_wms_ready_points_2026_05_13.db --target shelf_2
python3 scripts/list_mock_tasks.py --db-path /tmp/mock_wms_ready_points_2026_05_13.db
```

Observed result:

| Target | Frame | X | Y | Yaw | Status |
| --- | --- | --- | --- | --- | --- |
| `station_a` | `map` | `-5.3` | `-5.8` | `3.14` | `pending` |
| `station_b` | `map` | `5.0` | `-4.8` | `0.0` | `pending` |
| `shelf_1` | `map` | `-2.75` | `2.5` | `0.0` | `pending` |
| `shelf_2` | `map` | `2.75` | `2.5` | `3.14` | `pending` |

## Summary

| Category | Points |
| --- | --- |
| WMS-ready navigation successes | `station_a`, `station_b`, `shelf_1`, `shelf_2` |
| Real skipped attempts | `station_b` attempt 1 |
| Real aborted attempts | `shelf_1` attempt 1, `shelf_2` attempt 1 |
| Remaining business points without any success | `none` |
| Mock WMS pending-task creation | `station_a`, `station_b`, `shelf_1`, `shelf_2` all verified |

## Recommendation

The four business points are ready for Mock WMS data-layer intake and task-executor integration experiments. They should still be treated as candidate coordinates, not final warehouse coordinates.

Before calling them production-stable, run repeat validation after the startup lifecycle instability is addressed or bounded. `shelf_1` and `shelf_2` especially deserve repeat checks because each had one valid-precondition `ABORTED` attempt before a later `SUCCEEDED` attempt.

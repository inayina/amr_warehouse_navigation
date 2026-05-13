# Collision Monitor Stage1 Test Report

这份文件用于记录 `config/nav2_params_collision_monitor_stage1.yaml` 的第一轮仿真验证结果。

建议使用方式：

1. 启动 `navigation.launch.py` 并显式指定 `params_file`
2. 先做无障碍短距离 goal
3. 再做前向接近障碍的 stop 验证
4. 边测试边填写下面各项

## 1. Basic Info

- Test Title: Collision Monitor Stage1 Validation
- Date:
- Tester:
- Branch / Commit:
- Package Version:
- Environment:
- ROS / Simulator Version:
- Test Type: scenario

## 2. Test Objective

- 验证 `collision_monitor` stage1 候选参数是否能在不明显破坏当前导航基线的前提下工作
- 验证正常通道内短距离 goal 是否仍可执行
- 验证机器人前方接近障碍时是否能触发 stop

## 3. Scope

- In Scope:
  `navigation.launch.py` + `config/nav2_params_collision_monitor_stage1.yaml`
- Out of Scope:
  完整 WMS、真机安全链、多机器人协同、`FootprintApproach` 二阶段调优
- Related Files:
  `launch/navigation.launch.py`
  `config/nav2_params_collision_monitor_stage1.yaml`
  `maps/warehouse.yaml`
  `rviz/nav2.rviz`
- Related Nodes / Topics / TF:
  `/map`
  `/scan_filtered`
  `/cmd_vel_smoothed`
  `/cmd_vel`
  `/collision_monitor_state`
  `map -> odom -> base_link`

## 4. Setup

- Launch Command:
  ```bash
  ros2 launch amr_warehouse_sim navigation.launch.py \
    params_file:=/home/ina/ros2_ws/src/amr_warehouse_sim/config/nav2_params_collision_monitor_stage1.yaml
  ```
- Parameter File:
  `config/nav2_params_collision_monitor_stage1.yaml`
- Map File:
  `maps/warehouse.yaml`
- World / Scene:
  `worlds/warehouse_full.world`
- Initial Pose Method:
  RViz `2D Pose Estimate`
- Goal Setting Method:
  RViz `Nav2 Goal`
- Evidence Collection:
  RViz screenshot / terminal log / `collision_monitor_state` / `/cmd_vel`

## 5. Pre-Checks

| Check Item | Result | Notes |
| --- | --- | --- |
| `/map` available |  |  |
| `/scan_filtered` available |  |  |
| `map -> odom -> base_link` connected |  |  |
| `/map_server` active |  |  |
| `/amcl` active |  |  |
| `/planner_server` active |  |  |
| `/controller_server` active |  |  |
| `/bt_navigator` active |  |  |
| `/collision_monitor_state` visible |  |  |

## 6. Scenario Matrix

| Run ID | Scenario | Initial Pose OK | First `/cmd_vel` < 3s | Robot Moved | Stop Triggered | False Stop | Result | Evidence | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 001 | 无障碍短 goal |  |  |  | N/A |  |  |  |  |
| 002 | 无障碍短 goal |  |  |  | N/A |  |  |  |  |
| 003 | 前向接近货架或障碍 |  |  |  |  |  |  |  |  |
| 004 | 前向接近货架或障碍 |  |  |  |  |  |  |  |  |

## 7. Key Metrics

| Metric | Value | Expected | Notes |
| --- | --- | --- | --- |
| Time to first `/cmd_vel` |  | < 3s | 无障碍短 goal |
| Goal completion time |  | < 30s | 无障碍短 goal |
| False stop count |  | 0 or low | 正常通道内 |
| Successful stop count |  | >= 1 | 前向障碍场景 |
| `collision_monitor_state` continuity |  | stable |  |
| Overall task success rate |  |  |  |

## 8. Findings

- Finding 1:
  `collision_monitor` stage1 不是当前最主要 blocker。它会放大已有的 localization 冷启动不稳定问题，但不是根因。
- Finding 2:
  当前保存地图与 Gazebo 世界存在明显朝向差异。原始地图相对 Gazebo 约有 90 度旋转现象，导致 initial pose 按地图方向设置时，AMCL 往往需要通过机器人运动后再逐步修正。
- Finding 3:
  候选对齐地图让方向现象有改善，但冷启动后仍需要多次修正 initial pose，说明当前更核心的问题是 `map -> odom` 初始收敛一致性，而不是 stop polygon 本身。

## 9. Defects And Triage

| Defect ID | Severity | Symptom | Trigger Condition | Suspected Root Cause | Status |
| --- | --- | --- | --- | --- | --- |
| BUG-001 | Major | 冷启动后 LaserScan 与地图不能一次对齐，通常需要 2 到 3 次修正或多次短 goal 后才稳定 | 使用保存地图启动 Nav2 localization，设置 initial pose 后立即发 goal | 保存地图与 Gazebo 世界朝向不一致，且当前 AMCL 在对称货架环境中的冷启动收敛仍不稳定 | Open |
| BUG-002 | Medium | 开启 `collision_monitor stage1` 后，误停现象更容易出现 | localization 尚未稳定时直接启用 stage1 stop polygon | `collision_monitor` 放大了底层 localization / map alignment 问题，不建议在当前阶段继续单独调 stop polygon | Deferred |

## 10. Root Cause Notes

- 现象是什么：
  冷启动后 LaserScan 与 Map 初始朝向不稳定，需要 2 到 3 次 `2D Pose Estimate` 或短 goal 后才逐步对齐。
- 如何复现：
  1. 启动 `navigation.launch.py`
  2. 使用保存地图做 localization
  3. 在 RViz 中设置 initial pose
  4. 观察 LaserScan、Map 与 costmap 的初始对齐情况
- 是否只有开启 stage1 参数才出现：
  不是。stage1 参数会让问题更明显，但底层 localization 冷启动一致性问题在稳定基线下也存在。
- 更像是误拦车、TF 问题、AMCL 问题还是 controller 问题：
  当前更像是保存地图朝向与 Gazebo 世界不一致叠加 AMCL 冷启动收敛不稳定，优先归类为 localization / map alignment 问题。
- 下一步更适合改什么：
  `initial pose` 使用方式
  map alignment 候选方案
  AMCL 冷启动收敛验证
  revert to baseline for demos

## 11. Conclusion

- Normal corridor navigation:
  `Needs Investigation`
- Forward stop behavior:
  `Needs Investigation`
- Overall Result:
  `Needs Investigation`
- Confidence Level:
  `medium`
- Main Risks:
  当前如果继续推进 `collision_monitor` 或 runtime task flow，容易把 localization 冷启动不稳定误判成安全层或任务层问题。
- Recommended Next Step:
  暂停把 `collision_monitor stage1` 当成主线验证项，先把“保存地图启动后一次 initial pose 是否能稳定对齐”收成单独 blocker。

## 12. Portfolio-Friendly Summary

- 本次测试验证了什么：
  验证了当前 V2 导航基线上，轻量 `collision_monitor stage1` 候选参数是否适合直接进入仿真验证。
- 关键指标和通过标准是什么：
  重点看正常短 goal 是否仍能起步、前向 stop 是否可触发，以及冷启动后的 initial pose 是否能快速稳定收敛。
- 发现了哪些问题：
  真正阻塞项不是 stop polygon，而是保存地图与 Gazebo 世界朝向差异叠加 localization 冷启动不稳定。
- 采取了什么排查动作：
  试过缩小前向 stop polygon、增加候选对齐地图、关闭 AMCL 上次 pose 记忆，并分别观察对初始对齐和 costmap 的影响。
- 下一步准备怎么收敛：
  把 `collision_monitor stage1` 降级为实验候选项，优先单独解决 localization / map alignment 的冷启动一致性问题。

# Scenario: Restart And Relocalization Regression

这个场景用于验证系统是否具备“重复启动后仍可重新定位并继续导航”的基本稳定性。

相比只跑一次 goal，这个场景更接近新兴机器人公司常见的验证思路，因为他们通常更关心：

- 系统是否可重复启动
- localization 是否稳定可恢复
- 同一条链路在多次运行后是否表现一致

## 场景目标

- 验证 `navigation.launch.py` 在重启后是否仍能恢复到可导航状态
- 验证 AMCL / localization 是否能在重新设置 initial pose 后恢复
- 验证同一短距离 goal 在重复启动后仍可完成

## 适用范围

- 当前主线：V2 Nav2 导航与路径执行
- 主入口：`launch/navigation.launch.py`
- 配套脚本：`scripts/run_navigation.sh`
- 参考基础场景：`test/scenarios/short_goal_navigation_smoke.md`

## 前置条件

- 已至少成功执行过一次短距离导航 smoke test
- 当前地图 `maps/warehouse.yaml` 可用
- 当前参数 `config/nav2_params.yaml` 不做临时改动
- 每轮测试使用同一类起点区域和同一类短距离目标

## 执行步骤

1. 启动 `navigation.launch.py`
2. 确认 lifecycle nodes 为 `active`
3. 设置 initial pose
4. 执行一次短距离 goal，并记录结果
5. 停止当前导航进程或执行脚本中的清理流程
6. 重新启动 `navigation.launch.py`
7. 再次确认 `/map`、`/scan_filtered`、`map -> odom -> base_link`
8. 重新设置 initial pose
9. 执行同类短距离 goal，并记录结果
10. 至少重复 2 到 3 轮

## 建议记录的指标

- `restart_count`
  重启轮次
- `time_to_active`
  启动到关键 lifecycle nodes 进入 `active` 的时间
- `time_to_map_odom`
  启动到 `map -> odom` 可用的时间
- `goal_success_rate`
  多轮短距离 goal 的成功率
- `behavior_consistency`
  多轮运行时是否出现明显行为漂移

## 通过标准

- 每轮重启后关键 lifecycle nodes 都能进入 `active`
- 每轮都能重新设置 initial pose
- 每轮都能恢复 `map -> odom -> base_link`
- 至少 2 轮连续短距离 goal 成功
- 不需要临时改参数或手动修复节点状态

## 推荐输出结论

- `Pass`
  系统在重复重启后仍能恢复 localization 和短距离导航能力
- `Needs Investigation`
  系统可恢复，但重启后首次定位慢、goal 表现不稳定、偶发 recovery
- `Fail`
  重启后无法恢复 localization，或无法稳定复现短距离导航

## 结果记录模板

| Restart ID | Time to Active | Time to `map -> odom` | Goal Result | Completion Time | Notes |
| --- | --- | --- | --- | --- | --- |
| 001 |  |  |  |  |  |
| 002 |  |  |  |  |  |

## 常见失败归因方向

- 重启后 AMCL 不工作
  优先检查 initial pose 是否正确设置、scan 输入是否正常
- lifecycle nodes 未进入 `active`
  优先检查 bringup、参数文件和 node 启动日志
- 第二轮以后导航明显变差
  优先检查环境状态污染、旧进程未清理、TF 或 map 状态不一致

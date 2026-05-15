# Scenario Tests

这个目录用于放面向场景的端到端测试，重点验证“在一个具体业务场景里，系统能否稳定完成目标”。

当前已经补入三份更适合项目展示和求职表达的场景测试 spec：

- `short_goal_navigation_smoke.md`
  用于验证一次 1 到 2 米短距离导航是否成功，适合作为最小导航闭环 smoke test。
- `restart_relocalization_regression.md`
  用于验证重复启动后 localization 和短距离导航是否还能稳定恢复。
- `mock_wms_multi_task_regression.md`
  用于验证轻量 mock WMS 是否能顺序驱动多 task / 多 step 队列，并输出结构化报告。

当前主线运行时验证已经补成三份场景 spec：

- `headless_nav2_ready_integration.md`
  用于验证 fresh session 下 headless Nav2 是否能稳定进入 ready gate。
- `fixed_task_points_success_matrix_regression.md`
  用于验证 `station_a`、`station_b`、`shelf_1`、`shelf_2` 的固定任务点成功矩阵。
- `mock_wms_http_executor_end_to_end.md`
  用于验证 HTTP API -> executor -> Nav2 -> HTTP 状态回写的最小端到端闭环。

后续适合放入：

- 1 到 2 米短距离导航 smoke test
- 狭窄货架通道导航回归
- 重启导航后重新设置 initial pose 的重复验证
- 固定起点和目标点的多次重复成功率统计
- mock WMS 驱动的多任务回归
- 场景级 metrics 采集脚本或自动判定工具

这类测试比功能测试更接近项目展示、验收和真实机器人验证。

# Integration Tests

这个目录预留给链路级测试，重点验证多个组件连起来之后是否还能协同工作。

当前已经补入第一个 integration test：

- `test_navigation_pipeline_contract.py`
  用静态契约方式检查 V2 主线里 `simulation.launch.py -> navigation.launch.py -> nav2_params.yaml -> maps/warehouse.yaml` 的链路配置是否一致。
  这类测试不启动 Gazebo，但能先挡住跨文件改动导致的链路断裂。

后续适合放入：

- `/scan -> /scan_filtered` 链路检查
- `odom -> base_link`、`map -> odom -> base_link` TF 检查
- Nav2 lifecycle nodes 是否进入 `active`
- Gazebo、bridge、laser_filters、Nav2 之间的 topic 连通性验证

这类测试通常更适合配合 `launch_testing`、仿真启动脚本或受控 bag 回放来做。

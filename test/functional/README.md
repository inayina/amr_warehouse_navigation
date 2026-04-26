# Functional Tests

这个目录放单个入口或单个功能的 smoke test，例如：

- launch 文件是否还能生成 `LaunchDescription`
- 某个节点是否还能被正常导入或启动
- 启动参数拼接是否仍然有效

这类测试主要用于防止低级回归，例如路径改错、参数名改错、启动入口断裂。

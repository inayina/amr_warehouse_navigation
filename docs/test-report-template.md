# Robotics Test Report Template

这份模板用于把一次机器人验证结果整理成更像公司内部测试报告或面试展示材料的形式。

如果你更想投新兴机器人公司，这类材料很有价值，因为它能直接体现：

- 你会定义测试目标和范围
- 你会记录指标和证据
- 你会做缺陷归因和下一步建议

## 1. Basic Info

- Test Title:
- Date:
- Tester:
- Branch / Commit:
- Package Version:
- Environment:
- ROS / Simulator Version:
- Test Type:
  `data` / `functional` / `integration` / `scenario`

## 2. Test Objective

- 本次测试要验证什么
- 为什么当前阶段要做这个测试
- 它覆盖的是哪条系统主链

## 3. Scope

- In Scope:
- Out of Scope:
- Related Files:
- Related Nodes / Topics / TF:

## 4. Setup

- Launch Command:
- Parameter File:
- Map File:
- World / Scene:
- Initial Pose Method:
- Goal Setting Method:
- Evidence Collection:
  截图 / 录屏 / rosbag / terminal log / metrics table

## 5. Scenario Matrix

| Scenario ID | Scenario Name | Result | Evidence | Defect ID | Notes |
| --- | --- | --- | --- | --- | --- |
| S-001 |  |  |  |  |  |

## 6. Key Metrics

| Metric | Value | Expected | Notes |
| --- | --- | --- | --- |
| Time to first `/cmd_vel` |  |  |  |
| Goal completion time |  |  |  |
| Recovery count |  |  |  |
| Success rate |  |  |  |
| TF continuity |  |  |  |
| Lifecycle state |  |  |  |

## 7. Findings

- Finding 1:
- Finding 2:
- Finding 3:

## 8. Defects And Triage

| Defect ID | Severity | Symptom | Trigger Condition | Suspected Root Cause | Status |
| --- | --- | --- | --- | --- | --- |
| BUG-001 |  |  |  |  |  |

## 9. Root Cause Notes

- 现象是什么
- 如何复现
- 排查了哪些链路
- 最可能的根因是什么
- 是否已经验证修复

## 10. Conclusion

- Overall Result:
  `Pass` / `Needs Investigation` / `Fail`
- Confidence Level:
  `low` / `medium` / `high`
- Main Risks:
- Recommended Next Step:

## 11. Portfolio-Friendly Summary

这一段建议专门留给你自己后续写简历或面试复盘时复用。

- 这次测试验证了什么
- 你设计了哪些指标和通过标准
- 你发现了什么问题，如何定位
- 你推动了哪些修复或改进

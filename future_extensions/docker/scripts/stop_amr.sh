#!/bin/bash
echo "🛑 正在停止仿真并清理容器..."
cd ~/Amr_warehouse_sim && docker compose down
echo "✅ 系统已安全关闭。"

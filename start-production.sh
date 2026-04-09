#!/bin/bash
# 资产配置看板 - 生产模式启动脚本
# 用法: ./start-production.sh

echo "🚀 启动资产配置看板 (生产模式)"
echo "================================"

# 停止旧进程
echo "停止旧进程..."
pkill -f "python main.py" 2>/dev/null
pkill -f "cloudflared tunnel" 2>/dev/null
sleep 2

# 启动后端
echo "启动后端 (端口 8000)..."
cd ~/asset-allocation-dashboard/backend
source venv/bin/activate
nohup python main.py > /tmp/backend.log 2>&1 &
BACKEND_PID=$!

# 等待后端启动和预热
echo "等待后端预热缓存 (约 30 秒)..."
sleep 5

# 检查后端是否启动成功
if lsof -i :8000 | grep -q LISTEN; then
    echo "✅ 后端已启动 (PID: $BACKEND_PID)"
else
    echo "❌ 后端启动失败，查看日志: tail -f /tmp/backend.log"
    exit 1
fi

# 启动隧道
echo "启动 Cloudflare 隧道..."
nohup cloudflared tunnel run dashboard > /tmp/tunnel.log 2>&1 &
TUNNEL_PID=$!
sleep 5

# 检查隧道是否启动成功
if pgrep -f "cloudflared tunnel" > /dev/null; then
    echo "✅ 隧道已启动 (PID: $TUNNEL_PID)"
else
    echo "❌ 隧道启动失败，查看日志: tail -f /tmp/tunnel.log"
    exit 1
fi

echo ""
echo "================================"
echo "🎉 启动完成！"
echo ""
echo "访问地址:"
echo "  本地: http://localhost:8000"
echo "  外网: https://dashboard.cgfund.cloud"
echo ""
echo "日志文件:"
echo "  后端: tail -f /tmp/backend.log"
echo "  隧道: tail -f /tmp/tunnel.log"
echo ""
echo "停止服务: pkill -f 'python main.py'; pkill -f cloudflared"

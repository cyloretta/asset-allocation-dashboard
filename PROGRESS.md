# 资产配置看板 - 开发进度

**最后更新**: 2026-04-06

## 项目概述
AI 驱动的动态资产配置策略看板，基于宏观分析自动生成投资组合建议。

## 技术栈
- **后端**: FastAPI + Python (多数据源架构, FRED API, Claude/DeepSeek API, SQLite, APScheduler)
  - 数据源: Stooq (主), CoinGecko, Binance (Yahoo 被墙已禁用)
- **前端**: React 18 + TypeScript + Vite + Tailwind CSS + Recharts + SWR
- **外网访问**: Cloudflare Tunnel (`https://dashboard.cgfund.cloud`)

## 当前状态: 外网访问已配置 ✅ 生产模式部署 ✅

---

## 最新更新 (2026-04-03)

### 1. 多数据源架构 ✅
新增 `data/data_providers.py` - 实现数据源抽象和自动故障转移:

**数据源优先级:**
| 资产类型 | 主数据源 | 备份数据源 | 最终后备 |
|---------|---------|-----------|---------|
| 股票/ETF | Yahoo Finance | Stooq | 模拟数据 |
| 加密货币 | CoinGecko | Binance | 模拟数据 |

**核心特性:**
- **自动故障转移**: 主数据源失败时自动切换到备份
- **内存缓存**: 价格缓存 5 分钟，历史数据缓存 1 小时
- **重试机制**: 带指数退避的自动重试 (最多 3 次)
- **健康检测**: 实时监控各数据源状态

**新增 API:**
- `GET /api/system/data-sources` - 查看数据源健康状态
- `POST /api/system/clear-cache` - 清空数据缓存

### 2. 移动端响应式优化 ✅
- **Header 重构**: 移动端汉堡菜单，桌面端完整控制栏
- **MarketOverview**: 优化卡片尺寸和网格布局 (2/3/4/5 列自适应)
- **触摸友好**: 添加 `active:scale` 触摸反馈效果
- **字体缩放**: 移动端更小的字体尺寸

### 2. Toast 通知系统 ✅
新增 `components/Toast.tsx`:
- 全局 Toast Provider + useToast Hook
- 四种类型: `success` / `error` / `warning` / `info`
- Cyber 主题样式 (发光边框、霓虹配色)
- 自动消失 (4秒) + 手动关闭

### 3. 策略导出功能 ✅
- 配置方案区域新增「导出」按钮
- 使用 `html2canvas` 截图并保存为 PNG
- 文件名: `asset-allocation-YYYY-MM-DD.png`

### 4. 操作反馈增强 ✅
- 「全量同步」操作增加 Toast 提示
- 「AI 分析」运行状态通知
- 「策略优化」完成/失败提示

### 5. 下拉刷新组件 ✅
新增 `components/PullToRefresh.tsx`:
- 触摸下拉刷新 (移动端)
- 阈值判断 + 回弹动画
- 可选集成到 Dashboard

---

## 更新 (2026-03-25)

### 1. Cyber Fintech 主题实现 ✅
全面升级 UI 为赛博科技风格：
- **配色方案**: 深色背景 (#0a0a0f) + 霓虹色调
  - 主色: `#00f5ff` (青色) / `#00d4aa` (绿色)
  - 警示色: `#ff6b6b` (红) / `#ffd93d` (黄) / `#4ade80` (绿)
- **视觉效果**: 发光边框、悬浮光晕、渐变背景
- **字体**: JetBrains Mono (数据显示)

#### 已更新组件
| 组件 | 更新内容 |
|------|---------|
| `MacroAnalysis.tsx` | 霓虹状态标签、发光进度条、暗色卡片 |
| `AIAnalysisPanel.tsx` | 渐变卡片、霓虹徽章、发光效果 |
| `StrategyPanel.tsx` | 发光指标卡片、赛博风格按钮 |
| `AssetAllocation.tsx` | 霓虹表格样式、发光行悬浮效果 |
| `NewsPanel.tsx` | 暗色新闻卡片、悬浮光晕 |
| `Dashboard.tsx` | 整体布局赛博化 |
| `index.css` | 全局 Cyber 样式变量 |

### 2. 中文界面优化 ✅
- 所有 UI 文字已汉化
- 保留专有术语英文 (SPY, QQQ, Sharpe Ratio, VIX 等)
- AI 状态显示优化:
  - `检查中...` (加载)
  - `可用 · X分钟前` / `可用 · X小时前` (有效)
  - `请先运行 AI 分析` (无效/超时)
- "配置建议" 已更名为 "AI 建议"

### 3. 树状图替代饼图 ✅
- 新增 `Charts/LazyTreemap.tsx` 组件
- 面积比例直观展示资产权重 (总计 100%)
- 支持发光效果和响应式标签显示
- 懒加载优化性能

### 4. 桌面快捷方式 ✅
- 路径: `/Users/apple/Desktop/资产配置看板.command`
- 双击即可启动开发服务器并打开浏览器
- 显示本机和局域网访问地址

### 5. 局域网访问 ✅
- `vite.config.ts` 已配置 `host: true`
- 同一 WiFi 下手机可通过 `http://<本机IP>:5173` 访问
- 快捷方式启动时会显示局域网地址

---

## 后端 API (100%)

| 端点 | 功能 |
|------|------|
| `GET /api/market/prices` | 实时行情 (SPY, QQQ, GLD, BTC-USD, TLT) |
| `GET /api/market/history/{ticker}` | 历史数据 |
| `GET /api/market/technical/{ticker}` | 技术分析 |
| `GET /api/macro/indicators` | 宏观经济指标 |
| `GET /api/macro/regime` | 市场环境分析 (VIX, 收益率曲线, Fed 政策) |
| `GET /api/analysis/latest` | 最新 AI 分析 |
| `POST /api/analysis/run` | 触发新分析 |
| `GET /api/analysis/status` | AI 分析状态 (含超时检测) |
| `GET /api/strategy/current` | 当前配置策略 |
| `POST /api/strategy/optimize` | 组合优化 (Max Sharpe, Min Vol, Risk Parity) |
| `GET /api/strategy/efficient-frontier` | 有效前沿 |
| `POST /api/backtest/run` | 历史回测 |
| `POST /api/backtest/monte-carlo` | 蒙特卡洛模拟 |
| `GET /api/news/recent` | 新闻聚合 |
| `POST /api/system/update` | 手动触发更新 |

**定时任务**: 每日 6:00 AM 自动更新

---

## 前端组件结构

```
frontend/src/
├── components/
│   ├── Dashboard.tsx        # 主仪表盘布局 (Cyber 风格)
│   ├── MarketOverview.tsx   # 市场行情卡片
│   ├── MacroAnalysis.tsx    # 宏观环境面板 (霓虹状态)
│   ├── AssetAllocation.tsx  # 资产配置 (树状图)
│   ├── StrategyPanel.tsx    # 策略指标 + 回测
│   ├── AIAnalysisPanel.tsx  # AI 分析面板
│   ├── NewsPanel.tsx        # 新闻列表
│   └── Charts/
│       ├── index.tsx        # 图表导出 (懒加载封装)
│       ├── BacktestChart.tsx
│       ├── AllocationChart.tsx
│       ├── PriceChart.tsx
│       ├── LazyTreemap.tsx  # 资产配置树状图
│       └── LazyHistoryChart.tsx
├── hooks/
│   └── useAPI.ts            # SWR 数据获取 hooks
├── types/
│   └── index.ts             # TypeScript 类型定义
├── App.tsx
├── main.tsx
└── index.css                # Cyber 全局样式
```

---

## 启动方式

### 方式一: 桌面快捷方式
双击 `/Users/apple/Desktop/资产配置看板.command`

### 方式二: 命令行
```bash
cd ~/asset-allocation-dashboard

# 首次设置
./scripts/start.sh setup

# 启动全部服务
./scripts/start.sh

# 或分别启动
./scripts/start.sh backend   # 后端 http://localhost:8000
./scripts/start.sh frontend  # 前端 http://localhost:5173
```

### 方式三: 手动启动
```bash
# 后端
cd backend && source venv/bin/activate && python main.py

# 前端 (新终端)
cd frontend && npm run dev
```

---

## 访问地址

| 环境 | 地址 |
|------|------|
| 本机 | http://localhost:5173 |
| 局域网 | http://<本机IP>:5173 |
| 后端 API 文档 | http://localhost:8000/docs |

---

## 使用说明

1. 打开 http://localhost:5173
2. 点击右上角「全量同步」按钮获取最新数据
3. 在「AI 分析」区域点击「运行」获取 AI 洞察 (需配置 API Key)
4. 在「策略优化」区域选择优化方法，点击「优化」生成配置
5. 点击「回测」查看历史表现
6. 查看「配置方案」中的树状图了解资产权重分布

---

## 配置 API Keys

编辑 `backend/.env`:
```env
ANTHROPIC_API_KEY=sk-...  # Claude AI 分析 (必需)
FRED_API_KEY=...          # 宏观数据 (可选，有 mock 后备)
```

---

## 已解决的问题

1. **yfinance 数据获取失败** - 添加了 mock 数据后备方案
2. **优化 API 返回错误** - 修复 numpy.bool_ JSON 序列化问题
3. **CSS @apply 指令错误** - 自定义颜色改用直接 CSS 值
4. **AI 状态显示不明确** - 增加时间信息和超时检测

---

## 待开发功能 📋

### 高优先级
1. **外网访问** - ngrok/cloudflare tunnel (需注册账号)
2. ~~**移动端适配** - 响应式布局优化~~ ✅ 已完成

### 中优先级
3. ~~**真实数据接入** - 解决 yfinance/FRED 网络问题~~ ✅ 已实现多数据源架构
4. **数据持久化** - 将策略和分析结果保存到 SQLite
5. **用户配置** - 自定义资产池、风险偏好参数

### 低优先级
6. **历史策略对比** - 展示策略变化趋势图
7. ~~**通知功能** - 重大市场变化时推送提醒~~ ✅ 已实现 Toast 通知
8. ~~**导出报告** - PDF/Excel 导出功能~~ ✅ 已实现 PNG 截图导出

---

## 项目结构

```
asset-allocation-dashboard/
├── backend/
│   ├── main.py              # FastAPI 主程序
│   ├── config.py            # 配置
│   ├── data/                # 数据获取 (多数据源架构)
│   │   ├── data_providers.py # 多数据源调度器 (Stooq/CoinGecko/Binance/Yahoo)
│   │   └── market_data.py    # 市场数据封装
│   ├── analysis/            # AI 分析 + 技术分析
│   ├── strategy/            # 组合优化 + 回测
│   │   └── optimizer.py     # 已修复 JSON 序列化问题
│   ├── scheduler/           # 定时任务
│   ├── database/            # 数据模型
│   └── data.db              # SQLite 数据库
├── frontend/
│   ├── src/
│   │   ├── components/      # React 组件 (Cyber 风格 + 中文)
│   │   ├── hooks/           # SWR API hooks
│   │   └── types/           # TypeScript 类型
│   ├── vite.config.ts       # Vite 配置 (含 LAN 访问)
│   └── tailwind.config.js   # Tailwind 配置 (含 Cyber 主题)
├── scripts/
│   └── start.sh             # 启动脚本
├── README.md                # 项目说明
└── PROGRESS.md              # 开发进度 (本文件)
```

---

## 下次继续开发

发送此文件内容给 Claude，或直接说：
> "继续开发资产配置看板"

### 启动命令
```bash
cd ~/asset-allocation-dashboard
# 后端
cd backend && source venv/bin/activate && python main.py &
# 前端
cd ../frontend && npm run dev
# 打开浏览器 http://localhost:5173
```

### 待完成功能
1. ~~**外网访问**~~ ✅ 已完成 - `https://dashboard.cgfund.cloud`
2. **用户自定义资产池** - 允许用户添加/删除资产
3. **隧道开机自启** - 配置 launchd 让 cloudflared 开机自动运行

---

## Claude 工作备忘 (2026-04-06 续2) ⭐ 最新

### 调试中：策略优化不显示结果

#### 问题表现
用户报告点击"策略优化"后不显示结果

#### 错误追踪
1. `{"detail":"'allocation'"}` - KeyError，optimizer 返回了错误字典
2. `{"detail":"400: Insufficient data: 0 days, minimum 60 required"}` - 没有数据
3. `{"detail":"cannot reindex on an axis with duplicate labels"}` - 索引重复问题

#### 已完成修复
1. **main.py (~L673)**: 添加 optimizer 返回错误的检查
   ```python
   if "error" in result:
       raise HTTPException(status_code=400, detail=result["error"])
   ```

2. **market_data.py**: 重写 `get_historical_returns` 方法
   - 解决不同数据源日期索引不匹配问题
   - 添加索引去重代码：`close_series[~close_series.index.duplicated(keep='last')]`
   - 使用 reindex 对齐不同数据源的日期

#### 下次继续
1. 重启后端: `cd ~/asset-allocation-dashboard/backend && source venv/bin/activate && python main.py &`
2. 测试策略优化:
   ```bash
   curl -s -X POST "http://localhost:8000/api/strategy/optimize" \
     -H "Content-Type: application/json" \
     -H "Cookie: dashboard_auth=f747bdea14a56eb5d819343f5bde1ecb" \
     -d '{"method":"composite","use_ai_adjustments":true}'
   ```
3. 如果 Cookie 过期，先访问页面输入密码获取新 Cookie

---

## Claude 工作备忘 (2026-04-06 续)

### 本次完成：Dashboard 策略历史图表

#### 新增功能
- **StrategyHistory 组件** (`frontend/src/components/StrategyHistory.tsx`)
  - 策略指标趋势图（Sharpe / 预期收益 / 最大回撤）
  - 支持 7D / 30D / 90D 时间范围切换
  - 指标摘要卡片（平均值、趋势方向、范围）
  - 配置变化记录（可折叠显示）
  - 「详细对比」按钮跳转到完整对比模态框

#### Dashboard 集成
- 在"策略优化"/"配置方案"下方新增"策略历史"区块
- 使用已有的 `/api/strategy/history/trend` 和 `/api/strategy/history/allocation-changes` API
- 区域图展示选中指标的历史走势

#### 已知问题
- **Safari 浏览器兼容性问题**：页面黑屏，请使用 Chrome 访问

#### 修改文件
| 文件 | 修改内容 |
|------|---------|
| `frontend/src/components/StrategyHistory.tsx` | 新组件 |
| `frontend/src/components/Dashboard.tsx` | 导入并集成 StrategyHistory |
| `frontend/dist/` | 重新构建 |

---

## Claude 工作备忘 (2026-04-06)

### 完成：外网访问 + 性能优化

#### 1. Cloudflare Tunnel 配置 ✅
- **域名**: `cgfund.cloud` (腾讯云注册，NS 指向 Cloudflare)
- **隧道 ID**: `6360ba76-e666-43a0-b530-701d3cadc0e8`
- **访问地址**:
  - `https://dashboard.cgfund.cloud` - 主站
  - `https://cgfund.cloud` - 根域名
  - `https://api.cgfund.cloud` - API

**隧道配置文件** `~/.cloudflared/config.yml`:
```yaml
tunnel: 6360ba76-e666-43a0-b530-701d3cadc0e8
credentials-file: /Users/apple/.cloudflared/6360ba76-e666-43a0-b530-701d3cadc0e8.json
protocol: http2

ingress:
  - hostname: cgfund.cloud
    service: http://localhost:8000
  - hostname: dashboard.cgfund.cloud
    service: http://localhost:8000
  - hostname: api.cgfund.cloud
    service: http://localhost:8000
  - service: http_status:404
```

#### 2. 生产模式部署 ✅
- 前端已构建 (`npm run build`)，由后端 FastAPI 服务静态文件
- 不再需要运行 `npm run dev`
- **只需启动后端 + 隧道**

#### 3. 性能优化 ✅
**问题**: 首次加载 30+ 秒（Yahoo Finance 和 FRED API 被墙超时）

**解决方案**:
1. 数据源优先级调整 - 跳过 Yahoo，直接用 Stooq
   - 修改: `backend/data/data_providers.py` 第 477 行
2. 增加缓存时间
   - 价格缓存: 5分钟 → 10分钟
   - 历史缓存: 1小时 → 2小时
   - 宏观缓存: 10分钟 → 2小时
3. FRED API 超时: 10秒 → 5秒
4. **启动预热**: 后端启动时自动加载数据到缓存
   - 修改: `backend/main.py` 添加 `warmup_cache()` 函数

**效果**:
- 首次请求（预热后）: 0.04 秒
- 外网访问: ~0.6 秒

#### 4. Vite 配置 ✅
- 添加 `allowedHosts` 允许外网域名访问
- 修改: `frontend/vite.config.ts`

---

### 重要：启动命令（生产模式）

```bash
# 1. 启动后端（会自动预热缓存，等 30 秒左右）
cd ~/asset-allocation-dashboard/backend && source venv/bin/activate && python main.py &

# 2. 启动隧道
cloudflared tunnel run dashboard &

# 3. 检查服务
lsof -i :8000  # 后端
pgrep -f cloudflared  # 隧道
```

### 停止服务
```bash
pkill -f "python main.py"
pkill -f "cloudflared tunnel"
```

### 如果隧道断开 (Error 1033)
```bash
pkill -f cloudflared
cloudflared tunnel run dashboard &
```

---

### 关键文件（本次修改）

| 文件 | 修改内容 |
|------|---------|
| `~/.cloudflared/config.yml` | 隧道路由配置 |
| `~/.cloudflared/cert.pem` | Cloudflare 认证证书 |
| `~/.cloudflared/6360ba76-*.json` | 隧道凭证 |
| `backend/main.py` | 添加静态文件服务 + 启动预热 |
| `backend/data/data_providers.py` | 跳过 Yahoo，增加缓存 |
| `backend/data/macro_data.py` | 增加缓存时间，减少超时 |
| `frontend/vite.config.ts` | 添加 allowedHosts |
| `frontend/dist/` | 生产构建输出 |

---

### 待解决 / 已知问题

1. **隧道稳定性** - 偶尔断开，需要重启 (`cloudflared tunnel run dashboard`)
2. **SSL 证书** - Cloudflare Universal SSL，首次配置可能需要等几分钟
3. **数据延迟** - Stooq/FRED 数据有缓存，非实时

---

### Cloudflare 账号信息（用户需记住）

- **域名**: cgfund.cloud
- **NS 服务器**:
  - tegan.ns.cloudflare.com
  - vasilii.ns.cloudflare.com
- **SSL 模式**: Flexible
- **隧道名称**: dashboard

---

## Claude 工作备忘 (2026-04-03)

### 完成内容
1. **多数据源架构** - `backend/data/data_providers.py`
   - Yahoo → Stooq → Mock 自动故障转移
   - 内存缓存 (价格5分钟, 历史1小时)
   - API: `/api/system/data-sources`, `/api/system/clear-cache`

2. **数据时效性修复**
   - 国债收益率改用 FRED API (DGS10, DGS2, T10Y2Y)
   - 新闻时间添加 UTC 时区 (`+00:00`)
   - 前端宏观指标显示更新日期

### 关键文件
- `backend/data/data_providers.py` - 多数据源调度
- `backend/data/macro_data.py` - 宏观数据 (FRED API)
- `backend/data/news_data.py` - 新闻 RSS (UTC时区)
- `frontend/src/components/MacroAnalysis.tsx` - 宏观面板 (显示日期)

# 资产配置看板 - 开发进度

**最后更新**: 2026-03-25

## 项目概述
AI 驱动的动态资产配置策略看板，基于宏观分析自动生成投资组合建议。

## 技术栈
- **后端**: FastAPI + Python (yfinance, FRED API, Claude API, SQLite, APScheduler)
- **前端**: React 18 + TypeScript + Vite + Tailwind CSS + Recharts + SWR

## 当前状态: 核心功能完成 + UI 美化 ✅

---

## 最新更新 (2026-03-25)

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
2. **移动端适配** - 响应式布局优化

### 中优先级
3. **真实数据接入** - 解决 yfinance/FRED 网络问题
4. **数据持久化** - 将策略和分析结果保存到 SQLite
5. **用户配置** - 自定义资产池、风险偏好参数

### 低优先级
6. **历史策略对比** - 展示策略变化趋势图
7. **通知功能** - 重大市场变化时推送提醒
8. **导出报告** - PDF/Excel 导出功能

---

## 项目结构

```
asset-allocation-dashboard/
├── backend/
│   ├── main.py              # FastAPI 主程序
│   ├── config.py            # 配置
│   ├── data/                # 数据获取 (yfinance, FRED, RSS)
│   │   └── market_data.py   # 含 mock 数据后备
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
> "继续开发资产配置看板，上次完成了 Cyber 主题和中文界面"

或查看具体任务:
> "帮我实现外网访问功能"
> "优化移动端显示效果"

# Asset Allocation Dashboard

AI-powered dynamic asset allocation strategy dashboard with real-time market analysis.

## Features

- **Real-time Market Data**: Live prices for SPY, QQQ, GLD, BTC-USD, TLT
- **Macro Analysis**: Fed policy, yield curve, VIX monitoring
- **AI-Powered Analysis**: Claude AI integration for market insights
- **Portfolio Optimization**: Mean-variance, risk parity strategies
- **Backtesting**: Historical performance simulation
- **Daily Updates**: Scheduled data refresh and strategy updates

## Tech Stack

### Backend
- FastAPI (Python)
- yfinance for market data
- FRED API for macro indicators
- Anthropic Claude API for AI analysis
- SQLite for data persistence
- APScheduler for scheduled tasks

### Frontend
- React + TypeScript
- Vite build tool
- Tailwind CSS
- Recharts for visualizations

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- Claude API key (optional, for AI features)
- FRED API key (optional, for macro data)

### Installation

1. Clone and setup:
```bash
cd ~/asset-allocation-dashboard
chmod +x scripts/start.sh
./scripts/start.sh setup
```

2. Configure API keys:
```bash
cd backend
cp .env.example .env
# Edit .env and add your API keys
```

3. Start services:
```bash
./scripts/start.sh
```

4. Open http://localhost:5173 in your browser

## Project Structure

```
asset-allocation-dashboard/
├── backend/
│   ├── main.py              # FastAPI app
│   ├── config.py            # Settings
│   ├── data/                # Data fetchers
│   ├── analysis/            # AI & technical analysis
│   ├── strategy/            # Portfolio optimization
│   ├── scheduler/           # Scheduled jobs
│   └── database/            # Models & CRUD
├── frontend/
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── hooks/           # API hooks
│   │   └── types/           # TypeScript types
│   └── ...
└── scripts/
    └── start.sh             # Startup script
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/market/prices` | Current asset prices |
| `GET /api/macro/regime` | Market regime analysis |
| `GET /api/analysis/latest` | Latest AI analysis |
| `POST /api/analysis/run` | Trigger new analysis |
| `GET /api/strategy/current` | Current allocation |
| `POST /api/strategy/optimize` | Run optimization |
| `POST /api/backtest/run` | Run backtest |
| `GET /api/news/recent` | Recent market news |

Full API docs at http://localhost:8000/docs

## Configuration

Environment variables (`.env`):

```env
ANTHROPIC_API_KEY=sk-...  # For AI analysis
FRED_API_KEY=...          # For macro data
DAILY_UPDATE_HOUR=6       # Daily update time
```

## License

MIT

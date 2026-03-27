export interface AssetPrice {
  price: number;
  change: number;
  volume: number;
  high: number;
  low: number;
  date: string;
  is_mock?: boolean;
}

export interface MarketData {
  [ticker: string]: AssetPrice;
}

export interface MacroIndicator {
  series_id: string;
  name: string;
  description: string;
  value: number;
  date: string;
  history?: Array<{ date: string; value: number }>;
  is_mock?: boolean;
  signal?: string;
  is_estimate?: boolean;
}

export interface MarketRegime {
  volatility: 'low_volatility' | 'moderate_volatility' | 'high_volatility';
  yield_curve: 'normal' | 'flat' | 'inverted';
  monetary_policy: 'accommodative' | 'neutral' | 'restrictive';
  // 新增状态指标
  credit?: 'normal' | 'elevated' | 'stress';
  liquidity?: 'ample' | 'moderate' | 'tight';
  sentiment?: 'extreme_fear' | 'fear' | 'neutral' | 'greed' | 'extreme_greed';
  inflation?: 'deflation' | 'low_inflation' | 'on_target' | 'above_target' | 'high_inflation';
  // 新增数值指标
  cpi_yoy?: number;
  core_cpi_yoy?: number;
  overall_risk: number;
  recession_probability?: number;
  recommended_action?: 'defensive' | 'cautious' | 'balanced' | 'aggressive';
  indicators: { [key: string]: MacroIndicator };
}

export interface AIAnalysis {
  id?: number;
  date: string;
  type?: string;
  content: string;
  risk_score: number;
  key_factors?: string[][];
  recommendations?: object[];
  geopolitical_risk?: {
    score: number;
    key_risks: string[];
    analysis: string;
  };
  fed_policy?: {
    stance: string;
    rate_outlook: string;
    analysis: string;
  };
  tech_trend?: {
    outlook: string;
    key_factors: string[];
    analysis: string;
  };
  market_sentiment?: {
    level: string;
    score: number;
    short_term_outlook: string;
  };
  allocation_advice?: {
    adjustments: { [key: string]: string };
    reasoning: string;
    risk_level: string;
  };
  overall_risk_score?: number;
  summary?: string;
}

export interface PortfolioAllocation {
  [asset: string]: number;
}

// 方案C: 调仓建议
export interface RebalanceAdviceItem {
  current: number;
  target: number;
  drift: number;
  abs_drift: number;
  action: '调仓' | '维持';
  direction: '↑' | '↓' | '';
}

export interface RebalanceAdvice {
  [asset: string]: RebalanceAdviceItem;
}

export interface PlanCData {
  current_allocation: PortfolioAllocation;
  raw_allocation: PortfolioAllocation;
  rounded_allocation: PortfolioAllocation;
  rebalance_advice: RebalanceAdvice;
  rebalance_count: number;
  threshold: number;
}

export interface PortfolioMetrics {
  expected_return: number;
  expected_volatility: number;
  sharpe_ratio: number;
  max_drawdown: number;
}

// 统一风险上下文
export interface RiskContext {
  composite_risk: number;
  risk_level: 'low' | 'moderate' | 'high' | 'extreme';
  risk_asset_multiplier: number;
  safe_asset_boost: number;
  sources: {
    macro?: number;
    ai?: number;
    correlation?: number;
  };
}

export interface Strategy {
  id?: number;
  date: string;
  allocation: PortfolioAllocation;
  expected_return?: number;
  expected_volatility?: number;
  sharpe_ratio?: number;
  max_drawdown?: number;
  reasoning?: string;
  plan_c?: PlanCData | null;
  risk_context?: RiskContext | null;
}

export interface BacktestResult {
  portfolio_values: number[];
  portfolio_returns: number[];
  dates: string[];
  drawdown: number[];
  metrics: {
    total_return: number;
    annualized_return: number;
    annualized_volatility: number;
    sharpe_ratio: number;
    sortino_ratio: number;
    max_drawdown: number;
    calmar_ratio: number;
    var_95: number;
    cvar_95: number;
    positive_days: number;
  };
  final_value: number;
  total_return: number;
}

export interface NewsItem {
  title: string;
  title_zh?: string;
  source: string;
  url: string;
  published_at: string;
  summary: string;
  relevance_score: number;
}

export interface DashboardSummary {
  market: MarketData;
  macro: MarketRegime;
  strategy: Strategy | null;
  analysis: AIAnalysis | null;
}

export interface TechnicalAnalysis {
  current_price: number;
  sma_20: number | null;
  sma_50: number | null;
  sma_200: number | null;
  rsi: number;
  rsi_signal: string;
  macd: number | null;
  macd_signal: string;
  bb_upper: number | null;
  bb_lower: number | null;
  bb_position: number | null;
  // 新增 ADX 趋势强度指标
  adx?: number;
  adx_direction?: 'up' | 'down';
  trend_strength?: 'weak' | 'moderate' | 'strong' | 'very_strong';
  plus_di?: number | null;
  minus_di?: number | null;
  // ATR 和 ROC
  atr?: number | null;
  atr_pct?: number | null;
  roc?: number | null;
  // 趋势
  short_term_trend: string;
  long_term_trend: string;
  overall_signal: string;
}

// 用户配置
export interface AssetConstraint {
  min: number;
  max: number;
}

export interface UserConfig {
  id: number;
  name: string;
  is_active: boolean;
  asset_pool: string[];
  asset_constraints: { [asset: string]: AssetConstraint } | null;
  max_drawdown: number;
  target_sharpe: number;
  rebalance_threshold: number;
  preferred_method: string;
  use_ai_adjustments: boolean;
  created_at: string;
  updated_at: string | null;
}

// 策略快照
export interface StrategySnapshot {
  id: number;
  created_at: string;
  method: string;
  max_drawdown_limit: number;
  use_ai: boolean;
  allocation?: PortfolioAllocation;
  rounded_allocation?: PortfolioAllocation;
  metrics: PortfolioMetrics;
  market_snapshot?: MarketData;
  macro_snapshot?: MarketRegime;
}

// 历史趋势
export interface TrendDataPoint {
  id: number;
  date: string;
  sharpe: number | null;
  return: number | null;
  volatility: number | null;
  max_drawdown: number | null;
  method: string;
}

export interface MetricsSummary {
  min: number | null;
  max: number | null;
  avg: number | null;
  trend: 'up' | 'down' | 'stable';
}

export interface TrendResponse {
  data: TrendDataPoint[];
  metrics_summary: {
    sharpe: MetricsSummary;
    max_drawdown: MetricsSummary;
    return: MetricsSummary;
  } | null;
}

// 配置变化
export interface AllocationChange {
  date: string;
  method: string;
  changes: {
    [asset: string]: {
      from: number;
      to: number;
      change: number;
    };
  };
}

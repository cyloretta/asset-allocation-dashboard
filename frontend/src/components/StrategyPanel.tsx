import { useState, useEffect, forwardRef, useImperativeHandle, memo, useMemo, useCallback } from 'react';
import { Play, Settings, ChevronDown, ChevronUp, Info, AlertTriangle, Clock } from 'lucide-react';
import { useStrategy, useBacktest, useAIAnalysisStatus } from '../hooks/useApi';
import type { Strategy, PlanCData } from '../types';
import { BacktestChart, preloadCharts } from './Charts';

// Static JSX hoisting with cyber colors
const InfoIcon = <Info className="w-4 h-4 text-neon-cyan" />;
const ChevronUpCyan = <ChevronUp className="w-4 h-4 text-neon-cyan" />;
const ChevronDownCyan = <ChevronDown className="w-4 h-4 text-neon-cyan" />;
const ChevronUpGray = <ChevronUp className="w-4 h-4 text-gray-500" />;
const ChevronDownGray = <ChevronDown className="w-4 h-4 text-gray-500" />;
const ClockSmall = <Clock className="w-3 h-3" />;
const AlertTriangleSmall = <AlertTriangle className="w-3 h-3" />;

export interface StrategyPanelRef {
  optimize: () => Promise<PlanCData | null>;
  isOptimizing: boolean;
}

interface ReasoningData {
  method_name?: string;
  method?: string;
  ai_adjustments?: Record<string, any>;
  correlation_regime?: {
    is_crisis: boolean;
    regime: string;
    risk_adjustment: number;
  };
  out_of_sample?: {
    return: number;
    sharpe: number;
    volatility: number;
    max_drawdown: number;
  };
  train_days?: number;
  test_days?: number;
}

const StrategyReasoning = memo(function StrategyReasoning({ reasoning }: { reasoning: string }) {
  const [expanded, setExpanded] = useState(true);

  const data = useMemo<ReasoningData | null>(() => {
    try {
      return JSON.parse(reasoning);
    } catch {
      return null;
    }
  }, [reasoning]);

  const toggleExpanded = useCallback(() => setExpanded(prev => !prev), []);

  if (!data) {
    return (
      <div className="border-t border-white/5 pt-4">
        <h4 className="text-[10px] font-mono text-gray-500 tracking-widest mb-2">策略理由</h4>
        <p className="text-sm text-gray-400">{reasoning}</p>
      </div>
    );
  }

  const hasAIAdjustments = data.ai_adjustments && Object.keys(data.ai_adjustments).length > 0;

  return (
    <div className="border-t border-white/5 pt-4">
      <div
        className="flex items-center justify-between cursor-pointer mb-3"
        onClick={toggleExpanded}
      >
        <h4 className="text-[10px] font-mono text-gray-500 tracking-widest">策略理由</h4>
        {expanded ? ChevronUpGray : ChevronDownGray}
      </div>

      {expanded ? (
        <div className="space-y-3">
          {/* Optimization Method */}
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-mono text-gray-500">方法:</span>
            <span className="text-[10px] font-mono font-medium px-2 py-0.5 bg-neon-blue/10 text-neon-blue rounded border border-neon-blue/30">
              {data.method_name || data.method}
            </span>
          </div>

          {/* AI Adjustments Status */}
          {hasAIAdjustments ? (
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-mono text-gray-500">AI 信号:</span>
              <span className="text-[10px] font-mono font-medium px-2 py-0.5 bg-neon-green/10 text-neon-green rounded border border-neon-green/30">
                已应用
              </span>
              <span className="text-[10px] font-mono text-gray-600">
                (详见 AI 分析面板)
              </span>
            </div>
          ) : null}

          {/* Correlation Regime */}
          {data.correlation_regime ? (
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-mono text-gray-500">市场状态:</span>
              <span className={`text-[10px] font-mono font-medium px-2 py-0.5 rounded border ${
                data.correlation_regime.is_crisis
                  ? 'bg-status-loss/10 text-status-loss border-status-loss/30'
                  : data.correlation_regime.regime === 'elevated'
                    ? 'bg-status-warning/10 text-status-warning border-status-warning/30'
                    : 'bg-neon-green/10 text-neon-green border-neon-green/30'
              }`}>
                {data.correlation_regime.regime === 'crisis' ? '危机模式' :
                 data.correlation_regime.regime === 'elevated' ? '相关性升高' : '正常'}
              </span>
              {data.correlation_regime.risk_adjustment < 1 ? (
                <span className="text-[10px] font-mono text-status-warning flex items-center gap-1">
                  {AlertTriangleSmall}
                  风险调整 {(data.correlation_regime.risk_adjustment * 100).toFixed(0)}%
                </span>
              ) : null}
            </div>
          ) : null}

          {/* Out-of-Sample Validation */}
          {data.out_of_sample ? (
            <div className="rounded-lg p-3 border border-white/5"
                 style={{ background: 'rgba(255, 255, 255, 0.02)' }}>
              <div className="text-[10px] font-mono text-gray-500 tracking-wider mb-2">
                样本外验证 ({data.test_days}天):
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                <div className="flex justify-between">
                  <span className="text-gray-500">收益率</span>
                  <span className={data.out_of_sample.return >= 0 ? 'text-neon-green' : 'text-status-loss'}
                        style={{ textShadow: data.out_of_sample.return >= 0 ? '0 0 8px rgba(0, 255, 136, 0.4)' : '0 0 8px rgba(255, 51, 102, 0.4)' }}>
                    {(data.out_of_sample.return * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Sharpe</span>
                  <span className={data.out_of_sample.sharpe >= 1 ? 'text-neon-green' : 'text-gray-300'}>
                    {data.out_of_sample.sharpe.toFixed(2)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">波动率</span>
                  <span className="text-gray-300">{(data.out_of_sample.volatility * 100).toFixed(1)}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">最大回撤</span>
                  <span className="text-status-loss">
                    {(data.out_of_sample.max_drawdown * 100).toFixed(1)}%
                  </span>
                </div>
              </div>
            </div>
          ) : null}

          {/* Training Data Info */}
          {data.train_days ? (
            <div className="text-[10px] font-mono text-gray-600">
              训练: {data.train_days}天 | 测试: {data.test_days || 0}天
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
});

interface MetricCardProps {
  label: string;
  value: number | undefined;
  formatter: (v: number) => string;
  colorFn?: (v: number) => string;
  glowFn?: (v: number) => string;
}

const MetricCard = memo(function MetricCard({ label, value, formatter, colorFn, glowFn }: MetricCardProps) {
  const displayValue = value !== undefined ? formatter(value) : 'N/A';
  const colorClass = value !== undefined && colorFn ? colorFn(value) : 'text-gray-100';
  const glow = value !== undefined && glowFn ? glowFn(value) : 'none';

  return (
    <div className="rounded-lg p-3 border border-white/5"
         style={{ background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.02) 0%, transparent 100%)' }}>
      <div className="text-[10px] font-mono text-gray-500 tracking-wider">{label}</div>
      <div className={`text-xl font-mono font-bold ${colorClass}`}
           style={{ textShadow: glow }}>
        {displayValue}
      </div>
    </div>
  );
});

const getSharpeColor = (v: number): string =>
  v >= 1 ? 'text-neon-green' : v >= 0.5 ? 'text-status-warning' : 'text-status-loss';

const getSharpeGlow = (v: number): string =>
  v >= 1 ? '0 0 10px rgba(0, 255, 136, 0.4)' : v >= 0.5 ? '0 0 10px rgba(255, 170, 0, 0.4)' : '0 0 10px rgba(255, 51, 102, 0.4)';

const getDrawdownColor = (v: number): string =>
  v <= 0.2 ? 'text-neon-green' : v <= 0.3 ? 'text-status-warning' : 'text-status-loss';

const getDrawdownGlow = (v: number): string =>
  v <= 0.2 ? '0 0 10px rgba(0, 255, 136, 0.4)' : v <= 0.3 ? '0 0 10px rgba(255, 170, 0, 0.4)' : '0 0 10px rgba(255, 51, 102, 0.4)';

const formatPercent = (v: number): string => `${(v * 100).toFixed(1)}%`;
const formatSharpe = (v: number): string => v.toFixed(2);

interface Props {
  strategy: Strategy | null | undefined;
  onOptimized?: () => void;
  showInternalButton?: boolean;
}

const StrategyPanel = forwardRef<StrategyPanelRef, Props>(({ strategy: initialStrategy, onOptimized, showInternalButton = false }, ref) => {
  const { optimize, optimizing } = useStrategy();
  const { data: backtestData, runBacktest, loading: backtesting } = useBacktest();
  const { status: aiStatus, loading: aiStatusLoading, refresh: refreshAIStatus } = useAIAnalysisStatus();
  const [strategy, setStrategy] = useState(initialStrategy);
  const [showBacktest, setShowBacktest] = useState(false);
  const [showMethodInfo, setShowMethodInfo] = useState(false);
  const [hasOptimized, setHasOptimized] = useState(false);
  const [maxDrawdown, setMaxDrawdown] = useState(25);

  const hasValidAI = useMemo(() => aiStatus?.has_valid_cache ?? false, [aiStatus?.has_valid_cache]);
  const displayStrategy = useMemo(() => strategy || initialStrategy, [strategy, initialStrategy]);

  useEffect(() => {
    if (!hasOptimized) {
      setStrategy(initialStrategy);
    }
  }, [initialStrategy, hasOptimized]);

  const toggleMethodInfo = useCallback(() => setShowMethodInfo(prev => !prev), []);

  const handleDrawdownChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setMaxDrawdown(Number(e.target.value));
  }, []);

  const handleOptimize = useCallback(async (): Promise<PlanCData | null> => {
    if (!hasValidAI) {
      console.error('No valid AI analysis available');
      return null;
    }

    try {
      const result = await optimize('composite', true, maxDrawdown / 100);
      const newStrategy = {
        date: new Date().toISOString(),
        allocation: result.allocation,
        ...result.metrics,
      };
      setStrategy(newStrategy);
      setHasOptimized(true);
      setTimeout(() => {
        onOptimized?.();
      }, 500);
      return result.plan_c || null;
    } catch (err: any) {
      console.error('Optimization failed:', err);
      if (err?.response?.status === 400) {
        refreshAIStatus();
      }
      return null;
    }
  }, [hasValidAI, maxDrawdown, optimize, onOptimized, refreshAIStatus]);

  useImperativeHandle(ref, () => ({
    optimize: handleOptimize,
    isOptimizing: optimizing,
  }), [handleOptimize, optimizing]);

  const handleBacktest = useCallback(async () => {
    if (!displayStrategy?.allocation) return;
    try {
      await runBacktest(displayStrategy.allocation, 'monthly', 100000);
      setShowBacktest(true);
    } catch (err) {
      console.error('Backtest failed:', err);
    }
  }, [displayStrategy?.allocation, runBacktest]);

  const aiStatusText = useMemo(() => {
    if (aiStatusLoading) return '检查中...';
    if (hasValidAI) {
      const age = aiStatus?.age_minutes;
      if (age != null) {
        return age < 60 ? `可用 · ${Math.round(age)}分钟前` : `可用 · ${Math.round(age / 60)}小时前`;
      }
      return 'AI 分析可用';
    }
    return '请先运行 AI 分析';
  }, [aiStatusLoading, hasValidAI, aiStatus?.age_minutes]);

  return (
    <div className="space-y-4">
      {/* Method Info */}
      <div className="rounded-lg p-3 border border-neon-cyan/20"
           style={{ background: 'linear-gradient(135deg, rgba(0, 245, 255, 0.03) 0%, transparent 100%)' }}>
        <div
          className="flex items-center justify-between cursor-pointer"
          onClick={toggleMethodInfo}
        >
          <div className="flex items-center gap-2">
            {InfoIcon}
            <span className="text-xs font-mono text-neon-cyan tracking-wider">综合优化策略</span>
          </div>
          {showMethodInfo ? ChevronUpCyan : ChevronDownCyan}
        </div>
        {showMethodInfo ? (
          <div className="mt-3 text-xs text-gray-400 space-y-1.5 font-mono">
            <p><strong className="text-gray-300">目标:</strong> 在保证最大回撤不超过设定阈值的前提下，最大化 Sharpe Ratio</p>
            <p><strong className="text-gray-300">公式:</strong> <span className="text-neon-cyan">Obj = -Sharpe + Penalty × max(0, MDD - Threshold)²</span></p>
            <p><strong className="text-gray-300">Sharpe:</strong> (预期收益 - 无风险利率) / 波动率</p>
            <p><strong className="text-gray-300">回撤:</strong> MDD ≈ 2.5 × 年化波动率</p>
          </div>
        ) : null}
      </div>

      {/* Max Drawdown Slider */}
      <div className="rounded-lg p-4 border border-white/5"
           style={{ background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.02) 0%, transparent 100%)' }}>
        <div className="flex items-center justify-between mb-3">
          <span className="text-[10px] font-mono text-gray-500 tracking-wider">最大回撤阈值</span>
          <span className="text-sm font-mono font-bold text-neon-orange"
                style={{ textShadow: '0 0 10px rgba(255, 107, 0, 0.5)' }}>
            {maxDrawdown}%
          </span>
        </div>
        <input
          type="range"
          min="10"
          max="50"
          value={maxDrawdown}
          onChange={handleDrawdownChange}
          className="w-full h-1.5 bg-white/10 rounded-lg appearance-none cursor-pointer accent-neon-orange"
        />
        <div className="flex justify-between text-[10px] font-mono text-gray-600 mt-2">
          <span>保守 10%</span>
          <span>激进 50%</span>
        </div>
      </div>

      {/* Optimize Button + AI Status */}
      {showInternalButton ? (
        <div className="flex items-center gap-3">
          <button
            onClick={handleOptimize}
            disabled={optimizing || !hasValidAI}
            className={`flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg font-mono text-sm transition-all ${
              hasValidAI
                ? 'bg-neon-orange/10 text-neon-orange border border-neon-orange/40 hover:border-neon-orange/60 hover:bg-neon-orange/20'
                : 'bg-white/5 text-gray-600 border border-white/10 cursor-not-allowed'
            }`}
            title={!hasValidAI ? 'Run AI Analysis first' : ''}
          >
            <Settings className={`w-4 h-4 ${optimizing ? 'animate-spin' : ''}`} />
            {optimizing ? '优化中...' : '运行优化'}
          </button>

          <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-[10px] font-mono border ${
            hasValidAI
              ? 'bg-neon-green/10 text-neon-green border-neon-green/30'
              : 'bg-status-warning/10 text-status-warning border-status-warning/30'
          }`}>
            {ClockSmall}
            <span>{aiStatusText}</span>
          </div>
        </div>
      ) : null}

      {/* Metrics Display */}
      {displayStrategy ? (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <MetricCard
              label="预期年化收益"
              value={displayStrategy.expected_return}
              formatter={formatPercent}
              colorFn={() => 'text-neon-green'}
              glowFn={() => '0 0 10px rgba(0, 255, 136, 0.4)'}
            />
            <MetricCard
              label="年化波动率"
              value={displayStrategy.expected_volatility}
              formatter={formatPercent}
              colorFn={() => 'text-gray-200'}
            />
            <MetricCard
              label="Sharpe Ratio"
              value={displayStrategy.sharpe_ratio}
              formatter={formatSharpe}
              colorFn={getSharpeColor}
              glowFn={getSharpeGlow}
            />
            <MetricCard
              label="预估最大回撤"
              value={displayStrategy.max_drawdown}
              formatter={formatPercent}
              colorFn={getDrawdownColor}
              glowFn={getDrawdownGlow}
            />
          </div>

          {/* Metrics Legend */}
          <div className="text-[10px] font-mono text-gray-600 p-2 rounded border border-white/5"
               style={{ background: 'rgba(255, 255, 255, 0.02)' }}>
            <span className="text-neon-green">Sharpe ≥1.0 优秀</span>
            <span className="mx-2">|</span>
            <span className="text-status-warning">0.5-1.0 良好</span>
            <span className="mx-2">|</span>
            <span className="text-status-loss">&lt;0.5 一般</span>
          </div>

          {/* Backtest Button */}
          <button
            onClick={handleBacktest}
            onMouseEnter={preloadCharts}
            onFocus={preloadCharts}
            disabled={backtesting || !displayStrategy.allocation}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg font-mono text-sm bg-neon-purple/10 text-neon-purple border border-neon-purple/30 hover:border-neon-purple/50 hover:bg-neon-purple/20 transition-all disabled:opacity-50"
          >
            <Play className={`w-4 h-4 ${backtesting ? 'animate-pulse' : ''}`} />
            {backtesting ? '回测中...' : '运行历史回测'}
          </button>

          {/* Backtest Results */}
          {showBacktest && backtestData ? (
            <div className="border-t border-white/5 pt-4">
              <h4 className="text-[10px] font-mono text-gray-500 tracking-widest mb-3">回测结果 (1年)</h4>
              <div className="h-48">
                <BacktestChart data={backtestData} />
              </div>
              <div className="grid grid-cols-2 gap-2 mt-3 text-sm font-mono">
                <div className="flex justify-between">
                  <span className="text-gray-500">总收益</span>
                  <span className={`font-medium ${backtestData.total_return >= 0 ? 'text-neon-green' : 'text-status-loss'}`}
                        style={{ textShadow: backtestData.total_return >= 0 ? '0 0 8px rgba(0, 255, 136, 0.4)' : '0 0 8px rgba(255, 51, 102, 0.4)' }}>
                    {(backtestData.total_return * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">最终价值</span>
                  <span className="font-medium text-gray-200">${backtestData.final_value.toLocaleString()}</span>
                </div>
              </div>
            </div>
          ) : null}

          {/* Strategy Reasoning */}
          {displayStrategy.reasoning ? (
            <StrategyReasoning reasoning={displayStrategy.reasoning} />
          ) : null}
        </div>
      ) : null}
    </div>
  );
});

StrategyPanel.displayName = 'StrategyPanel';

export default StrategyPanel;

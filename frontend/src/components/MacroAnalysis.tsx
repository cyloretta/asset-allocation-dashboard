import { useState, memo, useMemo } from 'react';
import { ChevronDown, ChevronUp, Info, AlertTriangle, TrendingUp, Activity } from 'lucide-react';
import type { MarketRegime, MacroIndicator } from '../types';

interface Props {
  data: MarketRegime | null | undefined;
}

// Static JSX hoisting
const AlertTriangleIcon = <AlertTriangle className="w-4 h-4" />;
const ActivityIcon = <Activity className="w-4 h-4" />;
const TrendingUpIcon = <TrendingUp className="w-4 h-4" />;

// Cyber theme status labels
const REGIME_LABELS: { [category: string]: { [key: string]: { label: string; color: string } } } = {
  volatility: {
    low_volatility: { label: '低', color: 'bg-neon-green/20 text-neon-green border border-neon-green/30' },
    moderate_volatility: { label: '中等', color: 'bg-status-warning/20 text-status-warning border border-status-warning/30' },
    high_volatility: { label: '高', color: 'bg-status-loss/20 text-status-loss border border-status-loss/30' },
  },
  yield_curve: {
    normal: { label: '正常', color: 'bg-neon-green/20 text-neon-green border border-neon-green/30' },
    flat: { label: '平坦', color: 'bg-status-warning/20 text-status-warning border border-status-warning/30' },
    inverted: { label: '倒挂', color: 'bg-status-loss/20 text-status-loss border border-status-loss/30' },
  },
  monetary_policy: {
    accommodative: { label: '宽松', color: 'bg-neon-green/20 text-neon-green border border-neon-green/30' },
    neutral: { label: '中性', color: 'bg-status-warning/20 text-status-warning border border-status-warning/30' },
    restrictive: { label: '紧缩', color: 'bg-status-loss/20 text-status-loss border border-status-loss/30' },
  },
  credit: {
    normal: { label: '正常', color: 'bg-neon-green/20 text-neon-green border border-neon-green/30' },
    elevated: { label: '升高', color: 'bg-status-warning/20 text-status-warning border border-status-warning/30' },
    stress: { label: '压力', color: 'bg-status-loss/20 text-status-loss border border-status-loss/30' },
  },
  liquidity: {
    ample: { label: '充裕', color: 'bg-neon-green/20 text-neon-green border border-neon-green/30' },
    moderate: { label: '适中', color: 'bg-status-warning/20 text-status-warning border border-status-warning/30' },
    tight: { label: '紧张', color: 'bg-status-loss/20 text-status-loss border border-status-loss/30' },
  },
  sentiment: {
    extreme_fear: { label: '极度恐惧', color: 'bg-status-loss/20 text-status-loss border border-status-loss/30' },
    fear: { label: '恐惧', color: 'bg-neon-orange/20 text-neon-orange border border-neon-orange/30' },
    neutral: { label: '中性', color: 'bg-gray-500/20 text-gray-400 border border-gray-500/30' },
    greed: { label: '贪婪', color: 'bg-neon-green/20 text-neon-green border border-neon-green/30' },
    extreme_greed: { label: '极度贪婪', color: 'bg-neon-green/30 text-neon-green border border-neon-green/50' },
  },
  inflation: {
    deflation: { label: '通缩', color: 'bg-neon-blue/20 text-neon-blue border border-neon-blue/30' },
    low_inflation: { label: '低通胀', color: 'bg-neon-green/20 text-neon-green border border-neon-green/30' },
    on_target: { label: '达标', color: 'bg-neon-green/20 text-neon-green border border-neon-green/30' },
    above_target: { label: '偏高', color: 'bg-status-warning/20 text-status-warning border border-status-warning/30' },
    high_inflation: { label: '高通胀', color: 'bg-status-loss/20 text-status-loss border border-status-loss/30' },
  },
};

const ACTION_LABELS: { [key: string]: { label: string; color: string; icon: JSX.Element } } = {
  defensive: { label: '防御', color: 'bg-status-loss/20 text-status-loss border border-status-loss/40', icon: AlertTriangleIcon },
  cautious: { label: '谨慎', color: 'bg-status-warning/20 text-status-warning border border-status-warning/40', icon: ActivityIcon },
  balanced: { label: '均衡', color: 'bg-neon-blue/20 text-neon-blue border border-neon-blue/40', icon: ActivityIcon },
  aggressive: { label: '积极', color: 'bg-neon-green/20 text-neon-green border border-neon-green/40', icon: TrendingUpIcon },
};

const INDICATOR_CATEGORIES: { [key: string]: { name: string; keys: string[] } } = {
  rates: { name: '利率指标', keys: ['US10Y', 'US2Y', 'US3M', 'T10Y2Y', 'FEDFUNDS'] },
  inflation: { name: '通胀指标', keys: ['CPI_YOY', 'CORE_CPI_YOY'] },
  credit: { name: '信用市场', keys: ['CREDIT_SPREAD', 'TED_SPREAD'] },
  volatility: { name: '波动率', keys: ['VIX', 'VIX_PREMIUM'] },
  sentiment: { name: '市场情绪', keys: ['PUT_CALL_RATIO', 'FEAR_GREED'] },
  economic: { name: '经济指标', keys: ['JOBLESS_CLAIMS', 'M2_GROWTH'] },
  fx: { name: '汇率', keys: ['DXY'] },
};

const SIGNAL_COLORS: { [key: string]: string } = {
  normal: 'bg-neon-green/20 text-neon-green',
  high: 'bg-status-loss/20 text-status-loss',
  elevated: 'bg-status-warning/20 text-status-warning',
  low: 'bg-neon-green/20 text-neon-green',
  stress: 'bg-status-loss/20 text-status-loss',
  fear_excessive: 'bg-status-loss/20 text-status-loss',
  complacent: 'bg-status-warning/20 text-status-warning',
  expansion: 'bg-neon-green/20 text-neon-green',
  danger: 'bg-status-loss/20 text-status-loss',
  warning: 'bg-status-warning/20 text-status-warning',
  on_target: 'bg-neon-green/20 text-neon-green',
  above_target: 'bg-status-warning/20 text-status-warning',
  high_inflation: 'bg-status-loss/20 text-status-loss',
  sticky_inflation: 'bg-status-loss/20 text-status-loss',
  low_inflation: 'bg-neon-blue/20 text-neon-blue',
  deflation: 'bg-neon-blue/20 text-neon-blue',
};

function getRiskColor(score: number): string {
  if (score < 40) return 'text-neon-green';
  if (score < 60) return 'text-status-warning';
  return 'text-status-loss';
}

function getRiskBarColor(score: number): string {
  if (score < 40) return 'bg-neon-green';
  if (score < 60) return 'bg-status-warning';
  return 'bg-status-loss';
}

function getRiskGlow(score: number): string {
  if (score < 40) return '0 0 10px rgba(0, 255, 136, 0.5)';
  if (score < 60) return '0 0 10px rgba(255, 170, 0, 0.5)';
  return '0 0 10px rgba(255, 51, 102, 0.5)';
}

function formatIndicatorValue(indicator: MacroIndicator | undefined): string {
  if (!indicator) return '-';
  const { value, series_id } = indicator;
  if (typeof value !== 'number') return String(value);
  if (series_id === 'JOBLESS_CLAIMS') return `${(value / 1000).toFixed(0)}K`;
  if (series_id === 'FEAR_GREED') return `${value.toFixed(0)}/100`;
  return value.toFixed(2);
}

const SignalBadge = memo(function SignalBadge({ signal }: { signal?: string }) {
  if (!signal) return null;
  const color = SIGNAL_COLORS[signal] || 'bg-gray-500/20 text-gray-400';
  return (
    <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${color}`}>
      {signal.toUpperCase()}
    </span>
  );
});

const RiskInfoPanel = memo(function RiskInfoPanel() {
  return (
    <div className="rounded-lg p-3 text-xs border border-neon-cyan/20"
         style={{ background: 'linear-gradient(135deg, rgba(0, 245, 255, 0.05) 0%, rgba(0, 128, 255, 0.03) 100%)' }}>
      <div className="font-medium text-neon-cyan mb-2 font-mono tracking-wider">风险评分方法论</div>
      <div className="space-y-2 text-gray-400">
        <p><strong className="text-gray-300">学术优化权重:</strong></p>
        <ul className="list-disc list-inside space-y-1 ml-2">
          <li>收益率曲线: 25% <span className="text-gray-500">(Estrella研究: 衰退预测85%准确)</span></li>
          <li>信用利差: 20% <span className="text-gray-500">(领先股市3-6月)</span></li>
          <li>VIX 波动率: 15%</li>
          <li>通胀 CPI: 15% <span className="text-gray-500">(滞胀风险)</span></li>
          <li>流动性 TED: 15%</li>
          <li>市场情绪: 10% <span className="text-gray-500">(逆向指标)</span></li>
        </ul>
        <p className="mt-2"><strong className="text-gray-300">分值含义:</strong></p>
        <div className="grid grid-cols-2 gap-1 ml-2">
          <span className="text-neon-green">0-40: 低风险</span>
          <span className="text-neon-green">可增加风险敞口</span>
          <span className="text-status-warning">40-60: 中等风险</span>
          <span className="text-status-warning">维持均衡配置</span>
          <span className="text-status-loss">60-80: 较高风险</span>
          <span className="text-status-loss">适度降低敞口</span>
          <span className="text-red-400">80-100: 高风险</span>
          <span className="text-red-400">建议防御配置</span>
        </div>
      </div>
    </div>
  );
});

const MacroAnalysis = memo(function MacroAnalysis({ data }: Props) {
  const [expandedCategory, setExpandedCategory] = useState<string | null>('credit');
  const [showRiskInfo, setShowRiskInfo] = useState(false);

  if (!data) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="text-center">
          <div className="w-6 h-6 border-2 border-neon-cyan/30 border-t-neon-cyan rounded-full animate-spin mx-auto mb-2"></div>
          <p className="text-gray-500 font-mono text-sm">加载宏观数据中...</p>
        </div>
      </div>
    );
  }

  const hasEstimateData = useMemo(
    () => Object.values(data.indicators || {}).some((ind) => ind.is_estimate),
    [data.indicators]
  );

  return (
    <div className="space-y-4">
      {/* Risk Score & Recession Probability */}
      <div className="grid grid-cols-2 gap-4">
        {/* Risk Score */}
        <div className="rounded-lg p-4 border border-white/5"
             style={{ background: 'linear-gradient(135deg, rgba(0, 245, 255, 0.03) 0%, transparent 100%)' }}>
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] font-mono text-gray-500 tracking-widest">综合风险</span>
            <button onClick={() => setShowRiskInfo(!showRiskInfo)} className="text-gray-500 hover:text-neon-cyan transition-colors">
              <Info className="w-3 h-3" />
            </button>
          </div>
          <div className={`text-3xl font-mono font-bold ${getRiskColor(data.overall_risk)}`}
               style={{ textShadow: getRiskGlow(data.overall_risk) }}>
            {data.overall_risk}
          </div>
          <div className="w-full bg-white/5 rounded-full h-1.5 mt-3">
            <div
              className={`h-1.5 rounded-full ${getRiskBarColor(data.overall_risk)} transition-all duration-500`}
              style={{ width: `${data.overall_risk}%`, boxShadow: getRiskGlow(data.overall_risk) }}
            />
          </div>
        </div>

        {/* Recession Probability */}
        <div className="rounded-lg p-4 border border-white/5"
             style={{ background: 'linear-gradient(135deg, rgba(168, 85, 247, 0.03) 0%, transparent 100%)' }}>
          <div className="text-[10px] font-mono text-gray-500 tracking-widest mb-2">衰退概率</div>
          <div className={`text-3xl font-mono font-bold ${getRiskColor(data.recession_probability || 0)}`}
               style={{ textShadow: getRiskGlow(data.recession_probability || 0) }}>
            {data.recession_probability || 0}%
          </div>
          <div className="w-full bg-white/5 rounded-full h-1.5 mt-3">
            <div
              className={`h-1.5 rounded-full ${getRiskBarColor(data.recession_probability || 0)} transition-all duration-500`}
              style={{ width: `${data.recession_probability || 0}%`, boxShadow: getRiskGlow(data.recession_probability || 0) }}
            />
          </div>
        </div>
      </div>

      {showRiskInfo ? <RiskInfoPanel /> : null}

      {/* Recommended Action */}
      {data.recommended_action ? (
        <div className="flex items-center justify-center">
          <div className={`flex items-center gap-2 px-5 py-2.5 rounded-lg font-mono text-sm ${ACTION_LABELS[data.recommended_action]?.color || 'bg-gray-500/20 text-gray-400'}`}>
            {ACTION_LABELS[data.recommended_action]?.icon}
            <span className="font-medium tracking-wide">
              建议: {ACTION_LABELS[data.recommended_action]?.label || data.recommended_action}
            </span>
          </div>
        </div>
      ) : null}

      {/* Market Status Indicators Row 1 */}
      <div className="grid grid-cols-4 gap-2">
        <div className="text-center p-3 rounded-lg border border-white/5"
             style={{ background: 'rgba(255, 255, 255, 0.02)' }}>
          <div className="text-[9px] font-mono text-gray-500 tracking-widest mb-1.5">波动率</div>
          <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-mono font-medium ${
            REGIME_LABELS.volatility[data.volatility]?.color || 'bg-gray-500/20 text-gray-400'
          }`}>
            {REGIME_LABELS.volatility[data.volatility]?.label || data.volatility}
          </span>
        </div>
        <div className="text-center p-3 rounded-lg border border-white/5"
             style={{ background: 'rgba(255, 255, 255, 0.02)' }}>
          <div className="text-[9px] font-mono text-gray-500 tracking-widest mb-1.5">收益曲线</div>
          <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-mono font-medium ${
            REGIME_LABELS.yield_curve[data.yield_curve]?.color || 'bg-gray-500/20 text-gray-400'
          }`}>
            {REGIME_LABELS.yield_curve[data.yield_curve]?.label || data.yield_curve}
          </span>
        </div>
        {data.credit ? (
          <div className="text-center p-3 rounded-lg border border-white/5"
               style={{ background: 'rgba(255, 255, 255, 0.02)' }}>
            <div className="text-[9px] font-mono text-gray-500 tracking-widest mb-1.5">信用</div>
            <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-mono font-medium ${
              REGIME_LABELS.credit[data.credit]?.color || 'bg-gray-500/20 text-gray-400'
            }`}>
              {REGIME_LABELS.credit[data.credit]?.label || data.credit}
            </span>
          </div>
        ) : null}
        {data.liquidity ? (
          <div className="text-center p-3 rounded-lg border border-white/5"
               style={{ background: 'rgba(255, 255, 255, 0.02)' }}>
            <div className="text-[9px] font-mono text-gray-500 tracking-widest mb-1.5">流动性</div>
            <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-mono font-medium ${
              REGIME_LABELS.liquidity[data.liquidity]?.color || 'bg-gray-500/20 text-gray-400'
            }`}>
              {REGIME_LABELS.liquidity[data.liquidity]?.label || data.liquidity}
            </span>
          </div>
        ) : null}
      </div>

      {/* Market Status Indicators Row 2 */}
      <div className="grid grid-cols-3 gap-2">
        <div className="text-center p-3 rounded-lg border border-white/5"
             style={{ background: 'rgba(255, 255, 255, 0.02)' }}>
          <div className="text-[9px] font-mono text-gray-500 tracking-widest mb-1.5">Fed 政策</div>
          <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-mono font-medium ${
            REGIME_LABELS.monetary_policy[data.monetary_policy]?.color || 'bg-gray-500/20 text-gray-400'
          }`}>
            {REGIME_LABELS.monetary_policy[data.monetary_policy]?.label || data.monetary_policy}
          </span>
        </div>
        {data.sentiment ? (
          <div className="text-center p-3 rounded-lg border border-white/5"
               style={{ background: 'rgba(255, 255, 255, 0.02)' }}>
            <div className="text-[9px] font-mono text-gray-500 tracking-widest mb-1.5">情绪</div>
            <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-mono font-medium ${
              REGIME_LABELS.sentiment[data.sentiment]?.color || 'bg-gray-500/20 text-gray-400'
            }`}>
              {REGIME_LABELS.sentiment[data.sentiment]?.label || data.sentiment}
            </span>
          </div>
        ) : null}
        {data.inflation ? (
          <div className="text-center p-3 rounded-lg border border-white/5"
               style={{ background: 'rgba(255, 255, 255, 0.02)' }}>
            <div className="text-[9px] font-mono text-gray-500 tracking-widest mb-1.5">通胀</div>
            <div className="flex flex-col items-center gap-1">
              <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-mono font-medium ${
                REGIME_LABELS.inflation[data.inflation]?.color || 'bg-gray-500/20 text-gray-400'
              }`}>
                {REGIME_LABELS.inflation[data.inflation]?.label || data.inflation}
              </span>
              {data.cpi_yoy !== undefined ? (
                <span className="text-[10px] font-mono text-gray-500">{data.cpi_yoy.toFixed(1)}%</span>
              ) : null}
            </div>
          </div>
        ) : null}
      </div>

      {/* Detailed Indicators */}
      <div className="border-t border-white/5 pt-4">
        <h4 className="text-[10px] font-mono text-gray-500 tracking-widest mb-3">详细指标</h4>
        <div className="space-y-2">
          {Object.entries(INDICATOR_CATEGORIES).map(([categoryKey, category]) => {
            const categoryIndicators = category.keys
              .map(key => data.indicators?.[key])
              .filter(Boolean);

            if (categoryIndicators.length === 0) return null;

            const isExpanded = expandedCategory === categoryKey;

            return (
              <div key={categoryKey} className="rounded-lg overflow-hidden border border-white/5"
                   style={{ background: 'rgba(255, 255, 255, 0.02)' }}>
                <button
                  onClick={() => setExpandedCategory(isExpanded ? null : categoryKey)}
                  className="w-full flex items-center justify-between px-3 py-2.5 text-sm font-mono text-gray-300 hover:bg-white/5 transition-colors"
                >
                  <span>{category.name}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] text-gray-500 bg-white/5 px-2 py-0.5 rounded">{categoryIndicators.length}</span>
                    {isExpanded ? <ChevronUp className="w-4 h-4 text-gray-500" /> : <ChevronDown className="w-4 h-4 text-gray-500" />}
                  </div>
                </button>
                {isExpanded ? (
                  <div className="px-3 pb-3 space-y-1.5">
                    {category.keys.map(key => {
                      const indicator = data.indicators?.[key];
                      if (!indicator) return null;
                      return (
                        <div key={key} className="flex items-center justify-between py-1.5 text-sm border-t border-white/5">
                          <span className="text-gray-400 font-mono text-xs">{indicator.name}</span>
                          <div className="flex items-center gap-2">
                            <span className="font-mono font-medium text-gray-200">{formatIndicatorValue(indicator)}</span>
                            <SignalBadge signal={indicator.signal} />
                            {indicator.is_estimate ? <span className="text-[10px] text-status-warning">*</span> : null}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>
      </div>

      {hasEstimateData ? (
        <p className="text-[10px] font-mono text-gray-500">* 为估算数据，仅供参考</p>
      ) : null}
    </div>
  );
});

export default MacroAnalysis;

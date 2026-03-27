import { useState, memo, useCallback } from 'react';
import { AlertTriangle, TrendingUp, DollarSign, Cpu, ThermometerSun, Info, Clock } from 'lucide-react';
import { useAIAnalysis } from '../hooks/useApi';

// Static JSX hoisting with cyber colors
const AlertTriangleIcon = <AlertTriangle className="w-5 h-5 text-neon-orange" />;
const DollarSignIcon = <DollarSign className="w-5 h-5 text-neon-green" />;
const CpuIcon = <Cpu className="w-5 h-5 text-neon-purple" />;
const ThermometerSunIcon = <ThermometerSun className="w-5 h-5 text-neon-cyan" />;
const TrendingUpIcon = <TrendingUp className="w-5 h-5 text-neon-pink" />;
const ClockIcon = <Clock className="w-4 h-4" />;
const InfoIcon = <Info className="w-4 h-4" />;

const ANALYSIS_INFO = {
  geopolitical_risk: {
    name: '地缘政治风险',
    calculation: '基于全球冲突、贸易摩擦、政治不确定性等因素综合评估',
    ranges: [
      { range: '0-30', meaning: '低风险，地缘局势稳定' },
      { range: '30-60', meaning: '中等风险，存在局部紧张' },
      { range: '60-100', meaning: '高风险，重大地缘事件' },
    ],
    impact: '高分值时应增加黄金、国债等避险资产',
  },
  fed_policy: {
    name: 'Fed 政策',
    calculation: '分析 Fed 声明、点阵图、经济预测，判断货币政策立场',
    stances: [
      { stance: 'dovish (鸽派)', meaning: '倾向降息，利好股市和风险资产' },
      { stance: 'neutral (中性)', meaning: '维持现状，市场波动有限' },
      { stance: 'hawkish (鹰派)', meaning: '倾向加息，利好债券和现金' },
    ],
    impact: '鸽派时可增加股票配置，鹰派时应增加债券和现金',
  },
  tech_trend: {
    name: '科技/AI 趋势',
    calculation: '分析科技公司财报、AI 发展、半导体需求等因素',
    outlooks: [
      { outlook: 'bullish (看涨)', meaning: '科技股前景乐观' },
      { outlook: 'neutral (中性)', meaning: '科技股平稳运行' },
      { outlook: 'bearish (看跌)', meaning: '科技股面临压力' },
    ],
    impact: '看涨时可增加 QQQ 配置，看跌时应降低科技股比重',
  },
  market_sentiment: {
    name: '市场情绪',
    calculation: '综合 Fear & Greed 指数、Put/Call 比率、资金流向等',
    ranges: [
      { range: '0-25', meaning: '极度恐惧，可能是买入机会' },
      { range: '25-50', meaning: '恐惧，市场谨慎' },
      { range: '50-75', meaning: '贪婪，市场乐观' },
      { range: '75-100', meaning: '极度贪婪，需警惕回调' },
    ],
    impact: '逆向思维：极度恐惧时考虑买入，极度贪婪时考虑减仓',
  },
} as const;

type InfoKey = keyof typeof ANALYSIS_INFO;

interface Props {
  externalData?: any;
}

const InfoPanel = memo(function InfoPanel({ infoKey }: { infoKey: InfoKey }) {
  const info = ANALYSIS_INFO[infoKey];

  return (
    <div className="mt-2 rounded-lg p-3 text-xs border border-neon-cyan/20"
         style={{ background: 'linear-gradient(135deg, rgba(0, 245, 255, 0.03) 0%, transparent 100%)' }}>
      <p className="text-gray-400 mb-2"><strong className="text-gray-300">计算方式:</strong> {info.calculation}</p>
      {'ranges' in info ? (
        <div className="mb-2">
          <strong className="text-gray-300">分值含义:</strong>
          <ul className="ml-2 mt-1 space-y-0.5">
            {info.ranges.map((r, i) => (
              <li key={i} className="text-gray-500 font-mono">{r.range}: {r.meaning}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {'stances' in info ? (
        <div className="mb-2">
          <strong className="text-gray-300">立场含义:</strong>
          <ul className="ml-2 mt-1 space-y-0.5">
            {info.stances.map((s, i) => (
              <li key={i} className="text-gray-500 font-mono">{s.stance}: {s.meaning}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {'outlooks' in info ? (
        <div className="mb-2">
          <strong className="text-gray-300">展望含义:</strong>
          <ul className="ml-2 mt-1 space-y-0.5">
            {info.outlooks.map((o, i) => (
              <li key={i} className="text-gray-500 font-mono">{o.outlook}: {o.meaning}</li>
            ))}
          </ul>
        </div>
      ) : null}
      <p className="text-gray-400"><strong className="text-neon-cyan">配置影响:</strong> {info.impact}</p>
    </div>
  );
});

interface AdjustmentItemProps {
  asset: string;
  value: number | string;
}

const AdjustmentItem = memo(function AdjustmentItem({ asset, value }: AdjustmentItemProps) {
  let direction: 'increase' | 'decrease' | 'maintain';
  let displayValue: string;

  if (typeof value === 'number') {
    if (value > 0) {
      direction = 'increase';
      displayValue = `+${(value * 100).toFixed(0)}%`;
    } else if (value < 0) {
      direction = 'decrease';
      displayValue = `${(value * 100).toFixed(0)}%`;
    } else {
      direction = 'maintain';
      displayValue = '维持';
    }
  } else {
    direction = value as 'increase' | 'decrease' | 'maintain';
    displayValue = value === 'increase' ? '增加' : value === 'decrease' ? '减少' : '维持';
  }

  return (
    <div className={`text-center p-2.5 rounded-lg border ${
      direction === 'increase'
        ? 'bg-neon-green/5 border-neon-green/30'
        : direction === 'decrease'
          ? 'bg-status-loss/5 border-status-loss/30'
          : 'bg-white/5 border-white/10'
    }`}>
      <div className="text-[10px] font-mono text-gray-500 tracking-wider mb-1">{asset}</div>
      <span className={`text-sm font-mono font-bold ${
        direction === 'increase' ? 'text-neon-green' :
        direction === 'decrease' ? 'text-status-loss' :
        'text-gray-400'
      }`} style={{
        textShadow: direction === 'increase'
          ? '0 0 10px rgba(0, 255, 136, 0.4)'
          : direction === 'decrease'
            ? '0 0 10px rgba(255, 51, 102, 0.4)'
            : 'none'
      }}>
        {displayValue}
      </span>
    </div>
  );
});

const AIAnalysisPanel = memo(function AIAnalysisPanel({ externalData }: Props) {
  const { data: fetchedData, loading } = useAIAnalysis();
  const [showInfo, setShowInfo] = useState<string | null>(null);

  const data = externalData || fetchedData;

  const toggleInfo = useCallback((key: string) => {
    setShowInfo(prev => prev === key ? null : key);
  }, []);

  if (loading && !data) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="w-8 h-8 border-2 border-neon-purple/30 border-t-neon-purple rounded-full animate-spin"></div>
      </div>
    );
  }

  const analysis = data as any;

  if (!analysis) {
    return (
      <div className="text-center py-8">
        <p className="text-gray-500 font-mono text-sm">暂无分析数据</p>
        <p className="text-gray-600 text-xs mt-1">点击"运行"生成新分析</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Analysis Time Indicator */}
      {analysis.cached_at ? (
        <div className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-mono border ${
          analysis.is_valid_for_optimize
            ? 'bg-neon-green/5 border-neon-green/30 text-neon-green'
            : 'bg-status-warning/5 border-status-warning/30 text-status-warning'
        }`}>
          {ClockIcon}
          <span className="text-xs">
            {new Date(analysis.cached_at).toLocaleString('zh-CN')}
            {analysis.age_minutes != null ? (
              <span className="ml-2 text-gray-500">
                ({analysis.age_minutes < 1 ? '刚刚' : `${Math.round(analysis.age_minutes)}分钟前`})
              </span>
            ) : null}
          </span>
          {!analysis.is_valid_for_optimize ? (
            <span className="ml-auto text-[10px] tracking-wider">已过期 - 需重新运行</span>
          ) : null}
        </div>
      ) : null}

      {/* Summary */}
      {analysis.summary ? (
        <div className="rounded-lg p-4 border border-neon-purple/30"
             style={{ background: 'linear-gradient(135deg, rgba(168, 85, 247, 0.05) 0%, transparent 100%)' }}>
          <h4 className="font-mono text-neon-purple text-[10px] tracking-widest mb-2">摘要</h4>
          <p className="text-sm text-gray-300 leading-relaxed">{analysis.summary}</p>
        </div>
      ) : null}

      {/* Analysis Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Geopolitical Risk */}
        {analysis.geopolitical_risk ? (
          <div className="rounded-lg p-4 border border-white/5"
               style={{ background: 'linear-gradient(135deg, rgba(255, 107, 0, 0.03) 0%, transparent 100%)' }}>
            <div className="flex items-center gap-2 mb-3">
              {AlertTriangleIcon}
              <h4 className="font-mono text-sm text-gray-200">地缘政治风险</h4>
              <button onClick={() => toggleInfo('geopolitical_risk')} className="text-gray-500 hover:text-neon-cyan transition-colors">
                {InfoIcon}
              </button>
              <span className={`ml-auto text-xl font-mono font-bold ${
                analysis.geopolitical_risk.score > 60 ? 'text-status-loss' :
                analysis.geopolitical_risk.score > 40 ? 'text-status-warning' : 'text-neon-green'
              }`} style={{
                textShadow: analysis.geopolitical_risk.score > 60
                  ? '0 0 10px rgba(255, 51, 102, 0.5)'
                  : analysis.geopolitical_risk.score > 40
                    ? '0 0 10px rgba(255, 170, 0, 0.5)'
                    : '0 0 10px rgba(0, 255, 136, 0.5)'
              }}>
                {analysis.geopolitical_risk.score}
              </span>
            </div>
            {showInfo === 'geopolitical_risk' ? <InfoPanel infoKey="geopolitical_risk" /> : null}
            <p className="text-sm text-gray-400 mb-2">{analysis.geopolitical_risk.analysis}</p>
            {analysis.geopolitical_risk.key_risks?.length > 0 ? (
              <div className="flex flex-wrap gap-1">
                {analysis.geopolitical_risk.key_risks.map((risk: string, i: number) => (
                  <span key={i} className="text-[10px] font-mono bg-neon-orange/10 text-neon-orange px-2 py-0.5 rounded border border-neon-orange/30">
                    {risk}
                  </span>
                ))}
              </div>
            ) : null}
          </div>
        ) : null}

        {/* Fed Policy */}
        {analysis.fed_policy ? (
          <div className="rounded-lg p-4 border border-white/5"
               style={{ background: 'linear-gradient(135deg, rgba(0, 255, 136, 0.03) 0%, transparent 100%)' }}>
            <div className="flex items-center gap-2 mb-3">
              {DollarSignIcon}
              <h4 className="font-mono text-sm text-gray-200">Fed 政策</h4>
              <button onClick={() => toggleInfo('fed_policy')} className="text-gray-500 hover:text-neon-cyan transition-colors">
                {InfoIcon}
              </button>
              <span className={`ml-auto text-xs font-mono font-medium px-2 py-0.5 rounded border ${
                analysis.fed_policy.stance === 'dovish'
                  ? 'bg-neon-green/10 text-neon-green border-neon-green/30'
                  : analysis.fed_policy.stance === 'hawkish'
                    ? 'bg-status-loss/10 text-status-loss border-status-loss/30'
                    : 'bg-gray-500/10 text-gray-400 border-gray-500/30'
              }`}>
                {analysis.fed_policy.stance === 'dovish' ? 'DOVISH' :
                 analysis.fed_policy.stance === 'hawkish' ? 'HAWKISH' : 'NEUTRAL'}
              </span>
            </div>
            {showInfo === 'fed_policy' ? <InfoPanel infoKey="fed_policy" /> : null}
            <p className="text-sm text-gray-400 mb-2">{analysis.fed_policy.analysis}</p>
            <div className="text-[10px] font-mono text-gray-500">
              利率展望: <span className="text-gray-300">{analysis.fed_policy.rate_outlook}</span>
            </div>
          </div>
        ) : null}

        {/* Tech Trend */}
        {analysis.tech_trend ? (
          <div className="rounded-lg p-4 border border-white/5"
               style={{ background: 'linear-gradient(135deg, rgba(168, 85, 247, 0.03) 0%, transparent 100%)' }}>
            <div className="flex items-center gap-2 mb-3">
              {CpuIcon}
              <h4 className="font-mono text-sm text-gray-200">科技/AI 趋势</h4>
              <button onClick={() => toggleInfo('tech_trend')} className="text-gray-500 hover:text-neon-cyan transition-colors">
                {InfoIcon}
              </button>
              <span className={`ml-auto text-xs font-mono font-medium px-2 py-0.5 rounded border ${
                analysis.tech_trend.outlook === 'bullish'
                  ? 'bg-neon-green/10 text-neon-green border-neon-green/30'
                  : analysis.tech_trend.outlook === 'bearish'
                    ? 'bg-status-loss/10 text-status-loss border-status-loss/30'
                    : 'bg-gray-500/10 text-gray-400 border-gray-500/30'
              }`}>
                {analysis.tech_trend.outlook === 'bullish' ? 'BULLISH' :
                 analysis.tech_trend.outlook === 'bearish' ? 'BEARISH' : 'NEUTRAL'}
              </span>
            </div>
            {showInfo === 'tech_trend' ? <InfoPanel infoKey="tech_trend" /> : null}
            <p className="text-sm text-gray-400 mb-2">{analysis.tech_trend.analysis}</p>
            {analysis.tech_trend.key_factors?.length > 0 ? (
              <div className="flex flex-wrap gap-1">
                {analysis.tech_trend.key_factors.map((factor: string, i: number) => (
                  <span key={i} className="text-[10px] font-mono bg-neon-purple/10 text-neon-purple px-2 py-0.5 rounded border border-neon-purple/30">
                    {factor}
                  </span>
                ))}
              </div>
            ) : null}
          </div>
        ) : null}

        {/* Market Sentiment */}
        {analysis.market_sentiment ? (
          <div className="rounded-lg p-4 border border-white/5"
               style={{ background: 'linear-gradient(135deg, rgba(0, 245, 255, 0.03) 0%, transparent 100%)' }}>
            <div className="flex items-center gap-2 mb-3">
              {ThermometerSunIcon}
              <h4 className="font-mono text-sm text-gray-200">市场情绪</h4>
              <button onClick={() => toggleInfo('market_sentiment')} className="text-gray-500 hover:text-neon-cyan transition-colors">
                {InfoIcon}
              </button>
              <span className={`ml-auto text-xl font-mono font-bold ${
                analysis.market_sentiment.score > 70 ? 'text-neon-green' :
                analysis.market_sentiment.score < 30 ? 'text-status-loss' : 'text-status-warning'
              }`} style={{
                textShadow: analysis.market_sentiment.score > 70
                  ? '0 0 10px rgba(0, 255, 136, 0.5)'
                  : analysis.market_sentiment.score < 30
                    ? '0 0 10px rgba(255, 51, 102, 0.5)'
                    : '0 0 10px rgba(255, 170, 0, 0.5)'
              }}>
                {analysis.market_sentiment.score}
              </span>
            </div>
            {showInfo === 'market_sentiment' ? <InfoPanel infoKey="market_sentiment" /> : null}
            <p className="text-sm text-gray-400 mb-2">{analysis.market_sentiment.short_term_outlook}</p>
            <div className="text-xs">
              <span className={`font-mono font-medium px-2 py-0.5 rounded border ${
                analysis.market_sentiment.level.includes('greed')
                  ? 'bg-neon-green/10 text-neon-green border-neon-green/30'
                  : analysis.market_sentiment.level.includes('fear')
                    ? 'bg-status-loss/10 text-status-loss border-status-loss/30'
                    : 'bg-gray-500/10 text-gray-400 border-gray-500/30'
              }`}>
                {analysis.market_sentiment.level === 'extreme_greed' ? 'EXTREME GREED' :
                 analysis.market_sentiment.level === 'greed' ? 'GREED' :
                 analysis.market_sentiment.level === 'fear' ? 'FEAR' :
                 analysis.market_sentiment.level === 'extreme_fear' ? 'EXTREME FEAR' : 'NEUTRAL'}
              </span>
            </div>
          </div>
        ) : null}
      </div>

      {/* Allocation Advice */}
      {analysis.allocation_advice ? (
        <div className="border-t border-white/5 pt-4">
          <h4 className="font-mono text-sm text-gray-200 mb-3 flex items-center gap-2">
            {TrendingUpIcon}
            <span className="tracking-wider">AI 建议</span>
            {analysis.allocation_advice.risk_level ? (
              <span className={`ml-auto text-[10px] font-mono px-2 py-0.5 rounded border ${
                analysis.allocation_advice.risk_level === 'conservative'
                  ? 'bg-neon-blue/10 text-neon-blue border-neon-blue/30'
                  : analysis.allocation_advice.risk_level === 'aggressive'
                    ? 'bg-status-loss/10 text-status-loss border-status-loss/30'
                    : 'bg-status-warning/10 text-status-warning border-status-warning/30'
              }`}>
                {analysis.allocation_advice.risk_level === 'conservative' ? 'CONSERVATIVE' :
                 analysis.allocation_advice.risk_level === 'aggressive' ? 'AGGRESSIVE' : 'MODERATE'}
              </span>
            ) : null}
          </h4>
          <p className="text-sm text-gray-400 mb-3">{analysis.allocation_advice.reasoning}</p>
          <div className="grid grid-cols-3 md:grid-cols-6 gap-2">
            {Object.entries(analysis.allocation_advice.adjustments || {}).map(([asset, value]) => (
              <AdjustmentItem key={asset} asset={asset} value={value as number | string} />
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
});

export default AIAnalysisPanel;

import { useState, useMemo, memo } from 'react';
import { ChevronDown, ChevronUp, Info, HelpCircle, History, ArrowRight } from 'lucide-react';
import type { PortfolioAllocation, PlanCData } from '../types';
import { useStrategyHistory } from '../hooks/useApi';
import { AssetPieChart, HistoryChart, preloadCharts } from './Charts';

interface Props {
  allocation: PortfolioAllocation | null | undefined;
  planCData?: PlanCData | null;
}

// Cyber theme colors for assets
const COLORS: { [key: string]: string } = {
  'SPY': '#0080ff',      // neon-blue
  'QQQ': '#a855f7',      // neon-purple
  'GLD': '#ffdd00',      // neon-yellow
  'BTC-USD': '#ff6b00',  // neon-orange
  'TLT': '#00ff88',      // neon-green
  'CASH': '#6b7280',     // gray
};

const ASSET_NAMES: { [key: string]: string } = {
  'SPY': 'S&P 500',
  'QQQ': 'NASDAQ 100',
  'GLD': 'GOLD',
  'BTC-USD': 'BITCOIN',
  'TLT': 'TREASURY',
  'CASH': 'CASH',
};

const ASSET_CHARACTERISTICS: { [key: string]: { risk: string; role: string; correlation: string } } = {
  'SPY': {
    risk: '中等波动',
    role: '核心股票配置，跟踪美股大盘',
    correlation: '与 QQQ 高度相关 (0.9+)'
  },
  'QQQ': {
    risk: '高波动',
    role: '成长型配置，科技股敞口',
    correlation: '与 SPY 高度相关，与 TLT 负相关'
  },
  'GLD': {
    risk: '中等波动',
    role: '避险资产，对冲通胀和地缘风险',
    correlation: '与股票低相关，与美元负相关'
  },
  'BTC-USD': {
    risk: '极高波动',
    role: '另类资产，高风险高收益',
    correlation: '与传统资产相关性不稳定'
  },
  'TLT': {
    risk: '中低波动',
    role: '债券配置，稳定收益和对冲',
    correlation: '与股票负相关 (避险时)'
  },
  'CASH': {
    risk: '无波动',
    role: '流动性储备，降低组合波动',
    correlation: '与所有资产零相关'
  },
};

// Memoized sub-components
const RebalanceCard = memo(function RebalanceCard({ rebalanceNeeded, threshold }: { rebalanceNeeded: number; threshold: number }) {
  return (
    <div className={`rounded-lg p-4 border ${
      rebalanceNeeded > 0
        ? 'bg-status-warning/5 border-status-warning/30'
        : 'bg-neon-green/5 border-neon-green/30'
    }`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className={`text-lg ${rebalanceNeeded > 0 ? 'text-status-warning' : 'text-neon-green'}`}>
            {rebalanceNeeded > 0 ? '⚠️' : '✓'}
          </span>
          <span className={`font-mono text-sm ${rebalanceNeeded > 0 ? 'text-status-warning' : 'text-neon-green'}`}>
            {rebalanceNeeded > 0
              ? `${rebalanceNeeded} 个资产需要调仓`
              : '当前配置符合目标'}
          </span>
        </div>
        <span className="text-[10px] font-mono text-gray-500">
          漂移阈值: {Math.round(threshold * 100)}%
        </span>
      </div>
    </div>
  );
});

const AssetAllocation = memo(function AssetAllocation({ allocation, planCData }: Props) {
  const [showHistory, setShowHistory] = useState(false);
  const [showMethodology, setShowMethodology] = useState(false);
  const [showAssetDetail, setShowAssetDetail] = useState<string | null>(null);
  const { data: historyRaw, loading: historyLoading } = useStrategyHistory(30);

  if (!allocation) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="text-center">
          <div className="w-6 h-6 border-2 border-neon-pink/30 border-t-neon-pink rounded-full animate-spin mx-auto mb-2"></div>
          <p className="text-gray-500 font-mono text-sm">等待优化结果...</p>
        </div>
      </div>
    );
  }

  const displayAllocation = planCData?.rounded_allocation || allocation;

  const chartData = useMemo(() =>
    Object.entries(displayAllocation)
      .filter(([_, value]) => value > 0)
      .map(([name, value]) => ({
        name: ASSET_NAMES[name] || name,
        ticker: name,
        value: Math.round(value * 100),
      }))
      .sort((a, b) => b.value - a.value),
    [displayAllocation]
  );

  const historyData = useMemo(() =>
    historyRaw
      .slice()
      .reverse()
      .map(item => {
        const point: Record<string, any> = {
          date: new Date(item.date).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' }),
          sharpe: item.sharpe_ratio,
        };
        Object.entries(item.allocation).forEach(([asset, weight]) => {
          point[asset] = Math.round((weight as number) * 100);
        });
        return point;
      }),
    [historyRaw]
  );

  const activeAssets = Object.keys(displayAllocation).filter(k => displayAllocation[k] > 0.01);
  const hasPlanC = planCData && planCData.rebalance_advice && Object.keys(planCData.rebalance_advice).length > 0;
  const rebalanceNeeded = planCData?.rebalance_count || 0;

  return (
    <div className="space-y-4">
      {/* Rebalance Summary */}
      {hasPlanC ? (
        <RebalanceCard rebalanceNeeded={rebalanceNeeded} threshold={planCData?.threshold || 0.05} />
      ) : null}

      {/* Plan C: Current vs Target Comparison */}
      {hasPlanC ? (
        <div className="rounded-lg overflow-hidden border border-white/10">
          <div className="px-4 py-2.5 border-b border-white/5"
               style={{ background: 'linear-gradient(135deg, rgba(255, 0, 170, 0.05) 0%, transparent 100%)' }}>
            <h4 className="text-[10px] font-mono text-gray-400 tracking-widest">配置对比</h4>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/5">
                  <th className="px-3 py-2 text-left text-[10px] font-mono text-gray-500 tracking-wider">资产</th>
                  <th className="px-3 py-2 text-center text-[10px] font-mono text-gray-500 tracking-wider">当前</th>
                  <th className="px-3 py-2 text-center text-gray-600"></th>
                  <th className="px-3 py-2 text-center text-[10px] font-mono text-gray-500 tracking-wider">目标</th>
                  <th className="px-3 py-2 text-center text-[10px] font-mono text-gray-500 tracking-wider">漂移</th>
                  <th className="px-3 py-2 text-center text-[10px] font-mono text-gray-500 tracking-wider">操作</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(planCData!.rebalance_advice)
                  .filter(([asset]) => !asset.startsWith('_'))
                  .sort(([, a], [, b]) => b.target - a.target)
                  .map(([asset, advice]) => (
                    <tr key={asset} className="border-b border-white/5 last:border-b-0 hover:bg-white/5 transition-colors">
                      <td className="px-3 py-2.5">
                        <div className="flex items-center gap-2">
                          <div
                            className="w-3 h-3 rounded-full"
                            style={{ backgroundColor: COLORS[asset] || '#94a3b8', boxShadow: `0 0 8px ${COLORS[asset]}50` }}
                          />
                          <span className="font-mono text-gray-200">{ASSET_NAMES[asset] || asset}</span>
                        </div>
                      </td>
                      <td className="px-3 py-2.5 text-center font-mono text-gray-400">
                        {Math.round(advice.current * 100)}%
                      </td>
                      <td className="px-3 py-2.5 text-center text-gray-600">
                        <ArrowRight className="w-4 h-4 inline" />
                      </td>
                      <td className="px-3 py-2.5 text-center font-mono font-medium text-gray-200">
                        {Math.round(advice.target * 100)}%
                      </td>
                      <td className="px-3 py-2.5 text-center font-mono">
                        {advice.drift !== 0 ? (
                          <span className={advice.drift > 0 ? 'text-neon-green' : 'text-status-loss'}
                                style={{ textShadow: advice.drift > 0 ? '0 0 8px rgba(0, 255, 136, 0.4)' : '0 0 8px rgba(255, 51, 102, 0.4)' }}>
                            {advice.drift > 0 ? '+' : ''}{Math.round(advice.drift * 100)}%
                          </span>
                        ) : (
                          <span className="text-gray-600">-</span>
                        )}
                      </td>
                      <td className="px-3 py-2.5 text-center">
                        {advice.action === '调仓' ? (
                          advice.drift > 0 ? (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-neon-green/10 text-neon-green border border-neon-green/30">
                              加仓
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-status-loss/10 text-status-loss border border-status-loss/30">
                              减仓
                            </span>
                          )
                        ) : (
                          <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-white/5 text-gray-500 border border-white/10">
                            维持
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}

      {/* Methodology */}
      <div className="rounded-lg border border-neon-cyan/20"
           style={{ background: 'linear-gradient(135deg, rgba(0, 245, 255, 0.03) 0%, transparent 100%)' }}>
        <button
          className="w-full flex items-center justify-between p-3"
          onClick={() => setShowMethodology(!showMethodology)}
        >
          <div className="flex items-center gap-2">
            <HelpCircle className="w-4 h-4 text-neon-cyan" />
            <span className="text-xs font-mono text-neon-cyan tracking-wider">优化方法论</span>
          </div>
          {showMethodology ? (
            <ChevronUp className="w-4 h-4 text-neon-cyan" />
          ) : (
            <ChevronDown className="w-4 h-4 text-neon-cyan" />
          )}
        </button>

        {showMethodology ? (
          <div className="px-3 pb-3 text-xs text-gray-400 space-y-2">
            <div className="rounded p-2 border border-white/5" style={{ background: 'rgba(255, 255, 255, 0.02)' }}>
              <p><strong className="text-gray-300">优化目标:</strong> 最大化 Sharpe Ratio，同时控制最大回撤</p>
              <p className="mt-1 font-mono text-[10px] bg-cyber-darker p-1.5 rounded border border-white/5 text-neon-cyan">
                Objective = -Sharpe + Penalty × max(0, MDD - Threshold)²
              </p>
            </div>
            <div className="rounded p-2 border border-white/5" style={{ background: 'rgba(255, 255, 255, 0.02)' }}>
              <p><strong className="text-gray-300">数据源:</strong> 过去1年日收益率 → 年化收益/波动率/协方差</p>
              <p><strong className="text-gray-300">算法:</strong> SLSQP 约束优化 (权重 0-40%, 总和 100%)</p>
            </div>
            <div className="rounded p-2 border border-white/5" style={{ background: 'rgba(255, 255, 255, 0.02)' }}>
              <p><strong className="text-gray-300">方案C取整:</strong> 配置取整到 5%，漂移超过 5% 才建议调仓</p>
            </div>
          </div>
        ) : null}
      </div>

      <div className="flex flex-col lg:flex-row items-center gap-6">
        {/* Treemap */}
        <div className="w-full lg:w-1/2 h-64">
          <AssetPieChart data={chartData} colors={COLORS} />
        </div>

        {/* Allocation Table */}
        <div className="w-full lg:w-1/2">
          <div className="space-y-2">
            {chartData.map((item) => (
              <div key={item.ticker}>
                <div
                  className="flex items-center gap-3 cursor-pointer hover:bg-white/5 rounded-lg p-2 -m-1 transition-colors"
                  onClick={() => setShowAssetDetail(showAssetDetail === item.ticker ? null : item.ticker)}
                >
                  <div
                    className="w-3 h-3 rounded-full flex-shrink-0"
                    style={{ backgroundColor: COLORS[item.ticker] || '#94a3b8', boxShadow: `0 0 8px ${COLORS[item.ticker]}50` }}
                  />
                  <div className="flex-1">
                    <div className="flex justify-between items-center">
                      <div className="flex items-center gap-1">
                        <span className="text-sm font-mono text-gray-200">{item.name}</span>
                        <Info className="w-3 h-3 text-gray-600" />
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-mono font-bold text-gray-100">{item.value}%</span>
                        {hasPlanC && planCData!.rebalance_advice[item.ticker]?.action === '调仓' ? (
                          <span className={`text-xs font-mono font-medium ${
                            planCData!.rebalance_advice[item.ticker].direction === '↑'
                              ? 'text-neon-green'
                              : 'text-status-loss'
                          }`} style={{
                            textShadow: planCData!.rebalance_advice[item.ticker].direction === '↑'
                              ? '0 0 8px rgba(0, 255, 136, 0.5)'
                              : '0 0 8px rgba(255, 51, 102, 0.5)'
                          }}>
                            {planCData!.rebalance_advice[item.ticker].direction}
                          </span>
                        ) : null}
                      </div>
                    </div>
                    <div className="w-full bg-white/5 rounded-full h-1.5 mt-1.5">
                      <div
                        className="h-1.5 rounded-full transition-all duration-500"
                        style={{
                          width: `${item.value}%`,
                          backgroundColor: COLORS[item.ticker] || '#94a3b8',
                          boxShadow: `0 0 8px ${COLORS[item.ticker]}50`
                        }}
                      />
                    </div>
                  </div>
                </div>
                {showAssetDetail === item.ticker && ASSET_CHARACTERISTICS[item.ticker] ? (
                  <div className="ml-6 mt-2 p-3 rounded-lg text-xs text-gray-400 space-y-1 border border-white/5"
                       style={{ background: 'rgba(255, 255, 255, 0.02)' }}>
                    <p><strong className="text-gray-300">风险:</strong> {ASSET_CHARACTERISTICS[item.ticker].risk}</p>
                    <p><strong className="text-gray-300">角色:</strong> {ASSET_CHARACTERISTICS[item.ticker].role}</p>
                  </div>
                ) : null}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* History Toggle */}
      {historyData.length > 1 ? (
        <div className="border-t border-white/5 pt-4">
          <button
            className="flex items-center gap-2 text-sm font-mono text-gray-400 hover:text-neon-cyan transition-colors"
            onClick={() => setShowHistory(!showHistory)}
            onMouseEnter={preloadCharts}
            onFocus={preloadCharts}
          >
            <History className="w-4 h-4" />
            {showHistory ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            <span className="tracking-wider">历史配置 ({historyData.length} 条记录)</span>
          </button>

          {showHistory ? (
            <div className="mt-4">
              {historyLoading ? (
                <div className="h-48 flex items-center justify-center">
                  <div className="w-5 h-5 border-2 border-neon-cyan/30 border-t-neon-cyan rounded-full animate-spin"></div>
                  <span className="ml-2 text-gray-500 font-mono text-sm">加载中...</span>
                </div>
              ) : (
                <div className="h-48">
                  <HistoryChart
                    data={historyData}
                    activeAssets={activeAssets}
                    colors={COLORS}
                    assetNames={ASSET_NAMES}
                  />
                </div>
              )}
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
});

export default AssetAllocation;

import { memo, useState, useMemo } from 'react';
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Area,
  AreaChart
} from 'recharts';
import { TrendingUp, TrendingDown, Minus, ChevronDown, ChevronUp, History, GitCompare } from 'lucide-react';
import { useHistoryTrend, useAllocationChanges } from '../hooks/useApi';

interface StrategyHistoryProps {
  onOpenComparison?: () => void;
}

const METRICS = [
  { key: 'sharpe', name: '夏普比率', color: '#00f5ff', unit: '' },
  { key: 'return', name: '预期收益', color: '#00ff88', unit: '%' },
  { key: 'max_drawdown', name: '最大回撤', color: '#ff3366', unit: '%' },
] as const;

type MetricKey = typeof METRICS[number]['key'];

const TIME_RANGES = [
  { value: 7, label: '7D' },
  { value: 30, label: '30D' },
  { value: 90, label: '90D' },
];

const StrategyHistory = memo(function StrategyHistory({ onOpenComparison }: StrategyHistoryProps) {
  const [timeRange, setTimeRange] = useState(30);
  const [selectedMetric, setSelectedMetric] = useState<MetricKey>('sharpe');
  const [showChanges, setShowChanges] = useState(false);

  const { data: trendData, summary: trendSummary, loading: trendLoading } = useHistoryTrend(timeRange);
  const { data: allocationChanges, summary: changesSummary } = useAllocationChanges(timeRange);

  const formattedData = useMemo(() => {
    if (!trendData || trendData.length === 0) return [];
    return trendData.map(item => ({
      ...item,
      date: new Date(item.date).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' }),
      fullDate: new Date(item.date).toLocaleDateString('zh-CN'),
      return: item.return != null ? item.return * 100 : null,
      max_drawdown: item.max_drawdown != null ? item.max_drawdown * 100 : null,
    }));
  }, [trendData]);

  const currentMetric = METRICS.find(m => m.key === selectedMetric) || METRICS[0];

  const getTrendIcon = (trend: string) => {
    if (trend === 'up') return <TrendingUp className="w-4 h-4" />;
    if (trend === 'down') return <TrendingDown className="w-4 h-4" />;
    return <Minus className="w-4 h-4" />;
  };

  const getTrendColor = (trend: string, metric: string) => {
    if (metric === 'max_drawdown') {
      return trend === 'up' ? 'text-status-loss' : trend === 'down' ? 'text-neon-green' : 'text-gray-400';
    }
    return trend === 'up' ? 'text-neon-green' : trend === 'down' ? 'text-status-loss' : 'text-gray-400';
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('zh-CN', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (trendLoading) {
    return (
      <div className="h-64 flex items-center justify-center">
        <div className="w-6 h-6 border-2 border-neon-cyan/30 border-t-neon-cyan rounded-full animate-spin" />
      </div>
    );
  }

  if (!trendData || trendData.length === 0) {
    return (
      <div className="h-48 flex flex-col items-center justify-center text-gray-500 font-mono text-sm">
        <History className="w-8 h-8 mb-2 opacity-50" />
        <p>暂无历史数据</p>
        <p className="text-xs mt-1">运行策略优化后将自动记录</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header: 时间范围 + 指标选择 + 对比按钮 */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        {/* 时间范围 */}
        <div className="flex items-center gap-2">
          {TIME_RANGES.map(range => (
            <button
              key={range.value}
              onClick={() => setTimeRange(range.value)}
              className={`px-2.5 py-1 rounded-lg font-mono text-[10px] transition-all ${
                timeRange === range.value
                  ? 'bg-neon-cyan/20 text-neon-cyan border border-neon-cyan/40'
                  : 'bg-white/5 text-gray-400 border border-white/10 hover:border-white/20'
              }`}
            >
              {range.label}
            </button>
          ))}
        </div>

        {/* 指标选择 */}
        <div className="flex items-center gap-2">
          {METRICS.map(metric => (
            <button
              key={metric.key}
              onClick={() => setSelectedMetric(metric.key)}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg font-mono text-[10px] transition-all ${
                selectedMetric === metric.key
                  ? 'bg-white/10 border border-white/20'
                  : 'bg-white/5 border border-transparent hover:border-white/10'
              }`}
            >
              <div
                className="w-1.5 h-1.5 rounded-full"
                style={{ backgroundColor: metric.color, opacity: selectedMetric === metric.key ? 1 : 0.3 }}
              />
              <span className={selectedMetric === metric.key ? 'text-gray-200' : 'text-gray-500'}>
                {metric.name}
              </span>
            </button>
          ))}
        </div>

        {/* 对比按钮 */}
        {onOpenComparison && (
          <button
            onClick={onOpenComparison}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-mono text-[10px] bg-neon-purple/10 text-neon-purple border border-neon-purple/30 hover:border-neon-purple/50 transition-all"
          >
            <GitCompare className="w-3 h-3" />
            详细对比
          </button>
        )}
      </div>

      {/* 指标摘要卡片 */}
      {trendSummary && (
        <div className="grid grid-cols-3 gap-3">
          {METRICS.map(metric => {
            const s = trendSummary[metric.key as keyof typeof trendSummary];
            if (!s || typeof s !== 'object') return null;
            const isSelected = selectedMetric === metric.key;
            const avg = s.avg;
            const min = s.min;
            const max = s.max;
            const trend = s.trend;

            return (
              <button
                key={metric.key}
                onClick={() => setSelectedMetric(metric.key)}
                className={`rounded-lg p-3 border transition-all text-left ${
                  isSelected
                    ? 'border-white/20 bg-white/5'
                    : 'border-white/5 hover:border-white/10'
                }`}
                style={{
                  background: isSelected
                    ? `linear-gradient(135deg, ${metric.color}10 0%, transparent 100%)`
                    : undefined
                }}
              >
                <div className="text-[9px] font-mono text-gray-500 tracking-widest mb-1">{metric.name}</div>
                <div className="flex items-baseline gap-2">
                  <span className="text-lg font-mono font-bold text-gray-200">
                    {avg != null ? (metric.unit === '%' ? (avg * 100).toFixed(1) : avg.toFixed(2)) : '-'}
                    {metric.unit}
                  </span>
                  {trend && (
                    <span className={getTrendColor(trend, metric.key)}>
                      {getTrendIcon(trend)}
                    </span>
                  )}
                </div>
                <div className="text-[9px] font-mono text-gray-600 mt-0.5">
                  {min != null && max != null && (
                    metric.unit === '%'
                      ? `${(min * 100).toFixed(1)} ~ ${(max * 100).toFixed(1)}%`
                      : `${min.toFixed(2)} ~ ${max.toFixed(2)}`
                  )}
                </div>
              </button>
            );
          })}
        </div>
      )}

      {/* 图表 */}
      {formattedData.length > 0 && (
        <div className="h-48">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={formattedData} margin={{ top: 5, right: 5, left: -10, bottom: 0 }}>
              <defs>
                <linearGradient id={`gradient-${selectedMetric}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={currentMetric.color} stopOpacity={0.3}/>
                  <stop offset="95%" stopColor={currentMetric.color} stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" />
              <XAxis
                dataKey="date"
                tick={{ fill: '#4b5563', fontSize: 9 }}
                axisLine={{ stroke: 'rgba(255,255,255,0.05)' }}
                tickLine={false}
                interval="preserveStartEnd"
              />
              <YAxis
                tick={{ fill: '#4b5563', fontSize: 9 }}
                axisLine={{ stroke: 'rgba(255,255,255,0.05)' }}
                tickLine={false}
                width={35}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'rgba(10, 15, 25, 0.95)',
                  border: '1px solid rgba(255,255,255,0.1)',
                  borderRadius: '8px',
                  boxShadow: '0 4px 20px rgba(0,0,0,0.5)',
                  fontSize: 11
                }}
                labelStyle={{ color: '#9ca3af', fontSize: 10 }}
                formatter={(value) => {
                  if (value == null || typeof value !== 'number') return ['-', currentMetric.name];
                  return [
                    currentMetric.unit === '%' ? `${value.toFixed(1)}%` : value.toFixed(3),
                    currentMetric.name
                  ];
                }}
                labelFormatter={(label) => {
                  const item = formattedData.find(d => d.date === label);
                  return item?.fullDate || label;
                }}
              />
              <Area
                type="monotone"
                dataKey={selectedMetric}
                name={currentMetric.name}
                stroke={currentMetric.color}
                strokeWidth={2}
                fill={`url(#gradient-${selectedMetric})`}
                dot={false}
                activeDot={{ r: 4, fill: currentMetric.color, strokeWidth: 0 }}
              />
              {/* 夏普比率参考线 */}
              {selectedMetric === 'sharpe' && (
                <ReferenceLine
                  y={1}
                  stroke="rgba(0,245,255,0.4)"
                  strokeDasharray="5 5"
                  label={{ value: '1.0', position: 'right', fill: '#4b5563', fontSize: 9 }}
                />
              )}
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* 配置变化记录 (可折叠) */}
      {allocationChanges && allocationChanges.length > 0 && (
        <div className="border-t border-white/5 pt-3">
          <button
            onClick={() => setShowChanges(!showChanges)}
            className="flex items-center gap-2 text-[10px] font-mono text-gray-500 hover:text-gray-400 transition-colors"
          >
            <History className="w-3 h-3" />
            配置调整记录 ({changesSummary?.total_changes || 0})
            {showChanges ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          </button>

          {showChanges && (
            <div className="mt-2 space-y-2 max-h-32 overflow-y-auto pr-1">
              {allocationChanges.slice(0, 5).map((change, idx) => (
                <div
                  key={idx}
                  className="flex items-center gap-3 rounded-lg p-2 bg-white/[0.02] border border-white/5"
                >
                  <span className="text-[9px] font-mono text-gray-600 whitespace-nowrap">
                    {formatDate(change.date)}
                  </span>
                  <div className="flex flex-wrap gap-1">
                    {Object.entries(change.changes).slice(0, 4).map(([asset, detail]) => (
                      <span
                        key={asset}
                        className={`px-1.5 py-0.5 rounded text-[9px] font-mono ${
                          detail.change > 0
                            ? 'bg-neon-green/10 text-neon-green'
                            : 'bg-status-loss/10 text-status-loss'
                        }`}
                      >
                        {asset} {detail.change > 0 ? '+' : ''}{Math.round(detail.change * 100)}%
                      </span>
                    ))}
                    {Object.keys(change.changes).length > 4 && (
                      <span className="text-[9px] font-mono text-gray-600">
                        +{Object.keys(change.changes).length - 4}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
});

export default StrategyHistory;

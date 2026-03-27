import { memo, useState, useMemo } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine
} from 'recharts';
import type { TrendDataPoint, MetricsSummary } from '../../types';

interface TrendChartProps {
  data: TrendDataPoint[];
  summary: {
    sharpe: MetricsSummary;
    max_drawdown: MetricsSummary;
    return: MetricsSummary;
  } | null;
}

const METRICS = [
  { key: 'sharpe', name: '夏普比率', color: '#00f5ff', unit: '' },
  { key: 'return', name: '预期收益', color: '#00ff88', unit: '%' },
  { key: 'max_drawdown', name: '最大回撤', color: '#ff3366', unit: '%' },
];

const TrendChart = memo(function TrendChart({ data, summary }: TrendChartProps) {
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>(['sharpe']);

  const formattedData = useMemo(() => {
    return data.map(item => ({
      ...item,
      date: new Date(item.date).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' }),
      return: item.return ? item.return * 100 : null,
      max_drawdown: item.max_drawdown ? item.max_drawdown * 100 : null,
    }));
  }, [data]);

  const toggleMetric = (key: string) => {
    setSelectedMetrics(prev =>
      prev.includes(key)
        ? prev.filter(m => m !== key)
        : [...prev, key]
    );
  };

  const getTrendIcon = (trend: string) => {
    if (trend === 'up') return '↑';
    if (trend === 'down') return '↓';
    return '→';
  };

  const getTrendColor = (trend: string, metric: string) => {
    if (metric === 'max_drawdown') {
      return trend === 'up' ? 'text-status-loss' : trend === 'down' ? 'text-neon-green' : 'text-gray-400';
    }
    return trend === 'up' ? 'text-neon-green' : trend === 'down' ? 'text-status-loss' : 'text-gray-400';
  };

  if (data.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center text-gray-500 font-mono text-sm">
        暂无趋势数据
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* 指标选择器 */}
      <div className="flex items-center gap-3">
        {METRICS.map(metric => (
          <button
            key={metric.key}
            onClick={() => toggleMetric(metric.key)}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg font-mono text-xs transition-all ${
              selectedMetrics.includes(metric.key)
                ? 'bg-white/10 border border-white/20'
                : 'bg-white/5 border border-transparent hover:border-white/10'
            }`}
          >
            <div
              className="w-2 h-2 rounded-full"
              style={{ backgroundColor: metric.color, opacity: selectedMetrics.includes(metric.key) ? 1 : 0.3 }}
            />
            <span className={selectedMetrics.includes(metric.key) ? 'text-gray-200' : 'text-gray-500'}>
              {metric.name}
            </span>
          </button>
        ))}
      </div>

      {/* 指标摘要 */}
      {summary && (
        <div className="grid grid-cols-3 gap-4">
          {METRICS.map(metric => {
            const s = summary[metric.key as keyof typeof summary];
            if (!s) return null;
            return (
              <div
                key={metric.key}
                className="rounded-lg p-3 border border-white/10"
                style={{ background: `linear-gradient(135deg, ${metric.color}08 0%, transparent 100%)` }}
              >
                <div className="text-[10px] font-mono text-gray-500 tracking-widest mb-1">{metric.name}</div>
                <div className="flex items-baseline gap-2">
                  <span className="text-lg font-mono font-bold text-gray-200">
                    {s.avg !== null ? s.avg.toFixed(2) : '-'}
                    {metric.unit}
                  </span>
                  <span className={`text-sm font-mono ${getTrendColor(s.trend, metric.key)}`}>
                    {getTrendIcon(s.trend)}
                  </span>
                </div>
                <div className="text-[10px] font-mono text-gray-500 mt-1">
                  范围: {s.min?.toFixed(2)} ~ {s.max?.toFixed(2)}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* 图表 */}
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={formattedData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis
              dataKey="date"
              tick={{ fill: '#6b7280', fontSize: 10 }}
              axisLine={{ stroke: 'rgba(255,255,255,0.1)' }}
              tickLine={false}
            />
            <YAxis
              tick={{ fill: '#6b7280', fontSize: 10 }}
              axisLine={{ stroke: 'rgba(255,255,255,0.1)' }}
              tickLine={false}
              width={40}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'rgba(10, 15, 25, 0.95)',
                border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: '8px',
                boxShadow: '0 4px 20px rgba(0,0,0,0.5)'
              }}
              labelStyle={{ color: '#9ca3af', fontSize: 11 }}
              itemStyle={{ fontSize: 11 }}
            />
            {selectedMetrics.includes('sharpe') && (
              <Line
                type="monotone"
                dataKey="sharpe"
                name="夏普比率"
                stroke="#00f5ff"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, fill: '#00f5ff' }}
              />
            )}
            {selectedMetrics.includes('return') && (
              <Line
                type="monotone"
                dataKey="return"
                name="预期收益 (%)"
                stroke="#00ff88"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, fill: '#00ff88' }}
              />
            )}
            {selectedMetrics.includes('max_drawdown') && (
              <Line
                type="monotone"
                dataKey="max_drawdown"
                name="最大回撤 (%)"
                stroke="#ff3366"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, fill: '#ff3366' }}
              />
            )}
            {/* 夏普比率参考线 */}
            {selectedMetrics.includes('sharpe') && (
              <ReferenceLine y={1} stroke="rgba(0,245,255,0.3)" strokeDasharray="5 5" />
            )}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
});

export default TrendChart;

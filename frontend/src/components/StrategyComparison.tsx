import { useState, useEffect, memo, useCallback } from 'react';
import { X, GitCompare, Calendar, ChevronDown, ChevronUp } from 'lucide-react';
import { useStrategySnapshots, useHistoryTrend, useAllocationChanges, compareSnapshots } from '../hooks/useApi';
import type { TrendDataPoint } from '../types';
import TrendChart from './Charts/TrendChart';

interface StrategyComparisonProps {
  isOpen: boolean;
  onClose: () => void;
}

const TIME_RANGES = [
  { value: 7, label: '7D' },
  { value: 30, label: '30D' },
  { value: 90, label: '90D' },
];

const StrategyComparison = memo(function StrategyComparison({ isOpen, onClose }: StrategyComparisonProps) {
  const [timeRange, setTimeRange] = useState(30);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [compareResults, setCompareResults] = useState<any[] | null>(null);
  const [comparing, setComparing] = useState(false);
  const [showChanges, setShowChanges] = useState(false);

  const { data: snapshots, loading: snapshotsLoading } = useStrategySnapshots(timeRange);
  const { data: trendData, summary: trendSummary, loading: trendLoading } = useHistoryTrend(timeRange);
  const { data: allocationChanges, summary: changesSummary } = useAllocationChanges(timeRange);

  // 重置选择
  useEffect(() => {
    setSelectedIds([]);
    setCompareResults(null);
  }, [timeRange]);

  // 切换选择快照
  const toggleSnapshot = useCallback((id: number) => {
    setSelectedIds(prev => {
      if (prev.includes(id)) {
        return prev.filter(i => i !== id);
      }
      if (prev.length >= 3) {
        return [...prev.slice(1), id];
      }
      return [...prev, id];
    });
  }, []);

  // 执行对比
  const handleCompare = useCallback(async () => {
    if (selectedIds.length < 2) return;

    setComparing(true);
    try {
      const results = await compareSnapshots(selectedIds);
      setCompareResults(results);
    } catch (err) {
      console.error('Compare failed:', err);
    } finally {
      setComparing(false);
    }
  }, [selectedIds]);

  // 格式化日期
  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('zh-CN', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // 获取变化指示
  const getChangeIndicator = (current: number, baseline: number) => {
    const diff = current - baseline;
    const pct = baseline !== 0 ? (diff / baseline) * 100 : 0;

    if (Math.abs(pct) < 1) return null;

    return {
      value: pct,
      isPositive: diff > 0,
      display: `${diff > 0 ? '+' : ''}${pct.toFixed(1)}%`
    };
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} />

      {/* Modal */}
      <div className="relative w-full max-w-5xl max-h-[90vh] overflow-hidden rounded-2xl bg-cyber-dark border border-white/10 shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/10">
          <div className="flex items-center gap-3">
            <GitCompare className="w-5 h-5 text-neon-purple" />
            <h2 className="text-lg font-display font-semibold text-gradient">历史策略对比</h2>
          </div>

          {/* 时间范围选择 */}
          <div className="flex items-center gap-2">
            {TIME_RANGES.map(range => (
              <button
                key={range.value}
                onClick={() => setTimeRange(range.value)}
                className={`px-3 py-1.5 rounded-lg font-mono text-xs transition-all ${
                  timeRange === range.value
                    ? 'bg-neon-cyan/20 text-neon-cyan border border-neon-cyan/40'
                    : 'bg-white/5 text-gray-400 border border-white/10 hover:border-white/20'
                }`}
              >
                {range.label}
              </button>
            ))}
          </div>

          <button onClick={onClose} className="p-2 rounded-lg hover:bg-white/5 transition-colors">
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>

        <div className="overflow-y-auto" style={{ maxHeight: 'calc(90vh - 80px)' }}>
          <div className="p-6 space-y-6">
            {/* 趋势图表 */}
            <section>
              <h3 className="text-sm font-mono text-gray-400 tracking-widest mb-4">指标趋势</h3>
              {trendLoading ? (
                <div className="h-64 flex items-center justify-center">
                  <div className="w-6 h-6 border-2 border-neon-purple/30 border-t-neon-purple rounded-full animate-spin" />
                </div>
              ) : (
                <TrendChart data={trendData as TrendDataPoint[]} summary={trendSummary} />
              )}
            </section>

            {/* 配置变化历史 */}
            <section>
              <button
                onClick={() => setShowChanges(!showChanges)}
                className="flex items-center gap-2 text-sm font-mono text-gray-400 hover:text-neon-cyan transition-colors"
              >
                <Calendar className="w-4 h-4" />
                配置变化记录 ({changesSummary?.total_changes || 0} 次)
                {showChanges ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              </button>

              {showChanges && allocationChanges.length > 0 && (
                <div className="mt-3 space-y-2 max-h-48 overflow-y-auto">
                  {allocationChanges.map((change, idx) => (
                    <div
                      key={idx}
                      className="rounded-lg p-3 border border-white/10"
                      style={{ background: 'rgba(255,255,255,0.02)' }}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-mono text-gray-500">{formatDate(change.date)}</span>
                        <span className="text-[10px] font-mono text-gray-600">{change.method}</span>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {Object.entries(change.changes).map(([asset, detail]) => (
                          <div
                            key={asset}
                            className={`flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono ${
                              detail.change > 0
                                ? 'bg-neon-green/10 text-neon-green'
                                : 'bg-status-loss/10 text-status-loss'
                            }`}
                          >
                            <span>{asset}</span>
                            <span>{detail.change > 0 ? '+' : ''}{Math.round(detail.change * 100)}%</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>

            {/* 快照选择器 */}
            <section>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-mono text-gray-400 tracking-widest">
                  选择快照对比 (已选 {selectedIds.length}/3)
                </h3>
                <button
                  onClick={handleCompare}
                  disabled={selectedIds.length < 2 || comparing}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg font-mono text-sm transition-all ${
                    selectedIds.length >= 2
                      ? 'bg-neon-purple/10 text-neon-purple border border-neon-purple/30 hover:border-neon-purple/50'
                      : 'bg-white/5 text-gray-600 border border-white/10 cursor-not-allowed'
                  }`}
                >
                  <GitCompare className="w-4 h-4" />
                  {comparing ? '对比中...' : '对比选中'}
                </button>
              </div>

              {snapshotsLoading ? (
                <div className="h-32 flex items-center justify-center">
                  <div className="w-6 h-6 border-2 border-neon-purple/30 border-t-neon-purple rounded-full animate-spin" />
                </div>
              ) : (
                <div className="grid grid-cols-4 gap-3">
                  {snapshots.slice(0, 12).map(snapshot => {
                    const isSelected = selectedIds.includes(snapshot.id);
                    const metrics = snapshot.metrics;

                    return (
                      <button
                        key={snapshot.id}
                        onClick={() => toggleSnapshot(snapshot.id)}
                        className={`text-left p-3 rounded-lg transition-all ${
                          isSelected
                            ? 'bg-neon-purple/20 border border-neon-purple/40'
                            : 'bg-white/5 border border-white/10 hover:border-white/20'
                        }`}
                      >
                        <div className="text-[10px] font-mono text-gray-500 mb-1">
                          {formatDate(snapshot.created_at)}
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-mono text-gray-300">{snapshot.method}</span>
                          {metrics?.sharpe_ratio !== undefined && (
                            <span className={`text-xs font-mono ${
                              metrics.sharpe_ratio >= 1 ? 'text-neon-green' : 'text-status-warning'
                            }`}>
                              {metrics.sharpe_ratio.toFixed(2)}
                            </span>
                          )}
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}
            </section>

            {/* 对比结果 */}
            {compareResults && compareResults.length >= 2 && (
              <section>
                <h3 className="text-sm font-mono text-gray-400 tracking-widest mb-4">对比结果</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-white/10">
                        <th className="px-3 py-2 text-left text-[10px] font-mono text-gray-500 tracking-wider">指标</th>
                        {compareResults.map((r, idx) => (
                          <th key={r.id} className="px-3 py-2 text-center text-[10px] font-mono text-gray-500 tracking-wider">
                            {idx === 0 ? '基准' : `对比 ${idx}`}
                            <div className="text-gray-600 font-normal mt-0.5">{formatDate(r.created_at)}</div>
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {/* 方法 */}
                      <tr className="border-b border-white/5">
                        <td className="px-3 py-2 text-gray-400">优化方法</td>
                        {compareResults.map(r => (
                          <td key={r.id} className="px-3 py-2 text-center font-mono text-gray-200">{r.method}</td>
                        ))}
                      </tr>
                      {/* 夏普比率 */}
                      <tr className="border-b border-white/5">
                        <td className="px-3 py-2 text-gray-400">夏普比率</td>
                        {compareResults.map((r, idx) => {
                          const value = r.metrics?.sharpe_ratio;
                          const baseline = compareResults[0].metrics?.sharpe_ratio;
                          const change = idx > 0 && value !== undefined && baseline !== undefined
                            ? getChangeIndicator(value, baseline)
                            : null;

                          return (
                            <td key={r.id} className="px-3 py-2 text-center">
                              <span className="font-mono text-gray-200">{value?.toFixed(3) || '-'}</span>
                              {change && (
                                <span className={`ml-2 text-xs ${change.isPositive ? 'text-neon-green' : 'text-status-loss'}`}>
                                  {change.display}
                                </span>
                              )}
                            </td>
                          );
                        })}
                      </tr>
                      {/* 预期收益 */}
                      <tr className="border-b border-white/5">
                        <td className="px-3 py-2 text-gray-400">预期收益</td>
                        {compareResults.map((r, idx) => {
                          const value = r.metrics?.expected_return;
                          const baseline = compareResults[0].metrics?.expected_return;
                          const change = idx > 0 && value !== undefined && baseline !== undefined
                            ? getChangeIndicator(value, baseline)
                            : null;

                          return (
                            <td key={r.id} className="px-3 py-2 text-center">
                              <span className="font-mono text-gray-200">
                                {value !== undefined ? `${(value * 100).toFixed(1)}%` : '-'}
                              </span>
                              {change && (
                                <span className={`ml-2 text-xs ${change.isPositive ? 'text-neon-green' : 'text-status-loss'}`}>
                                  {change.display}
                                </span>
                              )}
                            </td>
                          );
                        })}
                      </tr>
                      {/* 最大回撤 */}
                      <tr className="border-b border-white/5">
                        <td className="px-3 py-2 text-gray-400">最大回撤</td>
                        {compareResults.map((r, idx) => {
                          const value = r.metrics?.max_drawdown;
                          const baseline = compareResults[0].metrics?.max_drawdown;
                          const change = idx > 0 && value !== undefined && baseline !== undefined
                            ? getChangeIndicator(value, baseline)
                            : null;

                          return (
                            <td key={r.id} className="px-3 py-2 text-center">
                              <span className="font-mono text-gray-200">
                                {value !== undefined ? `${(value * 100).toFixed(1)}%` : '-'}
                              </span>
                              {change && (
                                <span className={`ml-2 text-xs ${!change.isPositive ? 'text-neon-green' : 'text-status-loss'}`}>
                                  {change.display}
                                </span>
                              )}
                            </td>
                          );
                        })}
                      </tr>
                    </tbody>
                  </table>
                </div>

                {/* 配置对比 */}
                <div className="mt-4">
                  <h4 className="text-xs font-mono text-gray-500 tracking-widest mb-2">配置差异</h4>
                  <div className="grid grid-cols-3 gap-4">
                    {compareResults.map((r, idx) => (
                      <div key={r.id} className="rounded-lg p-3 border border-white/10">
                        <div className="text-[10px] font-mono text-gray-500 mb-2">
                          {idx === 0 ? '基准配置' : `对比 ${idx}`}
                        </div>
                        <div className="space-y-1">
                          {Object.entries(r.rounded_allocation || r.allocation || {})
                            .sort(([, a], [, b]) => (b as number) - (a as number))
                            .map(([asset, weight]) => (
                              <div key={asset} className="flex items-center justify-between text-xs">
                                <span className="font-mono text-gray-400">{asset}</span>
                                <span className="font-mono text-gray-200">{Math.round((weight as number) * 100)}%</span>
                              </div>
                            ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </section>
            )}
          </div>
        </div>
      </div>
    </div>
  );
});

export default StrategyComparison;

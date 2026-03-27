import { lazy, Suspense } from 'react';
import type { BacktestResult, PortfolioAllocation } from '../../types';

// ============================================
// 图表加载占位符
// ============================================
function ChartSkeleton({ height = 'h-48' }: { height?: string }) {
  return (
    <div className={`${height} w-full flex items-center justify-center bg-gray-50 rounded-lg animate-pulse`}>
      <div className="flex flex-col items-center gap-2 text-gray-400">
        <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        </svg>
        <span className="text-xs">加载图表...</span>
      </div>
    </div>
  );
}

// ============================================
// 懒加载图表组件
// ============================================
const LazyBacktestChart = lazy(() => import('./BacktestChart'));
const LazyAllocationChart = lazy(() => import('./AllocationChart'));
const LazyPriceChart = lazy(() => import('./PriceChart'));

// ============================================
// 带 Suspense 的图表包装器
// ============================================
interface BacktestChartProps {
  data: BacktestResult;
}

export function BacktestChart({ data }: BacktestChartProps) {
  return (
    <Suspense fallback={<ChartSkeleton />}>
      <LazyBacktestChart data={data} />
    </Suspense>
  );
}

interface AllocationChartProps {
  allocation: PortfolioAllocation;
  size?: 'sm' | 'md' | 'lg';
}

export function AllocationChart({ allocation, size }: AllocationChartProps) {
  return (
    <Suspense fallback={<ChartSkeleton height="h-56" />}>
      <LazyAllocationChart allocation={allocation} size={size} />
    </Suspense>
  );
}

interface PriceData {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface PriceChartProps {
  data: PriceData[];
  color?: string;
}

export function PriceChart({ data, color }: PriceChartProps) {
  return (
    <Suspense fallback={<ChartSkeleton />}>
      <LazyPriceChart data={data} color={color} />
    </Suspense>
  );
}

// ============================================
// 懒加载图表 (用于 AssetAllocation)
// ============================================
const LazyTreemapComponent = lazy(() => import('./LazyTreemap'));
const LazyHistoryChartComponent = lazy(() => import('./LazyHistoryChart'));

interface PieChartDataItem {
  name: string;
  ticker: string;
  value: number;
}

interface AssetPieChartProps {
  data: PieChartDataItem[];
  colors: { [key: string]: string };
}

export function AssetPieChart({ data, colors }: AssetPieChartProps) {
  return (
    <Suspense fallback={<ChartSkeleton height="h-56" />}>
      <LazyTreemapComponent data={data} colors={colors} />
    </Suspense>
  );
}

interface HistoryChartProps {
  data: Record<string, any>[];
  activeAssets: string[];
  colors: { [key: string]: string };
  assetNames: { [key: string]: string };
}

export function HistoryChart({ data, activeAssets, colors, assetNames }: HistoryChartProps) {
  return (
    <Suspense fallback={<ChartSkeleton />}>
      <LazyHistoryChartComponent
        data={data}
        activeAssets={activeAssets}
        colors={colors}
        assetNames={assetNames}
      />
    </Suspense>
  );
}

// 预加载函数 - 可在用户交互时调用
export function preloadCharts() {
  import('./BacktestChart');
  import('./AllocationChart');
  import('./PriceChart');
  import('./LazyTreemap');
  import('./LazyHistoryChart');
  import('./TrendChart');
}

// 导出 TrendChart
export { default as TrendChart } from './TrendChart';

import { useCallback } from 'react';
import useSWR, { mutate } from 'swr';
import axios from 'axios';
import type {
  MarketData,
  MarketRegime,
  AIAnalysis,
  Strategy,
  BacktestResult,
  NewsItem,
  DashboardSummary,
  TechnicalAnalysis,
  UserConfig,
  StrategySnapshot,
  TrendResponse,
  AllocationChange
} from '../types';

// ============================================
// API 客户端配置
// ============================================
const api = axios.create({
  baseURL: '/api',
  timeout: 120000  // 2分钟，AI分析需要较长时间
});

// SWR fetcher
const fetcher = async (url: string) => {
  const response = await api.get(url);
  return response.data;
};

// ============================================
// AI 分析状态类型
// ============================================
export interface AIAnalysisStatus {
  has_valid_cache: boolean;
  last_analysis_time: string | null;
  age_minutes: number | null;
  is_expired: boolean;
  max_age_minutes?: number;
  message: string;
}

// ============================================
// 市场数据 Hooks (使用 SWR)
// ============================================
export function useMarketPrices() {
  const { data, error, isLoading, mutate: refresh } = useSWR<{ data: MarketData }>(
    '/market/prices',
    fetcher,
    {
      refreshInterval: 60000,      // 每分钟自动刷新
      dedupingInterval: 5000,      // 5秒内去重
      revalidateOnFocus: false,    // 切换标签不重新请求
    }
  );

  return {
    data: data?.data ?? null,
    loading: isLoading,
    error: error ? 'Failed to fetch market prices' : null,
    refresh
  };
}

export function useMarketRegime() {
  const { data, error, isLoading } = useSWR<{ data: MarketRegime }>(
    '/macro/regime',
    fetcher,
    {
      dedupingInterval: 30000,     // 30秒内去重
      revalidateOnFocus: false,
    }
  );

  return {
    data: data?.data ?? null,
    loading: isLoading,
    error: error ? 'Failed to fetch market regime' : null
  };
}

// ============================================
// AI 分析 Hooks
// ============================================
export function useAIAnalysisStatus() {
  const { data, error, isLoading, mutate: refresh } = useSWR<{ data: AIAnalysisStatus }>(
    '/analysis/status',
    fetcher,
    {
      refreshInterval: 30000,      // 每30秒检查状态
      dedupingInterval: 5000,
      revalidateOnFocus: false,
    }
  );

  const fallbackStatus: AIAnalysisStatus = {
    has_valid_cache: false,
    last_analysis_time: null,
    age_minutes: null,
    is_expired: true,
    message: error ? '无法获取 AI 分析状态' : ''
  };

  return {
    status: data?.data ?? (error ? fallbackStatus : null),
    loading: isLoading,
    refresh
  };
}

export function useAIAnalysis() {
  const { data, error, isLoading, mutate: refreshData } = useSWR<{ data: AIAnalysis }>(
    '/analysis/latest',
    fetcher,
    {
      dedupingInterval: 10000,
      revalidateOnFocus: false,
    }
  );

  const runAnalysis = useCallback(async () => {
    const response = await api.post('/analysis/run');
    // 更新缓存
    refreshData({ data: response.data.data }, false);
    // 同时刷新状态
    mutate('/analysis/status');
    return response.data.data;
  }, [refreshData]);

  return {
    data: data?.data ?? null,
    loading: isLoading,
    error: error ? 'Failed to fetch AI analysis' : null,
    refresh: refreshData,
    runAnalysis
  };
}

// ============================================
// 策略 Hooks
// ============================================
export function useStrategy() {
  const { data, error, isLoading, mutate: refreshData } = useSWR<{ data: Strategy }>(
    '/strategy/current',
    fetcher,
    {
      dedupingInterval: 10000,
      revalidateOnFocus: false,
    }
  );

  const optimize = useCallback(async (
    method = 'max_sharpe',
    useAI = true,
    maxDrawdown?: number,
    targetSharpe?: number
  ) => {
    const response = await api.post('/strategy/optimize', {
      method,
      use_ai_adjustments: useAI,
      max_drawdown: maxDrawdown,
      target_sharpe: targetSharpe
    });
    // 更新本地缓存
    refreshData();
    return response.data.data;
  }, [refreshData]);

  return {
    data: data?.data ?? null,
    loading: isLoading,
    optimizing: false, // 由调用方管理
    error: error ? 'Failed to fetch strategy' : null,
    refresh: refreshData,
    optimize
  };
}

// ============================================
// 回测 Hook (非 SWR，按需调用)
// ============================================
export function useBacktest() {
  const { data, error, isLoading, mutate: setData } = useSWR<BacktestResult>(
    null, // 初始不请求
    null,
    { revalidateOnFocus: false }
  );

  const runBacktest = useCallback(async (
    allocation: { [key: string]: number },
    rebalanceFreq = 'monthly',
    startValue = 100000
  ) => {
    const response = await api.post('/backtest/run', {
      allocation,
      rebalance_freq: rebalanceFreq,
      start_value: startValue
    });
    setData(response.data.data, false);
    return response.data.data;
  }, [setData]);

  return {
    data: data ?? null,
    loading: isLoading,
    error: error ? 'Failed to run backtest' : null,
    runBacktest
  };
}

// ============================================
// 新闻 Hook
// ============================================
export function useNews() {
  const { data, error, isLoading } = useSWR<{ data: NewsItem[] }>(
    '/news/recent',
    fetcher,
    {
      dedupingInterval: 60000,     // 1分钟内去重
      revalidateOnFocus: false,
    }
  );

  return {
    data: data?.data ?? [],
    loading: isLoading,
    error: error ? 'Failed to fetch news' : null
  };
}

// ============================================
// Dashboard 汇总 Hook
// ============================================
export function useDashboardSummary() {
  const { data, error, isLoading, mutate: refresh } = useSWR<{ data: DashboardSummary } | DashboardSummary>(
    '/dashboard/summary',
    fetcher,
    {
      refreshInterval: 15 * 60 * 1000,  // 15分钟自动更新
      dedupingInterval: 30000,
      revalidateOnFocus: false,
    }
  );

  // 兼容两种响应格式
  const summaryData = data ? ('data' in data ? data.data : data) : null;

  return {
    data: summaryData,
    loading: isLoading,
    error: error ? 'Failed to fetch dashboard summary' : null,
    refresh
  };
}

// ============================================
// 技术分析 Hook
// ============================================
export function useTechnicalAnalysis(ticker: string) {
  const { data, error, isLoading } = useSWR<{ analysis: TechnicalAnalysis }>(
    ticker ? `/market/technical/${ticker}` : null,
    fetcher,
    {
      dedupingInterval: 60000,
      revalidateOnFocus: false,
    }
  );

  return {
    data: data?.analysis ?? null,
    loading: isLoading,
    error: error ? `Failed to fetch technical analysis for ${ticker}` : null
  };
}

// ============================================
// 策略历史 Hook
// ============================================
export function useStrategyHistory(days = 30) {
  const { data, error, isLoading } = useSWR<{ data: Array<{
    id: number;
    date: string;
    allocation: { [key: string]: number };
    sharpe_ratio: number;
  }> }>(
    `/strategy/history?days=${days}`,
    fetcher,
    {
      dedupingInterval: 60000,
      revalidateOnFocus: false,
    }
  );

  return {
    data: data?.data ?? [],
    loading: isLoading,
    error: error ? 'Failed to fetch strategy history' : null
  };
}

// ============================================
// 全量更新 (并行请求优化)
// ============================================
export async function triggerFullUpdate() {
  // P0优化: 并行执行系统更新和策略优化
  const [, optimizeResponse] = await Promise.all([
    api.post('/system/update'),
    api.post('/strategy/optimize', {
      method: 'composite',
      use_ai_adjustments: true
    })
  ]);

  // 刷新所有相关缓存
  mutate('/dashboard/summary');
  mutate('/market/prices');
  mutate('/macro/regime');
  mutate('/strategy/current');

  return optimizeResponse.data;
}

// ============================================
// 手动触发更新
// ============================================
export function triggerManualUpdate() {
  return api.post('/system/update');
}

// ============================================
// 全局缓存刷新
// ============================================
export function refreshAllData() {
  mutate('/dashboard/summary');
  mutate('/market/prices');
  mutate('/macro/regime');
  mutate('/strategy/current');
  mutate('/analysis/latest');
  mutate('/analysis/status');
  mutate('/news/recent');
}

// ============================================
// 用户配置 Hooks
// ============================================
export function useUserConfigs() {
  const { data, error, isLoading, mutate: refresh } = useSWR<{ data: UserConfig[] }>(
    '/config/',
    fetcher,
    {
      dedupingInterval: 30000,
      revalidateOnFocus: false,
    }
  );

  return {
    data: data?.data ?? [],
    loading: isLoading,
    error: error ? 'Failed to fetch user configs' : null,
    refresh
  };
}

export function useUserConfig(configId: number | null) {
  const { data, error, isLoading } = useSWR<{ data: UserConfig }>(
    configId ? `/config/${configId}` : null,
    fetcher,
    {
      dedupingInterval: 30000,
      revalidateOnFocus: false,
    }
  );

  return {
    data: data?.data ?? null,
    loading: isLoading,
    error: error ? 'Failed to fetch user config' : null
  };
}

export function useAvailableAssets() {
  const { data, error, isLoading } = useSWR<{ data: { [asset: string]: { name: string; min_weight: number; max_weight: number } } }>(
    '/config/available-assets',
    fetcher,
    {
      dedupingInterval: 60000,
      revalidateOnFocus: false,
    }
  );

  return {
    data: data?.data ?? {},
    loading: isLoading,
    error: error ? 'Failed to fetch available assets' : null
  };
}

export async function createUserConfig(config: Omit<UserConfig, 'id' | 'is_active' | 'created_at' | 'updated_at'>) {
  const response = await api.post('/config/', config);
  mutate('/config/');
  return response.data.data;
}

export async function updateUserConfig(configId: number, updates: Partial<UserConfig>) {
  const response = await api.put(`/config/${configId}`, updates);
  mutate('/config/');
  mutate(`/config/${configId}`);
  return response.data.data;
}

export async function deleteUserConfig(configId: number) {
  const response = await api.delete(`/config/${configId}`);
  mutate('/config/');
  return response.data.data;
}

// ============================================
// 策略快照 Hooks
// ============================================
export function useStrategySnapshots(days = 90) {
  const { data, error, isLoading, mutate: refresh } = useSWR<{ data: StrategySnapshot[] }>(
    `/strategy/snapshots?days=${days}`,
    fetcher,
    {
      dedupingInterval: 30000,
      revalidateOnFocus: false,
    }
  );

  return {
    data: data?.data ?? [],
    loading: isLoading,
    error: error ? 'Failed to fetch strategy snapshots' : null,
    refresh
  };
}

export function useSnapshotDetail(snapshotId: number | null) {
  const { data, error, isLoading } = useSWR<{ data: StrategySnapshot }>(
    snapshotId ? `/strategy/snapshots/${snapshotId}` : null,
    fetcher,
    {
      dedupingInterval: 60000,
      revalidateOnFocus: false,
    }
  );

  return {
    data: data?.data ?? null,
    loading: isLoading,
    error: error ? 'Failed to fetch snapshot detail' : null
  };
}

// ============================================
// 历史趋势 Hooks
// ============================================
export function useHistoryTrend(days = 90) {
  const { data, error, isLoading } = useSWR<TrendResponse>(
    `/strategy/history/trend?days=${days}`,
    fetcher,
    {
      dedupingInterval: 60000,
      revalidateOnFocus: false,
    }
  );

  return {
    data: data?.data ?? [],
    summary: data?.metrics_summary ?? null,
    loading: isLoading,
    error: error ? 'Failed to fetch history trend' : null
  };
}

export function useAllocationChanges(days = 90) {
  const { data, error, isLoading } = useSWR<{ data: AllocationChange[]; summary: { total_changes: number; period_days: number } }>(
    `/strategy/history/allocation-changes?days=${days}`,
    fetcher,
    {
      dedupingInterval: 60000,
      revalidateOnFocus: false,
    }
  );

  return {
    data: data?.data ?? [],
    summary: data?.summary ?? null,
    loading: isLoading,
    error: error ? 'Failed to fetch allocation changes' : null
  };
}

export async function compareSnapshots(snapshotIds: number[]) {
  const response = await api.post('/strategy/history/compare', { snapshot_ids: snapshotIds });
  return response.data.data;
}

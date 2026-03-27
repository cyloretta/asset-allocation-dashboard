import { useState, useEffect, useRef, useCallback, useMemo, memo } from 'react';
import { RefreshCw, TrendingUp, Activity, PieChart, Brain, Newspaper, Settings, Clock, Zap, Sliders, GitCompare } from 'lucide-react';
import MarketOverview from './MarketOverview';
import MacroAnalysis from './MacroAnalysis';
import AssetAllocation from './AssetAllocation';
import StrategyPanel, { StrategyPanelRef } from './StrategyPanel';
import AIAnalysisPanel from './AIAnalysisPanel';
import NewsPanel from './NewsPanel';
import ConfigPanel from './ConfigPanel';
import StrategyComparison from './StrategyComparison';
import { useDashboardSummary, triggerFullUpdate, useAIAnalysis, useAIAnalysisStatus } from '../hooks/useApi';
import type { PlanCData } from '../types';

// ============================================
// Cyber Theme: Section Header 组件
// ============================================
interface SectionHeaderProps {
  icon: React.ReactNode;
  title: string;
  accentColor?: 'cyan' | 'green' | 'purple' | 'pink' | 'orange';
  children?: React.ReactNode;
}

const SectionHeader = memo(function SectionHeader({
  icon, title, accentColor = 'cyan', children
}: SectionHeaderProps) {
  const accentStyles = {
    cyan: 'from-neon-cyan/20 to-neon-blue/20 border-neon-cyan/30 shadow-neon-cyan',
    green: 'from-neon-green/20 to-emerald-500/20 border-neon-green/30 shadow-neon-green',
    purple: 'from-neon-purple/20 to-violet-500/20 border-neon-purple/30 shadow-neon-purple',
    pink: 'from-neon-pink/20 to-rose-500/20 border-neon-pink/30 shadow-neon-pink',
    orange: 'from-neon-orange/20 to-amber-500/20 border-neon-orange/30',
  };

  const iconColors = {
    cyan: 'text-neon-cyan',
    green: 'text-neon-green',
    purple: 'text-neon-purple',
    pink: 'text-neon-pink',
    orange: 'text-neon-orange',
  };

  return (
    <div className="flex items-center gap-4 mb-5">
      <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${accentStyles[accentColor]} border flex items-center justify-center`}>
        <span className={iconColors[accentColor]} style={{ filter: `drop-shadow(0 0 6px currentColor)` }}>
          {icon}
        </span>
      </div>
      <h2 className="text-lg font-display font-semibold text-gray-100 tracking-tight">{title}</h2>
      {children}
    </div>
  );
});

// ============================================
// Cyber Loading Spinner
// ============================================
const LoadingSpinner = memo(function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center h-64">
      <div className="relative">
        {/* Outer ring */}
        <div className="w-16 h-16 rounded-full border-2 border-neon-cyan/20 animate-spin"
             style={{ animationDuration: '3s' }}>
          <div className="absolute top-0 left-1/2 w-2 h-2 -ml-1 -mt-1 bg-neon-cyan rounded-full shadow-neon-cyan"></div>
        </div>
        {/* Inner ring */}
        <div className="absolute inset-2 rounded-full border-2 border-neon-purple/20 animate-spin"
             style={{ animationDirection: 'reverse', animationDuration: '2s' }}>
          <div className="absolute bottom-0 left-1/2 w-1.5 h-1.5 -ml-0.5 mb-0 bg-neon-purple rounded-full"></div>
        </div>
        {/* Center dot */}
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="w-2 h-2 bg-neon-cyan rounded-full animate-pulse shadow-neon-cyan"></div>
        </div>
      </div>
      <div className="ml-6">
        <p className="text-neon-cyan font-mono text-sm tracking-wider">LOADING</p>
        <p className="text-gray-500 text-xs mt-1">Initializing data streams...</p>
      </div>
    </div>
  );
});

// ============================================
// Main Dashboard Component
// ============================================
export default function Dashboard() {
  const { data, loading, refresh } = useDashboardSummary();
  const { runAnalysis } = useAIAnalysis();
  const { status: aiStatus, refresh: refreshAIStatus } = useAIAnalysisStatus();
  const [updating, setUpdating] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [optimizing, setOptimizing] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [countdown, setCountdown] = useState(60);
  const [aiAnalysisData, setAiAnalysisData] = useState<any>(null);
  const [planCData, setPlanCData] = useState<PlanCData | null>(null);
  const [showConfigPanel, setShowConfigPanel] = useState(false);
  const [showComparison, setShowComparison] = useState(false);
  const strategyPanelRef = useRef<StrategyPanelRef>(null);

  const hasValidAI = useMemo(() => aiStatus?.has_valid_cache ?? false, [aiStatus?.has_valid_cache]);

  const lastOptimizeDate = useMemo(() => {
    if (!data?.strategy?.date) return null;
    return new Date(data.strategy.date).toLocaleString('zh-CN', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }, [data?.strategy?.date]);

  const aiStatusText = useMemo(() => {
    if (!hasValidAI) return '请先运行 AI 分析';
    const age = aiStatus?.age_minutes;
    if (age != null) {
      return age < 60 ? `可用 · ${Math.round(age)}分钟前` : `可用 · ${Math.round(age / 60)}小时前`;
    }
    return 'AI 分析可用';
  }, [hasValidAI, aiStatus?.age_minutes]);

  const handleOptimize = useCallback(async () => {
    if (!strategyPanelRef.current) return;
    setOptimizing(true);
    try {
      const planC = await strategyPanelRef.current.optimize();
      setPlanCData(planC);
    } finally {
      setOptimizing(false);
    }
  }, []);

  const handleRunAnalysis = useCallback(async () => {
    setAnalyzing(true);
    try {
      const result = await runAnalysis();
      setAiAnalysisData(result);
      refreshAIStatus();
    } catch (err) {
      console.error('Analysis failed:', err);
    } finally {
      setAnalyzing(false);
    }
  }, [runAnalysis, refreshAIStatus]);

  const handleManualUpdate = useCallback(async () => {
    setUpdating(true);
    try {
      await triggerFullUpdate();
      await refresh();
    } catch (err) {
      console.error('Update failed:', err);
    } finally {
      setUpdating(false);
    }
  }, [refresh]);

  const toggleAutoRefresh = useCallback(() => {
    setAutoRefresh(prev => !prev);
  }, []);

  useEffect(() => {
    if (!autoRefresh) {
      setCountdown(60);
      return;
    }
    const timer = setInterval(() => {
      setCountdown(prev => {
        if (prev <= 1) {
          refresh();
          return 60;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [autoRefresh, refresh]);

  const effectivePlanCData = useMemo(
    () => planCData || data?.strategy?.plan_c,
    [planCData, data?.strategy?.plan_c]
  );

  return (
    <div className="min-h-screen relative">
      {/* Background grid overlay */}
      <div className="fixed inset-0 pointer-events-none opacity-30">
        <div className="absolute inset-0" style={{
          backgroundImage: `radial-gradient(ellipse at 20% 0%, rgba(0, 245, 255, 0.08) 0%, transparent 50%),
                           radial-gradient(ellipse at 80% 100%, rgba(168, 85, 247, 0.06) 0%, transparent 50%)`
        }}></div>
      </div>

      <div className="container mx-auto px-4 py-6 max-w-7xl relative z-10">
        {/* ============================================
            Cyber Header
            ============================================ */}
        <header className="mb-8">
          <div className="card-elevated">
            <div className="flex items-center justify-between">
              {/* Logo & Title */}
              <div className="flex items-center gap-5">
                <div className="relative">
                  <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-neon-cyan/20 to-neon-purple/20 border border-neon-cyan/40 flex items-center justify-center">
                    <Zap className="w-7 h-7 text-neon-cyan" style={{ filter: 'drop-shadow(0 0 8px rgba(0, 245, 255, 0.6))' }} />
                  </div>
                  {/* Pulse indicator */}
                  <div className="absolute -top-1 -right-1 w-3 h-3">
                    <div className="absolute inset-0 bg-neon-green rounded-full animate-ping opacity-75"></div>
                    <div className="absolute inset-0 bg-neon-green rounded-full shadow-neon-green"></div>
                  </div>
                </div>
                <div>
                  <h1 className="text-2xl font-display font-bold text-gradient tracking-tight">
                    智能资产配置
                  </h1>
                  <p className="text-gray-500 text-sm font-mono tracking-wider mt-0.5">
                    AI 驱动的投资组合策略
                  </p>
                </div>
              </div>

              {/* Controls */}
              <div className="flex items-center gap-4">
                {/* Last update time */}
                {lastOptimizeDate ? (
                  <div className="text-right hidden md:block">
                    <p className="text-[10px] text-gray-600 uppercase tracking-widest font-mono">上次同步</p>
                    <p className="text-sm text-neon-cyan font-mono">{lastOptimizeDate}</p>
                  </div>
                ) : null}

                {/* Auto refresh toggle */}
                <button
                  onClick={toggleAutoRefresh}
                  className={`flex items-center gap-2 px-4 py-2.5 rounded-lg font-mono text-sm transition-all ${
                    autoRefresh
                      ? 'bg-neon-green/10 text-neon-green border border-neon-green/40'
                      : 'bg-white/5 text-gray-500 border border-white/10 hover:border-white/20'
                  }`}
                >
                  <Clock className={`w-4 h-4 ${autoRefresh ? 'animate-pulse' : ''}`} />
                  {autoRefresh ? (
                    <span className="tabular-nums">{String(countdown).padStart(2, '0')}秒</span>
                  ) : (
                    <span>自动</span>
                  )}
                </button>

                {/* Config button */}
                <button
                  onClick={() => setShowConfigPanel(true)}
                  className="flex items-center gap-2 px-3 py-2 rounded-lg font-mono text-sm bg-white/5 text-gray-400 border border-white/10 hover:border-neon-purple/40 hover:text-neon-purple transition-all"
                >
                  <Sliders className="w-4 h-4" />
                  <span>配置</span>
                </button>

                {/* History comparison button */}
                <button
                  onClick={() => setShowComparison(true)}
                  className="flex items-center gap-2 px-3 py-2 rounded-lg font-mono text-sm bg-white/5 text-gray-400 border border-white/10 hover:border-neon-cyan/40 hover:text-neon-cyan transition-all"
                >
                  <GitCompare className="w-4 h-4" />
                  <span>对比</span>
                </button>

                {/* Sync button */}
                <button
                  onClick={handleManualUpdate}
                  disabled={updating}
                  className="btn-primary flex items-center gap-2"
                >
                  <RefreshCw className={`w-4 h-4 ${updating ? 'animate-spin' : ''}`} />
                  <span className="font-mono text-sm">{updating ? '同步中...' : '全量同步'}</span>
                </button>
              </div>
            </div>
          </div>
        </header>

        {loading && !data ? (
          <LoadingSpinner />
        ) : (
          <div className="space-y-6">
            {/* ============================================
                Row 1: Market Overview
                ============================================ */}
            <section className="card-elevated corner-accent">
              <SectionHeader
                icon={<TrendingUp className="w-5 h-5" />}
                title="市场概览"
                accentColor="cyan"
              />
              <MarketOverview data={data?.market} />
            </section>

            {/* ============================================
                Row 2: Macro & AI Analysis
                ============================================ */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <section className="card-elevated">
                <SectionHeader
                  icon={<Activity className="w-5 h-5" />}
                  title="宏观环境"
                  accentColor="green"
                />
                <MacroAnalysis data={data?.macro} />
              </section>

              <section className="card-elevated">
                <SectionHeader
                  icon={<Brain className="w-5 h-5" />}
                  title="AI 分析"
                  accentColor="purple"
                >
                  <button
                    onClick={handleRunAnalysis}
                    disabled={analyzing}
                    className="ml-2 flex items-center gap-2 px-3 py-1.5 text-xs font-mono rounded-lg bg-neon-purple/10 text-neon-purple border border-neon-purple/30 hover:border-neon-purple/50 transition-all disabled:opacity-50"
                  >
                    <RefreshCw className={`w-3 h-3 ${analyzing ? 'animate-spin' : ''}`} />
                    {analyzing ? '运行中' : '运行'}
                  </button>
                  <span className="ml-auto px-3 py-1 text-[10px] font-mono tracking-widest rounded-full bg-neon-purple/10 text-neon-purple border border-neon-purple/20">
                    DEEPSEEK
                  </span>
                </SectionHeader>
                <AIAnalysisPanel externalData={aiAnalysisData} />
              </section>
            </div>

            {/* ============================================
                Row 3: Strategy & Allocation
                ============================================ */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <section className="card-elevated">
                <SectionHeader
                  icon={<Settings className="w-5 h-5" />}
                  title="策略优化"
                  accentColor="orange"
                >
                  <button
                    onClick={handleOptimize}
                    disabled={optimizing || !hasValidAI}
                    className={`ml-2 flex items-center gap-2 px-3 py-1.5 text-xs font-mono rounded-lg transition-all disabled:opacity-50 ${
                      hasValidAI
                        ? 'bg-neon-orange/10 text-neon-orange border border-neon-orange/30 hover:border-neon-orange/50'
                        : 'bg-white/5 text-gray-600 border border-white/10 cursor-not-allowed'
                    }`}
                    title={!hasValidAI ? '请先运行 AI 分析' : ''}
                  >
                    <RefreshCw className={`w-3 h-3 ${optimizing ? 'animate-spin' : ''}`} />
                    {optimizing ? '优化中' : '优化'}
                  </button>
                  {/* AI Status indicator */}
                  <div className={`ml-auto flex items-center gap-2 px-3 py-1.5 rounded-full text-[10px] font-mono tracking-widest ${
                    hasValidAI
                      ? 'bg-neon-green/10 text-neon-green border border-neon-green/30'
                      : 'bg-status-warning/10 text-status-warning border border-status-warning/30'
                  }`}>
                    <div className={`w-1.5 h-1.5 rounded-full ${hasValidAI ? 'bg-neon-green animate-pulse' : 'bg-status-warning'}`}></div>
                    <span>{aiStatusText}</span>
                  </div>
                </SectionHeader>
                <StrategyPanel ref={strategyPanelRef} strategy={data?.strategy} onOptimized={refresh} />
              </section>

              <section className="card-elevated">
                <SectionHeader
                  icon={<PieChart className="w-5 h-5" />}
                  title="配置方案"
                  accentColor="pink"
                >
                  {data?.strategy?.sharpe_ratio ? (
                    <span className={`ml-auto px-3 py-1.5 text-xs font-mono rounded-lg ${
                      data.strategy.sharpe_ratio >= 1
                        ? 'bg-neon-green/10 text-neon-green border border-neon-green/30'
                        : 'bg-status-warning/10 text-status-warning border border-status-warning/30'
                    }`}>
                      SHARPE {data.strategy.sharpe_ratio.toFixed(2)}
                    </span>
                  ) : null}
                </SectionHeader>
                <AssetAllocation allocation={data?.strategy?.allocation} planCData={effectivePlanCData} />
              </section>
            </div>

            {/* ============================================
                Row 4: News Feed
                ============================================ */}
            <section className="card-elevated">
              <SectionHeader
                icon={<Newspaper className="w-5 h-5" />}
                title="市场资讯"
                accentColor="cyan"
              />
              <NewsPanel />
            </section>
          </div>
        )}

        {/* ============================================
            Footer
            ============================================ */}
        <footer className="mt-10 py-6 border-t border-white/5">
          <div className="flex items-center justify-between text-xs text-gray-600 font-mono">
            <p>数据源: STOOQ · COINGECKO · TREASURY.GOV · RSS</p>
            <p className="flex items-center gap-2">
              <span className="w-1.5 h-1.5 bg-neon-green rounded-full animate-pulse"></span>
              系统运行正常
            </p>
          </div>
        </footer>
      </div>

      {/* Modals */}
      <ConfigPanel isOpen={showConfigPanel} onClose={() => setShowConfigPanel(false)} />
      <StrategyComparison isOpen={showComparison} onClose={() => setShowComparison(false)} />
    </div>
  );
}

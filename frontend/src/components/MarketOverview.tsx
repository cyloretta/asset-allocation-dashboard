import { memo } from 'react';
import { TrendingUp, TrendingDown } from 'lucide-react';
import type { MarketData } from '../types';

interface Props {
  data: MarketData | null | undefined;
}

// Asset configuration with cyber theme colors
const ASSET_CONFIG: { [key: string]: { name: string; symbol: string; icon: string } } = {
  'SPY': { name: 'S&P 500', symbol: 'SPY', icon: '📈' },
  'QQQ': { name: 'NASDAQ', symbol: 'QQQ', icon: '💻' },
  'GLD': { name: 'GOLD', symbol: 'GLD', icon: '🥇' },
  'BTC-USD': { name: 'BITCOIN', symbol: 'BTC', icon: '₿' },
  'TLT': { name: 'TREASURY', symbol: 'TLT', icon: '🏛️' },
  'CASH': { name: 'CASH', symbol: 'USD', icon: '💵' },
};

interface AssetCardProps {
  ticker: string;
  price: number;
  change: number;
  date?: string;
  is_mock?: boolean;
}

const AssetCard = memo(function AssetCard({ ticker, price, change, date, is_mock }: AssetCardProps) {
  const config = ASSET_CONFIG[ticker] || { name: ticker, symbol: ticker, icon: '📊' };
  const isPositive = change >= 0;

  return (
    <div className="group relative rounded-xl p-4 transition-all duration-300 hover:scale-[1.02]"
         style={{
           background: 'linear-gradient(135deg, rgba(0, 245, 255, 0.03) 0%, rgba(168, 85, 247, 0.02) 100%)',
           border: '1px solid rgba(0, 245, 255, 0.1)',
         }}>
      {/* Hover glow effect */}
      <div className="absolute inset-0 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity duration-300"
           style={{
             background: 'radial-gradient(ellipse at center, rgba(0, 245, 255, 0.05) 0%, transparent 70%)',
           }}></div>

      {/* Top row: Icon & Symbol */}
      <div className="relative flex items-center justify-between mb-3">
        <span className="text-xl">{config.icon}</span>
        <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold tracking-widest ${
          isPositive
            ? 'bg-neon-green/10 text-neon-green border border-neon-green/30'
            : 'bg-status-loss/10 text-status-loss border border-status-loss/30'
        }`}>
          {config.symbol}
        </span>
      </div>

      {/* Price */}
      <div className="relative font-mono text-xl font-bold text-gray-100 tracking-tight">
        <span className="text-gray-500 text-sm">$</span>
        {price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
      </div>

      {/* Change indicator */}
      <div className="relative flex items-center gap-1.5 mt-2">
        {isPositive ? (
          <TrendingUp className="w-4 h-4 text-neon-green" />
        ) : (
          <TrendingDown className="w-4 h-4 text-status-loss" />
        )}
        <span className={`font-mono text-sm font-semibold ${
          isPositive ? 'text-neon-green' : 'text-status-loss'
        }`} style={{ textShadow: isPositive ? '0 0 10px rgba(0, 255, 136, 0.4)' : '0 0 10px rgba(255, 51, 102, 0.4)' }}>
          {isPositive ? '+' : ''}{change.toFixed(2)}%
        </span>
      </div>

      {/* Asset name & status */}
      <div className="relative mt-3 pt-3 border-t border-white/5">
        <p className="text-[10px] text-gray-500 font-mono tracking-widest">{config.name}</p>
        <div className="flex items-center gap-2 mt-1">
          {date ? (
            <span className="text-[9px] text-gray-600 font-mono">{date}</span>
          ) : null}
          {is_mock ? (
            <span className="text-[9px] text-status-warning font-mono">模拟数据</span>
          ) : null}
        </div>
      </div>

      {/* Left accent bar */}
      <div className={`absolute left-0 top-4 bottom-4 w-[2px] rounded-full ${
        isPositive ? 'bg-neon-green' : 'bg-status-loss'
      }`} style={{ boxShadow: isPositive ? '0 0 8px rgba(0, 255, 136, 0.5)' : '0 0 8px rgba(255, 51, 102, 0.5)' }}></div>
    </div>
  );
});

const MarketOverview = memo(function MarketOverview({ data }: Props) {
  if (!data) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-neon-cyan/30 border-t-neon-cyan rounded-full animate-spin mx-auto mb-3"></div>
          <p className="text-gray-500 font-mono text-sm">加载市场数据中...</p>
        </div>
      </div>
    );
  }

  const assets = Object.entries(data).filter(([ticker]) => ticker !== 'CASH');

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
      {assets.map(([ticker, info]) => (
        <AssetCard
          key={ticker}
          ticker={ticker}
          price={info.price}
          change={info.change}
          date={info.date}
          is_mock={info.is_mock}
        />
      ))}
    </div>
  );
});

export default MarketOverview;

import { useState, useRef, useCallback, memo } from 'react';
import { RefreshCw } from 'lucide-react';

interface PullToRefreshProps {
  onRefresh: () => Promise<void>;
  children: React.ReactNode;
  disabled?: boolean;
}

const PullToRefresh = memo(function PullToRefresh({ onRefresh, children, disabled }: PullToRefreshProps) {
  const [pulling, setPulling] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [pullDistance, setPullDistance] = useState(0);
  const startYRef = useRef(0);
  const containerRef = useRef<HTMLDivElement>(null);

  const THRESHOLD = 80;
  const MAX_PULL = 120;

  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    if (disabled || refreshing) return;
    if (containerRef.current && containerRef.current.scrollTop === 0) {
      startYRef.current = e.touches[0].clientY;
      setPulling(true);
    }
  }, [disabled, refreshing]);

  const handleTouchMove = useCallback((e: React.TouchEvent) => {
    if (!pulling || disabled || refreshing) return;

    const currentY = e.touches[0].clientY;
    const diff = currentY - startYRef.current;

    if (diff > 0) {
      // Apply resistance
      const resistance = Math.min(diff * 0.5, MAX_PULL);
      setPullDistance(resistance);
    }
  }, [pulling, disabled, refreshing]);

  const handleTouchEnd = useCallback(async () => {
    if (!pulling || disabled) return;

    setPulling(false);

    if (pullDistance >= THRESHOLD && !refreshing) {
      setRefreshing(true);
      setPullDistance(60);

      try {
        await onRefresh();
      } finally {
        setRefreshing(false);
        setPullDistance(0);
      }
    } else {
      setPullDistance(0);
    }
  }, [pulling, pullDistance, refreshing, onRefresh, disabled]);

  const progress = Math.min(pullDistance / THRESHOLD, 1);
  const rotation = progress * 180;

  return (
    <div
      ref={containerRef}
      onTouchStart={handleTouchStart}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleTouchEnd}
      className="relative overflow-auto"
    >
      {/* Pull indicator */}
      <div
        className="absolute left-0 right-0 flex items-center justify-center transition-transform duration-200 pointer-events-none z-10"
        style={{
          transform: `translateY(${pullDistance - 50}px)`,
          opacity: pullDistance > 10 ? 1 : 0,
        }}
      >
        <div className={`w-10 h-10 rounded-full bg-cyber-base border border-neon-cyan/30 flex items-center justify-center ${
          refreshing ? 'animate-pulse' : ''
        }`}
             style={{ boxShadow: '0 0 20px rgba(0, 245, 255, 0.3)' }}>
          <RefreshCw
            className={`w-5 h-5 text-neon-cyan ${refreshing ? 'animate-spin' : ''}`}
            style={{ transform: refreshing ? 'none' : `rotate(${rotation}deg)` }}
          />
        </div>
      </div>

      {/* Pull hint text */}
      {pullDistance > 10 && !refreshing ? (
        <div
          className="absolute left-0 right-0 text-center transition-opacity duration-200 pointer-events-none z-10"
          style={{
            transform: `translateY(${pullDistance + 5}px)`,
            opacity: pullDistance > 20 ? 0.7 : 0,
          }}
        >
          <span className="text-[10px] font-mono text-gray-500">
            {pullDistance >= THRESHOLD ? '松开刷新' : '下拉刷新'}
          </span>
        </div>
      ) : null}

      {/* Content */}
      <div
        style={{
          transform: `translateY(${pullDistance}px)`,
          transition: pulling ? 'none' : 'transform 0.3s ease-out',
        }}
      >
        {children}
      </div>
    </div>
  );
});

export default PullToRefresh;

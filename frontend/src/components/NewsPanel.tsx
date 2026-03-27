import { memo } from 'react';
import { ExternalLink, Clock } from 'lucide-react';
import { useNews } from '../hooks/useApi';
import { formatDistanceToNow } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import type { NewsItem } from '../types';

// Static JSX hoisting with cyber colors
const ExternalLinkIcon = <ExternalLink className="w-4 h-4 text-gray-500 flex-shrink-0 group-hover:text-neon-cyan transition-colors" />;
const ClockIcon = <Clock className="w-3 h-3" />;

interface NewsCardProps {
  item: NewsItem;
}

const NewsCard = memo(function NewsCard({ item }: NewsCardProps) {
  return (
    <a
      href={item.url}
      target="_blank"
      rel="noopener noreferrer"
      className="group block p-4 rounded-xl transition-all duration-300 hover:scale-[1.02] border border-white/5 hover:border-neon-cyan/30"
      style={{
        background: 'linear-gradient(135deg, rgba(0, 245, 255, 0.02) 0%, rgba(168, 85, 247, 0.01) 100%)',
        contentVisibility: 'auto',
        containIntrinsicSize: '0 140px'
      }}
    >
      {/* Hover glow effect */}
      <div className="absolute inset-0 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none"
           style={{ background: 'radial-gradient(ellipse at center, rgba(0, 245, 255, 0.03) 0%, transparent 70%)' }}></div>

      <div className="relative">
        <div className="flex items-start justify-between gap-2 mb-2">
          <h4 className="text-sm font-medium text-gray-200 line-clamp-2 group-hover:text-neon-cyan transition-colors">
            {item.title_zh || item.title}
          </h4>
          {ExternalLinkIcon}
        </div>

        <p className="text-xs text-gray-500 line-clamp-2 mb-3">{item.summary}</p>

        <div className="flex items-center justify-between text-[10px] font-mono">
          <span className="px-2 py-0.5 rounded bg-white/5 text-gray-400 border border-white/10">
            {item.source}
          </span>
          <span className="flex items-center gap-1 text-gray-500">
            {ClockIcon}
            {formatDistanceToNow(new Date(item.published_at), { addSuffix: true, locale: zhCN })}
          </span>
        </div>

        {item.relevance_score > 0.5 ? (
          <div className="mt-3">
            <div className="w-full bg-white/5 rounded-full h-1">
              <div
                className="h-1 rounded-full bg-neon-cyan transition-all"
                style={{
                  width: `${item.relevance_score * 100}%`,
                  boxShadow: '0 0 8px rgba(0, 245, 255, 0.5)'
                }}
              />
            </div>
          </div>
        ) : null}
      </div>
    </a>
  );
});

const NewsPanel = memo(function NewsPanel() {
  const { data: news, loading, error } = useNews();

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="w-6 h-6 border-2 border-neon-cyan/30 border-t-neon-cyan rounded-full animate-spin"></div>
        <span className="ml-3 text-gray-500 font-mono text-sm">加载资讯中...</span>
      </div>
    );
  }

  if (error || !news.length) {
    return (
      <div className="text-center py-8">
        <p className="text-gray-500 font-mono text-sm">{error || '暂无最新资讯'}</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {news.slice(0, 9).map((item, index) => (
        <NewsCard key={item.url || index} item={item} />
      ))}
    </div>
  );
});

export default NewsPanel;

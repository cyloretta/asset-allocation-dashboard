import { useState, memo } from 'react';
import { Brain, AlertTriangle, Lightbulb, RefreshCw, Shield, TrendingDown, Users } from 'lucide-react';
import { useMasterPerspectives, type MasterPerspectives as MasterPerspectivesType } from '../hooks/useApi';

// ============================================
// 大师头像组件
// ============================================
const MasterAvatar = memo(function MasterAvatar({
  name,
  color
}: {
  name: 'taleb' | 'munger';
  color: string;
}) {
  const initials = name === 'taleb' ? 'NT' : 'CM';
  const title = name === 'taleb' ? '纳西姆·塔勒布' : '查理·芒格';

  return (
    <div className="flex items-center gap-3">
      <div
        className={`w-12 h-12 rounded-xl flex items-center justify-center text-lg font-bold border`}
        style={{
          backgroundColor: `${color}15`,
          borderColor: `${color}40`,
          color: color
        }}
      >
        {initials}
      </div>
      <div>
        <h4 className="text-gray-100 font-semibold">{title}</h4>
        <p className="text-xs text-gray-500">
          {name === 'taleb' ? '反脆弱 · 尾部风险' : '逆向思考 · 认知偏误'}
        </p>
      </div>
    </div>
  );
});

// ============================================
// 裁决徽章组件
// ============================================
const VerdictBadge = memo(function VerdictBadge({
  verdict,
  score,
  type
}: {
  verdict: string;
  score: number;
  type: 'taleb' | 'munger';
}) {
  const getColor = () => {
    if (type === 'taleb') {
      if (verdict === '反脆弱') return 'text-neon-green border-neon-green/40 bg-neon-green/10';
      if (verdict === '脆弱') return 'text-red-400 border-red-400/40 bg-red-400/10';
      return 'text-yellow-400 border-yellow-400/40 bg-yellow-400/10';
    } else {
      if (verdict === '明智') return 'text-neon-green border-neon-green/40 bg-neon-green/10';
      if (verdict === '愚蠢') return 'text-red-400 border-red-400/40 bg-red-400/10';
      return 'text-yellow-400 border-yellow-400/40 bg-yellow-400/10';
    }
  };

  return (
    <div className="flex items-center gap-3">
      <span className={`px-3 py-1 rounded-lg border text-sm font-mono ${getColor()}`}>
        {verdict}
      </span>
      <span className="text-gray-500 text-sm font-mono">
        {type === 'taleb' ? `风险 ${score}` : `信心 ${score}`}
      </span>
    </div>
  );
});

// ============================================
// 关注点列表组件
// ============================================
const ConcernsList = memo(function ConcernsList({
  items,
  icon: Icon,
  color
}: {
  items: string[];
  icon: React.ElementType;
  color: string;
}) {
  return (
    <ul className="space-y-2 mt-3">
      {items.map((item, i) => (
        <li key={i} className="flex items-start gap-2 text-sm text-gray-300">
          <Icon className="w-4 h-4 mt-0.5 flex-shrink-0" style={{ color }} />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
});

// ============================================
// 塔勒布面板
// ============================================
const TalebPanel = memo(function TalebPanel({ data }: { data: MasterPerspectivesType['taleb'] }) {
  const color = '#ff6b6b';

  return (
    <div className="card-cyber p-5 border-l-4" style={{ borderLeftColor: color }}>
      <div className="flex items-start justify-between mb-4">
        <MasterAvatar name="taleb" color={color} />
        <VerdictBadge verdict={data.verdict} score={data.risk_score} type="taleb" />
      </div>

      <div className="space-y-4">
        {/* 分析内容 */}
        <div className="bg-black/30 rounded-lg p-4 border border-white/5">
          <p className="text-gray-300 text-sm leading-relaxed italic">
            "{data.analysis}"
          </p>
        </div>

        {/* 关注点 */}
        <div>
          <h5 className="text-xs text-gray-500 uppercase tracking-wider mb-2 flex items-center gap-2">
            <AlertTriangle className="w-3 h-3" style={{ color }} />
            尾部风险关注
          </h5>
          <ConcernsList items={data.key_concerns} icon={Shield} color={color} />
        </div>

        {/* 杠铃建议 */}
        {data.barbell_suggestion && (
          <div className="bg-gradient-to-r from-red-500/5 to-transparent rounded-lg p-3 border border-red-500/20">
            <h5 className="text-xs text-red-400 uppercase tracking-wider mb-1 flex items-center gap-2">
              <TrendingDown className="w-3 h-3" />
              杠铃策略建议
            </h5>
            <p className="text-sm text-gray-300">{data.barbell_suggestion}</p>
          </div>
        )}
      </div>
    </div>
  );
});

// ============================================
// 芒格面板
// ============================================
const MungerPanel = memo(function MungerPanel({ data }: { data: MasterPerspectivesType['munger'] }) {
  const color = '#ffd93d';

  return (
    <div className="card-cyber p-5 border-l-4" style={{ borderLeftColor: color }}>
      <div className="flex items-start justify-between mb-4">
        <MasterAvatar name="munger" color={color} />
        <VerdictBadge verdict={data.verdict} score={data.confidence} type="munger" />
      </div>

      <div className="space-y-4">
        {/* 分析内容 */}
        <div className="bg-black/30 rounded-lg p-4 border border-white/5">
          <p className="text-gray-300 text-sm leading-relaxed italic">
            "{data.analysis}"
          </p>
        </div>

        {/* 认知偏误 */}
        <div>
          <h5 className="text-xs text-gray-500 uppercase tracking-wider mb-2 flex items-center gap-2">
            <Brain className="w-3 h-3" style={{ color }} />
            可能存在的认知偏误
          </h5>
          <ConcernsList items={data.cognitive_biases} icon={AlertTriangle} color={color} />
        </div>

        {/* 逆向思考 */}
        {data.inversion && (
          <div className="bg-gradient-to-r from-yellow-500/5 to-transparent rounded-lg p-3 border border-yellow-500/20">
            <h5 className="text-xs text-yellow-400 uppercase tracking-wider mb-1 flex items-center gap-2">
              <Lightbulb className="w-3 h-3" />
              逆向思考
            </h5>
            <p className="text-sm text-gray-300">{data.inversion}</p>
          </div>
        )}
      </div>
    </div>
  );
});

// ============================================
// 共识面板
// ============================================
const ConsensusPanel = memo(function ConsensusPanel({ data }: { data: MasterPerspectivesType['consensus'] }) {
  return (
    <div className="card-cyber p-5 bg-gradient-to-br from-neon-cyan/5 to-neon-purple/5 border-neon-cyan/20">
      <h4 className="text-gray-100 font-semibold mb-4 flex items-center gap-2">
        <Users className="w-5 h-5 text-neon-cyan" />
        大师共识
      </h4>

      <div className="grid md:grid-cols-2 gap-4 mb-4">
        {/* 共同观点 */}
        <div>
          <h5 className="text-xs text-neon-green uppercase tracking-wider mb-2">两位都同意</h5>
          <ul className="space-y-1">
            {data.agree_on.map((item, i) => (
              <li key={i} className="text-sm text-gray-300 flex items-start gap-2">
                <span className="text-neon-green">✓</span>
                {item}
              </li>
            ))}
          </ul>
        </div>

        {/* 分歧观点 */}
        <div>
          <h5 className="text-xs text-yellow-400 uppercase tracking-wider mb-2">观点分歧</h5>
          <ul className="space-y-1">
            {data.disagree_on.map((item, i) => (
              <li key={i} className="text-sm text-gray-300 flex items-start gap-2">
                <span className="text-yellow-400">⟷</span>
                {item}
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* 最终建议 */}
      <div className="bg-black/40 rounded-lg p-4 border border-neon-cyan/20">
        <h5 className="text-xs text-neon-cyan uppercase tracking-wider mb-2">综合建议</h5>
        <p className="text-gray-200 font-medium">{data.final_advice}</p>
      </div>
    </div>
  );
});

// ============================================
// 主组件
// ============================================
export default function MasterPerspectives() {
  const { data, loading, error, fetchPerspectives } = useMasterPerspectives();
  const [isRefreshing, setIsRefreshing] = useState(false);

  const handleFetch = async () => {
    setIsRefreshing(true);
    try {
      await fetchPerspectives();
    } finally {
      setIsRefreshing(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Header with action button */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-gray-500 text-sm">
            用塔勒布和芒格的思维框架审视当前资产配置
          </p>
        </div>
        <button
          onClick={handleFetch}
          disabled={loading || isRefreshing}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg font-mono text-sm transition-all ${
            loading || isRefreshing
              ? 'bg-white/5 text-gray-500 cursor-not-allowed'
              : 'bg-gradient-to-r from-neon-purple/20 to-neon-pink/20 text-neon-purple border border-neon-purple/30 hover:border-neon-purple/50'
          }`}
        >
          <RefreshCw className={`w-4 h-4 ${(loading || isRefreshing) ? 'animate-spin' : ''}`} />
          {loading || isRefreshing ? '分析中...' : data ? '重新分析' : '获取大师视角'}
        </button>
      </div>

      {/* Error state */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Loading state */}
      {(loading || isRefreshing) && !data && (
        <div className="card-cyber p-8 text-center">
          <div className="flex items-center justify-center gap-3">
            <Brain className="w-6 h-6 text-neon-purple animate-pulse" />
            <span className="text-gray-400">正在召唤两位投资大师...</span>
          </div>
        </div>
      )}

      {/* Data display */}
      {data && (
        <div className="space-y-4">
          {/* Two master panels */}
          <div className="grid lg:grid-cols-2 gap-4">
            <TalebPanel data={data.taleb} />
            <MungerPanel data={data.munger} />
          </div>

          {/* Consensus panel */}
          <ConsensusPanel data={data.consensus} />

          {/* Footer info */}
          <div className="flex items-center justify-between text-xs text-gray-600">
            <span>
              {data.is_mock ? '演示数据' : `AI 分析 · ${data.provider || 'unknown'}`}
            </span>
            <span>
              {new Date(data.timestamp).toLocaleString('zh-CN')}
            </span>
          </div>
        </div>
      )}

      {/* Empty state */}
      {!loading && !isRefreshing && !data && !error && (
        <div className="card-cyber p-8 text-center">
          <Brain className="w-12 h-12 text-gray-600 mx-auto mb-3" />
          <p className="text-gray-500 mb-2">点击上方按钮获取大师视角分析</p>
          <p className="text-gray-600 text-sm">需要先运行策略优化生成配置方案</p>
        </div>
      )}
    </div>
  );
}

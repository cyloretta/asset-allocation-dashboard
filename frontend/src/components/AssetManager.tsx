import { useState, useCallback, memo } from 'react';
import { X, Plus, Trash2, Search, Check, AlertCircle, Package } from 'lucide-react';
import {
  useAllAssets,
  useAssetTypes,
  searchAsset,
  addCustomAsset,
  deleteCustomAsset,
  type Asset,
  type AssetType
} from '../hooks/useApi';

interface AssetManagerProps {
  isOpen: boolean;
  onClose: () => void;
}

const AssetManager = memo(function AssetManager({ isOpen, onClose }: AssetManagerProps) {
  const { data: assets, loading, refresh } = useAllAssets();
  const { data: assetTypes } = useAssetTypes();

  const [searchQuery, setSearchQuery] = useState('');
  const [searchResult, setSearchResult] = useState<any>(null);
  const [searching, setSearching] = useState(false);

  const [showAddForm, setShowAddForm] = useState(false);
  const [newAsset, setNewAsset] = useState({
    ticker: '',
    name: '',
    asset_type: 'us_equity',
    min_weight: 0,
    max_weight: 0.4
  });

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // 搜索资产
  const handleSearch = useCallback(async () => {
    if (!searchQuery.trim()) return;
    setSearching(true);
    setSearchResult(null);
    setError(null);

    try {
      const result = await searchAsset(searchQuery.trim());
      setSearchResult(result);

      // 如果找到，自动填充表单
      if (result.found) {
        setNewAsset(prev => ({
          ...prev,
          ticker: result.ticker,
          name: result.name,
          asset_type: result.asset_type
        }));
        setShowAddForm(true);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || '搜索失败');
    } finally {
      setSearching(false);
    }
  }, [searchQuery]);

  // 添加资产
  const handleAdd = useCallback(async () => {
    if (!newAsset.ticker || !newAsset.name) {
      setError('请填写资产代码和名称');
      return;
    }

    setSaving(true);
    setError(null);

    try {
      await addCustomAsset(newAsset);
      setSuccess(`资产 ${newAsset.ticker} 添加成功`);
      setNewAsset({
        ticker: '',
        name: '',
        asset_type: 'us_equity',
        min_weight: 0,
        max_weight: 0.4
      });
      setShowAddForm(false);
      setSearchQuery('');
      setSearchResult(null);
      await refresh();
      setTimeout(() => setSuccess(null), 2000);
    } catch (err: any) {
      setError(err.response?.data?.detail || '添加失败');
    } finally {
      setSaving(false);
    }
  }, [newAsset, refresh]);

  // 删除资产
  const handleDelete = useCallback(async (ticker: string) => {
    if (!confirm(`确定要删除 ${ticker} 吗？`)) return;

    try {
      await deleteCustomAsset(ticker);
      setSuccess(`资产 ${ticker} 已删除`);
      await refresh();
      setTimeout(() => setSuccess(null), 2000);
    } catch (err: any) {
      setError(err.response?.data?.detail || '删除失败');
    }
  }, [refresh]);

  // 选择搜索建议
  const handleSelectSuggestion = useCallback((suggestion: any) => {
    setNewAsset(prev => ({
      ...prev,
      ticker: suggestion.ticker,
      name: suggestion.name,
      asset_type: suggestion.asset_type
    }));
    setShowAddForm(true);
    setSearchResult(null);
  }, []);

  if (!isOpen) return null;

  // 按类型分组资产
  const groupedAssets = assets.reduce((acc, asset) => {
    const type = asset.asset_type;
    if (!acc[type]) acc[type] = [];
    acc[type].push(asset);
    return acc;
  }, {} as Record<string, Asset[]>);

  const typeLabels: Record<string, string> = {
    us_equity: '美股',
    international: '国际',
    crypto: '加密货币',
    commodity: '商品',
    bond: '债券',
    etf: 'ETF',
    cash: '现金'
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} />

      {/* Modal */}
      <div className="relative w-full max-w-3xl max-h-[85vh] overflow-hidden rounded-2xl bg-cyber-dark border border-white/10 shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/10">
          <div className="flex items-center gap-3">
            <Package className="w-5 h-5 text-neon-cyan" />
            <h2 className="text-lg font-display font-semibold text-gradient">资产管理</h2>
          </div>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-white/5 transition-colors">
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>

        <div className="p-6 overflow-y-auto max-h-[calc(85vh-80px)]">
          {/* 通知 */}
          {error && (
            <div className="flex items-center gap-2 px-4 py-3 mb-4 rounded-lg bg-status-loss/10 border border-status-loss/30 text-status-loss text-sm">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              {error}
            </div>
          )}
          {success && (
            <div className="flex items-center gap-2 px-4 py-3 mb-4 rounded-lg bg-neon-green/10 border border-neon-green/30 text-neon-green text-sm">
              <Check className="w-4 h-4 flex-shrink-0" />
              {success}
            </div>
          )}

          {/* 搜索区 */}
          <div className="mb-6">
            <label className="block text-[10px] font-mono text-gray-500 tracking-widest mb-2">
              添加新资产
            </label>
            <div className="flex gap-2">
              <div className="flex-1 relative">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value.toUpperCase())}
                  onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                  placeholder="输入资产代码，如 AAPL, ETH-USD..."
                  className="w-full px-4 py-2.5 rounded-lg bg-white/5 border border-white/10 text-gray-200 font-mono text-sm focus:border-neon-cyan/50 focus:outline-none transition-colors"
                />
              </div>
              <button
                onClick={handleSearch}
                disabled={searching || !searchQuery.trim()}
                className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/30 hover:border-neon-cyan/50 transition-all font-mono text-sm disabled:opacity-50"
              >
                <Search className="w-4 h-4" />
                {searching ? '搜索中...' : '搜索'}
              </button>
              <button
                onClick={() => {
                  setShowAddForm(true);
                  setNewAsset(prev => ({ ...prev, ticker: searchQuery }));
                }}
                className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-neon-purple/10 text-neon-purple border border-neon-purple/30 hover:border-neon-purple/50 transition-all font-mono text-sm"
              >
                <Plus className="w-4 h-4" />
                手动添加
              </button>
            </div>

            {/* 搜索结果 */}
            {searchResult && !searchResult.found && searchResult.suggestions && (
              <div className="mt-3 p-3 rounded-lg bg-white/5 border border-white/10">
                <div className="text-xs text-gray-400 mb-2">可能的匹配：</div>
                <div className="flex flex-wrap gap-2">
                  {searchResult.suggestions.map((s: any) => (
                    <button
                      key={s.ticker}
                      onClick={() => handleSelectSuggestion(s)}
                      className="px-3 py-1.5 rounded-lg bg-neon-cyan/10 text-neon-cyan text-xs font-mono hover:bg-neon-cyan/20 transition-colors"
                    >
                      {s.ticker} - {s.name}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {searchResult && searchResult.is_builtin && (
              <div className="mt-3 p-3 rounded-lg bg-neon-yellow/10 border border-neon-yellow/30 text-neon-yellow text-sm">
                {searchResult.ticker} 是内置资产，无需添加
              </div>
            )}
          </div>

          {/* 添加表单 */}
          {showAddForm && (
            <div className="mb-6 p-4 rounded-lg bg-white/5 border border-neon-purple/30">
              <div className="flex items-center justify-between mb-4">
                <span className="text-sm text-gray-300 font-mono">添加资产</span>
                <button
                  onClick={() => setShowAddForm(false)}
                  className="text-gray-500 hover:text-gray-300"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="grid grid-cols-2 gap-4 mb-4">
                <div>
                  <label className="block text-[10px] font-mono text-gray-500 mb-1">代码</label>
                  <input
                    type="text"
                    value={newAsset.ticker}
                    onChange={(e) => setNewAsset(prev => ({ ...prev, ticker: e.target.value.toUpperCase() }))}
                    placeholder="如 AAPL"
                    className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-gray-200 font-mono text-sm focus:border-neon-purple/50 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-[10px] font-mono text-gray-500 mb-1">名称</label>
                  <input
                    type="text"
                    value={newAsset.name}
                    onChange={(e) => setNewAsset(prev => ({ ...prev, name: e.target.value }))}
                    placeholder="如 Apple Inc."
                    className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-gray-200 font-mono text-sm focus:border-neon-purple/50 focus:outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-4 mb-4">
                <div>
                  <label className="block text-[10px] font-mono text-gray-500 mb-1">类型</label>
                  <select
                    value={newAsset.asset_type}
                    onChange={(e) => setNewAsset(prev => ({ ...prev, asset_type: e.target.value }))}
                    className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-gray-200 font-mono text-sm focus:border-neon-purple/50 focus:outline-none"
                  >
                    {assetTypes.map((type: AssetType) => (
                      <option key={type.value} value={type.value}>{type.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-[10px] font-mono text-gray-500 mb-1">
                    最小权重 ({Math.round(newAsset.min_weight * 100)}%)
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="0.5"
                    step="0.05"
                    value={newAsset.min_weight}
                    onChange={(e) => setNewAsset(prev => ({ ...prev, min_weight: parseFloat(e.target.value) }))}
                    className="w-full accent-neon-purple"
                  />
                </div>
                <div>
                  <label className="block text-[10px] font-mono text-gray-500 mb-1">
                    最大权重 ({Math.round(newAsset.max_weight * 100)}%)
                  </label>
                  <input
                    type="range"
                    min="0.1"
                    max="1"
                    step="0.05"
                    value={newAsset.max_weight}
                    onChange={(e) => setNewAsset(prev => ({ ...prev, max_weight: parseFloat(e.target.value) }))}
                    className="w-full accent-neon-purple"
                  />
                </div>
              </div>

              <button
                onClick={handleAdd}
                disabled={saving || !newAsset.ticker || !newAsset.name}
                className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-neon-purple/20 text-neon-purple border border-neon-purple/40 hover:border-neon-purple/60 transition-all font-mono text-sm disabled:opacity-50"
              >
                <Plus className="w-4 h-4" />
                {saving ? '添加中...' : '确认添加'}
              </button>
            </div>
          )}

          {/* 资产列表 */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <label className="text-[10px] font-mono text-gray-500 tracking-widest">
                已有资产 ({assets.length})
              </label>
              {loading && (
                <div className="w-4 h-4 border-2 border-neon-cyan/30 border-t-neon-cyan rounded-full animate-spin" />
              )}
            </div>

            <div className="space-y-4">
              {Object.entries(groupedAssets).map(([type, typeAssets]) => (
                <div key={type}>
                  <div className="text-xs text-gray-500 font-mono mb-2 px-1">
                    {typeLabels[type] || type} ({typeAssets.length})
                  </div>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                    {typeAssets.map((asset: Asset) => (
                      <div
                        key={asset.ticker}
                        className={`flex items-center justify-between px-3 py-2 rounded-lg border transition-all ${
                          asset.is_builtin
                            ? 'bg-white/5 border-white/10'
                            : 'bg-neon-purple/5 border-neon-purple/20'
                        }`}
                      >
                        <div className="min-w-0">
                          <div className="font-mono text-sm text-gray-200 truncate">{asset.ticker}</div>
                          <div className="text-[10px] text-gray-500 truncate">{asset.name}</div>
                        </div>
                        {!asset.is_builtin && (
                          <button
                            onClick={() => handleDelete(asset.ticker)}
                            className="ml-2 p-1.5 rounded-lg text-gray-500 hover:text-status-loss hover:bg-status-loss/10 transition-colors flex-shrink-0"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
});

export default AssetManager;

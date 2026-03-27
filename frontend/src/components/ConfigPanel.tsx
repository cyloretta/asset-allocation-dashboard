import { useState, useEffect, memo, useCallback } from 'react';
import { X, Plus, Trash2, Save, Check, AlertCircle } from 'lucide-react';
import {
  useUserConfigs,
  useAvailableAssets,
  createUserConfig,
  updateUserConfig,
  deleteUserConfig
} from '../hooks/useApi';
import type { AssetConstraint } from '../types';

interface ConfigPanelProps {
  isOpen: boolean;
  onClose: () => void;
  onConfigSelect?: (configId: number) => void;
}

const OPTIMIZATION_METHODS = [
  { value: 'max_sharpe_cvar', label: '夏普最大化 (CVaR约束)', description: '推荐：平衡收益与风险' },
  { value: 'max_sharpe', label: '最大夏普比率', description: '追求风险调整后最高收益' },
  { value: 'min_volatility', label: '最小波动率', description: '保守策略，最低波动' },
  { value: 'risk_parity', label: '风险平价', description: '各资产等风险贡献' },
  { value: 'composite', label: '综合优化', description: '多目标平衡' },
  { value: 'risk_aware', label: '风险感知', description: '根据市场状态动态调整' },
];

const ConfigPanel = memo(function ConfigPanel({ isOpen, onClose }: ConfigPanelProps) {
  const { data: configs, loading: configsLoading, refresh: refreshConfigs } = useUserConfigs();
  const { data: availableAssets } = useAvailableAssets();

  const [selectedConfigId, setSelectedConfigId] = useState<number | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // 编辑表单状态
  const [formData, setFormData] = useState({
    name: '',
    asset_pool: [] as string[],
    asset_constraints: {} as { [asset: string]: AssetConstraint },
    max_drawdown: 0.25,
    target_sharpe: 1.0,
    rebalance_threshold: 0.05,
    preferred_method: 'max_sharpe_cvar',
    use_ai_adjustments: true,
  });

  // 加载选中配置
  useEffect(() => {
    if (selectedConfigId) {
      const config = configs.find(c => c.id === selectedConfigId);
      if (config) {
        setFormData({
          name: config.name,
          asset_pool: config.asset_pool || [],
          asset_constraints: config.asset_constraints || {},
          max_drawdown: config.max_drawdown,
          target_sharpe: config.target_sharpe,
          rebalance_threshold: config.rebalance_threshold,
          preferred_method: config.preferred_method,
          use_ai_adjustments: config.use_ai_adjustments,
        });
      }
    }
  }, [selectedConfigId, configs]);

  // 重置表单
  const resetForm = useCallback(() => {
    setFormData({
      name: '',
      asset_pool: Object.keys(availableAssets),
      asset_constraints: {},
      max_drawdown: 0.25,
      target_sharpe: 1.0,
      rebalance_threshold: 0.05,
      preferred_method: 'max_sharpe_cvar',
      use_ai_adjustments: true,
    });
  }, [availableAssets]);

  // 开始创建新配置
  const handleStartCreate = useCallback(() => {
    setIsCreating(true);
    setSelectedConfigId(null);
    resetForm();
    setError(null);
    setSuccess(null);
  }, [resetForm]);

  // 选择配置
  const handleSelectConfig = useCallback((configId: number) => {
    setSelectedConfigId(configId);
    setIsCreating(false);
    setError(null);
    setSuccess(null);
  }, []);

  // 保存配置
  const handleSave = useCallback(async () => {
    if (!formData.name.trim()) {
      setError('请输入配置名称');
      return;
    }

    setSaving(true);
    setError(null);

    try {
      if (isCreating) {
        await createUserConfig(formData as any);
        setSuccess('配置创建成功');
      } else if (selectedConfigId) {
        await updateUserConfig(selectedConfigId, formData as any);
        setSuccess('配置更新成功');
      }
      await refreshConfigs();
      setTimeout(() => setSuccess(null), 2000);
    } catch (err: any) {
      setError(err.response?.data?.detail || '保存失败');
    } finally {
      setSaving(false);
    }
  }, [formData, isCreating, selectedConfigId, refreshConfigs]);

  // 删除配置
  const handleDelete = useCallback(async () => {
    if (!selectedConfigId) return;
    if (!confirm('确定要删除这个配置吗？')) return;

    try {
      await deleteUserConfig(selectedConfigId);
      setSelectedConfigId(null);
      await refreshConfigs();
      setSuccess('配置已删除');
      setTimeout(() => setSuccess(null), 2000);
    } catch (err: any) {
      setError(err.response?.data?.detail || '删除失败');
    }
  }, [selectedConfigId, refreshConfigs]);

  // 切换资产池中的资产
  const toggleAsset = useCallback((asset: string) => {
    setFormData(prev => ({
      ...prev,
      asset_pool: prev.asset_pool.includes(asset)
        ? prev.asset_pool.filter(a => a !== asset)
        : [...prev.asset_pool, asset]
    }));
  }, []);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} />

      {/* Modal */}
      <div className="relative w-full max-w-4xl max-h-[90vh] overflow-hidden rounded-2xl bg-cyber-dark border border-white/10 shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/10">
          <h2 className="text-lg font-display font-semibold text-gradient">用户配置管理</h2>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-white/5 transition-colors">
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>

        <div className="flex h-[calc(90vh-120px)]">
          {/* 配置列表 */}
          <div className="w-64 border-r border-white/10 overflow-y-auto">
            <div className="p-4">
              <button
                onClick={handleStartCreate}
                className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/30 hover:border-neon-cyan/50 transition-all font-mono text-sm"
              >
                <Plus className="w-4 h-4" />
                新建配置
              </button>
            </div>

            {configsLoading ? (
              <div className="p-4 text-center">
                <div className="w-5 h-5 border-2 border-neon-cyan/30 border-t-neon-cyan rounded-full animate-spin mx-auto" />
              </div>
            ) : (
              <div className="space-y-1 px-2">
                {configs.map(config => (
                  <button
                    key={config.id}
                    onClick={() => handleSelectConfig(config.id)}
                    className={`w-full text-left px-4 py-3 rounded-lg transition-all ${
                      selectedConfigId === config.id
                        ? 'bg-neon-purple/20 border border-neon-purple/40'
                        : 'hover:bg-white/5 border border-transparent'
                    }`}
                  >
                    <div className="font-mono text-sm text-gray-200">{config.name}</div>
                    <div className="text-[10px] text-gray-500 mt-0.5">
                      {config.asset_pool?.length || 0} 资产 · {config.preferred_method}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* 编辑区域 */}
          <div className="flex-1 overflow-y-auto p-6">
            {!selectedConfigId && !isCreating ? (
              <div className="h-full flex items-center justify-center text-gray-500 font-mono text-sm">
                选择一个配置或创建新配置
              </div>
            ) : (
              <div className="space-y-6">
                {/* 通知 */}
                {error && (
                  <div className="flex items-center gap-2 px-4 py-3 rounded-lg bg-status-loss/10 border border-status-loss/30 text-status-loss text-sm">
                    <AlertCircle className="w-4 h-4" />
                    {error}
                  </div>
                )}
                {success && (
                  <div className="flex items-center gap-2 px-4 py-3 rounded-lg bg-neon-green/10 border border-neon-green/30 text-neon-green text-sm">
                    <Check className="w-4 h-4" />
                    {success}
                  </div>
                )}

                {/* 配置名称 */}
                <div>
                  <label className="block text-[10px] font-mono text-gray-500 tracking-widest mb-2">配置名称</label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={e => setFormData(prev => ({ ...prev, name: e.target.value }))}
                    placeholder="例如：保守型配置"
                    className="w-full px-4 py-2.5 rounded-lg bg-white/5 border border-white/10 text-gray-200 font-mono text-sm focus:border-neon-cyan/50 focus:outline-none transition-colors"
                  />
                </div>

                {/* 资产池 */}
                <div>
                  <label className="block text-[10px] font-mono text-gray-500 tracking-widest mb-2">资产池</label>
                  <div className="grid grid-cols-3 gap-2">
                    {Object.entries(availableAssets).map(([asset]) => (
                      <button
                        key={asset}
                        onClick={() => toggleAsset(asset)}
                        className={`px-3 py-2 rounded-lg font-mono text-sm transition-all ${
                          formData.asset_pool.includes(asset)
                            ? 'bg-neon-cyan/20 text-neon-cyan border border-neon-cyan/40'
                            : 'bg-white/5 text-gray-400 border border-white/10 hover:border-white/20'
                        }`}
                      >
                        {asset}
                      </button>
                    ))}
                  </div>
                </div>

                {/* 风险偏好 */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-[10px] font-mono text-gray-500 tracking-widest mb-2">
                      最大回撤限制 ({Math.round(formData.max_drawdown * 100)}%)
                    </label>
                    <input
                      type="range"
                      min="0.05"
                      max="0.50"
                      step="0.05"
                      value={formData.max_drawdown}
                      onChange={e => setFormData(prev => ({ ...prev, max_drawdown: parseFloat(e.target.value) }))}
                      className="w-full accent-neon-cyan"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-mono text-gray-500 tracking-widest mb-2">
                      目标夏普比率 ({formData.target_sharpe.toFixed(1)})
                    </label>
                    <input
                      type="range"
                      min="0.5"
                      max="3.0"
                      step="0.1"
                      value={formData.target_sharpe}
                      onChange={e => setFormData(prev => ({ ...prev, target_sharpe: parseFloat(e.target.value) }))}
                      className="w-full accent-neon-purple"
                    />
                  </div>
                </div>

                {/* 优化方法 */}
                <div>
                  <label className="block text-[10px] font-mono text-gray-500 tracking-widest mb-2">优化方法</label>
                  <div className="grid grid-cols-2 gap-2">
                    {OPTIMIZATION_METHODS.map(method => (
                      <button
                        key={method.value}
                        onClick={() => setFormData(prev => ({ ...prev, preferred_method: method.value }))}
                        className={`text-left px-3 py-2 rounded-lg transition-all ${
                          formData.preferred_method === method.value
                            ? 'bg-neon-purple/20 border border-neon-purple/40'
                            : 'bg-white/5 border border-white/10 hover:border-white/20'
                        }`}
                      >
                        <div className="font-mono text-sm text-gray-200">{method.label}</div>
                        <div className="text-[10px] text-gray-500">{method.description}</div>
                      </button>
                    ))}
                  </div>
                </div>

                {/* AI 调整 */}
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => setFormData(prev => ({ ...prev, use_ai_adjustments: !prev.use_ai_adjustments }))}
                    className={`w-12 h-6 rounded-full transition-all ${
                      formData.use_ai_adjustments
                        ? 'bg-neon-green/30'
                        : 'bg-white/10'
                    }`}
                  >
                    <div className={`w-5 h-5 rounded-full transition-all ${
                      formData.use_ai_adjustments
                        ? 'bg-neon-green translate-x-6'
                        : 'bg-gray-400 translate-x-0.5'
                    }`} />
                  </button>
                  <span className="text-sm text-gray-300 font-mono">启用 AI 智能调整</span>
                </div>

                {/* 操作按钮 */}
                <div className="flex items-center justify-between pt-4 border-t border-white/10">
                  {selectedConfigId && !isCreating && (
                    <button
                      onClick={handleDelete}
                      className="flex items-center gap-2 px-4 py-2 rounded-lg bg-status-loss/10 text-status-loss border border-status-loss/30 hover:border-status-loss/50 transition-all font-mono text-sm"
                    >
                      <Trash2 className="w-4 h-4" />
                      删除
                    </button>
                  )}
                  <div className="flex-1" />
                  <button
                    onClick={handleSave}
                    disabled={saving}
                    className="flex items-center gap-2 px-6 py-2.5 rounded-lg bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/30 hover:border-neon-cyan/50 transition-all font-mono text-sm disabled:opacity-50"
                  >
                    <Save className="w-4 h-4" />
                    {saving ? '保存中...' : isCreating ? '创建配置' : '保存更改'}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
});

export default ConfigPanel;

import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import type { PortfolioAllocation } from '../../types';

interface Props {
  allocation: PortfolioAllocation;
  size?: 'sm' | 'md' | 'lg';
}

const COLORS: { [key: string]: string } = {
  'SPY': '#3b82f6',
  'QQQ': '#8b5cf6',
  'GLD': '#f59e0b',
  'BTC-USD': '#f97316',
  'TLT': '#10b981',
  'CASH': '#6b7280',
};

export default function AllocationChart({ allocation, size = 'md' }: Props) {
  const chartData = Object.entries(allocation)
    .filter(([_, value]) => value > 0)
    .map(([name, value]) => ({
      name,
      value: Math.round(value * 100),
    }));

  const dimensions = {
    sm: { inner: 30, outer: 50 },
    md: { inner: 50, outer: 80 },
    lg: { inner: 70, outer: 110 },
  };

  const { inner, outer } = dimensions[size];

  return (
    <ResponsiveContainer width="100%" height="100%">
      <PieChart>
        <Pie
          data={chartData}
          cx="50%"
          cy="50%"
          innerRadius={inner}
          outerRadius={outer}
          paddingAngle={2}
          dataKey="value"
        >
          {chartData.map((entry) => (
            <Cell key={entry.name} fill={COLORS[entry.name] || '#94a3b8'} />
          ))}
        </Pie>
        <Tooltip
          formatter={(value: number) => [`${value}%`, 'Weight']}
          contentStyle={{
            backgroundColor: 'white',
            border: '1px solid #e5e7eb',
            borderRadius: '8px',
            fontSize: '12px'
          }}
        />
      </PieChart>
    </ResponsiveContainer>
  );
}

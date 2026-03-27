import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine
} from 'recharts';
import type { BacktestResult } from '../../types';

interface Props {
  data: BacktestResult;
}

export default function BacktestChart({ data }: Props) {
  const chartData = data.dates.map((date, index) => ({
    date: date,
    value: data.portfolio_values[index],
    drawdown: data.drawdown[index] * 100
  }));

  // Sample data for performance (show every 10th point for large datasets)
  const sampledData = chartData.length > 100
    ? chartData.filter((_, i) => i % Math.ceil(chartData.length / 100) === 0)
    : chartData;

  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={sampledData}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis
          dataKey="date"
          tickFormatter={(value) => {
            const date = new Date(value);
            return `${date.getMonth() + 1}/${date.getFullYear().toString().slice(2)}`;
          }}
          tick={{ fontSize: 10 }}
          interval="preserveStartEnd"
        />
        <YAxis
          tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`}
          tick={{ fontSize: 10 }}
          domain={['dataMin', 'dataMax']}
        />
        <Tooltip
          formatter={(value: number, name: string) => {
            if (name === 'value') return [`$${value.toLocaleString()}`, 'Value'];
            return [`${value.toFixed(2)}%`, 'Drawdown'];
          }}
          labelFormatter={(label) => new Date(label).toLocaleDateString()}
          contentStyle={{
            backgroundColor: 'white',
            border: '1px solid #e5e7eb',
            borderRadius: '8px',
            fontSize: '12px'
          }}
        />
        <ReferenceLine
          y={100000}
          stroke="#9ca3af"
          strokeDasharray="3 3"
          label={{ value: 'Initial', position: 'right', fontSize: 10, fill: '#9ca3af' }}
        />
        <Line
          type="monotone"
          dataKey="value"
          stroke="#3b82f6"
          strokeWidth={2}
          dot={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

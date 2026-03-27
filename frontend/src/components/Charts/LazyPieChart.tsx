import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';

interface ChartDataItem {
  name: string;
  ticker: string;
  value: number;
}

interface Props {
  data: ChartDataItem[];
  colors: { [key: string]: string };
}

export default function LazyPieChart({ data, colors }: Props) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          innerRadius={45}
          outerRadius={75}
          paddingAngle={2}
          dataKey="value"
        >
          {data.map((entry) => (
            <Cell key={entry.ticker} fill={colors[entry.ticker] || '#94a3b8'} />
          ))}
        </Pie>
        <Tooltip
          formatter={(value: number) => [`${value}%`, '权重']}
          contentStyle={{
            backgroundColor: 'white',
            border: '1px solid #e5e7eb',
            borderRadius: '8px',
          }}
        />
      </PieChart>
    </ResponsiveContainer>
  );
}

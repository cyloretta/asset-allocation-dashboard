import { LineChart, Line, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface Props {
  data: Record<string, any>[];
  activeAssets: string[];
  colors: { [key: string]: string };
  assetNames: { [key: string]: string };
}

export default function LazyHistoryChart({ data, activeAssets, colors, assetNames }: Props) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={data}>
        <XAxis
          dataKey="date"
          tick={{ fontSize: 10 }}
          interval="preserveStartEnd"
        />
        <YAxis
          tick={{ fontSize: 10 }}
          domain={[0, 100]}
          tickFormatter={(v) => `${v}%`}
        />
        <Tooltip
          formatter={(value: number) => [`${value}%`]}
          contentStyle={{
            backgroundColor: 'white',
            border: '1px solid #e5e7eb',
            borderRadius: '8px',
            fontSize: '12px',
          }}
        />
        <Legend
          wrapperStyle={{ fontSize: '10px' }}
          formatter={(value) => assetNames[value] || value}
        />
        {activeAssets.map(asset => (
          <Line
            key={asset}
            type="stepAfter"
            dataKey={asset}
            stroke={colors[asset] || '#94a3b8'}
            strokeWidth={2}
            dot={false}
            name={asset}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}

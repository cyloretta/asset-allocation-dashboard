import { Treemap, ResponsiveContainer, Tooltip } from 'recharts';

interface ChartDataItem {
  name: string;
  ticker: string;
  value: number;
}

interface Props {
  data: ChartDataItem[];
  colors: { [key: string]: string };
}

// 自定义 Treemap 内容渲染
interface CustomContentProps {
  x: number;
  y: number;
  width: number;
  height: number;
  name: string;
  ticker: string;
  value: number;
  colors: { [key: string]: string };
}

function CustomTreemapContent(props: CustomContentProps) {
  const { x, y, width, height, name, ticker, value, colors } = props;
  const color = colors[ticker] || '#6b7280';

  // 只有足够大的区块才显示文字
  const showLabel = width > 50 && height > 40;
  const showValue = width > 40 && height > 25;

  return (
    <g>
      <rect
        x={x}
        y={y}
        width={width}
        height={height}
        fill={color}
        stroke="rgba(10, 10, 15, 0.8)"
        strokeWidth={2}
        rx={4}
        style={{
          filter: `drop-shadow(0 0 8px ${color}50)`,
          transition: 'all 0.3s ease',
        }}
      />
      {/* 渐变叠加层 */}
      <rect
        x={x}
        y={y}
        width={width}
        height={height}
        fill="url(#treemapGradient)"
        rx={4}
        style={{ pointerEvents: 'none' }}
      />
      {showLabel && (
        <>
          <text
            x={x + width / 2}
            y={y + height / 2 - (showValue ? 8 : 0)}
            textAnchor="middle"
            dominantBaseline="middle"
            fill="#ffffff"
            fontSize={width > 80 ? 13 : 11}
            fontFamily="'JetBrains Mono', monospace"
            fontWeight="600"
            style={{ textShadow: '0 1px 2px rgba(0,0,0,0.8)' }}
          >
            {name}
          </text>
          {showValue && (
            <text
              x={x + width / 2}
              y={y + height / 2 + 12}
              textAnchor="middle"
              dominantBaseline="middle"
              fill="rgba(255,255,255,0.9)"
              fontSize={width > 80 ? 16 : 12}
              fontFamily="'JetBrains Mono', monospace"
              fontWeight="700"
              style={{ textShadow: '0 1px 2px rgba(0,0,0,0.8)' }}
            >
              {value}%
            </text>
          )}
        </>
      )}
    </g>
  );
}

export default function LazyTreemap({ data, colors }: Props) {
  // 将数据转换为 Treemap 格式
  const treemapData = data.map(item => ({
    ...item,
    size: item.value, // Treemap 使用 size 作为面积
  }));

  return (
    <ResponsiveContainer width="100%" height="100%">
      <Treemap
        data={treemapData}
        dataKey="size"
        aspectRatio={4 / 3}
        stroke="none"
        content={<CustomTreemapContent x={0} y={0} width={0} height={0} name="" ticker="" value={0} colors={colors} />}
      >
        <defs>
          <linearGradient id="treemapGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="rgba(255,255,255,0.1)" />
            <stop offset="100%" stopColor="rgba(0,0,0,0.2)" />
          </linearGradient>
        </defs>
        <Tooltip
          formatter={(value: number) => [`${value}%`, '权重']}
          contentStyle={{
            backgroundColor: 'rgba(13, 13, 20, 0.95)',
            border: '1px solid rgba(0, 245, 255, 0.3)',
            borderRadius: '8px',
            boxShadow: '0 0 20px rgba(0, 245, 255, 0.2)',
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: '12px',
            color: '#e5e7eb',
          }}
          labelStyle={{ color: '#00f5ff', fontWeight: 600 }}
        />
      </Treemap>
    </ResponsiveContainer>
  );
}

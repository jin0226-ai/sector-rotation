import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import type { ScoreTrends } from '../../types';

interface Props {
  data: ScoreTrends;
}

const COLORS = [
  '#3b82f6', // blue
  '#10b981', // green
  '#f59e0b', // amber
  '#ef4444', // red
  '#8b5cf6', // purple
  '#ec4899', // pink
  '#06b6d4', // cyan
  '#f97316', // orange
  '#84cc16', // lime
  '#6366f1', // indigo
  '#14b8a6', // teal
];

function ScoreTrendsChart({ data }: Props) {
  // Transform data for Recharts
  const chartData = data.dates.map((date, idx) => {
    const point: Record<string, any> = {
      date: new Date(date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    };

    Object.entries(data.sectors).forEach(([symbol, sectorData]) => {
      point[symbol] = sectorData.scores[idx];
    });

    return point;
  });

  const sectors = Object.keys(data.sectors);

  return (
    <div className="h-80">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: '#e5e7eb' }}
          />
          <YAxis
            domain={[0, 100]}
            tick={{ fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: '#e5e7eb' }}
            tickFormatter={(value) => `${value}`}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: 'white',
              border: '1px solid #e5e7eb',
              borderRadius: '8px',
              fontSize: '12px',
            }}
            formatter={(value: number) => [value?.toFixed(1), '']}
          />
          <Legend
            wrapperStyle={{ fontSize: '11px' }}
            iconType="line"
          />
          {sectors.map((symbol, idx) => (
            <Line
              key={symbol}
              type="monotone"
              dataKey={symbol}
              name={data.sectors[symbol].name}
              stroke={COLORS[idx % COLORS.length]}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export default ScoreTrendsChart;

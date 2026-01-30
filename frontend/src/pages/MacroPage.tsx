import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { RefreshCw, TrendingUp, TrendingDown, Minus, Info } from 'lucide-react';
import { fetchMacroDashboard, fetchMacroHistory, fetchBusinessCycle } from '../services/api';

const CATEGORIES = [
  { id: 'all', name: 'All' },
  { id: 'growth', name: 'Growth' },
  { id: 'labor', name: 'Labor' },
  { id: 'inflation', name: 'Inflation' },
  { id: 'rates', name: 'Rates' },
  { id: 'sentiment', name: 'Sentiment' },
  { id: 'housing', name: 'Housing' },
];

function MacroPage() {
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [selectedVariable, setSelectedVariable] = useState<string | null>(null);

  const { data: macroDashboard, isLoading } = useQuery({
    queryKey: ['macroDashboard'],
    queryFn: fetchMacroDashboard,
  });

  const { data: businessCycle } = useQuery({
    queryKey: ['businessCycle'],
    queryFn: fetchBusinessCycle,
  });

  const { data: variableHistory } = useQuery({
    queryKey: ['macroHistory', selectedVariable],
    queryFn: () => fetchMacroHistory(selectedVariable!),
    enabled: !!selectedVariable,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  const filteredVariables = macroDashboard?.variables?.filter(
    (v: any) => selectedCategory === 'all' || v.category === selectedCategory
  ) || [];

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'rising':
        return <TrendingUp className="w-4 h-4 text-green-500" />;
      case 'falling':
        return <TrendingDown className="w-4 h-4 text-red-500" />;
      default:
        return <Minus className="w-4 h-4 text-gray-400" />;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'high':
        return 'bg-red-100 text-red-700';
      case 'low':
        return 'bg-green-100 text-green-700';
      default:
        return 'bg-gray-100 text-gray-700';
    }
  };

  const phaseInfo: Record<string, { color: string; description: string }> = {
    early_cycle: {
      color: 'bg-green-100 text-green-800',
      description: 'Economy recovering from recession. Favor Financials, Consumer Discretionary, Industrials.',
    },
    mid_cycle: {
      color: 'bg-blue-100 text-blue-800',
      description: 'Economy expanding with sustained growth. Favor Technology, Communication Services.',
    },
    late_cycle: {
      color: 'bg-orange-100 text-orange-800',
      description: 'Economy overheating, inflation rising. Favor Energy, Materials.',
    },
    recession: {
      color: 'bg-red-100 text-red-800',
      description: 'Economic contraction. Favor defensive sectors: Healthcare, Consumer Staples, Utilities.',
    },
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Macro Economic Data</h1>
        <p className="text-sm text-gray-500 mt-1">
          Track key economic indicators and business cycle phase
        </p>
      </div>

      {/* Business Cycle */}
      {businessCycle && (
        <div className="card">
          <div className="flex items-start justify-between">
            <div>
              <h3 className="text-lg font-semibold mb-2">Business Cycle Phase</h3>
              <div className="flex items-center gap-3 mb-3">
                <span className={`px-4 py-2 rounded-lg text-sm font-medium ${
                  phaseInfo[businessCycle.current_phase]?.color || 'bg-gray-100'
                }`}>
                  {businessCycle.current_phase?.replace('_', ' ').replace(/\b\w/g, (l: string) => l.toUpperCase())}
                </span>
                <span className="text-sm text-gray-500">
                  Confidence: {(businessCycle.confidence * 100).toFixed(0)}%
                </span>
              </div>
              <p className="text-sm text-gray-600 max-w-2xl">
                {phaseInfo[businessCycle.current_phase]?.description}
              </p>
            </div>
            <Info className="w-5 h-5 text-gray-400" />
          </div>
        </div>
      )}

      {/* Category Filter */}
      <div className="flex gap-2 flex-wrap">
        {CATEGORIES.map((cat) => (
          <button
            key={cat.id}
            onClick={() => setSelectedCategory(cat.id)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              selectedCategory === cat.id
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {cat.name}
          </button>
        ))}
      </div>

      {/* Variables Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredVariables.map((variable: any) => (
          <button
            key={variable.id}
            onClick={() => setSelectedVariable(variable.id)}
            className={`card text-left hover:border-blue-300 transition-colors ${
              selectedVariable === variable.id ? 'border-blue-500 ring-2 ring-blue-100' : ''
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                {getTrendIcon(variable.trend)}
                <span className="font-medium">{variable.name}</span>
              </div>
              <span className={`px-2 py-1 rounded text-xs font-medium ${getStatusBadge(variable.status)}`}>
                {variable.status}
              </span>
            </div>

            <div className="flex items-end justify-between">
              <div>
                <p className="text-2xl font-bold">
                  {typeof variable.value === 'number'
                    ? variable.value.toLocaleString(undefined, { maximumFractionDigits: 2 })
                    : variable.value}
                </p>
                <p className="text-xs text-gray-500">{variable.id}</p>
              </div>
              <div className="text-right">
                <p className="text-sm font-medium text-gray-600">
                  {variable.percentile?.toFixed(0)}th
                </p>
                <p className="text-xs text-gray-400">percentile</p>
              </div>
            </div>

            {/* Mini percentile bar */}
            <div className="mt-3 w-full bg-gray-200 rounded-full h-1.5">
              <div
                className={`h-1.5 rounded-full ${
                  variable.percentile >= 80 ? 'bg-red-500' :
                  variable.percentile <= 20 ? 'bg-green-500' :
                  'bg-blue-500'
                }`}
                style={{ width: `${variable.percentile}%` }}
              />
            </div>
          </button>
        ))}
      </div>

      {/* Selected Variable History */}
      {selectedVariable && variableHistory && variableHistory.length > 0 && (
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">
            {selectedVariable} Historical Data
          </h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={variableHistory.slice(-252)}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 10 }}
                  tickFormatter={(date) => new Date(date).toLocaleDateString('en-US', { month: 'short', year: '2-digit' })}
                />
                <YAxis
                  tick={{ fontSize: 11 }}
                  domain={['auto', 'auto']}
                />
                <Tooltip
                  formatter={(value: number) => [value.toLocaleString(undefined, { maximumFractionDigits: 2 }), selectedVariable]}
                  labelFormatter={(date) => new Date(date).toLocaleDateString()}
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
          </div>
        </div>
      )}
    </div>
  );
}

export default MacroPage;

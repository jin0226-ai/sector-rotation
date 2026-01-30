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
import { RefreshCw, TrendingUp, TrendingDown, ArrowUpRight, ArrowDownRight } from 'lucide-react';
import { fetchSectors, fetchSectorHistory, fetchScoreBreakdown } from '../services/api';

function SectorsPage() {
  const [selectedSector, setSelectedSector] = useState<string | null>(null);

  const { data: sectors, isLoading } = useQuery({
    queryKey: ['sectors'],
    queryFn: fetchSectors,
  });

  const { data: sectorHistory } = useQuery({
    queryKey: ['sectorHistory', selectedSector],
    queryFn: () => fetchSectorHistory(selectedSector!, 90),
    enabled: !!selectedSector,
  });

  const { data: scoreBreakdown } = useQuery({
    queryKey: ['scoreBreakdown', selectedSector],
    queryFn: () => fetchScoreBreakdown(selectedSector!),
    enabled: !!selectedSector,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Sector Analysis</h1>
        <p className="text-sm text-gray-500 mt-1">
          Detailed view of sector ETFs and their performance
        </p>
      </div>

      {/* Sector Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {sectors?.map((sector: any) => (
          <button
            key={sector.symbol}
            onClick={() => setSelectedSector(sector.symbol)}
            className={`card text-left hover:border-blue-300 transition-colors ${
              selectedSector === sector.symbol ? 'border-blue-500 ring-2 ring-blue-100' : ''
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="font-bold text-lg">{sector.symbol}</span>
              <span className={`flex items-center gap-1 text-sm ${
                sector.change_1d >= 0 ? 'text-green-600' : 'text-red-600'
              }`}>
                {sector.change_1d >= 0 ? (
                  <ArrowUpRight className="w-4 h-4" />
                ) : (
                  <ArrowDownRight className="w-4 h-4" />
                )}
                {sector.change_1d >= 0 ? '+' : ''}{sector.change_1d?.toFixed(2)}%
              </span>
            </div>
            <p className="text-sm text-gray-500 mb-2">{sector.name}</p>
            <p className="text-xl font-semibold">
              ${sector.price?.toFixed(2)}
            </p>
            <div className="mt-2 flex gap-2 text-xs">
              <span className={`${(sector.change_1m || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                1M: {(sector.change_1m || 0) >= 0 ? '+' : ''}{sector.change_1m?.toFixed(1)}%
              </span>
              <span className={`${(sector.change_3m || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                3M: {(sector.change_3m || 0) >= 0 ? '+' : ''}{sector.change_3m?.toFixed(1)}%
              </span>
            </div>
          </button>
        ))}
      </div>

      {/* Selected Sector Details */}
      {selectedSector && scoreBreakdown && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Score Breakdown */}
          <div className="card">
            <h3 className="text-lg font-semibold mb-4">
              {scoreBreakdown.symbol} Score Breakdown
            </h3>

            <div className="mb-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-2xl font-bold">
                  {scoreBreakdown.composite_score?.toFixed(1)}
                </span>
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                  scoreBreakdown.recommendation === 'Overweight'
                    ? 'bg-green-100 text-green-700'
                    : scoreBreakdown.recommendation === 'Underweight'
                    ? 'bg-red-100 text-red-700'
                    : 'bg-gray-100 text-gray-700'
                }`}>
                  {scoreBreakdown.recommendation}
                </span>
              </div>
            </div>

            <div className="space-y-3">
              {Object.entries(scoreBreakdown.components || {}).map(([key, comp]: [string, any]) => (
                <div key={key}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-gray-600">{key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</span>
                    <span className="font-medium">{comp.value?.toFixed(1)} ({(comp.weight * 100).toFixed(0)}%)</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-blue-600 h-2 rounded-full"
                      style={{ width: `${comp.value}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Price Chart */}
          {sectorHistory && sectorHistory.length > 0 && (
            <div className="card">
              <h3 className="text-lg font-semibold mb-4">Price History (90 Days)</h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={sectorHistory}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis
                      dataKey="date"
                      tick={{ fontSize: 10 }}
                      tickFormatter={(date) => new Date(date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                    />
                    <YAxis
                      tick={{ fontSize: 11 }}
                      domain={['auto', 'auto']}
                      tickFormatter={(value) => `$${value.toFixed(0)}`}
                    />
                    <Tooltip
                      formatter={(value: number) => [`$${value.toFixed(2)}`, 'Price']}
                      labelFormatter={(date) => new Date(date).toLocaleDateString()}
                    />
                    <Line
                      type="monotone"
                      dataKey="adj_close"
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
      )}

      {/* Macro Sensitivity */}
      {selectedSector && scoreBreakdown?.macro_sensitivity && (
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">
            {selectedSector} Macro Sensitivity
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Object.entries(scoreBreakdown.macro_sensitivity).map(([factor, value]: [string, any]) => (
              <div key={factor} className="p-3 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-500 mb-1">
                  {factor.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                </p>
                <p className={`text-lg font-semibold ${
                  value > 0 ? 'text-green-600' : value < 0 ? 'text-red-600' : 'text-gray-600'
                }`}>
                  {value > 0 ? '+' : ''}{value.toFixed(2)}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default SectorsPage;

import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  BarChart,
  Bar,
} from 'recharts';
import { RefreshCw, Play, TrendingUp, TrendingDown, Target, Activity } from 'lucide-react';
import { fetchDefaultBacktest, runBacktest } from '../services/api';

function BacktestPage() {
  const [config, setConfig] = useState({
    start_date: '2005-01-01',
    end_date: '',
    initial_capital: 100000,
    rebalance_frequency: 'monthly',
    top_n_sectors: 3,
  });

  const { data: defaultBacktest, isLoading } = useQuery({
    queryKey: ['defaultBacktest'],
    queryFn: fetchDefaultBacktest,
  });

  const mutation = useMutation({
    mutationFn: runBacktest,
  });

  const backtest = mutation.data || defaultBacktest;
  const performance = backtest?.results?.performance;
  const equityCurve = backtest?.results?.equity_curve || [];
  const monthlyReturns = backtest?.results?.monthly_returns || [];

  const handleRunBacktest = () => {
    mutation.mutate(config);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Backtesting</h1>
          <p className="text-sm text-gray-500 mt-1">
            Test sector rotation strategy on historical data
          </p>
        </div>
      </div>

      {/* Configuration */}
      <div className="card">
        <h3 className="text-lg font-semibold mb-4">Backtest Configuration</h3>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Start Date
            </label>
            <input
              type="date"
              value={config.start_date}
              onChange={(e) => setConfig({ ...config, start_date: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              End Date
            </label>
            <input
              type="date"
              value={config.end_date}
              onChange={(e) => setConfig({ ...config, end_date: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
              placeholder="Today"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Initial Capital
            </label>
            <input
              type="number"
              value={config.initial_capital}
              onChange={(e) => setConfig({ ...config, initial_capital: Number(e.target.value) })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Rebalance
            </label>
            <select
              value={config.rebalance_frequency}
              onChange={(e) => setConfig({ ...config, rebalance_frequency: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
            >
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
              <option value="monthly">Monthly</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Top N Sectors
            </label>
            <select
              value={config.top_n_sectors}
              onChange={(e) => setConfig({ ...config, top_n_sectors: Number(e.target.value) })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
            >
              {[1, 2, 3, 4, 5].map((n) => (
                <option key={n} value={n}>{n}</option>
              ))}
            </select>
          </div>
        </div>
        <button
          onClick={handleRunBacktest}
          disabled={mutation.isPending}
          className="mt-4 flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          {mutation.isPending ? (
            <RefreshCw className="w-4 h-4 animate-spin" />
          ) : (
            <Play className="w-4 h-4" />
          )}
          Run Backtest
        </button>
      </div>

      {/* Performance Metrics */}
      {performance && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
          <div className="card">
            <div className="flex items-center gap-2 text-gray-500 text-sm mb-1">
              <TrendingUp className="w-4 h-4" />
              Total Return
            </div>
            <p className={`text-2xl font-bold ${performance.total_return >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {performance.total_return >= 0 ? '+' : ''}{performance.total_return.toFixed(1)}%
            </p>
            <p className="text-xs text-gray-500">
              vs Benchmark: {performance.benchmark_return.toFixed(1)}%
            </p>
          </div>

          <div className="card">
            <div className="flex items-center gap-2 text-gray-500 text-sm mb-1">
              <Activity className="w-4 h-4" />
              Annualized
            </div>
            <p className={`text-2xl font-bold ${performance.annualized_return >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {performance.annualized_return >= 0 ? '+' : ''}{performance.annualized_return.toFixed(1)}%
            </p>
          </div>

          <div className="card">
            <div className="flex items-center gap-2 text-gray-500 text-sm mb-1">
              <Target className="w-4 h-4" />
              Sharpe Ratio
            </div>
            <p className="text-2xl font-bold text-gray-900">
              {performance.sharpe_ratio.toFixed(2)}
            </p>
          </div>

          <div className="card">
            <div className="flex items-center gap-2 text-gray-500 text-sm mb-1">
              <TrendingDown className="w-4 h-4" />
              Max Drawdown
            </div>
            <p className="text-2xl font-bold text-red-600">
              {performance.max_drawdown.toFixed(1)}%
            </p>
          </div>

          <div className="card">
            <div className="text-gray-500 text-sm mb-1">Alpha</div>
            <p className={`text-2xl font-bold ${performance.alpha >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {performance.alpha >= 0 ? '+' : ''}{performance.alpha.toFixed(1)}%
            </p>
          </div>

          <div className="card">
            <div className="text-gray-500 text-sm mb-1">Win Rate</div>
            <p className="text-2xl font-bold text-gray-900">
              {performance.win_rate.toFixed(0)}%
            </p>
          </div>
        </div>
      )}

      {/* Equity Curve */}
      {equityCurve.length > 0 && (
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">Equity Curve</h3>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={equityCurve}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 11 }}
                  tickFormatter={(date) => new Date(date).toLocaleDateString('en-US', { month: 'short', year: '2-digit' })}
                />
                <YAxis
                  tick={{ fontSize: 11 }}
                  tickFormatter={(value) => `$${(value / 1000).toFixed(0)}K`}
                />
                <Tooltip
                  formatter={(value: number) => [`$${value.toLocaleString()}`, '']}
                  labelFormatter={(date) => new Date(date).toLocaleDateString()}
                />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="portfolio_value"
                  name="Strategy"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="benchmark_value"
                  name="S&P 500"
                  stroke="#9ca3af"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Monthly Returns */}
      {monthlyReturns.length > 0 && (
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">Monthly Excess Returns</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={monthlyReturns.slice(-24)}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis
                  dataKey="month"
                  tick={{ fontSize: 10 }}
                  tickFormatter={(month) => month.slice(5)}
                />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip
                  formatter={(value: number) => [`${value.toFixed(2)}%`, '']}
                />
                <Bar
                  dataKey="excess_return"
                  name="Excess Return"
                  fill="#3b82f6"
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
}

export default BacktestPage;

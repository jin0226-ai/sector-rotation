import { useQuery } from '@tanstack/react-query';
import { RefreshCw, AlertTriangle, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { fetchDashboard, fetchHeatmap } from '../services/api';
import SectorRankingTable from '../components/Dashboard/SectorRankingTable';
import MacroStatusPanel from '../components/Dashboard/MacroStatusPanel';
import HeatMap from '../components/Dashboard/HeatMap';
import ScoreTrendsChart from '../components/Dashboard/ScoreTrendsChart';

function DashboardPage() {
  const { data: dashboard, isLoading, error, refetch } = useQuery({
    queryKey: ['dashboard'],
    queryFn: fetchDashboard,
    refetchInterval: 5 * 60 * 1000, // Refetch every 5 minutes
  });

  const { data: heatmap } = useQuery({
    queryKey: ['heatmap'],
    queryFn: fetchHeatmap,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-800">Error loading dashboard data</p>
        <button
          onClick={() => refetch()}
          className="mt-2 text-red-600 hover:text-red-800 text-sm"
        >
          Try again
        </button>
      </div>
    );
  }

  const phaseColors: Record<string, string> = {
    early_cycle: 'bg-green-100 text-green-800',
    mid_cycle: 'bg-blue-100 text-blue-800',
    late_cycle: 'bg-orange-100 text-orange-800',
    recession: 'bg-red-100 text-red-800',
  };

  const phaseLabels: Record<string, string> = {
    early_cycle: 'Early Cycle',
    mid_cycle: 'Mid Cycle',
    late_cycle: 'Late Cycle',
    recession: 'Recession',
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Sector Rotation Dashboard</h1>
          <p className="text-sm text-gray-500 mt-1">
            Last updated: {dashboard?.last_updated
              ? new Date(dashboard.last_updated).toLocaleString()
              : 'N/A'}
          </p>
        </div>
        <button
          onClick={() => refetch()}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {/* Business Cycle & Alerts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Business Cycle */}
        <div className="card">
          <h3 className="text-sm font-medium text-gray-500 mb-2">Business Cycle Phase</h3>
          <div className="flex items-center gap-3">
            <span className={`px-3 py-1 rounded-full text-sm font-medium ${
              phaseColors[dashboard?.business_cycle.phase || 'mid_cycle']
            }`}>
              {phaseLabels[dashboard?.business_cycle.phase || 'mid_cycle']}
            </span>
            <span className="text-sm text-gray-500">
              Confidence: {((dashboard?.business_cycle.confidence || 0) * 100).toFixed(0)}%
            </span>
          </div>
        </div>

        {/* Top Gainers */}
        <div className="card">
          <h3 className="text-sm font-medium text-gray-500 mb-2">Top Gainers Today</h3>
          <div className="space-y-2">
            {dashboard?.top_movers.gainers.map((mover) => (
              <div key={mover.symbol} className="flex items-center justify-between">
                <span className="text-sm font-medium">{mover.symbol}</span>
                <span className="text-green-600 text-sm flex items-center gap-1">
                  <TrendingUp className="w-4 h-4" />
                  +{mover.change.toFixed(2)}%
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Top Losers */}
        <div className="card">
          <h3 className="text-sm font-medium text-gray-500 mb-2">Top Losers Today</h3>
          <div className="space-y-2">
            {dashboard?.top_movers.losers.map((mover) => (
              <div key={mover.symbol} className="flex items-center justify-between">
                <span className="text-sm font-medium">{mover.symbol}</span>
                <span className="text-red-600 text-sm flex items-center gap-1">
                  <TrendingDown className="w-4 h-4" />
                  {mover.change.toFixed(2)}%
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Alerts */}
      {dashboard?.macro_summary.alerts && dashboard.macro_summary.alerts.length > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle className="w-5 h-5 text-yellow-600" />
            <h3 className="font-medium text-yellow-800">Macro Alerts</h3>
          </div>
          <ul className="space-y-1">
            {dashboard.macro_summary.alerts.map((alert, idx) => (
              <li key={idx} className="text-sm text-yellow-700">
                {alert.message}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Main Grid */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {/* Sector Rankings */}
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Sector Rankings</h3>
          {dashboard?.sector_rankings && (
            <SectorRankingTable rankings={dashboard.sector_rankings} />
          )}
        </div>

        {/* Macro Status */}
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Key Macro Indicators</h3>
          {dashboard?.macro_summary.key_indicators && (
            <MacroStatusPanel indicators={dashboard.macro_summary.key_indicators} />
          )}
        </div>
      </div>

      {/* Heatmap */}
      {heatmap && (
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Macro Variables × Sector Sensitivity
          </h3>
          <HeatMap data={heatmap} />
        </div>
      )}

      {/* Score Trends */}
      {dashboard?.score_trends_30d && (
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Sector Score Trends (30 Days)
          </h3>
          <ScoreTrendsChart data={dashboard.score_trends_30d} />
        </div>
      )}
    </div>
  );
}

export default DashboardPage;

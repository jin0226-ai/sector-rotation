import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import type { SectorRanking } from '../../types';

interface Props {
  rankings: SectorRanking[];
}

function SectorRankingTable({ rankings }: Props) {
  const getRecommendationColor = (rec: string) => {
    switch (rec) {
      case 'Overweight':
        return 'text-green-600 bg-green-50';
      case 'Underweight':
        return 'text-red-600 bg-red-50';
      default:
        return 'text-gray-600 bg-gray-50';
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 70) return 'text-green-600';
    if (score >= 40) return 'text-gray-600';
    return 'text-red-600';
  };

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200">
            <th className="text-left py-2 px-2 font-medium text-gray-500">Rank</th>
            <th className="text-left py-2 px-2 font-medium text-gray-500">Sector</th>
            <th className="text-right py-2 px-2 font-medium text-gray-500">Score</th>
            <th className="text-right py-2 px-2 font-medium text-gray-500">Change</th>
            <th className="text-center py-2 px-2 font-medium text-gray-500">Signal</th>
          </tr>
        </thead>
        <tbody>
          {rankings.map((sector) => (
            <tr key={sector.symbol} className="border-b border-gray-100 hover:bg-gray-50">
              <td className="py-3 px-2">
                <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium ${
                  sector.rank <= 3 ? 'bg-green-100 text-green-700' :
                  sector.rank >= 9 ? 'bg-red-100 text-red-700' :
                  'bg-gray-100 text-gray-700'
                }`}>
                  {sector.rank}
                </span>
              </td>
              <td className="py-3 px-2">
                <div>
                  <span className="font-medium">{sector.symbol}</span>
                  <span className="text-gray-500 ml-2 text-xs">{sector.name}</span>
                </div>
              </td>
              <td className="py-3 px-2 text-right">
                <span className={`font-semibold ${getScoreColor(sector.composite_score)}`}>
                  {sector.composite_score.toFixed(1)}
                </span>
              </td>
              <td className="py-3 px-2 text-right">
                {sector.change_1d !== undefined && (
                  <span className={`flex items-center justify-end gap-1 ${
                    sector.change_1d > 0 ? 'text-green-600' :
                    sector.change_1d < 0 ? 'text-red-600' :
                    'text-gray-500'
                  }`}>
                    {sector.change_1d > 0 ? <TrendingUp className="w-4 h-4" /> :
                     sector.change_1d < 0 ? <TrendingDown className="w-4 h-4" /> :
                     <Minus className="w-4 h-4" />}
                    {sector.change_1d > 0 ? '+' : ''}{sector.change_1d?.toFixed(2)}%
                  </span>
                )}
              </td>
              <td className="py-3 px-2 text-center">
                <span className={`px-2 py-1 rounded text-xs font-medium ${getRecommendationColor(sector.recommendation)}`}>
                  {sector.recommendation}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* Score breakdown legend */}
      <div className="mt-4 pt-4 border-t border-gray-100">
        <p className="text-xs text-gray-500 mb-2">Score Components:</p>
        <div className="flex flex-wrap gap-4 text-xs text-gray-600">
          <span>ML Model: 40%</span>
          <span>Business Cycle: 25%</span>
          <span>Momentum: 20%</span>
          <span>Macro Sensitivity: 15%</span>
        </div>
      </div>
    </div>
  );
}

export default SectorRankingTable;

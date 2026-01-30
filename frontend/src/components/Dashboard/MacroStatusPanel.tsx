import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import type { MacroIndicator } from '../../types';

interface Props {
  indicators: MacroIndicator[];
}

function MacroStatusPanel({ indicators }: Props) {
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

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'high':
        return 'bg-red-100 text-red-700';
      case 'low':
        return 'bg-green-100 text-green-700';
      default:
        return 'bg-gray-100 text-gray-700';
    }
  };

  const getPercentileColor = (percentile: number) => {
    if (percentile >= 80) return 'text-red-600';
    if (percentile <= 20) return 'text-green-600';
    return 'text-gray-600';
  };

  return (
    <div className="space-y-3">
      {indicators.map((indicator) => (
        <div
          key={indicator.id}
          className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
        >
          <div className="flex items-center gap-3">
            {getTrendIcon(indicator.trend)}
            <div>
              <p className="font-medium text-sm">{indicator.name}</p>
              <p className="text-xs text-gray-500">{indicator.id}</p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="text-right">
              <p className="font-semibold">
                {typeof indicator.value === 'number'
                  ? indicator.value.toLocaleString(undefined, {
                      maximumFractionDigits: 2,
                    })
                  : indicator.value}
              </p>
              <p className={`text-xs ${getPercentileColor(indicator.percentile)}`}>
                {indicator.percentile?.toFixed(0)}th percentile
              </p>
            </div>

            <span className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(indicator.status)}`}>
              {indicator.status}
            </span>
          </div>
        </div>
      ))}

      {/* Legend */}
      <div className="mt-4 pt-3 border-t border-gray-200">
        <p className="text-xs text-gray-500">
          Percentile shows where current value ranks in historical distribution
        </p>
      </div>
    </div>
  );
}

export default MacroStatusPanel;

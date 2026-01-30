import type { HeatmapData } from '../../types';

interface Props {
  data: HeatmapData;
}

function HeatMap({ data }: Props) {
  const getColor = (value: number) => {
    // Value ranges from -1 to 1
    if (value >= 0.7) return 'bg-green-600 text-white';
    if (value >= 0.4) return 'bg-green-400 text-white';
    if (value >= 0.1) return 'bg-green-200 text-green-800';
    if (value > -0.1) return 'bg-gray-100 text-gray-600';
    if (value > -0.4) return 'bg-red-200 text-red-800';
    if (value > -0.7) return 'bg-red-400 text-white';
    return 'bg-red-600 text-white';
  };

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr>
            <th className="text-left p-2 font-medium text-gray-500 min-w-[120px]">
              Variable
            </th>
            {data.sectors.map((symbol, idx) => (
              <th key={symbol} className="p-2 font-medium text-gray-700 text-center min-w-[60px]">
                <div className="transform -rotate-45 origin-center whitespace-nowrap">
                  {symbol}
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.variables.map((variable, rowIdx) => (
            <tr key={variable}>
              <td className="p-2 font-medium text-gray-600 border-t border-gray-100">
                {variable}
              </td>
              {data.matrix[rowIdx].map((value, colIdx) => (
                <td
                  key={`${rowIdx}-${colIdx}`}
                  className={`p-2 text-center border-t border-gray-100 ${getColor(value)}`}
                  title={`${variable} × ${data.sectors[colIdx]}: ${value.toFixed(2)}`}
                >
                  {value.toFixed(1)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>

      {/* Legend */}
      <div className="mt-4 flex items-center justify-center gap-2">
        <span className="text-xs text-gray-500">Negative</span>
        <div className="flex">
          <div className="w-6 h-4 bg-red-600"></div>
          <div className="w-6 h-4 bg-red-400"></div>
          <div className="w-6 h-4 bg-red-200"></div>
          <div className="w-6 h-4 bg-gray-100"></div>
          <div className="w-6 h-4 bg-green-200"></div>
          <div className="w-6 h-4 bg-green-400"></div>
          <div className="w-6 h-4 bg-green-600"></div>
        </div>
        <span className="text-xs text-gray-500">Positive</span>
      </div>

      <p className="text-xs text-gray-500 text-center mt-2">
        Shows how each sector responds to changes in macro variables
      </p>
    </div>
  );
}

export default HeatMap;

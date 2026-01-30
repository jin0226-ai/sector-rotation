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

      {/* Korean Explanation */}
      <div className="mt-6 p-4 bg-gray-50 rounded-lg text-sm text-gray-700">
        <h4 className="font-semibold text-gray-800 mb-3">📊 수치 해석 방법</h4>
        <div className="mb-4 p-3 bg-white rounded border border-gray-200">
          <p className="mb-2">
            <span className="font-medium text-green-600">양수(+)</span>: 해당 매크로 변수가 상승할 때 해당 섹터에 <strong>긍정적</strong> 영향 (수익률 상승)
          </p>
          <p>
            <span className="font-medium text-red-600">음수(-)</span>: 해당 매크로 변수가 상승할 때 해당 섹터에 <strong>부정적</strong> 영향 (수익률 하락)
          </p>
        </div>

        <h4 className="font-semibold text-gray-800 mb-3">📈 매크로 변수 설명</h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div className="p-2 bg-white rounded border-l-4 border-blue-400">
            <p className="font-medium text-gray-800">Interest Rates (금리)</p>
            <p className="text-xs text-gray-600">연준 기준금리. 상승 시 차입비용 증가, 성장주에 불리</p>
          </div>
          <div className="p-2 bg-white rounded border-l-4 border-blue-400">
            <p className="font-medium text-gray-800">Yield Curve (수익률 곡선)</p>
            <p className="text-xs text-gray-600">장단기 금리차(10년-2년). 역전 시 경기침체 신호</p>
          </div>
          <div className="p-2 bg-white rounded border-l-4 border-green-400">
            <p className="font-medium text-gray-800">GDP Growth (GDP 성장률)</p>
            <p className="text-xs text-gray-600">실질 GDP 성장률. 경기 확장/수축의 핵심 지표</p>
          </div>
          <div className="p-2 bg-white rounded border-l-4 border-orange-400">
            <p className="font-medium text-gray-800">Inflation (인플레이션)</p>
            <p className="text-xs text-gray-600">소비자물가지수(CPI). 고인플레 시 실질수익률 감소</p>
          </div>
          <div className="p-2 bg-white rounded border-l-4 border-red-400">
            <p className="font-medium text-gray-800">Unemployment (실업률)</p>
            <p className="text-xs text-gray-600">실업자 비율. 상승 시 소비 감소, 경기 악화 신호</p>
          </div>
          <div className="p-2 bg-white rounded border-l-4 border-purple-400">
            <p className="font-medium text-gray-800">Consumer Confidence (소비자 신뢰지수)</p>
            <p className="text-xs text-gray-600">소비심리 지표. 상승 시 소비재/경기순환주에 유리</p>
          </div>
          <div className="p-2 bg-white rounded border-l-4 border-yellow-500">
            <p className="font-medium text-gray-800">Oil Prices (유가)</p>
            <p className="text-xs text-gray-600">WTI 원유 가격. 에너지 섹터에 직접적 영향</p>
          </div>
          <div className="p-2 bg-white rounded border-l-4 border-pink-400">
            <p className="font-medium text-gray-800">Credit Spreads (신용 스프레드)</p>
            <p className="text-xs text-gray-600">회사채-국채 금리차. 확대 시 금융위험 증가 신호</p>
          </div>
          <div className="p-2 bg-white rounded border-l-4 border-red-500">
            <p className="font-medium text-gray-800">Financial Stress (금융 스트레스)</p>
            <p className="text-xs text-gray-600">금융시장 불안정성 지수. 상승 시 위험자산 회피</p>
          </div>
          <div className="p-2 bg-white rounded border-l-4 border-teal-400">
            <p className="font-medium text-gray-800">Industrial Production (산업생산)</p>
            <p className="text-xs text-gray-600">제조업 생산지수. 실물경기 활동의 직접 지표</p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default HeatMap;

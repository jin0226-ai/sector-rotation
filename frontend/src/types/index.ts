// Dashboard types
export interface DashboardData {
  last_updated: string | null;
  business_cycle: {
    phase: string;
    confidence: number;
  };
  macro_summary: {
    key_indicators: MacroIndicator[];
    alerts: Alert[];
  };
  sector_rankings: SectorRanking[];
  top_movers: {
    gainers: Mover[];
    losers: Mover[];
  };
  score_trends_30d: ScoreTrends;
}

export interface MacroIndicator {
  id: string;
  name: string;
  value: number;
  trend: string;
  percentile: number;
  status: 'high' | 'low' | 'normal';
  category?: string;
}

export interface Alert {
  indicator: string;
  message: string;
  severity: 'warning' | 'critical';
}

export interface SectorRanking {
  rank: number;
  symbol: string;
  name: string;
  composite_score: number;
  ml_score: number;
  cycle_score: number;
  momentum_score: number;
  macro_sensitivity_score: number;
  recommendation: string;
  price?: number;
  change_1d?: number;
  date?: string;
}

export interface Mover {
  symbol: string;
  name: string;
  change: number;
}

export interface ScoreTrends {
  dates: string[];
  sectors: {
    [symbol: string]: {
      name: string;
      scores: (number | null)[];
    };
  };
}

// Heatmap types
export interface HeatmapData {
  variables: string[];
  variable_ids: string[];
  sectors: string[];
  sector_names: string[];
  matrix: number[][];
}

// Backtest types
export interface BacktestResult {
  backtest_id: string;
  config: BacktestConfig;
  results: BacktestPerformance;
  created_at?: string;
}

export interface BacktestConfig {
  start_date: string;
  end_date?: string;
  initial_capital: number;
  rebalance_frequency: string;
  top_n_sectors: number;
}

export interface BacktestPerformance {
  performance: {
    total_return: number;
    benchmark_return: number;
    excess_return: number;
    annualized_return: number;
    sharpe_ratio: number;
    max_drawdown: number;
    win_rate: number;
    alpha: number;
    beta: number;
  };
  equity_curve: EquityPoint[];
  monthly_returns: MonthlyReturn[];
}

export interface EquityPoint {
  date: string;
  portfolio_value: number;
  benchmark_value: number;
}

export interface MonthlyReturn {
  month: string;
  portfolio_return: number;
  benchmark_return: number;
  excess_return: number;
}

// Sector detail types
export interface SectorDetail {
  symbol: string;
  name: string;
  price: number;
  returns: {
    [period: string]: number;
  };
  technicals: {
    rsi_14: number;
    sma_20: number;
    sma_50: number;
    sma_200: number;
    trend: number;
  };
}

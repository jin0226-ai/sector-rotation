import axios from 'axios';
import type {
  DashboardData,
  HeatmapData,
  BacktestResult,
  SectorRanking,
  MacroIndicator,
} from '../types';

const API_BASE_URL = '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Dashboard
export const fetchDashboard = async (): Promise<DashboardData> => {
  const { data } = await api.get('/dashboard/');
  return data;
};

// Macro data
export const fetchMacroVariables = async (): Promise<MacroIndicator[]> => {
  const { data } = await api.get('/macro/variables');
  return data;
};

export const fetchMacroDashboard = async () => {
  const { data } = await api.get('/macro/dashboard');
  return data;
};

export const fetchMacroHistory = async (variableId: string, startDate?: string) => {
  const params = startDate ? { start_date: startDate } : {};
  const { data } = await api.get(`/macro/variables/${variableId}/history`, { params });
  return data;
};

export const fetchBusinessCycle = async () => {
  const { data } = await api.get('/macro/business-cycle');
  return data;
};

// Sectors
export const fetchSectors = async () => {
  const { data } = await api.get('/sectors/');
  return data;
};

export const fetchSectorDetail = async (symbol: string) => {
  const { data } = await api.get(`/sectors/${symbol}`);
  return data;
};

export const fetchSectorHistory = async (symbol: string, limit = 252) => {
  const { data } = await api.get(`/sectors/${symbol}/history`, { params: { limit } });
  return data;
};

export const fetchRelativePerformance = async (symbol: string) => {
  const { data } = await api.get(`/sectors/${symbol}/relative-performance`);
  return data;
};

// Scores
export const fetchSectorRankings = async (): Promise<SectorRanking[]> => {
  const { data } = await api.get('/scores/rankings');
  return data;
};

export const fetchRankingHistory = async (days = 90) => {
  const { data } = await api.get('/scores/rankings/history', { params: { days } });
  return data;
};

export const fetchHeatmap = async (): Promise<HeatmapData> => {
  const { data } = await api.get('/scores/heatmap');
  return data;
};

export const fetchScoreBreakdown = async (symbol: string) => {
  const { data } = await api.get(`/scores/${symbol}/breakdown`);
  return data;
};

export const fetchScoreTrends = async (days = 180) => {
  const { data } = await api.get('/scores/trends', { params: { days } });
  return data;
};

// Backtest
export const runBacktest = async (config: {
  start_date: string;
  end_date?: string;
  initial_capital: number;
  rebalance_frequency: string;
  top_n_sectors: number;
}): Promise<BacktestResult> => {
  const { data } = await api.post('/backtest/run', config);
  return data;
};

export const fetchBacktestResult = async (backtestId: string): Promise<BacktestResult> => {
  const { data } = await api.get(`/backtest/results/${backtestId}`);
  return data;
};

export const fetchDefaultBacktest = async (): Promise<BacktestResult> => {
  const { data } = await api.get('/backtest/default');
  return data;
};

export const fetchCorrelation = async () => {
  const { data } = await api.get('/backtest/correlation');
  return data;
};

// Data refresh
export const refreshMacroData = async () => {
  const { data } = await api.post('/macro/refresh');
  return data;
};

export const refreshSectorData = async () => {
  const { data } = await api.post('/sectors/refresh');
  return data;
};

export const updateScores = async () => {
  const { data } = await api.post('/scores/update');
  return data;
};

export default api;

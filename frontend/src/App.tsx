import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  TrendingUp,
  BarChart3,
  History,
  Settings,
  Activity,
} from 'lucide-react';
import DashboardPage from './pages/DashboardPage';
import BacktestPage from './pages/BacktestPage';
import SectorsPage from './pages/SectorsPage';
import MacroPage from './pages/MacroPage';

function App() {
  return (
    <BrowserRouter>
      <div className="flex min-h-screen bg-gray-50">
        {/* Sidebar */}
        <aside className="w-64 bg-white border-r border-gray-200 fixed h-full">
          <div className="p-6">
            <h1 className="text-xl font-bold text-gray-800 flex items-center gap-2">
              <Activity className="w-6 h-6 text-blue-600" />
              Sector Rotation
            </h1>
            <p className="text-sm text-gray-500 mt-1">Macro-based Analysis</p>
          </div>

          <nav className="mt-6">
            <NavLink
              to="/"
              className={({ isActive }) =>
                `flex items-center gap-3 px-6 py-3 text-sm font-medium transition-colors ${
                  isActive
                    ? 'text-blue-600 bg-blue-50 border-r-2 border-blue-600'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                }`
              }
            >
              <LayoutDashboard className="w-5 h-5" />
              Dashboard
            </NavLink>

            <NavLink
              to="/sectors"
              className={({ isActive }) =>
                `flex items-center gap-3 px-6 py-3 text-sm font-medium transition-colors ${
                  isActive
                    ? 'text-blue-600 bg-blue-50 border-r-2 border-blue-600'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                }`
              }
            >
              <TrendingUp className="w-5 h-5" />
              Sectors
            </NavLink>

            <NavLink
              to="/macro"
              className={({ isActive }) =>
                `flex items-center gap-3 px-6 py-3 text-sm font-medium transition-colors ${
                  isActive
                    ? 'text-blue-600 bg-blue-50 border-r-2 border-blue-600'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                }`
              }
            >
              <BarChart3 className="w-5 h-5" />
              Macro Data
            </NavLink>

            <NavLink
              to="/backtest"
              className={({ isActive }) =>
                `flex items-center gap-3 px-6 py-3 text-sm font-medium transition-colors ${
                  isActive
                    ? 'text-blue-600 bg-blue-50 border-r-2 border-blue-600'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                }`
              }
            >
              <History className="w-5 h-5" />
              Backtest
            </NavLink>
          </nav>

          <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-gray-200">
            <p className="text-xs text-gray-400 text-center">
              Fidelity Sector Rotation Model
            </p>
          </div>
        </aside>

        {/* Main content */}
        <main className="flex-1 ml-64 p-8">
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/sectors" element={<SectorsPage />} />
            <Route path="/macro" element={<MacroPage />} />
            <Route path="/backtest" element={<BacktestPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;

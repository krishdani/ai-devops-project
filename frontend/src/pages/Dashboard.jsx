import React, { useState, useEffect } from 'react';
import { 
  Activity, 
  AlertCircle, 
  Terminal, 
  ShieldAlert, 
  RefreshCcw,
  Clock
} from 'lucide-react';
import { dashboardService } from '../services/api';
import StatCard from '../components/StatCard';

const Dashboard = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(new Date());

  const fetchData = async () => {
    try {
      const response = await dashboardService.getDashboardData();
      setData(response.data);
      setLastUpdated(new Date());
      setError(null);
    } catch (err) {
      console.error("Dashboard fetch error:", err);
      setError("Failed to fetch dashboard data. Make sure backend is running.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  if (loading && !data) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-200px)]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    );
  }

  const stats = [
    { 
      label: 'Total Logs Processed', 
      value: data?.watcher_stats?.lines_processed || 0, 
      icon: Terminal, 
      color: 'primary' 
    },
    { 
      label: 'Critical Alerts', 
      value: data?.log_level_distribution?.CRITICAL || 0, 
      icon: ShieldAlert, 
      color: 'danger' 
    },
    { 
      label: 'Active Errors', 
      value: data?.log_level_distribution?.ERROR || 0, 
      icon: AlertCircle, 
      color: 'warning' 
    },
    { 
      label: 'AI Analyses', 
      value: data?.watcher_stats?.ai_analyses_run || 0, 
      icon: Activity, 
      color: 'success' 
    },
  ];

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight mb-2">Overview</h2>
          <div className="flex items-center gap-2 text-secondary text-sm">
            <Clock className="w-4 h-4" />
            <span>Last updated: {lastUpdated.toLocaleTimeString()}</span>
          </div>
        </div>
        <button 
          onClick={fetchData}
          className="flex items-center gap-2 px-4 py-2 bg-white/5 hover:bg-white/10 border border-border rounded-lg transition-all"
        >
          <RefreshCcw className="w-4 h-4" />
          <span>Refresh</span>
        </button>
      </div>

      {error && (
        <div className="p-4 bg-danger/10 border border-danger/20 text-danger rounded-xl flex items-center gap-3">
          <AlertCircle className="w-5 h-5" />
          <p>{error}</p>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat, i) => (
          <StatCard key={i} {...stat} />
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* AI Summary Card */}
        <div className="glass rounded-2xl p-8">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-xl font-bold flex items-center gap-2">
              <Activity className="text-primary" />
              Latest AI Assessment
            </h3>
            <span className={`px-3 py-1 rounded-full text-xs font-bold ${
              data?.risk_level === 'CRITICAL' ? 'bg-danger/20 text-danger' :
              data?.risk_level === 'HIGH' ? 'bg-warning/20 text-warning' :
              'bg-success/20 text-success'
            }`}>
              {data?.risk_level || 'UNKNOWN'} RISK
            </span>
          </div>
          
          {data?.latest_analysis ? (
            <div className="space-y-4">
              <p className="text-secondary leading-relaxed">
                {data.latest_analysis.summary}
              </p>
              <div className="grid grid-cols-2 gap-4 pt-4 border-t border-border">
                <div>
                  <p className="text-xs text-secondary uppercase tracking-wider font-bold mb-1">Anomalies</p>
                  <p className="text-xl font-bold">{data.latest_analysis.anomalies?.length || 0}</p>
                </div>
                <div>
                  <p className="text-xs text-secondary uppercase tracking-wider font-bold mb-1">Security Threats</p>
                  <p className="text-xl font-bold">{data.latest_analysis.security_threats?.length || 0}</p>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-12 text-secondary">
              <RefreshCcw className="w-12 h-12 mb-4 opacity-20" />
              <p>Waiting for first AI analysis batch...</p>
            </div>
          )}
        </div>

        {/* System Health Card */}
        <div className="glass rounded-2xl p-8">
          <h3 className="text-xl font-bold mb-6 flex items-center gap-2">
            <ShieldAlert className="text-primary" />
            Service Health
          </h3>
          <div className="space-y-4">
            {Object.entries(data?.config_summary || {}).map(([key, value]) => (
              <div key={key} className="flex items-center justify-between p-3 rounded-xl bg-white/5 border border-border">
                <span className="text-secondary capitalize">{key.replace('_', ' ')}</span>
                <span className={`flex items-center gap-2 text-sm font-bold ${value ? 'text-success' : 'text-secondary'}`}>
                  <div className={`w-2 h-2 rounded-full ${value ? 'bg-success animate-pulse' : 'bg-secondary'}`} />
                  {value ? 'ACTIVE' : 'DISABLED'}
                </span>
              </div>
            ))}
            <div className="flex items-center justify-between p-3 rounded-xl bg-white/5 border border-border">
              <span className="text-secondary">Log Buffer</span>
              <span className="text-sm font-bold">
                {data?.watcher_stats?.buffer_size || 0} / 50 lines
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;

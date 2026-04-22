import React, { useState, useEffect } from 'react';
import { Terminal, Search, Filter, RefreshCcw, AlertTriangle } from 'lucide-react';
import { logsService } from '../services/api';

const Logs = () => {
  const [logs, setLogs] = useState([]);
  const [type, setType] = useState('application');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchLogs = async () => {
    try {
      const response = await logsService.getLogs(type, 100);
      setLogs(response.data.logs);
      setError(null);
    } catch (err) {
      console.error("Logs fetch error:", err);
      setError("Failed to fetch logs.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setLoading(true);
    fetchLogs();
    const interval = setInterval(fetchLogs, 5000);
    return () => clearInterval(interval);
  }, [type]);

  const getLevelColor = (level) => {
    switch (level) {
      case 'CRITICAL': return 'text-danger bg-danger/10';
      case 'ERROR': return 'text-danger bg-danger/10';
      case 'WARNING': return 'text-warning bg-warning/10';
      default: return 'text-secondary bg-white/5';
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-3xl font-bold tracking-tight">Real-time Logs</h2>
        <div className="flex items-center gap-3">
          <div className="flex bg-card border border-border rounded-lg p-1">
            <button
              onClick={() => setType('application')}
              className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${
                type === 'application' ? 'bg-primary text-white shadow-lg' : 'text-secondary hover:text-white'
              }`}
            >
              Application
            </button>
            <button
              onClick={() => setType('security')}
              className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${
                type === 'security' ? 'bg-primary text-white shadow-lg' : 'text-secondary hover:text-white'
              }`}
            >
              Security
            </button>
          </div>
          <button 
            onClick={fetchLogs}
            className="p-2 bg-white/5 hover:bg-white/10 border border-border rounded-lg transition-all"
          >
            <RefreshCcw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      <div className="glass rounded-2xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-border bg-white/5">
                <th className="px-6 py-4 text-xs font-bold text-secondary uppercase tracking-wider">Timestamp</th>
                <th className="px-6 py-4 text-xs font-bold text-secondary uppercase tracking-wider">Level</th>
                <th className="px-6 py-4 text-xs font-bold text-secondary uppercase tracking-wider">Module</th>
                <th className="px-6 py-4 text-xs font-bold text-secondary uppercase tracking-wider">Message</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {logs.length > 0 ? (logs.map((log, i) => (
                <tr key={i} className="hover:bg-white/5 transition-colors group">
                  <td className="px-6 py-4 text-sm text-secondary whitespace-nowrap font-mono">
                    {new Date(log.timestamp).toLocaleTimeString()}
                  </td>
                  <td className="px-6 py-4">
                    <span className={`px-2 py-1 rounded text-[10px] font-bold ${getLevelColor(log.level)}`}>
                      {log.level}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm font-medium text-white/80">
                    {log.module || 'system'}
                  </td>
                  <td className="px-6 py-4 text-sm text-secondary group-hover:text-white transition-colors">
                    {log.message}
                    {log.event_type && (
                      <span className="ml-2 text-[10px] bg-primary/20 text-primary px-1.5 py-0.5 rounded border border-primary/30">
                        {log.event_type}
                      </span>
                    )}
                  </td>
                </tr>
              ))) : (
                <tr>
                  <td colSpan="4" className="px-6 py-12 text-center text-secondary">
                    {loading ? "Loading logs..." : "No logs found."}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default Logs;

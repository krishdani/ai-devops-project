import React, { useState, useEffect } from 'react';
import { AlertTriangle, CheckCircle, Bell, RefreshCcw, Filter } from 'lucide-react';
import { alertsService } from '../services/api';

const Alerts = () => {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState(null);

  const fetchData = async () => {
    try {
      const [alertsRes, statsRes] = await Promise.all([
        alertsService.getAlerts(50),
        alertsService.getStats()
      ]);
      setAlerts(alertsRes.data.alerts);
      setStats(statsRes.data);
    } catch (err) {
      console.error("Alerts fetch error:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleAcknowledge = async (id) => {
    try {
      await alertsService.acknowledgeAlert(id);
      fetchData();
    } catch (err) {
      console.error("Acknowledge error:", err);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  const getSeverityStyles = (severity) => {
    switch (severity) {
      case 'CRITICAL': return 'border-danger/30 bg-danger/5 text-danger';
      case 'ERROR': return 'border-danger/20 bg-danger/5 text-danger';
      case 'WARNING': return 'border-warning/20 bg-warning/5 text-warning';
      default: return 'border-primary/20 bg-primary/5 text-primary';
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight mb-1">Alerts</h2>
          <p className="text-secondary text-sm">Monitor and respond to security threats and system anomalies.</p>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex gap-2">
            <div className="px-4 py-2 glass rounded-lg text-center">
              <p className="text-[10px] text-secondary uppercase font-bold">Unresolved</p>
              <p className="text-xl font-bold text-danger">{stats?.unacknowledged || 0}</p>
            </div>
          </div>
          <button 
            onClick={fetchData}
            className="p-2 bg-white/5 hover:bg-white/10 border border-border rounded-lg transition-all"
          >
            <RefreshCcw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      <div className="space-y-4">
        {alerts.length > 0 ? (
          alerts.map((alert) => (
            <div 
              key={alert.id} 
              className={`glass rounded-2xl p-6 border flex items-start justify-between transition-all hover:scale-[1.01] ${
                alert.acknowledged ? 'opacity-50 grayscale-[0.5]' : getSeverityStyles(alert.severity)
              }`}
            >
              <div className="flex gap-4">
                <div className={`p-3 rounded-xl ${alert.acknowledged ? 'bg-white/5' : 'bg-current/10'}`}>
                  {alert.acknowledged ? <CheckCircle className="w-6 h-6" /> : <AlertTriangle className="w-6 h-6" />}
                </div>
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-[10px] font-black uppercase tracking-widest px-1.5 py-0.5 rounded bg-black/20">
                      {alert.alert_type}
                    </span>
                    <span className="text-xs opacity-60 font-medium">
                      {new Date(alert.timestamp).toLocaleString()}
                    </span>
                  </div>
                  <h4 className="text-lg font-bold mb-1">{alert.message}</h4>
                  <div className="flex items-center gap-4 text-xs opacity-70">
                    <span>Source: <span className="font-bold">{alert.source}</span></span>
                    <span>ID: <span className="font-mono">{alert.id}</span></span>
                  </div>
                </div>
              </div>
              
              {!alert.acknowledged && (
                <button
                  onClick={() => handleAcknowledge(alert.id)}
                  className="px-4 py-2 bg-white/10 hover:bg-white/20 border border-white/10 rounded-lg text-xs font-bold transition-all"
                >
                  ACKNOWLEDGE
                </button>
              )}
            </div>
          ))
        ) : (
          <div className="flex flex-col items-center justify-center py-20 glass rounded-2xl text-secondary">
            <Bell className="w-16 h-16 mb-4 opacity-10" />
            <p className="text-xl font-medium">No active alerts detected</p>
            <p className="text-sm">System is operating within normal parameters.</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default Alerts;

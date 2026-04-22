import React, { useState, useEffect } from 'react';
import { 
  Cpu, 
  Brain, 
  ShieldAlert, 
  Zap, 
  CheckCircle, 
  AlertCircle,
  RefreshCcw,
  Sparkles
} from 'lucide-react';
import { analysisService } from '../services/api';

const Analysis = () => {
  const [analysis, setAnalysis] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState(false);

  const fetchData = async () => {
    try {
      const [latestRes, historyRes] = await Promise.all([
        analysisService.getLatest(),
        analysisService.getHistory(10)
      ]);
      setAnalysis(latestRes.data.message ? null : latestRes.data);
      setHistory(historyRes.data.analyses);
    } catch (err) {
      console.error("Analysis fetch error:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleManualTrigger = async () => {
    setTriggering(true);
    try {
      await analysisService.triggerAnalysis('application', 50);
      fetchData();
    } catch (err) {
      console.error("Trigger error:", err);
    } finally {
      setTriggering(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000); // AI analysis is slower, refresh less often
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <div className="space-y-8 max-w-6xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight mb-1 flex items-center gap-3">
            <Sparkles className="text-primary" />
            AI Insights
          </h2>
          <p className="text-secondary text-sm">Deep analysis of logs using GPT-4o / Claude 3.5 Sonnet.</p>
        </div>
        <button 
          onClick={handleManualTrigger}
          disabled={triggering}
          className="flex items-center gap-2 px-6 py-2.5 bg-primary hover:bg-primary/90 text-white rounded-xl font-bold transition-all disabled:opacity-50"
        >
          {triggering ? <RefreshCcw className="w-5 h-5 animate-spin" /> : <Brain className="w-5 h-5" />}
          <span>{triggering ? 'Analyzing...' : 'Trigger Analysis'}</span>
        </button>
      </div>

      {!analysis ? (
        <div className="glass rounded-3xl p-12 text-center">
          <Cpu className="w-16 h-16 mx-auto mb-6 text-primary/20" />
          <h3 className="text-2xl font-bold mb-2">No Analysis Available</h3>
          <p className="text-secondary mb-8">The AI engine is waiting for the next batch of logs to process.</p>
          <button 
            onClick={handleManualTrigger}
            className="text-primary font-bold hover:underline"
          >
            Trigger manual analysis now &rarr;
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Assessment */}
          <div className="lg:col-span-2 space-y-8">
            <div className="glass rounded-3xl p-8 border-l-4 border-primary shadow-xl">
              <div className="flex items-center justify-between mb-6">
                <span className="text-xs font-black uppercase tracking-widest text-primary bg-primary/10 px-3 py-1 rounded-full">
                  Executive Summary
                </span>
                <div className="flex items-center gap-2 text-secondary text-xs">
                  <Zap className="w-4 h-4" />
                  <span>Powered by {analysis.provider}</span>
                </div>
              </div>
              <p className="text-xl font-medium leading-relaxed text-white/90">
                {analysis.summary}
              </p>
            </div>

            {/* Recommendations */}
            <div className="glass rounded-3xl p-8">
              <h3 className="text-xl font-bold mb-6 flex items-center gap-2">
                <CheckCircle className="text-success" />
                Recommended Actions
              </h3>
              <div className="space-y-4">
                {analysis.recommended_actions?.map((action, i) => (
                  <div key={i} className="flex gap-4 p-4 rounded-2xl bg-white/5 border border-border group hover:border-success/30 transition-all">
                    <div className="w-6 h-6 rounded-full bg-success/20 text-success flex-shrink-0 flex items-center justify-center text-xs font-bold">
                      {i + 1}
                    </div>
                    <p className="text-white/80 group-hover:text-white transition-colors">{action}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Side Panels */}
          <div className="space-y-8">
            {/* Risk Level */}
            <div className="glass rounded-3xl p-8 text-center overflow-hidden relative">
               <div className={`absolute inset-0 opacity-10 blur-3xl ${
                 analysis.risk_level === 'CRITICAL' ? 'bg-danger' : 
                 analysis.risk_level === 'HIGH' ? 'bg-warning' : 'bg-success'
               }`} />
               <h3 className="text-secondary font-bold uppercase tracking-widest text-xs mb-4 relative z-10">Threat Level</h3>
               <p className={`text-5xl font-black mb-4 relative z-10 ${
                 analysis.risk_level === 'CRITICAL' ? 'text-danger' : 
                 analysis.risk_level === 'HIGH' ? 'text-warning' : 'text-success'
               }`}>
                 {analysis.risk_level}
               </p>
               <p className="text-secondary text-sm relative z-10">Based on recent log patterns</p>
            </div>

            {/* Threats Detected */}
            <div className="glass rounded-3xl p-8">
              <h3 className="text-lg font-bold mb-6 flex items-center gap-2">
                <ShieldAlert className="text-danger" />
                Threats & Anomalies
              </h3>
              <div className="space-y-4">
                {[...(analysis.security_threats || []), ...(analysis.anomalies || [])].map((item, i) => (
                  <div key={i} className="p-4 rounded-xl bg-white/5 border border-border">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-[10px] font-black uppercase text-danger">{item.threat_type || item.type}</span>
                      <span className="text-[10px] text-secondary">{item.severity}</span>
                    </div>
                    <p className="text-xs text-white/70">{item.description}</p>
                  </div>
                ))}
                {!analysis.security_threats?.length && !analysis.anomalies?.length && (
                  <p className="text-secondary text-center text-sm py-4">No critical issues found.</p>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* History Table */}
      <div className="space-y-4">
        <h3 className="text-xl font-bold flex items-center gap-2">
          <RefreshCcw className="text-secondary w-5 h-5" />
          Analysis History
        </h3>
        <div className="glass rounded-2xl overflow-hidden">
          <table className="w-full text-left">
            <thead className="bg-white/5 border-b border-border">
              <tr>
                <th className="px-6 py-4 text-xs font-bold text-secondary uppercase tracking-wider">Time</th>
                <th className="px-6 py-4 text-xs font-bold text-secondary uppercase tracking-wider">Risk</th>
                <th className="px-6 py-4 text-xs font-bold text-secondary uppercase tracking-wider">Summary</th>
                <th className="px-6 py-4 text-xs font-bold text-secondary uppercase tracking-wider">Provider</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {history.map((h, i) => (
                <tr key={i} className="hover:bg-white/5 transition-colors">
                  <td className="px-6 py-4 text-sm text-secondary whitespace-nowrap">
                    {new Date(h.analyzed_at).toLocaleTimeString()}
                  </td>
                  <td className="px-6 py-4">
                    <span className={`text-[10px] font-bold px-2 py-1 rounded ${
                      h.risk_level === 'CRITICAL' ? 'bg-danger/10 text-danger' : 
                      h.risk_level === 'HIGH' ? 'bg-warning/10 text-warning' : 'bg-success/10 text-success'
                    }`}>
                      {h.risk_level}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-white/70 line-clamp-1 truncate max-w-md">
                    {h.summary}
                  </td>
                  <td className="px-6 py-4 text-xs text-secondary italic">
                    {h.provider}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default Analysis;

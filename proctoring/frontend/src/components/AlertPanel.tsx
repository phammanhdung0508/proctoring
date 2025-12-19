/**
 * AlertPanel Component
 *
 * Displays real-time alerts and violations detected during proctoring
 */

import { useProctoringStore } from '../stores/proctoringStore';
import type { Alert } from '../types';
import { useRef } from 'react';

export function AlertPanel() {
  const { alerts, unacknowledgedAlerts, acknowledgeAlert, clearAlerts } =
    useProctoringStore();

  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to top when new alerts arrive (since newest are at top)
  // or handle scroll behavior if needed. 
  // Actually, newest first means we stay at top.

  const getAlertIcon = (level: Alert['level']) => {
    switch (level) {
      case 'critical':
        return '🚨';
      case 'high':
        return '⚠️';
      case 'medium':
        return '⚡';
      case 'low':
        return 'ℹ️';
      default:
        return '❓';
    }
  };

  const getAlertStyle = (level: Alert['level']) => {
    switch (level) {
      case 'critical':
        return 'bg-rose-50 border-rose-200 hover:border-rose-300';
      case 'high':
        return 'bg-amber-50 border-amber-200 hover:border-amber-300';
      case 'medium':
        return 'bg-cyan-50 border-cyan-200 hover:border-cyan-300';
      case 'low':
        return 'bg-slate-50 border-slate-200 hover:border-slate-300';
      default:
        return 'bg-slate-50 border-slate-200 hover:border-slate-300';
    }
  };

  const formatTimestamp = (timestamp: number) => {
    return new Date(timestamp * 1000).toLocaleTimeString();
  };

  return (
    <div className="glass rounded-2xl flex flex-col h-full overflow-hidden shadow-lg shadow-slate-200/50" data-testid="alert-panel">
      <div className="px-5 py-4 border-b border-white/50 flex items-center justify-between bg-white/40">
        <div>
          <h3 className="text-sm font-bold uppercase tracking-wider text-slate-800 flex items-center gap-2">
            <span>🛡️</span> Security Events
          </h3>
          {unacknowledgedAlerts > 0 && (
            <span className="text-[10px] text-amber-600 font-bold animate-pulse mt-0.5 block">
              {unacknowledgedAlerts} New Attention Required
            </span>
          )}
        </div>
        {alerts.length > 0 && (
          <button
            onClick={clearAlerts}
            data-testid="clear-alerts-btn"
            className="text-xs px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-slate-600 hover:bg-slate-50 hover:text-slate-900 transition-colors shadow-sm font-semibold"
          >
            Clear Log
          </button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3 custom-scrollbar" data-testid="alert-list">
        {alerts.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-slate-400 space-y-3 p-8">
            <div className="w-16 h-16 rounded-full bg-slate-50 flex items-center justify-center text-3xl opacity-50">
              ✅
            </div>
            <div className="text-center">
              <p className="text-sm font-medium text-slate-500">No Violations Detected</p>
              <p className="text-xs text-slate-400 mt-1">System is monitoring for suspicious activity.</p>
            </div>
          </div>
        ) : (
          alerts.map((alert) => (
            <div
              key={alert.id}
              data-testid={`alert-item-${alert.level}`}
              className={`border-l-4 rounded-r-xl p-4 transition-all duration-300 animate-in fade-in slide-in-from-top-2 ${getAlertStyle(alert.level)} ${alert.level === 'critical' ? 'border-l-rose-500' :
                alert.level === 'high' ? 'border-l-amber-500' :
                  alert.level === 'medium' ? 'border-l-cyan-500' :
                    'border-l-slate-400'
                } ${alert.acknowledged ? 'opacity-60 grayscale-[0.5]' : 'shadow-sm hover:shadow-md hover:-translate-y-0.5'}`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1.5">
                    <span className="text-xl" role="img" aria-label="alert icon">{getAlertIcon(alert.level)}</span>
                    <span className="text-xs font-bold uppercase tracking-wide opacity-70">
                      {formatTimestamp(alert.timestamp)}
                    </span>
                    {!alert.acknowledged && (
                      <span className="w-2 h-2 rounded-full bg-rose-500 animate-pulse ml-auto sm:ml-0" />
                    )}
                  </div>

                  <h4 className="text-sm font-bold text-slate-900 mb-1 leading-tight">
                    {alert.message}
                  </h4>

                  {/* Violations List */}
                  {alert.violations.length > 0 && (
                    <ul className="mt-2 space-y-1 bg-white/50 rounded-lg p-2">
                      {alert.violations.map((violation, idx) => (
                        <li key={idx} className="flex items-start text-xs text-slate-700">
                          <span className="mr-1.5 text-slate-400">•</span>
                          <span>{violation}</span>
                        </li>
                      ))}
                    </ul>
                  )}

                  <div className="mt-3 flex items-center justify-between">
                    {/* Risk Score Pill */}
                    <div className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${alert.risk_score >= 70 ? 'bg-rose-100 text-rose-700 border-rose-200' :
                      alert.risk_score >= 40 ? 'bg-amber-100 text-amber-700 border-amber-200' :
                        'bg-emerald-100 text-emerald-700 border-emerald-200'
                      }`}>
                      RISK SCORE: {alert.risk_score.toFixed(0)}
                    </div>

                    {!alert.acknowledged && (
                      <button
                        onClick={() => acknowledgeAlert(alert.id)}
                        data-testid={`acknowledge-btn-${alert.id}`}
                        className="text-[10px] font-bold uppercase tracking-wider text-slate-500 hover:text-slate-900 underline decoration-slate-300 hover:decoration-slate-900 underline-offset-2 transition-all"
                      >
                        Acknowledge
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}

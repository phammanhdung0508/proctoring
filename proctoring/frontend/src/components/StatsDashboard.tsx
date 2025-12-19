/**
 * StatsDashboard Component
 *
 * Displays real-time statistics and metrics from the proctoring session
 */

import { useMemo } from 'react';
import { XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts';
import { useProctoringStore } from '../stores/proctoringStore';

export function StatsDashboard() {
  const { session, latestAnalysis, analysisHistory, avgProcessingTime } =
    useProctoringStore();

  // Prepare chart data from history
  const riskScoreHistory = useMemo(() => {
    return analysisHistory
      .slice(0, 50)
      .reverse()
      .map((analysis, idx) => ({
        index: idx,
        score: analysis.risk.risk_score,
      }));
  }, [analysisHistory]);

  if (!session) {
    return (
      <div className="glass rounded-xl p-8 text-center text-slate-500" data-testid="stats-no-session">
        <div className="text-4xl mb-4 grayscale opacity-50">📊</div>
        <div className="text-sm font-medium">No active session data</div>
        <div className="text-xs text-slate-400 mt-1">Start monitoring to see real-time analytics</div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="stats-dashboard">
      <div className="flex flex-wrap items-center justify-between gap-3 px-1">
        <div>
          <h3 className="text-lg font-bold text-slate-900">Session Analytics</h3>
          <p className="text-sm text-slate-500">Real-time signals from detection engine</p>
        </div>
        <div className="px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-xs font-bold text-slate-600 shadow-sm flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
          LIVE UPDATE
        </div>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Risk Score Chart */}
        <div className="lg:col-span-2 glass p-6 rounded-2xl shadow-sm">
          <div className="flex items-center justify-between gap-3 mb-6">
            <div>
              <p className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-1">Risk Trend</p>
              <h3 className="text-lg font-bold text-slate-900">
                Live Risk Analysis
              </h3>
            </div>
          </div>

          <div className="h-[250px] w-full" data-testid="risk-chart">
            {riskScoreHistory.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={riskScoreHistory}>
                  <defs>
                    <linearGradient id="colorRisk" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.2} />
                      <stop offset="95%" stopColor="#f43f5e" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                  <XAxis dataKey="index" hide />
                  <YAxis domain={[0, 100]} hide />
                  <Tooltip
                    contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)', background: 'rgba(255, 255, 255, 0.9)' }}
                    itemStyle={{ color: '#0f172a', fontWeight: 600, fontSize: '13px' }}
                    formatter={(value: number) => [`${value.toFixed(1)}`, 'Risk Score']}
                    labelStyle={{ display: 'none' }}
                  />
                  <Area
                    type="monotone"
                    dataKey="score"
                    stroke="#f43f5e"
                    strokeWidth={3}
                    fillOpacity={1}
                    fill="url(#colorRisk)"
                    animationDuration={500}
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-slate-400 bg-slate-50/50 rounded-xl border border-dashed border-slate-200">
                Waiting for data stream...
              </div>
            )}
          </div>
        </div>

        {/* Pipeline Health */}
        <div className="glass p-6 rounded-2xl shadow-sm space-y-6">
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-1">System Health</p>
            <h3 className="text-lg font-bold text-slate-900">Pipeline Stats</h3>
          </div>

          <div className="space-y-4">
            <div className="p-4 rounded-xl bg-white/50 border border-white/60">
              <p className="text-xs text-slate-500 mb-1">Avg Processing Latency</p>
              <div className="flex items-baseline gap-1">
                <span className="text-2xl font-bold text-slate-900">{avgProcessingTime.toFixed(0)}</span>
                <span className="text-xs font-semibold text-slate-500">ms</span>
              </div>
              <div className="w-full bg-slate-200 h-1.5 rounded-full mt-2 overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-300 ${avgProcessingTime > 200 ? 'bg-amber-500' : 'bg-emerald-500'}`}
                  style={{ width: `${Math.min((avgProcessingTime / 500) * 100, 100)}%` }}
                ></div>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-white/50 border border-white/60">
              <p className="text-xs text-slate-500 mb-1">Total Violations</p>
              <div className="flex items-baseline gap-1">
                <span className="text-2xl font-bold text-rose-600">{session.total_violations}</span>
                <span className="text-xs font-semibold text-slate-500">detected</span>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-white/50 border border-white/60">
              <p className="text-xs text-slate-500 mb-1">Active Alerts</p>
              <div className="flex items-baseline gap-1">
                <span className="text-2xl font-bold text-amber-600">{session.alerts.length}</span>
                <span className="text-xs font-semibold text-slate-500">pending</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Latest Analysis Details */}
      {latestAnalysis && (
        <div className="glass p-6 rounded-2xl shadow-sm" data-testid="latest-analysis">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="text-lg font-bold text-slate-900">
                Live Frame Breakdown
              </h3>
            </div>
            <div className="px-3 py-1 rounded-full bg-slate-100 text-xs font-mono font-medium text-slate-600">
              TS: {new Date(latestAnalysis.metadata.timestamp * 1000).toLocaleTimeString()}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Gaze */}
            <div className="bg-white/60 rounded-xl p-4 border border-white/60 hover:shadow-md transition-shadow">
              <div className="text-sm font-bold text-slate-800 mb-3 flex items-center gap-2">
                <span className="bg-blue-100 text-blue-700 p-1.5 rounded-lg text-lg">👁️</span>
                Gaze Analysis
              </div>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between items-center p-2 rounded-lg bg-slate-50">
                  <span className="text-slate-600">Face</span>
                  <span className={`font-bold px-2 py-0.5 rounded text-xs ${latestAnalysis.gaze.face_detected ? 'bg-emerald-100 text-emerald-700' : 'bg-rose-100 text-rose-700'}`}>
                    {latestAnalysis.gaze.face_detected ? 'DETECTED' : 'MISSING'}
                  </span>
                </div>
                <div className="flex justify-between items-center p-2 rounded-lg bg-slate-50">
                  <span className="text-slate-600">Focus</span>
                  <span className={`font-bold px-2 py-0.5 rounded text-xs ${latestAnalysis.gaze.deviation ? 'bg-rose-100 text-rose-700' : 'bg-emerald-100 text-emerald-700'}`}>
                    {latestAnalysis.gaze.deviation ? 'DISTRACTED' : 'FOCUSED'}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-2 mt-2">
                  <div className="text-center p-2 bg-slate-50 rounded-lg">
                    <div className="text-[10px] text-slate-400 uppercase">Yaw</div>
                    <div className="font-mono font-semibold">{latestAnalysis.gaze.yaw.toFixed(1)}°</div>
                  </div>
                  <div className="text-center p-2 bg-slate-50 rounded-lg">
                    <div className="text-[10px] text-slate-400 uppercase">Pitch</div>
                    <div className="font-mono font-semibold">{latestAnalysis.gaze.pitch.toFixed(1)}°</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Objects */}
            <div className="bg-white/60 rounded-xl p-4 border border-white/60 hover:shadow-md transition-shadow">
              <div className="text-sm font-bold text-slate-800 mb-3 flex items-center gap-2">
                <span className="bg-purple-100 text-purple-700 p-1.5 rounded-lg text-lg">📱</span>
                Object Detection
              </div>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between items-center p-2 rounded-lg bg-slate-50">
                  <span className="text-slate-600">Persons</span>
                  <span className={`font-bold px-2 py-0.5 rounded text-xs ${latestAnalysis.objects.person_count > 1 ? 'bg-rose-100 text-rose-700' : 'bg-slate-200 text-slate-700'}`}>
                    {latestAnalysis.objects.person_count}
                  </span>
                </div>
                <div className="flex justify-between items-start p-2 rounded-lg bg-slate-50 min-h-[60px]">
                  <span className="text-slate-600">Forbidden</span>
                  <div className="text-right">
                    {latestAnalysis.objects.forbidden_items.length > 0 ? (
                      <div className="flex flex-col gap-1 items-end">
                        {latestAnalysis.objects.forbidden_items.map((item, idx) => (
                          <span key={idx} className="text-xs font-bold text-rose-600 bg-rose-50 px-1.5 py-0.5 rounded border border-rose-100">
                            {item.object}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span className="text-xs font-bold text-emerald-600 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-100">NONE</span>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Behavior */}
            <div className="bg-white/60 rounded-xl p-4 border border-white/60 hover:shadow-md transition-shadow">
              <div className="text-sm font-bold text-slate-800 mb-3 flex items-center gap-2">
                <span className="bg-amber-100 text-amber-700 p-1.5 rounded-lg text-lg">📈</span>
                Behavior Metrics
              </div>
              <div className="space-y-2 text-sm">
                <div className="p-3 rounded-lg bg-slate-50 mb-2">
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-slate-500">Pattern Suspicion Score</span>
                    <span className="font-bold text-slate-900">{latestAnalysis.behavior.pattern_score.toFixed(0)}/100</span>
                  </div>
                  <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${latestAnalysis.behavior.pattern_score > 50 ? 'bg-rose-500' : 'bg-emerald-500'}`}
                      style={{ width: `${Math.min(latestAnalysis.behavior.pattern_score, 100)}%` }}
                    />
                  </div>
                </div>

                <div className="text-xs text-slate-500 italic p-2 border-l-2 border-slate-200 bg-slate-50/50">
                  "{latestAnalysis.behavior.analysis_summary || 'No anomaly detected.'}"
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

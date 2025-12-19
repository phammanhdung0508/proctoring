/**
 * Main App Component
 *
 * Proctoring Dashboard - integrates all components
 */

import { useEffect, useState } from 'react';
import { VideoCapture } from './components/VideoCapture';
import { AlertPanel } from './components/AlertPanel';
import { StatsDashboard } from './components/StatsDashboard';
import { createWebSocketClient } from './services/websocket';
import { useProctoringStore } from './stores/proctoringStore';
import type { AnalysisMessage } from './types';

// Configuration
const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws';
const DEFAULT_SESSION_ID = `session-${Date.now()}`;

function App() {
  const [sessionId] = useState(DEFAULT_SESSION_ID);
  const [isMonitoring, setIsMonitoring] = useState(false);

  const {
    session,
    isConnected,
    startSession,
    endSession,
    setConnected,
    updateAnalysis,
    reset,
  } = useProctoringStore();

  // Initialize WebSocket client once
  const [wsClient] = useState(() => {
    return createWebSocketClient({
      url: WS_URL,
      sessionId,
      onConnected: () => {
        console.log('✅ WebSocket connected');
        setConnected(true);
      },
      onAnalysis: (message: AnalysisMessage) => {
        console.log('📊 Analysis received:', message);
        updateAnalysis({
          gaze: message.gaze,
          objects: message.objects,
          behavior: message.behavior,
          risk: message.risk,
          metadata: message.metadata,
        });
      },
      onError: (error: Error) => {
        console.error('❌ WebSocket error:', error);
      },
      onDisconnected: () => {
        console.log('🔌 WebSocket disconnected');
        setConnected(false);
      },
      reconnectInterval: 3000,
      maxReconnectAttempts: 5,
    });
  });

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      wsClient?.disconnect();
    };
  }, [wsClient]);

  // Handle start monitoring
  const handleStartMonitoring = () => {
    if (!wsClient) return;

    // Connect WebSocket
    wsClient.connect();

    // Start session in store
    startSession(sessionId);
    setIsMonitoring(true);
  };

  // Handle stop monitoring
  const handleStopMonitoring = () => {
    if (!wsClient) return;

    // Disconnect WebSocket
    wsClient.disconnect();

    // End session in store
    endSession();
    setIsMonitoring(false);
  };

  // Handle reset
  const handleReset = () => {
    handleStopMonitoring();
    reset();
  };

  const riskScore = session?.current_risk_score ?? 0;
  const maxRiskScore = session?.max_risk_score ?? 0;
  const totalFrames = session?.total_frames ?? 0;
  // Removed unused totalViolations
  const sessionDurationMinutes = session && session.started_at
    ? Math.max(0, Math.floor((Date.now() - session.started_at) / 60000))
    : 0;

  return (
    <div className="relative min-h-screen overflow-hidden selection:bg-cyan-200 selection:text-cyan-900" data-testid="app-root">
      {/* Dynamic Background */}
      <div className="fixed inset-0 z-0">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_left,_var(--tw-gradient-stops))] from-indigo-100 via-slate-50 to-white" />
        <div className="absolute top-[-10%] left-[-10%] w-[500px] h-[500px] bg-purple-200/30 rounded-full blur-[100px] animate-pulse-subtle" />
        <div className="absolute top-[20%] right-[-5%] w-[400px] h-[400px] bg-cyan-200/30 rounded-full blur-[80px] animate-pulse-subtle delay-1000" />
        <div className="absolute bottom-[-10%] left-[20%] w-[600px] h-[600px] bg-blue-100/40 rounded-full blur-[120px] animate-pulse-subtle delay-2000" />
        <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-20 brightness-100 contrast-150 mix-blend-overlay" />
      </div>

      <div className="relative z-10 max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">

        {/* Navigation Bar */}
        <nav className="glass rounded-2xl p-4 flex flex-wrap items-center justify-between gap-4 sticky top-4 z-50 transition-all duration-300">
          <div className="flex items-center gap-4">
            <div className="h-12 w-12 rounded-xl bg-slate-900 text-white flex items-center justify-center shadow-lg shadow-slate-900/20 group cursor-default">
              <span className="text-xl group-hover:scale-110 transition-transform duration-300">👁️</span>
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-[0.25em] font-bold text-slate-500 mb-0.5">Sentinel AI</p>
              <h1 className="text-lg font-bold text-slate-900 leading-none">Proctoring Interface</h1>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="hidden md:flex items-center gap-2 px-4 py-2 rounded-xl bg-white/50 border border-white/60 text-xs font-semibold text-slate-600 shadow-sm" data-testid="session-id-display">
              <span className="w-2 h-2 rounded-full bg-slate-400"></span>
              ID: {sessionId.slice(-8)}
            </div>

            <div
              className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold border transition-all duration-300 ${isConnected
                ? 'bg-emerald-50/80 text-emerald-700 border-emerald-200 shadow-sm shadow-emerald-100'
                : 'bg-amber-50/80 text-amber-700 border-amber-200'
                }`}
              data-testid="connection-status"
            >
              <span className={`w-2.5 h-2.5 rounded-full ${isConnected ? 'bg-emerald-500 animate-pulse' : 'bg-amber-500'}`} />
              {isConnected ? 'System Online' : 'Connecting...'}
            </div>
          </div>
        </nav>

        {/* Dashboard Header Stats */}
        <header className="grid grid-cols-2 md:grid-cols-4 gap-4" data-testid="header-stats">
          <div className="glass-card p-5 rounded-2xl group hover:-translate-y-1 transition-transform">
            <p className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Status</p>
            <div className="flex items-center justify-between">
              <p className="text-2xl font-bold text-slate-900" data-testid="status-text">
                {session?.status === 'active' ? 'Active' : 'Standby'}
              </p>
              <div className={`h-8 w-8 rounded-full flex items-center justify-center text-lg ${isMonitoring ? 'bg-emerald-100 text-emerald-600' : 'bg-slate-100 text-slate-400'}`}>
                {isMonitoring ? '⚡' : '💤'}
              </div>
            </div>
          </div>

          <div className="glass-card p-5 rounded-2xl group hover:-translate-y-1 transition-transform">
            <p className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Risk Level</p>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-2xl font-bold text-slate-900" data-testid="risk-score-display">{riskScore.toFixed(0)}</p>
                {maxRiskScore > 0 && <span className="text-xs text-slate-500">Peak: {maxRiskScore.toFixed(0)}</span>}
              </div>
              <div
                className={`h-2 w-16 mobile-hidden rounded-full overflow-hidden bg-slate-100 border border-slate-200`}
              >
                <div
                  className={`h-full transition-all duration-500 ${riskScore > 70 ? 'bg-rose-500' : riskScore > 30 ? 'bg-amber-500' : 'bg-emerald-500'
                    }`}
                  style={{ width: `${Math.min(riskScore, 100)}%` }}
                />
              </div>
            </div>
          </div>

          <div className="glass-card p-5 rounded-2xl group hover:-translate-y-1 transition-transform">
            <p className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Processed</p>
            <div className="flex items-center justify-between">
              <p className="text-2xl font-bold text-slate-900" data-testid="total-frames-display">{totalFrames}</p>
              <span className="text-xs px-2 py-1 rounded-md bg-slate-100 text-slate-600 font-mono">FRAMES</span>
            </div>
          </div>

          <div className="glass-card p-5 rounded-2xl group hover:-translate-y-1 transition-transform">
            <p className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Duration</p>
            <div className="flex items-center justify-between">
              <p className="text-2xl font-bold text-slate-900" data-testid="duration-display">{sessionDurationMinutes}m</p>
              <span className="text-xs px-2 py-1 rounded-md bg-slate-100 text-slate-600">LIVE</span>
            </div>
          </div>
        </header>

        {/* Main Content Areas */}
        <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">

          {/* Left Column: Video & Controls */}
          <div className="xl:col-span-8 space-y-6">

            {/* Control Bar */}
            <div className="glass p-4 rounded-2xl flex flex-wrap items-center justify-between gap-4">
              <div>
                <h2 className="text-lg font-bold text-slate-900">Live Session Control</h2>
                <p className="text-sm text-slate-500">Manage video feed and detection analysis</p>
              </div>
              <div className="flex items-center gap-3">
                {!isMonitoring ? (
                  <button
                    onClick={handleStartMonitoring}
                    data-testid="start-monitoring-btn"
                    className="px-6 py-2.5 bg-slate-900 hover:bg-slate-800 text-white font-bold rounded-xl shadow-lg shadow-slate-900/20 hover:shadow-xl hover:shadow-slate-900/30 active:scale-95 transition-all duration-200 flex items-center gap-2 group"
                  >
                    <span>Start Monitoring</span>
                    <span className="group-hover:translate-x-0.5 transition-transform">→</span>
                  </button>
                ) : (
                  <>
                    <button
                      onClick={handleReset}
                      data-testid="reset-btn"
                      className="px-5 py-2.5 bg-white hover:bg-slate-50 text-slate-700 font-bold rounded-xl border border-slate-200 shadow-sm hover:shadow active:scale-95 transition-all duration-200"
                    >
                      Reset
                    </button>
                    <button
                      onClick={handleStopMonitoring}
                      data-testid="stop-monitoring-btn"
                      className="px-6 py-2.5 bg-rose-500 hover:bg-rose-600 text-white font-bold rounded-xl shadow-lg shadow-rose-500/30 hover:shadow-xl hover:shadow-rose-500/40 active:scale-95 transition-all duration-200"
                    >
                      Stop Session
                    </button>
                  </>
                )}
              </div>
            </div>

            <VideoCapture
              wsClient={wsClient}
              isActive={isMonitoring && isConnected}
              targetFPS={5}
            />

            <StatsDashboard />
          </div>

          {/* Right Column: Alerts & Side Panel */}
          <aside className="xl:col-span-4 h-full min-h-[500px] flex flex-col gap-6">
            <AlertPanel />

            {/* Quick Legend / Info */}
            <div className="glass p-5 rounded-2xl space-y-4">
              <h3 className="text-sm font-bold uppercase tracking-wider text-slate-400">System Legend</h3>
              <div className="space-y-3">
                <div className="flex items-center gap-3 text-sm">
                  <span className="w-3 h-3 rounded-full bg-emerald-500 shadow-sm shadow-emerald-200"></span>
                  <span className="font-medium text-slate-700">Normal Behavior</span>
                </div>
                <div className="flex items-center gap-3 text-sm">
                  <span className="w-3 h-3 rounded-full bg-amber-500 shadow-sm shadow-amber-200"></span>
                  <span className="font-medium text-slate-700">Warning (Suspicious)</span>
                </div>
                <div className="flex items-center gap-3 text-sm">
                  <span className="w-3 h-3 rounded-full bg-rose-500 shadow-sm shadow-rose-200"></span>
                  <span className="font-medium text-slate-700">Critical Violation</span>
                </div>
              </div>
            </div>
          </aside>

        </div>
      </div>
    </div>
  );
}

export default App;


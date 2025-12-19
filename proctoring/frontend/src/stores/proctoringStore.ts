/**
 * Proctoring Store
 *
 * Global state management for the proctoring session using Zustand
 */

import { create } from 'zustand';
import type {
  AnalysisResults,
  Alert,
  ProctoringSession,
} from '../types';

interface ProctoringState {
  // Session management
  session: ProctoringSession | null;
  isConnected: boolean;

  // Analysis data
  latestAnalysis: AnalysisResults | null;
  analysisHistory: AnalysisResults[];

  // Alerts
  alerts: Alert[];
  unacknowledgedAlerts: number;

  // Performance metrics
  avgProcessingTime: number;
  frameCount: number;

  // Actions
  startSession: (sessionId: string) => void;
  endSession: () => void;
  setConnected: (connected: boolean) => void;
  updateAnalysis: (analysis: AnalysisResults) => void;
  addAlert: (alert: Alert) => void;
  acknowledgeAlert: (alertId: string) => void;
  clearAlerts: () => void;
  reset: () => void;
}

const initialSession: ProctoringSession = {
  id: '',
  started_at: Date.now(),
  status: 'idle',
  total_frames: 0,
  total_violations: 0,
  current_risk_score: 0,
  max_risk_score: 0,
  alerts: [],
};

export const useProctoringStore = create<ProctoringState>((set) => ({
  // Initial state
  session: null,
  isConnected: false,
  latestAnalysis: null,
  analysisHistory: [],
  alerts: [],
  unacknowledgedAlerts: 0,
  avgProcessingTime: 0,
  frameCount: 0,

  // Start a new proctoring session
  startSession: (sessionId: string) => {
    set({
      session: {
        ...initialSession,
        id: sessionId,
        started_at: Date.now(),
        status: 'active',
      },
      analysisHistory: [],
      alerts: [],
      unacknowledgedAlerts: 0,
      frameCount: 0,
      latestAnalysis: null,
    });
  },

  // End the current session
  endSession: () => {
    set((state) => ({
      session: state.session
        ? { ...state.session, status: 'ended' }
        : null,
    }));
  },

  // Set connection status
  setConnected: (connected: boolean) => {
    set({ isConnected: connected });
  },

  // Update with new analysis results
  updateAnalysis: (analysis: AnalysisResults) => {
    set((state) => {
      const newFrameCount = state.frameCount + 1;
      const currentSession = state.session;

      if (!currentSession) return state;

      // Update session with new data
      const updatedSession: ProctoringSession = {
        ...currentSession,
        total_frames: newFrameCount,
        total_violations:
          currentSession.total_violations + analysis.risk.violation_count,
        current_risk_score: analysis.risk.risk_score,
        max_risk_score: Math.max(
          currentSession.max_risk_score,
          analysis.risk.risk_score
        ),
      };

      // Add to history (keep last 100 results)
      const newHistory = [analysis, ...state.analysisHistory].slice(0, 100);

      // Calculate average processing time
      const newAvgTime =
        (state.avgProcessingTime * state.frameCount +
          analysis.metadata.processing_time_ms) /
        newFrameCount;

      // Create alert only for HIGH and CRITICAL violations
      // HIGH: Phone detection, multiple faces, looking at another screen
      // CRITICAL: Multiple concurrent violations
      let newAlerts = state.alerts;
      let newUnacknowledged = state.unacknowledgedAlerts;

      if (
        analysis.risk.alert_level === 'high' ||
        analysis.risk.alert_level === 'critical'
      ) {
        const alert: Alert = {
          id: `alert-${Date.now()}-${Math.random()}`,
          timestamp: analysis.metadata.timestamp,
          level: analysis.risk.alert_level,
          message: analysis.risk.violations.join(', '),
          violations: analysis.risk.violations,
          risk_score: analysis.risk.risk_score,
          acknowledged: false,
        };

        newAlerts = [alert, ...state.alerts];
        newUnacknowledged = state.unacknowledgedAlerts + 1;
        updatedSession.alerts = newAlerts;
      }

      return {
        session: updatedSession,
        latestAnalysis: analysis,
        analysisHistory: newHistory,
        frameCount: newFrameCount,
        avgProcessingTime: newAvgTime,
        alerts: newAlerts,
        unacknowledgedAlerts: newUnacknowledged,
      };
    });
  },

  // Manually add an alert
  addAlert: (alert: Alert) => {
    set((state) => ({
      alerts: [alert, ...state.alerts],
      unacknowledgedAlerts: state.unacknowledgedAlerts + 1,
    }));
  },

  // Acknowledge an alert
  acknowledgeAlert: (alertId: string) => {
    set((state) => {
      const alerts = state.alerts.map((alert) =>
        alert.id === alertId ? { ...alert, acknowledged: true } : alert
      );

      const unacknowledged = alerts.filter((a) => !a.acknowledged).length;

      return {
        alerts,
        unacknowledgedAlerts: unacknowledged,
      };
    });
  },

  // Clear all alerts
  clearAlerts: () => {
    set({
      alerts: [],
      unacknowledgedAlerts: 0,
    });
  },

  // Reset entire state
  reset: () => {
    set({
      session: null,
      isConnected: false,
      latestAnalysis: null,
      analysisHistory: [],
      alerts: [],
      unacknowledgedAlerts: 0,
      avgProcessingTime: 0,
      frameCount: 0,
    });
  },
}));

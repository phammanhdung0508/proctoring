/**
 * Type definitions for the AI Proctoring System frontend
 */

// Gaze detection results
export interface GazeResults {
  face_detected: boolean;
  deviation: boolean;
  yaw: number;
  pitch: number;
  roll: number;
  deviation_duration: number;
  landmarks_count: number;
  confidence: number;
}

// Object detection results
export interface ForbiddenItem {
  object: string;
  confidence: number;
  bbox: [number, number, number, number]; // [x1, y1, x2, y2]
  class_name: string;
}

export interface ObjectResults {
  person_count: number;
  forbidden_items: ForbiddenItem[];
  all_detections: Array<{
    class_id: number;
    class_name: string;
    confidence: number;
    bbox: [number, number, number, number];
  }>;
  confidence: number;
}

// Behavior analysis results
export interface BehaviorResults {
  repeated_deviations: number;
  repeated_objects: number;
  pattern_score: number;
  avg_person_count: number;
  analysis_summary: string;
  window_frames: number;
}

// Risk scoring results
export interface RiskResults {
  risk_score: number;
  violation_count: number;
  violations: string[];
  alert_level: 'low' | 'medium' | 'high' | 'critical' | 'error';
  recommendations: string[];
  details: {
    base_score: number;
    gaze_contribution: number;
    object_contribution: number;
    person_contribution: number;
    behavior_contribution: number;
    multiplier_applied: boolean;
    person_count: number;
    forbidden_items_count: number;
  };
}

// Analysis metadata
export interface AnalysisMetadata {
  session_id: string;
  timestamp: number;
  processing_time_ms: number;
  avg_processing_time_ms: number;
  frame_within_timeout: boolean;
  error?: string;
}

// Complete analysis results from backend
export interface AnalysisResults {
  gaze: GazeResults;
  objects: ObjectResults;
  behavior: BehaviorResults;
  risk: RiskResults;
  metadata: AnalysisMetadata;
}

// WebSocket message types
export type WebSocketMessageType =
  | 'connected'
  | 'frame'
  | 'analysis'
  | 'ping'
  | 'pong'
  | 'get_stats'
  | 'stats'
  | 'error';

export interface WebSocketMessage {
  type: WebSocketMessageType;
  session_id?: string;
  message?: string;
  timestamp?: number;
  data?: unknown;
}

// Frame message from client to server
export interface FrameMessage extends WebSocketMessage {
  type: 'frame';
  data: string; // Base64-encoded JPEG
  timestamp: number;
}

// Analysis message from server to client
export interface AnalysisMessage extends WebSocketMessage {
  type: 'analysis';
  session_id: string;
  gaze: GazeResults;
  objects: ObjectResults;
  behavior: BehaviorResults;
  risk: RiskResults;
  metadata: AnalysisMetadata;
}

// Session statistics
export interface SessionStats {
  session_id: string;
  behavior_statistics: {
    total_frames_analyzed: number;
    total_gaze_deviations: number;
    total_object_detections: number;
    avg_person_count: number;
  };
  scoring_config: {
    secondary_person_weight: number;
    forbidden_object_weight: number;
    gaze_deviation_weight: number;
    multiple_violations_multiplier: number;
  };
  performance: {
    avg_processing_time_ms: number;
    total_frames_processed: number;
  };
}

// Alert configuration
export interface Alert {
  id: string;
  timestamp: number;
  level: 'low' | 'medium' | 'high' | 'critical';
  message: string;
  violations: string[];
  risk_score: number;
  acknowledged: boolean;
}

// Proctoring session
export interface ProctoringSession {
  id: string;
  started_at: number;
  status: 'idle' | 'active' | 'paused' | 'ended';
  total_frames: number;
  total_violations: number;
  current_risk_score: number;
  max_risk_score: number;
  alerts: Alert[];
}

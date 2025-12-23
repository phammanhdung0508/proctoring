/**
 * VideoCapture Component
 *
 * Captures video from the user's webcam and sends frames to the backend for analysis
 */

import { useEffect, useRef, useState } from 'react';
import {
  requestCameraAccess,
  stopMediaStream,
  captureFrame,
  FrameRateCalculator,
} from '../utils/videoUtils';
import type { WebSocketClient } from '../services/websocket';
import { useProctoringStore } from '../stores/proctoringStore';

interface VideoCaptureProps {
  wsClient: WebSocketClient | null;
  isActive: boolean;
  targetFPS?: number;
  showDebugOverlay?: boolean;
}

export function VideoCapture({
  wsClient,
  isActive,
  targetFPS = 5,
  showDebugOverlay = false,
}: VideoCaptureProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const intervalRef = useRef<number | null>(null);
  const fpsCalculator = useRef(new FrameRateCalculator());
  const latestAnalysis = useProctoringStore((state) => state.latestAnalysis);

  const [cameraError, setCameraError] = useState<string | null>(null);
  const [isReady, setIsReady] = useState(false);
  const [currentFPS, setCurrentFPS] = useState(0);
  const [framesSent, setFramesSent] = useState(0);

  // Initialize camera
  useEffect(() => {
    let mounted = true;

    async function initCamera() {
      try {
        setCameraError(null);
        const stream = await requestCameraAccess();

        if (!mounted) {
          stopMediaStream(stream);
          return;
        }

        streamRef.current = stream;

        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          setIsReady(true);
        }
      } catch (error) {
        console.error('❌ Failed to access camera:', error);
        setCameraError(
          error instanceof Error
            ? error.message
            : 'Failed to access camera'
        );
      }
    }

    initCamera();

    return () => {
      mounted = false;
      if (streamRef.current) {
        stopMediaStream(streamRef.current);
        streamRef.current = null;
      }
      setIsReady(false);
    };
  }, []);

  // Handle frame capture and sending
  useEffect(() => {
    console.log('📹 VideoCapture state:', {
      isActive,
      isReady,
      hasWsClient: wsClient !== null,
      targetFPS
    });

    if (!isActive || !isReady || !wsClient) {
      // Stop capturing if inactive, not ready, or no WebSocket client
      if (intervalRef.current !== null) {
        console.log('⏸️  Stopping frame capture');
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      return;
    }

    // Start capturing frames
    const intervalMs = 1000 / targetFPS;
    console.log(`▶️  Starting frame capture at ${targetFPS} FPS (interval: ${intervalMs}ms)`);

    intervalRef.current = window.setInterval(() => {
      if (!videoRef.current) {
        console.warn('⚠️ Video ref not available');
        return;
      }

      const frameData = captureFrame(videoRef.current, 0.8);

      if (!frameData) {
        console.warn('⚠️ Failed to capture frame');
        return;
      }

      if (wsClient) {
        wsClient.sendFrame(frameData);
        setFramesSent((prev) => prev + 1);

        // Update FPS calculation
        fpsCalculator.current.addFrame();
        setCurrentFPS(Math.round(fpsCalculator.current.getFPS()));
      }
    }, intervalMs);

    return () => {
      if (intervalRef.current !== null) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [isActive, isReady, wsClient, targetFPS]);

  // Reset stats when becoming inactive
  useEffect(() => {
    if (!isActive) {
      setFramesSent(0);
      setCurrentFPS(0);
      fpsCalculator.current.reset();
    }
  }, [isActive]);

  useEffect(() => {
    const canvas = canvasRef.current;
    const video = videoRef.current;

    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    if (!showDebugOverlay || !latestAnalysis || !video) {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      return;
    }

    const { videoWidth, videoHeight } = video;
    if (!videoWidth || !videoHeight) return;

    if (canvas.width !== videoWidth || canvas.height !== videoHeight) {
      canvas.width = videoWidth;
      canvas.height = videoHeight;
    }

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const drawLabel = (text: string, x: number, y: number, color: string) => {
      ctx.font = '12px Inter, system-ui, sans-serif';
      const padding = 4;
      const textWidth = ctx.measureText(text).width;
      ctx.fillStyle = color;
      ctx.fillRect(x, y - 16, textWidth + padding * 2, 16);
      ctx.fillStyle = '#0f172a';
      ctx.fillText(text, x + padding, y - 4);
    };

    const drawBox = (
      bbox: [number, number, number, number],
      color: string,
      label?: string
    ) => {
      const [x1, y1, x2, y2] = bbox;
      const width = x2 - x1;
      const height = y2 - y1;

      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.strokeRect(x1, y1, width, height);

      if (label) {
        drawLabel(label, x1, Math.max(16, y1), color);
      }
    };

    latestAnalysis.objects.forbidden_items.forEach((item) => {
      drawBox(
        item.bbox,
        '#ef4444',
        `${item.class_name || item.object}`
      );
    });

    latestAnalysis.objects.all_detections.forEach((detection) => {
      const isPerson = detection.class_name === 'person';
      const color = isPerson ? '#facc15' : '#38bdf8';
      drawBox(detection.bbox, color, detection.class_name);
    });

    if (latestAnalysis.gaze.face_detected) {
      const centerX = canvas.width / 2;
      const centerY = canvas.height / 2;
      const length = Math.min(canvas.width, canvas.height) * 0.2;
      const yawRadians = (latestAnalysis.gaze.yaw * Math.PI) / 180;
      const pitchRadians = (latestAnalysis.gaze.pitch * Math.PI) / 180;
      const endX = centerX + Math.sin(yawRadians) * length;
      const endY = centerY + Math.sin(pitchRadians) * length;

      ctx.strokeStyle = '#a855f7';
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.moveTo(centerX, centerY);
      ctx.lineTo(endX, endY);
      ctx.stroke();

      const angle = Math.atan2(endY - centerY, endX - centerX);
      const arrowLength = 10;
      ctx.beginPath();
      ctx.moveTo(endX, endY);
      ctx.lineTo(
        endX - arrowLength * Math.cos(angle - Math.PI / 6),
        endY - arrowLength * Math.sin(angle - Math.PI / 6)
      );
      ctx.lineTo(
        endX - arrowLength * Math.cos(angle + Math.PI / 6),
        endY - arrowLength * Math.sin(angle + Math.PI / 6)
      );
      ctx.closePath();
      ctx.fillStyle = '#a855f7';
      ctx.fill();

      ctx.fillStyle = '#f3e8ff';
      ctx.beginPath();
      ctx.arc(centerX, centerY, 4, 0, Math.PI * 2);
      ctx.fill();
    }
  }, [latestAnalysis, showDebugOverlay, isReady]);

  if (cameraError) {
    return (
      <div className="bg-rose-50 border border-rose-200 rounded-2xl p-6 text-center shadow-sm" data-testid="camera-error">
        <div className="text-rose-700 text-lg font-semibold mb-2">Camera access error</div>
        <div className="text-rose-600 text-sm">{cameraError}</div>
        <div className="mt-4 text-xs text-rose-600">
          Grant camera permissions and refresh to re-arm the live feed.
        </div>
      </div>
    );
  }

  return (
    <div className="glass rounded-2xl overflow-hidden" data-testid="video-capture-container">
      <div className="flex items-center justify-between px-5 py-4 border-b border-white/50">
        <div>
          <h3 className="text-sm font-bold uppercase tracking-wider text-slate-800 flex items-center gap-2">
            <span className="text-lg">📹</span> Live Feed
          </h3>
        </div>
        <div className="flex items-center gap-2 text-xs font-bold">
          <div className="px-2 py-1 rounded-md bg-white/50 border border-white/60 text-slate-600">
            {targetFPS} FPS TARGET
          </div>
          <div
            className={`px-2 py-1 rounded-md border flex items-center gap-1.5 ${isActive
              ? 'bg-emerald-100 text-emerald-700 border-emerald-200'
              : 'bg-slate-100 text-slate-600 border-slate-200'
              }`}
            data-testid="monitoring-status-badge"
          >
            <span className={`w-1.5 h-1.5 rounded-full ${isActive ? 'bg-emerald-600 animate-pulse' : 'bg-slate-400'}`} />
            {isActive ? 'LIVE' : 'PAUSED'}
          </div>
        </div>
      </div>

      {/* Video Feed */}
      <div className="relative bg-black aspect-video overflow-hidden group">

        {/* Placeholder / Empty State styling */}
        <div className="absolute inset-0 z-0">
          {!isReady && (
            <div className="w-full h-full flex flex-col items-center justify-center text-white/50 space-y-3">
              <div className="w-12 h-12 border-2 border-white/20 border-t-white/80 rounded-full animate-spin" />
              <p className="text-sm font-medium tracking-wide">Initializing Camera...</p>
            </div>
          )}
        </div>

        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          data-testid="video-element"
          className={`w-full h-full object-cover relative z-10 transition-opacity duration-500 ${isReady ? 'opacity-100' : 'opacity-0'}`}
          onLoadedMetadata={() => setIsReady(true)}
        />

        <canvas
          ref={canvasRef}
          aria-hidden="true"
          className={`absolute inset-0 z-20 w-full h-full pointer-events-none transition-opacity duration-300 ${showDebugOverlay ? 'opacity-100' : 'opacity-0'}`}
        />

        {/* Overlay Grid (Cyberpunk-ish) */}
        <div className="absolute inset-0 z-10 pointer-events-none opacity-20 bg-[linear-gradient(rgba(255,255,255,0.05)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.05)_1px,transparent_1px)] bg-[size:50px_50px]" />

        {/* Recording Indicator */}
        {isActive && (
          <div className="absolute inset-0 z-20 pointer-events-none border-[3px] border-rose-500/30 animate-pulse" />
        )}

        {/* Floating Stats */}
        <div className="absolute bottom-4 left-4 right-4 z-30 flex items-end justify-between opacity-0 group-hover:opacity-100 transition-opacity duration-300">
          <div className="bg-black/60 backdrop-blur-md rounded-lg p-2 text-white/90 text-xs font-mono space-y-1">
            <div className="flex items-center gap-2">
              <span className="text-white/50">RES:</span>
              <span>{videoRef.current?.videoWidth}x{videoRef.current?.videoHeight}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-white/50">FPS:</span>
              <span data-testid="current-fps">{currentFPS}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-white/50">Sent:</span>
              <span data-testid="frames-sent">{framesSent}</span>
            </div>
          </div>

          {isActive && (
            <div className="bg-rose-500/90 backdrop-blur text-white px-3 py-1 rounded-full text-xs font-bold animate-pulse flex items-center gap-2">
              <span className="w-2 h-2 bg-white rounded-full" />
              REC
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

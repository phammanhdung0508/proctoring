/**
 * WebSocket Client Service
 *
 * Handles real-time communication with the backend proctoring server
 */

import type {
  WebSocketMessage,
  AnalysisMessage,
  FrameMessage,
} from '../types';

export interface WebSocketConfig {
  url: string;
  sessionId: string;
  onConnected?: () => void;
  onAnalysis?: (message: AnalysisMessage) => void;
  onError?: (error: Error) => void;
  onDisconnected?: () => void;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private config: WebSocketConfig;
  private reconnectAttempts = 0;
  private reconnectTimer: number | null = null;
  private isManuallyDisconnected = false;

  constructor(config: WebSocketConfig) {
    this.config = {
      reconnectInterval: 3000,
      maxReconnectAttempts: 5,
      ...config,
    };
  }

  /**
   * Connect to the WebSocket server
   */
  connect(): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      console.warn('WebSocket already connected');
      return;
    }

    this.isManuallyDisconnected = false;
    const wsUrl = `${this.config.url}/${this.config.sessionId}`;

    try {
      console.log(`📡 Connecting to WebSocket: ${wsUrl}`);
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = this.handleOpen.bind(this);
      this.ws.onmessage = this.handleMessage.bind(this);
      this.ws.onerror = this.handleError.bind(this);
      this.ws.onclose = this.handleClose.bind(this);
    } catch (error) {
      console.error('❌ WebSocket connection error:', error);
      this.config.onError?.(error as Error);
      this.scheduleReconnect();
    }
  }

  /**
   * Disconnect from the WebSocket server
   */
  disconnect(): void {
    this.isManuallyDisconnected = true;
    this.clearReconnectTimer();

    if (this.ws) {
      this.ws.close(1000, 'Client disconnect');
      this.ws = null;
    }
  }

  /**
   * Send a frame to the server for analysis
   */
  sendFrame(frameData: string | Blob, timestamp?: number): void {
    if (!this.isConnected()) {
      // Limit warning logs to avoid console spam
      if (Math.random() < 0.05) {
        console.warn('⚠️ Cannot send frame: WebSocket not connected');
      }
      return;
    }

    if (frameData instanceof Blob) {
      // FAST PATH: Send binary data directly
      // This avoids Base64 encoding overhead
      this.sendBinary(frameData);
    } else {
      // SLOW PATH: Legacy JSON/Base64
      const message: FrameMessage = {
        type: 'frame',
        data: frameData,
        timestamp: timestamp || Date.now() / 1000,
      };

      // Only log occasionally
      if (Math.random() < 0.01) {
        console.log('📤 Sending frame (JSON):', {
          dataSize: frameData.length,
          timestamp: message.timestamp
        });
      }

      this.send(message);
    }
  }

  /**
   * Send binary data to the server
   */
  private sendBinary(data: Blob): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      return;
    }

    try {
      this.ws.send(data);
    } catch (error) {
      console.error('❌ Error sending binary message:', error);
      this.config.onError?.(error as Error);
    }
  }

  /**
   * Send a ping to check connection
   */
  ping(): void {
    this.send({ type: 'ping', timestamp: Date.now() / 1000 });
  }

  /**
   * Request session statistics
   */
  requestStats(): void {
    this.send({ type: 'get_stats', timestamp: Date.now() / 1000 });
  }

  /**
   * Check if WebSocket is connected
   */
  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  /**
   * Get connection state
   */
  getState(): number {
    return this.ws?.readyState ?? WebSocket.CLOSED;
  }

  /**
   * Handle WebSocket open event
   */
  private handleOpen(): void {
    console.log('✅ WebSocket connected');
    this.reconnectAttempts = 0;
    this.clearReconnectTimer();
    this.config.onConnected?.();
  }

  /**
   * Handle incoming WebSocket messages
   */
  private handleMessage(event: MessageEvent): void {
    try {
      const message: WebSocketMessage = JSON.parse(event.data);

      switch (message.type) {
        case 'connected':
          console.log('🔌 Server confirmed connection:', message.message);
          break;

        case 'analysis':
          this.config.onAnalysis?.(message as AnalysisMessage);
          break;

        case 'pong':
          console.log('🏓 Pong received');
          break;

        case 'stats':
          console.log('📊 Stats received:', message.data);
          break;

        case 'error':
          console.error('❌ Server error:', message.message);
          this.config.onError?.(new Error(message.message));
          break;

        default:
          console.log('📨 Unknown message type:', message.type);
      }
    } catch (error) {
      console.error('❌ Error parsing message:', error);
      this.config.onError?.(error as Error);
    }
  }

  /**
   * Handle WebSocket error event
   */
  private handleError(event: Event): void {
    console.error('❌ WebSocket error:', event);
    this.config.onError?.(new Error('WebSocket error'));
  }

  /**
   * Handle WebSocket close event
   */
  private handleClose(event: CloseEvent): void {
    console.log(`🔌 WebSocket closed: ${event.code} - ${event.reason}`);
    this.ws = null;
    this.config.onDisconnected?.();

    // Attempt to reconnect if not manually disconnected
    if (!this.isManuallyDisconnected) {
      this.scheduleReconnect();
    }
  }

  /**
   * Send a message to the server
   */
  private send(message: WebSocketMessage): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn('⚠️ Cannot send message: WebSocket not connected');
      return;
    }

    try {
      this.ws.send(JSON.stringify(message));
    } catch (error) {
      console.error('❌ Error sending message:', error);
      this.config.onError?.(error as Error);
    }
  }

  /**
   * Schedule a reconnection attempt
   */
  private scheduleReconnect(): void {
    const maxAttempts = this.config.maxReconnectAttempts ?? 5;

    if (this.reconnectAttempts >= maxAttempts) {
      console.error(`❌ Max reconnect attempts (${maxAttempts}) reached`);
      this.config.onError?.(new Error('Max reconnect attempts reached'));
      return;
    }

    this.reconnectAttempts++;
    const interval = this.config.reconnectInterval ?? 3000;

    console.log(
      `🔄 Scheduling reconnect attempt ${this.reconnectAttempts}/${maxAttempts} in ${interval}ms`
    );

    this.reconnectTimer = window.setTimeout(() => {
      this.connect();
    }, interval);
  }

  /**
   * Clear the reconnect timer
   */
  private clearReconnectTimer(): void {
    if (this.reconnectTimer !== null) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }
}

/**
 * Create a WebSocket client instance
 */
export function createWebSocketClient(config: WebSocketConfig): WebSocketClient {
  return new WebSocketClient(config);
}

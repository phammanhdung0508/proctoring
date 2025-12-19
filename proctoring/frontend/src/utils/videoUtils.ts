/**
 * Video Utilities
 *
 * Helper functions for video capture and frame processing
 */

/**
 * Request camera access
 */
export async function requestCameraAccess(
  constraints?: MediaStreamConstraints
): Promise<MediaStream> {
  const defaultConstraints: MediaStreamConstraints = {
    video: {
      width: { ideal: 1280 },
      height: { ideal: 720 },
      facingMode: 'user',
    },
    audio: false,
  };

  try {
    const stream = await navigator.mediaDevices.getUserMedia(
      constraints || defaultConstraints
    );
    return stream;
  } catch (error) {
    console.error('❌ Error accessing camera:', error);
    throw new Error('Failed to access camera');
  }
}

/**
 * Capture a frame from a video element
 */
export function captureFrame(
  video: HTMLVideoElement,
  quality = 0.8
): string | null {
  if (!video || video.readyState !== video.HAVE_ENOUGH_DATA) {
    return null;
  }

  try {
    // Create a canvas to capture the frame
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    const ctx = canvas.getContext('2d');
    if (!ctx) {
      console.error('❌ Failed to get canvas context');
      return null;
    }

    // Draw the current video frame
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    // Convert to base64 JPEG
    const dataUrl = canvas.toDataURL('image/jpeg', quality);

    // Extract base64 data (remove "data:image/jpeg;base64," prefix)
    const base64Data = dataUrl.split(',')[1];

    return base64Data;
  } catch (error) {
    console.error('❌ Error capturing frame:', error);
    return null;
  }
}

/**
 * Stop a media stream
 */
export function stopMediaStream(stream: MediaStream | null): void {
  if (!stream) return;

  stream.getTracks().forEach((track) => {
    track.stop();
  });
}

/**
 * Check if camera is available
 */
export async function isCameraAvailable(): Promise<boolean> {
  try {
    const devices = await navigator.mediaDevices.enumerateDevices();
    return devices.some((device) => device.kind === 'videoinput');
  } catch (error) {
    console.error('❌ Error checking camera availability:', error);
    return false;
  }
}

/**
 * Get list of available cameras
 */
export async function getCameraList(): Promise<MediaDeviceInfo[]> {
  try {
    const devices = await navigator.mediaDevices.enumerateDevices();
    return devices.filter((device) => device.kind === 'videoinput');
  } catch (error) {
    console.error('❌ Error getting camera list:', error);
    return [];
  }
}

/**
 * Calculate frame rate
 */
export class FrameRateCalculator {
  private timestamps: number[] = [];
  private maxSamples = 30;

  addFrame(): void {
    const now = performance.now();
    this.timestamps.push(now);

    // Keep only recent samples
    if (this.timestamps.length > this.maxSamples) {
      this.timestamps.shift();
    }
  }

  getFPS(): number {
    if (this.timestamps.length < 2) {
      return 0;
    }

    const first = this.timestamps[0];
    const last = this.timestamps[this.timestamps.length - 1];
    const elapsed = last - first;

    if (elapsed === 0) {
      return 0;
    }

    return ((this.timestamps.length - 1) / elapsed) * 1000;
  }

  reset(): void {
    this.timestamps = [];
  }
}
